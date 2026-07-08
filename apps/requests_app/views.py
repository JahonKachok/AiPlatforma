from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.notifications.services import notify_user

from .forms import RequestCommentForm, RequestForm
from .models import Request, RequestStatus


def _visible_requests(user):
    return Request.objects.filter(
        Q(created_by=user) | Q(assignee=user) | Q(project__members__user=user)
    ).distinct().select_related("project", "created_by", "assignee")


@login_required
def request_list(request):
    requests_qs = _visible_requests(request.user)
    status = request.GET.get("status")
    if status:
        requests_qs = requests_qs.filter(status=status)

    counts = {value: _visible_requests(request.user).filter(status=value).count() for value, _l in RequestStatus.choices}

    return render(request, "requests_app/request_list.html", {
        "requests": requests_qs,
        "status": status or "",
        "statuses": RequestStatus.choices,
        "counts": counts,
    })


@login_required
def request_create(request):
    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.created_by = request.user
            req.save()
            if req.assignee and req.assignee_id != request.user.id:
                notify_user(
                    req.assignee, "system", _("New request assigned"),
                    _('You were assigned to "%(title)s".') % {"title": req.title},
                    link=f"/requests/{req.pk}/",
                )
            messages.success(request, _("Request created."))
            return redirect("requests_app:detail", pk=req.pk)
    else:
        form = RequestForm()
    return render(request, "requests_app/request_form.html", {"form": form, "is_create": True})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(_visible_requests(request.user), pk=pk)
    if request.method == "POST":
        comment_form = RequestCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.request = req
            comment.user = request.user
            comment.save()
            notify_target = req.assignee if req.assignee_id != request.user.id else req.created_by
            if notify_target and notify_target.id != request.user.id:
                notify_user(
                    notify_target, "comment", _("New comment"),
                    _('%(user)s commented on "%(title)s".') % {"user": request.user.get_short_name(), "title": req.title},
                    link=f"/requests/{req.pk}/",
                )
            return redirect("requests_app:detail", pk=pk)
    else:
        comment_form = RequestCommentForm()
    return render(request, "requests_app/request_detail.html", {"request_obj": req, "comment_form": comment_form})


@login_required
def request_update(request, pk):
    req = get_object_or_404(_visible_requests(request.user), pk=pk)
    if request.method == "POST":
        form = RequestForm(request.POST, instance=req)
        if form.is_valid():
            form.save()
            messages.success(request, _("Request updated."))
            return redirect("requests_app:detail", pk=pk)
    else:
        form = RequestForm(instance=req)
    return render(request, "requests_app/request_form.html", {"form": form, "request_obj": req, "is_create": False})


@login_required
def request_delete(request, pk):
    req = get_object_or_404(_visible_requests(request.user), pk=pk)
    if request.method == "POST":
        req.delete()
        messages.success(request, _("Request deleted."))
        return redirect("requests_app:list")
    return render(request, "requests_app/request_confirm_delete.html", {"request_obj": req})
