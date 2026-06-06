"""One-off script that fills the database with realistic example data
for local development / demos. Safe to re-run: skips users that already exist
by email, and only seeds projects/tasks/etc. when none exist yet.

Run with:  python seed_data.py
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine, Base
from app.models import user as user_models, project as project_models, task as task_models
from app.models import document as document_models, finance as finance_models, request_model as request_models
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStage, ProjectStatus, Section, SubObject, SectionStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskComment
from app.models.document import Document, DocumentStatus, ApprovalStage, ApprovalStatus
from app.models.finance import FinancialRecord, RecordType, RecordStatus
from app.models.request_model import Request, RequestType, RequestStatus, RequestPriority, RequestComment
from app.utils.security import hash_password

now = datetime.utcnow()


def days(n):
    return now + timedelta(days=n)


SEED_USERS = [
    dict(email="manager@platform.uz", full_name="Bobur Rashidov", role=UserRole.manager, department="Boshqaruv", phone="+998 91 234 56 78"),
    dict(email="gip1@platform.uz", full_name="Farrux Usmonov", role=UserRole.gip, department="Loyihalash", phone="+998 93 345 67 89"),
    dict(email="gip2@platform.uz", full_name="Zafar Nazarov", role=UserRole.gip, department="Loyihalash", phone="+998 94 456 78 90"),
    dict(email="designer1@platform.uz", full_name="Malika Yusupova", role=UserRole.designer, department="Arxitektura", phone="+998 95 567 89 01"),
    dict(email="designer2@platform.uz", full_name="Sanjar Ahmedov", role=UserRole.designer, department="Konstruksiyalar", phone="+998 97 678 90 12"),
    dict(email="reviewer@platform.uz", full_name="Nilufar Hasanova", role=UserRole.reviewer, department="Nazorat", phone="+998 98 789 01 23"),
    dict(email="client1@platform.uz", full_name="Kamol Ishmatov", role=UserRole.client, department=None, phone="+998 99 890 12 34"),
]

SEED_PROJECTS = [
    dict(
        name='ЖК "Yangi ufq"', description="12 qavatli turar-joy majmuasi, 3 ta blok",
        client_name='"Ufq Qurilish" MChJ', client_contact="+998 71 200 10 10",
        address="Toshkent sh., Yunusobod tumani", stage=ProjectStage.working_docs, status=ProjectStatus.active,
        start_date=days(-120), deadline=days(160), budget=4_500_000_000, paid_amount=1_800_000_000,
    ),
    dict(
        name='БЦ "Silk Tower"', description="22 qavatli biznes-markaz, ofis va savdo maydonchalari",
        client_name="Silk Group LLC", client_contact="+998 71 200 20 20",
        address="Toshkent sh., Mirzo Ulug'bek tumani", stage=ProjectStage.expertise, status=ProjectStatus.active,
        start_date=days(-200), deadline=days(90), budget=8_200_000_000, paid_amount=5_100_000_000,
    ),
    dict(
        name='Savdo markazi "Mega Mall"', description="Yopiq savdo-ko'ngilochar majmua",
        client_name="Mega Invest", client_contact="+998 71 200 30 30",
        address="Samarqand sh., Registon ko'chasi", stage=ProjectStage.preliminary, status=ProjectStatus.active,
        start_date=days(-40), deadline=days(260), budget=6_000_000_000, paid_amount=900_000_000,
    ),
    dict(
        name="45-maktab binosi", description="Zamonaviy maktab binosini qurish loyihasi",
        client_name="Xalq ta'limi vazirligi", client_contact="+998 71 200 40 40",
        address="Farg'ona viloyati, Qo'qon shahri", stage=ProjectStage.concept, status=ProjectStatus.on_hold,
        start_date=days(-10), deadline=days(300), budget=2_300_000_000, paid_amount=0,
    ),
]

SEED_TASKS = [
    # (project_idx, title, description, assignee_email, status, priority, deadline_offset)
    (0, "Fasad arxitekturasini ishlab chiqish", "Korpus A fasadi uchun arxitektura yechimlari", "designer1@platform.uz", TaskStatus.in_progress, TaskPriority.high, 7),
    (0, "Poydevor konstruksiyasini hisoblash", "Korpus B poydevori uchun yuk hisob-kitoblari", "designer2@platform.uz", TaskStatus.review, TaskPriority.high, 3),
    (0, "Smetani yangilash", "Material narxlari bo'yicha smetani qayta ko'rib chiqish", "manager@platform.uz", TaskStatus.new, TaskPriority.medium, 14),
    (1, "Texnik topshiriqni tasdiqlash", "Mijoz bilan texnik topshiriqni kelishish", "gip1@platform.uz", TaskStatus.completed, TaskPriority.medium, -5),
    (1, "Muhandislik tarmoqlari chizmalari", "Shamollatish va konditsioner tizimlari chizmalari", "designer2@platform.uz", TaskStatus.in_progress, TaskPriority.critical, 5),
    (1, "Ekspertiza uchun hujjatlarni tayyorlash", "Davlat ekspertizasiga topshiriladigan paket", "gip2@platform.uz", TaskStatus.revision, TaskPriority.high, 2),
    (2, "Bosh reja konseptini ishlab chiqish", "Savdo markazi uchastkasining bosh rejasi", "designer1@platform.uz", TaskStatus.new, TaskPriority.medium, 20),
    (2, "Avtoturargoh sig'imini hisoblash", "Yer osti avtoturargoh joylari soni va o'lchamlari", "designer2@platform.uz", TaskStatus.new, TaskPriority.low, 25),
    (3, "Ish loyihasi uchun byudjetni baholash", "Maktab binosi uchun dastlabki byudjet hisob-kitobi", "manager@platform.uz", TaskStatus.new, TaskPriority.medium, 30),
]

SEED_DOCUMENTS = [
    # (project_idx, name, doc_type, status, uploader_email, reviewer_email)
    (0, "AR-001_Fasadlar_KorpusA_v2.pdf", "PDF", DocumentStatus.review, "designer1@platform.uz", "gip1@platform.uz"),
    (0, "Smeta_ЖК_YangiUfq.xlsx", "XLSX", DocumentStatus.approved, "manager@platform.uz", "gip1@platform.uz"),
    (1, "TZ_SilkTower_v3.docx", "DOCX", DocumentStatus.draft, "gip2@platform.uz", "manager@platform.uz"),
    (1, "KR-014_Konstruksiya_sxemasi.dwg", "DWG", DocumentStatus.rejected, "designer2@platform.uz", "reviewer@platform.uz"),
    (2, "Bosh_reja_MegaMall_v1.pdf", "PDF", DocumentStatus.review, "designer1@platform.uz", "gip2@platform.uz"),
]

SEED_FINANCIAL_RECORDS = [
    # (project_idx, type, amount, description, category, status)
    (0, RecordType.income, 900_000_000, "Mijozdan 2-bosqich to'lovi", "Shartnoma to'lovi", RecordStatus.confirmed),
    (0, RecordType.expense, 120_000_000, "Qurilish materiallari xaridi", "Materiallar", RecordStatus.confirmed),
    (1, RecordType.advance, 250_000_000, "Pудратчиga avans to'lovi", "Avans", RecordStatus.pending),
    (1, RecordType.income, 1_500_000_000, "Mijozdan asosiy to'lov", "Shartnoma to'lovi", RecordStatus.confirmed),
    (2, RecordType.expense, 60_000_000, "Geodezik tadqiqotlar", "Xizmatlar", RecordStatus.pending),
    (3, RecordType.payment, 35_000_000, "Loyihalash xizmatlari uchun to'lov", "Xizmatlar", RecordStatus.cancelled),
]

SEED_REQUESTS = [
    # (project_idx, title, description, type, creator_email, assignee_email, status, priority, comment)
    (0, "Fasad rangini o'zgartirish so'rovi", "Mijoz fasad rangini iliqroq tusga almashtirishni so'ramoqda",
     RequestType.change, "client1@platform.uz", "gip1@platform.uz", RequestStatus.in_progress, RequestPriority.medium,
     "Ranglar palitrasi bo'yicha 3 ta variant tayyorlanmoqda."),
    (1, "Konstruktiv yechim bo'yicha aniqlik", "8-qavat yuk ko'tarish hisobida farqlar aniqlandi",
     RequestType.clarification, "reviewer@platform.uz", "designer2@platform.uz", RequestStatus.open, RequestPriority.high, None),
    (2, "Qo'shimcha kirish joyini ko'rib chiqish", "Mijoz binoning shimoliy tomonidan qo'shimcha kirish so'ramoqda",
     RequestType.improvement, "client1@platform.uz", "gip2@platform.uz", RequestStatus.resolved, RequestPriority.low,
     "Qo'shimcha kirish bosh rejaga kiritildi."),
]


async def get_or_create_user(db: AsyncSession, data: dict) -> User:
    result = await db.execute(select(User).where(User.email == data["email"]))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    u = User(
        email=data["email"], full_name=data["full_name"], role=data["role"],
        department=data["department"], phone=data["phone"],
        password_hash=hash_password("password123"), is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        users_by_email = {}
        for data in SEED_USERS:
            users_by_email[data["email"]] = await get_or_create_user(db, data)
        await db.commit()

        admin_result = await db.execute(select(User).where(User.email == "admin@platform.uz"))
        admin = admin_result.scalar_one()
        users_by_email["admin@platform.uz"] = admin

        # Remove leftover Playwright verification artifacts (names like "Test Project 1234567890")
        stale = (await db.execute(select(Project).where(Project.name.like("Test Project %")))).scalars().all()
        for p in stale:
            await db.delete(p)
        if stale:
            await db.commit()
            print(f"{len(stale)} ta sinov yozuvi (Test Project ...) tozalandi.")

        existing_projects = (await db.execute(select(Project))).scalars().all()
        if existing_projects:
            print(f"{len(existing_projects)} ta loyiha allaqachon mavjud — loyihalarni qayta yaratish o'tkazib yuborildi.")
            print("Foydalanuvchilar tayyor:", ", ".join(users_by_email))
            return

        projects = []
        for p in SEED_PROJECTS:
            project = Project(created_by=admin.id, **p)
            db.add(project)
            projects.append(project)
        await db.flush()

        # A couple of sections per project for realism
        for idx, project in enumerate(projects[:2]):
            db.add(Section(project_id=project.id, name="Arxitektura bo'limi", code="AR", gip_id=users_by_email["gip1@platform.uz"].id, status=SectionStatus.in_progress))
            db.add(Section(project_id=project.id, name="Konstruksiya bo'limi", code="KR", gip_id=users_by_email["gip2@platform.uz"].id, status=SectionStatus.in_progress))
            db.add(SubObject(project_id=project.id, name=f"{idx + 1}-korpus", gip_id=users_by_email["gip1@platform.uz"].id, status=SectionStatus.in_progress))

        for project_idx, title, description, assignee_email, status, priority, deadline_offset in SEED_TASKS:
            task = Task(
                title=title, description=description, project_id=projects[project_idx].id,
                assignee_id=users_by_email[assignee_email].id, creator_id=admin.id,
                status=status, priority=priority, deadline=days(deadline_offset),
            )
            db.add(task)
            await db.flush()
            db.add(TaskComment(task_id=task.id, user_id=users_by_email[assignee_email].id, content="Ishni boshladim, birinchi natijalar shu hafta oxirida tayyor bo'ladi."))

        for project_idx, name, doc_type, status, uploader_email, reviewer_email in SEED_DOCUMENTS:
            document = Document(
                name=name, doc_type=doc_type, project_id=projects[project_idx].id,
                uploaded_by=users_by_email[uploader_email].id, version="1.0", status=status,
                file_size=1_500_000 + project_idx * 250_000, mime_type="application/octet-stream",
            )
            db.add(document)
            await db.flush()
            stage_status = (
                ApprovalStatus.approved if status == DocumentStatus.approved else
                ApprovalStatus.rejected if status == DocumentStatus.rejected else
                ApprovalStatus.pending
            )
            db.add(ApprovalStage(
                document_id=document.id, stage_order=1, stage_name="Ichki ko'rib chiqish",
                reviewer_id=users_by_email[reviewer_email].id, status=stage_status,
                comment="Diqqat bilan tekshirildi." if stage_status != ApprovalStatus.pending else None,
                reviewed_at=now if stage_status != ApprovalStatus.pending else None,
            ))

        for project_idx, rtype, amount, description, category, status in SEED_FINANCIAL_RECORDS:
            db.add(FinancialRecord(
                project_id=projects[project_idx].id, type=rtype, amount=amount, currency="UZS",
                description=description, category=category, date=days(-(amount % 30)),
                status=status, created_by=users_by_email["manager@platform.uz"].id,
            ))

        for project_idx, title, description, rtype, creator_email, assignee_email, status, priority, comment in SEED_REQUESTS:
            req = Request(
                title=title, description=description, type=rtype, project_id=projects[project_idx].id,
                created_by=users_by_email[creator_email].id, assignee_id=users_by_email[assignee_email].id,
                status=status, priority=priority,
            )
            db.add(req)
            await db.flush()
            if comment:
                db.add(RequestComment(request_id=req.id, user_id=users_by_email[assignee_email].id, content=comment))

        await db.commit()
        print(f"Tayyor: {len(SEED_USERS)} foydalanuvchi, {len(SEED_PROJECTS)} loyiha, {len(SEED_TASKS)} vazifa, "
              f"{len(SEED_DOCUMENTS)} hujjat, {len(SEED_FINANCIAL_RECORDS)} moliyaviy yozuv, {len(SEED_REQUESTS)} so'rov qo'shildi.")
        print("Yangi foydalanuvchilar paroli: password123")


if __name__ == "__main__":
    asyncio.run(seed())
