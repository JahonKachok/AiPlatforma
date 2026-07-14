from django.core.management.base import BaseCommand

from apps.ai_agents import services


class Command(BaseCommand):
    help = "AI muddat agentini qo'lda ishga tushiradi (sinov uchun). Standart rejim: faqat chop etadi; --send bilan bildirishnomalar ham yuboriladi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send",
            action="store_true",
            help="Hisobotni chop etish bilan birga admin/rahbarlarga bildirishnoma sifatida yuborish.",
        )

    def handle(self, *args, **options):
        if not services.is_configured():
            self.stdout.write(self.style.ERROR("AI kaliti o'rnatilmagan."))
            self.stdout.write(
                ".env fayliga quyidagilardan birini qo'shing:\n"
                "  GEMINI_API_KEY=AIza...      (bepul: https://aistudio.google.com)\n"
                "  ANTHROPIC_API_KEY=sk-ant... (https://console.anthropic.com)"
            )
            return

        context = services.collect_deadline_context()
        if context is None:
            self.stdout.write(self.style.SUCCESS("Kechikkan yoki muddati yaqin vazifalar yo'q — hisobot kerak emas."))
            return

        provider = services.get_provider()
        self.stdout.write(self.style.MIGRATE_HEADING(f"AI'ga ({provider}) yuborilayotgan kontekst:"))
        self.stdout.write(context)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("AI javobi:"))

        report = services.ask_ai(services.DEADLINE_AGENT_SYSTEM, context, agent="deadline")
        if not report:
            self.stdout.write(self.style.WARNING("AI bo'sh javob qaytardi."))
            return
        self.stdout.write(report)

        if options["send"]:
            from apps.accounts.models import User
            from apps.notifications.services import notify_user

            recipients = User.objects.filter(
                role__in=[User.Role.ADMIN, User.Role.MANAGER], is_active=True
            )
            for user in recipients:
                notify_user(user, "deadline", "AI: Muddatlar bo'yicha kunlik hisobot", report, link="/tasks/")
            self.stdout.write(self.style.SUCCESS(f"\n{recipients.count()} ta foydalanuvchiga yuborildi."))
