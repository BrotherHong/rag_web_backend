"""系統設定 API 路由"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import SystemSetting, User, UserRole
from app.schemas.system_setting import (
    SystemSettingBatchUpdate,
    SystemSettingCreate,
    SystemSettingListResponse,
    SystemSettingPublicResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.schemas import MessageResponse
from app.services.activity import activity_service

router = APIRouter(prefix="/settings", tags=["系統設定"])


@router.get("/public", response_model=list[SystemSettingPublicResponse], summary="取得公開設定")
async def get_public_settings(
    category: Optional[str] = Query(None, description="設定類型篩選"),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有公開的系統設定
    
    - 不需認證
    - 只返回 is_public=True 的設定
    - 敏感資訊會被隱藏
    
    - **category**: 設定類型（app, rag, security, feature）
    """
    query = select(SystemSetting).where(SystemSetting.is_public == True)
    
    if category:
        query = query.where(SystemSetting.category == category)
    
    result = await db.execute(query)
    settings = result.scalars().all()
    
    # 過濾敏感資訊
    return [
        SystemSettingPublicResponse(
            key=setting.key,
            value=setting.value if not setting.is_sensitive else {"hidden": True},
            category=setting.category,
            display_name=setting.display_name,
            description=setting.description
        )
        for setting in settings
    ]


@router.get("/", response_model=SystemSettingListResponse, summary="取得設定列表")
async def list_settings(
    page: int = Query(1, ge=1, description="頁碼"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    category: Optional[str] = Query(None, description="設定類型篩選"),
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得系統設定列表（分頁）
    
    需要認證，一般使用者只能看公開設定，管理員可看所有設定
    
    - **page**: 頁碼
    - **limit**: 每頁數量
    - **category**: 設定類型
    - **search**: 搜尋 key, display_name, description
    """
    # 基礎查詢
    query = select(SystemSetting)
    
    # 權限過濾：一般使用者只能看公開設定
    if current_user.role not in [UserRole.ADMIN]:
        query = query.where(SystemSetting.is_public == True)
    
    # 類型過濾
    if category:
        query = query.where(SystemSetting.category == category)
    
    # 搜尋過濾
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (SystemSetting.key.ilike(search_pattern)) |
            (SystemSetting.display_name.ilike(search_pattern)) |
            (SystemSetting.description.ilike(search_pattern))
        )
    
    # 計算總數
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query) or 0
    
    # 分頁
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # 執行查詢
    result = await db.execute(query)
    settings = result.scalars().all()
    
    # 計算總頁數
    pages = math.ceil(total / limit) if total > 0 else 1
    
    return SystemSettingListResponse(
        items=settings,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/{key}", response_model=SystemSettingResponse, summary="取得特定設定")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得特定的系統設定
    
    - **key**: 設定鍵
    
    權限：一般使用者只能取得公開設定，管理員可取得所有設定
    """
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="設定不存在"
        )
    
    # 權限檢查
    if not setting.is_public and current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權限訪問此設定"
        )
    
    return setting


@router.post(
    "/",
    response_model=SystemSettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立系統設定",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def create_setting(
    setting_data: SystemSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    建立新的系統設定
    
    需要系統管理員權限
    
    - **key**: 設定鍵（唯一）
    - **value**: 設定值（JSON 格式）
    - **category**: 設定類型
    - **display_name**: 顯示名稱
    - **description**: 說明描述
    - **is_sensitive**: 是否為敏感資訊
    - **is_public**: 是否可公開訪問
    - **validation_schema**: 資料驗證 schema
    """
    # 檢查 key 是否已存在
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == setting_data.key))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="設定鍵已存在"
        )
    
    # 建立設定
    setting = SystemSetting(**setting_data.model_dump())
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="create",
        description=f"建立系統設定: {setting.key}"
    )
    await db.commit()
    
    return setting


@router.put(
    "/{key}",
    response_model=SystemSettingResponse,
    summary="更新系統設定",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def update_setting(
    key: str,
    setting_data: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新系統設定
    
    需要系統管理員權限
    
    - **key**: 設定鍵
    - 其他欄位可選更新
    """
    # 查詢設定
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="設定不存在"
        )
    
    # 更新欄位
    update_data = setting_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)
    
    await db.commit()
    await db.refresh(setting)
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="update",
        description=f"更新系統設定: {setting.key}"
    )
    await db.commit()
    
    return setting


@router.post(
    "/batch",
    response_model=MessageResponse,
    summary="批次更新設定",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def batch_update_settings(
    batch_data: SystemSettingBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批次更新多個系統設定
    
    需要系統管理員權限
    
    - **settings**: 設定字典，key 為設定鍵，value 為設定值
    
    只更新已存在的設定，不存在的會被忽略
    """
    updated_count = 0
    
    for key, value in batch_data.settings.items():
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
            updated_count += 1
    
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="update",
        description=f"批次更新 {updated_count} 個系統設定"
    )
    await db.commit()
    
    return MessageResponse(
        message="批次更新成功",
        detail=f"已更新 {updated_count} 個設定"
    )


@router.delete(
    "/{key}",
    response_model=MessageResponse,
    summary="刪除系統設定",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刪除系統設定
    
    需要系統管理員權限
    
    - **key**: 設定鍵
    """
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="設定不存在"
        )
    
    setting_key = setting.key
    await db.delete(setting)
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="delete",
        description=f"刪除系統設定: {setting_key}"
    )
    await db.commit()
    
    return MessageResponse(
        message="設定刪除成功",
        detail=f"已刪除設定: {setting_key}"
    )
