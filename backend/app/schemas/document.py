from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.document import DocumentStatus, ApprovalStatus


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    version_number: str
    file_path: str
    file_size: int
    uploaded_by: str
    notes: Optional[str]
    created_at: datetime


class ApprovalStageCreate(BaseModel):
    stage_order: int
    stage_name: str
    reviewer_id: str


class ApprovalStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    stage_order: int
    stage_name: str
    reviewer_id: str
    status: ApprovalStatus
    comment: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime


class ApprovalReviewRequest(BaseModel):
    status: ApprovalStatus
    comment: Optional[str] = None


class DocumentCreate(BaseModel):
    name: str
    doc_type: Optional[str] = None
    project_id: str
    section_id: Optional[str] = None
    version: str = "1.0"


class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    doc_type: Optional[str] = None
    section_id: Optional[str] = None
    version: Optional[str] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    doc_type: Optional[str]
    project_id: str
    section_id: Optional[str]
    uploaded_by: str
    version: str
    status: DocumentStatus
    file_path: Optional[str]
    file_size: int
    mime_type: Optional[str]
    google_drive_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    versions: List[DocumentVersionResponse] = []
    approval_stages: List[ApprovalStageResponse] = []
