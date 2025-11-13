"""Qdrant 向量資料庫連線管理"""

from typing import AsyncGenerator
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings

# 全域 Qdrant 客戶端
qdrant_client: QdrantClient = None

# Collection 名稱
COLLECTION_NAME = "rag_documents"


async def init_qdrant():
    """初始化 Qdrant 連線並創建 Collection"""
    global qdrant_client
    
    # 建立客戶端連線
    qdrant_client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=30
    )
    
    # 檢查 Collection 是否存在，不存在則創建
    collections = qdrant_client.get_collections()
    collection_names = [col.name for col in collections.collections]
    
    if COLLECTION_NAME not in collection_names:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIM,  # 向量維度
                distance=models.Distance.COSINE  # 使用餘弦相似度
            )
        )
    
    return qdrant_client


async def close_qdrant():
    """關閉 Qdrant 連線"""
    global qdrant_client
    if qdrant_client:
        qdrant_client.close()


async def get_qdrant() -> AsyncGenerator[QdrantClient, None]:
    """
    Qdrant 依賴注入
    
    使用方式:
        @router.get("/search")
        async def vector_search(qdrant: QdrantClient = Depends(get_qdrant)):
            results = await qdrant.search(
                collection_name=COLLECTION_NAME,
                query_vector=[0.1, 0.2, ...],
                limit=10
            )
            return results
    """
    if qdrant_client is None:
        await init_qdrant()
    yield qdrant_client
