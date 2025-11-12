# 👨‍💻 開發指南

## 給 GitHub Copilot 的使用說明

> 當你使用 Copilot 開發此後端專案時，請遵循以下指南

---

## 🎯 專案概述

這是一個 **RAG (Retrieval-Augmented Generation) 知識庫管理系統** 的後端 API：

- **框架**: FastAPI (Python 3.11+)
- **資料庫**: PostgreSQL 16 + Redis + Qdrant
- **任務佇列**: Celery
- **部署**: Docker Compose
- **前端專案**: `rag_web_admin` (React + Vite)

---

## 📋 開發前必讀

### 1. 資料隔離原則

**核心概念**: 每個處室 (department) 的資料必須完全隔離

```python
# ✅ 正確：自動過濾處室
@router.get("/files")
async def get_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 自動過濾當前使用者的處室資料
    query = select(File).where(File.department_id == current_user.department_id)
    # ...

# ❌ 錯誤：未過濾處室
@router.get("/files")
async def get_files(db: AsyncSession = Depends(get_db)):
    query = select(File)  # 會返回所有處室的資料！
```

### 2. 權限檢查層級

```python
from app.dependencies import (
    get_current_user,        # 一般使用者
    get_current_active_admin, # 管理員（admin）
    get_current_super_admin   # 超級管理員（super_admin）
)

# 一般使用者端點
@router.get("/files")
async def get_files(current_user: User = Depends(get_current_user)):
    pass

# 管理員端點（處室管理員）
@router.post("/categories")
async def create_category(current_user: User = Depends(get_current_active_admin)):
    pass

# 超級管理員端點（跨處室操作）
@router.post("/departments")
async def create_department(current_user: User = Depends(get_current_super_admin)):
    pass
```

### 3. 異步程式設計規範

**FastAPI 完全支援 async/await，請使用異步模式**

```python
# ✅ 正確：異步資料庫操作
@router.get("/files/{file_id}")
async def get_file(file_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    return file

# ❌ 錯誤：混用同步操作
@router.get("/files/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):  # 錯誤的 Session
    file = db.query(File).filter(File.id == file_id).first()  # 舊式查詢
    return file
```

---

## 🏗️ 程式碼結構規範

### 分層架構

```
請求 → 路由層 (api/) → 服務層 (services/) → 模型層 (models/) → 資料庫
```

#### 路由層 (api/v1/files.py)
- **職責**: 接收 HTTP 請求、參數驗證、呼叫服務層
- **不應該**: 直接操作資料庫、包含業務邏輯

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 只負責接收請求和呼叫服務
    result = await file_service.upload_file(
        db=db,
        file=file,
        category_id=category_id,
        uploader_id=current_user.id,
        department_id=current_user.department_id
    )
    return result
```

#### 服務層 (services/file_service.py)
- **職責**: 業務邏輯、資料處理、資料庫操作
- **應該**: 可重用、獨立測試

```python
class FileService:
    async def upload_file(
        self,
        db: AsyncSession,
        file: UploadFile,
        category_id: int,
        uploader_id: int,
        department_id: int
    ) -> File:
        # 1. 驗證
        self._validate_file(file)
        
        # 2. 儲存檔案
        file_path = await self._save_file(file, department_id)
        
        # 3. 建立資料庫記錄
        db_file = File(
            filename=file_path,
            # ...
        )
        db.add(db_file)
        await db.commit()
        
        # 4. 記錄活動
        await activity_service.log_activity(...)
        
        return db_file
```

---

## 🔐 安全開發規範

### 1. 密碼處理

```python
from app.core.security import get_password_hash, verify_password

# ✅ 正確：使用 bcrypt 雜湊
hashed_password = get_password_hash("user_password")

# ✅ 正確：驗證密碼
is_valid = verify_password("input_password", hashed_password)

# ❌ 永遠不要：
password = "plain_text_password"  # 不要儲存明文密碼！
```

### 2. SQL Injection 防護

```python
# ✅ 正確：使用 SQLAlchemy ORM（自動參數化）
query = select(File).where(File.filename == user_input)

# ✅ 正確：使用參數綁定
query = text("SELECT * FROM files WHERE filename = :filename")
result = await db.execute(query, {"filename": user_input})

# ❌ 危險：字串拼接 SQL
query = f"SELECT * FROM files WHERE filename = '{user_input}'"  # SQL Injection!
```

### 3. 輸入驗證

```python
from pydantic import BaseModel, Field, validator

