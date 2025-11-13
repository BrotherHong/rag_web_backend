"""活動記錄模型"""

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.file import File


class ActivityType(str, Enum):
    """活動類型"""
    LOGIN = "login"                # 登入
    LOGOUT = "logout"              # 登出
    UPLOAD = "upload"              # 上傳檔案
    DOWNLOAD = "download"          # 下載檔案
    DELETE = "delete"              # 刪除檔案
    SEARCH = "search"              # 搜尋
    QUERY = "query"                # RAG 查詢
    UPDATE_PROFILE = "update_profile"  # 更新個人資料
    UPDATE_FILE = "update_file"    # 更新檔案資訊
    CREATE_USER = "create_user"    # 建立使用者
    UPDATE_USER = "update_user"    # 更新使用者
    DELETE_USER = "delete_user"    # 刪除使用者


class Activity(Base, TimestampMixin):
    """活動記錄表"""
    
    __tablename__ = "activities"
    
    # 主鍵
    id: Mapped[int] = mapped_column(primary_key=True, comment="活動 ID")
    
    # 活動資訊
    activity_type: Mapped[ActivityType] = mapped_column(
        SQLEnum(ActivityType),
        nullable=False,
        index=True,
        comment="活動類型"
    )
    
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="活動描述"
    )
    
    ip_address: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="IP 位址"
    )
    
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="User Agent"
    )
    
    extra_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="額外資訊 (JSON 格式)"
    )
    
    # 外鍵
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="使用者 ID"
    )
    
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="關聯檔案 ID"
    )
    
    # 關聯
    user: Mapped["User"] = relationship(
        "User",
        back_populates="activities"
    )
    
    file: Mapped["File"] = relationship(
        "File",
        back_populates="activities"
    )
    
    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, type='{self.activity_type}', user_id={self.user_id})>"
