"""AI Ofis workspace and generation. No provider call holds a database transaction."""
import logging
import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import OfficeEmployee, OfficeLead, OfficeResult, OfficeTask

logger = logging.getLogger(__name__)
LEASE = timedelta(minutes=3)


class OfficeError(ValueError):
    pass


def today_counts():
    day = timezone.localdate()
    return {
        "leads": OfficeLead.objects.filter(created_at__date=day).count(),
        "tasks": OfficeTask.objects.filter(created_at__date=day).count(),
        "results": OfficeResult.objects.filter(created_at__date=day).count(),
    }


def workspace():
    tasks = list(OfficeTask.objects.select_related("result").order_by("-pk"))
    rows = []
    now = timezone.now()
    for task in tasks:
        result = getattr(task, "result", None)
        rows.append({
            "id": task.pk, "employee": task.employee_id, "lead": task.lead_id, "brief": task.brief,
            "status": task.status, "busy": bool(task.run_token and task.started_at > now - LEASE),
            "body": result.body if result else "", "updated": result.updated_at.isoformat() if result else "",
        })
    employees = list(OfficeEmployee.objects.order_by("name").values("key", "name", "role", "description"))
    for employee in employees:
        own = [t for t in rows if t["employee"] == employee["key"]]
        active = next((t for t in own if t["status"] == "working"), None)
        employee["state"] = "working" if active else (own[0]["status"] if own else "idle")
        employee["current"] = active["id"] if active else None
    return {
        "employees": employees, "tasks": rows,
        "leads": list(OfficeLead.objects.order_by("-pk").values("id", "brief", "employee_id", "price", "status")),
        "today": today_counts(), "demo": not bool(settings.AI_OFFICE_API_KEY),
    }


def report():
    leads = OfficeLead.objects.all()
    tasks = OfficeTask.objects.all()
    today = today_counts()
    return (f"Bugun {today['leads']} ta lid va {today['tasks']} ta vazifa qo‘shildi. "
            f"{today['results']} ta natija tayyorlandi.\n\n"
            f"Jami {leads.count()} ta lid. Yangi: {leads.filter(status='new').count()}, "
            f"bog‘lanilgan: {leads.filter(status='contacted').count()}.\n"
            f"Jami {tasks.count()} ta vazifa. Ish jarayonida: {tasks.filter(status='working').count()}, "
            f"tayyor: {tasks.filter(status='ready').count()}.")


def sales_draft(task):
    brief = task.lead.brief if task.lead else task.brief
    match = re.match(r"([A-ZА-ЯЁ][\w‘’'-]+)\s+(?:Telegram|Instagram|telefon|orqali|ingliz|kurs)", brief)
    greeting = f"Assalomu alaykum, {match[1]}!" if match else "Assalomu alaykum!"
    subject = re.search(r"([\w‘’'-]+\s+tili|[\w‘’'-]+)\s+kurs", brief, re.I)
    if subject:
        intro = f"{subject[1].capitalize()} kursiga qiziqqaningiz uchun rahmat."
    else:
        intro = "Murojaatingiz uchun rahmat."
    if task.lead and task.lead.price is not None:
        amount = f"{task.lead.price:,}".replace(",", " ")
        detail = f"Narxi {amount} so‘m. Batafsil ma’lumot yuborishimni xohlaysizmi?"
    elif re.search("narx|qancha|to‘lov|to'lov", brief, re.I):
        detail = "Narxni aniqlashtirib, sizga shu yerda yozaman. Qaysi format sizga qulay?"
    else:
        detail = "Sizga mos variantni tavsiya qilishimiz uchun ehtiyojingiz haqida batafsilroq yozasizmi?"
    return f"{greeting} {intro} {detail}"


def generate_text(task):
    role = task.employee_id
    facts = report() if role in ("analyst", "director") else ""
    if not settings.AI_OFFICE_API_KEY:
        if role == "sales":
            return sales_draft(task)
        if role == "analyst":
            return f"{task.brief}\n\n{facts}"
        if role == "marketing":
            topic = re.sub(r"\s+(?:haqida|uchun|mavzusida)\s+(?:Telegram\s+|Instagram\s+)?"
                           r"post.*$", "", task.brief, flags=re.I).strip(" .!?")
            if "tili" in topic.lower() and re.search("kurs|klub", topic, re.I):
                return (f"{topic}\n\nTil o‘rganish siz uchun nimadan boshlanadi: suhbatdanmi yoki "
                        "yangi so‘zlardanmi? Maqsadingizni izohlarda yozing. Mashg‘ulotlar haqida "
                        "batafsil ma’lumot olish uchun bizga xabar yuboring.")
            return (f"{topic}\n\nBu mavzuda sizni eng ko‘p qaysi savol qiziqtiradi? "
                    "Izohlarda yozing yoki batafsil ma’lumot uchun bizga xabar yuboring.")
        return f"{task.brief}\n\n{facts}\n\nIsh rejasi: yangi lidlarni ko‘rib chiqing va ochiq vazifalar bo‘yicha mas’ullar bilan muddatni kelishing."

    from google import genai
    from google.genai import types

    instructions = {
        "sales": "Lidga yuborish uchun qisqa, muloyim javob loyihasini yoz.",
        "marketing": "Berilgan mavzu va auditoriyaga mos ijtimoiy tarmoq posti yoz.",
        "analyst": "Berilgan haqiqiy ko‘rsatkichlarga asoslanib qisqa hisobot yoz.",
        "director": "Berilgan ko‘rsatkichlar va vazifa asosida rahbar uchun qisqa ish rejasi yoz.",
    }
    prompt = f"Vazifa: {task.brief}\n{facts}"
    if task.lead:
        prompt += f"\nLid murojaati: {task.lead.brief}\nTasdiqlangan narx (so‘m): {task.lead.price}"
    with genai.Client(api_key=settings.AI_OFFICE_API_KEY, http_options=types.HttpOptions(timeout=45000)) as client:
        reply = client.models.generate_content(
            model=settings.AI_OFFICE_MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=instructions[role] + " O‘zbek tilida yoz. Berilmagan narx, chegirma, "
                "muddat va raqamlarni o‘ylab topma. Narx noma’lum bo‘lsa aniqlashtirilishini ayt.",
                max_output_tokens=1500))
    text = (reply.text or "").strip()
    if not text:
        raise OfficeError("Bo‘sh javob.")
    # Price questions with no verified fee must not acquire an AI-invented quote.
    if role == "sales" and (not task.lead or task.lead.price is None):
        if (re.search(r"narx|qancha|to[‘’'ʻ]lov", prompt, re.I) or
                re.search(r"\d|so[‘’'ʻ]?m|dollar|ming|million|bepul|tekin|chegirma", text, re.I)):
            return sales_draft(task)
    return text


def run_task(pk):
    token, now = uuid.uuid4(), timezone.now()
    claimed = (OfficeTask.objects.filter(pk=pk).exclude(status="ready")
               .filter(Q(run_token__isnull=True) | Q(started_at__lt=now - LEASE))
               .update(run_token=token, started_at=now, status="working"))
    if not claimed:
        return
    task = OfficeTask.objects.select_related("lead", "employee").get(pk=pk)
    try:
        body = generate_text(task)
    except Exception as exc:
        logger.warning("Office generation failed for task %s (%s)", pk, type(exc).__name__)
        OfficeTask.objects.filter(pk=pk, run_token=token).update(status="error", run_token=None)
        return
    with transaction.atomic():
        if OfficeTask.objects.filter(pk=pk, run_token=token).update(status="ready", run_token=None):
            OfficeResult.objects.update_or_create(task_id=pk, defaults={"body": body})
