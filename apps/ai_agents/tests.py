from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.finance.models import AdministrativeExpense, FinanceCategory, FinancialRecord
from apps.notifications.models import Notification
from apps.projects.models import Project

from . import orchestrator
from .models import AgentMemory, PendingAction

ASK = "apps.ai_agents.orchestrator.ask_json"


def finance(**over):
    data = {
        "scope": "project", "direction": "out", "amount": 50, "currency": "USD", "project": "Zavod",
        "counterparty": "o'tkazgich", "project_category": "Оплата исполнителю", "office_category": "other",
        "method": "cash", "date": "", "period": "once", "note": "avans",
    }
    data.update(over)
    return data


class RouteTests(TestCase):
    def test_keyword_routing_needs_no_llm(self):
        cases = {
            "Bugun o'tkazgichga 50 dollar o'tkazib yubordim": "treasurer",
            "Перевёл подрядчику 2 млн сум по проекту Завод": "treasurer",
            "Ofis ijarasi uchun 5 mln so'm to'ladim": "quartermaster",
            "Зарплата Алишеру 800$": "quartermaster",
            "Aliga Zavodning AR razdellarini zip qilib tashla": "archivist",
            "Mening KPI ballarim qancha?": "kpi",
            "Eslab qol: matn ustma-ust tushmasin": "memory",
            "Переведи чертеж на китайский": "translator",
            "Переведи чертеж 25 на китайский": "translator",
            "Оплати Иванову пять миллионов по Кислороду": "treasurer",
            "Ofis ijarasi uchun besh million so‘m berdim": "quartermaster",
            "Salom, bugun nima ishlar bor?": None,
            "45-maktab loyihasi qachon tugaydi?": None,  # raqam bor, pul yo'q
        }
        for text, agent in cases.items():
            self.assertEqual(orchestrator.route(text), agent, text)


