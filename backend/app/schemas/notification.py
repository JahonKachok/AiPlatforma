from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: Optional[str]
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int