class FileUploadRequest(BaseModel):
    category_id: int = Field(..., gt=0, description="分類 ID")
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('description')
    def sanitize_description(cls, v):
        if v:
            # 清理 HTML 標籤
            return re.sub(r'<[^>]+>', '', v)
        return v
```

---

## 📊 資料庫操作規範

### SQLAlchemy 2.0 查詢語法

```python
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload

# 基本查詢
stmt = select(File).where(File.id == file_id)
result = await db.execute(stmt)
file = result.scalar_one_or_none()

# 關聯查詢（避免 N+1 問題）
stmt = select(File).options(
    joinedload(File.category),
    joinedload(File.uploader)
).where(File.id == file_id)

# 聚合查詢
stmt = select(func.count(File.id)).where(File.department_id == dept_id)
total = await db.scalar(stmt)

# 複雜條件
stmt = select(File).where(
    and_(
        File.department_id == dept_id,
        or_(
            File.status == "completed",
            File.status == "processing"
        )
    )
)
```

### 交易處理

```python
# 自動交易（推薦）
async def create_category(db: AsyncSession, ...):
    category = Category(...)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

# 手動交易（需要回滾時）
async def batch_operation(db: AsyncSession, ...):
    try:
        # 多個操作
        db.add(obj1)
        db.add(obj2)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise
```

---

## 🎨 API 設計規範

### RESTful 端點命名

```python
# ✅ 正確的 RESTful 設計
GET    /api/files           # 列表
POST   /api/files           # 建立
GET    /api/files/{id}      # 詳情
PUT    /api/files/{id}      # 更新（全部）
PATCH  /api/files/{id}      # 更新（部分）
DELETE /api/files/{id}      # 刪除

# ✅ 子資源
GET    /api/files/{id}/download      # 下載檔案
POST   /api/files/{id}/vectorize     # 向量化檔案

# ✅ 統計與動作
GET    /api/categories/stats         # 統計資料
POST   /api/settings/backup          # 執行動作

# ❌ 避免：
GET    /api/getFiles                 # 不要在 URL 中使用動詞
POST   /api/file_create              # 不好的命名
```

### 回應格式標準化

```python
# 成功回應（單一資源）
{
    "id": 1,
    "filename": "document.pdf",
    "createdAt": "2025-10-31T10:00:00Z"
}

# 成功回應（列表 + 分頁）
{
    "items": [...],
    "total": 156,
    "page": 1,
    "pages": 16
}

# 錯誤回應
{
    "detail": "檔案不存在",
    "error_code": "FILE_NOT_FOUND",
    "status_code": 404
}
```

### Pydantic Schema 定義

```python
# schemas/file.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FileBase(BaseModel):
    """基礎 Schema"""
    filename: str
    description: Optional[str] = None

class FileCreate(FileBase):
    """建立時使用"""
    category_id: int

class FileUpdate(BaseModel):
    """更新時使用（所有欄位可選）"""
    description: Optional[str] = None
    category_id: Optional[int] = None

class FileResponse(FileBase):
    """回應時使用"""
    id: int
    file_size: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy 2.0 新語法
