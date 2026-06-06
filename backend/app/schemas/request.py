from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.request_model import RequestType, RequestStatus, RequestPriority


class RequestCommentCreate(BaseModel):
    content: str


class RequestCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    request_id: str
    user_id: str
    content: str
    created_at: datetime


class RequestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: RequestType = RequestType.clarification
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: RequestPriority = RequestPriority.medium


class RequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[RequestType] = None
    assignee_id: Optional[str] = None
    status: Optional[RequestStatus] = None
    priority: Optional[RequestPriority] = None


class RequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str]
    type: RequestType
    project_id: Optional[str]
    created_by: str
    assignee_id: Optional[str]
    status: RequestStatus
    priority: RequestPriority
    created_at: datetime
    updated_at: datetime
    comments: List[RequestCommentResponse] = []