class MonitorTests(TestCase):
    @override_settings(AI_OFFICE_API_KEY="unit-test-key", AI_OFFICE_MODEL="test-model")
    def test_office_provider_stays_server_side_and_does_not_invent_a_price(self):
        from django.urls import reverse
        from .models import OfficeLead, OfficeResult, OfficeTask

        manager = User.objects.create_user(email="ai-office@example.test", role=User.Role.MANAGER)
        self.client.force_login(manager)
        lead = OfficeLead.objects.create(employee_id="sales", brief="Aziza ingliz tili kursining narxini so‘radi")
        task = OfficeTask.objects.create(employee_id="sales", lead=lead, brief="Javob tayyorla")
        url = reverse("ai_agents:office_action", args=["generate"])
        with mock.patch("google.genai.Client") as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.side_effect = [TimeoutError(), SimpleNamespace(text="Kurs 500 000 so‘m.")]
            self.assertEqual(self.client.post(url, {"id": task.pk}).json()["office"]["tasks"][0]["status"], "error")
            response = self.client.post(url, {"id": task.pk})
            self.assertFalse(response.json()["office"]["demo"])
            self.assertNotContains(response, "unit-test-key")
            self.assertEqual(generate.call_args.kwargs["model"], "test-model")
        self.assertIn("aniqlashtirib", OfficeResult.objects.get(task=task).body)

    @override_settings(AI_OFFICE_API_KEY="")
    def test_virtual_office_failure_retry_and_edited_result(self):
        from django.urls import reverse
        from .models import OfficeLead, OfficeResult, OfficeTask

        manager = User.objects.create_user(email="team@example.test", role=User.Role.MANAGER)
        self.client.force_login(manager)

        def post(action, **values):
            return self.client.post(reverse("ai_agents:office_action", args=[action]), values)

        lead_id = post("lead-add", employee="sales", brief="Aziza Telegram orqali ingliz tili kursining narxini so‘radi").json()["created"]
        task_id = post("task-add", employee="sales", brief="Javob yozing", lead=lead_id).json()["created"]
        with mock.patch("apps.ai_agents.virtual_office.generate_text", side_effect=TimeoutError):
            post("generate", id=task_id)
        self.assertEqual(OfficeTask.objects.get(pk=task_id).status, "error")
        self.assertFalse(OfficeResult.objects.exists())
        post("generate", id=task_id)
        result = OfficeResult.objects.get(task_id=task_id)
        self.assertIn("Aziza", result.body)
        self.assertNotRegex(result.body, r"\d")
        timestamp = result.updated_at.isoformat()
        self.assertEqual(post("result-edit", id=task_id, updated=timestamp, body="Tahrirlangan javob").status_code, 200)
        self.assertEqual(post("result-edit", id=task_id, updated=timestamp, body="Eski nusxa").status_code, 409)
        post("generate", id=task_id)
        post("lead-status", id=lead_id, status="contacted")
        self.assertEqual(OfficeResult.objects.get(task_id=task_id).body, "Tahrirlangan javob")
        self.assertEqual(OfficeLead.objects.get(pk=lead_id).status, "contacted")
        manager.role = User.Role.DESIGNER
        manager.save(update_fields=["role"])
        self.assertEqual(post("lead-add", employee="sales", brief="Test").status_code, 403)

    def test_office_status_groups_activity_and_restricts_access(self):
        from datetime import timedelta
        from django.urls import reverse
        from django.utils import timezone
        from .models import AILog

        manager = User.objects.create_user(email="office@example.com", role=User.Role.MANAGER)
        self.client.force_login(manager)
        AILog.objects.create(agent="worker:translator", status="success")
        AILog.objects.create(agent="translator", status="success")
        PendingAction.objects.create(user=manager, kind="office_expense")
        expired = PendingAction.objects.create(user=manager, kind="project_operation")
        PendingAction.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(days=2))
        status_url = reverse("ai_agents:office_status")
        stations = {s["key"]: s for s in self.client.get(status_url).json()["stations"]}
        self.assertEqual(len(stations), 10)
        self.assertEqual(stations["translator"]["calls"], 2)
        self.assertEqual(stations["quartermaster"]["state"], "waiting")
        self.assertEqual(stations["treasurer"]["pending"], 0)
        self.assertEqual(stations["gost"]["state"], "offline")
        page_url = reverse("ai_agents:office")
        self.assertContains(self.client.get(page_url), 'data-roster=', count=10)
        self.assertContains(self.client.get(page_url, {"team": "office"}), 'id="board-dialog"')
        manager.role = User.Role.DESIGNER
        manager.save(update_fields=["role"])
        for url in (status_url, page_url):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_activity_keeps_history_and_excludes_expired_confirmations(self):
        from datetime import timedelta

        from django.urls import reverse
        from django.utils import timezone

        from .models import AILog

        manager = User.objects.create_user(email="monitor@example.com", role=User.Role.MANAGER)
        self.client.force_login(manager)
        url = reverse("ai_agents:dashboard")
        AILog.objects.create(agent="worker:translator", status="success")
        old = AILog.objects.create(agent="translator", status="error")
        AILog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=8))
        AILog.objects.create(agent="secretary", status="empty")
        expired = PendingAction.objects.create(user=manager, kind="project_operation")
        PendingAction.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(days=2))
        PendingAction.objects.create(user=manager, kind="office_expense")
        PendingAction.objects.create(user=manager, kind="office_expense", done_at=timezone.now())

        response = self.client.get(url, {"feed": "calls", "agent": "translator"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["week_total"], 2)
        self.assertEqual(len(response.context["days"]), 7)
        self.assertEqual(response.context["events"].paginator.count, 2)
        response = self.client.get(url, {"feed": "pending"})
        self.assertEqual(response.context["pending_count"], 1)
        self.assertEqual(response.context["events"].paginator.count, 1)
        self.assertEqual(response.context["events"][0].kind, "office_expense")
        manager.role = User.Role.DESIGNER
        manager.save(update_fields=["role"])
        self.assertEqual(self.client.get(url).status_code, 403)


class FinanceAgentTests(TestCase):
    def setUp(self):
        self.boss = User.objects.create_user(email="b@example.com", password="x", full_name="Boss", role=User.Role.MANAGER)
        self.designer = User.objects.create_user(email="d@example.com", password="x", full_name="Des", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="Zavod", created_by=self.boss)

    def test_treasurer_asks_confirmation_then_writes_operation(self):
        with mock.patch(ASK, return_value=finance()) as ask:
            reply = orchestrator.handle(self.boss, "Bugun o'tkazgichga 50 dollar naqd berdim, Zavod", "uz")
        self.assertIn("Zavod", ask.call_args.args[1])  # loyihalar ro'yxati kontekstda
        self.assertFalse(FinancialRecord.objects.exists())  # tasdiqsiz yozilmaydi
        data = reply.buttons[0][0][1]
        self.assertTrue(data.startswith("ag:ok:"))
        done = orchestrator.confirm(self.boss, data, "uz")
        record = FinancialRecord.objects.get()
        self.assertEqual((record.type, record.amount, record.currency, record.account), ("expense", 50, "USD", "usd_cash"))
        self.assertEqual(record.pult_info.counterparty, "o'tkazgich")
        self.assertIn("-50 USD", done.text)  # loyiha balansi
        self.assertEqual(orchestrator.confirm(self.boss, data, "uz").text, orchestrator.t("pd.expired", "uz"))  # ikki marta emas

    def test_quartermaster_writes_office_expense(self):
        data = finance(scope="office", office_category="salary", amount=8000000, currency="UZS",
                       counterparty="Alisher", period="once", project="")
        with mock.patch(ASK, return_value=data):
            reply = orchestrator.handle(self.boss, "Alisherga oylik 8 mln so'm berdim", "ru")
        self.assertIn("Завхоз", reply.text)
        orchestrator.confirm(self.boss, reply.buttons[0][0][1], "ru")
        expense = AdministrativeExpense.objects.get()
        self.assertEqual((expense.category, expense.amount, expense.period), ("Зарплата", 8000000, "once"))
        from .zavxoz import upcoming
        self.assertFalse(upcoming())
        self.assertTrue(FinanceCategory.objects.filter(name="Зарплата", type="admin").exists())

    def test_cancel_and_foreign_user(self):
        with mock.patch(ASK, return_value=finance()):
            reply = orchestrator.handle(self.boss, "50 dollar to'ladim Zavod", "uz")
        ok, no = reply.buttons[0][0][1], reply.buttons[0][1][1]
        self.assertEqual(orchestrator.confirm(self.designer, ok, "uz").text, orchestrator.t("pd.expired", "uz"))
        orchestrator.confirm(self.boss, no, "uz")
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertIsNotNone(PendingAction.objects.get().done_at)

    def test_only_finance_roles_and_no_tokens_spent_otherwise(self):
        with mock.patch(ASK) as ask:
            reply = orchestrator.handle(self.designer, "50 dollar to'ladim", "uz")
        ask.assert_not_called()
        self.assertIn("faqat rahbar", reply.text)

    def test_unknown_project_is_asked_back(self):
        with mock.patch(ASK, return_value=finance(project="Yo'q loyiha")):
            reply = orchestrator.handle(self.boss, "50 dollar to'ladim", "uz")
        self.assertFalse(reply.buttons)
        self.assertIn("Yo'q loyiha", reply.text)

    def test_not_money_falls_back_to_chat(self):
        with mock.patch(ASK, return_value=finance(scope="none")):
            self.assertIsNone(orchestrator.handle(self.boss, "2 ta so'm haqida savol", "uz"))

    def test_memory_rules_go_into_the_agent_prompt(self):
        reply = orchestrator.handle(self.boss, "Eslab qol: dollar to'lovlarini doim naqd deb yoz", "uz")
        self.assertIn("🧠", reply.text)
        self.assertEqual(AgentMemory.objects.get().agent, "treasurer")
        with mock.patch(ASK, return_value=finance()) as ask:
            orchestrator.handle(self.boss, "100 dollar to'ladim Zavod", "uz")
        self.assertIn("doim naqd", ask.call_args.args[0])


class ZavxozReminderTests(TestCase):
    def test_rent_reminder_three_days_before_once(self):
        from .zavxoz import send_payment_reminders

        boss = User.objects.create_user(email="b@example.com", password="x", full_name="Boss", role=User.Role.MANAGER)
        from .zavxoz import _add_period

        today = timezone.localdate()
        # Oxirgi to'lov shunday tanlanadiki, keyingisi aynan 3 kundan keyin bo'lsin.
        last = next(today - timedelta(days=back) for back in range(25, 40)
                    if (_add_period(today - timedelta(days=back), "month") - today).days == 3)
        AdministrativeExpense.objects.create(category="rent", amount=5000000, currency="UZS", period="month",
                                             date=last, created_by=boss)
        self.assertEqual(send_payment_reminders(today), 1)
        self.assertEqual(send_payment_reminders(today), 0)
        self.assertTrue(Notification.objects.filter(user=boss, title="Завхоз: оплата «Аренда»").exists())


@override_settings(ANTHROPIC_API_KEY="k", GEMINI_API_KEY="", AI_PROVIDER="", AI_MODEL="claude-opus-5-5")
class AskJsonTests(TestCase):
    def test_claude_structured_output_with_fallback(self):
        from . import services

        message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text='{"agent": "kpi"}')])
        client = mock.MagicMock()
        client.beta.messages.create.return_value = message
        with mock.patch.object(services, "_get_anthropic_client", return_value=client):
            data = services.ask_json("sys", "hi", {"type": "object"}, agent="orchestrator")
        self.assertEqual(data, {"agent": "kpi"})
        kwargs = client.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(kwargs["output_config"]["effort"], "low")
        self.assertEqual(kwargs["fallbacks"], "default")
        self.assertEqual(kwargs["model"], "claude-opus-5-5")

    def test_refusal_and_errors_return_none(self):
        from . import services

        client = mock.MagicMock()
        client.beta.messages.create.return_value = SimpleNamespace(stop_reason="refusal", content=[])
        with mock.patch.object(services, "_get_anthropic_client", return_value=client):
            self.assertIsNone(services.ask_json("s", "p", {}, agent="x"))
        client.beta.messages.create.side_effect = RuntimeError("boom")
        with mock.patch.object(services, "_get_anthropic_client", return_value=client):
            self.assertIsNone(services.ask_json("s", "p", {}, agent="x"))

    def test_other_models_get_no_fallback_param(self):
        from . import services

        client = mock.MagicMock()
        client.messages.create.return_value = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")])
        with self.settings(AI_MODEL="claude-haiku-5-5"), mock.patch.object(services, "_get_anthropic_client", return_value=client):
            services.ask_json("s", "p", {}, agent="x")
        self.assertNotIn("fallbacks", client.messages.create.call_args.kwargs)
