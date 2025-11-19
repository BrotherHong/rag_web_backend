# Docker 部署指南

## 📦 架構說明

本專案的 Docker 部署分為開發和生產兩種模式：

### 開發模式 (docker-compose.dev.yml)
```
本機
├── FastAPI 應用程式（本機運行，熱重載）
│
└── Docker 容器
    ├── PostgreSQL 16
    └── Redis 7 (可選)
```

### 生產模式 (docker-compose.yml)
```
全部在 Docker 中
├── PostgreSQL 容器
├── Backend 容器 (FastAPI)
├── Frontend 容器 (Nginx + React，來自 rag_web_admin)
└── Redis 容器 (可選)

Docker Network: rag_network
```

---

## 🚀 開發環境部署

**用於本機開發，FastAPI 在本機運行支援熱重載。**

### 1. 啟動資料庫

```bash
# 啟動 PostgreSQL 和 Redis
docker-compose -f docker-compose.dev.yml up -d

# 查看狀態
docker-compose -f docker-compose.dev.yml ps
```

### 2. 本機運行後端

```bash
# 啟動虛擬環境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 初始化資料庫（首次）
python scripts/init_db.py

# 啟動 FastAPI（熱重載）
python -m uvicorn app.main:app --reload
```

### 3. 管理指令

```bash
# 查看日誌
docker-compose -f docker-compose.dev.yml logs -f

# 停止資料庫
docker-compose -f docker-compose.dev.yml down

# 清除資料（危險）
docker-compose -f docker-compose.dev.yml down -v
```

---

## 🚀 生產環境部署

**完全容器化部署，包含前後端。**

## 🚀 生產環境部署

**完全容器化部署，包含前後端。**

### 1. 環境準備

```bash
# 複製環境變數範例
cp .env.production.example .env

# 編輯環境變數（重要！）
nano .env
```

必須修改的配置：

```bash
# 資料庫密碼（必須修改）
POSTGRES_PASSWORD=your_secure_password_here

# JWT 密鑰（使用以下指令生成）
# openssl rand -hex 32
SECRET_KEY=your_generated_secret_key_here

# CORS 設定（根據前端域名設定）
ALLOWED_ORIGINS=http://localhost:3000,http://yourdomain.com
```

### 2. 啟動服務

```bash
# 啟動所有服務（PostgreSQL + Backend）
docker-compose up -d

# 查看啟動日誌
docker-compose logs -f

# 檢查容器狀態
docker-compose ps
```

### 3. 初始化資料庫

```bash
# 執行資料庫 migration
docker exec -it rag_backend alembic upgrade head

# 創建超級管理員（可選，或通過 API 創建）
docker exec -it rag_backend python -c "
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
db = SessionLocal()
admin = User(
    username='admin',
    hashed_password=get_password_hash('admin123'),
    email='admin@example.com',
    role=UserRole.SUPER_ADMIN
)
db.add(admin)
db.commit()
"
```

### 4. 驗證部署

```bash
# 測試 API 健康檢查
curl http://localhost:8000/api/health

# 測試 API 文件
curl http://localhost:8000/docs
```

## 🔧 常用管理指令

### 容器管理

```bash
# 啟動服務
docker-compose up -d

# 停止服務
docker-compose down

# 重啟特定服務
docker-compose restart backend

# 查看日誌
docker-compose logs -f backend
docker-compose logs -f postgres

# 重建並重啟
docker-compose up -d --build
```

### 資料庫管理

```bash
# 進入資料庫
docker exec -it rag_postgres psql -U postgres -d rag_db

# 執行 migration
docker exec -it rag_backend alembic upgrade head

# 創建新 migration
docker exec -it rag_backend alembic revision --autogenerate -m "description"

# 查看 migration 狀態
docker exec -it rag_backend alembic current

# 備份資料庫
docker exec rag_postgres pg_dump -U postgres rag_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢復資料庫
cat backup.sql | docker exec -i rag_postgres psql -U postgres -d rag_db
```

### 進入容器

```bash
# 進入後端容器
docker exec -it rag_backend bash

# 進入資料庫容器
docker exec -it rag_postgres bash
```

## 🌐 網路配置

後端服務創建了一個 Docker 網路 `rag_network`，供前後端容器通訊使用。

### 網路資訊

