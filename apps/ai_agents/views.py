"""AI Agentlari boshqaruv paneli (admin/manager uchun)."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required

from . import services
from .models import AILog


@role_required("admin", "manager")
def ai_dashboard(request):
    """Agentlar ro'yxati va AI audit jurnali."""
    from django_celery_beat.models import PeriodicTask

    schedule = PeriodicTask.objects.filter(task="apps.ai_agents.tasks.run_deadline_agent").first()
    last_run = AILog.objects.filter(agent="deadline").first()
    logs = AILog.objects.all()[:30]

    return render(request, "ai_agents/dashboard.html", {
        "provider": services.get_provider(),
        "schedule": schedule,
        "last_run": last_run,
        "logs": logs,
    })


@role_required("admin", "manager")
@require_POST
def run_deadline_now(request):
    """Muddat agentini qo'lda ishga tushirish."""
    if not services.is_configured():
        messages.error(request, _("AI kaliti sozlanmagan (GEMINI_API_KEY yoki ANTHROPIC_API_KEY)."))
        return redirect("ai_agents:dashboard")

    from .tasks import run_deadline_agent

    result = run_deadline_agent.delay()
    outcome = result.get() if result.ready() else None
    if outcome == "skipped: nothing to report":
        messages.info(request, _("Kechikkan yoki muddati yaqin vazifalar yo'q — hisobot kerak emas."))
    else:
        messages.success(request, _("Agent ishga tushirildi. Hisobot admin va rahbarlarga yuborildi."))
    return redirect("ai_agents:dashboard")
