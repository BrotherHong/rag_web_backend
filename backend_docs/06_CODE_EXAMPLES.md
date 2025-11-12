# 💻 核心程式碼範例

## 完整模組實作範例

### 1. 檔案上傳完整流程

#### app/api/v1/files.py (路由層)

```python
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.file import FileUploadResponse, FileListResponse, FileDetailResponse
from app.services.file_service import FileService
from app.tasks.file_tasks import process_file_task

router = APIRouter()
file_service = FileService()

@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    category_id: int = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳單一檔案
    
    - **file**: 檔案資料 (multipart/form-data)
    - **category_id**: 分類 ID
    - **description**: 檔案描述 (可選)
    
    回傳上傳成功的檔案資訊
    """
    try:
        # 呼叫服務層處理上傳
        result = await file_service.upload_file(
            db=db,
            file=file,
            category_id=category_id,
            description=description,
            uploader_id=current_user.id,
            department_id=current_user.department_id
        )
        
        # 觸發背景處理任務
        process_file_task.delay(result.id)
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

@router.get("/", response_model=FileListResponse)
async def get_files(
    page: int = 1,
    limit: int = 10,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得檔案列表（自動過濾處室）"""
    result = await file_service.get_files(
        db=db,
        department_id=current_user.department_id,
        page=page,
        limit=limit,
        category_id=category_id,
        search=search
    )
    return result

@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得檔案詳細資訊"""
    file = await file_service.get_file_by_id(db, file_id)
    
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 權限檢查
    if file.department_id != current_user.department_id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限存取此檔案")
    
    return file

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除檔案"""
    success = await file_service.delete_file(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        department_id=current_user.department_id,
        is_super_admin=current_user.is_super_admin
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="檔案不存在或無權限刪除")
    
    return {"message": "檔案已刪除"}
```

---

#### app/services/file_service.py (業務邏輯層)

```python
import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.orm import joinedload
import aiofiles
import math

from app.models.file import File
from app.models.category import Category
from app.schemas.file import FileUploadResponse, FileListResponse, FileDetailResponse
from app.core.config import settings
from app.services.activity_service import ActivityService

activity_service = ActivityService()

class FileService:
    """檔案管理服務"""
    
    async def upload_file(
        self,
        db: AsyncSession,
        file: UploadFile,
        category_id: int,
        uploader_id: int,
        department_id: int,
        description: Optional[str] = None
    ) -> File:
        """
        處理檔案上傳
        
        Args:
            db: 資料庫 Session
            file: 上傳的檔案
            category_id: 分類 ID
            uploader_id: 上傳者 ID
            department_id: 處室 ID
            description: 檔案描述
            
        Returns:
            File: 建立的檔案記錄
        """
        # 1. 驗證檔案大小
        file.file.seek(0, 2)  # 移到檔案末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置到開頭
        
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"檔案過大，最大允許 {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB")
        
        # 2. 驗證檔案類型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支援的檔案格式: {file_ext}")
        
        # 3. 驗證分類是否存在且屬於該處室
        category = await db.get(Category, category_id)
        if not category or category.department_id != department_id:
            raise ValueError("分類不存在或不屬於您的處室")
        
        # 4. 生成唯一檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{timestamp}_{unique_id}_{file.filename}"
        
        # 5. 建立儲存目錄
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(department_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, safe_filename)
        
        # 6. 異步儲存檔案
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 7. 建立資料庫記錄
        db_file = File(
            filename=safe_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_ext[1:],  # 去掉點號
            mime_type=file.content_type,
            category_id=category_id,
            department_id=department_id,
            uploader_id=uploader_id,
            description=description,
            status="pending"
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        # 8. 更新分類檔案計數
        category.file_count += 1
        await db.commit()
        
        # 9. 記錄活動
        await activity_service.log_activity(
            db=db,
            user_id=uploader_id,
            action="upload",
            entity_type="file",
            entity_id=db_file.id,
            description=f"上傳檔案: {file.filename}",
            department_id=department_id
        )
        
        return db_file
    
    async def get_files(
        self,
        db: AsyncSession,
        department_id: int,
        page: int = 1,
        limit: int = 10,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc"
    ) -> FileListResponse:
        """
        取得檔案列表（分頁、篩選、搜尋）
        """
        # 1. 建立基礎查詢
        query = select(File).where(File.department_id == department_id)
        
        # 2. 載入關聯資料
        query = query.options(
            joinedload(File.category),
            joinedload(File.uploader)
        )
        
        # 3. 分類篩選
        if category_id:
            query = query.where(File.category_id == category_id)
        
        # 4. 搜尋
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    File.original_filename.ilike(search_pattern),
                    File.description.ilike(search_pattern)
                )
            )
        
        # 5. 排序
        order_column = getattr(File, sort, File.created_at)
        if order == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # 6. 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # 7. 分頁
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # 8. 執行查詢
        result = await db.execute(query)
        files = result.scalars().unique().all()
        
        return FileListResponse(
            items=files,
            total=total,
            page=page,
            pages=math.ceil(total / limit) if total > 0 else 0
        )
    
    async def get_file_by_id(
        self,
        db: AsyncSession,
        file_id: int
    ) -> Optional[File]:
        """根據 ID 取得檔案"""
        query = select(File).where(File.id == file_id).options(
            joinedload(File.category),
            joinedload(File.uploader),
            joinedload(File.department)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def delete_file(
        self,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        department_id: int,
        is_super_admin: bool = False
    ) -> bool:
        """
        刪除檔案
        
        Returns:
            bool: 是否刪除成功
        """
        # 1. 取得檔案
        file = await self.get_file_by_id(db, file_id)
        if not file:
            return False
        
        # 2. 權限檢查
        if not is_super_admin and file.department_id != department_id:
            return False
        
        # 3. 刪除實體檔案
        if os.path.exists(file.file_path):
            try:
                os.remove(file.file_path)
            except Exception as e:
                print(f"刪除實體檔案失敗: {e}")
        
        # 4. 更新分類計數
        if file.category:
            file.category.file_count = max(0, file.category.file_count - 1)
        
        # 5. 刪除資料庫記錄
        await db.delete(file)
        await db.commit()
        
        # 6. 記錄活動
        await activity_service.log_activity(
            db=db,
            user_id=user_id,
            action="delete",
            entity_type="file",
            entity_id=file_id,
            description=f"刪除檔案: {file.original_filename}",
            department_id=department_id
        )
        
        return True
```

