FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 建立上傳目錄
RUN mkdir -p uploads logs

# 複製啟動腳本並設定執行權限
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 暴露端口
EXPOSE 8000

# 使用啟動腳本
CMD ["./entrypoint.sh"]
