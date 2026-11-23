import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Discipline, User
from apps.finance.models import EmployeeContract, FinancialRecord
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskComment

from .models import CompositionTemplate, Contract, OperationInfo, PlanRow, ProgressReport, PultSettings, TaskWorkflow
from .services import kpi_points, save_workflow, today


class PultTestBase(TestCase):
    def setUp(self):
        self.boss = User.objects.create_user(email="boss@example.com", password="pw12345!", full_name="Boss", role=User.Role.MANAGER)
        self.gip = User.objects.create_user(email="gip@example.com", password="pw12345!", full_name="Gip", role=User.Role.GIP)
        self.worker = User.objects.create_user(email="worker@example.com", password="pw12345!", full_name="Worker", role=User.Role.DESIGNER)
        self.other = User.objects.create_user(email="other@example.com", password="pw12345!", full_name="Other", role=User.Role.DESIGNER)
        self.client_user = User.objects.create_user(email="client@example.com", password="pw12345!", full_name="Client", role=User.Role.CLIENT)
        self.project = Project.objects.create(name="P1", created_by=self.boss)
        for u in (self.gip, self.worker, self.other):
            ProjectMember.objects.create(project=self.project, user=u, can_edit=False)
        self.task = Task.objects.create(title="AR drawings", project=self.project, assignee=self.worker, creator=self.gip, reviewer=self.gip)
        self.wf = self.task.workflow

    def post(self, user, url, body):
        self.client.force_login(user)
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def act(self, user, action, params=None, expect=None):
        url = reverse("pult:api_action", args=[self.wf.number])
        return self.post(user, url, {"action": action, "params": params or {}, "expect_status": expect})

    def refresh(self):
        self.task.refresh_from_db()
        self.wf.refresh_from_db()


class WorkflowRowTests(PultTestBase):
    def test_every_platform_task_gets_a_number(self):
        second = Task.objects.create(title="KJ", project=self.project, creator=self.boss)
        self.assertEqual(second.workflow.number, self.wf.number + 1)

    def test_data_endpoint_lists_task_by_number(self):
        self.client.force_login(self.worker)
        data = self.client.get(reverse("pult:api_data")).json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["viewer"]["role"], "Специалист")
        row = next(t for t in data["tasks"] if t["id"] == self.wf.number)
        self.assertEqual(row["assignee"], "Worker")
        self.assertEqual(row["status"], "Новая")
        self.assertFalse(row["canApprove"])

    def test_client_role_has_no_access(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("pult:api_data")).status_code, 403)

    def test_status_moved_on_old_board_is_respected(self):
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.REVIEW)
        self.client.force_login(self.gip)
        data = self.client.get(reverse("pult:api_data")).json()
        row = next(t for t in data["tasks"] if t["id"] == self.wf.number)
        self.assertEqual(row["status"], "На проверке")
        self.assertTrue(row["canApprove"])


class SectionPageTests(PultTestBase):
    """Pult sahifalari alohida menyuda emas, platforma bo'limlari ichida."""

    def test_sections_live_under_their_menus(self):
        self.client.force_login(self.boss)
        for name, path in (("section_work", "/tasks/my-work/"), ("section_plan", "/projects/schedule/"),
                           ("section_contracts", "/finance/contracts/"), ("section_kpi", "/accounts/users/kpi/"),
                           ("section_home", "/reports/summary/")):
            self.assertEqual(reverse(f"pult:{name}"), path)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "?embed=1#")

    def test_role_without_the_page_is_refused(self):
        self.client.force_login(self.worker)
        self.assertEqual(self.client.get(reverse("pult:section_work")).status_code, 200)
        self.assertEqual(self.client.get(reverse("pult:section_contracts")).status_code, 403)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("pult:section_work")).status_code, 403)

    def test_viewer_pages_come_from_the_server(self):
        self.client.force_login(self.worker)
        pages = self.client.get(reverse("pult:api_data")).json()["viewer"]["pages"]
        self.assertEqual(pages, ["work", "kanban", "plan", "kpi"])

    def test_menu_shows_only_allowed_tabs(self):
        self.client.force_login(self.worker)
        board = self.client.get(reverse("tasks:board"))
        self.assertContains(board, reverse("pult:section_work"))
        self.assertNotContains(board, reverse("pult:section_tasks"))
        self.assertNotContains(board, "/tasks/gantt/")
        self.assertNotContains(board, 'href="/pult/"')

    def test_old_address_redirects(self):
        self.client.force_login(self.boss)
        self.assertRedirects(self.client.get("/pult/"), reverse("pult:section_work"))

    def test_gantt_tab_is_removed(self):
        self.client.force_login(self.boss)
        self.assertNotContains(self.client.get(reverse("tasks:board")), "/tasks/gantt/")
        self.assertRedirects(self.client.get("/tasks/gantt/"), reverse("tasks:board"), fetch_redirect_response=False)


