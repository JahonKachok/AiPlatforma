"""«Запросы»: so'rovlar reyestri, kontaktlar, ТКП versiyalari, Excel'dan ko'chirish,
direktor imzosi va muhri. Bo'limni kim ko'rishini ``nav.allowed_pages`` hal qiladi.
"""
import base64
import io
import json
import re
import zipfile
from datetime import date, datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.runtime_config import decrypt, encrypt
from apps.documents.models import AuditLog
from apps.projects.models import Project

from .finance import cur_in, cur_out
from .models import (
    CommercialOffer, CommercialRequest, OfferLibraryItem, PultSettings, RequestContact, RequestLog, SealImage,
)
from .nav import allowed_pages
from .services import PultError, today

STATUSES = set(CommercialRequest.Status.values)
# ТКП saqlanganda holat faqat shu bosqichlardan «ТКП отправлено»ga o'tadi.
BEFORE_OFFER = {CommercialRequest.Status.NEW, CommercialRequest.Status.PREPARING}
MAX_OFFER_BYTES = 200_000
MAX_IMPORT_BYTES = 20 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000
MAX_SEAL_BYTES = 2 * 1024 * 1024

TEXT_FIELDS = ("short", "client", "title", "owner", "kind", "basis", "place", "folder", "tz", "note", "reason")
DATE_FIELDS = {"date": "received", "due": "due"}
CONTACT_FIELDS = {"name": "name", "role": "role", "phone": "phone", "email": "email", "tg": "telegram", "note": "note"}


# ---------------------------------------------------------------- ruxsatlar

def can_requests(user):
    return "req" in allowed_pages(user)


def require_requests(user):
    if not can_requests(user):
        raise PultError("Нет доступа к разделу «Запросы».", 403)


def can_manage_seal(user):
    return user.is_superuser or user.role == User.Role.ADMIN


def can_sign(user):
    if not can_requests(user):
        return False
    return can_manage_seal(user) or PultSettings.load().signers.filter(pk=user.pk).exists()


# ---------------------------------------------------------------- yordamchilar

def _clean(model, field, value):
    """Matnni maydon uzunligiga keltiradi (None -> '')."""
    text = str(value if value is not None else "").strip()
    limit = model._meta.get_field(field).max_length
    return text[:limit] if limit else text


def _date(value, label="Дата"):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise PultError(f"{label}: неверная дата.")


def _number(value):
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    # NaN va cheksizlik JSON'ni ham, yig'indilarni ham buzadi.
    return n if n == n and abs(n) < 1e15 else None


def _iso(d):
    return d.isoformat() if d else None


def _log(req, text, author):
    RequestLog.objects.create(request=req, date=today(), text=_clean(RequestLog, "text", text), author=author[:255])


def _next_number():
    numbers = [int(m.group(1)) for n in CommercialRequest.objects.values_list("number", flat=True)
               if (m := re.search(r"(\d+)$", n))]
    return "R" + str(max(numbers, default=0) + 1).zfill(3)


def _locked(number):
    req = CommercialRequest.objects.select_for_update().filter(number=str(number or "")).first()
    if req is None:
        raise PultError("Запрос не найден, обновите страницу.", 404)
    return req


# ---------------------------------------------------------------- brauzerga

def payload(user):
    """Ro'yxat ma'lumoti. ТКП tarkibi (``data``) og'ir bo'lgani uchun bu yerda
    yo'q — u ochilganda alohida so'raladi (``offer_data``)."""
    if not can_requests(user):
        return {}
    out, contacts, offers, logs = [], [], [], []
    for r in CommercialRequest.objects.select_related("project", "updated_by"):
        out.append({
            "no": r.number, "date": _iso(r.received), "short": r.short, "client": r.client, "title": r.title,
            "status": r.status, "owner": r.owner, "due": _iso(r.due), "kind": r.kind, "basis": r.basis,
            "place": r.place, "folder": r.folder, "tz": r.tz, "tkpNo": r.offer_no, "tkpDate": _iso(r.offer_date),
            "amount": r.amount, "cur": cur_out(r.currency), "vat": r.vat, "tkpText": r.offer_text,
            "tkp2Date": _iso(r.offer2_date), "tkp2": r.offer2_text, "reason": r.reason, "note": r.note,
            "project": r.project.name if r.project_id else "", "version": r.version,
        })
    for c in RequestContact.objects.select_related("request"):
        contacts.append({"id": c.pk, "req": c.request.number, "name": c.name, "role": c.role, "phone": c.phone,
                         "email": c.email, "tg": c.telegram, "note": c.note})
    for o in CommercialOffer.objects.select_related("request", "author").defer("data"):
        offers.append({"id": o.pk, "req": o.request.number, "no": o.number, "date": _iso(o.date), "ver": o.version,
                       "net": o.net, "vat": o.vat, "total": o.total, "cur": cur_out(o.currency),
                       "by": o.author.full_name if o.author_id else o.author_name, "at": o.created_at.isoformat()})
    for x in RequestLog.objects.select_related("request"):
        logs.append({"date": _iso(x.date), "req": x.request.number, "text": x.text, "by": x.author})
    library = [
        {"sec": i.section, "group": i.group, "text": i.text, "priceRaw": i.value, "price": _price(i.value),
         "days": i.days, "def": "Да" if i.is_default else "Нет", "order": i.order}
        for i in OfferLibraryItem.objects.all()
    ]
    return {"reqs": out, "rcont": contacts, "tkp": offers, "rlog": logs, "tkplib": library}


