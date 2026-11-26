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
            "Salom, bugun nima ishlar bor?": None,
            "45-maktab loyihasi qachon tugaydi?": None,  # raqam bor, pul yo'q
        }
        for text, agent in cases.items():
            self.assertEqual(orchestrator.route(text), agent, text)


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
        self.assertEqual((expense.category, expense.amount, expense.period), ("Зарплата", 8000000, "month"))
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
        self.assertIn("buxgalter", reply.text)

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
