# 📁 專案資料夾結構

## 完整目錄結構

```
rag_web_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 應用程式入口
│   ├── config.py               # 配置管理
│   ├── dependencies.py         # 全域依賴
│   │
│   ├── api/                    # API 路由層
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # 認證路由
│   │   │   ├── files.py        # 檔案管理路由
│   │   │   ├── categories.py  # 分類管理路由
│   │   │   ├── activities.py  # 活動記錄路由
│   │   │   ├── upload.py       # 批次上傳路由
│   │   │   ├── users.py        # 使用者管理路由
│   │   │   ├── departments.py # 處室管理路由
│   │   │   ├── settings.py    # 系統設定路由
│   │   │   └── statistics.py  # 統計資料路由
│   │   └── deps.py             # API 層級依賴
│   │
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── base.py             # Base 模型與 Mixin
│   │   ├── user.py             # 使用者模型
│   │   ├── department.py      # 處室模型
│   │   ├── file.py             # 檔案模型
│   │   ├── category.py         # 分類模型
│   │   ├── activity.py         # 活動記錄模型
│   │   ├── settings.py         # 系統設定模型
│   │   └── backup.py           # 備份記錄模型
│   │
│   ├── schemas/                # Pydantic Schemas (資料驗證)
│   │   ├── __init__.py
│   │   ├── user.py             # 使用者 Schema
│   │   ├── file.py             # 檔案 Schema
│   │   ├── category.py         # 分類 Schema
│   │   ├── activity.py         # 活動 Schema
│   │   ├── auth.py             # 認證 Schema
│   │   ├── upload.py           # 上傳 Schema
│   │   ├── statistics.py       # 統計資料 Schema
│   │   └── common.py           # 共用 Schema (分頁、回應)
│   │
│   ├── services/               # 業務邏輯層
│   │   ├── __init__.py
│   │   ├── auth_service.py     # 認證服務
│   │   ├── user_service.py     # 使用者服務
│   │   ├── file_service.py     # 檔案服務
│   │   ├── category_service.py # 分類服務
│   │   ├── activity_service.py # 活動記錄服務
│   │   ├── upload_service.py   # 上傳服務
│   │   ├── qdrant_service.py   # 向量資料庫服務
│   │   ├── rag_service.py      # RAG 服務
│   │   └── cache_service.py    # 快取服務
│   │
│   ├── core/                   # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py         # 安全相關 (JWT, 密碼)
│   │   ├── database.py         # 資料庫連線
│   │   ├── redis.py            # Redis 連線
│   │   ├── exceptions.py       # 自定義例外
│   │   ├── middleware.py       # 中介軟體
│   │   └── logging.py          # 日誌配置
│   │
│   ├── utils/                  # 工具函式
│   │   ├── __init__.py
│   │   ├── file_utils.py       # 檔案處理工具
│   │   ├── text_extraction.py # 文字提取
│   │   ├── validators.py       # 驗證器
│   │   └── helpers.py          # 輔助函式
│   │
│   └── tasks/                  # Celery 背景任務
│       ├── __init__.py
│       ├── celery_app.py       # Celery 應用程式
│       ├── file_tasks.py       # 檔案處理任務
│       ├── vector_tasks.py     # 向量化任務
│       └── backup_tasks.py     # 備份任務
│
├── alembic/                    # 資料庫遷移
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── tests/                      # 測試
│   ├── __init__.py
│   ├── conftest.py             # pytest 配置
│   ├── test_auth.py
│   ├── test_files.py
│   ├── test_categories.py
│   └── test_rag.py
│
├── docker/                     # Docker 配置
│   ├── Dockerfile
│   ├── Dockerfile.worker       # Celery Worker
│   └── nginx.conf              # Nginx 配置
│
├── scripts/                    # 工具腳本
│   ├── init_db.py              # 初始化資料庫
│   ├── create_admin.py         # 建立管理員
│   └── migrate.sh              # 遷移腳本
│
├── uploads/                    # 上傳檔案目錄 (開發環境)
│   └── .gitkeep
│
├── logs/                       # 日誌目錄
│   └── .gitkeep
│
├── .env                        # 環境變數
├── .env.example                # 環境變數範例
├── .gitignore
├── alembic.ini                 # Alembic 配置
├── docker-compose.yml          # Docker Compose 配置
├── requirements.txt            # Python 依賴
├── requirements-dev.txt        # 開發依賴
├── pytest.ini                  # pytest 配置
└── README.md                   # 專案說明
```

