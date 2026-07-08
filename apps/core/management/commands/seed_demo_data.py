"""Idempotent demo-data seeder for local development, modeled on the
previous FastAPI app's seed_data.py. Safe to re-run: skips users that
already exist by email, and only seeds projects/tasks/etc. when none exist.

    python manage.py seed_demo_data
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.documents.models import ApprovalStage, ApprovalStatus, Document, DocumentStatus
from apps.finance.models import FinancialRecord, RecordStatus, RecordType
from apps.projects.models import Project, ProjectMember, Section, SectionStatus, SubObject
from apps.requests_app.models import Request, RequestComment, RequestPriority, RequestStatus, RequestType
from apps.tasks.models import Task, TaskComment

TODAY = date.today()


def days(n):
    return TODAY + timedelta(days=n)


SEED_USERS = [
    dict(email="manager@platform.uz", full_name="Bobur Rashidov", role=User.Role.MANAGER, department="Boshqaruv", phone="+998 91 234 56 78"),
    dict(email="gip1@platform.uz", full_name="Farrux Usmonov", role=User.Role.GIP, department="Loyihalash", phone="+998 93 345 67 89"),
    dict(email="gip2@platform.uz", full_name="Zafar Nazarov", role=User.Role.GIP, department="Loyihalash", phone="+998 94 456 78 90"),
    dict(email="designer1@platform.uz", full_name="Malika Yusupova", role=User.Role.DESIGNER, department="Arxitektura", phone="+998 95 567 89 01"),
    dict(email="designer2@platform.uz", full_name="Sanjar Ahmedov", role=User.Role.DESIGNER, department="Konstruksiyalar", phone="+998 97 678 90 12"),
    dict(email="reviewer@platform.uz", full_name="Nilufar Hasanova", role=User.Role.REVIEWER, department="Nazorat", phone="+998 98 789 01 23"),
    dict(email="client1@platform.uz", full_name="Kamol Ishmatov", role=User.Role.CLIENT, department=None, phone="+998 99 890 12 34"),
]

SEED_PROJECTS = [
    dict(
        name='ЖК "Yangi ufq"', description="12 qavatli turar-joy majmuasi, 3 ta blok",
        client_name='"Ufq Qurilish" MChJ', client_contact="+998 71 200 10 10",
        address="Toshkent sh., Yunusobod tumani", stage=Project.Stage.WORKING_DOCS, status=Project.Status.ACTIVE,
        start_date=days(-120), deadline=days(160), budget=4_500_000_000, paid_amount=1_800_000_000,
    ),
    dict(
        name='БЦ "Silk Tower"', description="22 qavatli biznes-markaz, ofis va savdo maydonchalari",
        client_name="Silk Group LLC", client_contact="+998 71 200 20 20",
        address="Toshkent sh., Mirzo Ulug'bek tumani", stage=Project.Stage.EXPERTISE, status=Project.Status.ACTIVE,
        start_date=days(-200), deadline=days(90), budget=8_200_000_000, paid_amount=5_100_000_000,
    ),
    dict(
        name='Savdo markazi "Mega Mall"', description="Yopiq savdo-ko'ngilochar majmua",
        client_name="Mega Invest", client_contact="+998 71 200 30 30",
        address="Samarqand sh., Registon ko'chasi", stage=Project.Stage.PRELIMINARY, status=Project.Status.ACTIVE,
        start_date=days(-40), deadline=days(260), budget=6_000_000_000, paid_amount=900_000_000,
    ),
    dict(
        name="45-maktab binosi", description="Zamonaviy maktab binosini qurish loyihasi",
        client_name="Xalq ta'limi vazirligi", client_contact="+998 71 200 40 40",
        address="Farg'ona viloyati, Qo'qon shahri", stage=Project.Stage.CONCEPT, status=Project.Status.ON_HOLD,
        start_date=days(-10), deadline=days(300), budget=2_300_000_000, paid_amount=0,
    ),
]

SEED_TASKS = [
    (0, "Fasad arxitekturasini ishlab chiqish", "Korpus A fasadi uchun arxitektura yechimlari", "designer1@platform.uz", Task.Status.IN_PROGRESS, Task.Priority.HIGH, 7),
    (0, "Poydevor konstruksiyasini hisoblash", "Korpus B poydevori uchun yuk hisob-kitoblari", "designer2@platform.uz", Task.Status.REVIEW, Task.Priority.HIGH, 3),
    (0, "Smetani yangilash", "Material narxlari bo'yicha smetani qayta ko'rib chiqish", "manager@platform.uz", Task.Status.NEW, Task.Priority.MEDIUM, 14),
    (1, "Texnik topshiriqni tasdiqlash", "Mijoz bilan texnik topshiriqni kelishish", "gip1@platform.uz", Task.Status.COMPLETED, Task.Priority.MEDIUM, -5),
    (1, "Muhandislik tarmoqlari chizmalari", "Shamollatish va konditsioner tizimlari chizmalari", "designer2@platform.uz", Task.Status.IN_PROGRESS, Task.Priority.CRITICAL, 5),
    (1, "Ekspertiza uchun hujjatlarni tayyorlash", "Davlat ekspertizasiga topshiriladigan paket", "gip2@platform.uz", Task.Status.REVISION, Task.Priority.HIGH, 2),
    (2, "Bosh reja konseptini ishlab chiqish", "Savdo markazi uchastkasining bosh rejasi", "designer1@platform.uz", Task.Status.NEW, Task.Priority.MEDIUM, 20),
    (2, "Avtoturargoh sig'imini hisoblash", "Yer osti avtoturargoh joylari soni va o'lchamlari", "designer2@platform.uz", Task.Status.NEW, Task.Priority.LOW, 25),
    (3, "Ish loyihasi uchun byudjetni baholash", "Maktab binosi uchun dastlabki byudjet hisob-kitobi", "manager@platform.uz", Task.Status.NEW, Task.Priority.MEDIUM, 30),
]

SEED_DOCUMENTS = [
    (0, "AR-001_Fasadlar_KorpusA_v2.pdf", "PDF", DocumentStatus.REVIEW, "designer1@platform.uz", "gip1@platform.uz"),
    (0, "Smeta_JK_YangiUfq.xlsx", "XLSX", DocumentStatus.APPROVED, "manager@platform.uz", "gip1@platform.uz"),
    (1, "TZ_SilkTower_v3.docx", "DOCX", DocumentStatus.DRAFT, "gip2@platform.uz", "manager@platform.uz"),
    (1, "KR-014_Konstruksiya_sxemasi.dwg", "DWG", DocumentStatus.REJECTED, "designer2@platform.uz", "reviewer@platform.uz"),
    (2, "Bosh_reja_MegaMall_v1.pdf", "PDF", DocumentStatus.REVIEW, "designer1@platform.uz", "gip2@platform.uz"),
]

SEED_FINANCIAL_RECORDS = [
    (0, RecordType.INCOME, 900_000_000, "Mijozdan 2-bosqich to'lovi", "Shartnoma to'lovi", RecordStatus.CONFIRMED),
    (0, RecordType.EXPENSE, 120_000_000, "Qurilish materiallari xaridi", "Materiallar", RecordStatus.CONFIRMED),
    (1, RecordType.ADVANCE, 250_000_000, "Pudratchiga avans to'lovi", "Avans", RecordStatus.PENDING),
    (1, RecordType.INCOME, 1_500_000_000, "Mijozdan asosiy to'lov", "Shartnoma to'lovi", RecordStatus.CONFIRMED),
    (2, RecordType.EXPENSE, 60_000_000, "Geodezik tadqiqotlar", "Xizmatlar", RecordStatus.PENDING),
    (3, RecordType.PAYMENT, 35_000_000, "Loyihalash xizmatlari uchun to'lov", "Xizmatlar", RecordStatus.CANCELLED),
]

SEED_REQUESTS = [
    (0, "Fasad rangini o'zgartirish so'rovi", "Mijoz fasad rangini iliqroq tusga almashtirishni so'ramoqda",
     RequestType.CHANGE, "client1@platform.uz", "gip1@platform.uz", RequestStatus.IN_PROGRESS, RequestPriority.MEDIUM,
     "Ranglar palitrasi bo'yicha 3 ta variant tayyorlanmoqda."),
    (1, "Konstruktiv yechim bo'yicha aniqlik", "8-qavat yuk ko'tarish hisobida farqlar aniqlandi",
     RequestType.CLARIFICATION, "reviewer@platform.uz", "designer2@platform.uz", RequestStatus.OPEN, RequestPriority.HIGH, None),
    (2, "Qo'shimcha kirish joyini ko'rib chiqish", "Mijoz binoning shimoliy tomonidan qo'shimcha kirish so'ramoqda",
     RequestType.IMPROVEMENT, "client1@platform.uz", "gip2@platform.uz", RequestStatus.RESOLVED, RequestPriority.LOW,
     "Qo'shimcha kirish bosh rejaga kiritildi."),
]


class Command(BaseCommand):
    help = "Seeds the database with realistic demo data for local development."

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).order_by("created_at").first()
        if not admin:
            self.stderr.write(self.style.ERROR(
                "No superuser found. Create one first: python manage.py createsuperuser"
            ))
            return

        users_by_email = {"admin@platform.uz": admin}
        for data in SEED_USERS:
            user, created = User.objects.get_or_create(email=data["email"], defaults={
                **{k: v for k, v in data.items() if k != "email"},
                "is_active": True,
            })
            if created:
                user.set_password("password123")
                user.save(update_fields=["password"])
            users_by_email[data["email"]] = user

        if Project.objects.exists():
            self.stdout.write(self.style.WARNING(
                f"{Project.objects.count()} project(s) already exist — skipping project/task/document seeding."
            ))
            self.stdout.write("Users ready: " + ", ".join(users_by_email))
            return

        projects = [Project.objects.create(created_by=admin, **p) for p in SEED_PROJECTS]

        # Every seeded staff member can see every seeded project (small-company
        # demo data) — otherwise non-admin/manager logins would see an empty
        # projects list despite having tasks/documents assigned to them.
        for project in projects:
            for user in users_by_email.values():
                if user.role != User.Role.CLIENT:
                    ProjectMember.objects.get_or_create(project=project, user=user)

        for idx, project in enumerate(projects[:2]):
            Section.objects.create(project=project, name="Arxitektura bo'limi", code="AR", gip=users_by_email["gip1@platform.uz"], status=SectionStatus.IN_PROGRESS)
            Section.objects.create(project=project, name="Konstruksiya bo'limi", code="KR", gip=users_by_email["gip2@platform.uz"], status=SectionStatus.IN_PROGRESS)
            SubObject.objects.create(project=project, name=f"{idx + 1}-korpus", gip=users_by_email["gip1@platform.uz"], status=SectionStatus.IN_PROGRESS)

        for project_idx, title, description, assignee_email, status, priority, deadline_offset in SEED_TASKS:
            task = Task.objects.create(
                title=title, description=description, project=projects[project_idx],
                assignee=users_by_email[assignee_email], creator=admin,
                status=status, priority=priority, deadline=days(deadline_offset),
            )
            TaskComment.objects.create(
                task=task, user=users_by_email[assignee_email],
                content="Ishni boshladim, birinchi natijalar shu hafta oxirida tayyor bo'ladi.",
            )

        for project_idx, name, doc_type, status, uploader_email, reviewer_email in SEED_DOCUMENTS:
            document = Document.objects.create(
                name=name, doc_type=doc_type, project=projects[project_idx],
                uploaded_by=users_by_email[uploader_email], version="1.0", status=status,
                file_size=1_500_000 + project_idx * 250_000, mime_type="application/octet-stream",
            )
            stage_status = (
                ApprovalStatus.APPROVED if status == DocumentStatus.APPROVED else
                ApprovalStatus.REJECTED if status == DocumentStatus.REJECTED else
                ApprovalStatus.PENDING
            )
            ApprovalStage.objects.create(
                document=document, stage_order=1, stage_name="Ichki ko'rib chiqish",
                reviewer=users_by_email[reviewer_email], status=stage_status,
                comment="Diqqat bilan tekshirildi." if stage_status != ApprovalStatus.PENDING else None,
                reviewed_at=timezone.now() if stage_status != ApprovalStatus.PENDING else None,
            )

        for project_idx, rtype, amount, description, category, status in SEED_FINANCIAL_RECORDS:
            FinancialRecord.objects.create(
                project=projects[project_idx], type=rtype, amount=amount, currency="UZS",
                description=description, category=category, date=days(-(amount % 30)),
                status=status, created_by=users_by_email["manager@platform.uz"],
            )

        for project_idx, title, description, rtype, creator_email, assignee_email, status, priority, comment in SEED_REQUESTS:
            req = Request.objects.create(
                title=title, description=description, type=rtype, project=projects[project_idx],
                created_by=users_by_email[creator_email], assignee=users_by_email[assignee_email],
                status=status, priority=priority,
            )
            if comment:
                RequestComment.objects.create(request=req, user=users_by_email[assignee_email], content=comment)

        self.stdout.write(self.style.SUCCESS(
            f"Done: {len(SEED_USERS)} users, {len(SEED_PROJECTS)} projects, {len(SEED_TASKS)} tasks, "
            f"{len(SEED_DOCUMENTS)} documents, {len(SEED_FINANCIAL_RECORDS)} financial records, "
            f"{len(SEED_REQUESTS)} requests added."
        ))
        self.stdout.write("New users' password: password123")
