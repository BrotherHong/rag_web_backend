#!/bin/bash
set -e

echo "==================================="
echo "Starting RAG Web Backend"
echo "==================================="

# 等待資料庫準備就緒
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h postgres -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "PostgreSQL is ready!"

# 執行資料庫遷移
echo "Running database migrations..."
export ALEMBIC_CONFIG_DATABASE_URL="${DATABASE_URL}"
alembic upgrade head

# 檢查是否需要初始化資料（檢查是否已有處室資料）
echo "Checking if database initialization is needed..."
INIT_CHECK=$(python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def check_init():
    database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@db:5432/rag_web')
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM departments'))
        count = result.scalar()
    await engine.dispose()
    return count

count = asyncio.run(check_init())
print('yes' if count == 0 else 'no')
" 2>/dev/null || echo "yes")

if [ "$INIT_CHECK" = "yes" ]; then
    echo "Initializing database with default data..."
    
    # 初始化基礎資料
    echo "Creating departments, categories, and admin users..."
    python scripts/init_db.py
    
    # 初始化系統設定
    echo "Creating system settings..."
    python scripts/init_system_settings.py
    
    echo "Database initialization completed!"
else
    echo "Database already initialized, skipping initialization."
fi

echo "==================================="
echo "Starting FastAPI application..."
echo "==================================="

# 啟動應用程式
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
