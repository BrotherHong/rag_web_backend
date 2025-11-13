"""Pydantic Schemas - 用於 API 請求/響應的資料驗證"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ===== 使用者 Schemas =====

class UserBase(BaseModel):
    """使用者基礎欄位"""
    username: str = Field(..., min_length=3, max_length=50, description="使用者名稱")
    email: EmailStr = Field(..., description="電子郵件")
    full_name: str = Field(..., min_length=1, max_length=100, description="全名")


class UserCreate(UserBase):
    """建立使用者請求"""
    password: str = Field(..., min_length=6, max_length=128, description="密碼")
    department_id: int = Field(..., description="所屬處室 ID")


class UserUpdate(BaseModel):
    """更新使用者請求"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """使用者響應"""
    id: int
    role: str
    is_active: bool
    department_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== 認證 Schemas =====

class Token(BaseModel):
    """JWT Token 響應"""
    access_token: str = Field(..., description="JWT Access Token")
    token_type: str = Field(default="bearer", description="Token 類型")


class TokenData(BaseModel):
    """Token 中包含的資料"""
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    """登入請求"""
    username: str = Field(..., description="使用者名稱")
    password: str = Field(..., description="密碼")


class ChangePasswordRequest(BaseModel):
    """修改密碼請求"""
    old_password: str = Field(..., description="舊密碼")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密碼")


# ===== 處室 Schemas =====

class DepartmentBase(BaseModel):
    """處室基礎欄位"""
    name: str = Field(..., min_length=1, max_length=100, description="處室名稱")
    description: Optional[str] = Field(None, description="處室描述")


class DepartmentCreate(DepartmentBase):
    """建立處室請求"""
    pass


class DepartmentResponse(DepartmentBase):
    """處室響應"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== 通用 Schemas =====

class MessageResponse(BaseModel):
    """通用訊息響應"""
    message: str = Field(..., description="訊息內容")
    detail: Optional[str] = Field(None, description="詳細資訊")


class PaginationParams(BaseModel):
    """分頁參數"""
    skip: int = Field(default=0, ge=0, description="跳過筆數")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")


__all__ = [
    # 使用者
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # 認證
    "Token",
    "TokenData",
    "LoginRequest",
    "ChangePasswordRequest",
    # 處室
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentResponse",
    # 通用
    "MessageResponse",
    "PaginationParams",
]

# 註: 檔案和分類的 Schemas 在各自的模組中
# from app.schemas.file import *
# from app.schemas.category import *
