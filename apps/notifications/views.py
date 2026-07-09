from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    qs = request.user.notifications.all()
    total = qs.count()
    unread = qs.filter(is_read=False).count()
    stat_cards = [
        {"label": _("Total"), "value": total},
        {"label": _("Unread"), "value": unread,
         "color": "text-blue-600 dark:text-blue-400"},
        {"label": _("Read"), "value": total - unread,
         "color": "text-green-600 dark:text-green-400"},
        {"label": _("Last 7 days"), "value": qs.filter(
            created_at__gte=timezone.now() - timedelta(days=7)).count(),
         "color": "text-amber-600 dark:text-amber-400"},
    ]
    return render(request, "notifications/notification_list.html", {
        "notifications": qs[:100],
        "stat_cards": stat_cards,
    })


@login_required
def unread_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})


@login_required
def recent_partial(request):
    notifications = request.user.notifications.all()[:8]
    return render(request, "notifications/_recent.html", {"notifications": notifications})


@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("notifications:list")


@login_required
@require_POST
def delete_notification(request, pk):
    get_object_or_404(Notification, pk=pk, user=request.user).delete()
    return redirect("notifications:list")
