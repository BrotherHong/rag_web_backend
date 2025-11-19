@echo off
REM RAG 後端部署腳本 (Windows 版本)
REM 用途：自動化部署到生產環境

echo 🚀 開始部署 RAG 後端系統...

REM 檢查 .env 檔案
if not exist .env (
    echo ❌ 錯誤：找不到 .env 檔案
    echo 請從 .env.example 複製並填入正確的設定：
    echo   copy .env.example .env
    echo   notepad .env
    exit /b 1
)

echo ✅ 找到 .env 檔案

REM 檢查 Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安裝或未啟動
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose 未安裝
    exit /b 1
)

echo ✅ Docker 環境檢查通過

REM 停止舊的容器
echo ⏹️  停止舊容器...
docker-compose -f docker-compose.prod.yml down

REM 拉取最新程式碼（如果在 Git 倉庫中）
if exist .git (
    echo 📥 拉取最新程式碼...
    git pull origin main
)

REM 建立並啟動容器
echo 🏗️  建立 Docker 映像...
docker-compose -f docker-compose.prod.yml build

echo 🚀 啟動服務...
docker-compose -f docker-compose.prod.yml up -d

REM 等待資料庫啟動
echo ⏳ 等待資料庫啟動...
timeout /t 10 /nobreak

REM 執行資料庫遷移
echo 📊 執行資料庫遷移...
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

REM 詢問是否初始化資料
set /p INIT="是否執行資料庫初始化?(首次部署選 Y,更新部署選 N) [Y/N]: "
if /i "%INIT%"=="Y" (
    echo 🗄️  初始化資料庫(處室、分類、管理員)...
    docker-compose -f docker-compose.prod.yml exec -T backend python scripts/init_db.py
    
    echo ⚙️  初始化系統設定...
    docker-compose -f docker-compose.prod.yml exec -T backend python scripts/init_system_settings.py
)

REM 顯示服務狀態
echo.
echo ✅ 部署完成！
echo.
echo 📊 服務狀態：
docker-compose -f docker-compose.prod.yml ps

echo.
echo 🌐 服務地址：
echo   - API 文檔: http://localhost:8000/api/docs
echo   - API 根路徑: http://localhost:8000/api/
echo   - 健康檢查: http://localhost:8000/health

echo.
echo 📋 查看日誌：
echo   docker-compose -f docker-compose.prod.yml logs -f backend

echo.
echo ⏹️  停止服務：
echo   docker-compose -f docker-compose.prod.yml down

echo.
echo 🎉 部署成功！

pause
