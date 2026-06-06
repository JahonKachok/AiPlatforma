import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class RequestType(str, enum.Enum):
    change = "change"
    clarification = "clarification"
    improvement = "improvement"
    issue = "issue"


class RequestStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class RequestPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[RequestType] = mapped_column(SAEnum(RequestType, native_enum=False), default=RequestType.clarification)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus, native_enum=False), default=RequestStatus.open)
    priority: Mapped[RequestPriority] = mapped_column(SAEnum(RequestPriority, native_enum=False), default=RequestPriority.medium)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project | None"] = relationship("Project", back_populates="requests")
    comments: Mapped[list["RequestComment"]] = relationship("RequestComment", back_populates="request", cascade="all, delete-orphan")


class RequestComment(Base):
    __tablename__ = "request_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped["Request"] = relationship("Request", back_populates="comments")
