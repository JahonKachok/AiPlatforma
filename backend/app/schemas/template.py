from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.template import TemplateType


class TemplateCreate(BaseModel):
    name: str
    template_type: TemplateType = TemplateType.contract
    description: Optional[str] = None
    content: str


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_type: Optional[TemplateType] = None
    description: Optional[str] = None
    content: Optional[str] = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    template_type: TemplateType
    description: Optional[str]
    content: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class TemplateGenerateRequest(BaseModel):
    project_id: str
    contract_id: Optional[str] = None
    employee_id: Optional[str] = None
    extra_fields: dict[str, str] = {}
    save_as_document: bool = True
