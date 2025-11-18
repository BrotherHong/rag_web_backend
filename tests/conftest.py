"""
測試配置和 Fixtures
提供測試所需的共用資源和工具
"""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
from app.models import User, Department, SystemSetting
from app.core.security import get_password_hash

# 測試資料庫 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# ===== 資料庫 Fixtures =====

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """創建事件循環"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """創建測試資料庫引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # 創建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session_maker(test_engine):
    """創建測試 Session Maker"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
async def db_session(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """提供資料庫 Session"""
    async with test_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def override_get_db(db_session):
    """覆蓋資料庫依賴"""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


# ===== 客戶端 Fixtures =====

@pytest.fixture(scope="function")
def client(override_get_db) -> Generator:
    """同步測試客戶端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
async def async_client(override_get_db) -> AsyncGenerator:
    """異步測試客戶端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ===== 測試資料 Fixtures =====

@pytest.fixture
async def test_department(db_session: AsyncSession) -> Department:
    """創建測試處室"""
    department = Department(
        name="測試處室",
        description="這是測試用的處室",
    )
    db_session.add(department)
    await db_session.commit()
    await db_session.refresh(department)
    return department


@pytest.fixture
async def test_admin_user(db_session: AsyncSession, test_department: Department) -> User:
    """創建測試管理員"""
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        full_name="測試管理員",
        role="ADMIN",
        department_id=test_department.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_dept_admin_user(db_session: AsyncSession, test_department: Department) -> User:
    """創建測試處室管理員"""
    user = User(
        username="deptadmin",
        email="deptadmin@test.com",
        hashed_password=get_password_hash("dept123"),
        full_name="處室管理員",
        role="DEPT_ADMIN",
        department_id=test_department.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_normal_user(db_session: AsyncSession, test_department: Department) -> User:
    """創建測試普通使用者"""
    user = User(
        username="user",
        email="user@test.com",
        hashed_password=get_password_hash("user123"),
        full_name="普通使用者",
        role="USER",
        department_id=test_department.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ===== 認證 Fixtures =====

@pytest.fixture
def admin_token(client, test_admin_user) -> str:
    """獲取管理員 Token"""
    response = client.post(
        "/api/auth/token",
        data={
            "username": "admin",
            "password": "admin123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def dept_admin_token(client, test_dept_admin_user) -> str:
    """獲取處室管理員 Token"""
    response = client.post(
        "/api/auth/token",
        data={
            "username": "deptadmin",
            "password": "dept123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(client, test_normal_user) -> str:
    """獲取普通使用者 Token"""
    response = client.post(
        "/api/auth/token",
        data={
            "username": "user",
            "password": "user123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """管理員請求標頭"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def dept_admin_headers(dept_admin_token) -> dict:
    """處室管理員請求標頭"""
    return {"Authorization": f"Bearer {dept_admin_token}"}


@pytest.fixture
def user_headers(user_token) -> dict:
    """普通使用者請求標頭"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
async def test_settings(db_session: AsyncSession):
    """建立測試用的系統設定"""
    from app.models.system_setting import SystemSetting
    
    settings = [
        SystemSetting(
            key="app.max_file_size",
            value={"bytes": 52428800},
            display_name="最大檔案大小",
            description="Maximum file upload size",
            category="app",
            is_public=True,
            is_sensitive=False
        ),
        SystemSetting(
            key="rag.temperature",
            value={"value": 0.7},
            display_name="RAG Temperature",
            description="RAG model temperature",
            category="rag",
            is_public=False,
            is_sensitive=False
        ),
        SystemSetting(
            key="rag.max_tokens",
            value={"value": 2000},
            display_name="RAG Max Tokens",
            description="RAG model max tokens",
            category="rag",
            is_public=False,
            is_sensitive=False
        ),
    ]
    
    for setting in settings:
        db_session.add(setting)
    await db_session.commit()
    
    return settings


# ===== 工具 Fixtures =====

@pytest.fixture
def sample_file_content() -> bytes:
    """範例檔案內容"""
    return b"This is a test file content for testing purposes."


@pytest.fixture
def sample_pdf_file(tmp_path, sample_file_content):
    """創建範例 PDF 檔案"""
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(sample_file_content)
    return file_path
