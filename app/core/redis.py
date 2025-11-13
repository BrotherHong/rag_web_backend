"""Redis 連線與快取管理"""

from typing import AsyncGenerator
import redis.asyncio as redis
from app.config import settings

# 全域 Redis 客戶端
redis_client: redis.Redis = None


async def init_redis():
    """初始化 Redis 連線"""
    global redis_client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10
    )
    return redis_client


async def close_redis():
    """關閉 Redis 連線"""
    global redis_client
    if redis_client:
        await redis_client.close()


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Redis 依賴注入
    
    使用方式:
        @router.get("/")
        async def get_cached(redis: Redis = Depends(get_redis)):
            value = await redis.get("key")
            return {"value": value}
    """
    if redis_client is None:
        await init_redis()
    yield redis_client
