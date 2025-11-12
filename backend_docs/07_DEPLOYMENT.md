# 🚀 部署指南

## 部署架構選擇

### 開發環境
```
本地開發 → Python虛擬環境 → SQLite/PostgreSQL
```

### 測試環境
```
Docker Compose → 容器化服務 → 內部網路測試
```

### 生產環境
```
Docker + Nginx + PostgreSQL + Redis + Qdrant
或
Kubernetes 叢集部署（大規模）
```

---

## 1. Docker 部署（推薦）

### Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 建立必要目錄
RUN mkdir -p /app/uploads /app/logs

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 啟動命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Docker Compose 完整配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 資料庫
  postgres:
    image: postgres:16-alpine
    container_name: rag_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-rag_db}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - rag_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: rag_redis
    restart: always
    command: >
      redis-server
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --requirepass ${REDIS_PASSWORD:-redis123}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - rag_network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant 向量資料庫
  qdrant:
    image: qdrant/qdrant:latest
    container_name: rag_qdrant
    restart: always
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - rag_network
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334

  # FastAPI 後端
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_backend
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-rag_db}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started
    networks:
      - rag_network

  # Celery Worker
  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_celery_worker
    restart: always
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=100
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-rag_db}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - redis
      - backend
    networks:
      - rag_network

  # Flower (Celery 監控)
  flower:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: rag_flower
    restart: always
    command: celery -A app.tasks.celery_app flower --port=5555 --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin123}
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-redis123}@redis:6379/2
    depends_on:
      - redis
      - celery_worker
    networks:
      - rag_network

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: rag_nginx
    restart: always
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/ssl:/etc/nginx/ssl:ro  # SSL 憑證
      - nginx_logs:/var/log/nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    networks:
      - rag_network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  qdrant_data:
    driver: local
  nginx_logs:
    driver: local

networks:
  rag_network:
    driver: bridge
```

---

### Nginx 配置

```nginx
# docker/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    # 速率限制
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    
    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }
    
    # HTTPS 主伺服器
    server {
        listen 443 ssl http2;
        server_name your-domain.com;
        
        # SSL 憑證
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        # 安全標頭
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000" always;
        
        # 檔案上傳大小限制
        client_max_body_size 100M;
        
        # API 路由
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket 支援
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # 超時設定
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # 前端靜態檔案
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
        
        # 健康檢查
        location /health {
            proxy_pass http://backend/health;
            access_log off;
        }
    }
}
```

---

## 2. 環境變數配置

### .env.production

```env
# 應用設定
APP_NAME=RAG Knowledge Base
DEBUG=False
API_V1_PREFIX=/api

# 安全金鑰（請使用 openssl rand -hex 32 生成）
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this-too
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 資料庫
POSTGRES_DB=rag_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-strong-password
DATABASE_URL=postgresql+asyncpg://postgres:your-strong-password@postgres:5432/rag_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_PASSWORD=redis-strong-password
REDIS_URL=redis://:redis-strong-password@redis:6379/0
REDIS_CACHE_TTL=3600

# Celery
CELERY_BROKER_URL=redis://:redis-strong-password@redis:6379/1
CELERY_RESULT_BACKEND=redis://:redis-strong-password@redis:6379/2

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=rag_documents

# 檔案上傳
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf,.docx,.txt,.md
UPLOAD_DIR=/app/uploads

# CORS
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Flower（Celery 監控）
FLOWER_USER=admin
FLOWER_PASSWORD=flower-admin-password
```

---

## 3. 部署步驟

### 步驟 1: 準備伺服器

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安裝 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 驗證安裝
docker --version
docker-compose --version
```

---

### 步驟 2: 部署後端

```bash
# 1. Clone 專案
cd /opt
sudo git clone https://github.com/BrotherHong/rag_web_backend.git
cd rag_web_backend

# 2. 設定環境變數
sudo cp .env.example .env.production
sudo nano .env.production  # 編輯並填入實際值

# 3. 建立必要目錄
sudo mkdir -p uploads logs docker/ssl

# 4. 生成 SSL 憑證（測試用）
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/key.pem \
  -out docker/ssl/cert.pem

# 5. 建構並啟動服務
sudo docker-compose --env-file .env.production up -d --build

# 6. 查看日誌
sudo docker-compose logs -f backend

# 7. 執行資料庫遷移
sudo docker-compose exec backend alembic upgrade head

# 8. 建立超級管理員
sudo docker-compose exec backend python scripts/create_admin.py
```

