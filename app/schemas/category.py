"""分類管理相關的 Pydantic Schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """分類基礎 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="分類名稱")
    color: str = Field(default="blue", description="分類顏色")


class CategoryCreate(CategoryBase):
    """建立分類"""
    pass


class CategoryUpdate(BaseModel):
    """更新分類（所有欄位可選）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None


class CategorySchema(CategoryBase):
    """分類資訊 Schema"""
    id: int
    file_count: Optional[int] = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """分類列表回應"""
    items: List[CategorySchema]


class CategoryStatItem(BaseModel):
    """分類統計項目"""
    id: int
    name: str
    color: str
    file_count: int
    total_size: int
    percentage: float


class CategoryStatsResponse(BaseModel):
    """分類統計回應"""
    stats: List[CategoryStatItem]
