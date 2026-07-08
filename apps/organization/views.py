from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

from .forms import DepartmentForm, DepartmentMemberForm, OrganizationalUnitForm
from .models import Department, DepartmentMember, OrganizationalUnit

MANAGE_ROLES = (User.Role.ADMIN, User.Role.MANAGER)


def _can_manage(user):
    return user.is_superuser or user.role in MANAGE_ROLES


@login_required
def department_list(request):
    departments = Department.objects.prefetch_related("units__members__user")
    search = request.GET.get("search")
    if search:
        departments = departments.filter(name__icontains=search)
    view_mode = request.GET.get("view", "hierarchy")
    return render(request, "organization/department_list.html", {
        "departments": departments,
        "search": search or "",
        "view_mode": view_mode,
        "can_manage": _can_manage(request.user),
        "department_form": DepartmentForm(),
        "users": User.objects.filter(is_active=True),
    })


@login_required
def department_create(request):
    if not _can_manage(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Department created."))
    return redirect("organization:list")


@login_required
def department_update(request, pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, _("Department updated."))
            return redirect("organization:list")
    else:
        form = DepartmentForm(instance=department)
    return render(request, "organization/department_form.html", {"form": form, "department": department})


@login_required
def department_delete(request, pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.delete()
        messages.success(request, _("Department deleted."))
    return redirect("organization:list")


@login_required
def unit_create(request, department_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    department = get_object_or_404(Department, pk=department_pk)
    if request.method == "POST":
        form = OrganizationalUnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.department = department
            unit.save()
            messages.success(request, _("Unit added."))
    return redirect("organization:list")


@login_required
def unit_delete(request, pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    unit = get_object_or_404(OrganizationalUnit, pk=pk)
    if request.method == "POST":
        unit.delete()
        messages.success(request, _("Unit deleted."))
    return redirect("organization:list")


@login_required
def member_add(request, unit_pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    unit = get_object_or_404(OrganizationalUnit, pk=unit_pk)
    if request.method == "POST":
        form = DepartmentMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.unit = unit
            member.save()
            messages.success(request, _("Member added."))
    return redirect("organization:list")


@login_required
def member_remove(request, pk):
    if not _can_manage(request.user):
        raise PermissionDenied
    member = get_object_or_404(DepartmentMember, pk=pk)
    if request.method == "POST":
        member.delete()
        messages.success(request, _("Member removed."))
    return redirect("organization:list")
