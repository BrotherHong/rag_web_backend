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
        action: str,
        description: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        department_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Activity:
        """記錄活動
        
        Args:
            db: 資料庫 Session
            user_id: 使用者 ID
            action: 操作動作 (login, logout, upload, download, delete, update, create, view)
            description: 描述
            entity_type: 實體類型 (file, category, user, etc.)
            entity_id: 實體 ID
            department_id: 處室 ID
            ip_address: IP 位址
            user_agent: User Agent
            metadata: 額外元資料
            
        Returns:
            Activity: 活動記錄物件
        """
        activity = Activity(
            user_id=user_id,
            action=action,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            department_id=department_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            created_at=datetime.now()
        )
        
        db.add(activity)
        await db.flush()  # 不立即 commit，讓調用者決定何時 commit
        
        return activity


# 建立全域活動記錄服務實例
activity_service = ActivityService()
