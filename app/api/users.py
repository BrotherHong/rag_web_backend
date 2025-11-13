"""使用者管理 API 路由"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash, require_role
from app.models import User, UserRole, Department
from app.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    MessageResponse,
)

router = APIRouter(prefix="/users", tags=["使用者管理"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立使用者",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEPT_ADMIN))]
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    建立新使用者
    
    需要管理員或處室管理員權限
    
    - **username**: 使用者名稱（唯一）
    - **email**: 電子郵件（唯一）
    - **password**: 密碼
    - **full_name**: 全名
    - **department_id**: 所屬處室 ID
    """
    # 檢查使用者名稱是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="使用者名稱已存在"
        )
    
    # 檢查 Email 是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email 已被使用"
        )
    
    # 檢查處室是否存在
    result = await db.execute(select(Department).where(Department.id == user_data.department_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="處室不存在"
        )
    
    # 處室管理員只能建立自己處室的使用者
    if current_user.role == UserRole.DEPT_ADMIN:
        if user_data.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="處室管理員只能建立自己處室的使用者"
            )
    
    # 建立使用者
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        department_id=user_data.department_id,
        role=UserRole.USER,  # 新使用者預設為一般使用者
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=List[UserResponse], summary="取得使用者列表")
async def list_users(
    skip: int = Query(default=0, ge=0, description="跳過筆數"),
    limit: int = Query(default=20, ge=1, le=100, description="每頁筆數"),
    department_id: int = Query(default=None, description="篩選處室 ID"),
    is_active: bool = Query(default=None, description="篩選是否啟用"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得使用者列表（分頁）
    
    - **skip**: 跳過筆數
    - **limit**: 每頁筆數
    - **department_id**: 篩選特定處室
    - **is_active**: 篩選是否啟用
    
    處室管理員只能查看自己處室的使用者
    """
    query = select(User)
    
    # 處室管理員只能查看自己處室的使用者
    if current_user.role == UserRole.DEPT_ADMIN:
        query = query.where(User.department_id == current_user.department_id)
    elif department_id:
        query = query.where(User.department_id == department_id)
    
    # 篩選是否啟用
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # 分頁
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse, summary="取得使用者詳情")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得特定使用者的詳細資訊
    
    - **user_id**: 使用者 ID
    
    處室管理員只能查看自己處室的使用者
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    # 處室管理員只能查看自己處室的使用者
    if current_user.role == UserRole.DEPT_ADMIN:
        if user.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限查看此使用者"
            )
    
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新使用者",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEPT_ADMIN))]
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新使用者資訊
    
    需要管理員或處室管理員權限
    
    - **user_id**: 使用者 ID
    - **email**: 新的 Email（可選）
    - **full_name**: 新的全名（可選）
    - **department_id**: 新的處室 ID（可選）
    - **is_active**: 是否啟用（可選）
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    # 處室管理員只能更新自己處室的使用者
    if current_user.role == UserRole.DEPT_ADMIN:
        if user.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限更新此使用者"
            )
    
    # 更新欄位
    update_data = user_data.model_dump(exclude_unset=True)
    
    # 檢查 Email 是否重複
    if "email" in update_data:
        result = await db.execute(
            select(User).where(User.email == update_data["email"], User.id != user_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email 已被使用"
            )
    
    # 檢查處室是否存在
    if "department_id" in update_data:
        result = await db.execute(select(Department).where(Department.id == update_data["department_id"]))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="處室不存在"
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="刪除使用者",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刪除使用者
    
    需要系統管理員權限
    
    - **user_id**: 使用者 ID
    
    注意：不能刪除自己
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能刪除自己"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    await db.delete(user)
    await db.commit()
    
    return MessageResponse(
        message="使用者刪除成功",
        detail=f"已刪除使用者: {user.username}"
    )
