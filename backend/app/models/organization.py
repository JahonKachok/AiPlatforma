import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class DepartmentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    head_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[DepartmentStatus] = mapped_column(SAEnum(DepartmentStatus, native_enum=False), default=DepartmentStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    units: Mapped[list["OrganizationalUnit"]] = relationship("OrganizationalUnit", back_populates="department", cascade="all, delete-orphan")


class OrganizationalUnit(Base):
    __tablename__ = "organizational_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # Hierarchy level
    status: Mapped[DepartmentStatus] = mapped_column(SAEnum(DepartmentStatus, native_enum=False), default=DepartmentStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department: Mapped["Department"] = relationship("Department", back_populates="units")
    members: Mapped[list["DepartmentMember"]] = relationship("DepartmentMember", back_populates="unit", cascade="all, delete-orphan", foreign_keys="DepartmentMember.unit_id")


class DepartmentMember(Base):
    __tablename__ = "department_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizational_units.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "Lead", "Senior", "Junior"
    manager_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)  # Direct manager
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)  # Primary assignment
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    unit: Mapped["OrganizationalUnit"] = relationship("OrganizationalUnit", back_populates="members", foreign_keys=[unit_id])


class ReportingRelationship(Base):
    __tablename__ = "reporting_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    manager_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subordinate_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("departments.id"), nullable=True)
    is_direct: Mapped[bool] = mapped_column(Boolean, default=True)  # Direct report vs indirect
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
