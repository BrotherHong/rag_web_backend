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

# 2. 設定環境變數
cp .env.example .env
nano .env  # 填入生產環境設定

# 3. 執行部署腳本
chmod +x deploy.sh
./deploy.sh
```

### 方法 2：手動部署

```bash
# 1. Clone 專案
git clone https://github.com/你的帳號/rag_web_backend.git
cd rag_web_backend

# 2. 設定環境變數
cp .env.example .env
nano .env

# 3. 建立並啟動容器
docker-compose -f docker-compose.prod.yml up -d --build

# 4. 執行資料庫遷移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. 初始化資料（僅首次部署）
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
```

---

## ⚙️ 環境變數設定

**重要：請務必修改以下設定值！**

```env
# 安全設定（必須修改！）
SECRET_KEY=請-改-成-至-少-32-字-元-的-隨-機-字-串
JWT_SECRET_KEY=另-一-個-32-字-元-的-隨-機-字-串

# 資料庫密碼（必須修改！）
POSTGRES_PASSWORD=你的強密碼

# Redis 密碼（必須修改！）
REDIS_PASSWORD=你的Redis密碼

# OpenAI API Key（必須填入！）
OPENAI_API_KEY=sk-你的真實API金鑰

# CORS 設定（改成你的前端網址）
CORS_ORIGINS=https://你的網域.com,https://admin.你的網域.com

# 除錯模式（生產環境必須設為 False）
DEBUG=False
```

**生成隨機密鑰：**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🔄 更新部署

```bash
# 拉取最新程式碼
git pull origin main

# 重新建立並啟動
docker-compose -f docker-compose.prod.yml up -d --build

# 執行資料庫遷移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

或使用自動部署腳本：
```bash
./deploy.sh
```

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

# 僅 Celery
docker-compose -f docker-compose.prod.yml logs -f celery_worker
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
- 閱讀 [開發文件](./backend_docs/)
- 聯繫維護者

---

**部署成功後，訪問：**
- 🌐 API 文檔: http://你的伺服器IP:8000/api/docs
- 💚 健康檢查: http://你的伺服器IP:8000/health
- 🌺 Celery 監控: http://你的伺服器IP:5555
