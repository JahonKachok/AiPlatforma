import json
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from . import finance, plan, services
from .payload import build_payload
from .services import PultError, pult_role


@login_required
def pult_page(request):
    """Platforma ichidagi sahifa: menyu + Pult iframe'da (uning CSS'i platformaga aralashmaydi)."""
    return render(request, "pult/page.html")


@xframe_options_sameorigin
@login_required
def pult_app(request):
    return render(request, "pult/app.html")


def api(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "Войдите в систему."}, status=401)
        if pult_role(request.user) is None:
            return JsonResponse({"ok": False, "error": "Нет доступа к Пульту."}, status=403)
        try:
            body = json.loads(request.body or b"{}") if request.method == "POST" else {}
        except ValueError:
            return JsonResponse({"ok": False, "error": "Неверный запрос."}, status=400)
        if not isinstance(body, dict):
            return JsonResponse({"ok": False, "error": "Неверный запрос."}, status=400)
        try:
            return JsonResponse({"ok": True, **(view(request, body, *args, **kwargs) or {})})
        except PultError as e:
            return JsonResponse({"ok": False, "error": e.message}, status=e.status)
    return wrapper


@require_GET
@api
def api_data(request, body):
    return build_payload(request.user)


@require_POST
@api
def api_create(request, body):
    _task, wf = services.create_task(request.user, body)
    return {"id": wf.number}


@require_POST
@api
def api_edit(request, body, number):
    services.edit_task(request.user, number, body)
    return {"id": number}


@require_POST
@api
def api_action(request, body, number):
    params = body.get("params") if isinstance(body.get("params"), dict) else {}
    params["expect_status"] = body.get("expect_status")
    _task, wf = services.run_action(request.user, number, str(body.get("action") or ""), params)
    return {"id": number, "status": wf.status}


def api_plan(request, *args, **kwargs):
    return _api_plan_get(request) if request.method == "GET" else _api_plan_save(request)


@require_GET
@api
def _api_plan_get(request, body):
    return plan.plan_state(request.user)


@require_POST
@api
def _api_plan_save(request, body):
    return {"changed": plan.save_plan(request.user, body.get("rows"), body.get("version"))}


@require_POST
@api
def api_sync(request, body):
    return {"counts": plan.apply_sync(request.user, body, finance.can_finance(request.user))}


@require_POST
@api
def api_plan_import(request, body):
    return {"added": plan.import_platform_objects(request.user, body.get("project"))}


@require_POST
@api
def api_discipline(request, body):
    plan.add_discipline(request.user, body)
    return {}


@require_POST
@api
def api_cipher(request, body):
    plan.save_cipher(request.user, body)
    return {}


@require_POST
@api
def api_operations(request, body):
    return {"ids": finance.create_operations(request.user, body.get("rows"))}


@require_POST
@api
def api_report(request, body):
    items = body.get("items") if isinstance(body.get("items"), list) else []
    count = services.send_report(request.user, items, str(body.get("note") or "").strip())
    return {"count": count}