---

### 步驟 3: 驗證部署

```bash
# 檢查所有容器狀態
sudo docker-compose ps

# 預期輸出：
# NAME                STATUS              PORTS
# rag_backend         Up                  0.0.0.0:8000->8000/tcp
# rag_postgres        Up (healthy)        0.0.0.0:5432->5432/tcp
# rag_redis           Up (healthy)        0.0.0.0:6379->6379/tcp
# rag_qdrant          Up                  0.0.0.0:6333->6333/tcp
# rag_celery_worker   Up
# rag_flower          Up                  0.0.0.0:5555->5555/tcp
# rag_nginx           Up                  0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp

# 測試 API
curl http://localhost:8000/health
# 預期回應: {"status":"healthy"}

# 測試 Swagger 文檔
# 開啟瀏覽器: http://your-server-ip:8000/api/docs
```

---

## 4. 資料庫備份與恢復

### 自動備份腳本

```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/opt/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rag_db_$TIMESTAMP.sql.gz"

# 建立備份目錄
mkdir -p $BACKUP_DIR

# 執行備份
docker exec rag_postgres pg_dump -U postgres rag_db | gzip > $BACKUP_FILE

# 保留最近 30 天的備份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

### 設定 Cron 定時備份

```bash
# 每天凌晨 2 點執行備份
sudo crontab -e

# 加入以下行
0 2 * * * /opt/rag_web_backend/scripts/backup_db.sh >> /var/log/backup.log 2>&1
```

### 恢復資料庫

```bash
# 從備份恢復
gunzip -c /opt/backups/postgres/rag_db_20251031_020000.sql.gz | \
  docker exec -i rag_postgres psql -U postgres -d rag_db
```

---

## 5. 監控與日誌

### 應用監控

```bash
# 查看容器資源使用
docker stats

# 查看後端日誌
docker logs -f rag_backend --tail 100

# 查看 Celery Worker 日誌
docker logs -f rag_celery_worker --tail 100

# 查看 Nginx 訪問日誌
docker exec rag_nginx tail -f /var/log/nginx/access.log
```

### Flower 監控面板

訪問 `http://your-server-ip:5555` 查看 Celery 任務狀態

---

## 6. 更新部署

```bash
# 1. 拉取最新程式碼
cd /opt/rag_web_backend
sudo git pull origin master

# 2. 重新建構並啟動
sudo docker-compose --env-file .env.production up -d --build

# 3. 執行資料庫遷移
sudo docker-compose exec backend alembic upgrade head

# 4. 重啟服務
sudo docker-compose restart backend celery_worker
```

---

## 7. 故障排除

### 常見問題

1. **資料庫連線失敗**
```bash
# 檢查 PostgreSQL 是否正常運行
docker logs rag_postgres

# 重啟資料庫
docker-compose restart postgres
```

2. **Redis 連線失敗**
```bash
# 測試 Redis 連線
docker exec rag_redis redis-cli -a your-redis-password ping

# 應回傳: PONG
```

3. **Celery 任務卡住**
```bash
# 重啟 Worker
docker-compose restart celery_worker

# 清空任務佇列
docker exec rag_redis redis-cli -a your-redis-password FLUSHDB
```

---

## 8. 安全檢查清單

- ✅ 修改所有預設密碼
- ✅ 使用強加密金鑰（SECRET_KEY, JWT_SECRET_KEY）
- ✅ 啟用 HTTPS（生產環境）
- ✅ 配置防火牆規則
- ✅ 定期更新系統和 Docker 映像
- ✅ 設定自動備份
- ✅ 限制 API 速率
- ✅ 配置日誌輪轉
- ✅ 使用環境變數管理敏感資訊
- ✅ 啟用容器健康檢查

---

**下一步**: 閱讀 [08_DEVELOPMENT_GUIDE.md](./08_DEVELOPMENT_GUIDE.md) 了解開發指南
