from apps.accounts.models import User

FINANCE_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.FINANCE}


def can_manage_finance(user):
    """Moliyaviy ma'lumotlar (hisob qoldiqlari, pul oqimi, hamkasblarning
    maoshlari) faqat moliya rollariga ochiq. Ilgari loyihaga a'zo har kim —
    mijoz roli ham — ularni ko'rib, Excel'ga eksport qila olardi."""
    return user.is_superuser or user.role in FINANCE_ROLES
