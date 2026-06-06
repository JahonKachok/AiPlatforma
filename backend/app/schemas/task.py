from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.task import TaskStatus, TaskPriority


class TaskCommentCreate(BaseModel):
    content: str


class TaskCommentUpdate(BaseModel):
    content: str


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime


class TaskAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    user_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str]
    created_at: datetime


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: str
    section_id: Optional[str] = None
    assignee_id: Optional[str] = None
    status: TaskStatus = TaskStatus.new
    priority: TaskPriority = TaskPriority.medium
    deadline: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    section_id: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    deadline: Optional[datetime] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: Optional[str]
    project_id: str
    section_id: Optional[str]
    assignee_id: Optional[str]
    creator_id: str
    status: TaskStatus
    priority: TaskPriority
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    comments: List[TaskCommentResponse] = []
    attachments: List[TaskAttachmentResponse] = []
