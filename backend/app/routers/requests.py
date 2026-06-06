from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.request_model import Request, RequestComment
from app.schemas.request import (
    RequestCreate, RequestUpdate, RequestResponse,
    RequestCommentCreate, RequestCommentResponse,
)
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/requests", tags=["requests"])


async def get_request_or_404(request_id: str, db: AsyncSession) -> Request:
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.comments))
        .where(Request.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.get("", response_model=list[RequestResponse])
async def list_requests(
    project_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Request).options(selectinload(Request.comments))
    if project_id:
        query = query.where(Request.project_id == project_id)
    if status:
        query = query.where(Request.status == status)
    result = await db.execute(query.order_by(Request.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=RequestResponse, status_code=201)
async def create_request(
    data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    req = Request(**data.model_dump(), created_by=current_user.id)
    db.add(req)
    await db.commit()
    return await get_request_or_404(req.id, db)


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_request_or_404(request_id, db)


@router.put("/{request_id}", response_model=RequestResponse)
async def update_request(
    request_id: str,
    data: RequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    req = await get_request_or_404(request_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(req, field, value)
    await db.commit()
    return await get_request_or_404(request_id, db)


@router.delete("/{request_id}")
async def delete_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    req = await get_request_or_404(request_id, db)
    await db.delete(req)
    await db.commit()
    return {"message": "Request deleted"}


@router.post("/{request_id}/comments", response_model=RequestCommentResponse, status_code=201)
async def add_comment(
    request_id: str,
    data: RequestCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await get_request_or_404(request_id, db)
    comment = RequestComment(request_id=request_id, user_id=current_user.id, content=data.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