---

## 核心檔案說明

### 1. app/main.py (應用程式入口)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, files, categories, activities, upload, users, departments, settings, statistics
from app.core.config import settings as app_settings
from app.core.middleware import LoggingMiddleware, RateLimitMiddleware
from app.core.exceptions import setup_exception_handlers

# 建立 FastAPI 應用程式
app = FastAPI(
    title=app_settings.APP_NAME,
    version="1.0.0",
    description="RAG 知識庫管理系統後端 API",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定義中介軟體
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# 註冊例外處理器
setup_exception_handlers(app)

# 註冊路由
app.include_router(auth.router, prefix="/api/auth", tags=["認證"])
app.include_router(files.router, prefix="/api/files", tags=["檔案管理"])
app.include_router(categories.router, prefix="/api/categories", tags=["分類管理"])
app.include_router(activities.router, prefix="/api/activities", tags=["活動記錄"])
app.include_router(upload.router, prefix="/api/upload", tags=["批次上傳"])
app.include_router(users.router, prefix="/api/users", tags=["使用者管理"])
app.include_router(departments.router, prefix="/api/departments", tags=["處室管理"])
app.include_router(settings.router, prefix="/api/settings", tags=["系統設定"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["統計資料"])

@app.get("/")
async def root():
    return {"message": "RAG Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

### 2. app/config.py (配置管理)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 應用設定
    APP_NAME: str = "RAG Knowledge Base"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api"
    
    # 安全設定
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # 資料庫
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "rag_documents"
    
    # 檔案上傳
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    UPLOAD_DIR: str = "./uploads"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

### 3. app/core/database.py (資料庫連線)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 建立異步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 建立 Session Factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 依賴注入
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

### 4. app/core/security.py (安全功能)

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# 密碼加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """產生密碼雜湊"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """建立 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """解碼 JWT Token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
```

---

### 5. app/dependencies.py (全域依賴)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.models.user import User
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """取得當前使用者"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效的認證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解碼 Token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # 查詢使用者
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="帳號已停用")
    
    return user

async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """驗證管理員權限"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return current_user

async def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """驗證超級管理員權限"""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="需要超級管理員權限")
    return current_user
```

---

### 6. app/tasks/celery_app.py (Celery 配置)

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    'rag_tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.file_tasks',
        'app.tasks.vector_tasks',
        'app.tasks.backup_tasks'
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Taipei',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
)
```

---

### 7. docker-compose.yml (Docker Compose)

```yaml
version: '3.8'

services:
  # PostgreSQL 資料庫
  postgres:
    image: postgres:16
    container_name: rag_postgres
    environment:
      POSTGRES_DB: rag_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: rag_redis
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant 向量資料庫
  qdrant:
    image: qdrant/qdrant:latest
    container_name: rag_qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333

  # FastAPI 後端
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
      - ./uploads:/app/uploads
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/rag_db
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started

  # Celery Worker
  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_celery_worker
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    volumes:
      - .:/app
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/rag_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - postgres
      - redis
      - backend

  # Flower (Celery 監控)
  flower:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_flower
    command: celery -A app.tasks.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - redis
      - celery_worker

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

---

## 開發工作流程

### 1. 專案初始化
```bash
# 建立專案目錄
mkdir rag_web_backend
cd rag_web_backend

# 建立虛擬環境
python -m venv venv
.\venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 複製環境變數範例
copy .env.example .env
# 編輯 .env 填入實際值
```

### 2. 資料庫初始化
```bash
# 初始化 Alembic
alembic init alembic

# 建立初始遷移
alembic revision --autogenerate -m "Initial tables"

# 執行遷移
alembic upgrade head

# 建立預設資料
python scripts/init_db.py
```

### 3. 啟動開發伺服器
```bash
# 啟動 FastAPI
uvicorn app.main:app --reload

# 或使用 Docker Compose
docker-compose up -d
```

### 4. 測試
```bash
# 執行測試
pytest

# 測試涵蓋率
pytest --cov=app tests/
```

---

**下一步**: 閱讀 [06_CODE_EXAMPLES.md](./06_CODE_EXAMPLES.md) 查看完整程式碼範例
