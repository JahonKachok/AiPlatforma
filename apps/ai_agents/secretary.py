"""Sekretar-Dogovornik: rasmiy xat/shartnoma, direktor tasdig'i, imzo va muhr.

Oqim:
1. «Xat tayyorla: ...» -> AI matnni JSON qilib beradi -> DOCX blankada (shapka).
2. Ishchi kompyuter DOCX'ni PDF'ga o'giradi (Word) — WorkerJob(then="secretary_review").
3. PDF direktorga (imzo huquqi borlarga) Telegram'da [✅ Imzo va muhr] [❌ Rad].
4. Tasdiqlansa «Директор» yozuvi ustiga PNG imzo va muhr qo'yiladi
   (apps/documents/signing.py), yangi reviziya bo'lib saqlanadi va so'rovchiga
   tayyor PDF yuboriladi.
Telegram'ga «imzola» izohi bilan yuborilgan tayyor PDF ham 3-qadamdan boshlanadi.
"""
import base64
import io
import logging
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.telegram_bot.texts import t

from . import prompts
from .orchestrator import Reply, _memory_rules
from .services import ask_json

logger = logging.getLogger(__name__)

SIGN_CAPTION = re.compile(r"(imzo|imzola|подпис|на подпись|sign)", re.I)
LETTERHEAD = settings.BASE_DIR / "static" / "pult" / "gastec-letterhead.png"


def _lib_setting(name, default):
    from apps.pult.models import OfferLibraryItem

    row = OfferLibraryItem.objects.filter(section="Настройка", text=name).exclude(value="").first()
    return row.value if row else default


def signers():
    from apps.accounts.models import User
    from apps.pult.inquiries import can_sign

    users = User.objects.filter(is_active=True).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
    return [u for u in users if can_sign(u)]


# ---------------------------------------------------------------- 1. qoralama

def build_docx(data):
    """Blankadagi rasmiy xat (DOCX baytlari)."""
    from docx import Document as Docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    doc = Docx()
    section = doc.sections[0]
    section.left_margin = section.right_margin = Cm(2)
    if LETTERHEAD.exists():
        section.header.paragraphs[0].add_run().add_picture(str(LETTERHEAD), width=Cm(17))
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Times New Roman", Pt(12)
    p = doc.add_paragraph(f"№ ____  от {timezone.localdate():%d.%m.%Y}")
    if data.get("addressee"):
        p = doc.add_paragraph(data["addressee"])
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(data.get("title") or "").bold = True
    for para in (data.get("body") or "").split("\n"):
        if para.strip():
            doc.add_paragraph(para.strip()).paragraph_format.first_line_indent = Cm(1.25)
    doc.add_paragraph()
    org = _lib_setting("Подпись: организация", "ООО «GASTEC PROJECT»")
    fio = _lib_setting("Подпись: ФИО", "")
    # Imzo qo'yiladigan joy: «Директор» so'zi (signing.py uni topadi).
    doc.add_paragraph(f"Директор {org}\t\t\t{fio}")
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _safe_name(title):
    name = re.sub(r"[^\w\- ]+", "", title, flags=re.U).strip()[:60] or "Письмо"
    return name.replace(" ", "_")


def draft(user, text, lang="uz"):
    from apps.documents.models import AuditLog, Document, DocumentVersion
    from apps.pult.services import internal_project
    from apps.worker.models import JobKind
    from apps.worker.services import create_job, is_online

    context = f"today={timezone.localdate().isoformat()}\nauthor={user.full_name}\nrequest: {text[:3000]}"
    data = ask_json(prompts.SECRETARY + _memory_rules(user, "secretary"), context, prompts.SECRETARY_SCHEMA,
                    agent="secretary", max_tokens=4000)
    if not data or not data.get("body"):
        return Reply(t("ag.not_understood", lang))
    filename = f"{_safe_name(data.get('title') or 'Письмо')}.docx"
    project = internal_project(user)
    document = Document.objects.create(
        name=(data.get("title") or "Письмо")[:255], doc_type="letter", project=project, uploaded_by=user,
        file=ContentFile(build_docx(data), name=filename),
    )
    document.file_size = document.file.size
    document.save(update_fields=["file_size"])
    DocumentVersion.objects.create(document=document, version_number=document.version, file=document.file.name,
                                   file_size=document.file_size, uploaded_by=user, notes="Sekretar: qoralama")
    AuditLog.log(obj=document, action="secretary_draft", user=user)
    create_job(JobKind.DOCX_TO_PDF, document, user, then="secretary_review")
    key = "ag.letter_queued" if is_online() else "ag.letter_queued_offline"
    return Reply(t(key, lang, title=document.name))


