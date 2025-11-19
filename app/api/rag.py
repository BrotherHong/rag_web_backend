"""RAG 查詢 API 路由"""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.query_history import QueryHistory
from app.schemas.rag import (
    QueryRequest,
    QueryResponse,
    DocumentSource,
    QueryHistoryListResponse,
    QueryHistoryItem,
    SearchRequest,
    SummaryRequest,
    SummaryResponse
)
from app.services.mock_rag_processor import mock_rag_processor
from app.services.rag_processor_interface import SearchScope, QueryType
from app.services.activity import activity_service

router = APIRouter(prefix="/rag", tags=["RAG查詢"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RAG 查詢
    
    - 使用語義搜尋找到相關文檔
    - 生成基於文檔的答案
    - 自動記錄查詢歷史
    - 處室資料隔離
    """
    try:
        # 解析參數
        scope = SearchScope(request.scope)
        query_type = QueryType(request.query_type)
        
        # 呼叫 RAG 處理器
        result = await mock_rag_processor.query(
            query_text=request.query,
            scope=scope,
            scope_ids=request.scope_ids,
            query_type=query_type,
            top_k=request.top_k
        )
        
        # 轉換來源格式並查詢檔案資訊
        sources = []
        for source in result.sources:
            # 查詢檔案資訊
            file = await db.get(File, source.file_id)
            file_name = file.original_filename if file else f"檔案_{source.file_id}"
            
            sources.append(DocumentSource(
                file_id=source.file_id,
                file_name=file_name,
                chunk_id=source.chunk_id,
                content=source.content,
                score=source.score
            ))
        
        # 儲存查詢歷史
        query_history = QueryHistory(
            query=result.query,
            answer=result.answer,
            sources=[s.model_dump() for s in sources],
            source_count=len(sources),
            query_type=request.query_type,
            scope=request.scope,
            tokens_used=result.tokens_used,
            processing_time=result.processing_time,
            user_id=current_user.id
        )
        
        db.add(query_history)
        await db.commit()
        
        # 記錄活動
        await activity_service.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="query",
            description=f"查詢: {request.query[:50]}...",
            department_id=current_user.department_id,
            extra_data={
                "query_type": request.query_type,
                "source_count": len(sources)
            }
        )
        
        return QueryResponse(
            query=result.query,
            answer=result.answer,
            sources=sources,
            tokens_used=result.tokens_used,
            processing_time=result.processing_time,
            timestamp=result.timestamp
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"參數錯誤: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查詢處理失敗: {str(e)}"
        )


@router.get("/history", response_model=QueryHistoryListResponse)
async def get_query_history(
    page: int = Query(1, ge=1, description="頁碼"),
    limit: int = Query(10, ge=1, le=100, description="每頁數量"),
    search: Optional[str] = Query(None, description="搜尋查詢內容"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得查詢歷史
    
    - 自動過濾處室
    - 支援搜尋和分頁
    - 按時間倒序排列
    """
    # 建立基礎查詢（自動過濾處室）
    query = select(QueryHistory).where(
        QueryHistory.department_id == current_user.department_id
    )
    
    # 搜尋
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            QueryHistory.query.ilike(search_pattern)
        )
    
    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 排序和分頁
    query = query.order_by(desc(QueryHistory.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # 執行查詢
    result = await db.execute(query)
    history_items = result.scalars().all()
    
    return QueryHistoryListResponse(
        items=[QueryHistoryItem.model_validate(item) for item in history_items],
        total=total,
        page=page,
        pages=math.ceil(total / limit) if total > 0 else 0
    )


@router.get("/history/{history_id}", response_model=QueryResponse)
async def get_query_history_detail(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得查詢歷史詳情
    
    - 包含完整的查詢和答案
    - 包含所有來源文檔
    - 權限檢查
    """
    history = await db.get(QueryHistory, history_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="查詢歷史不存在")
    
    # 權限檢查
    if history.department_id != current_user.department_id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限查看此查詢歷史")
    
    # 轉換來源格式
    sources = [DocumentSource(**s) for s in history.sources]
    
    return QueryResponse(
        query=history.query,
        answer=history.answer,
        sources=sources,
        tokens_used=history.tokens_used,
        processing_time=history.processing_time,
        timestamp=history.created_at
    )


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除查詢歷史
    
    - 只能刪除自己的查詢歷史
    - 管理員可以刪除處室內的所有歷史
    """
    history = await db.get(QueryHistory, history_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="查詢歷史不存在")
    
    # 權限檢查
    is_owner = history.user_id == current_user.id
    is_dept_admin = (
        current_user.role in ["admin", "super_admin"] and
        history.department_id == current_user.department_id
    )
    
    if not (is_owner or is_dept_admin):
        raise HTTPException(status_code=403, detail="無權限刪除此查詢歷史")
    
    await db.delete(history)
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="delete",
        description=f"刪除查詢歷史: {history.query[:50]}...",
        department_id=current_user.department_id
    )


@router.post("/search", response_model=QueryResponse)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """語義搜尋文檔
    
    - 只返回相似文檔，不生成答案
    - 支援過濾條件
    - 處室資料隔離
    """
    try:
        # 呼叫搜尋功能
        sources = await mock_rag_processor.search_similar_documents(
            query_text=request.query,
            top_k=request.top_k,
            filters=request.filters
        )
        
        # 轉換來源格式
        document_sources = []
        for source in sources:
            # 查詢檔案資訊
            file = await db.get(File, source.file_id)
            file_name = file.original_filename if file else f"檔案_{source.file_id}"
            
            document_sources.append(DocumentSource(
                file_id=source.file_id,
                file_name=file_name,
                chunk_id=source.chunk_id,
                content=source.content,
                score=source.score
            ))
        
        # 記錄活動
        await activity_service.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="search",
            description=f"搜尋文檔: {request.query[:50]}...",
            department_id=current_user.department_id
        )
        
        return QueryResponse(
            query=request.query,
            answer="",  # 搜尋模式不生成答案
            sources=document_sources,
            tokens_used=0,
            processing_time=0.0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜尋失敗: {str(e)}"
        )


@router.post("/summary", response_model=SummaryResponse)
async def get_document_summary(
    request: SummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得文檔摘要
    
    - 生成文檔內容摘要
    - 需要檔案已經向量化
    - 權限檢查
    """
    # 查詢檔案
    file = await db.get(File, request.file_id)
    
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 權限檢查
    if file.department_id != current_user.department_id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限查看此檔案")
    
    # 檢查是否已向量化
    if not file.is_vectorized:
        raise HTTPException(status_code=400, detail="檔案尚未處理完成")
    
    try:
        # 生成摘要
        summary = await mock_rag_processor.get_document_summary(request.file_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="無法生成摘要")
        
        # 記錄活動
        await activity_service.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="view",
            description=f"查看文檔摘要: {file.original_filename}",
            department_id=current_user.department_id
        )
        
        return SummaryResponse(
            file_id=file.id,
            file_name=file.original_filename,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成摘要失敗: {str(e)}"
        )