def offer_data(user, pk):
    require_requests(user)
    offer = CommercialOffer.objects.filter(pk=pk).first()
    if offer is None:
        raise PultError("Сохранённое ТКП не найдено.", 404)
    return {"data": offer.data, "ver": offer.version}


# ---------------------------------------------------------------- kartochka

def _apply_fields(req, data):
    for key in TEXT_FIELDS:
        if key in data:
            setattr(req, key, _clean(CommercialRequest, key, data[key]))
    for key, field in DATE_FIELDS.items():
        if key in data:
            setattr(req, field, _date(data[key]))
    if "status" in data:
        if data["status"] not in STATUSES:
            raise PultError("Неизвестный статус запроса.")
        req.status = data["status"]
    if "project" in data:
        name = str(data["project"] or "").strip()
        project = Project.objects.filter(name=name).first() if name else None
        if name and project is None:
            raise PultError(f"Проект «{name}» не найден.")
        req.project = project
    # Havola sahifada <a href> bo'lib chiqadi: javascript: kabi sxemalar o'tmasin.
    if req.folder and not req.folder.startswith("https://"):
        raise PultError("Ссылка на папку должна начинаться с https://")
    if not req.short and not req.title:
        raise PultError("Напишите краткое название или название объекта.")


def _save_contacts(req, rows):
    if not isinstance(rows, list) or len(rows) > 100:
        raise PultError("Неверный список контактов.")
    existing = {c.pk: c for c in req.contacts.all()}
    keep = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PultError("Неверный список контактов.")
        values = {field: _clean(RequestContact, field, row.get(key)) for key, field in CONTACT_FIELDS.items()}
        contact = existing.get(row.get("id")) if row.get("id") else None
        if not any(values.values()):
            continue  # bo'shatilgan qator — kontakt o'chiriladi
        if contact is None:
            RequestContact.objects.create(request=req, **values)
            continue
        keep.add(contact.pk)
        for field, value in values.items():
            setattr(contact, field, value)
        contact.save()
    req.contacts.filter(pk__in=set(existing) - keep).delete()


def save_request(user, body):
    require_requests(user)
    data = body.get("set")
    if not isinstance(data, dict):
        raise PultError("Неверный запрос.")
    number = str(body.get("no") or "").strip()
    for _attempt in range(5):
        try:
            with transaction.atomic():
                if number:
                    req = _locked(number)
                    if body.get("version") != req.version:
                        raise PultError("Запрос уже изменён другим сотрудником. Закройте карточку и откройте её снова.", 409)
                    old = req.status
                    _apply_fields(req, data)
                    req.version += 1
                    text = f"Статус: {old} → {req.status}" if old != req.status else "Карточка изменена"
                else:
                    req = CommercialRequest(number=_next_number())
                    _apply_fields(req, data)
                    text = "Запрос создан"
                req.updated_by = user
                req.save()
                if "contacts" in body:
                    _save_contacts(req, body["contacts"])
                _log(req, text, user.full_name)
            return req
        except IntegrityError:
            # Ikki kishi bir vaqtda yangi so'rov ochdi — keyingi raqam bilan qayta.
            if number:
                raise
    raise PultError("Не удалось присвоить номер, повторите.", 409)


# ---------------------------------------------------------------- ТКП

def offer_totals(data):
    """Summalar serverda qayta hisoblanadi (brauzerdagi tkpCalc bilan bir xil qoida)."""
    rate = (_number(data.get("vatRate")) or 0) / 100
    items = data.get("items") if isinstance(data.get("items"), list) else []
    total_items = sum(_number(x.get("price")) or 0 for x in items if isinstance(x, dict) and x.get("on"))
    manual = _number(data.get("manual")) or 0
    if total_items > 0:
        net = total_items
        vat = _round(net * rate)
        return net, vat, net + vat
    if manual > 0:
        if data.get("manualVat"):
            net = _round(manual / (1 + rate))
            return net, manual - net, manual
        vat = _round(manual * rate)
        return manual, vat, manual + vat
    return 0, 0, 0


