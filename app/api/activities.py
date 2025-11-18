"""活動記錄 API 路由"""

import math
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.activity import Activity, ActivityType
from app.models.file import File
from app.schemas.activity import (
    ActivityListResponse,
    ActivityListItem,
    ActivityDetail,
    ActivityStatsResponse
)

router = APIRouter(prefix="/activities", tags=["活動記錄"])


@router.get("", response_model=ActivityListResponse)
async def get_activities(
    page: int = Query(1, ge=1, description="頁碼"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    activity_type: Optional[str] = Query(None, description="活動類型篩選"),
    user_id: Optional[int] = Query(None, description="使用者ID篩選"),
    file_id: Optional[int] = Query(None, description="檔案ID篩選"),
    search: Optional[str] = Query(None, description="搜尋描述"),
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得活動記錄列表
    
    - 支援分頁
    - 支援多種篩選條件
    - 自動過濾處室（一般使用者只能看自己處室的活動）
    - 超級管理員可以看所有活動
    """
    
    # 建立基礎查詢
    query = select(Activity).options(
        joinedload(Activity.user),
        joinedload(Activity.file)
    )
    
    # 處室隔離：一般使用者只能看自己處室的活動
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        # 需要 join user 表來過濾處室
        query = query.join(Activity.user).where(
            User.department_id == current_user.department_id
        )
    
    # 活動類型篩選
    if activity_type:
        try:
            type_enum = ActivityType(activity_type)
            query = query.where(Activity.activity_type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="無效的活動類型")
    
    # 使用者篩選
    if user_id:
        query = query.where(Activity.user_id == user_id)
    
    # 檔案篩選
    if file_id:
        query = query.where(Activity.file_id == file_id)
    
    # 描述搜尋
    if search:
        query = query.where(Activity.description.ilike(f"%{search}%"))
    
    # 日期範圍篩選
    if start_date:
        query = query.where(Activity.created_at >= start_date)
    if end_date:
        query = query.where(Activity.created_at <= end_date)
    
    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 排序和分頁
    query = query.order_by(desc(Activity.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # 執行查詢
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # 轉換為回應格式
    items = []
    for activity in activities:
        items.append(ActivityListItem(
            id=activity.id,
            activity_type=activity.activity_type.value,
            description=activity.description,
            user_id=activity.user_id,
            username=activity.user.username if activity.user else "未知",
            user_full_name=activity.user.full_name if activity.user else "未知",
            file_id=activity.file_id,
            file_name=activity.file.original_filename if activity.file else None,
            ip_address=activity.ip_address,
            created_at=activity.created_at
        ))
    
    return ActivityListResponse(
        items=items,
        total=total or 0,
        page=page,
        pages=math.ceil(total / limit) if total and total > 0 else 0
    )


@router.get("/{activity_id}", response_model=ActivityDetail)
async def get_activity_detail(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得活動記錄詳情
    
    - 包含完整的活動資訊
    - 包含關聯的使用者和檔案資訊
    - 權限檢查
    """
    
    # 查詢活動記錄
    query = select(Activity).where(Activity.id == activity_id).options(
        joinedload(Activity.user),
        joinedload(Activity.file)
    )
    
    result = await db.execute(query)
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="活動記錄不存在")
    
    # 權限檢查：一般使用者只能查看自己處室的活動
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        if activity.user.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="無權限查看此活動記錄")
    
    # 構建回應
    response = ActivityDetail.model_validate(activity)
    
    # 添加關聯資訊
    if activity.user:
        response.user = {
            "id": activity.user.id,
            "username": activity.user.username,
            "full_name": activity.user.full_name,
            "email": activity.user.email
        }
    
    if activity.file:
        response.file = {
            "id": activity.file.id,
            "filename": activity.file.original_filename,
            "file_type": activity.file.file_type,
            "file_size": activity.file.file_size
        }
    
    return response


@router.get("/stats/summary", response_model=ActivityStatsResponse)
async def get_activity_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得活動統計
    
    - 各種時間範圍的統計
    - 依活動類型統計
    - 依使用者統計
    - 最近活動列表
    """
    
    # 基礎查詢（處室隔離）
    from app.models.user import UserRole
    base_query = select(Activity).join(Activity.user)
    
    if current_user.role != UserRole.ADMIN:
        base_query = base_query.where(User.department_id == current_user.department_id)
    
    # 1. 總活動數
    total_query = select(func.count()).select_from(base_query.subquery())
    total_activities = await db.scalar(total_query) or 0
    
    # 2. 今日活動數
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.count()).select_from(
        base_query.where(Activity.created_at >= today_start).subquery()
    )
    activities_today = await db.scalar(today_query) or 0
    
    # 3. 本週活動數
    week_start = today_start - timedelta(days=today_start.weekday())
    week_query = select(func.count()).select_from(
        base_query.where(Activity.created_at >= week_start).subquery()
    )
    activities_this_week = await db.scalar(week_query) or 0
    
    # 4. 本月活動數
    month_start = today_start.replace(day=1)
    month_query = select(func.count()).select_from(
        base_query.where(Activity.created_at >= month_start).subquery()
    )
    activities_this_month = await db.scalar(month_query) or 0
    
    # 5. 依活動類型統計
    type_query = select(
        Activity.activity_type,
        func.count(Activity.id).label('count')
    ).select_from(base_query.subquery()).group_by(Activity.activity_type)
    
    type_result = await db.execute(type_query)
    by_type = {row[0].value: row[1] for row in type_result.all()}
    
    # 6. 依使用者統計（前10）
    user_query = select(
        User.id,
        User.username,
        User.full_name,
        func.count(Activity.id).label('activity_count')
    ).select_from(
        base_query.subquery()
    ).join(User, Activity.user_id == User.id).group_by(
        User.id, User.username, User.full_name
    ).order_by(desc('activity_count')).limit(10)
    
    user_result = await db.execute(user_query)
    by_user = [
        {
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "activity_count": row[3]
        }
        for row in user_result.all()
    ]
    
    # 7. 最近活動（前10）
    recent_query = base_query.options(
        joinedload(Activity.user),
        joinedload(Activity.file)
    ).order_by(desc(Activity.created_at)).limit(10)
    
    recent_result = await db.execute(recent_query)
    recent_activities_data = recent_result.scalars().all()
    
    recent_activities = [
        ActivityListItem(
            id=activity.id,
            activity_type=activity.activity_type.value,
            description=activity.description,
            user_id=activity.user_id,
            username=activity.user.username if activity.user else "未知",
            user_full_name=activity.user.full_name if activity.user else "未知",
            file_id=activity.file_id,
            file_name=activity.file.original_filename if activity.file else None,
            ip_address=activity.ip_address,
            created_at=activity.created_at
        )
        for activity in recent_activities_data
    ]
    
    return ActivityStatsResponse(
        total_activities=total_activities,
        activities_today=activities_today,
        activities_this_week=activities_this_week,
        activities_this_month=activities_this_month,
        by_type=by_type,
        by_user=by_user,
        recent_activities=recent_activities
    )
