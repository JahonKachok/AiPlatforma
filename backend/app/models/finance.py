import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class RecordType(str, enum.Enum):
    income = "income"
    expense = "expense"
    advance = "advance"
    payment = "payment"


class RecordStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class ContractStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    terminated = "terminated"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[RecordType] = mapped_column(SAEnum(RecordType, native_enum=False), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus, native_enum=False), default=RecordStatus.pending)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="financial_records")


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    signed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[ContractStatus] = mapped_column(SAEnum(ContractStatus, native_enum=False), default=ContractStatus.draft)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="contracts")


class EmployeeContract(Base):
    __tablename__ = "employee_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    advance: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ContractStatus] = mapped_column(SAEnum(ContractStatus, native_enum=False), default=ContractStatus.active)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
