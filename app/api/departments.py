"""處室管理 API 路由"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models import Department, UserRole
from app.schemas import DepartmentCreate, DepartmentResponse, MessageResponse

router = APIRouter(prefix="/departments", tags=["處室管理"])


@router.get("/", response_model=List[DepartmentResponse], summary="取得處室列表")
async def list_departments(db: AsyncSession = Depends(get_db)):
    """
    取得所有處室列表
    
    公開端點，不需要認證
    """
    result = await db.execute(select(Department))
    departments = result.scalars().all()
    return departments


@router.get("/{department_id}", response_model=DepartmentResponse, summary="取得處室詳情")
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定處室的詳細資訊
    
    - **department_id**: 處室 ID
    """
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="處室不存在"
        )
    
    return department


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立處室",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def create_department(
    department_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    建立新處室
    
    需要系統管理員權限
    
    - **name**: 處室名稱（唯一）
    - **description**: 處室描述（可選）
    """
    # 檢查名稱是否已存在
    result = await db.execute(select(Department).where(Department.name == department_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="處室名稱已存在"
        )
    
    # 建立處室
    department = Department(**department_data.model_dump())
    db.add(department)
    await db.commit()
    await db.refresh(department)
    
    return department


@router.delete(
    "/{department_id}",
    response_model=MessageResponse,
    summary="刪除處室",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    刪除處室
    
    需要系統管理員權限
    
    - **department_id**: 處室 ID
    
    注意：刪除處室會同時刪除該處室下的所有使用者和檔案
    """
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="處室不存在"
        )
    
    await db.delete(department)
    await db.commit()
    
    return MessageResponse(
        message="處室刪除成功",
        detail=f"已刪除處室: {department.name}"
    )