```bash
# 查看網路詳情
docker network inspect rag_network

# 測試網路連通性
docker exec -it rag_backend ping rag_postgres
```

### 端口映射

- **8000**: FastAPI 後端 API
- **5432**: PostgreSQL（僅開發環境，生產環境建議不暴露）

## 📊 監控和日誌

### 容器狀態

```bash
# 查看所有容器
docker ps

# 查看資源使用
docker stats

# 查看健康狀態
docker inspect --format='{{.State.Health.Status}}' rag_backend
```

### 日誌管理

```bash
# 實時查看日誌
docker-compose logs -f

# 查看最近 100 行
docker-compose logs --tail=100 backend

# 保存日誌到文件
docker-compose logs > logs_$(date +%Y%m%d).txt
```

應用日誌位置（容器內）：
- `/app/logs/app.log` - 應用日誌
- `/app/logs/error.log` - 錯誤日誌

## 🔒 安全建議

1. **修改預設密碼**
   ```bash
   # 絕不使用預設的 postgres123
   POSTGRES_PASSWORD=use_strong_password
   ```

2. **生成安全密鑰**
   ```bash
   openssl rand -hex 32
   ```

3. **限制 CORS**
   ```bash
   # 只允許特定域名
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

4. **不暴露資料庫端口**
   - 生產環境移除 `ports: - "5432:5432"`

5. **定期備份**
   ```bash
   # 設定 cron 自動備份
   0 2 * * * /path/to/backup.sh
   ```

6. **更新容器**
   ```bash
   # 定期更新基礎映像
   docker-compose pull
   docker-compose up -d
   ```

## 🐛 故障排除

### 容器無法啟動

```bash
# 查看詳細錯誤
docker-compose logs backend

# 檢查配置
docker-compose config

# 重建容器
docker-compose up -d --build --force-recreate
```

### 資料庫連接失敗

```bash
# 檢查資料庫是否就緒
docker exec -it rag_postgres pg_isready -U postgres

# 檢查環境變數
docker exec -it rag_backend env | grep POSTGRES

# 測試連接
docker exec -it rag_backend python -c "
from sqlalchemy import create_engine
from app.config import settings
engine = create_engine(settings.DATABASE_URL)
print('Connection OK')
"
```

### Migration 失敗

```bash
# 查看當前版本
docker exec -it rag_backend alembic current

# 回退一個版本
docker exec -it rag_backend alembic downgrade -1

# 強制標記為最新
docker exec -it rag_backend alembic stamp head
```

### 磁碟空間不足

```bash
# 清理未使用的映像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷（危險！會刪除資料）
docker volume prune
```

## 🔄 更新部署

```bash
# 1. 拉取最新代碼
git pull

# 2. 停止服務
docker-compose down

# 3. 備份資料庫（重要！）
docker exec rag_postgres pg_dump -U postgres rag_db > backup_before_update.sql

# 4. 重建並啟動
docker-compose up -d --build

# 5. 執行新的 migration
docker exec -it rag_backend alembic upgrade head

# 6. 驗證
curl http://localhost:8000/api/health
```

## 📝 環境變數說明

### 必需設定

| 變數 | 說明 | 範例 |
|------|------|------|
| `POSTGRES_PASSWORD` | 資料庫密碼 | `strong_password_123` |
| `SECRET_KEY` | JWT 密鑰 | `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | CORS 允許的域名 | `http://localhost:3000` |

### 可選設定

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `POSTGRES_DB` | 資料庫名稱 | `rag_db` |
| `POSTGRES_USER` | 資料庫使用者 | `postgres` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期 | `30` |

## 🚀 生產環境建議

1. **使用專用機器或 VPS**
2. **設定防火牆** - 只開放必要端口
3. **啟用 SSL/TLS** - 使用 Let's Encrypt
4. **設定自動備份** - 每日備份資料庫
5. **監控系統** - 使用 Prometheus + Grafana
6. **日誌管理** - 使用 ELK Stack 或 Loki
7. **負載均衡** - 使用 Nginx 或 Traefik
8. **容器編排** - 考慮使用 Docker Swarm 或 Kubernetes

## 📞 支援

遇到問題請查看：
1. 容器日誌：`docker-compose logs -f`
2. 健康檢查：`docker ps` 查看 STATUS
3. 資料庫連接：檢查環境變數和網路
4. Migration 狀態：`alembic current`
