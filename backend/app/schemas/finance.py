from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.finance import RecordType, RecordStatus, ContractStatus


class FinancialRecordCreate(BaseModel):
    project_id: str
    type: RecordType
    amount: float
    currency: str = "UZS"
    description: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    status: RecordStatus = RecordStatus.pending


class FinancialRecordUpdate(BaseModel):
    type: Optional[RecordType] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[RecordStatus] = None


class FinancialRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    type: RecordType
    amount: float
    currency: str
    description: Optional[str]
    category: Optional[str]
    date: datetime
    status: RecordStatus
    created_by: str
    created_at: datetime


class ContractCreate(BaseModel):
    project_id: str
    client_name: str
    contract_number: Optional[str] = None
    amount: float
    signed_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None


class ContractUpdate(BaseModel):
    client_name: Optional[str] = None
    contract_number: Optional[str] = None
    amount: Optional[float] = None
    signed_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    status: Optional[ContractStatus] = None
    notes: Optional[str] = None


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    client_name: str
    contract_number: Optional[str]
    amount: float
    signed_date: Optional[datetime]
    deadline: Optional[datetime]
    status: ContractStatus
    file_path: Optional[str]
    notes: Optional[str]
    created_by: str
    created_at: datetime


class EmployeeContractCreate(BaseModel):
    user_id: str
    project_id: str
    amount: float
    advance: float = 0.0
    notes: Optional[str] = None


class EmployeeContractUpdate(BaseModel):
    amount: Optional[float] = None
    advance: Optional[float] = None
    paid: Optional[float] = None
    status: Optional[ContractStatus] = None
    notes: Optional[str] = None


class EmployeeContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    project_id: str
    amount: float
    advance: float
    paid: float
    status: ContractStatus
    notes: Optional[str]
    created_at: datetime


class FinanceStatsResponse(BaseModel):
    total_income: float
    total_expense: float
    total_advance: float
    total_debt: float
    confirmed_records: int
    pending_records: int
