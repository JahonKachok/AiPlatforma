"""Состав и календарный график проекта (avval «Состав проекта» varag'i).

Sroklar, bog'lanishlar va kritik yo'l brauzerda hisoblanadi (pult.js:
schedule); server qatorlarni saqlaydi, kim qaysi loyihani o'zgartira olishini
tekshiradi va bir vaqtda ikki kishi yozib yubormasligini kuzatadi.
"""
from datetime import date

from django.db import transaction
from django.db.models import Max

from apps.accounts.models import Discipline
from apps.projects.models import Project
from apps.projects.permissions import ensure_project_member, visible_projects_for
from apps.tasks.models import Task

from .models import CipherRule, Contract, DisciplineConfig, Flow, PlanRow, PultSettings, StageConfig
from .models import WorkflowStatus as WS
from .services import (
    BOSS, GIP, PultError, ensure_workflow, get_task, log_status, pult_role, resolve_person, save_workflow,
)

# JSON kaliti (pult.js PF) -> model maydoni
FIELDS = {
    "wbs": "wbs", "code": "code", "name": "name", "kind": "kind", "owner": "owner", "dur": "dur", "preds": "preds",
    "snet": "snet", "as": "actual_start", "af": "actual_finish", "pct": "pct", "cs": "calc_start",
    "cf": "calc_finish", "bs": "base_start", "bf": "base_finish", "client": "client", "comment": "comment",
    "inPlan": "in_plan", "doc": "doc", "pay": "pay", "price": "price", "cur": "cur", "contract": "contract",
    "task": "task", "closed": "closed",
}
DATES = {"snet", "as", "af", "cs", "cf", "bs", "bf", "closed"}
FLOATS = {"dur", "pct", "price"}
INTS = {"task"}
AUTO_SRC = "Состав проекта"


def can_plan(user, project, visible_ids=None):
    if pult_role(user) == BOSS:
        return True
    if pult_role(user) != GIP:
        return False
    if visible_ids is not None:
        return project.pk in visible_ids
    return visible_projects_for(user).filter(pk=project.pk).exists()


def _projects_for(user):
    return Project.objects.all() if pult_role(user) == BOSS else visible_projects_for(user)


def row_json(r):
    out = {"id": r.pk, "project": r.project.name}
    for key, field in FIELDS.items():
        value = getattr(r, field)
        if key in DATES:
            value = value.isoformat() if value else None
        elif value == "":
            value = None
        out[key] = value
    return out


def plan_rows(user):
    return list(PlanRow.objects.filter(project__in=_projects_for(user)).select_related("project"))


def plan_state(user):
    s = PultSettings.load()
    return {
        "rows": [row_json(r) for r in plan_rows(user)],
        "version": s.plan_version,
        "nextId": (PlanRow.objects.aggregate(m=Max("id"))["m"] or 0) + 1,
    }


def _parse_value(key, value):
    if value in (None, ""):
        return None if key in DATES | FLOATS | INTS else ""
    try:
        if key in DATES:
            return date.fromisoformat(str(value)[:10])
        if key in FLOATS:
            return float(value)
        if key in INTS:
            return int(value)
    except (TypeError, ValueError):
        raise PultError(f"Неверное значение в поле «{key}»: {value}")
    return str(value).strip()[:500]


def _values(row_dict):
    return {FIELDS[k]: _parse_value(k, row_dict.get(k)) for k in FIELDS}


def _model_values(r):
    return {f: getattr(r, f) for f in FIELDS.values()}


def _bump_version():
    s = PultSettings.load()
    PultSettings.objects.filter(pk=s.pk).update(plan_version=s.plan_version + 1)


