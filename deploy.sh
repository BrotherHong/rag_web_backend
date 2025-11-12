#!/bin/bash

# RAG 後端部署腳本
# 用途：自動化部署到生產環境

set -e  # 遇到錯誤立即停止

echo "🚀 開始部署 RAG 後端系統..."

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 檢查 .env 檔案
if [ ! -f .env ]; then
    echo -e "${RED}❌ 錯誤：找不到 .env 檔案${NC}"
    echo "請從 .env.example 複製並填入正確的設定："
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

echo -e "${GREEN}✅ 找到 .env 檔案${NC}"

# 檢查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安裝${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安裝${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 環境檢查通過${NC}"

# 停止舊的容器
echo -e "${YELLOW}⏹️  停止舊容器...${NC}"
docker-compose -f docker-compose.prod.yml down

# 拉取最新程式碼（如果在 Git 倉庫中）
if [ -d .git ]; then
    echo -e "${YELLOW}📥 拉取最新程式碼...${NC}"
    git pull origin main || git pull origin master
fi

# 建立並啟動容器
echo -e "${YELLOW}🏗️  建立 Docker 映像...${NC}"
docker-compose -f docker-compose.prod.yml build

echo -e "${YELLOW}🚀 啟動服務...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# 等待資料庫啟動
echo -e "${YELLOW}⏳ 等待資料庫啟動...${NC}"
sleep 10

# 執行資料庫遷移
echo -e "${YELLOW}📊 執行資料庫遷移...${NC}"
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 初始化資料（僅首次部署時）
read -p "是否執行資料庫初始化？(首次部署選 y，更新部署選 n) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗄️  初始化資料庫...${NC}"
    docker-compose -f docker-compose.prod.yml exec -T backend python scripts/init_db.py
fi

# 顯示服務狀態
echo -e "\n${GREEN}✅ 部署完成！${NC}"
echo -e "\n📊 服務狀態："
docker-compose -f docker-compose.prod.yml ps

echo -e "\n🌐 服務地址："
echo "  - API 文檔: http://localhost:8000/api/docs"
echo "  - API 根路徑: http://localhost:8000/api/"
echo "  - 健康檢查: http://localhost:8000/health"
echo "  - Celery 監控: http://localhost:5555"

echo -e "\n📋 查看日誌："
echo "  docker-compose -f docker-compose.prod.yml logs -f backend"

echo -e "\n⏹️  停止服務："
echo "  docker-compose -f docker-compose.prod.yml down"

echo -e "\n${GREEN}🎉 部署成功！${NC}"
