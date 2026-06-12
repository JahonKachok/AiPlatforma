import os
import shutil
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.document import AuditLog
from app.schemas.document import AuditLogResponse
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


def _db_file_path() -> str | None:
    url = settings.DATABASE_URL
    if "sqlite" not in url:
        return None
    path = url.split("///")[-1]
    return path.lstrip("./") if not os.path.isabs(path) else path


@router.post("/backup")
async def create_backup(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.zip"
    backup_path = os.path.join(settings.BACKUP_DIR, backup_name)

    db_file = _db_file_path()
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_file and os.path.exists(db_file):
            zf.write(db_file, arcname=os.path.basename(db_file))
        if os.path.isdir(settings.UPLOAD_DIR):
            for root, _, files in os.walk(settings.UPLOAD_DIR):
                for f in files:
                    full = os.path.join(root, f)
                    zf.write(full, arcname=os.path.relpath(full, start="."))

    size = os.path.getsize(backup_path)
    return {
        "message": "Backup created",
        "filename": backup_name,
        "size": size,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    if not os.path.isdir(settings.BACKUP_DIR):
        return []
    backups = []
    for name in sorted(os.listdir(settings.BACKUP_DIR), reverse=True):
        if not name.endswith(".zip"):
            continue
        full = os.path.join(settings.BACKUP_DIR, name)
        backups.append({
            "filename": name,
            "size": os.path.getsize(full),
            "created_at": datetime.utcfromtimestamp(os.path.getmtime(full)).isoformat(),
        })
    return backups


@router.get("/backups/{filename}")
async def download_backup(
    filename: str,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    safe_name = os.path.basename(filename)
    path = os.path.join(settings.BACKUP_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(path, filename=safe_name)


@router.delete("/backups/{filename}")
async def delete_backup(
    filename: str,
    current_user: User = Depends(require_roles(UserRole.admin)),
):
    safe_name = os.path.basename(filename)
    path = os.path.join(settings.BACKUP_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")
    os.remove(path)
    return {"message": "Backup deleted"}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    result = await db.execute(query.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)))
    return result.scalars().all()