---

### 2. 認證系統完整實作

#### app/api/v1/auth.py

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.auth import LoginRequest, LoginResponse, TokenVerifyResponse
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    使用者登入
    
    - **username**: 使用者名稱
    - **password**: 密碼
    
    回傳 JWT Token 和使用者資訊
    """
    result = await auth_service.authenticate_user(
        db=db,
        redis=redis,
        username=credentials.username,
        password=credentials.password
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return result

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """使用者登出"""
    await auth_service.logout_user(
        redis=redis,
        db=db,
        user_id=current_user.id,
        username=current_user.username
    )
    
    return {"message": "登出成功"}

@router.get("/verify", response_model=TokenVerifyResponse)
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """驗證 Token 是否有效"""
    return TokenVerifyResponse(
        valid=True,
        user=current_user
    )

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """刷新 Token"""
    new_token = await auth_service.refresh_token(
        redis=redis,
        user_id=current_user.id,
        username=current_user.username
    )
    
    return {"token": new_token}
```

---

#### app/services/auth_service.py

```python
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginResponse
from app.schemas.user import UserSchema
from app.services.activity_service import ActivityService

activity_service = ActivityService()

class AuthService:
    """認證服務"""
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        redis: Redis,
        username: str,
        password: str
    ) -> Optional[LoginResponse]:
        """
        驗證使用者並生成 Token
        """
        # 1. 查詢使用者
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # 2. 驗證密碼
        if not verify_password(password, user.hashed_password):
            return None
        
        # 3. 檢查帳號是否啟用
        if not user.is_active:
            return None
        
        # 4. 生成 JWT Token
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "department_id": user.department_id
        }
        access_token = create_access_token(data=token_data)
        
        # 5. 儲存 Session 到 Redis (24小時)
        session_key = f"session:{user.id}"
        await redis.setex(session_key, 86400, access_token)
        
        # 6. 更新最後登入時間
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # 7. 記錄登入活動
        await activity_service.log_activity(
            db=db,
            user_id=user.id,
            action="login",
            description=f"{user.username} 登入系統",
            department_id=user.department_id
        )
        
        return LoginResponse(
            token=access_token,
            user=UserSchema.from_orm(user)
        )
    
    async def logout_user(
        self,
        redis: Redis,
        db: AsyncSession,
        user_id: int,
        username: str
    ) -> bool:
        """使用者登出"""
        # 1. 刪除 Redis Session
        session_key = f"session:{user_id}"
        await redis.delete(session_key)
        
        # 2. 記錄登出活動
        await activity_service.log_activity(
            db=db,
            user_id=user_id,
            action="logout",
            description=f"{username} 登出系統"
        )
        
        return True
    
    async def refresh_token(
        self,
        redis: Redis,
        user_id: int,
        username: str
    ) -> str:
        """刷新 Token"""
        # 生成新 Token
        token_data = {
            "sub": username,
            "user_id": user_id
        }
        new_token = create_access_token(data=token_data)
        
        # 更新 Redis Session
        session_key = f"session:{user_id}"
        await redis.setex(session_key, 86400, new_token)
        
        return new_token
```

---

### 3. Celery 背景任務

#### app/tasks/file_tasks.py

```python
from celery import Task
from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.file import File
from app.utils.text_extraction import extract_text_from_file
from app.services.qdrant_service import QdrantService
from sqlalchemy import select
import asyncio

qdrant_service = QdrantService()

class DatabaseTask(Task):
    """支援異步資料庫的 Celery Task"""
    
    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))
    
    async def run(self, *args, **kwargs):
        raise NotImplementedError()

@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
async def process_file_task(self, file_id: int):
    """
    處理檔案：提取文字、向量化、儲存到 Qdrant
    
    Args:
        file_id: 檔案 ID
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 取得檔案
            result = await db.execute(select(File).where(File.id == file_id))
            file = result.scalar_one_or_none()
            
            if not file:
                return {"status": "error", "message": "檔案不存在"}
            
            # 2. 更新狀態為處理中
            file.status = "processing"
            await db.commit()
            
            # 3. 提取文字
            text = await extract_text_from_file(file.file_path, file.file_type)
            
            if not text:
                file.status = "failed"
                file.processing_error = "無法提取文字內容"
                await db.commit()
                return {"status": "error", "message": "文字提取失敗"}
            
            # 4. 向量化並儲存
            vector_count = await qdrant_service.vectorize_and_store(
                file_id=file.id,
                text=text,
                metadata={
                    "filename": file.original_filename,
                    "department_id": file.department_id,
                    "category_id": file.category_id
                }
            )
            
            # 5. 更新檔案狀態
            file.status = "completed"
            file.is_vectorized = True
            file.vector_count = vector_count
            await db.commit()
            
            return {
                "status": "success",
                "file_id": file_id,
                "vector_count": vector_count
            }
        
        except Exception as e:
            # 錯誤處理
            file.status = "failed"
            file.processing_error = str(e)
            await db.commit()
            
            # 重試機制
            raise self.retry(exc=e, countdown=60)