def _round(x):
    # JS Math.round kabi (0.5 — yuqoriga); Python round() juft songa yaxlitlaydi.
    return int(x + 0.5)


def save_offer(user, number, body):
    require_requests(user)
    data = body.get("data")
    if not isinstance(data, dict):
        raise PultError("Неверный запрос.")
    if len(str(data)) > MAX_OFFER_BYTES:
        raise PultError("ТКП слишком большое. Уберите лишние позиции.")
    offer_no = _clean(CommercialOffer, "number", data.get("no"))
    if not offer_no:
        raise PultError("Укажите № ТКП.")
    offer_date = _date(data.get("date"), "Дата ТКП")
    net, vat, total = offer_totals(data)
    if not total or total < 0:
        raise PultError("Нет суммы: отметьте позиции с ценой или введите сумму вручную.")
    currency = cur_in(data.get("cur"))
    without_vat = data.get("vatMode") == "without"
    shown = net if without_vat else total
    text = str(body.get("text") or "").strip()[:2000]
    with transaction.atomic():
        req = _locked(number)
        if CommercialOffer.objects.filter(number=offer_no).exclude(request=req).exists() or (
            CommercialRequest.objects.filter(offer_no=offer_no).exclude(pk=req.pk).exists()
        ):
            raise PultError(f"№ ТКП {offer_no} уже занят другим запросом. Измените номер.", 409)
        version = (req.offers.filter(number=offer_no).order_by("-version").values_list("version", flat=True).first() or 0) + 1
        offer = CommercialOffer.objects.create(
            request=req, number=offer_no, version=version, date=offer_date, net=net, vat=vat, total=total,
            currency=currency, data=data, author=user,
        )
        req.amount, req.currency, req.vat = shown, currency, "без НДС" if without_vat else "с НДС"
        if req.offer_no and req.offer_no != offer_no:
            req.offer2_date, req.offer2_text = offer_date, text
        else:
            req.offer_no, req.offer_date, req.offer_text = offer_no, offer_date, text
        if req.status in BEFORE_OFFER:
            req.status = CommercialRequest.Status.SENT
        req.version += 1
        req.updated_by = user
        req.save()
        amount = f"{shown:,.0f}".replace(",", " ")
        _log(req, f"ТКП №{offer_no} сохранено (версия {version}): {amount} {cur_out(currency)}", user.full_name)
    return offer


# ---------------------------------------------------------------- imzo va muhr

def seal_images(user, doc_name):
    """Rasmlarni faqat imzo huquqi bor odamga beradi; har foydalanish auditga yoziladi."""
    if not can_sign(user):
        raise PultError("Подпись и печать может ставить только руководитель.", 403)
    images = {i.kind: i for i in SealImage.objects.all()}
    out = {kind: decrypt(i.encrypted) for kind, i in images.items()}
    ready = bool(out.get("seal") and out.get("sign"))
    if ready:
        AuditLog.log(obj=images["seal"], action="seal_used", user=user, details={"document": str(doc_name or "")[:255]})
    return {"ready": ready, "canUpload": can_manage_seal(user),
            "images": {"seal": out["seal"], "sign": out["sign"]} if ready else None}


def save_seal(user, files):
    if not can_manage_seal(user):
        raise PultError("Загрузить подпись и печать может только администратор.", 403)
    from PIL import Image

    saved = 0
    for kind, _label in SealImage.KINDS:
        f = files.get(kind)
        if f is None:
            continue
        if f.size > MAX_SEAL_BYTES:
            raise PultError("Картинка больше 2 МБ.")
        raw = f.read()
        try:
            with Image.open(io.BytesIO(raw)) as img:
                fmt = img.format
                img.verify()
        except Exception:
            raise PultError("Файл не похож на картинку PNG.")
        if fmt != "PNG":
            raise PultError("Нужна картинка PNG с прозрачным фоном.")
        obj, _created = SealImage.objects.update_or_create(
            kind=kind, defaults={"encrypted": encrypt(base64.b64encode(raw).decode()), "updated_by": user},
        )
        AuditLog.log(obj=obj, action="seal_uploaded", user=user)
        saved += 1
    if not saved:
        raise PultError("Выберите картинку подписи или печати.")
    return saved