class ActionTests(PultTestBase):
    def test_full_cycle_accept_submit_review(self):
        self.wf.days = 5
        save_workflow(self.task, self.wf)
        self.assertEqual(self.act(self.worker, "accept").status_code, 200)
        self.refresh()
        self.assertEqual(self.wf.status, "В работе")
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)
        self.assertEqual(self.task.deadline, today() + timedelta(days=5))

        self.assertEqual(self.act(self.worker, "submit", {"src": True}).status_code, 200)
        self.refresh()
        self.assertEqual(self.task.status, Task.Status.REVIEW)
        self.assertEqual(self.wf.done, 1)

        self.assertEqual(self.act(self.gip, "review_ok").status_code, 200)
        self.refresh()
        self.assertEqual(self.wf.status, "Принята")
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertTrue(ProgressReport.objects.filter(task=self.task, status="Принята").exists())

    def test_assignee_cannot_accept_own_work(self):
        self.wf.status = "На проверке"
        save_workflow(self.task, self.wf)
        response = self.act(self.worker, "review_ok")
        self.assertEqual(response.status_code, 403)
        self.refresh()
        self.assertEqual(self.wf.status, "На проверке")

    def test_other_designer_cannot_act_for_assignee(self):
        self.assertEqual(self.act(self.other, "accept_own", {"days": 3}).status_code, 403)

    def test_action_from_wrong_status_is_rejected(self):
        self.assertEqual(self.act(self.worker, "submit").status_code, 409)

    def test_stale_status_is_rejected(self):
        response = self.act(self.worker, "accept_own", {"days": 3}, expect="В работе")
        self.assertEqual(response.status_code, 409)

    def test_review_back_counts_rework_and_leaves_comment(self):
        self.wf.status = "На проверке"
        self.wf.done = 1
        save_workflow(self.task, self.wf)
        self.assertEqual(self.act(self.gip, "review_back", {"why": "fix axes"}).status_code, 200)
        self.refresh()
        self.assertEqual(self.wf.status, "На доработке")
        self.assertEqual(self.wf.reworks, 1)
        self.assertEqual(self.task.status, Task.Status.REVISION)
        self.assertTrue(TaskComment.objects.filter(task=self.task, content__contains="fix axes").exists())

    def test_review_back_requires_reason(self):
        self.wf.status = "На проверке"
        save_workflow(self.task, self.wf)
        self.assertEqual(self.act(self.gip, "review_back", {"why": " "}).status_code, 400)

    def test_approval_pause_extends_term(self):
        self.wf.status, self.wf.days = "Согласование", 10
        self.wf.start_date = today() - timedelta(days=5)
        self.wf.approval_since = today() - timedelta(days=3)
        save_workflow(self.task, self.wf)
        self.act(self.gip, "appr_ok")
        self.refresh()
        self.assertEqual(self.wf.days, 13)
        self.assertIsNone(self.wf.approval_since)

    def test_only_boss_can_drag_on_kanban(self):
        self.assertEqual(self.act(self.gip, "move", {"col": "done"}).status_code, 403)
        self.assertEqual(self.act(self.boss, "move", {"col": "done"}).status_code, 200)
        self.refresh()
        self.assertEqual(self.wf.status, "Принята")


