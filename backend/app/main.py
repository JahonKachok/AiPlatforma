import os
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base, get_db
from app.websocket.manager import manager
from app.services.telegram_service import telegram_service
from app.services.google_drive_service import google_drive_service
from app.services.scheduler import deadline_watcher
from app.utils.security import verify_token
from app.models import user, project, task, document, finance, notification, request_model, template

from app.routers import auth, users, projects, tasks, documents, approvals, finance as finance_router
from app.routers import notifications, requests, reports, templates, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AiPlatforma API...")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "tasks"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "contracts"), exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema_upgrades()
    logger.info("Database tables created/verified")

    await telegram_service.initialize()
    google_drive_service.initialize()

    await create_default_admin()
    await create_default_templates()

    watcher_task = asyncio.create_task(deadline_watcher())
    logger.info("Deadline watcher started")

    yield

    logger.info("Shutting down AiPlatforma API...")
    watcher_task.cancel()
    await engine.dispose()


async def ensure_schema_upgrades():
    """Add columns introduced after initial release (SQLite has no auto-migration)."""
    upgrades = [
        ("documents", "deadline", "DATETIME"),
        ("project_members", "can_edit", "BOOLEAN DEFAULT 1"),
        ("project_members", "expires_at", "DATETIME"),
    ]
    async with engine.begin() as conn:
        for table, column, ddl_type in upgrades:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            existing = {row[1] for row in result.fetchall()}
            if column not in existing:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
                logger.info(f"Schema upgrade: added {table}.{column}")


async def create_default_admin():
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.utils.security import hash_password

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@platform.uz"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                email="admin@platform.uz",
                full_name="Administrator",
                password_hash=hash_password("admin123"),
                role=UserRole.admin,
                is_active=True,
                department="IT",
            )
            db.add(admin)
            await db.commit()
            logger.info("Default admin user created: admin@platform.uz / admin123")


async def create_default_templates():
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.models.template import DocumentTemplate, TemplateType

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(DocumentTemplate).limit(1))
        if existing.scalar_one_or_none():
            return

        admin_result = await db.execute(select(User).where(User.role == UserRole.admin).limit(1))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            return

        defaults = [
            DocumentTemplate(
                name="Loyihalash shartnomasi",
                template_type=TemplateType.contract,
                description="Buyurtmachi bilan loyihalash ishlari shartnomasi",
                content=(
                    "SHARTNOMA № {{contract_number}}\n"
                    "Sana: {{today}}\n\n"
                    "Buyurtmachi: {{client_name}}\n"
                    "Aloqa: {{client_contact}}\n\n"
                    "Loyiha: {{project_name}}\n"
                    "Obyekt manzili: {{address}}\n\n"
                    "1. SHARTNOMA PREDMETI\n"
                    "Ijrochi {{project_name}} obyekti bo'yicha loyihalash ishlarini bajarish majburiyatini oladi.\n\n"
                    "2. SHARTNOMA SUMMASI\n"
                    "Ishlarning umumiy qiymati: {{amount}} so'm.\n\n"
                    "3. MUDDATLAR\n"
                    "Ishlarni boshlash: {{start_date}}\n"
                    "Ishlarni tugatish: {{deadline}}\n\n"
                    "4. TOMONLAR IMZOLARI\n"
                    "Buyurtmachi: ____________    Ijrochi: ____________"
                ),
                created_by=admin.id,
            ),
            DocumentTemplate(
                name="Bajarilgan ishlar dalolatnomasi",
                template_type=TemplateType.act,
                description="Bajarilgan ishlar uchun qabul-topshirish dalolatnomasi",
                content=(
                    "DALOLATNOMA\n"
                    "Sana: {{today}}\n\n"
                    "Loyiha: {{project_name}}\n"
                    "Buyurtmachi: {{client_name}}\n"
                    "Obyekt manzili: {{address}}\n\n"
                    "Shartnoma bo'yicha bajarilgan ishlar qiymati: {{amount}} so'm.\n"
                    "To'langan summa: {{paid_amount}} so'm.\n\n"
                    "Ishlar to'liq hajmda bajarildi. Tomonlar bir-biriga da'vo qilmaydi.\n\n"
                    "Buyurtmachi: ____________    Ijrochi: ____________"
                ),
                created_by=admin.id,
            ),
            DocumentTemplate(
                name="Hisob-faktura",
                template_type=TemplateType.invoice,
                description="To'lov uchun hisob",
                content=(
                    "HISOB № {{contract_number}}\n"
                    "Sana: {{today}}\n\n"
                    "To'lovchi: {{client_name}}\n"
                    "Loyiha: {{project_name}}\n\n"
                    "To'lov summasi: {{amount}} so'm\n"
                    "To'lov asosi: {{project_name}} loyihasi bo'yicha loyihalash xizmatlari\n\n"
                    "To'lov muddati: 5 (besh) bank kuni ichida."
                ),
                created_by=admin.id,
            ),
            DocumentTemplate(
                name="Ijrochi bilan shartnoma",
                template_type=TemplateType.contract,
                description="Xodim/loyihachi bilan ish shartnomasi",
                content=(
                    "IJROCHI SHARTNOMASI\n"
                    "Sana: {{today}}\n\n"
                    "Ijrochi: {{employee_name}}\n"
                    "Email: {{employee_email}}\n"
                    "Telefon: {{employee_phone}}\n\n"
                    "Loyiha: {{project_name}}\n"
                    "Obyekt manzili: {{address}}\n\n"
                    "Shartnoma summasi: {{employee_contract_amount}} so'm\n"
                    "Avans: {{employee_advance}} so'm\n"
                    "To'langan: {{employee_paid}} so'm\n"
                    "Qoldiq: {{employee_balance}} so'm\n\n"
                    "Ish tugash muddati: {{deadline}}\n\n"
                    "Buyurtmachi: ____________    Ijrochi: ____________"
                ),
                created_by=admin.id,
            ),
        ]
        db.add_all(defaults)
        await db.commit()
        logger.info(f"Created {len(defaults)} default document templates")


app = FastAPI(
    title="AiPlatforma API",
    description="GASTEC construction company project management platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(finance_router.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(requests.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    payload = verify_token(token)
    if not payload or payload.get("sub") != user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_to_user(user_id, {"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# Serve the built frontend (production single-server deployment), if present.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    logger.info(f"Serving frontend from {FRONTEND_DIST}")
