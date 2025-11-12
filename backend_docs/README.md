# 🚀 RAG 系統後端架構規劃文件

> **專案分離建議**：前端 (`rag_web_admin`) 和後端 (`rag_web_backend`) 應該是**獨立的專案**
> 
> 此文件提供完整的後端架構規劃，供 Copilot 和開發者參考

---

## 📂 文件結構

本目錄包含完整的後端開發規劃文件：

### 核心文件
1. **[01_ARCHITECTURE.md](./01_ARCHITECTURE.md)** - 系統架構總覽
2. **[02_TECH_STACK.md](./02_TECH_STACK.md)** - 技術堆疊與依賴
3. **[03_DATABASE_DESIGN.md](./03_DATABASE_DESIGN.md)** - 資料庫設計
4. **[04_API_DESIGN.md](./04_API_DESIGN.md)** - API 端點設計
5. **[05_FOLDER_STRUCTURE.md](./05_FOLDER_STRUCTURE.md)** - 專案資料夾結構
6. **[06_CODE_EXAMPLES.md](./06_CODE_EXAMPLES.md)** - 核心程式碼範例
7. **[07_DEPLOYMENT.md](./07_DEPLOYMENT.md)** - 部署與運維
8. **[08_DEVELOPMENT_GUIDE.md](./08_DEVELOPMENT_GUIDE.md)** - 開發指南

---

## 🎯 快速開始

### 前置條件
```bash
# 環境需求
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (推薦)
```

### 建立新的後端專案
```bash
# 1. 建立後端專案目錄 (與前端平行)
cd c:\Users\user\Documents\NCKU\RAG_web
mkdir rag_web_backend
cd rag_web_backend

# 2. 初始化 Python 虛擬環境
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. 安裝 FastAPI 與基礎套件
pip install fastapi uvicorn sqlalchemy asyncpg redis python-jose passlib

# 4. 建立專案結構 (參考 05_FOLDER_STRUCTURE.md)
```

---

## 📋 與前端的整合點

### API 端點對應
前端已經定義好的 API 模組：

| 前端模組 | 對應後端路由 | 說明 |
|---------|------------|------|
| `api/auth.js` | `/api/auth/*` | 登入、登出、驗證 |
| `api/files.js` | `/api/files/*` | 檔案管理 |
| `api/categories.js` | `/api/categories/*` | 分類管理 |
| `api/activities.js` | `/api/activities/*` | 活動記錄 |
| `api/upload.js` | `/api/upload/*` | 批次上傳 |
| `api/users.js` | `/api/users/*` | 使用者管理 |
| `api/departments.js` | `/api/departments/*` | 處室管理 |
| `api/settings.js` | `/api/settings/*` | 系統設定 |

### 環境變數設定
```env
# 前端 (.env)
VITE_API_BASE_URL=http://localhost:8000/api

# 後端 (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rag_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
```

---

## 🏗️ 專案分離結構

```
RAG_web/
├── rag_web_admin/          # 前端專案 (已存在)
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── backend_docs/       # 後端架構文件 (此目錄)
│
└── rag_web_backend/        # 後端專案 (待建立)
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   ├── models/
    │   ├── services/
    │   └── ...
    ├── requirements.txt
    ├── docker-compose.yml
    └── README.md
```

---

## 🔗 相關資源

- **前端專案**: `../` (上層目錄)
- **前端 API 介面**: `../src/services/api/`
- **API 模擬資料**: `../src/services/mock/database.js`
- **前端資料結構參考**: 根據 `../src/services/mock/database.js` 設計

---

## 💡 使用建議

### 給 Copilot
```
當開發後端時，請參考此目錄的文件：
1. 遵循 01_ARCHITECTURE.md 的架構設計
2. 使用 02_TECH_STACK.md 指定的技術棧
3. 實作 04_API_DESIGN.md 定義的所有端點
4. 參考 06_CODE_EXAMPLES.md 的程式碼風格
```

### 給開發者
1. **先讀完所有文件** - 理解整體架構
2. **從 Database 開始** - 建立資料庫 Schema
3. **實作 Auth 模組** - 完成認證系統
4. **逐步實作 API** - 按照前端需求實作
5. **測試與部署** - 參考部署文件

---

## 📊 開發進度追蹤

- [ ] 專案初始化
- [ ] 資料庫設計與遷移
- [ ] 認證系統 (JWT)
- [ ] 檔案管理 API
- [ ] 分類管理 API
- [ ] 使用者管理 API
- [ ] 處室管理 API
- [ ] 批次上傳系統
- [ ] RAG 整合 (LangChain + Qdrant)
- [ ] Redis 快取
- [ ] 測試與部署

---

**文件版本**: 1.1.0  
**最後更新**: 2025-11-12  
**維護者**: BrotherHong
