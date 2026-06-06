from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.finance import FinancialRecord, Contract, EmployeeContract, RecordType, RecordStatus
from app.schemas.finance import (
    FinancialRecordCreate, FinancialRecordUpdate, FinancialRecordResponse,
    ContractCreate, ContractUpdate, ContractResponse,
    EmployeeContractCreate, EmployeeContractUpdate, EmployeeContractResponse,
    FinanceStatsResponse,
)
from app.utils.dependencies import get_current_active_user
from app.services.file_service import save_upload_file

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/records", response_model=list[FinancialRecordResponse])
async def list_records(
    project_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(FinancialRecord)
    if project_id:
        query = query.where(FinancialRecord.project_id == project_id)
    if type:
        query = query.where(FinancialRecord.type == type)
    if status:
        query = query.where(FinancialRecord.status == status)
    result = await db.execute(query.order_by(FinancialRecord.date.desc()))
    return result.scalars().all()


@router.post("/records", response_model=FinancialRecordResponse, status_code=201)
async def create_record(
    data: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = FinancialRecord(**data.model_dump(), created_by=current_user.id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/records/{record_id}", response_model=FinancialRecordResponse)
async def update_record(
    record_id: str,
    data: FinancialRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(FinancialRecord).where(FinancialRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/records/{record_id}")
async def delete_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(FinancialRecord).where(FinancialRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.delete(record)
    await db.commit()
    return {"message": "Record deleted"}


@router.get("/stats", response_model=FinanceStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(FinancialRecord))
    records = result.scalars().all()
    return FinanceStatsResponse(
        total_income=sum(r.amount for r in records if r.type == RecordType.income and r.status == RecordStatus.confirmed),
        total_expense=sum(r.amount for r in records if r.type == RecordType.expense and r.status == RecordStatus.confirmed),
        total_advance=sum(r.amount for r in records if r.type == RecordType.advance),
        total_debt=sum(r.amount for r in records if r.type == RecordType.payment and r.status == RecordStatus.pending),
        confirmed_records=sum(1 for r in records if r.status == RecordStatus.confirmed),
        pending_records=sum(1 for r in records if r.status == RecordStatus.pending),
    )


@router.get("/contracts", response_model=list[ContractResponse])
async def list_contracts(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Contract)
    if project_id:
        query = query.where(Contract.project_id == project_id)
    result = await db.execute(query.order_by(Contract.created_at.desc()))
    return result.scalars().all()


@router.post("/contracts", response_model=ContractResponse, status_code=201)
async def create_contract(
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    contract = Contract(**data.model_dump(), created_by=current_user.id)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


@router.put("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(contract, field, value)
    await db.commit()
    await db.refresh(contract)
    return contract


@router.get("/employee-contracts", response_model=list[EmployeeContractResponse])
async def list_employee_contracts(
    project_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(EmployeeContract)
    if project_id:
        query = query.where(EmployeeContract.project_id == project_id)
    if user_id:
        query = query.where(EmployeeContract.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/employee-contracts", response_model=EmployeeContractResponse, status_code=201)
async def create_employee_contract(
    data: EmployeeContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ec = EmployeeContract(**data.model_dump())
    db.add(ec)
    await db.commit()
    await db.refresh(ec)
    return ec


@router.put("/employee-contracts/{ec_id}", response_model=EmployeeContractResponse)
async def update_employee_contract(
    ec_id: str,
    data: EmployeeContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(EmployeeContract).where(EmployeeContract.id == ec_id))
    ec = result.scalar_one_or_none()
    if not ec:
        raise HTTPException(status_code=404, detail="Employee contract not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(ec, field, value)
    await db.commit()
    await db.refresh(ec)
    return ec


@router.get("/project/{project_id}/summary")
async def get_project_summary(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    records_result = await db.execute(
        select(FinancialRecord).where(FinancialRecord.project_id == project_id)
    )
    records = records_result.scalars().all()
    contracts_result = await db.execute(
        select(Contract).where(Contract.project_id == project_id)
    )
    contracts = contracts_result.scalars().all()
    return {
        "total_income": sum(r.amount for r in records if r.type == RecordType.income),
        "total_expense": sum(r.amount for r in records if r.type == RecordType.expense),
        "total_contracts": sum(c.amount for c in contracts),
        "records_count": len(records),
        "contracts_count": len(contracts),
    }
