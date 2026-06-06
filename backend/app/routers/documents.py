from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import os

from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentVersion, AuditLog
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentVersionResponse,
)
from app.utils.dependencies import get_current_active_user
from app.services.file_service import save_upload_file, delete_file

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_document_or_404(doc_id: str, db: AsyncSession) -> Document:
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.versions), selectinload(Document.approval_stages))
        .where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    project_id: str | None = None,
    status: str | None = None,
    doc_type: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Document).options(selectinload(Document.versions), selectinload(Document.approval_stages))
    if project_id:
        query = query.where(Document.project_id == project_id)
    if status:
        query = query.where(Document.status == status)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if search:
        query = query.where(Document.name.ilike(f"%{search}%"))
    result = await db.execute(query.order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    name: str = Form(...),
    project_id: str = Form(...),
    doc_type: str | None = Form(None),
    section_id: str | None = Form(None),
    version: str = Form("1.0"),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    file_path = None
    file_size = 0
    mime_type = None

    if file:
        file_path, file_size = await save_upload_file(file, f"documents/{project_id}")
        mime_type = file.content_type

    doc = Document(
        name=name,
        project_id=project_id,
        doc_type=doc_type,
        section_id=section_id,
        version=version,
        uploaded_by=current_user.id,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(doc)
    await db.flush()

    db.add(AuditLog(
        entity_type="document", entity_id=doc.id,
        action="upload", user_id=current_user.id,
        details={"name": name, "version": version},
    ))

    if file_path:
        db.add(DocumentVersion(
            document_id=doc.id,
            version_number=version,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=current_user.id,
            notes="Initial version",
        ))

    await db.commit()
    return await get_document_or_404(doc.id, db)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_document_or_404(doc_id, db)


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = await get_document_or_404(doc_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    await db.commit()
    return await get_document_or_404(doc_id, db)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = await get_document_or_404(doc_id, db)
    if doc.file_path:
        delete_file(doc.file_path)
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted"}


@router.post("/{doc_id}/versions", response_model=DocumentVersionResponse, status_code=201)
async def upload_new_version(
    doc_id: str,
    notes: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = await get_document_or_404(doc_id, db)
    file_path, file_size = await save_upload_file(file, f"documents/{doc.project_id}")

    parts = doc.version.split(".")
    minor = int(parts[1]) + 1 if len(parts) > 1 else 1
    new_version = f"{parts[0]}.{minor}"

    doc.version = new_version
    doc.file_path = file_path
    doc.file_size = file_size

    version = DocumentVersion(
        document_id=doc_id,
        version_number=new_version,
        file_path=file_path,
        file_size=file_size,
        uploaded_by=current_user.id,
        notes=notes,
    )
    db.add(version)
    db.add(AuditLog(
        entity_type="document", entity_id=doc_id,
        action="new_version", user_id=current_user.id,
        details={"version": new_version},
    ))
    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionResponse])
async def get_versions(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = await get_document_or_404(doc_id, db)
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(doc.file_path, filename=doc.name)
