from celery import shared_task
from django.utils.translation import gettext as _


@shared_task
def send_documents_to_telegram(sender_id, recipient_id, document_ids):
    """Tanlangan hujjatlarni oluvchining Telegram'iga yuboradi: bitta fayl —
    o'zi, bir nechta — ZIP. Yuboruvchi ko'ra olmaydigan hujjatlar tushib
    qoladi (ko'rinish qoidasi vazifa ichida qayta tekshiriladi)."""
    from apps.accounts.models import User
    from apps.notifications.models import NotificationType
    from apps.notifications.services import notify_user
    from apps.projects.permissions import visible_projects_for
    from apps.telegram_bot.services import send_document

    from .models import AuditLog, Document
    from .services import TELEGRAM_FILE_LIMIT, build_zip, file_basename, zip_filename

    sender = User.objects.filter(pk=sender_id).first()
    recipient = User.objects.filter(pk=recipient_id, is_active=True).first()
    if sender is None or recipient is None or not recipient.telegram_chat_id:
        return False
    documents = list(
        Document.objects.filter(pk__in=document_ids, project__in=visible_projects_for(sender))
        .exclude(file="").exclude(file__isnull=True)
        .select_related("project", "section__sub_object__parent", "section__discipline")
    )
    if not documents:
        return False

    def fail(reason):
        notify_user(sender, NotificationType.DOCUMENT, _("Files were not sent to Telegram"), reason)
        return False

    caption = _("From %(sender)s: %(count)s file(s)") % {"sender": sender.get_short_name(), "count": len(documents)}
    if len(documents) == 1:
        document = documents[0]
        if document.file_size > TELEGRAM_FILE_LIMIT:
            return fail(_("The file is larger than 50 MB, Telegram does not accept it. Download it from the platform."))
        try:
            handle = document.file.open("rb")
        except FileNotFoundError:
            return fail(_("The file was not found in storage."))
        with handle:
            ok = send_document(recipient.telegram_chat_id, handle, file_basename(document), f"{caption}\n{document.name}")
        sent = documents
    else:
        archive, sent = build_zip(documents)
        with archive:
            archive.seek(0, 2)
            size = archive.tell()
            archive.seek(0)
            if size > TELEGRAM_FILE_LIMIT:
                return fail(_("The ZIP archive is larger than 50 MB, Telegram does not accept it. Download the ZIP from the platform."))
            ok = send_document(recipient.telegram_chat_id, archive, zip_filename(sent), caption)
    if not ok:
        return fail(_("Telegram did not accept the file. Check that the recipient has not blocked the bot."))
    for document in sent:
        AuditLog.log(obj=document, action="sent_telegram", user=sender, details={"to": str(recipient.pk)})
    return True