@transaction.atomic
def save_plan(user, rows, version):
    """Brauzer ko'rgan barcha qatorlarni qaytaradi; faqat o'zgargan loyihalar yoziladi."""
    s = PultSettings.objects.select_for_update().get(pk=PultSettings.load().pk)
    if version is None or int(version) != s.plan_version:
        raise PultError("Состав проекта только что изменил кто-то другой. Данные обновлены — повторите действие.", 409)
    if not isinstance(rows, list):
        raise PultError("Неверный запрос.")

    projects = list(_projects_for(user))
    visible_ids = {p.pk for p in projects}
    by_name = {}
    for p in projects:
        by_name.setdefault(p.name, []).append(p)

    incoming = {}
    for d in rows:
        if not isinstance(d, dict):
            raise PultError("Неверный запрос.")
        try:
            rid = int(d.get("id"))
        except (TypeError, ValueError):
            raise PultError("У строки состава нет ID.")
        if rid < 1 or rid in incoming:
            raise PultError(f"Неверный или повторный ID {rid}.")
        matches = by_name.get(str(d.get("project") or ""), [])
        if len(matches) != 1:
            raise PultError(f"Проект «{d.get('project')}» не найден или его имя не уникально.")
        incoming[rid] = (matches[0], _values(d))

    existing = {r.pk: r for r in PlanRow.objects.filter(project_id__in=visible_ids)}
    new_ids = [rid for rid in incoming if rid not in existing]
    if PlanRow.objects.filter(pk__in=new_ids).exists():
        raise PultError("ID строки уже занят в другом проекте. Обновите страницу и повторите.", 409)

    changed = set()
    for rid, r in existing.items():
        if rid not in incoming:
            changed.add(r.project_id)
        else:
            project, values = incoming[rid]
            if project.pk != r.project_id or values != _model_values(r):
                changed.update({project.pk, r.project_id})
    changed.update(incoming[rid][0].pk for rid in new_ids)

    for project in projects:
        if project.pk in changed and not can_plan(user, project, visible_ids):
            raise PultError(f"Нет прав менять состав проекта «{project.name}».", 403)

    PlanRow.objects.filter(pk__in=[rid for rid, r in existing.items() if rid not in incoming and r.project_id in changed]).delete()
    for rid, (project, values) in incoming.items():
        if project.pk not in changed:
            continue
        row = existing.get(rid) or PlanRow(pk=rid)
        row.project = project
        for field, value in values.items():
            setattr(row, field, value)
        row.save()
    if changed:
        PultSettings.objects.filter(pk=s.pk).update(plan_version=s.plan_version + 1)
    return len(changed)


# ---------------------------------------------------------------- reference data

DEFAULT_STAGES = [("Проектирование", 70, None, "Специалист", 1), ("Смета", 10, 5, "Сметчик", 2),
                  ("Оформление", 15, 3, "Оформитель", 3), ("Печать", 5, 1, "Печать", 4)]


def disciplines_json():
    out = []
    for d in Discipline.objects.select_related("pult_config"):
        cfg = getattr(d, "pult_config", None) or DisciplineConfig(discipline=d)
        out.append({"code": d.code, "name": d.name, "dur": cfg.duration, "links": cfg.links, "order": cfg.order,
                    "lat": cfg.latin_code, "dtype": cfg.doc_type, "smeta": "Да" if cfg.needs_estimate else "Нет"})
    return sorted(out, key=lambda x: (x["order"], x["code"]))


def stages_json():
    rows = list(StageConfig.objects.all())
    if not rows:
        return [{"name": n, "w": w, "days": d, "role": r, "order": o} for n, w, d, r, o in DEFAULT_STAGES]
    return [{"name": s.name, "w": s.weight, "days": s.days, "role": s.role, "order": s.order} for s in rows]


def ciphers_json(user):
    return [
        {"project": c.project.name, "prefix": c.prefix, "stage": c.stage, "code": c.code, "digits": c.digits, "common": c.common}
        for c in CipherRule.objects.filter(project__in=_projects_for(user)).select_related("project")
    ]


def _manager_project(user, name):
    matches = list(_projects_for(user).filter(name=str(name or ""))[:2])
    if len(matches) != 1:
        raise PultError(f"Проект «{name}» не найден или его имя не уникально.")
    if not can_plan(user, matches[0]):
        raise PultError("Это может сделать ГИП проекта или руководитель.", 403)
    return matches[0]


@transaction.atomic
def add_discipline(user, data):
    if pult_role(user) not in (BOSS, GIP):
        raise PultError("Добавлять дисциплины может ГИП или руководитель.", 403)
    code = str(data.get("code") or "").strip().upper()[:20]
    name = str(data.get("name") or "").strip()[:100]
    if not code or not name:
        raise PultError("Нужны шифр и наименование.")
    if Discipline.objects.filter(code=code).exists():
        raise PultError(f"Шифр {code} уже есть.")
    order = (DisciplineConfig.objects.aggregate(m=Max("order"))["m"] or 0) + 1
    discipline = Discipline.objects.create(code=code, name=name)
    try:
        duration = max(1, int(data.get("dur") or 10))
    except (TypeError, ValueError):
        duration = 10
    DisciplineConfig.objects.create(discipline=discipline, duration=duration, links=str(data.get("links") or "")[:255], order=order)
    return discipline


