import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @property
    def enabled(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM)

    def _send_sync(self, to_email: str, subject: str, body_html: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        try:
            if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
            return True
        finally:
            server.quit()

    async def send_email(self, to_email: str, subject: str, body_html: str) -> bool:
        if not self.enabled or not to_email:
            return False
        try:
            return await asyncio.to_thread(self._send_sync, to_email, subject, body_html)
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_notification_email(self, to_email: str, title: str, message: str, link: str | None = None) -> bool:
        link_html = ""
        if link:
            url = f"{settings.FRONTEND_URL.rstrip('/')}{link}"
            link_html = f'<p><a href="{url}">Platformada ochish</a></p>'
        body = (
            f"<html><body style='font-family:Arial,sans-serif'>"
            f"<h3>{title}</h3>"
            f"<p>{message}</p>"
            f"{link_html}"
            f"<hr><small>AiPlatforma — loyihalash boshqaruv platformasi</small>"
            f"</body></html>"
        )
        return await self.send_email(to_email, f"AiPlatforma: {title}", body)


email_service = EmailService()