class ReportAndCreateTests(PultTestBase):
    def test_daily_report_updates_percent(self):
        self.wf.status, self.wf.start_date, self.wf.days = "В работе", today(), 5
        save_workflow(self.task, self.wf)
        response = self.post(self.worker, reverse("pult:api_report"), {"items": [{"id": self.wf.number, "done": 40}], "note": "walls"})
        self.assertEqual(response.status_code, 200)
        self.refresh()
        self.assertAlmostEqual(self.wf.done, 0.4)
        self.assertTrue(ProgressReport.objects.filter(task=self.task, status="", comment="Отчёт: walls").exists())

    def test_report_for_someone_elses_task_is_rejected(self):
        self.wf.status = "В работе"
        save_workflow(self.task, self.wf)
        response = self.post(self.other, reverse("pult:api_report"), {"items": [{"id": self.wf.number, "done": 40}]})
        self.assertEqual(response.status_code, 403)

    def test_gip_creates_task_with_term(self):
        response = self.post(self.gip, reverse("pult:api_create"), {"task": "KJ", "assignee": "Worker", "project": "P1", "days": 4})
        self.assertEqual(response.status_code, 200)
        wf = TaskWorkflow.objects.get(number=response.json()["id"])
        self.assertEqual(wf.status, "В работе")
        self.assertEqual(wf.task.creator, self.gip)
        self.assertEqual(wf.task.deadline, today() + timedelta(days=4))

    def test_designer_cannot_create_project_task(self):
        response = self.post(self.worker, reverse("pult:api_create"), {"task": "x", "assignee": "Other", "project": "P1", "flow": "Проект"})
        self.assertEqual(response.status_code, 403)

    def test_nonstd_task_without_project_goes_to_internal_project(self):
        response = self.post(self.boss, reverse("pult:api_create"), {"task": "Order paper", "assignee": "Other", "project": "GASTEC", "flow": "Нестандартная", "dept": "Админ"})
        self.assertEqual(response.status_code, 200)
        wf = TaskWorkflow.objects.get(number=response.json()["id"])
        self.assertEqual(wf.task.project, PultSettings.load().internal_project)
        self.assertEqual(wf.dept, "Админ")

    def test_edit_requires_manage_right(self):
        url = reverse("pult:api_edit", args=[self.wf.number])
        body = {"task": "renamed", "assignee": "Worker", "project": "P1", "status": "Принята"}
        self.assertEqual(self.post(self.other, url, body).status_code, 403)
        self.assertEqual(self.post(self.boss, url, body).status_code, 200)
        self.refresh()
        self.assertEqual(self.task.title, "renamed")
        self.assertEqual(self.wf.finished_at, today())


class KpiTests(TestCase):
    def test_points(self):
        s = PultSettings()
        self.assertEqual(kpi_points(-1, 0, 0, s), 5)   # early + clean
        self.assertEqual(kpi_points(0, 1, 0, s), 0)    # on time, one rework
        self.assertEqual(kpi_points(5, 3, 10, s), -9)  # late big, quality floor, missed cap


