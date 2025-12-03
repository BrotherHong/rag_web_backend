"""統計與系統資訊 API 路由"""

import os
import shutil
import platform
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import Activity, File, User, UserRole, Category, QueryHistory
from app.config import settings

router = APIRouter(tags=["統計與系統"])


@router.get("/statistics", summary="取得系統統計資料")
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得系統整體統計資料
    
    前端期望格式:
    {
      totalFiles: number,
      filesByCategory: [{name, count, color}],
      monthlyQueries: number,
      systemStatus: "正常",
      storageUsed: string,
      storageTotal: string
    }
    """
    # # 根據使用者權限過濾資料
    # if current_user.role == UserRole.SUPER_ADMIN:
    #     # 系統管理員可以看到所有資料
    #     department_filter = None
    # else:
    #     # 處室管理員只能看自己處室
    #     department_filter = current_user.department_id
    # 上述註解是為了解決在super admin角色下進入各處室儀表板後顯示出資料加總數為全域不為各處室的問題
    # 若要拿到加總資料則須再增加判斷邏輯讓department_filter = None即可拿到全域資料

    department_filter = current_user.department_id
    # 全部都要帶有處室id才能正確顯示各處室的統計數據

    # 1. 總檔案數
    file_query = select(func.count(File.id))
    if department_filter:
        file_query = file_query.where(File.department_id == department_filter)
    total_files = await db.scalar(file_query) or 0
    
    # 2. 依分類統計檔案
    category_query = select(
        Category.name,
        Category.color,
        func.count(File.id).label('count')
    ).select_from(Category).outerjoin(
        File, Category.id == File.category_id
    )
    if department_filter:
        category_query = category_query.where(File.department_id == department_filter)
    category_query = category_query.group_by(Category.id, Category.name, Category.color)
    
    category_result = await db.execute(category_query)
    files_by_category = [
        {
            "name": row.name,
            "count": row.count,
            "color": row.color or "gray"
        }
        for row in category_result
    ]
    
    # 3. 本月查詢數
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query_count_query = select(func.count(QueryHistory.id)).where(
        QueryHistory.created_at >= month_start
    )
    if department_filter:
        query_count_query = query_count_query.where(QueryHistory.department_id == department_filter)
    monthly_queries = await db.scalar(query_count_query) or 0
    
    # 4. 儲存空間使用情況
    upload_dir = settings.UPLOAD_DIR
    if os.path.exists(upload_dir):
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(upload_dir)
            for filename in filenames
        )
        storage_used = f"{total_size / (1024**3):.2f} GB"
    else:
        storage_used = "0 GB"
    
    # 5. 磁碟總容量
    try:
        # 使用 shutil.disk_usage 替代 psutil（Python 內建）
        disk_usage = shutil.disk_usage(os.path.dirname(upload_dir) if os.path.exists(upload_dir) else ".")
        storage_total = f"{disk_usage.total / (1024**3):.2f} GB"
    except:
        storage_total = "N/A"
    
    # 6. 系統狀態
    system_status = {
        "status": "running",
        "message": "系統運行正常"
    }
    
    return {
        "totalFiles": total_files,
        "filesByCategory": files_by_category,
        "monthlyQueries": monthly_queries,
        "systemStatus": system_status,
        "storageUsed": storage_used,
        "storageTotal": storage_total
    }


@router.get("/system/info", summary="取得系統資訊")
async def get_system_info(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    取得系統詳細資訊（僅管理員）
    
    返回格式:
    {
      version: string,
      platform: string,
      databaseSize: string,
      totalFiles: number,
      totalUsers: number,
      totalActivities: number,
      storage: { used, total, usedBytes, totalBytes, percentage }
    }
    """
    # 1. 儲存空間（使用 Python 內建的 shutil，跨平台支援）
    upload_dir = settings.UPLOAD_DIR
    try:
        # 確保目錄存在
        if os.path.exists(upload_dir):
            disk_path = upload_dir
        else:
            disk_path = "."
        
        disk_usage = shutil.disk_usage(disk_path)
        used_bytes = disk_usage.used
        total_bytes = disk_usage.total
        used_gb = used_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
        percentage = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0
        
        storage = {
            "used": f"{used_gb:.2f} GB",
            "total": f"{total_gb:.2f} GB",
            "usedBytes": used_bytes,
            "totalBytes": total_bytes,
            "percentage": round(percentage, 1)
        }
    except Exception as e:
        storage = {
            "used": "N/A",
            "total": "N/A",
            "usedBytes": 0,
            "totalBytes": 0,
            "percentage": 0
        }
    
    # 2. 資料庫統計
    total_files = await db.scalar(select(func.count(File.id))) or 0
    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_activities = await db.scalar(select(func.count(Activity.id))) or 0
    
    # 資料庫大小（估算）
    database_size = f"約 {(total_files * 0.01 + total_activities * 0.001):.2f} MB"
    
    # 3. 系統平台資訊（跨平台）
    try:
        platform_info = f"{platform.system()} {platform.release()}"
        python_version = platform.python_version()
        platform_full = f"{platform_info} (Python {python_version})"
    except:
        platform_full = "Unknown Platform"
    
    return {
        "version": "1.0.0",
        "platform": platform_full,
        "databaseSize": database_size,
        "totalFiles": total_files,
        "totalUsers": total_users,
        "totalActivities": total_activities,
        "storage": storage
    }
