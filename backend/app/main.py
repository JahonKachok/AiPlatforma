import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine, Base, get_db
from app.websocket.manager import manager
from app.services.telegram_service import telegram_service
from app.services.google_drive_service import google_drive_service
from app.utils.security import verify_token
from app.models import user, project, task, document, finance, notification, request_model

from app.routers import auth, users, projects, tasks, documents, approvals, finance as finance_router
from app.routers import notifications, requests, reports

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
    logger.info("Database tables created/verified")

    await telegram_service.initialize()
    google_drive_service.initialize()

    await create_default_admin()

    yield

    logger.info("Shutting down AiPlatforma API...")
    await engine.dispose()


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