# ---------------------------------------------------------------- Excel'dan ko'chirish
# Google Sheets'dagi moliya fayli .xlsx qilib yuklanadi; varaq va ustun nomlari o'sha yerdagidek.

SHEET_REQ = {
    "№": "number", "Дата поступления": "received", "Краткое название": "short", "Заказчик": "client",
    "Объект / название проекта": "title", "Статус": "status", "Ответственный": "owner", "Срок подачи ТКП": "due",
    "Вид работ": "kind", "Основание (письмо, тендер)": "basis", "Место объекта": "place",
    "Папка на Диске": "folder", "ТЗ (ссылка)": "tz", "№ ТКП": "offer_no", "Дата ТКП": "offer_date",
    "Сумма ТКП": "amount", "Валюта": "currency", "НДС": "vat", "ТКП (как в письме)": "offer_text",
    "Дата ТКП-2": "offer2_date", "ТКП-2": "offer2_text", "Причина выигрыша / проигрыша": "reason",
    "Примечание": "note", "Проект в финансах": "project",
}
SHEET_CONTACT = {"Запрос №": "req", "Имя": "name", "Должность / организация": "role", "Телефон": "phone",
                 "Email": "email", "Telegram": "telegram", "Примечание": "note"}
SHEET_OFFER = {"Запрос №": "req", "№ ТКП": "number", "Дата": "date", "Версия": "version", "Сумма без НДС": "net",
               "НДС": "vat", "Итого": "total", "Валюта": "currency", "Кто": "by", "Данные (не редактировать)": "json"}
SHEET_LIB = {"Раздел": "section", "Группа": "group", "Текст": "text", "Цена без НДС, сум": "value", "Дней": "days",
             "По умолчанию": "default", "Порядок": "order"}
SHEET_LOG = {"Дата": "date", "Запрос №": "req", "Событие": "text", "Кто": "by"}


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _cell_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _cell(value)
    if m := re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})", text):
        parts = int(m[3]), int(m[2]), int(m[1])
    elif m := re.match(r"^(\d{4})-(\d{2})-(\d{2})", text):
        parts = int(m[1]), int(m[2]), int(m[3])
    else:
        return None
    try:
        return date(*parts)
    except ValueError:
        return None


