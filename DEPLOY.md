# 🚀 部署指南

## 部署到生產環境

### 前置準備

1. **伺服器需求**
   - Ubuntu 20.04+ / CentOS 8+ / Debian 11+
   - Docker 20.10+
   - Docker Compose 2.0+
   - 至少 4GB RAM
   - 至少 20GB 硬碟空間

2. **安裝 Docker**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安裝 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## 📦 部署步驟

### 方法 1：自動部署（推薦）

```bash
# 1. Clone 專案
git clone https://github.com/你的帳號/rag_web_backend.git
cd rag_web_backend

# 2. 設定環境變數（⚠️ 重要！請務必修改敏感資訊）
cp .env.production.example .env
nano .env  # 修改資料庫密碼、JWT密鑰等敏感資訊

# 3. 執行部署腳本（會自動執行遷移和初始化）
chmod +x deploy.sh
./deploy.sh
```

### 方法 2：手動部署

```bash
# 1. Clone 專案
git clone https://github.com/你的帳號/rag_web_backend.git
cd rag_web_backend

# 2. 設定環境變數（⚠️ 重要！）
cp .env.production.example .env
nano .env  # 修改以下必要設定：
         # - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
         # - JWT_SECRET_KEY (至少32字元)
         # - REDIS_PASSWORD (如果啟用Redis)
         # - CORS_ORIGINS (前端網址)

# 3. 建立並啟動容器（自動執行遷移和初始化）
docker-compose -f docker-compose.prod.yml up -d --build

# 4. 查看啟動日誌，確認初始化成功
docker-compose -f docker-compose.prod.yml logs -f backend
```

**✨ 新功能：自動初始化**

從 v2.0 開始，容器在首次啟動時會自動執行：
- ✅ 資料庫遷移 (Alembic migrations)
- ✅ 創建預設處室和分類
- ✅ 創建管理員帳號
- ✅ 初始化系統設定

無需手動執行 `init_db.py` 和 `init_system_settings.py`！

---

## ⚙️ 環境變數設定

**⚠️ 安全警告：生產環境必須修改所有預設密碼和密鑰！**

### 必須修改的設定（安全性）

```env
# 1. JWT 密鑰（必須改為強隨機字串，至少32字元）
JWT_SECRET_KEY=請使用下方指令生成隨機字串

# 2. 資料庫認證（必須改為強密碼）
POSTGRES_USER=postgres
POSTGRES_PASSWORD=請改為強密碼-至少16字元
POSTGRES_DB=rag_db

# 3. Redis 密碼（如果啟用Redis）
REDIS_PASSWORD=請改為強密碼

# 4. 除錯模式（生產環境必須設為 False）
DEBUG=False
```

### 需要配置的設定

```env
# CORS 設定（改成你的前端網址）
CORS_ORIGINS=https://你的網域.com,https://admin.你的網域.com

# OpenAI API Key（如果使用RAG功能）
OPENAI_API_KEY=sk-你的真實API金鑰
```

### 生成安全密鑰的方法

```bash
# 方法1: 使用 Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法2: 使用 OpenSSL
openssl rand -base64 32

# 方法3: 使用 UUID
python -c "import uuid; print(str(uuid.uuid4()).replace('-', ''))"
```

### 完整配置範例

參考 `.env.production.example` 檔案，包含所有可用的環境變數和詳細說明。

**資料庫 URL 格式：**
```env
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

**注意事項：**
- ✅ 所有密碼至少 16 字元，包含大小寫字母、數字、特殊字符
- ✅ JWT_SECRET_KEY 至少 32 字元的隨機字串
- ✅ 不要將 `.env` 檔案提交到 Git（已在 .gitignore 中）
- ✅ 定期更換密碼和密鑰
- ✅ 使用環境變數注入或密鑰管理服務（如 AWS Secrets Manager）

---

## 🔄 更新部署

```bash
# 拉取最新程式碼
git pull origin main

# 重新建立並啟動（會自動執行新的遷移）
docker-compose -f docker-compose.prod.yml up -d --build

# 查看更新日誌
docker-compose -f docker-compose.prod.yml logs -f backend
```

或使用自動部署腳本：
```bash
./deploy.sh
```

**注意：** 容器啟動時會自動執行未完成的資料庫遷移，無需手動執行 `alembic upgrade head`。

---

## 📊 管理指令

### 查看服務狀態
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 查看日誌
```bash
# 所有服務
docker-compose -f docker-compose.prod.yml logs -f

# 僅後端
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 重啟服務
```bash
# 重啟所有服務
docker-compose -f docker-compose.prod.yml restart

# 僅重啟後端
docker-compose -f docker-compose.prod.yml restart backend
```

### 停止服務
```bash
docker-compose -f docker-compose.prod.yml down
```

### 進入容器
```bash
# 進入後端容器
docker-compose -f docker-compose.prod.yml exec backend bash

# 進入資料庫容器
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d rag_db
```

---

## 🔐 安全建議

1. **使用 HTTPS**
   - 設定 Nginx 反向代理
   - 使用 Let's Encrypt 免費 SSL 憑證

2. **防火牆設定**
   ```bash
   # 只開放必要端口
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

3. **定期備份資料庫**
   ```bash
   # 備份
   docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres rag_db > backup.sql
   
   # 還原
   docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d rag_db < backup.sql
   ```

4. **監控與日誌**
   - 使用 Docker logs 記錄
   - 設定日誌輪替
   - 監控磁碟空間

---

## 🌐 Nginx 反向代理設定（可選）

如果要設定 HTTPS 和自訂網域：

```nginx
# /etc/nginx/sites-available/rag-backend
server {
    listen 80;
    server_name api.你的網域.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

啟用設定：
```bash
sudo ln -s /etc/nginx/sites-available/rag-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 設定 SSL（Let's Encrypt）
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.你的網域.com
```

---

## 🆘 常見問題

### 容器無法啟動
```bash
# 查看錯誤日誌
docker-compose -f docker-compose.prod.yml logs

# 清理並重建
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

### 資料庫連線失敗
- 檢查 `.env` 中的 `DATABASE_URL`
- 確認 PostgreSQL 容器正在運行
- 檢查防火牆設定

### Redis 連線失敗
- 檢查 Redis 密碼設定
- 確認 Redis 容器正在運行

### 磁碟空間不足
```bash
# 清理未使用的 Docker 資源
docker system prune -a
```

---

## 📞 需要協助？

- 查看 [GitHub Issues](https://github.com/你的帳號/rag_web_backend/issues)
- 閱讀 [README](./README.md) 和 [快速開始指南](./QUICKSTART.md)
- 聯繫維護者

---

**部署成功後，訪問：**
- 🌐 API 文檔: http://你的伺服器IP:8000/api/docs
- 💚 健康檢查: http://你的伺服器IP:8000/health
