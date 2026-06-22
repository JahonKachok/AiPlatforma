from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.organization import (
    Department, OrganizationalUnit, DepartmentMember, ReportingRelationship
)
from app.schemas.organization import (
    DepartmentResponse, DepartmentCreate, DepartmentUpdate,
    OrganizationalUnitResponse, OrganizationalUnitCreate, OrganizationalUnitUpdate,
    DepartmentMemberResponse, DepartmentMemberCreate, DepartmentMemberUpdate,
    ReportingRelationshipResponse, ReportingRelationshipCreate
)
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/organization", tags=["organization"])


# ========== DEPARTMENTS ==========

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.units))
        .order_by(Department.name)
    )
    return result.scalars().all()


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.units))
        .where(Department.id == dept_id)
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    dept = Department(**data.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(dept, field, value)

    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    await db.delete(dept)
    await db.commit()
    return {"message": "Department deleted"}


# ========== ORGANIZATIONAL UNITS ==========

@router.get("/units", response_model=list[OrganizationalUnitResponse])
async def list_units(
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(OrganizationalUnit).options(selectinload(OrganizationalUnit.members))
    if department_id:
        query = query.where(OrganizationalUnit.department_id == department_id)
    result = await db.execute(query.order_by(OrganizationalUnit.name))
    return result.scalars().all()


@router.get("/units/{unit_id}", response_model=OrganizationalUnitResponse)
async def get_unit(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(OrganizationalUnit)
        .options(selectinload(OrganizationalUnit.members))
        .where(OrganizationalUnit.id == unit_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.post("/units", response_model=OrganizationalUnitResponse, status_code=201)
async def create_unit(
    data: OrganizationalUnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    unit = OrganizationalUnit(**data.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@router.put("/units/{unit_id}", response_model=OrganizationalUnitResponse)
async def update_unit(
    unit_id: str,
    data: OrganizationalUnitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(OrganizationalUnit).where(OrganizationalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(unit, field, value)

    await db.commit()
    await db.refresh(unit)
    return unit


# ========== DEPARTMENT MEMBERS ==========

@router.get("/members", response_model=list[DepartmentMemberResponse])
async def list_members(
    unit_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(DepartmentMember)
    if unit_id:
        query = query.where(DepartmentMember.unit_id == unit_id)
    if user_id:
        query = query.where(DepartmentMember.user_id == user_id)
    result = await db.execute(query.where(DepartmentMember.left_at == None))
    return result.scalars().all()


@router.post("/members", response_model=DepartmentMemberResponse, status_code=201)
async def add_member(
    data: DepartmentMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    member = DepartmentMember(**data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.put("/members/{member_id}", response_model=DepartmentMemberResponse)
async def update_member(
    member_id: str,
    data: DepartmentMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(DepartmentMember).where(DepartmentMember.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/members/{member_id}")
async def remove_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(DepartmentMember).where(DepartmentMember.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()
    return {"message": "Member removed"}


# ========== REPORTING RELATIONSHIPS ==========

@router.get("/reporting-chain/{user_id}", response_model=list[ReportingRelationshipResponse])
async def get_reporting_chain(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ReportingRelationship)
        .where(ReportingRelationship.subordinate_id == user_id)
        .where(ReportingRelationship.ended_at == None)
    )
    return result.scalars().all()


@router.get("/direct-reports/{manager_id}", response_model=list[ReportingRelationshipResponse])
async def get_direct_reports(
    manager_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ReportingRelationship)
        .where(ReportingRelationship.manager_id == manager_id)
        .where(ReportingRelationship.is_direct == True)
        .where(ReportingRelationship.ended_at == None)
    )
    return result.scalars().all()


@router.post("/reporting-relationships", response_model=ReportingRelationshipResponse, status_code=201)
async def create_reporting_relationship(
    data: ReportingRelationshipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rel = ReportingRelationship(**data.model_dump())
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


@router.delete("/reporting-relationships/{rel_id}")
async def delete_reporting_relationship(
    rel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(ReportingRelationship).where(ReportingRelationship.id == rel_id))
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Reporting relationship not found")

    await db.delete(rel)
    await db.commit()
    return {"message": "Reporting relationship deleted"}