```

---

## 🧪 測試規範

### 測試結構

```python
# tests/test_files.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_upload_file(async_client: AsyncClient, auth_headers: dict):
    """測試檔案上傳"""
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    data = {"category_id": 1, "description": "Test file"}
    
    response = await async_client.post(
        "/api/files/upload",
        files=files,
        data=data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_get_files_with_department_isolation(
    async_client: AsyncClient,
    auth_headers_dept1: dict,
    auth_headers_dept2: dict
):
    """測試處室資料隔離"""
    # 處室1的使用者
    response1 = await async_client.get(
        "/api/files",
        headers=auth_headers_dept1
    )
    files1 = response1.json()["items"]
    
    # 處室2的使用者
    response2 = await async_client.get(
        "/api/files",
        headers=auth_headers_dept2
    )
    files2 = response2.json()["items"]
    
    # 應該看到不同的檔案
    assert files1 != files2
```

---

## 🚀 效能最佳化

### 1. 資料庫查詢優化

```python
# ❌ N+1 查詢問題
files = await db.execute(select(File))
for file in files:
    category = await db.get(Category, file.category_id)  # 每次都查詢！

# ✅ 使用 joinedload 預載入
stmt = select(File).options(joinedload(File.category))
files = await db.execute(stmt)
for file in files:
    print(file.category.name)  # 不會觸發額外查詢
```

### 2. Redis 快取

```python
from app.core.redis import get_redis

async def get_categories_cached(
    db: AsyncSession,
    redis: Redis = Depends(get_redis)
):
    # 嘗試從快取讀取
    cache_key = "categories:all"
    cached = await redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # 快取未命中，查詢資料庫
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    
    # 儲存到快取（1小時）
    await redis.setex(
        cache_key,
        3600,
        json.dumps([c.dict() for c in categories])
    )
    
    return categories
```

### 3. 背景任務

```python
# ❌ 同步處理（會阻塞回應）
@router.post("/files/upload")
async def upload_file(...):
    # 儲存檔案
    file_path = save_file(file)
    
    # 處理檔案（耗時操作）
    text = extract_text(file_path)  # 可能需要 10 秒
    vectors = vectorize(text)       # 可能需要 30 秒
    store_vectors(vectors)
    
    return {"status": "completed"}  # 使用者等待 40 秒

# ✅ 使用 Celery 背景任務
@router.post("/files/upload")
async def upload_file(...):
    # 只儲存檔案
    file_path = save_file(file)
    
    # 觸發背景任務
    process_file_task.delay(file_id)
    
    return {"status": "pending"}  # 立即回應
```

---

## 📝 程式碼風格

### 命名規範

```python
# 變數和函式：snake_case
user_name = "John"
def get_user_by_id(user_id: int):
    pass

# 類別：PascalCase
class FileService:
    pass

class UserSchema(BaseModel):
    pass

# 常數：UPPER_SNAKE_CASE
MAX_FILE_SIZE = 52428800
DEFAULT_PAGE_SIZE = 10

# 私有方法：前綴底線
class FileService:
    def upload_file(self):
        return self._validate_file()
    
    def _validate_file(self):  # 私有方法
        pass
```

### 型別註解

```python
# ✅ 使用完整型別註解
from typing import Optional, List, Dict, Any

def get_files(
    department_id: int,
    page: int = 1,
    limit: int = 10
) -> List[File]:
    pass

async def process_data(
    data: Dict[str, Any]
) -> Optional[str]:
    pass
```

### 文件字串

```python
def upload_file(
    db: AsyncSession,
    file: UploadFile,
    category_id: int
) -> File:
    """
    上傳檔案並建立資料庫記錄
    
    Args:
        db: 資料庫 Session
        file: 上傳的檔案物件
        category_id: 分類 ID
        
    Returns:
        File: 建立的檔案記錄
        
    Raises:
        ValueError: 當檔案格式不支援時
        HTTPException: 當分類不存在時
        
    Example:
        >>> file = await upload_file(db, upload_file, 1)
        >>> print(file.id)
        123
    """
    pass
```

---

## 🐛 常見錯誤與解決

### 1. 忘記 await
```python
# ❌ 錯誤
result = db.execute(select(File))  # 返回 coroutine，不是結果

# ✅ 正確
result = await db.execute(select(File))
```

### 2. 忘記 commit
```python
# ❌ 錯誤：資料不會保存
db.add(new_file)
return new_file

# ✅ 正確
db.add(new_file)
await db.commit()
await db.refresh(new_file)
return new_file
```

### 3. 循環導入
```python
# ❌ 錯誤：models/file.py
from app.models.category import Category  # 如果 category.py 也導入 file.py

# ✅ 正確：使用字串引用
class File(Base):
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship('Category', back_populates='files')
```

---

## 🎓 學習資源

- **FastAPI 官方文檔**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **Pydantic**: https://docs.pydantic.dev/
- **Celery**: https://docs.celeryq.dev/
- **LangChain**: https://python.langchain.com/

---

## 🤖 給 Copilot 的提示詞範例

當開發新功能時，可以這樣提示 Copilot：

```
# 提示 1: 建立新的 API 端點
"""
建立一個處室管理的 API 端點：
- 路由: /api/departments
- 方法: GET, POST, PUT, DELETE
- 需要超級管理員權限
- 遵循專案的分層架構（路由 -> 服務 -> 模型）
- 使用 SQLAlchemy 2.0 異步語法
"""

# 提示 2: 實作服務層
"""
實作 DepartmentService 類別：
- 方法: get_all, get_by_id, create, update, delete
- 使用異步資料庫操作
- 包含錯誤處理
- 記錄活動日誌
"""

# 提示 3: 撰寫測試
"""
為 DepartmentService 撰寫單元測試：
- 使用 pytest 和 AsyncClient
- 測試 CRUD 操作
- 測試權限驗證
- 使用 fixtures 建立測試資料
"""
```

---

**專案完成度**: ✅ 文件齊全，可開始開發！
