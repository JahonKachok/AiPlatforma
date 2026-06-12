import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class TemplateType(str, enum.Enum):
    contract = "contract"
    act = "act"
    appendix = "appendix"
    invoice = "invoice"
    other = "other"


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[TemplateType] = mapped_column(SAEnum(TemplateType, native_enum=False), default=TemplateType.contract)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Template body with {{placeholder}} variables, e.g. {{project_name}}, {{client_name}}, {{amount}}
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
