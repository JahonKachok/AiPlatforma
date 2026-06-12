from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.project import ProjectStage, ProjectStatus, SectionStatus


class SubObjectCreate(BaseModel):
    name: str
    address: Optional[str] = None
    gip_id: Optional[str] = None


class SubObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    address: Optional[str]
    gip_id: Optional[str]
    status: SectionStatus
    created_at: datetime


class SectionCreate(BaseModel):
    name: str
    code: Optional[str] = None
    sub_object_id: Optional[str] = None
    gip_id: Optional[str] = None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    sub_object_id: Optional[str]
    code: Optional[str]
    name: str
    gip_id: Optional[str]
    status: SectionStatus
    created_at: datetime


class ProjectMemberCreate(BaseModel):
    user_id: str
    role_in_project: Optional[str] = None
    can_edit: bool = True
    expires_at: Optional[datetime] = None


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    role_in_project: Optional[str]
    can_edit: bool = True
    expires_at: Optional[datetime] = None
    joined_at: datetime


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    address: Optional[str] = None
    stage: ProjectStage = ProjectStage.concept
    start_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    budget: float = 0.0


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    address: Optional[str] = None
    stage: Optional[ProjectStage] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    budget: Optional[float] = None
    paid_amount: Optional[float] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: Optional[str]
    client_name: Optional[str]
    client_contact: Optional[str]
    address: Optional[str]
    stage: ProjectStage
    status: ProjectStatus
    start_date: Optional[datetime]
    deadline: Optional[datetime]
    budget: float
    paid_amount: float
    created_by: str
    created_at: datetime
    updated_at: datetime
    members: List[ProjectMemberResponse] = []
    sub_objects: List[SubObjectResponse] = []
    sections: List[SectionResponse] = []


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    client_name: Optional[str]
    address: Optional[str]
    stage: ProjectStage
    status: ProjectStatus
    deadline: Optional[datetime]
    budget: float
    paid_amount: float
    created_at: datetime
