"""處室模型"""

from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.file import File


class Department(Base, TimestampMixin):
    """處室表"""
    
    __tablename__ = "departments"
    
    # 主鍵
    id: Mapped[int] = mapped_column(primary_key=True, comment="處室 ID")
    
    # 基本資料
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="處室名稱"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="處室描述"
    )
    
    # 關聯
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="department",
        cascade="all, delete-orphan"
    )
    
    files: Mapped[List["File"]] = relationship(
        "File",
        back_populates="department",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}')>"
