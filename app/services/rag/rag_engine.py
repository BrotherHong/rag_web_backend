#!/usr/bin/env python3
"""
RAG引擎 - 整合檢索和生成（Web Backend版本）
"""

import os
from typing import List, Dict, Optional
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.prompts.rag import RAG_ANSWER_PROMPT, RAG_NO_RESULTS_PROMPT
from .vector_store import VectorStore
from .reranker import Reranker


class RAGEngine:
    """
    檢索增強生成引擎
    """
    
    def __init__(self, 
                 base_path="uploads/1/processed",
                 base_url="https://primehub.aic.ncku.edu.tw/console/apps/ollama-0-11-10-z0s7s",
                 model="qwen2.5:32b",
                 similarity_threshold=0.1,
                 max_context_docs=3):
        """
        初始化RAG引擎
        
        參數:
            base_path: 處理後文件的基礎路徑
            base_url: Ollama伺服器地址
            model: 用於生成回答的模型
            similarity_threshold: 相似度閾值
            max_context_docs: 用於上下文的最大文檔數
        """
        self.client = OllamaClient(base_url=base_url, model=model)
        self.vector_store = VectorStore(base_path=base_path)
        self.similarity_threshold = similarity_threshold
        self.max_context_docs = max_context_docs
        self.reranker = Reranker()
        
    def query(self, question: str, 
              top_k: int = 250, 
              include_similarity_scores: bool = False) -> Dict:
        """
        執行RAG查詢
        
        參數:
            question: 用戶問題
            top_k: 檢索文檔數量
            include_similarity_scores: 是否在結果中包含相似度分數
            
        返回:
            查詢結果字典
        """
        print(f"\n=== RAG查詢 ===")
        print(f"問題: {question}")
        
        # 1. 檢索相關文檔
        similar_docs = self.vector_store.search_similar(
            query_text=question,
            top_k=top_k,
            similarity_threshold=self.similarity_threshold
        )
        
        if not similar_docs:
            # 沒有找到相關文檔
            return {
                'question': question,
                'answer': RAG_NO_RESULTS_PROMPT,
                'sources': [],
                'retrieved_docs': 0
            }
        
        # 準備候選文檔並進行 rerank
        candidates = [{
            'document': doc['document'],
            'similarity': doc['similarity'],
            'summary': self.vector_store.get_document_summary(doc['document']['filename']) or ''
        } for doc in similar_docs]
        reranked_docs = self.reranker.rerank(question, candidates)
        
        # 2. 使用 top N 文檔構建上下文
        top_docs = reranked_docs[:self.max_context_docs]
        
        # 3. 生成詳細回答
        context = self._build_context(top_docs)
        prompt = RAG_ANSWER_PROMPT.format(query=question, context=context)
        response = self.client.generate(prompt)
        
        # 4. 整理結果
        sources = []
        for doc_result in reranked_docs[:self.max_context_docs]:
            doc_info = doc_result['document']
            filename = doc_info['filename']
            original_filename = doc_info.get('original_filename', filename)  # ✅ 優先使用 original_filename
            
            # 動態載入路徑資訊
            doc_content = self.vector_store.get_document_content(filename)
            original_path = doc_content['original_path'] if doc_content else ''
            source_link = doc_content['source_link'] if doc_content else ''
            download_link = doc_content['download_link'] if doc_content else ''
            
            source = {
                'filename': original_filename,  # ✅ 使用原始檔名
                'original_path': original_path,
                'source_link': source_link,
                'download_link': download_link
            }
            if include_similarity_scores:
                source['similarity'] = doc_result['similarity']
                source['score'] = doc_result['score']
            sources.append(source)
        
        result = {
            'question': question,
            'answer': response,
            'sources': sources,
            'retrieved_docs': len(similar_docs),
            'used_for_answer': len(top_docs)
        }
        
        # 顯示結果
        print(f"\n=== 回答結果 ===")
        print(f"檢索 {len(similar_docs)} 個文檔，使用 Top {len(top_docs)} 生成回答")
        print(f"\n來源文檔:")
        for i, source in enumerate(sources, 1):
            if include_similarity_scores:
                print(f"  {i}. {source['filename']} (相似度: {source['similarity']:.4f}, Rerank: {source['score']:.4f})")
            else:
                print(f"  {i}. {source['filename']}")
        
        return result
    
    def _build_context(self, top_docs):
        """建立上下文字串"""
        context_parts = []
        for i, doc in enumerate(top_docs, 1):
            document = doc['document']
            filename = document['filename']
            original_filename = document.get('original_filename', filename)  # ✅ 優先使用原始檔名
            
            # 從 vector_store 獲取文檔完整內容
            doc_content = self.vector_store.get_document_content(filename)
            if doc_content and doc_content.get('original_content'):
                content = doc_content['original_content']
                context_parts.append(f"文檔{i}（{original_filename}）：\n{content}\n")  # ✅ 使用原始檔名
            else:
                # 如果無法獲取內容，使用摘要
                summary = doc.get('summary', '')
                context_parts.append(f"文檔{i}（{original_filename}）：\n{summary}\n")  # ✅ 使用原始檔名
        
        return "\n".join(context_parts)
    
    def get_system_stats(self) -> Dict:
        """
        獲取系統統計信息
        
        返回:
            系統統計字典
        """
        vector_stats = self.vector_store.get_stats()
        
        return {
            'model': self.client.model,
            'similarity_threshold': self.similarity_threshold,
            'max_context_docs': self.max_context_docs,
            'vector_store_stats': vector_stats
        }
