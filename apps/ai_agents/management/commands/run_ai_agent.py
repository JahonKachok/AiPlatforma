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
            self.stdout.write(self.style.ERROR("ANTHROPIC_API_KEY o'rnatilmagan."))
            self.stdout.write(
                "Kalitni https://console.anthropic.com dan oling va .env fayliga qo'shing:\n"
                "  ANTHROPIC_API_KEY=sk-ant-..."
            )
            return

        context = services.collect_deadline_context()
        if context is None:
            self.stdout.write(self.style.SUCCESS("Kechikkan yoki muddati yaqin vazifalar yo'q — hisobot kerak emas."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Claude'ga yuborilayotgan kontekst:"))
        self.stdout.write(context)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Claude javobi:"))

        report = services.ask_claude(services.DEADLINE_AGENT_SYSTEM, context)
        if not report:
            self.stdout.write(self.style.WARNING("Claude bo'sh javob qaytardi."))
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
