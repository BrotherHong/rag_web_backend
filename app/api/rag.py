"""RAG 查詢 API 路由"""

import json
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.security import get_current_user
from app.config import settings
from app.models.user import User
from app.schemas.rag import (
    QueryRequest,
    QueryResponse,
    DocumentSource
)
from app.services.rag.rag_engine import RAGEngine
from app.services.activity import activity_service

router = APIRouter(prefix="/rag", tags=["RAG查詢"])


# 可選認證：允許匿名訪問
async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    可選的用戶認證
    如果提供 token 則驗證，否則返回 None（匿名用戶）
    """
    if not authorization:
        return None
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        
        if user_id:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            return result.scalar_one_or_none()
    except (JWTError, ValueError):
        pass
    
    return None

# TODO: Support multiple departments - currently hardcoded to department 1 (人事室)
DEPARTMENT_ID = 1
BASE_PATH = f"uploads/{DEPARTMENT_ID}/processed"

# Initialize RAG Engine
try:
    rag_engine = RAGEngine(base_path=BASE_PATH, debug_mode=True)  # 開啟 debug 模式
    print(f"✅ RAG Engine initialized with base_path: {BASE_PATH}")
except Exception as e:
    print(f"⚠️ Warning: Failed to initialize RAG Engine: {e}")
    rag_engine = None


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """RAG 查詢（公開端點，無需認證）
    
    - 使用語義搜尋找到相關文檔
    - 生成基於文檔的答案（使用真實 LLM）
    - 自動記錄查詢歷史（如果已登入）
    - 支援處室資料過濾
    """
    
    try:
        # 決定處室 ID：優先使用 scope_ids[0]，否則使用已登入用戶的處室
        department_id = None
        if request.scope_ids and len(request.scope_ids) > 0:
            department_id = request.scope_ids[0]
        elif current_user and current_user.department_id:
            department_id = current_user.department_id
        else:
            raise HTTPException(
                status_code=400,
                detail="未登入用戶必須指定 scope_ids"
            )
        
        # 動態初始化對應處室的 RAG 引擎
        base_path = f"uploads/{department_id}/processed"
        try:
            dept_rag_engine = RAGEngine(base_path=base_path, debug_mode=True)  # 開啟 debug 模式
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"處室 {department_id} 的 RAG 引擎未初始化，請確認系統配置和 embeddings 資料"
            )
        
        start_time = time.time()
        
        # Execute RAG query with real implementation (top_k fixed at 250)
        result = dept_rag_engine.query(
            question=request.query,
            top_k=250,
            include_similarity_scores=True  # Include scores for metadata
        )
        
        processing_time = time.time() - start_time
        
        # Convert sources to API format and fetch file_id from database
        sources = []
        for source in result['sources']:
            original_filename = source['filename']
            
            # Query database to find file_id
            from app.models.file import File as FileModel
            file_query = select(FileModel).where(
                FileModel.department_id == department_id,
                FileModel.original_filename == original_filename
            )
            file_result = await db.execute(file_query)
            file_record = file_result.scalar_one_or_none()
            
            if not file_record:
                # This should not happen - file record must exist for processed files
                print(f"⚠️ Warning: File record not found for {original_filename}")
                continue
            
            doc_source = DocumentSource(
                file_id=file_record.id,
                file_name=original_filename,
                source_link=source.get('source_link', ''),
                download_link=f"/public/files/{file_record.id}/download"  # 移除 /api 前綴，由前端的 BASE_URL 提供
            )
            sources.append(doc_source)
        
        # Log activity (only if user is authenticated)
        if current_user:
            await activity_service.log_activity(
                db=db,
                user_id=current_user.id,
                activity_type="query",
                description=f"查詢: {request.query[:50]}...",
                department_id=current_user.department_id,
                extra_data=json.dumps({
                    "source_count": len(sources),
                    "retrieved_docs": result.get('retrieved_docs', 0),
                    "query_department_id": department_id
                })
            )
        
        # Return simplified response
        return QueryResponse(
            query=request.query,
            answer=result['answer'],
            sources=sources
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"參數錯誤: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"查詢處理失敗: {str(e)}"
        )
