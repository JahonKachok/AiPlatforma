"""AI Agentlari boshqaruv paneli (admin/manager uchun)."""
from django.contrib import messages
from django import forms
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import override
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required

from . import services
from .models import AILog, OfficeEmployee, OfficeLead, OfficeResult, OfficeTask
from .monitoring import monitor_context, office_stations
from . import virtual_office


@role_required("admin", "manager")
def office(request):
    with override("uz"):
        agents = request.GET.get("team") != "office"
        return render(request, "ai_agents/office.html", {
            "agent_floor": agents, "office": office_stations() if agents else virtual_office.workspace(),
        })


class BriefForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=OfficeEmployee.objects.all())
    brief = forms.CharField(max_length=3000)


class LeadForm(BriefForm):
    price = forms.IntegerField(required=False, min_value=0, max_value=999999999999)


class TaskForm(BriefForm):
    lead = forms.ModelChoiceField(queryset=OfficeLead.objects.all(), required=False)


@role_required("admin", "manager")
def office_data(request):
    response = JsonResponse(virtual_office.workspace())
    response["Cache-Control"] = "private, no-store"
    return response


@role_required("admin", "manager")
@require_POST
def office_action(request, action):
    data = request.POST
    pk = data.get("id", "")
    if action not in ("lead-add", "task-add") and not (pk.isascii() and pk.isdigit() and len(pk) <= 18):
        return JsonResponse({"error": "Yozuv raqami noto‘g‘ri."}, status=400)
    created = None
    if action in ("lead-add", "task-add"):
        form = LeadForm(data) if action == "lead-add" else TaskForm(data)
        if not form.is_valid():
            return JsonResponse({"error": "Mas’ul, matn va kiritilgan qiymatlarni tekshiring."}, status=400)
        if action == "lead-add":
            created = OfficeLead.objects.create(**form.cleaned_data).pk
        else:
            created = OfficeTask.objects.create(**form.cleaned_data, status="working").pk
    elif action == "generate":
        task = get_object_or_404(OfficeTask, pk=pk)
        virtual_office.run_task(task.pk)
    elif action == "lead-status":
        if data.get("status") not in OfficeLead.Status.values:
            return JsonResponse({"error": "Lid holati noto‘g‘ri."}, status=400)
        lead = get_object_or_404(OfficeLead, pk=pk)
        lead.status = data["status"]
        lead.save(update_fields=["status"])
    elif action == "task-status":
        if data.get("status") not in ("new", "working", "ready"):
            return JsonResponse({"error": "Vazifa holati noto‘g‘ri."}, status=400)
        editable = OfficeTask.objects.filter(pk=pk).filter(
            Q(run_token__isnull=True) | Q(started_at__lt=timezone.now() - virtual_office.LEASE))
        if not editable.update(status=data["status"], run_token=None):
            return JsonResponse({"error": "Vazifa band. Doskani yangilang."}, status=409)
    elif action == "result-edit":
        body = data.get("body", "").strip()
        if not body or len(body) > 16000:
            return JsonResponse({"error": "Natija 1–16 000 belgidan iborat bo‘lsin."}, status=400)
        result = get_object_or_404(OfficeResult, task_id=pk)
        if (result.updated_at.isoformat() != data.get("updated") or
                not OfficeResult.objects.filter(pk=result.pk, updated_at=result.updated_at)
                .update(body=body, updated_at=timezone.now())):
            return JsonResponse({"error": "Natija boshqa oynada o‘zgargan. Nusxangizni olib, sahifani yangilang."}, status=409)
    else:
        return JsonResponse({"error": "Amal topilmadi."}, status=404)
    return JsonResponse({"office": virtual_office.workspace(), "created": created})


@role_required("admin", "manager")
def office_status(request):
    with override("uz"):
        response = JsonResponse(office_stations())
    response["Cache-Control"] = "private, no-store"
    return response


@role_required("admin", "manager")
def ai_dashboard(request):
    """Agentlar ro'yxati va AI audit jurnali."""
    from django_celery_beat.models import PeriodicTask

    schedule = PeriodicTask.objects.filter(task="apps.ai_agents.tasks.run_deadline_agent").first()
    last_run = AILog.objects.filter(agent="deadline").first()

    return render(request, "ai_agents/dashboard.html", {
        "provider": services.get_provider(),
        "schedule": schedule,
        "last_run": last_run,
        **monitor_context(request.GET),
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