@transaction.atomic
def save_cipher(user, data):
    project = _manager_project(user, data.get("project"))
    prefix, stage, code = (str(data.get(k) or "").strip().upper() for k in ("prefix", "stage", "code"))
    if not prefix or not stage or not code:
        raise PultError("Нужны префикс, стадия и код проекта.")
    try:
        digits = max(2, min(8, int(data.get("digits") or 5)))
    except (TypeError, ValueError):
        digits = 5
    CipherRule.objects.update_or_create(project=project, defaults={
        "prefix": prefix[:20], "stage": stage[:10], "code": code[:20], "digits": digits,
        "common": (str(data.get("common") or "").strip().upper() or "ZZ01")[:10],
    })


# ---------------------------------------------------------------- import from the platform's objects

def _wbs_top(rows):
    tops = [int(w) for w in (r.wbs for r in rows) if w.isdigit()]
    return max(tops, default=0)


@transaction.atomic
def import_platform_objects(user, project_name):
    """Loyiha ustasida kiritilgan obyekt/pod-obyekt va fanlarni Состав'ga qo'shadi.

    Pultda bitta daraja bor (Объект → Раздел), shuning uchun pod-obyekt alohida
    «Obyekt · Pod» obyektiga aylanadi. Ilgari ko'chirilganlar (source_key)
    qayta qo'shilmaydi; mavjud bo'limda ijrochi bo'sh bo'lsa — to'ldiriladi."""
    from apps.projects.models import SubObject

    project = _manager_project(user, project_name)
    PultSettings.objects.select_for_update().get(pk=PultSettings.load().pk)
    rows = list(PlanRow.objects.filter(project=project))
    by_key = {r.source_key: r for r in rows if r.source_key}
    next_id = (PlanRow.objects.aggregate(m=Max("id"))["m"] or 0) + 1
    top = _wbs_top(rows)
    obj_codes = [int(c[2:]) for c in (r.code for r in rows if r.kind == "Объект") if c[2:].isdigit()]
    next_code = max(obj_codes, default=0) + 1
    configs = {c.discipline_id: c for c in DisciplineConfig.objects.all()}
    added = {"objects": 0, "sections": 0, "owners": 0}

    leaves = []
    objects = SubObject.objects.filter(project=project, parent__isnull=True).prefetch_related(
        "disciplines__discipline", "disciplines__assignee", "pod_objects__disciplines__discipline",
        "pod_objects__disciplines__assignee",
    )
    for obj in objects:
        pods = list(obj.pod_objects.all())
        if obj.disciplines.all() or not pods:
            leaves.append((obj, obj.name))
        leaves += [(pod, f"{obj.name} · {pod.name}") for pod in pods]

    for sub, name in leaves:
        obj_row = by_key.get(f"so:{sub.pk}")
        if obj_row is None:
            top += 1
            obj_row = PlanRow.objects.create(
                id=next_id, project=project, wbs=str(top), code=f"BL{next_code:02d}", name=name[:500],
                kind="Объект", client="Да", in_plan="Нет", source_key=f"so:{sub.pk}",
                comment="Из объектов платформы",
            )
            next_id, next_code = next_id + 1, next_code + 1
            added["objects"] += 1
        kids = [r for r in PlanRow.objects.filter(project=project, wbs__startswith=obj_row.wbs + ".")]
        sub_n = max((int(r.wbs.rsplit(".", 1)[1]) for r in kids if r.wbs.rsplit(".", 1)[1].isdigit()), default=0)
        for sd in sub.disciplines.all():
            owner = sd.assignee.full_name if sd.assignee_id else ""
            existing = by_key.get(f"sod:{sd.pk}") or next(
                (r for r in kids if r.code == sd.discipline.code and r.wbs.rsplit(".", 1)[0] == obj_row.wbs), None)
            if existing is not None:
                if owner and not existing.owner:
                    existing.owner = owner
                    existing.save(update_fields=["owner", "updated_at"])
                    added["owners"] += 1
                continue
            sub_n += 1
            cfg = configs.get(sd.discipline_id)
            PlanRow.objects.create(
                id=next_id, project=project, wbs=f"{obj_row.wbs}.{sub_n}", code=sd.discipline.code,
                name=sd.discipline.name, kind="Раздел", owner=owner, dur=cfg.duration if cfg else 10,
                client="Да", in_plan="Нет", source_key=f"sod:{sd.pk}",
                snet=None, comment=f"Срок в платформе: {sd.deadline:%d.%m.%Y}" if sd.deadline else "",
            )
            next_id += 1
            added["sections"] += 1
    if any(added.values()):
        _bump_version()
    return added