class PlanTests(PultTestBase):
    def plan_url(self):
        return reverse("pult:api_plan")

    def state(self, user):
        self.client.force_login(user)
        return self.client.get(self.plan_url()).json()

    def row(self, rid, **kw):
        base = {"id": rid, "project": "P1", "wbs": str(rid), "code": "АР", "name": "Архитектура", "kind": "Раздел", "dur": 10, "inPlan": "Да"}
        base.update(kw)
        return base

    def test_object_from_composition_appears_on_project_page(self):
        from apps.projects.models import SubObject, SubObjectDiscipline

        state = self.state(self.gip)
        rows = [self.row(1, wbs="1", code="BL01", name="Корпус 1", kind="Объект", dur=None),
                self.row(2, wbs="1.1", code="АР", name="Архитектура", owner="Worker")]
        self.assertEqual(self.post(self.gip, self.plan_url(), {"rows": rows, "version": state["version"]}).status_code, 200)
        sub = SubObject.objects.get(project=self.project)
        self.assertEqual(sub.name, "Корпус 1")
        link = SubObjectDiscipline.objects.get(sub_object=sub)
        self.assertEqual((link.discipline.code, link.assignee), (PlanRow.objects.get(pk=2).code, self.worker))
        self.assertEqual(PlanRow.objects.get(pk=1).source_key, f"so:{sub.pk}")
        # rename in the composition renames the object; nothing is duplicated
        state = self.state(self.gip)
        rows[0]["name"] = "Корпус А"
        self.assertEqual(self.post(self.gip, self.plan_url(), {"rows": rows, "version": state["version"]}).status_code, 200)
        self.assertEqual(list(SubObject.objects.filter(project=self.project).values_list("name", flat=True)), ["Корпус А"])
        self.assertEqual(SubObjectDiscipline.objects.filter(sub_object=sub).count(), 1)

    def test_gip_saves_plan_and_version_moves(self):
        state = self.state(self.gip)
        response = self.post(self.gip, self.plan_url(), {"rows": [self.row(state["nextId"])], "version": state["version"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlanRow.objects.get().name, "Архитектура")
        self.assertEqual(self.state(self.gip)["version"], state["version"] + 1)

    def test_stale_version_is_rejected(self):
        state = self.state(self.gip)
        response = self.post(self.gip, self.plan_url(), {"rows": [self.row(1)], "version": state["version"] + 5})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(PlanRow.objects.exists())

    def test_designer_cannot_change_plan(self):
        state = self.state(self.worker)
        response = self.post(self.worker, self.plan_url(), {"rows": [self.row(1)], "version": state["version"]})
        self.assertEqual(response.status_code, 403)

    def test_rows_of_unseen_projects_survive(self):
        hidden = Project.objects.create(name="Hidden", created_by=self.boss)
        PlanRow.objects.create(id=50, project=hidden, name="secret")
        state = self.state(self.gip)
        self.post(self.gip, self.plan_url(), {"rows": [], "version": state["version"]})
        self.assertTrue(PlanRow.objects.filter(pk=50).exists())

    def test_sync_creates_draft_tasks_and_links_them(self):
        PlanRow.objects.create(id=7, project=self.project, wbs="1.1", code="АР", name="Архитектура", kind="Раздел", owner="Worker")
        body = {"project": "P1", "taskNew": [{"id": 999, "assignee": "Worker", "task": "АР — Архитектура", "days": 6, "section": 7, "comment": "Из состава проекта"}],
                "sec": [[7, {"task": 999}]]}
        response = self.post(self.gip, reverse("pult:api_sync"), body)
        self.assertEqual(response.status_code, 200)
        wf = TaskWorkflow.objects.get(section=7)
        self.assertEqual(wf.status, "Черновик")
        self.assertEqual(wf.flow, "Проект")
        self.assertEqual(PlanRow.objects.get(pk=7).task, wf.number)

    def test_sync_rejects_section_of_other_project(self):
        other = Project.objects.create(name="P2", created_by=self.boss)
        PlanRow.objects.create(id=8, project=other, name="x")
        body = {"project": "P1", "taskNew": [{"id": 1, "assignee": "Worker", "task": "x", "section": 8}]}
        self.assertEqual(self.post(self.gip, reverse("pult:api_sync"), body).status_code, 400)

    def test_task_section_must_belong_to_project(self):
        other = Project.objects.create(name="P2", created_by=self.boss)
        PlanRow.objects.create(id=9, project=other, name="x")
        body = {"task": "x", "assignee": "Worker", "project": "P1", "section": 9, "flow": "Проект"}
        self.assertEqual(self.post(self.gip, reverse("pult:api_create"), body).status_code, 400)

    def test_gip_adds_discipline(self):
        response = self.post(self.gip, reverse("pult:api_discipline"), {"code": "гсн", "name": "Газоснабжение", "dur": 12})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Discipline.objects.get(code="ГСН").pult_config.duration, 12)

    def test_default_composition_template_is_seeded(self):
        self.client.force_login(self.gip)
        tpls = self.client.get(reverse("pult:api_data")).json()["compTemplates"]
        self.assertEqual(len(tpls), 1)
        items = {it["wbs"]: it for it in tpls[0]["items"]}
        self.assertEqual(items["3.2"]["preds"], "2.2ОН-5; 3.1НН+5")

    def test_gip_edits_composition_template(self):
        url = reverse("pult:api_comp_template")
        items = [
            {"wbs": "2", "name": "Этап", "kind": "Этап"},
            {"wbs": "1", "name": "Старт", "kind": "Веха"},
            {"wbs": "2.1", "code": "ар", "name": "Архитектура", "kind": "Раздел", "dur": 7, "preds": "1 ; 1нн+2"},
        ]
        response = self.post(self.gip, url, {"name": "Жилой дом", "items": items})
        self.assertEqual(response.status_code, 200, response.content)
        tpl = CompositionTemplate.objects.get(name="Жилой дом")
        self.assertEqual([it["wbs"] for it in tpl.items], ["1", "2", "2.1"])
        self.assertEqual(tpl.items[2]["preds"], "1; 1НН+2")
        self.assertEqual(tpl.items[2]["code"], "АР")
        self.assertIsNone(tpl.items[1]["dur"])
        # link to a missing row is refused
        bad = items[:2] + [{**items[2], "preds": "9"}]
        self.assertEqual(self.post(self.gip, url, {"id": tpl.pk, "name": "Жилой дом", "items": bad}).status_code, 400)
        # workers cannot edit, GIP can delete
        self.assertEqual(self.post(self.worker, url, {"id": tpl.pk, "delete": True}).status_code, 403)
        self.assertEqual(self.post(self.gip, url, {"id": tpl.pk, "delete": True}).status_code, 200)
        self.assertFalse(CompositionTemplate.objects.filter(name="Жилой дом").exists())

    def test_discipline_from_users_page_shows_in_composition(self):
        self.client.force_login(self.boss)
        self.client.post(reverse("accounts:discipline_create"), {"code": "ГСН", "name": "Газоснабжение"})
        cfg = Discipline.objects.get(code="ГСН").pult_config
        self.assertEqual(cfg.latin_code, "GSN")
        data = self.client.get(reverse("pult:api_data")).json()
        self.assertIn("ГСН", [d["code"] for d in data["disc"]])

    def test_composition_section_becomes_discipline(self):
        state = self.state(self.gip)
        rows = [self.row(1, code="ИД", name="ИД. Сбор исходных данных")]
        self.assertEqual(self.post(self.gip, self.plan_url(), {"rows": rows, "version": state["version"]}).status_code, 200)
        d = Discipline.objects.get(code="ИД")
        self.assertEqual(d.name, "Сбор исходных данных")
        self.assertEqual(d.pult_config.latin_code, "ID")

    def test_discipline_used_in_composition_cannot_be_deleted(self):
        d = Discipline.objects.create(code="ТХ", name="Технология")
        PlanRow.objects.create(id=3, project=self.project, wbs="1.1", code="ТХ", name="Технология", kind="Раздел")
        self.client.force_login(self.boss)
        self.client.post(reverse("accounts:discipline_delete", args=[d.pk]))
        self.assertTrue(Discipline.objects.filter(pk=d.pk).exists())


class FinanceTests(PultTestBase):
    def test_finance_is_hidden_from_designer(self):
        self.client.force_login(self.worker)
        data = self.client.get(reverse("pult:api_data")).json()
        self.assertFalse(data["features"]["finance"])
        self.assertNotIn("ops", data)
        response = self.post(self.worker, reverse("pult:api_ops"), {"rows": [{"date": "2026-10-01", "project": "P1", "uzs": 5}]})
        self.assertEqual(response.status_code, 403)

    def test_contract_payment_updates_employee_contract(self):
        body = {"project": "P1", "conNew": [{"id": "Д-001", "name": "Worker", "section": "АР", "cur": "USD", "amount": 500, "note": ""}]}
        self.assertEqual(self.post(self.boss, reverse("pult:api_sync"), body).status_code, 200)
        contract = Contract.objects.get(code="Д-001")
        self.assertEqual(contract.user, self.worker)

        row = {"date": "2026-10-01", "project": "P1", "who": "Worker", "cat": "Оплата исполнителю", "usd": -200,
               "method": "Наличные", "contract": "Д-001", "offset": 200, "note": "аванс"}
        self.assertEqual(self.post(self.boss, reverse("pult:api_ops"), {"rows": [row]}).status_code, 200)
        record = FinancialRecord.objects.get(pult_info__contract=contract)
        self.assertEqual((record.type, record.amount, record.currency, record.account), ("expense", 200, "USD", "usd_cash"))
        ec = EmployeeContract.objects.get(pk=contract.employee_contract_id)
        self.assertEqual((ec.amount, ec.paid), (500, 200))

        self.client.force_login(self.boss)
        data = self.client.get(reverse("pult:api_data")).json()
        c = next(x for x in data["contracts"] if x["id"] == "Д-001")
        self.assertEqual(c["rest"], 300)
        self.assertEqual(data["home"]["usd"], -200)

    def test_conversion_writes_two_records(self):
        row = {"date": "2026-10-01", "project": "P1", "who": "Банк", "cat": "Конвертация", "uzs": 12700000, "usd": -1000, "method": "Перечисление"}
        self.post(self.boss, reverse("pult:api_ops"), {"rows": [row]})
        self.assertEqual(FinancialRecord.objects.count(), 2)
        self.assertEqual(OperationInfo.objects.count(), 2)

    def test_records_from_finance_page_get_numbers(self):
        record = FinancialRecord.objects.create(project=self.project, type="income", amount=10, date=today(), created_by=self.boss)
        self.assertTrue(OperationInfo.objects.filter(record=record).exists())

class PlatformImportTests(PultTestBase):
    def test_objects_and_disciplines_are_imported_once(self):
        from apps.projects.models import SubObject, SubObjectDiscipline
        ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Arxitektura"})
        office = SubObject.objects.create(project=self.project, name="Офис")
        block = SubObject.objects.create(project=self.project, name="Блок А", parent=office)
        SubObjectDiscipline.objects.create(sub_object=block, discipline=ar, assignee=self.worker)
        url = reverse("pult:api_plan_import")

        first = self.post(self.gip, url, {"project": "P1"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["added"], {"objects": 1, "sections": 1, "owners": 0})
        obj = PlanRow.objects.get(kind="Объект")
        self.assertEqual(obj.name, "Офис · Блок А")
        section = PlanRow.objects.get(kind="Раздел")
        self.assertEqual((section.wbs, section.code, section.owner, section.in_plan), (obj.wbs + ".1", "AR", "Worker", "Нет"))

        again = self.post(self.gip, url, {"project": "P1"})
        self.assertEqual(again.json()["added"], {"objects": 0, "sections": 0, "owners": 0})
        self.assertEqual(PlanRow.objects.count(), 2)

    def test_designer_cannot_import(self):
        self.assertEqual(self.post(self.worker, reverse("pult:api_plan_import"), {"project": "P1"}).status_code, 403)

class ReminderTests(PultTestBase):
    def setUp(self):
        super().setUp()
        from datetime import date
        from unittest import mock

        # Eslatmalar faqat ish kunida ketadi — testni hafta kuniga bog'lab qo'ymaymiz.
        patcher = mock.patch("apps.pult.tasks.today", return_value=date(2026, 10, 28))  # chorshanba
        patcher.start()
        self.addCleanup(patcher.stop)
        self.day = date(2026, 10, 28)

    def test_report_reminder_goes_to_assignee_without_report_once(self):
        from apps.notifications.models import Notification

        from .tasks import REPORT_TITLE, remind_daily_reports
        self.wf.status, self.wf.start_date, self.wf.days = "В работе", self.day - timedelta(days=2), 10
        save_workflow(self.task, self.wf)
        self.assertEqual(remind_daily_reports(), 1)
        self.assertEqual(remind_daily_reports(), 0)  # bir kunda bitta xabar
        self.assertEqual(Notification.objects.filter(user=self.worker, title=REPORT_TITLE).count(), 1)

    def test_no_reminder_after_report(self):
        from .tasks import remind_daily_reports
        self.wf.status, self.wf.start_date = "В работе", self.day - timedelta(days=2)
        save_workflow(self.task, self.wf)
        ProgressReport.objects.create(task=self.task, author=self.worker, date=self.day, done=0.3, comment="Отчёт")
        self.assertEqual(remind_daily_reports(), 0)

    def test_digest_reaches_reviewer_not_assignee(self):
        from apps.notifications.models import Notification

        from .tasks import DIGEST_TITLE, digest_pending_decisions
        self.wf.status = "На проверке"
        save_workflow(self.task, self.wf)
        digest_pending_decisions()
        self.assertTrue(Notification.objects.filter(user=self.gip, title=DIGEST_TITLE).exists())
        self.assertFalse(Notification.objects.filter(user=self.worker, title=DIGEST_TITLE).exists())

class CipherRuleTests(PultTestBase):
    """Shifr: ИСПОЛНИТЕЛЬ_ЗАКАЗЧИК_ДОГОВОР_ОБЪЕКТ_ДИСЦИПЛИНА_№ (GTP_MIM_D125_OF_AR_001)."""

    def save(self, user, **kw):
        body = {"project": "P1", "prefix": "GTP", "client": "MIM", "code": "D125", "digits": 3, **kw}
        return self.post(user, reverse("pult:api_cipher"), body)

    def test_gip_saves_six_part_rule(self):
        response = self.save(self.gip, prefix=" gtp ", client="m im", digits=4)
        self.assertEqual(response.status_code, 200, response.content)
        rule = self.project.pult_cipher
        self.assertEqual((rule.prefix, rule.client, rule.code, rule.digits, rule.stage), ("GTP", "MIM", "D125", 4, ""))
        self.assertEqual(str(rule), "GTP_MIM_D125")

    def test_customer_code_is_required(self):
        response = self.save(self.gip, client="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("заказчика", response.json()["error"])

    def test_rule_reaches_the_browser_with_customer_code(self):
        self.save(self.gip)
        self.client.force_login(self.gip)
        ciphers = self.client.get(reverse("pult:api_data")).json()["ciphers"]
        self.assertEqual(ciphers, [{"project": "P1", "prefix": "GTP", "client": "MIM", "code": "D125", "digits": 3, "common": "ZZ01"}])

    def test_designer_cannot_change_rule(self):
        self.assertEqual(self.save(self.worker).status_code, 403)


class UnifiedBoardTests(PultTestBase):
    """«Канбан разделов» «Задачи» doskasiga qo'shildi: bitta ustunlar ketma-ketligi."""

    COLUMNS = ["draft", "new", "work", "appr", "smeta", "form", "print", "closed"]

    def make_section_task(self, status="Черновик", section=7):
        PlanRow.objects.get_or_create(id=section, defaults={
            "project": self.project, "wbs": "1.1", "code": "AR", "name": "Архитектура", "kind": "Раздел", "owner": "Worker"})
        task = Task.objects.create(title="AR — Архитектура", project=self.project, assignee=self.worker, creator=self.gip)
        wf = task.workflow
        wf.status, wf.flow, wf.stage, wf.section = status, "Проект", "Проектирование", section
        save_workflow(task, wf)
        return task, wf

    def move(self, user, task, column):
        self.client.force_login(user)
        return self.client.post(reverse("tasks:board_move", args=[task.pk]), {"column": column})

    def test_section_kanban_tab_is_gone_and_redirects(self):
        self.client.force_login(self.boss)
        board = self.client.get(reverse("tasks:board"))
        self.assertNotContains(board, 'href="/tasks/sections/"')
        self.assertRedirects(self.client.get("/tasks/sections/"), "/tasks/?kind=project", fetch_redirect_response=False)

    def test_board_shows_stage_columns_in_order(self):
        self.client.force_login(self.boss)
        html = self.client.get(reverse("tasks:board")).content.decode()
        positions = [html.index(f'data-kanban-column="{c}"') for c in self.COLUMNS]
        self.assertEqual(positions, sorted(positions))

    def test_project_and_nonstandard_filter(self):
        task, _wf = self.make_section_task()
        self.client.force_login(self.boss)
        project = self.client.get(reverse("tasks:board") + "?kind=project").content.decode()
        other = self.client.get(reverse("tasks:board") + "?kind=other").content.decode()
        self.assertIn(str(task.pk), project)
        self.assertNotIn(str(self.task.pk), project)
        self.assertIn(str(self.task.pk), other)
        self.assertNotIn(str(task.pk), other)

    def test_card_moves_through_every_column(self):
        task, wf = self.make_section_task()
        expected = {"new": ("Новая", "Проектирование"), "work": ("В работе", "Проектирование"),
                    "appr": ("Согласование", "Проектирование"), "smeta": ("В работе", "Смета"),
                    "form": ("В работе", "Оформление"), "print": ("В работе", "Печать"),
                    "closed": ("Принята", "Печать"), "draft": ("Черновик", "Проектирование")}
        for column, (status, stage) in expected.items():
            response = self.move(self.boss, task, column)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["column"], column)
            wf.refresh_from_db()
            self.assertEqual((wf.status, wf.stage), (status, stage), column)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.NEW)  # platforma holati ham sinxron

    def test_stage_columns_need_a_section(self):
        self.assertEqual(self.move(self.boss, self.task, "smeta").status_code, 400)

    def test_gip_moves_designer_does_not(self):
        self.assertEqual(self.move(self.gip, self.task, "work").status_code, 200)
        self.assertEqual(self.move(self.worker, self.task, "closed").status_code, 403)
        self.refresh()
        self.assertEqual(self.wf.status, "В работе")

    def test_board_delete_button(self):
        self.client.force_login(self.boss)
        self.assertContains(self.client.get(reverse("tasks:board")), reverse("tasks:delete", args=[self.task.pk]))
        response = self.client.post(reverse("tasks:delete", args=[self.task.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json(), {"ok": True})
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())


class DeleteTaskTests(PultTestBase):
    def test_creator_deletes_and_composition_link_is_cleared(self):
        PlanRow.objects.create(id=7, project=self.project, wbs="1.1", code="AR", kind="Раздел", task=self.wf.number)
        response = self.post(self.gip, reverse("pult:api_delete", args=[self.wf.number]), {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertIsNone(PlanRow.objects.get(pk=7).task)

    def test_assignee_cannot_delete(self):
        self.assertEqual(self.post(self.worker, reverse("pult:api_delete", args=[self.wf.number]), {}).status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_payload_says_who_can_delete(self):
        for user, can in ((self.gip, True), (self.worker, False)):
            self.client.force_login(user)
            row = next(t for t in self.client.get(reverse("pult:api_data")).json()["tasks"] if t["id"] == self.wf.number)
            self.assertEqual(row["canDelete"], can)


class SectionTaskSyncTests(PultTestBase):
    """Bitta bo'limga bitta vazifa: Состав'dan tushgan qoralama va «+ Задача» — bir obyekt."""

    def setUp(self):
        super().setUp()
        PlanRow.objects.create(id=7, project=self.project, wbs="1.1", code="AR", name="Архитектура", kind="Раздел", owner="Worker")

    def sync(self):
        body = {"project": "P1", "taskNew": [{"id": 999, "assignee": "Worker", "task": "AR — Архитектура", "section": 7}],
                "sec": [[7, {"task": 999}]]}
        return self.post(self.gip, reverse("pult:api_sync"), body)

    def create(self, **kw):
        body = {"task": "Фасады", "assignee": "Worker", "project": "P1", "section": 7, "flow": "Проект", **kw}
        return self.post(self.gip, reverse("pult:api_create"), body)

    def test_new_task_fills_the_draft_instead_of_duplicating(self):
        self.sync()
        draft = TaskWorkflow.objects.get(section=7)
        response = self.create(days=5)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], draft.number)
        self.assertEqual(TaskWorkflow.objects.filter(section=7).count(), 1)
        draft.refresh_from_db()
        self.assertEqual((draft.status, draft.days, draft.task.title), ("В работе", 5, "Фасады"))

    def test_sync_does_not_duplicate_task_created_in_tasks(self):
        number = self.create().json()["id"]
        self.assertEqual(PlanRow.objects.get(pk=7).task, number)  # Состав'da ham ko'rinadi
        self.sync()
        self.assertEqual(TaskWorkflow.objects.filter(section=7).count(), 1)
        self.assertEqual(PlanRow.objects.get(pk=7).task, number)

    def test_task_in_progress_is_not_duplicated(self):
        self.create(days=3)
        response = self.create()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(TaskWorkflow.objects.filter(section=7).count(), 1)

    def test_section_of_another_employee_is_refused(self):
        response = self.create(assignee="Other")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Worker", response.json()["error"])
        self.assertFalse(TaskWorkflow.objects.filter(section=7).exists())

    def test_project_task_needs_a_section(self):
        self.assertEqual(self.create(section=None).status_code, 400)

    def test_nonstandard_task_stays_out_of_composition(self):
        response = self.post(self.gip, reverse("pult:api_create"), {"task": "Купить бумагу", "assignee": "Other", "project": "", "flow": "Нестандартная"})
        self.assertEqual(response.status_code, 200)
        wf = TaskWorkflow.objects.get(number=response.json()["id"])
        self.assertEqual((wf.flow, wf.section), ("Нестандартная", None))
        self.assertIsNone(PlanRow.objects.get(pk=7).task)


class CompositionCleanupTests(PultTestBase):
    """Состав'dan o'chirilgan / ijrochisi olingan bo'lim qoralamasi «Черновик»da qolmaydi."""

    def save(self, rows):
        self.client.force_login(self.gip)
        version = self.client.get(reverse("pult:api_plan")).json()["version"]
        response = self.post(self.gip, reverse("pult:api_plan"), {"rows": rows, "version": version})
        self.assertEqual(response.status_code, 200, response.content)

    def row(self, rid, **kw):
        return {"id": rid, "project": "P1", "wbs": f"1.{rid}", "code": "AR", "name": "Архитектура", "kind": "Раздел", "owner": "Worker", **kw}

    def draft(self, section):
        body = {"project": "P1", "taskNew": [{"id": 900 + section, "assignee": "Worker", "task": "x", "section": section}]}
        self.post(self.gip, reverse("pult:api_sync"), body)
        return TaskWorkflow.objects.get(section=section)

    def test_removed_section_drops_its_draft(self):
        self.save([self.row(1), self.row(2)])
        wf = self.draft(1)
        self.save([self.row(2)])
        self.assertFalse(Task.objects.filter(pk=wf.task_id).exists())

    def test_unassigned_section_drops_its_draft(self):
        self.save([self.row(1)])
        wf = self.draft(1)
        self.save([self.row(1, owner="")])
        self.assertFalse(Task.objects.filter(pk=wf.task_id).exists())

    def test_issued_task_is_kept(self):
        self.save([self.row(1)])
        wf = self.draft(1)
        wf.status = "Новая"
        wf.save()
        self.save([])
        self.assertTrue(Task.objects.filter(pk=wf.task_id).exists())


class DisciplineSourceTests(PultTestBase):
    """Fanlar bitta manbadan (DB): «АР» (kirill) va «AR» (lotin) — bitta fan."""

    def test_cyrillic_section_code_maps_to_latin_discipline(self):
        self.assertTrue(Discipline.objects.filter(code="AR").exists())
        self.client.force_login(self.gip)
        version = self.client.get(reverse("pult:api_plan")).json()["version"]
        row = {"id": 1, "project": "P1", "wbs": "1.1", "code": "АР", "name": "Архитектура", "kind": "Раздел"}
        self.post(self.gip, reverse("pult:api_plan"), {"rows": [row], "version": version})
        self.assertEqual(PlanRow.objects.get(pk=1).code, "AR")
        self.assertFalse(Discipline.objects.filter(code="АР").exists())

    def test_users_page_rejects_cyrillic_duplicate(self):
        self.client.force_login(self.boss)
        self.client.post(reverse("accounts:discipline_create"), {"code": "АР", "name": "Архитектура"})
        self.assertFalse(Discipline.objects.filter(code="АР").exists())

    def test_latin_code_setting_links_other_spelling(self):
        from .plan import canonical_code

        cfg = Discipline.objects.get(code="KR").pult_config
        cfg.latin_code = "KJ"
        cfg.save()
        self.assertEqual(canonical_code("КЖ"), "KR")
        self.assertEqual(canonical_code("кр"), "KR")
        self.assertEqual(canonical_code("ГСН"), "ГСН")
