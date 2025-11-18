"""RAG 處理器標準接口

定義 RAG 查詢處理的標準接口，用於整合外部 LLM 和向量搜尋模組。
實際的 LangChain + OpenAI 實現可以在不修改核心系統的情況下接入。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class QueryType(str, Enum):
    """查詢類型"""
    SIMPLE = "simple"           # 簡單查詢
    SEMANTIC = "semantic"       # 語義搜尋
    HYBRID = "hybrid"           # 混合搜尋（關鍵字+語義）
    CONVERSATIONAL = "conversational"  # 對話式查詢


class SearchScope(str, Enum):
    """搜尋範圍"""
    ALL = "all"                 # 所有檔案
    CATEGORY = "category"       # 指定分類
    FILES = "files"             # 指定檔案
    DEPARTMENT = "department"   # 指定處室


class DocumentChunk:
    """文檔區塊類（搜尋結果）"""
    
    def __init__(
        self,
        file_id: int,
        chunk_id: int,
        content: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file_id = file_id
        self.chunk_id = chunk_id
        self.content = content
        self.score = score  # 相關性分數 (0-1)
        self.metadata = metadata or {}


class RAGQueryResult:
    """RAG 查詢結果類"""
    
    def __init__(
        self,
        query: str,
        answer: str,
        sources: List[DocumentChunk],
        tokens_used: int = 0,
        processing_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.query = query
        self.answer = answer
        self.sources = sources
        self.tokens_used = tokens_used
        self.processing_time = processing_time
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class IRAGProcessor(ABC):
    """RAG 處理器標準接口
    
    定義 RAG 查詢處理的標準方法，包含向量搜尋、文檔檢索和答案生成。
    外部 LangChain 實現只需實現此接口即可無縫整合。
    
    使用範例：
        processor = YourRAGProcessor(
            openai_api_key="...",
            model_name="gpt-4",
            qdrant_client=qdrant_client
        )
        
        result = await processor.query(
            query_text="什麼是資料隔離原則？",
            department_id=1,
            scope=SearchScope.ALL
        )
    """
    
    @abstractmethod
    async def query(
        self,
        query_text: str,
        department_id: int,
        scope: SearchScope = SearchScope.ALL,
        scope_ids: Optional[List[int]] = None,
        query_type: QueryType = QueryType.SEMANTIC,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None
    ) -> RAGQueryResult:
        """執行 RAG 查詢
        
        Args:
            query_text: 使用者查詢文字
            department_id: 處室 ID（資料隔離）
            scope: 搜尋範圍
            scope_ids: 範圍限定 ID 列表（分類 ID 或檔案 ID）
            query_type: 查詢類型
            top_k: 返回最相關的 K 個文檔區塊
            options: 額外選項（如 temperature, max_tokens 等）
            
        Returns:
            RAGQueryResult: 查詢結果，包含答案和來源
        """
        pass
    
    @abstractmethod
    async def vectorize_document(
        self,
        file_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """將文檔向量化並存儲
        
        Args:
            file_id: 檔案 ID
            content: 文檔內容
            metadata: 元資料（如檔案名、分類等）
            
        Returns:
            Dict: 包含 chunk_count, vector_count 等資訊
        """
        pass
    
    @abstractmethod
    async def delete_document_vectors(
        self,
        file_id: int
    ) -> bool:
        """刪除文檔的向量
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            bool: 是否成功刪除
        """
        pass
    
    @abstractmethod
    async def search_similar_documents(
        self,
        query_text: str,
        department_id: int,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """語義搜尋相似文檔
        
        Args:
            query_text: 查詢文字
            department_id: 處室 ID
            top_k: 返回數量
            filters: 過濾條件（如分類、檔案類型等）
            
        Returns:
            List[DocumentChunk]: 相似文檔區塊列表
        """
        pass
    
    @abstractmethod
    async def get_document_summary(
        self,
        file_id: int
    ) -> Optional[str]:
        """取得文檔摘要
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            Optional[str]: 文檔摘要，若無則返回 None
        """
        pass


class RAGProcessorRegistry:
    """RAG 處理器註冊器
    
    用於管理多個 RAG 處理器實現，支援動態切換。
    """
    
    def __init__(self):
        self._processors: Dict[str, IRAGProcessor] = {}
    
    def register(self, name: str, processor: IRAGProcessor):
        """註冊處理器
        
        Args:
            name: 處理器名稱
            processor: 處理器實例
        """
        self._processors[name] = processor
    
    def get(self, name: str) -> Optional[IRAGProcessor]:
        """取得處理器
        
        Args:
            name: 處理器名稱
            
        Returns:
            Optional[IRAGProcessor]: 處理器實例，若不存在則返回 None
        """
        return self._processors.get(name)
    
    def list_processors(self) -> List[str]:
        """列出所有註冊的處理器名稱"""
        return list(self._processors.keys())
