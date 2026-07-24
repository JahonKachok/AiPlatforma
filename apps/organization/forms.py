from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Department, DepartmentMember, OrganizationalUnit


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Bo'lim nomi (masalan: Qurilish bo'limi)"}),
            "code": forms.TextInput(attrs={"placeholder": "Kodi (masalan: QUR-01)"}),
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Tavsif (ixtiyoriy)"}),
        }
        help_texts = {
            "name": _("The department's name — shown under this name in lists."),
            "code": _("A unique short code for the department; it must not repeat across other departments."),
            "description": _("A short description of the department (optional)."),
            "head": _("The manager responsible for this department (optional)."),
            "status": _("The department's current status: Active, Inactive, or Archived."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["head"].empty_label = "Rahbar (ixtiyoriy)"


class OrganizationalUnitForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OrganizationalUnit
        fields = ["name", "code", "description", "manager", "level", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "name": _("The unit's name."),
            "code": _("A short code for the unit (optional)."),
            "description": _("A short description of the unit (optional)."),
            "manager": _("The manager responsible for this unit (optional)."),
            "level": _("The unit's hierarchical level (a number)."),
            "status": _("The unit's current status."),
        }


class DepartmentMemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DepartmentMember
        fields = ["user", "role_in_unit", "manager", "is_primary"]
        help_texts = {
            "user": _("The employee being added to the unit."),
            "role_in_unit": _("The employee's position/role in this unit (free text)."),
            "manager": _("The employee's direct manager (optional)."),
            "is_primary": _("If checked, this is considered the employee's primary unit."),
        }
