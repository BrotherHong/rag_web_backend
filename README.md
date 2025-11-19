# RAG 知識庫管理系統後端

> 基於 FastAPI + PostgreSQL + Redis 的企業級知識庫管理與檢索增強生成系統

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 目錄

- [專案簡介](#專案簡介)
- [核心功能](#核心功能)
- [技術架構](#技術架構)
- [快速開始](#快速開始)
- [API 文件](#api-文件)
- [專案結構](#專案結構)
- [開發指南](#開發指南)
- [測試](#測試)
- [部署](#部署)
- [常見問題](#常見問題)

## 🎯 專案簡介

RAG 知識庫管理系統是一個企業級的知識管理解決方案，結合了檢索增強生成（Retrieval-Augmented Generation, RAG）技術，幫助組織有效管理和檢索內部文件知識。

### 核心特色

- 🔐 **完整的權限管理**: 支援多角色(系統管理員、處室管理員、一般使用者)與細粒度權限控制
- 📁 **智能文件管理**: 支援多種文件格式上傳、自動解析與向量化
- 🔍 **RAG 智能檢索**: 基於向量相似度的語意搜尋與生成式回答 (Mock 實現)
- 👥 **多處室架構**: 支援組織結構管理,資料隔離與權限分級
- 📊 **豐富的統計**: 使用者、檔案、查詢等多維度數據統計
- 🔄 **活動追蹤**: 完整的操作日誌與審計追蹤
- 🚀 **容器化部署**: Docker Compose 一鍵部署,輕鬆擴展

## ✨ 核心功能

### 1. 使用者與權限管理

- ✅ JWT Token 身份驗證
- ✅ 角色基礎存取控制（RBAC）
- ✅ 處室級資料隔離
- ✅ 使用者 CRUD 與統計
- ✅ 密碼修改與安全管理

### 2. 文件管理

- ✅ 支援 PDF、DOCX、TXT 等格式
- ✅ 文件上傳與向量化處理
- ✅ 文件分類管理
- ✅ 文件搜尋與篩選
- ✅ 文件狀態追蹤（處理中、完成、失敗）
- ✅ 文件統計與分析

### 3. RAG 查詢系統

- ✅ 語義化查詢（向量搜尋）
- ✅ 上下文增強生成
- ✅ 查詢歷史記錄
- ✅ 查詢結果評分與排序
- ✅ 查詢統計分析

### 4. 組織架構管理

- ✅ 處室 CRUD 操作
- ✅ 處室統計資訊
- ✅ 分類管理
- ✅ 系統設定管理

### 5. 活動日誌

- ✅ 使用者操作追蹤
- ✅ 檔案操作記錄
- ✅ 查詢歷史記錄
- ✅ 活動統計與分析

## 🏗️ 技術架構

### 後端技術棧

| 技術 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 程式語言 (最低要求 3.10) |
| FastAPI | 0.115 | Web 框架 |
| PostgreSQL | 16 | 主資料庫 |
| SQLAlchemy | 2.0 | ORM 框架 (非同步支援) |
| Pydantic | 2.11 | 資料驗證 |
| Alembic | 1.15 | 資料庫遷移 |
| Redis | 7 (可選) | 快取與 Session |

### 系統架構圖

```
┌─────────────────┐
│   前端應用      │
│  (React/Vue)    │
└────────┬────────┘
         │ HTTP/REST
         ↓
┌─────────────────────────────────────┐
│        FastAPI 應用層               │
│  ┌──────────┬──────────┬─────────┐ │
│  │ 認證授權 │ 業務邏輯 │ 檔案處理│ │
│  └──────────┴──────────┴─────────┘ │
└────┬─────────┬──────────┬──────────┘
     │         │          │
     ↓         ↓          ↓
┌─────────┐ ┌─────┐ ┌─────────┐
│PostgreSQL│ │Redis│ │ 檔案儲存  │
│  資料庫  │ │快取 │ │ (uploads) │
└─────────┘ └─────┘ └─────────┘
```

### 資料庫設計

#### 核心資料表

- **users**: 使用者資料
- **departments**: 處室資訊
- **categories**: 文件分類
- **files**: 文件管理
- **query_history**: 查詢歷史
- **activities**: 活動記錄
- **system_settings**: 系統設定

## 🚀 快速開始

### ⚙️ 環境架構說明

本專案採用**開發/生產環境分離**的架構設計：

#### 開發環境（推薦用於本機開發）
```
本機 Windows/Mac/Linux
├── Python venv（本機虛擬環境）
│   └── FastAPI 應用程式（熱重載、快速除錯）
│
└── Docker 容器（docker-compose.yml）
    ├── PostgreSQL 16
    └── Redis 7 (可選)
```

**特點**：
- ✅ FastAPI 在本機運行，支援熱重載和 VS Code debugger
- ✅ 資料庫在 Docker 中，環境一致不污染本機
- ✅ 開發效率高，修改代碼立即生效

#### 生產環境（用於正式部署）
```
全部在 Docker 中（docker-compose.prod.yml）
├── backend（FastAPI 容器）
├── PostgreSQL 16
└── Redis 7 (可選)
```

**特點**：
- ✅ 完全容器化，環境完全隔離
- ✅ 一鍵部署，易於擴展
- ✅ 簡單可靠，生產等級穩定性

---

### 環境需求

**必須：**
- Python 3.10+ (最低 3.10，建議 3.11 或 3.12)
- PostgreSQL 16+ (或使用 Docker)
- Docker & Docker Compose (如果使用容器化部署)

**可選：**
- Redis 7+ (用於快取，如不安裝系統仍可正常運作)

### 1. 克隆專案

```bash
git clone <repository-url>
cd rag_web_backend
```

### 2. 環境配置

複製環境變數範本並編輯:

```bash
cp .env.example .env
```

編輯 `.env` 檔案，設定必要的環境變數:

```env
# 應用設定
APP_NAME="RAG Knowledge Base"
DEBUG=True
API_V1_PREFIX="/api"

# 安全設定
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 資料庫
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rag_db

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=rag_documents
```

### 3. 使用 Docker Compose 啟動服務

```bash
# 啟動所有服務(PostgreSQL, Redis)
docker-compose up -d

# 查看服務狀態
docker-compose ps
```

### 4. 建立 Python 虛擬環境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 5. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 6. 初始化資料庫

```bash
# 執行資料庫初始化腳本(處室、分類、管理員)
python scripts/init_db.py

# 初始化系統設定
python scripts/init_system_settings.py

# 或使用完整重置(⚠️ 會刪除所有資料)
python scripts/reset_db.py
```

這將會建立:
- ✅ 3 個預設處室(人事室、會計室、總務處)
- ✅ 7 個檔案分類
- ✅ 預設管理員帳號(admin / admin123)
- ✅ 系統設定(app, rag, security, feature, backup)

### 7. 啟動應用程式

```bash
# 開發模式（支援熱重載）
python -m uvicorn app.main:app --reload

# 生產模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 8. 訪問應用

- **API 文件 (Swagger)**: http://localhost:8000/docs
- **API 文件 (ReDoc)**: http://localhost:8000/redoc
- **健康檢查**: http://localhost:8000/health

### 9. 預設帳號

```
帳號: admin
密碼: admin123
角色: ADMIN（系統管理員）
```

⚠️ **重要**: 首次登入後請立即修改密碼！

## 📚 API 文件

### API 端點總覽

| 模組 | 端點數量 | 說明 |
|------|---------|------|
| 認證 | 2 | 登入、獲取當前使用者 |
| 使用者 | 7 | CRUD、統計、密碼管理 |
| 處室 | 6 | CRUD、統計 |
| 分類 | 6 | CRUD、檔案查詢 |
| 檔案 | 8 | 上傳、下載、搜尋、統計 |
| RAG | 3 | 查詢、歷史、統計 (Mock 實現) |
| 活動 | 3 | 列表、詳情、統計 |
| 設定 | 7 | CRUD、批次更新 |

**總計: 42+ API 端點**

### 快速範例

#### 1. 使用者登入

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

回應:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 2. 獲取使用者列表

```bash
curl -X GET "http://localhost:8000/api/users?page=1&limit=10" \
  -H "Authorization: Bearer <your_token>"
```

#### 3. 上傳文件

```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@document.pdf" \
  -F "category_id=1"
```

#### 4. RAG 查詢

```bash
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "什麼是年假規定?", "top_k": 5}'
```

更多 API 範例請查看 Swagger 文件: http://localhost:8000/docs

## 📂 專案結構

```
rag_web_backend/
│
├── app/                          # 應用程式主目錄
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py              # 認證相關端點
│   │   ├── users.py             # 使用者管理端點
│   │   ├── departments.py       # 處室管理端點
│   │   ├── categories.py        # 分類管理端點
│   │   ├── files.py             # 檔案管理端點
│   │   ├── rag.py               # RAG 查詢端點
│   │   ├── activities.py        # 活動記錄端點
│   │   └── settings.py          # 系統設定端點
│   │
│   ├── core/                     # 核心功能模組
│   │   ├── database.py          # 資料庫連線
│   │   ├── redis.py             # Redis 連線 (可選)
│   │   └── security.py          # 安全與認證
│   │
│   ├── models/                   # SQLAlchemy 資料模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── department.py
│   │   ├── file.py
│   │   ├── category.py
│   │   ├── query_history.py
│   │   ├── activity.py
│   │   └── system_setting.py
│   │
│   ├── schemas/                  # Pydantic 資料驗證模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── department.py
│   │   ├── file.py
│   │   └── ...
│   │
│   ├── services/                 # 業務邏輯服務
│   │   ├── file_service.py      # 檔案處理服務
│   │   ├── rag_service.py       # RAG 查詢服務 (Mock)
│   │   ├── activity.py          # 活動記錄服務
│   │   └── embedding.py         # 向量化服務 (預留)
│   │
│   ├── utils/                    # 工具函數
│   │   ├── file_processor.py    # 檔案處理
│   │   └── text_splitter.py     # 文本分割
│   │
│   ├── config.py                 # 應用配置
│   └── main.py                   # FastAPI 應用入口
│
├── scripts/                      # 腳本工具
│   ├── init_db.py               # 資料庫初始化(處室、分類、管理員)
│   ├── init_system_settings.py # 系統設定初始化
│   ├── reset_db.py              # 完整重置資料庫
│   └── README.md                # 腳本使用說明
│
├── uploads/                      # 檔案上傳目錄
├── logs/                         # 日誌目錄
├── docker-compose.yml            # 開發環境 Docker 編排檔案
├── docker-compose.prod.yml       # 生產環境 Docker 編排檔案
├── requirements.txt              # Python 相依套件
├── pytest.ini                    # pytest 配置
├── .env.example                  # 環境變數範本
├── .gitignore
├── QUICKSTART.md                 # 快速部署指南
└── README.md
```

## 🛠️ 開發指南

### 開發環境設定

1. **安裝開發工具**

```bash
# 安裝開發相依套件
pip install -r requirements-dev.txt
```

2. **程式碼格式化**

```bash
# 使用 black 格式化程式碼
black app/ tests/

# 使用 isort 排序 import
isort app/ tests/
```

3. **程式碼檢查**

```bash
# 使用 flake8 檢查程式碼
flake8 app/ tests/

# 使用 mypy 進行型別檢查
mypy app/
```

### 資料庫遷移

```bash
# 建立新的遷移檔案
alembic revision --autogenerate -m "description"

# 執行遷移
alembic upgrade head

# 回滾遷移
alembic downgrade -1
```

### 新增 API 端點

1. 在 `app/models/` 建立資料模型
2. 在 `app/schemas/` 建立驗證模型
3. 在 `app/api/` 建立路由端點
4. 在 `tests/` 新增測試(可選)

### 修改系統設定選項

系統設定選項(如 AI 模型、回應風格等下拉選單)完全由後端管理。詳細修改方法請參考: [scripts/SYSTEM_SETTINGS_GUIDE.md](scripts/SYSTEM_SETTINGS_GUIDE.md)

## 🚀 部署

### 🔧 開發環境部署（本機開發）

這是**推薦的日常開發方式**：

```bash
# 1. 啟動資料庫服務（Docker）
docker-compose up -d

# 2. 確認服務運行
docker-compose ps

# 3. 啟動虛擬環境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 4. 初始化資料庫（首次運行）
python scripts/init_db.py

# 5. 啟動 FastAPI（本機，支援熱重載）
python -m uvicorn app.main:app --reload

# 6. 訪問 API 文件
# http://localhost:8000/docs
```

**優點**：
- ⚡ 代碼修改立即生效（熱重載）
- 🐛 可使用 VS Code debugger 設置斷點
- 💻 資源占用低，開發效率高

---

### 🚀 生產環境部署（正式部署）

使用 **docker-compose.prod.yml** 進行完全容器化部署：

#### 步驟 1: 準備環境變數

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯生產環境配置
nano .env
```

**重要配置項**：
```env
# 生產環境必須設定
DEBUG=False
SECRET_KEY=<強密碼-至少32字元>
JWT_SECRET_KEY=<強密碼-至少32字元>

# 資料庫密碼（docker-compose.prod.yml 會使用）
POSTGRES_PASSWORD=<強密碼>
REDIS_PASSWORD=<強密碼>

# OpenAI API Key（用於 RAG 功能）
OPENAI_API_KEY=<your-api-key>
```

#### 步驟 2: 構建並啟動所有服務

```bash
# 構建映像並啟動所有容器
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f
```

#### 步驟 3: 初始化資料庫

```bash
# 進入 backend 容器
docker-compose -f docker-compose.prod.yml exec backend bash

# 執行資料庫初始化
python scripts/init_db.py

# 退出容器
exit
```

#### 步驟 4: 驗證部署

訪問以下 URL 確認服務正常：

- **API 文件**: http://your-server:8000/docs
- **健康檢查**: http://your-server:8000/health
- **Celery 監控**: http://your-server:5555

#### 管理命令

```bash
# 查看容器狀態
docker-compose -f docker-compose.prod.yml ps

# 查看特定服務日誌
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs celery_worker

# 重啟服務
docker-compose -f docker-compose.prod.yml restart backend

# 停止所有服務
docker-compose -f docker-compose.prod.yml down

# 停止並刪除數據卷（⚠️ 慎用）
docker-compose -f docker-compose.prod.yml down -v
```

---

### 🔐 生產環境安全建議

1. **使用強密碼**
   - 修改 `.env` 中的所有預設密碼
   - 使用至少 32 字元的隨機字串

2. **使用 Nginx 反向代理**

```nginx
server {
    listen 80;
    server_name api.example.com;

    # HTTPS 重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL 證書
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 反向代理到 FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 檔案上傳大小限制
    client_max_body_size 50M;
}
```

3. **防火牆設定**
   ```bash
   # 只開放必要端口
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw allow 22/tcp    # SSH
   ufw enable
   ```

4. **定期備份**
   ```bash
   # 備份資料庫
   docker-compose -f docker-compose.prod.yml exec postgres \
     pg_dump -U postgres rag_db > backup_$(date +%Y%m%d).sql

   # 備份上傳檔案
   tar -czf uploads_backup_$(date +%Y%m%d).tar.gz ./uploads
   ```

5. **監控與日誌**
   - 定期檢查日誌: `docker-compose -f docker-compose.prod.yml logs --tail=100`
   - 考慮使用 Prometheus + Grafana 進行系統監控

---

## 📝 更新日誌

### Version 1.0.0 (2025-01-19)

#### 新功能
- ✅ 完整的使用者認證與授權系統
- ✅ 多角色權限管理(SUPER_ADMIN, DEPT_ADMIN, USER)
- ✅ 檔案上傳與管理功能
- ✅ RAG 智能查詢功能 (Mock 實現)
- ✅ 處室與分類管理
- ✅ 活動記錄與審計追蹤
- ✅ 系統設定管理(支援巢狀結構)
- ✅ 下拉選項後端管理(value + label 格式)
- ✅ Docker 容器化部署

#### 技術優化
- ✅ 移除 Celery 背景任務(簡化架構)
- ✅ 移除 Qdrant 向量資料庫(RAG 使用 Mock)
- ✅ 清理不使用的環境變數
- ✅ 前後端資料結構統一(巢狀格式)
- ✅ 系統設定改為混合模式(資料庫 + 環境變數)

#### 已知問題
- ⚠️ RAG 查詢功能目前為 Mock 實現,需要接入真實 LLM API
- ⚠️ 檔案向量化功能尚未實現

# 2. 構建並啟動
docker-compose -f docker-compose.prod.yml up -d --build

# 3. 初始化資料庫
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_db.py

# 4. 配置 Nginx 反向代理
---

## ❓ 常見問題

### Q1: 啟動時無法連接資料庫

**A**: 確認 Docker 服務已啟動:
```bash
docker-compose ps
docker-compose up -d
```

### Q2: JWT Token 驗證失敗

**A**: 檢查 `.env` 中的 `JWT_SECRET_KEY` 是否正確設定。

### Q3: 檔案上傳失敗

**A**: 確認:
- 檔案大小不超過設定上限
- 檔案格式為支援的類型(PDF, DOCX, TXT)
- `uploads/` 目錄有寫入權限

### Q4: 如何修改系統設定選項(下拉選單)?

**A**: 請參考 [scripts/SYSTEM_SETTINGS_GUIDE.md](scripts/SYSTEM_SETTINGS_GUIDE.md) 完整修改指南。

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！

1. Fork 本專案
2. 建立特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 👥 作者

- **開發團隊** - RAG Knowledge Base Team
- **專案負責人** - BrotherHong

## 🙏 致謝

- [FastAPI](https://fastapi.tiangolo.com/) - 現代化的 Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - 強大的 ORM 工具
- [Qdrant](https://qdrant.tech/) - 高效能向量資料庫
- [OpenAI](https://openai.com/) - GPT 模型支援

## 📧 聯絡方式

- Email: your-email@example.com
- 專案連結: [GitHub Repository](https://github.com/your-repo)

---

**Built with ❤️ using FastAPI**