# ---------------------------------------------------------------- «Задачи и договоры»

SYNC_TASK_FIELDS = {"assignee", "task", "amount", "days", "status"}


@transaction.atomic
def apply_sync(user, data, finance_allowed):
    """Состав bo'yicha brauzer hisoblagan o'zgarishlarni (planSync) qo'llaydi.
    Har bir element shu loyihaga tegishliligi va maydonlari tekshiriladi."""
    from .finance import create_contract, next_contract_code, update_contract

    project = _manager_project(user, data.get("project"))
    plan = {r.pk: r for r in PlanRow.objects.filter(project=project)}
    task_map, con_map = {}, {}
    counts = {"taskNew": 0, "taskUpd": 0, "conNew": 0, "conUpd": 0}

    for item in data.get("taskNew") or []:
        section = item.get("section")
        if section not in plan:
            raise PultError(f"Раздел {section} не найден в составе проекта.")
        assignee = resolve_person(item.get("assignee"))
        task = Task.objects.create(
            title=str(item.get("task") or "").strip()[:255] or plan[section].name, project=project,
            assignee=assignee, creator=user, description=str(item.get("comment") or "") or None,
        )
        wf = ensure_workflow(task)
        wf.status, wf.flow, wf.stage, wf.section = WS.DRAFT, Flow.PROJECT, "Проектирование", section
        wf.days = int(item["days"]) if str(item.get("days") or "").isdigit() else None
        wf.amount = float(item["amount"]) if item.get("amount") not in (None, "") else None
        save_workflow(task, wf)
        log_status(task, wf, user, "Черновик: из состава проекта")
        ensure_project_member(project, assignee)
        task_map[item.get("id")] = wf.number
        counts["taskNew"] += 1

    for upd in data.get("taskUpd") or []:
        task, wf = get_task(user, upd.get("id"))
        if task.project_id != project.pk:
            raise PultError(f"Задача №{wf.number} из другого проекта.")
        changes = upd.get("set") or {}
        if set(changes) - SYNC_TASK_FIELDS:
            raise PultError("Недопустимое изменение задачи.")
        if "assignee" in changes:
            task.assignee = resolve_person(changes["assignee"])
            ensure_project_member(project, task.assignee)
        if "task" in changes:
            task.title = str(changes["task"])[:255]
        task.save()
        if "amount" in changes:
            wf.amount = float(changes["amount"]) if changes["amount"] not in (None, "") else None
        if "days" in changes and wf.status in (WS.DRAFT, WS.NEW):
            wf.days = int(changes["days"]) if changes["days"] not in (None, "") else None
        if "status" in changes:
            if changes["status"] != WS.CANCELLED:
                raise PultError("Синхронизация может только отменить задачу.")
            wf.status = WS.CANCELLED
        save_workflow(task, wf)
        if "status" in changes:
            log_status(task, wf, user, "Отменена: раздел снят из состава")
        counts["taskUpd"] += 1

    if finance_allowed:
        for c in data.get("conNew") or []:
            code = str(c.get("id") or "")
            if not code or Contract.objects.filter(code=code).exists():
                code = next_contract_code()
            create_contract(project, code, c, source=AUTO_SRC)
            con_map[c.get("id")] = code
            counts["conNew"] += 1
        for u in data.get("conUpd") or []:
            contract = Contract.objects.filter(code=u.get("id"), project=project).first()
            if contract is None:
                raise PultError(f"Договор {u.get('id')} не найден в проекте.")
            update_contract(contract, u.get("set") or {})
            counts["conUpd"] += 1

    for entry in data.get("sec") or []:
        if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[1], dict):
            raise PultError("Неверный запрос.")
        row = plan.get(entry[0])
        if row is None:
            continue
        links = entry[1]
        if "task" in links:
            value = task_map.get(links["task"], links["task"])
            row.task = int(value) if str(value).isdigit() else None
        if "contract" in links and finance_allowed:
            row.contract = str(con_map.get(links["contract"], links["contract"]) or "")
        row.save()
    _bump_version()
    return counts
