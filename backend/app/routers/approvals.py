from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.document import Document, ApprovalStage, DocumentStatus, ApprovalStatus, AuditLog
from app.models.notification import NotificationType
from app.schemas.document import ApprovalStageCreate, ApprovalStageResponse, ApprovalReviewRequest
from app.utils.dependencies import get_current_active_user
from app.websocket.manager import manager
from app.services.notify import notify_user

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalStageResponse])
async def list_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ApprovalStage)
        .where(ApprovalStage.reviewer_id == current_user.id)
        .order_by(ApprovalStage.created_at.desc())
    )
    return result.scalars().all()


@router.get("/pending", response_model=list[ApprovalStageResponse])
async def get_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ApprovalStage).where(
            ApprovalStage.reviewer_id == current_user.id,
            ApprovalStage.status == ApprovalStatus.pending,
        )
    )
    return result.scalars().all()


@router.post("/{document_id}/stages", response_model=list[ApprovalStageResponse], status_code=201)
async def create_approval_workflow(
    document_id: str,
    stages: list[ApprovalStageCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    existing = await db.execute(select(ApprovalStage).where(ApprovalStage.document_id == document_id))
    for stage in existing.scalars().all():
        await db.delete(stage)

    created_stages = []
    for stage_data in stages:
        stage = ApprovalStage(document_id=document_id, **stage_data.model_dump())
        db.add(stage)
        created_stages.append(stage)

        await notify_user(
            db, stage_data.reviewer_id, NotificationType.approval,
            "Hujjatni ko'rib chiqish so'rovi",
            f"'{doc.name}' hujjatini ko'rib chiqishingiz so'ralmoqda",
            f"/approvals?doc={document_id}",
        )

    doc.status = DocumentStatus.review
    await db.commit()

    for stage in created_stages:
        await db.refresh(stage)
    return created_stages


@router.put("/stages/{stage_id}", response_model=ApprovalStageResponse)
async def review_stage(
    stage_id: str,
    data: ApprovalReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(ApprovalStage).where(ApprovalStage.id == stage_id))
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Approval stage not found")
    if stage.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your approval stage")
    if stage.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Stage already reviewed")

    stage.status = data.status
    stage.comment = data.comment
    stage.reviewed_at = datetime.utcnow()

    doc_result = await db.execute(
        select(Document)
        .options(selectinload(Document.approval_stages))
        .where(Document.id == stage.document_id)
    )
    doc = doc_result.scalar_one_or_none()

    if doc:
        if data.status == ApprovalStatus.rejected:
            doc.status = DocumentStatus.rejected
        elif data.status == ApprovalStatus.revision:
            # Needs rework: send the document back to the executor (draft)
            doc.status = DocumentStatus.draft
        else:
            all_stages = await db.execute(
                select(ApprovalStage).where(ApprovalStage.document_id == doc.id)
            )
            all_approved = all(s.status == ApprovalStatus.approved for s in all_stages.scalars().all() if s.id != stage_id)
            if all_approved:
                doc.status = DocumentStatus.approved

        db.add(AuditLog(
            entity_type="document", entity_id=doc.id,
            action=f"approval_{data.status.value}",
            user_id=current_user.id,
            details={"stage": stage.stage_name, "comment": data.comment},
        ))

        status_titles = {
            ApprovalStatus.approved: "Hujjat tasdiqlandi",
            ApprovalStatus.rejected: "Hujjat rad etildi",
            ApprovalStatus.revision: "Hujjat qayta ishlashga qaytarildi",
        }
        await notify_user(
            db, doc.uploaded_by, NotificationType.approval,
            status_titles.get(data.status, "Hujjat holati o'zgardi"),
            f"'{doc.name}' hujjati: {stage.stage_name} bosqichi — {data.status.value}"
            + (f". Izoh: {data.comment}" if data.comment else ""),
            f"/documents?id={doc.id}",
        )
        await manager.send_to_user(doc.uploaded_by, {
            "type": "approval",
            "document_id": doc.id,
            "status": data.status.value,
        })

    await db.commit()
    await db.refresh(stage)
    return stage
