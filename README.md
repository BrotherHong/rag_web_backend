# RAG Knowledge Base Management System - Backend

> RAG 知識庫管理系統後端 API

## 🚀 快速開始

### 環境需求

- Python 3.11+
- PostgreSQL 16
- Redis 7
- Docker & Docker Compose（推薦）

### 安裝步驟

1. **建立虛擬環境**

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. **安裝依賴**

```bash
pip install -r requirements.txt
```

3. **設定環境變數**

```bash
copy .env.example .env
# 編輯 .env 填入實際設定
```

4. **啟動資料庫（Docker）**

```bash
docker-compose up -d postgres redis qdrant
```

5. **資料庫遷移**

```bash
alembic upgrade head
python scripts/init_db.py
```

6. **啟動開發伺服器**

```bash
uvicorn app.main:app --reload
```

訪問 API 文檔：http://localhost:8000/api/docs

## 📂 專案結構

```
rag_web_backend/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心功能（資料庫、安全）
│   ├── models/       # SQLAlchemy 模型
│   ├── schemas/      # Pydantic Schemas
│   ├── services/     # 業務邏輯
│   ├── tasks/        # Celery 背景任務
│   └── utils/        # 工具函式
├── tests/            # 測試
├── scripts/          # 工具腳本
├── uploads/          # 上傳檔案
└── logs/             # 日誌
```

## 🔧 開發指令

```bash
# 執行測試
pytest

# 建立資料庫遷移
alembic revision --autogenerate -m "description"

# 執行遷移
alembic upgrade head

# 啟動 Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info
```

## 📖 API 文檔

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 🏗️ 技術棧

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0
- **Cache**: Redis 7
- **Vector DB**: Qdrant
- **Task Queue**: Celery
- **Auth**: JWT (python-jose)
- **Password**: bcrypt (passlib)

## 📝 開發注意事項

1. **處室資料隔離**: 所有查詢必須自動過濾 `department_id`
2. **異步優先**: 使用 `async/await` 和 `AsyncSession`
3. **權限分層**: user, admin, super_admin 三個層級
4. **活動記錄**: 重要操作需記錄到 activities 表

---

## 🚀 部署到生產環境

### 快速部署

**Linux/Mac:**
```bash
./deploy.sh
```

**Windows:**
```bash
deploy.bat
```

### 手動部署

```bash
# 1. Clone 專案
git clone https://github.com/你的帳號/rag_web_backend.git
cd rag_web_backend

# 2. 設定環境變數
cp .env.example .env
nano .env  # 填入生產環境設定

# 3. 啟動服務
docker-compose -f docker-compose.prod.yml up -d --build

# 4. 資料庫遷移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
```

**詳細說明：** 請參考 [DEPLOY.md](./DEPLOY.md) 和 [QUICKSTART.md](./QUICKSTART.md)

---

## 🔄 開發環境 vs 生產環境

| 環境 | FastAPI | 資料庫 | 啟動指令 |
|------|---------|--------|----------|
| **開發** | 本機虛擬環境 | Docker | `docker-compose up -d` + `uvicorn app.main:app --reload` |
| **生產** | Docker 容器 | Docker | `docker-compose -f docker-compose.prod.yml up -d` |

---

## 👥 作者

BrotherHong

## 📄 授權

MIT License
