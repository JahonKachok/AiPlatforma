import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ProjectStage(str, enum.Enum):
    concept = "concept"
    preliminary = "preliminary"
    working_docs = "working_docs"
    expertise = "expertise"
    construction = "construction"


class ProjectStatus(str, enum.Enum):
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"


class SectionStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    review = "review"
    completed = "completed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stage: Mapped[ProjectStage] = mapped_column(SAEnum(ProjectStage, native_enum=False), default=ProjectStage.concept)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus, native_enum=False), default=ProjectStatus.active)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    sub_objects: Mapped[list["SubObject"]] = relationship("SubObject", back_populates="project", cascade="all, delete-orphan")
    sections: Mapped[list["Section"]] = relationship("Section", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    financial_records: Mapped[list["FinancialRecord"]] = relationship("FinancialRecord", back_populates="project", cascade="all, delete-orphan")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="project", cascade="all, delete-orphan")
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="project", cascade="all, delete-orphan")


class SubObject(Base):
    __tablename__ = "sub_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[SectionStatus] = mapped_column(SAEnum(SectionStatus, native_enum=False), default=SectionStatus.not_started)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="sub_objects")
    sections: Mapped[list["Section"]] = relationship("Section", back_populates="sub_object")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sub_object_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sub_objects.id"), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[SectionStatus] = mapped_column(SAEnum(SectionStatus, native_enum=False), default=SectionStatus.not_started)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="sections")
    sub_object: Mapped["SubObject | None"] = relationship("SubObject", back_populates="sections")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="section")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_project: Mapped[str | None] = mapped_column(String(100), nullable=True)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="members")
