"""模擬 RAG 處理器 (Mock RAG Processor)

用於開發和測試階段，模擬 RAG 查詢流程。
實際的 LangChain + OpenAI 實現完成後，可直接替換此模擬器。
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.rag_processor_interface import (
    IRAGProcessor,
    RAGQueryResult,
    DocumentChunk,
    QueryType,
    SearchScope
)


class MockRAGProcessor(IRAGProcessor):
    """模擬 RAG 處理器
    
    模擬 RAG 查詢的各個步驟，用於測試和演示。
    生成模擬的答案和來源文檔。
    """
    
    def __init__(
        self,
        response_delay: float = 1.0,
        enable_logging: bool = True
    ):
        """初始化模擬處理器
        
        Args:
            response_delay: 響應延遲時間（秒）
            enable_logging: 是否啟用日誌輸出
        """
        self.response_delay = response_delay
        self.enable_logging = enable_logging
        
        # 模擬向量存儲（實際應該在 Qdrant 中）
        self._vector_store: Dict[int, Dict[str, Any]] = {}
        
        # 模擬知識庫
        self._mock_knowledge = {
            "資料隔離": "資料隔離原則是指每個處室的資料必須完全隔離，不同處室之間不能互相存取資料。",
            "權限管理": "系統分為三種權限層級：一般使用者、處室管理員和超級管理員。",
            "檔案上傳": "支援 PDF、DOCX、TXT、MD 等格式，單個檔案最大 50MB。",
            "向量化": "檔案上傳後會自動進行文字擷取、分塊和向量嵌入處理。",
            "搜尋功能": "系統支援語義搜尋、關鍵字搜尋和混合搜尋三種模式。"
        }
    
    def _log(self, message: str):
        """日誌輸出"""
        if self.enable_logging:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[MockRAGProcessor {timestamp}] {message}")
    
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
        """執行模擬 RAG 查詢"""
        
        self._log(f"收到查詢: '{query_text}' (處室: {department_id})")
        
        start_time = datetime.now()
        
        # 模擬處理延遲
        await asyncio.sleep(self.response_delay)
        
        # 1. 模擬向量搜尋
        sources = await self._mock_vector_search(
            query_text, 
            department_id, 
            top_k
        )
        
        # 2. 生成模擬答案
        answer = self._generate_mock_answer(query_text, sources)
        
        # 3. 計算處理時間
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 4. 模擬 Token 使用
        tokens_used = len(query_text) * 2 + len(answer)
        
        result = RAGQueryResult(
            query=query_text,
            answer=answer,
            sources=sources,
            tokens_used=tokens_used,
            processing_time=processing_time,
            metadata={
                "query_type": query_type.value,
                "scope": scope.value,
                "model": "mock-gpt-4",
                "department_id": department_id
            }
        )
        
        self._log(f"查詢完成，找到 {len(sources)} 個相關文檔")
        
        return result
    
    async def _mock_vector_search(
        self,
        query_text: str,
        department_id: int,
        top_k: int
    ) -> List[DocumentChunk]:
        """模擬向量搜尋"""
        
        sources = []
        
        # 根據查詢關鍵字匹配知識庫
        matched_topics = []
        query_lower = query_text.lower()
        
        for topic, content in self._mock_knowledge.items():
            if any(keyword in query_lower for keyword in topic.lower().split()):
                matched_topics.append((topic, content))
        
        # 如果沒有匹配，隨機選擇
        if not matched_topics:
            matched_topics = random.sample(
                list(self._mock_knowledge.items()), 
                min(2, len(self._mock_knowledge))
            )
        
        # 生成模擬的 DocumentChunk
        for i, (topic, content) in enumerate(matched_topics[:top_k]):
            chunk = DocumentChunk(
                file_id=random.randint(1, 10),
                chunk_id=i,
                content=content,
                score=random.uniform(0.7, 0.95),  # 模擬相關性分數
                metadata={
                    "topic": topic,
                    "filename": f"文檔_{topic}.pdf",
                    "page": random.randint(1, 50)
                }
            )
            sources.append(chunk)
        
        # 按分數排序
        sources.sort(key=lambda x: x.score, reverse=True)
        
        return sources
    
    def _generate_mock_answer(
        self,
        query_text: str,
        sources: List[DocumentChunk]
    ) -> str:
        """生成模擬答案"""
        
        if not sources:
            return "抱歉，我在知識庫中找不到相關的資訊來回答您的問題。"
        
        # 組合來源內容
        context = "\n\n".join([source.content for source in sources[:3]])
        
        # 生成模擬答案（實際應該用 LLM）
        answer_templates = [
            f"根據系統文檔，{context[:100]}...\n\n這是基於 {len(sources)} 個相關文檔的回答。",
            f"關於您的問題，系統找到以下資訊：\n\n{context[:150]}...\n\n希望這能回答您的疑問。",
            f"依據知識庫內容，{context[:120]}...\n\n（此回答參考了 {len(sources)} 份相關文件）"
        ]
        
        return random.choice(answer_templates)
    
    async def vectorize_document(
        self,
        file_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """模擬文檔向量化"""
        
        self._log(f"開始向量化文檔 ID: {file_id}")
        
        # 模擬處理時間
        await asyncio.sleep(self.response_delay * 0.5)
        
        # 模擬分塊
        chunk_size = 500
        chunks = [
            content[i:i+chunk_size] 
            for i in range(0, len(content), chunk_size)
        ]
        chunk_count = len(chunks)
        
        # 模擬向量生成（實際應該調用 OpenAI Embeddings）
        vectors = [
            [random.uniform(-1, 1) for _ in range(1536)]  # 1536 維向量
            for _ in chunks
        ]
        
        # 儲存到模擬向量存儲
        self._vector_store[file_id] = {
            "chunks": chunks,
            "vectors": vectors,
            "metadata": metadata or {},
            "created_at": datetime.now()
        }
        
        self._log(f"文檔 ID {file_id} 向量化完成: {chunk_count} 個區塊")
        
        return {
            "chunk_count": chunk_count,
            "vector_count": len(vectors),
            "embedding_model": "mock-text-embedding-ada-002"
        }
    
    async def delete_document_vectors(
        self,
        file_id: int
    ) -> bool:
        """刪除文檔向量"""
        
        if file_id in self._vector_store:
            del self._vector_store[file_id]
            self._log(f"已刪除文檔 ID {file_id} 的向量")
            return True
        
        self._log(f"文檔 ID {file_id} 的向量不存在")
        return False
    
    async def search_similar_documents(
        self,
        query_text: str,
        department_id: int,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """語義搜尋相似文檔"""
        
        self._log(f"搜尋相似文檔: '{query_text}'")
        
        # 使用內部的向量搜尋方法
        return await self._mock_vector_search(query_text, department_id, top_k)
    
    async def get_document_summary(
        self,
        file_id: int
    ) -> Optional[str]:
        """取得文檔摘要"""
        
        if file_id not in self._vector_store:
            return None
        
        # 模擬生成摘要（實際應該用 LLM）
        doc_info = self._vector_store[file_id]
        chunk_count = len(doc_info["chunks"])
        
        summaries = [
            f"本文檔包含 {chunk_count} 個主要段落，涵蓋了系統操作、權限管理和資料處理等主題。",
            f"此文件共分為 {chunk_count} 個章節，詳細說明了系統的功能和使用方法。",
            f"這是一份包含 {chunk_count} 個部分的技術文檔，提供了完整的操作指南。"
        ]
        
        return random.choice(summaries)


# 預設的模擬處理器實例
mock_rag_processor = MockRAGProcessor(
    response_delay=0.8,  # 較短的延遲以加快測試
    enable_logging=True
)
