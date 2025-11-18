"""RAG 查詢相關的 Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """RAG 查詢請求"""
    
    query: str = Field(..., min_length=1, max_length=1000, description="查詢問題")
    scope: str = Field(default="all", description="搜尋範圍: all, category, files")
    scope_ids: Optional[List[int]] = Field(default=None, description="範圍限定 ID")
    query_type: str = Field(default="semantic", description="查詢類型: simple, semantic, hybrid")
    top_k: int = Field(default=5, ge=1, le=20, description="返回最相關的 K 個文檔")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "什麼是資料隔離原則？",
                "scope": "all",
                "query_type": "semantic",
                "top_k": 5
            }
        }


class DocumentSource(BaseModel):
    """文檔來源"""
    
    file_id: int = Field(..., description="檔案 ID")
    file_name: str = Field(..., description="檔案名稱")
    chunk_id: int = Field(..., description="文檔區塊 ID")
    content: str = Field(..., description="相關內容")
    score: float = Field(..., ge=0.0, le=1.0, description="相關性分數")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外資訊")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": 1,
                "file_name": "系統操作手冊.pdf",
                "chunk_id": 3,
                "content": "資料隔離原則是指每個處室的資料必須完全隔離...",
                "score": 0.92,
                "metadata": {"page": 15, "section": "安全規範"}
            }
        }


class QueryResponse(BaseModel):
    """RAG 查詢回應"""
    
    query: str = Field(..., description="原始查詢")
    answer: str = Field(..., description="生成的答案")
    sources: List[DocumentSource] = Field(..., description="來源文檔")
    tokens_used: int = Field(default=0, description="使用的 Token 數量")
    processing_time: float = Field(..., description="處理時間（秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="查詢時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外資訊")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "什麼是資料隔離原則？",
                "answer": "根據系統文檔，資料隔離原則是指每個處室的資料必須完全隔離...",
                "sources": [
                    {
                        "file_id": 1,
                        "file_name": "系統操作手冊.pdf",
                        "chunk_id": 3,
                        "content": "資料隔離原則...",
                        "score": 0.92,
                        "metadata": {"page": 15}
                    }
                ],
                "tokens_used": 250,
                "processing_time": 1.2,
                "timestamp": "2024-01-15T10:30:00",
                "metadata": {"model": "gpt-4", "query_type": "semantic"}
            }
        }


class QueryHistoryItem(BaseModel):
    """查詢歷史項目"""
    
    id: int
    query: str
    answer: str
    source_count: int = Field(..., description="來源數量")
    tokens_used: int
    processing_time: float
    created_at: datetime
    user_id: int
    department_id: int
    
    class Config:
        from_attributes = True


class QueryHistoryListResponse(BaseModel):
    """查詢歷史列表回應"""
    
    items: List[QueryHistoryItem]
    total: int
    page: int
    pages: int


class SearchRequest(BaseModel):
    """文檔搜尋請求"""
    
    query: str = Field(..., min_length=1, max_length=500, description="搜尋關鍵字")
    top_k: int = Field(default=10, ge=1, le=50, description="返回數量")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="過濾條件")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "檔案上傳",
                "top_k": 10,
                "filters": {"category_id": 1, "file_type": "pdf"}
            }
        }


class SummaryRequest(BaseModel):
    """文檔摘要請求"""
    
    file_id: int = Field(..., description="檔案 ID")


class SummaryResponse(BaseModel):
    """文檔摘要回應"""
    
    file_id: int
    file_name: str
    summary: str
    generated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": 1,
                "file_name": "系統操作手冊.pdf",
                "summary": "本文檔包含 10 個主要章節，涵蓋了系統安裝、配置、操作和維護等內容...",
                "generated_at": "2024-01-15T10:30:00"
            }
        }
