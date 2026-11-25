"""Pult bo'limlari alohida menyu emas: har biri platformaning o'ziga mos
bo'limida (Vazifalar, Loyihalar, Moliya, ...) tab sifatida ochiladi.

Bu yerda qaysi Pult sahifasi qaysi menyuga tegishli, uning URL'i va qaysi
rollar uni ko'rishi yozilgan. Ruxsatlar ro'yxati brauzerga ham `viewer.pages`
orqali boradi (payload.py), shuning uchun pult.js va menyu bir xil qoidaga
tayanadi.
"""
from django.utils.translation import gettext_lazy as _

from .finance import can_finance
from .services import ACCOUNTANT, ADMIN_DEPT, BOSS, GIP, HR, pult_role

# section -> (menyu guruhi, URL yo'li, tab nomi). Tartib — tablar tartibi.
SECTIONS = {
    "work": ("tasks", "tasks/my-work/", _("My work")),
    "tasks": ("tasks", "tasks/register/", _("Task register")),
    "req": ("inquiries", "inquiries/", _("Inquiries")),
    "comp": ("projects", "projects/composition/", _("Project composition")),
    "plan": ("projects", "projects/schedule/", _("Project schedule")),
    "money": ("finance", "finance/operations/", _("Operations")),
    "contracts": ("finance", "finance/contracts/", _("Contracts")),
    "team": ("users", "accounts/users/workload/", _("Workload")),
    "kpi": ("users", "accounts/users/kpi/", _("KPI")),
    "home": ("reports", "reports/summary/", _("Operational summary")),
}

# Guruhning platformadagi asosiy sahifasi (tablar qatorida birinchi turadi).
# «inquiries» guruhida asosiy sahifa yo'q: menyu to'g'ridan-to'g'ri Pult sahifasini ochadi.
GROUP_HOME = {
    "tasks": ("tasks:board", _("Tasks")),
    "projects": ("projects:list", _("Projects")),
    "finance": ("finance:home", _("Finance")),
    "users": ("accounts:user_list", _("Users")),
    "reports": ("reports:dashboard", _("Reports")),
}

# Asosiy sahifaning ichki tablari (bir sahifada, #hash bilan ochiladi). Pult
# sahifalarida ham tablar qatori bir xil bo'lishi uchun shu yerdan chiziladi.
GROUP_EXTRA_TABS = {
    "users": [("tab-disciplines", _("Disciplines"))],
}

# «kanban» — tab emas: «Задачи» doskasining «Проектные» rejimi (urls.py yo'naltiradi).
ALL_PAGES = ["work", "home", "req", "kanban", "tasks", "comp", "plan", "team", "kpi", "money", "contracts"]
ROLE_PAGES = {
    BOSS: ALL_PAGES,
    GIP: ["work", "kanban", "tasks", "comp", "plan", "team", "kpi"],
    ACCOUNTANT: ["work", "kanban", "money", "contracts", "kpi"],
    HR: ["work", "kanban", "kpi"],
    ADMIN_DEPT: ["work", "kanban", "kpi"],
}
SPEC_PAGES = ["work", "kanban", "plan", "kpi"]
FINANCE_PAGES = ("money", "contracts")


def allowed_pages(user):
    """Foydalanuvchi ko'ra oladigan Pult sahifalari (mijoz — hech biri)."""
    role = pult_role(user)
    if role is None:
        return []
    pages = ROLE_PAGES.get(role, SPEC_PAGES)
    if not can_finance(user):
        pages = [p for p in pages if p not in FINANCE_PAGES]
    return list(pages)


def section_url_name(section):
    return f"section_{section}"
