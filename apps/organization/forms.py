from django import forms

from apps.core.forms import StyledFormMixin

from .models import Department, DepartmentMember, OrganizationalUnit


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class OrganizationalUnitForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OrganizationalUnit
        fields = ["name", "code", "description", "manager", "level", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class DepartmentMemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DepartmentMember
        fields = ["user", "role_in_unit", "manager", "is_primary"]
