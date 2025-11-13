"""分類模型"""

from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.file import File


class Category(Base, TimestampMixin):
    """分類表"""
    
    __tablename__ = "categories"
    
    # 主鍵
    id: Mapped[int] = mapped_column(primary_key=True, comment="分類 ID")
    
    # 基本資料
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="分類名稱"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="分類描述"
    )
    
    # 關聯
    files: Mapped[List["File"]] = relationship(
        "File",
        back_populates="category"
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