# ---------------------------------------------------------------- 3. tasdiq

def request_approval(document, requester):
    """PDF'ni imzo huquqi borlarga tugmalar bilan yuboradi."""
    from apps.documents.archivist import open_file
    from apps.documents.services import file_basename
    from apps.telegram_bot.services import chat_language, send_document, send_message

    approvers = signers()
    if not approvers and requester and requester.telegram_chat_id:
        send_message(requester.telegram_chat_id, t("ag.no_signers", chat_language(requester.telegram_chat_id)),
                     parse_mode=None)
        return 0
    who = requester.full_name if requester else "—"
    for user in approvers:
        lang = chat_language(user.telegram_chat_id)
        buttons = [[(t("ag.sign_ok", lang), f"sg:ok:{document.pk}"), (t("ag.sign_no", lang), f"sg:no:{document.pk}")]]
        with open_file(document) as fh:
            send_document(user.telegram_chat_id, fh, file_basename(document), t("ag.sign_ask", lang, name=document.name, who=who))
        send_message(user.telegram_chat_id, t("ag.sign_question", lang, name=document.name), parse_mode=None, buttons=buttons)
    return len(approvers)


def submit_pdf(user, filename, data, lang="uz"):
    """Telegram'ga «imzola» izohi bilan yuborilgan PDF — direktor tasdig'iga."""
    from apps.documents.models import AuditLog, Document, DocumentVersion
    from apps.pult.services import internal_project

    if not filename.lower().endswith(".pdf"):
        return Reply(t("ag.sign_pdf_only", lang))
    document = Document.objects.create(
        name=filename.rsplit(".", 1)[0][:255], doc_type="letter", project=internal_project(user), uploaded_by=user,
        file=ContentFile(bytes(data), name=filename), file_size=len(data),
    )
    DocumentVersion.objects.create(document=document, version_number=document.version, file=document.file.name,
                                   file_size=document.file_size, uploaded_by=user, notes="Imzoga yuborildi")
    AuditLog.log(obj=document, action="sent_for_signature", user=user)
    sent = request_approval(document, user)
    return Reply(t("ag.sign_sent", lang) if sent else t("ag.no_signers", lang))


def decide(user, data, lang="uz"):
    """Tugma «sg:ok:<hujjat>» / «sg:no:<hujjat>» — faqat imzo huquqi borlar."""
    from apps.documents.archivist import add_revision, open_file
    from apps.documents.models import AuditLog, Document
    from apps.documents.services import file_basename
    from apps.documents.signing import LabelNotFound, sign_pdf
    from apps.pult.inquiries import can_sign, seal_images
    from apps.telegram_bot.services import send_document, send_message

    parts = data.split(":")
    if user is None or len(parts) != 3 or not can_sign(user):
        return Reply(t("ag.sign_denied", lang))
    document = Document.objects.filter(pk=parts[2] if re.fullmatch(r"[0-9a-f-]{36}", parts[2]) else None).first()
    if document is None:
        return Reply(t("pd.expired", lang))
    requester = document.uploaded_by
    if parts[1] != "ok":
        AuditLog.log(obj=document, action="signature_rejected", user=user)
        if requester.telegram_chat_id and requester.pk != user.pk:
            send_message(requester.telegram_chat_id, f"❌ {document.name}: {user.full_name}", parse_mode=None)
        return Reply(t("ag.sign_rejected", lang))
    if AuditLog.objects.filter(object_id=str(document.pk), action="signed").exists():
        return Reply(t("pd.expired", lang))
    images = seal_images(user, document.name)
    if not images["ready"]:
        return Reply(t("ag.no_seal", lang))
    with open_file(document) as fh:
        pdf = fh.read()
    try:
        signed = sign_pdf(pdf, base64.b64decode(images["images"]["sign"]), base64.b64decode(images["images"]["seal"]))
    except LabelNotFound:
        return Reply(t("ag.no_label", lang))
    name = file_basename(document)
    add_revision(document, ContentFile(signed, name=name), user, notes="Imzo va muhr")
    AuditLog.log(obj=document, action="signed", user=user)
    for target in {requester, user}:
        if target.telegram_chat_id:
            send_document(target.telegram_chat_id, io.BytesIO(signed), name, f"✅ {document.name}")
    return Reply(t("ag.signed", lang, name=document.name))
