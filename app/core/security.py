"""安全性與認證核心功能

提供密碼加密、JWT Token 生成與驗證等功能
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.models import User

# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密碼流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼
    
    Args:
        plain_password: 明文密碼
        hashed_password: 雜湊密碼
        
    Returns:
        bool: 密碼是否正確
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    將明文密碼轉換為雜湊值
    
    Args:
        password: 明文密碼
        
    Returns:
        str: 雜湊後的密碼
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT Access Token
    
    Args:
        data: 要編碼的資料（通常包含 sub: user_id）
        expires_delta: 過期時間（預設使用設定檔中的值）
        
    Returns:
        str: JWT Token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    從 JWT Token 中取得當前使用者
    
    依賴注入函數，用於需要認證的路由
    
    Args:
        token: JWT Token
        db: 資料庫 Session
        
    Returns:
        User: 當前使用者物件
        
    Raises:
        HTTPException: Token 無效或使用者不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解碼 JWT Token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # 從資料庫取得使用者
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號已停用"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    取得當前啟用的使用者
    
    Args:
        current_user: 當前使用者
        
    Returns:
        User: 啟用的使用者物件
        
    Raises:
        HTTPException: 使用者未啟用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號未啟用"
        )
    return current_user


async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    取得當前啟用的管理員使用者
    
    Args:
        current_user: 當前使用者
        
    Returns:
        User: 管理員使用者物件
        
    Raises:
        HTTPException: 使用者不是管理員或帳號未啟用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號未啟用"
        )
    
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    
    return current_user


async def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    取得當前超級管理員使用者
    
    Args:
        current_user: 當前使用者
        
    Returns:
        User: 超級管理員使用者物件
        
    Raises:
        HTTPException: 使用者不是超級管理員
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="使用者帳號未啟用"
        )
    
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超級管理員權限"
        )
    
    return current_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    驗證使用者帳號密碼
    
    Args:
        db: 資料庫 Session
        username: 使用者名稱
        password: 密碼
        
    Returns:
        Optional[User]: 驗證成功返回使用者物件，失敗返回 None
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def require_role(*allowed_roles):
    """
    權限檢查裝飾器工廠
    
    建立一個依賴注入函數，檢查使用者是否具有指定角色
    
    Args:
        *allowed_roles: 允許的角色列表
        
    Returns:
        依賴注入函數
        
    Example:
        @router.get("/admin")
        async def admin_only(user: User = Depends(require_role(UserRole.ADMIN))):
            return {"message": "Admin access"}
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="權限不足"
            )
        return current_user
    
    return role_checker
