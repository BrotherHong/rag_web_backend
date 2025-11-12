# 🚀 快速部署指南

## 開發環境 vs 生產環境

### 📍 目前（開發環境）

```bash
# 1. 啟動資料庫
docker-compose up -d

# 2. 啟動虛擬環境
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. 啟動 FastAPI
uvicorn app.main:app --reload
```

**訪問：**
- http://localhost:8000/api/docs

---

### 🚀 未來（生產環境）

#### **Linux/Mac:**
```bash
# 一鍵部署
./deploy.sh
```

#### **Windows:**
```bash
# 一鍵部署
deploy.bat
```

#### **手動部署:**
```bash
# 1. 設定環境變數
cp .env.example .env
nano .env  # 填入生產設定

# 2. 啟動所有服務（包含 FastAPI）
docker-compose -f docker-compose.prod.yml up -d --build

# 3. 執行資料庫遷移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. 初始化資料（僅首次）
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
```

**訪問：**
- http://你的伺服器IP:8000/api/docs

---

## 📦 Git 部署流程

### 1️⃣ 初次設定（開發電腦）

```bash
# 初始化 Git
git init
git add .
git commit -m "Initial commit"

# 推送到 GitHub
git remote add origin https://github.com/你的帳號/rag_web_backend.git
git push -u origin main
```

### 2️⃣ 部署到伺服器

```bash
# SSH 到伺服器
ssh user@你的伺服器IP

# Clone 專案
git clone https://github.com/你的帳號/rag_web_backend.git
cd rag_web_backend

# 設定環境變數
cp .env.example .env
nano .env  # 填入生產環境設定

# 執行部署
./deploy.sh  # Linux/Mac
# 或 deploy.bat  # Windows
```

### 3️⃣ 更新部署

```bash
# 在伺服器上
cd rag_web_backend
git pull origin main
./deploy.sh
```

---

## 🔄 切換環境

### 從開發切換到生產：

```bash
# 停止開發環境
docker-compose down

# 啟動生產環境
docker-compose -f docker-compose.prod.yml up -d --build
```

### 從生產切換回開發：

```bash
# 停止生產環境
docker-compose -f docker-compose.prod.yml down

# 啟動開發環境
docker-compose up -d
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

---

## 🔐 重要：環境變數安全

**絕對不要提交到 Git 的檔案：**
- ❌ `.env`（包含密碼和 API Key）
- ❌ `uploads/`（使用者上傳的檔案）
- ❌ `logs/`（日誌檔案）

**可以提交到 Git 的檔案：**
- ✅ `.env.example`（範本）
- ✅ 所有程式碼
- ✅ `requirements.txt`
- ✅ `docker-compose.yml` 和 `docker-compose.prod.yml`

---

## 📊 服務管理指令

```bash
# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f backend

# 重啟服務
docker-compose -f docker-compose.prod.yml restart backend

# 停止服務
docker-compose -f docker-compose.prod.yml down

# 完全清理（包含 volumes）
docker-compose -f docker-compose.prod.yml down -v
```

---

## 🆘 遇到問題？

1. 查看 [DEPLOY.md](./DEPLOY.md) 完整部署文件
2. 查看容器日誌：`docker-compose logs`
3. 檢查 `.env` 設定是否正確
4. 確認 Docker 是否正常運行

---

**🎉 現在你已經準備好隨時部署到生產環境了！**
