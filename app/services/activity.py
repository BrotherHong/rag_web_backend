"""活動記錄服務 (Activity Logging Service)"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.activity import Activity


class ActivityService:
    """活動記錄服務"""
    
    async def log_activity(
        self,
        db: AsyncSession,
        user_id: int,
        activity_type: str,
        description: str,
        file_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[str] = None
    ) -> Activity:
        """記錄活動
        
        Args:
            db: 資料庫 Session
            user_id: 使用者 ID
            activity_type: 活動類型 (login, logout, upload, download, delete, etc.)
            description: 描述
            file_id: 關聯檔案 ID
            ip_address: IP 位址
            user_agent: User Agent
            extra_data: 額外資訊 (JSON 格式)
            
        Returns:
            Activity: 活動記錄物件
        """
        activity = Activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            file_id=file_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data
        )
        
        db.add(activity)
        await db.flush()  # 不立即 commit，讓調用者決定何時 commit
        
        return activity


# 建立全域活動記錄服務實例
activity_service = ActivityService()
