import json
import re
from unittest import mock

from asgiref.sync import async_to_sync
from django.core.management import call_command
from django.test import TestCase, override_settings
from telegram import Update
from telegram.ext import Application
from telegram.request import BaseRequest

from apps.accounts.models import User
from apps.projects.models import Project

from .models import TelegramLinkToken
from .texts import LANGS, T

CHAT = 777001


def html_ok(text):
    """Telegram'ning HTML parse_mode qoidalarining soddalashtirilgani:
    ruxsat etilmagan teg yoki yalang'och "&" bo'lsa xabar rad etiladi."""
    if any(m.group(1) not in ("b", "i", "a", "code", "pre")
           for m in re.finditer(r"</?([^>\s]*)", text)):
        return False
    return not re.search(r"&(?!(lt|gt|amp|quot);)", text)


class FakeTelegram(BaseRequest):
    """Tarmoqsiz Telegram API: yuborilgan xabarlarni yozib boradi va HTML
    xato bo'lsa haqiqiy API kabi 400 qaytaradi."""

    def __init__(self):
        super().__init__()
        self.sent = []

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **kwargs):
        if "/file/bot" in url:
            return 200, b"%PDF-1.4 test"
        endpoint = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        if endpoint == "getMe":
            result = {"id": 1, "is_bot": True, "first_name": "Bot", "username": "bot"}
        elif endpoint == "getFile":
            result = {"file_id": "F", "file_unique_id": "U", "file_path": "documents/f.pdf"}
        elif endpoint in ("answerCallbackQuery", "sendChatAction", "setMyCommands"):
            result = True
        elif params.get("parse_mode") == "HTML" and not html_ok(params.get("text", "")):
            return 400, json.dumps({"ok": False, "error_code": 400,
                                    "description": "Bad Request: can't parse entities"}).encode()
        else:
            self.sent.append(params.get("text", ""))
            result = {"message_id": len(self.sent), "date": 0,
                      "chat": {"id": CHAT, "type": "private"}}
        return 200, json.dumps({"ok": True, "result": result}).encode()


@override_settings(TELEGRAM_BOT_TOKEN="1:TEST")
class BotHandlerTests(TestCase):
    def setUp(self):
        self.api = FakeTelegram()
        original_builder = Application.builder
        captured = {}

        def builder():
            return original_builder().request(self.api).get_updates_request(FakeTelegram())

        with mock.patch.object(Application, "builder", staticmethod(builder)), \
             mock.patch.object(Application, "run_polling",
                               lambda app, *a, **k: captured.setdefault("app", app)):
            call_command("run_telegram_bot", stdout=mock.MagicMock())
        self.app = captured["app"]
        self.errors = []

        async def on_error(update, context):
            self.errors.append(context.error)

        self.app.add_error_handler(on_error)
        async_to_sync(self.app.initialize)()
        self.update_id = 0
        self.user = User.objects.create_user(email="u@example.com", password="x",
                                             full_name="Ali <Vali> & Co",
                                             role=User.Role.ADMIN)

    def send(self, text=None, **extra):
        self.update_id += 1
        message = {"message_id": self.update_id, "date": 0,
                   "chat": {"id": CHAT, "type": "private"},
                   "from": {"id": CHAT, "is_bot": False, "first_name": "T"}, **extra}
        if text is not None:
            message["text"] = text
            if text.startswith("/"):
                message["entities"] = [{"type": "bot_command", "offset": 0,
                                        "length": len(text.split()[0])}]
        update = Update.de_json({"update_id": self.update_id, "message": message}, self.app.bot)
        async_to_sync(self.app.process_update)(update)

    def press(self, data):
        self.update_id += 1
        update = Update.de_json({"update_id": self.update_id, "callback_query": {
            "id": "q", "chat_instance": "c", "data": data,
            "from": {"id": CHAT, "is_bot": False, "first_name": "T"},
            "message": {"message_id": 1, "date": 0, "chat": {"id": CHAT, "type": "private"}},
        }}, self.app.bot)
        async_to_sync(self.app.process_update)(update)

    def link(self, user):
        self.send(f"/start link_{TelegramLinkToken.issue(user).token}")

    def test_link_escapes_name_and_token_is_single_use(self):
        token = TelegramLinkToken.issue(self.user).token
        self.send(f"/start link_{token}")
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, str(CHAT))
        self.assertIn("Ali &lt;Vali&gt; &amp; Co", self.api.sent[-1])
        self.send(f"/link {token}")
        self.assertIn("yaroqsiz", self.api.sent[-1])
        self.assertEqual(self.errors, [])

    def test_linking_second_account_unlinks_the_first(self):
        other = User.objects.create_user(email="o@example.com", password="x", full_name="Other")
        self.link(self.user)
        self.link(other)
        self.assertEqual(
            list(User.objects.filter(telegram_chat_id=str(CHAT)).values_list("email", flat=True)),
            ["o@example.com"],
        )

    def test_upload_with_html_caption_is_saved_and_confirmed(self):
        Project.objects.create(name="Bino <A>", created_by=self.user)
        self.link(self.user)
        self.send(document={"file_id": "F", "file_unique_id": "U", "file_name": "smeta.pdf"},
                  caption="Smeta <v2> & B")
        project = Project.objects.get()
        self.press(f"tgdoc:{project.pk}")
        self.assertEqual(self.errors, [])
        self.assertIn("Smeta &lt;v2&gt; &amp; B", self.api.sent[-1])
        self.assertTrue(project.documents.filter(name="Smeta <v2> & B").exists())

    def test_disallowed_file_type_is_rejected_before_choosing_project(self):
        Project.objects.create(name="P", created_by=self.user)
        self.link(self.user)
        self.send(document={"file_id": "F", "file_unique_id": "U", "file_name": "x.html"},
                  caption="x")
        self.assertIn("pdf", self.api.sent[-1])
        self.assertNotIn("Qaysi loyihaga", self.api.sent[-1])


class NotificationTextTests(TestCase):
    def test_telegram_notification_is_html_escaped(self):
        from apps.notifications.tasks import send_notification_telegram

        user = User.objects.create_user(email="n@example.com", password="x", full_name="N",
                                        telegram_chat_id="1")
        with mock.patch("apps.telegram_bot.services.send_message") as send:
            send_notification_telegram(str(user.pk), "Vazifa <1>", "A & B")
        self.assertEqual(send.call_args.args[1], "<b>Vazifa &lt;1&gt;</b>\nA &amp; B")

    def test_every_bot_text_has_all_languages_with_same_placeholders(self):
        for key, entry in T.items():
            fields = {lang: set(re.findall(r"{(\w+)}", entry[lang])) for lang in LANGS}
            self.assertEqual(len(set(map(frozenset, fields.values()))), 1, key)
