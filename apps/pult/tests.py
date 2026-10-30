import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Discipline, User
from apps.finance.models import EmployeeContract, FinancialRecord
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskComment

from .models import Contract, OperationInfo, PlanRow, ProgressReport, PultSettings, TaskWorkflow
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