```

---

### 4. RAG 查詢服務

#### app/services/rag_service.py

```python
from typing import List, Dict, Any
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings

class RAGService:
    """RAG 查詢服務"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
    
    async def query(
        self,
        question: str,
        department_id: int,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        RAG 查詢
        
        Args:
            question: 使用者問題
            department_id: 處室 ID（資料隔離）
            top_k: 返回最相關的 K 個文件片段
            
        Returns:
            包含回答和引用來源的字典
        """
        # 1. 將問題向量化
        query_vector = await self.embeddings.aembed_query(question)
        
        # 2. 在 Qdrant 中搜尋相關文件（過濾處室）
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="department_id",
                        match=MatchValue(value=department_id)
                    )
                ]
            )
        )
        
        # 3. 提取文件內容
        contexts = []
        sources = []
        
        for hit in search_result:
            contexts.append(hit.payload.get("text", ""))
            sources.append({
                "file_id": hit.payload.get("file_id"),
                "filename": hit.payload.get("filename"),
                "score": hit.score
            })
        
        if not contexts:
            return {
                "answer": "抱歉，我在知識庫中找不到相關資訊。",
                "sources": []
            }
        
        # 4. 組合 Prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "你是一個專業的助理，根據提供的文件內容回答問題。"),
            ("user", """
參考資料：
{context}

問題：{question}

請根據上述參考資料回答問題。如果參考資料中沒有相關資訊，請誠實告知。
            """)
        ])
        
        context_text = "\n\n".join([f"[文件 {i+1}]\n{ctx}" for i, ctx in enumerate(contexts)])
        
        # 5. 呼叫 LLM 生成回答
        messages = prompt_template.format_messages(
            context=context_text,
            question=question
        )
        
        response = await self.llm.agenerate([messages])
        answer = response.generations[0][0].text
        
        return {
            "answer": answer,
            "sources": sources[:3],  # 只返回前 3 個來源
            "total_sources": len(sources)
        }
```

---

### 5. Redis 快取服務

#### app/core/redis.py

```python
from redis.asyncio import Redis, ConnectionPool
from typing import Optional, Any
import json
from app.core.config import settings

# 建立連線池
redis_pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50
)

async def get_redis() -> Redis:
    """取得 Redis 連線"""
    redis = Redis(connection_pool=redis_pool)
    try:
        yield redis
    finally:
        await redis.close()

class CacheService:
    """快取服務"""
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.default_ttl = settings.REDIS_CACHE_TTL
    
    async def get(self, key: str) -> Optional[Any]:
        """取得快取"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """設定快取"""
        ttl = ttl or self.default_ttl
        serialized = json.dumps(value)
        return await self.redis.setex(key, ttl, serialized)
    
    async def delete(self, key: str) -> bool:
        """刪除快取"""
        return await self.redis.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """檢查快取是否存在"""
        return await self.redis.exists(key) > 0
```

---

**下一步**: 閱讀 [07_DEPLOYMENT.md](./07_DEPLOYMENT.md) 了解部署流程
