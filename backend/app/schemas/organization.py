from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.organization import DepartmentStatus


class DepartmentMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    unit_id: str
    user_id: str
    role_in_unit: Optional[str]
    manager_id: Optional[str]
    is_primary: bool
    joined_at: datetime
    left_at: Optional[datetime]


class OrganizationalUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    department_id: str
    name: str
    code: Optional[str]
    description: Optional[str]
    manager_id: Optional[str]
    level: int
    status: DepartmentStatus
    created_at: datetime
    updated_at: datetime
    members: List[DepartmentMemberResponse] = []


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    code: Optional[str]
    description: Optional[str]
    head_id: Optional[str]
    status: DepartmentStatus
    created_at: datetime
    updated_at: datetime
    units: List[OrganizationalUnitResponse] = []


class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[str] = None
    status: Optional[DepartmentStatus] = None


class OrganizationalUnitCreate(BaseModel):
    department_id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    level: int = 1


class OrganizationalUnitUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    level: Optional[int] = None
    status: Optional[DepartmentStatus] = None


class DepartmentMemberCreate(BaseModel):
    unit_id: str
    user_id: str
    role_in_unit: Optional[str] = None
    manager_id: Optional[str] = None
    is_primary: bool = True


class DepartmentMemberUpdate(BaseModel):
    role_in_unit: Optional[str] = None
    manager_id: Optional[str] = None
    is_primary: Optional[bool] = None


class ReportingRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    manager_id: str
    subordinate_id: str
    department_id: Optional[str]
    is_direct: bool
    started_at: datetime
    ended_at: Optional[datetime]


class ReportingRelationshipCreate(BaseModel):
    manager_id: str
    subordinate_id: str
    department_id: Optional[str] = None
    is_direct: bool = True


class OrganizationHierarchyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    departments: int
    total_members: int
    hierarchy_levels: int
