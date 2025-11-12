# 🛠️ 技術堆疊與依賴

## Python 環境

```bash
Python 3.11+  # 推薦 3.11 或 3.12
```

---

## 核心依賴 (requirements.txt)

```txt
# Web 框架
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9

# 資料庫 ORM
sqlalchemy>=2.0.35
asyncpg>=0.29.0              # PostgreSQL 異步驅動
alembic>=1.13.0              # 資料庫遷移

# 快取與佇列
redis>=5.0.0
celery>=5.4.0
flower>=2.0.0                # Celery 監控

# 認證與安全
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# 資料驗證
pydantic>=2.9.0
pydantic-settings>=2.5.0
email-validator>=2.2.0

# 檔案處理
python-magic>=0.4.27
pypdf2>=3.0.0
python-docx>=1.1.0
pillow>=10.4.0

# 向量與 RAG
qdrant-client>=1.11.0
langchain>=0.3.0
langchain-openai>=0.2.0
openai>=1.51.0
tiktoken>=0.7.0

# 物件儲存
minio>=7.2.0

# 工具
python-dotenv>=1.0.0
httpx>=0.27.0
aiofiles>=24.1.0

# 監控與日誌
prometheus-client>=0.21.0
python-json-logger>=2.0.0

# 開發工具
pytest>=8.3.0
pytest-asyncio>=0.24.0
black>=24.8.0
flake8>=7.1.0
mypy>=1.11.0
```

---

## 資料庫與中介軟體

### PostgreSQL
```yaml
version: "16"
extensions:
  - pg_trgm       # 模糊搜尋
  - pgvector      # 向量擴展 (可選)
```

### Redis
```yaml
version: "7"
configuration:
  maxmemory: 2gb
  maxmemory-policy: allkeys-lru
  appendonly: yes
```

### Qdrant
```yaml
version: "latest"
configuration:
  storage:
    storage_path: /qdrant/storage
  service:
    http_port: 6333
```

### MinIO (可選)
```yaml
version: "latest"
configuration:
  MINIO_ROOT_USER: admin
  MINIO_ROOT_PASSWORD: password
```

---

## 開發工具

### IDE 推薦
- **VS Code** + 擴展:
  - Python
  - Pylance
  - Docker
  - REST Client
  - GitLens

### API 測試
- **Swagger UI**: `http://localhost:8000/docs` (FastAPI 內建)
- **ReDoc**: `http://localhost:8000/redoc`
- **Postman**: 手動測試
- **pytest**: 自動化測試

### 資料庫管理
- **DBeaver**: 通用資料庫工具
- **pgAdmin**: PostgreSQL 專用
- **Redis Commander**: Redis GUI

---

## FastAPI 功能特性

### 自動文檔生成
```python
# 訪問 http://localhost:8000/docs
# 自動生成互動式 API 文檔 (Swagger UI)
```

### 資料驗證 (Pydantic)
```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    department_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "hr_admin",
                "email": "hr@ncku.edu.tw",
                "password": "SecurePass123",
                "department_id": 1
            }
        }
```

### 依賴注入
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 資料庫 Session 依賴
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# 當前使用者依賴
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # 驗證 Token 並返回使用者
    pass

# 使用依賴
@router.get("/files")
async def get_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pass
```

### 異步支援
```python
# 完整的異步支援
@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    db: AsyncSession = Depends(get_db)
):
    # 異步檔案讀取
    content = await file.read()
    
    # 異步資料庫操作
    result = await db.execute(query)
    
    # 異步 HTTP 請求
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=content)
```

---

## SQLAlchemy 2.0 特性

### 異步 ORM
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# 建立異步引擎
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    echo=True
)

# 異步 Session
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)
```

### 現代查詢語法
```python
from sqlalchemy import select

# 舊版 (1.x)
files = session.query(File).filter(File.category == 'pdf').all()

# 新版 (2.0)
stmt = select(File).where(File.category == 'pdf')
result = await session.execute(stmt)
files = result.scalars().all()
```

---

## Celery 任務佇列

### 配置
```python
from celery import Celery

celery = Celery(
    'rag_tasks',
    broker='redis://localhost:6379/1',
    backend='redis://localhost:6379/2'
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Taipei',
    enable_utc=True,
)
```

### 任務定義
```python
@celery.task(bind=True, max_retries=3)
def process_file(self, file_id: int):
    try:
        # 1. 提取文字
        text = extract_text(file_id)
        
        # 2. 分塊
        chunks = split_text(text)
        
        # 3. 向量化
        embeddings = create_embeddings(chunks)
        
        # 4. 儲存到 Qdrant
        store_vectors(file_id, embeddings)
        
        return {"status": "success", "chunks": len(chunks)}
    except Exception as exc:
        # 重試機制
        raise self.retry(exc=exc, countdown=60)
```

---

## LangChain RAG 配置

### 文件載入器
```python
from langchain.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader
)

# 根據檔案類型選擇載入器
loaders = {
    '.pdf': PyPDFLoader,
    '.docx': Docx2txtLoader,
    '.txt': TextLoader
}
```

### 文字分塊
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,          # 每塊最大字元數
    chunk_overlap=200,        # 塊之間的重疊
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)
```

### 向量儲存
```python
from langchain.vectorstores import Qdrant
from langchain.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002"
)

vectorstore = Qdrant(
    client=qdrant_client,
    collection_name="rag_documents",
    embeddings=embeddings
)
```

### RAG Chain
```python
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(
        search_kwargs={"k": 5}  # 取前 5 個最相關文件
    )
)
```

---

## Docker 容器化

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/rag_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - qdrant

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: rag_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  celery_worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    depends_on:
      - redis
      - postgres

volumes:
  postgres_data:
  qdrant_data:
```

---

## 環境變數管理

### .env 範例
```env
# 應用設定
APP_NAME=RAG Knowledge Base
DEBUG=False
SECRET_KEY=your-super-secret-key-here

# 資料庫
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/rag_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# MinIO (可選)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password
MINIO_BUCKET=rag-files

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 檔案上傳
MAX_FILE_SIZE=52428800  # 50MB
ALLOWED_EXTENSIONS=.pdf,.docx,.txt
```

---

**下一步**: 閱讀 [03_DATABASE_DESIGN.md](./03_DATABASE_DESIGN.md) 了解資料庫設計
