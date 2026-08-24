from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

from .models import Account, EmployeeContract, FinanceSettings, FinancialRecord


class FinanceRecordPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN)
        self.designer = User.objects.create_user(email="designer@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P1", created_by=self.admin)
        ProjectMember.objects.create(project=self.project, user=self.designer, can_edit=False)

    def test_non_editing_member_cannot_add_record(self):
        self.client.force_login(self.designer)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "income", "amount": 100, "date": "2026-01-01", "status": "pending",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FinancialRecord.objects.count(), 0)

    def test_admin_can_add_record(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "income", "amount": 100, "currency": "UZS", "date": "2026-01-01", "status": "pending",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinancialRecord.objects.count(), 1)

    def test_add_income_button_creates_an_income_record(self):
        # The project finance tab's "+ Добавить доход" button submits the shared
        # record form with a button-supplied type=income instead of a visible dropdown.
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "income", "amount": 250, "currency": "UZS", "date": "2026-01-01", "status": "confirmed",
        })
        self.assertEqual(response.status_code, 302)
        record = FinancialRecord.objects.get()
        self.assertEqual(record.type, "income")

    def test_add_expense_button_creates_an_expense_record(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "expense", "amount": 150, "currency": "UZS", "date": "2026-01-01", "status": "confirmed",
        })
        self.assertEqual(response.status_code, 302)
        record = FinancialRecord.objects.get()
        self.assertEqual(record.type, "expense")


class EmployeeContractPayTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin2@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN)
        self.employee = User.objects.create_user(email="employee@example.com", password="pw12345!", full_name="Employee", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P2", created_by=self.admin)
        self.contract = EmployeeContract.objects.create(user=self.employee, project=self.project, amount=1000)

    def test_paying_salary_reduces_balance_and_logs_a_transaction(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": self.contract.pk, "amount": 400, "account": Account.UZS_BANK,
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.paid, 400)
        self.assertEqual(self.contract.balance, 600)
        self.assertEqual(FinancialRecord.objects.filter(project=self.project).count(), 1)

    def test_cannot_pay_more_than_the_remaining_balance(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": self.contract.pk, "amount": 5000, "account": Account.UZS_BANK,
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.paid, 0)
        self.assertEqual(FinancialRecord.objects.filter(project=self.project).count(), 0)

    def test_usd_payment_is_converted_into_the_contract_currency(self):
        """A USD payout must move a UZS balance by the converted amount, not by
        the raw figure typed in."""
        settings_obj = FinanceSettings.get_solo()
        settings_obj.usd_rate = 12700
        settings_obj.save()
        contract = EmployeeContract.objects.create(
            user=self.employee, project=self.project, amount=25_000_000, currency="UZS",
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": contract.pk, "amount": 1000,
            "payment_currency": "USD", "account": Account.USD_CASH,
        })
        contract.refresh_from_db()
        self.assertEqual(contract.paid, 12_700_000)
        self.assertEqual(contract.balance, 12_300_000)

        record = FinancialRecord.objects.filter(project=self.project).latest("created_at")
        self.assertEqual(record.amount, 1000)          # stored as entered
        self.assertEqual(record.currency, "USD")
        self.assertEqual(record.exchange_rate, 12700)  # rate kept for audit

    def test_usd_overpayment_is_refused_after_conversion(self):
        settings_obj = FinanceSettings.get_solo()
        settings_obj.usd_rate = 12700
        settings_obj.save()
        contract = EmployeeContract.objects.create(
            user=self.employee, project=self.project, amount=25_000_000, currency="UZS",
        )
        self.client.force_login(self.admin)
        # 3000 USD = 38 100 000 UZS, over the 25 000 000 balance.
        self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": contract.pk, "amount": 3000,
            "payment_currency": "USD", "account": Account.USD_CASH,
        })
        contract.refresh_from_db()
        self.assertEqual(contract.paid, 0)

    def test_currency_must_match_the_account(self):
        contract = EmployeeContract.objects.create(
            user=self.employee, project=self.project, amount=25_000_000, currency="UZS",
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": contract.pk, "amount": 100,
            "payment_currency": "USD", "account": Account.UZS_BANK,
        })
        contract.refresh_from_db()
        self.assertEqual(contract.paid, 0)

    def test_uzs_payment_stores_no_exchange_rate(self):
        """Same-currency payouts stay exactly as they were before the picker."""
        self.client.force_login(self.admin)
        self.client.post(reverse("finance:pay_employee_contract"), {
            "employee_contract": self.contract.pk, "amount": 400,
            "payment_currency": "UZS", "account": Account.UZS_BANK,
        })
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.paid, 400)
        record = FinancialRecord.objects.filter(project=self.project).latest("created_at")
        self.assertIsNone(record.exchange_rate)


class ExchangeRateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin3@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN)
        self.designer = User.objects.create_user(email="designer3@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER)

    @patch("apps.finance.views.fetch_usd_rate", return_value=12345.67)
    def test_admin_can_refresh_rate_from_cbu(self, mock_fetch):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:update_rate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinanceSettings.get_solo().usd_rate, 12345.67)

    @patch("apps.finance.views.fetch_usd_rate", return_value=None)
    def test_rate_unchanged_when_cbu_is_unreachable(self, mock_fetch):
        FinanceSettings.objects.create(pk=1, usd_rate=11111)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:update_rate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinanceSettings.get_solo().usd_rate, 11111)

    def test_non_finance_role_cannot_refresh_rate(self):
        self.client.force_login(self.designer)
        response = self.client.post(reverse("finance:update_rate"))
        self.assertEqual(response.status_code, 403)

    @patch("apps.finance.views.fetch_usd_rate_poytaxtbank", return_value=12345.67)
    def test_admin_can_refresh_rate_from_poytaxtbank(self, mock_fetch):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:update_rate_poytaxtbank"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinanceSettings.get_solo().usd_rate, 12345.67)

    @patch("apps.finance.views.fetch_usd_rate_poytaxtbank", return_value=None)
    def test_rate_unchanged_when_poytaxtbank_is_unreachable(self, mock_fetch):
        FinanceSettings.objects.create(pk=1, usd_rate=11111)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:update_rate_poytaxtbank"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinanceSettings.get_solo().usd_rate, 11111)

    def test_non_finance_role_cannot_refresh_rate_from_poytaxtbank(self):
        self.client.force_login(self.designer)
        response = self.client.post(reverse("finance:update_rate_poytaxtbank"))
        self.assertEqual(response.status_code, 403)