def _cell_number(value):
    if isinstance(value, (int, float)):
        return _number(value)
    text = re.sub(r"\s", "", _cell(value)).rstrip(",.")
    if re.match(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$", text):
        text = text.replace(",", "")
    elif re.match(r"^-?\d+,\d+$", text):
        text = text.replace(",", ".")
    return _number(text)


def _price(raw):
    return _cell_number(raw)


def _sheet(book, name, columns, required):
    if name not in book.sheetnames:
        return []
    rows = book[name].iter_rows(values_only=True)
    header = [columns.get(_cell(h)) for h in next(rows, ())]
    if not set(required) <= set(header):
        raise PultError(f"На листе «{name}» не найдены нужные колонки.")
    out = []
    for i, row in enumerate(rows):
        if i >= MAX_IMPORT_ROWS:
            raise PultError(f"На листе «{name}» слишком много строк.")
        out.append({key: value for key, value in zip(header, row) if key})
    return out


def import_workbook(user, upload):
    """Mavjud yozuvlar ustiga yozilmaydi: faqat platformada yo'qlari qo'shiladi,
    shuning uchun faylni qayta yuklash xavfsiz. «Справочник ТКП» qatorlari
    (narxlar) esa fayldagiga yangilanadi."""
    from openpyxl import load_workbook
    from openpyxl.utils.exceptions import InvalidFileException

    require_requests(user)
    if upload is None:
        raise PultError("Выберите файл Excel (.xlsx).")
    if upload.size > MAX_IMPORT_BYTES:
        raise PultError("Файл больше 20 МБ.")
    try:
        book = load_workbook(upload, read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise PultError("Файл не открылся. Нужен Excel (.xlsx).")
    try:
        sheets = {
            "reqs": _sheet(book, "Запросы", SHEET_REQ, ("number", "status")),
            "contacts": _sheet(book, "Контакты запросов", SHEET_CONTACT, ("req", "name")),
            "offers": _sheet(book, "ТКП", SHEET_OFFER, ("req", "number")),
            "lib": _sheet(book, "Справочник ТКП", SHEET_LIB, ("section", "text")),
            "log": _sheet(book, "Журнал запросов", SHEET_LOG, ("req", "text")),
        }
    finally:
        book.close()
    if not any(sheets.values()):
        raise PultError("В файле нет листов «Запросы» или «Справочник ТКП».")

    counts = dict.fromkeys(("requests", "contacts", "offers", "library", "skipped"), 0)
    with transaction.atomic():
        projects = {p.name: p for p in Project.objects.all()}
        existing = {r.number: r for r in CommercialRequest.objects.all()}
        fresh = set()
        for row in sheets["reqs"]:
            number = _clean(CommercialRequest, "number", _cell(row.get("number")))
            if not number:
                continue
            if number in existing:
                counts["skipped"] += 1
                continue
            req = CommercialRequest(number=number, updated_by=user)
            notes = [_cell(row.get("note"))]
            for field in ("short", "client", "title", "owner", "kind", "basis", "place", "tz", "offer_no", "vat",
                          "offer_text", "offer2_text", "reason"):
                setattr(req, field, _clean(CommercialRequest, field, _cell(row.get(field))))
            for field in ("received", "due", "offer_date", "offer2_date"):
                setattr(req, field, _cell_date(row.get(field)))
            req.amount = _cell_number(row.get("amount"))
            req.currency = "USD" if _cell(row.get("currency")).upper() in ("USD", "$") else "UZS"
            status = _cell(row.get("status"))
            req.status = status if status in STATUSES else CommercialRequest.Status.NEW
            if status and status not in STATUSES:
                notes.append(f"Статус в таблице: {status}")
            folder = _cell(row.get("folder"))
            if folder.startswith("https://"):
                req.folder = _clean(CommercialRequest, "folder", folder)
            elif folder:
                notes.append(f"Папка: {folder}")
            project = _cell(row.get("project"))
            req.project = projects.get(project)
            if project and req.project is None:
                notes.append(f"Проект в финансах: {project}")
            req.note = "\n".join(n for n in notes if n)
            req.save()
            existing[number] = req
            fresh.add(number)
            counts["requests"] += 1

        for row in sheets["contacts"]:
            req = existing.get(_cell(row.get("req")))
            values = {f: _clean(RequestContact, f, _cell(row.get(f))) for f in CONTACT_FIELDS.values()}
            if req is None or not (values["name"] or values["phone"]):
                continue
            # Platformada tahrirlangan kartochkaning kontaktlari qayta paydo bo'lmasin.
            if req.number in fresh and not req.contacts.filter(name=values["name"], phone=values["phone"]).exists():
                RequestContact.objects.create(request=req, **values)
                counts["contacts"] += 1

        for row in sheets["offers"]:
            req = existing.get(_cell(row.get("req")))
            number = _clean(CommercialOffer, "number", _cell(row.get("number")))
            if req is None or not number:
                continue
            version = max(1, int(_cell_number(row.get("version")) or 1))
            if req.offers.filter(number=number, version=version).exists():
                continue
            try:
                data = json.loads(_cell(row.get("json")) or "{}")
            except ValueError:
                data = {}
            CommercialOffer.objects.create(
                request=req, number=number, version=version, date=_cell_date(row.get("date")),
                net=_cell_number(row.get("net")) or 0, vat=_cell_number(row.get("vat")) or 0,
                total=_cell_number(row.get("total")) or 0,
                currency="USD" if _cell(row.get("currency")).upper() in ("USD", "$") else "UZS",
                data=data if isinstance(data, dict) else {}, author_name=_cell(row.get("by"))[:255],
            )
            counts["offers"] += 1

        sections = {s for s, _label in OfferLibraryItem.SECTIONS}
        for row in sheets["lib"]:
            section, text = _cell(row.get("section")), _cell(row.get("text"))
            if section not in sections or not text:
                continue
            days, order = _cell_number(row.get("days")), _cell_number(row.get("order"))
            item = OfferLibraryItem.objects.filter(section=section, group=_cell(row.get("group"))[:255], text=text).first()
            item = item or OfferLibraryItem(section=section, group=_cell(row.get("group"))[:255], text=text)
            item.value = _clean(OfferLibraryItem, "value", _cell(row.get("value")))
            item.days = int(days) if days is not None and days >= 0 else None
            item.is_default = _cell(row.get("default")).lower() == "да"
            item.order = int(order) if order is not None and order >= 0 else 999
            item.save()
            counts["library"] += 1

        for row in sheets["log"]:
            req = existing.get(_cell(row.get("req")))
            text = _clean(RequestLog, "text", _cell(row.get("text")))
            if req is None or req.number not in fresh or not text:
                continue
            RequestLog.objects.create(request=req, date=_cell_date(row.get("date")) or timezone.localdate(),
                                      text=text, author=_cell(row.get("by"))[:255])
        for number in fresh:
            _log(existing[number], "Перенесено из Excel", user.full_name)
    return counts
