#!/usr/bin/env python3
"""
文檔Embedding處理器 - Web Backend版本
"""

import numpy as np
from typing import List, Optional
from app.models.llm.ollama_client import OllamaClient
from app.config import settings


class EmbeddingProcessor:
    """
    處理文檔摘要的向量化
    """
    
    def __init__(self, 
                 base_url: str = None,
                 embedding_model: str = None):
        """
        初始化Embedding處理器
        
        參數:
            base_url: Ollama伺服器地址（預設從設定檔讀取）
            embedding_model: 使用的embedding模型（預設從設定檔讀取）
        """
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.embedding_model = embedding_model or settings.OLLAMA_EMBEDDING_MODEL
        self.client = OllamaClient(base_url=self.base_url)
        
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        為文本生成embedding向量
        
        參數:
            text: 要向量化的文本
            
        返回:
            embedding向量或None(如果失敗)
        """
        try:
            # 使用Ollama的embedding API
            embedding = self.client.generate_embedding(text, model=self.embedding_model)
            return embedding
            
        except Exception as e:
            print(f"生成embedding失敗: {str(e)}")
            return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        計算兩個向量的余弦相似度
        
        參數:
            vec1, vec2: 要比較的向量
            
        返回:
            余弦相似度值 (0-1)
        """
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            print(f"相似度計算失敗: {str(e)}")
            return 0.0
