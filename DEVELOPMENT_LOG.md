# RAG 知識庫後端開發日誌

## 2025-11-12 (星期二)

### 21:56 - 資料庫連線層實作完成 ✅

#### 建立的檔案：
1. **app/core/database.py** - PostgreSQL 異步連線池
   - 使用 SQLAlchemy 2.0 async engine
   - 配置連線池：pool_size=20, max_overflow=40
   - 實作 `get_db()` 依賴注入函數
   - 實作 `init_db()` 和 `close_db()` 生命週期管理

2. **app/core/redis.py** - Redis 連線管理
   - 使用 redis.asyncio 客戶端
   - 實作全域 redis_client
   - 實作 `init_redis()`, `close_redis()`, `get_redis()` 函數
   - 配置 max_connections=10

3. **app/core/qdrant.py** - Qdrant 向量資料庫連線
   - 使用 qdrant-client
   - 自動建立 Collection: "rag_documents"
   - 配置向量維度：1536 (OpenAI text-embedding-ada-002)
   - 使用 COSINE 距離計算

4. **app/config.py** - 新增配置
   - 新增 `EMBEDDING_DIM: int = 1536`

5. **app/main.py** - 整合生命週期管理
   - 使用 `@asynccontextmanager` 實作 lifespan
   - 啟動時初始化所有資料庫連線
   - 關閉時清理所有連線

#### 安裝的套件：
```bash
pip install qdrant-client==1.11.0 redis==5.0.0
```

#### 問題解決：
- ❌ Qdrant 方法不是 async 的 → 移除 await 關鍵字
- ❌ Settings 缺少 EMBEDDING_DIM → 新增到 app/config.py
- ✅ 所有資料庫連線成功初始化

---

### 22:00 - 資料庫模型建立完成 ✅

#### 建立的檔案：
1. **app/models/base.py** - 基礎類別
   - `Base`: DeclarativeBase 基礎類別
   - `TimestampMixin`: 自動管理 created_at, updated_at

2. **app/models/department.py** - 處室模型
   - 欄位：id, name, description
   - 關聯：users (一對多), files (一對多)

3. **app/models/user.py** - 使用者模型
   - 欄位：id, username, email, hashed_password, full_name, role, is_active
   - Enum: UserRole (admin, dept_admin, user)
   - 外鍵：department_id
   - 關聯：department, uploaded_files, activities

4. **app/models/category.py** - 分類模型
   - 欄位：id, name, description
   - 關聯：files (一對多)

5. **app/models/file.py** - 檔案模型
   - 欄位：id, filename, file_path, file_size, file_type, status, error_message
   - 向量化欄位：is_vectorized, chunk_count, summary
   - Enum: FileStatus (pending, processing, completed, failed)
   - 外鍵：uploader_id, department_id, category_id
   - 關聯：uploader, department, category, activities

6. **app/models/activity.py** - 活動記錄模型
   - 欄位：id, activity_type, description, ip_address, user_agent, extra_data
   - Enum: ActivityType (login, logout, upload, download, delete, search, query, etc.)
   - 外鍵：user_id, file_id
   - 關聯：user, file

7. **app/models/__init__.py** - 模型匯出
   - 統一匯出所有模型和 Enum 類型

#### 問題解決：
- ❌ `metadata` 欄位與 SQLAlchemy 保留字衝突 → 改名為 `extra_data`

---

### 22:10 - Alembic 資料庫遷移設定完成 ✅

#### 執行的步驟：
1. **初始化 Alembic**
   ```bash
   alembic init alembic
   ```

2. **配置 alembic/env.py** - 支援 Async SQLAlchemy
   - 匯入 `asyncio`, `sys`
   - Windows 平台修正：設定 `WindowsSelectorEventLoopPolicy`
   - 匯入專案配置和所有模型
   - 設定 target_metadata = Base.metadata
   - 改寫 `run_migrations_online()` 支援 async engine
   - 使用 `connection.run_sync()` 執行遷移

3. **安裝必要套件**
   ```bash
   pip install psycopg2-binary  # 嘗試但不相容
   pip install psycopg          # PostgreSQL 同步驅動
   pip install psycopg[binary]  # 二進位版本
   ```

4. **建立初始遷移**
   ```bash
   alembic revision --autogenerate -m "Initial migration: Create all tables"
   ```
   生成檔案：`alembic/versions/a7e8cebf2a93_initial_migration_create_all_tables.py`

5. **執行遷移**
   ```bash
   alembic upgrade head
   ```

#### 建立的資料表：
- ✅ departments
- ✅ users
- ✅ categories
- ✅ files
- ✅ activities

#### 問題解決：
- ❌ `engine_from_config` 未定義 → 改用 `async_engine_from_config`
- ❌ Activity 模型的 `metadata` 欄位衝突 → 改名為 `extra_data`
- ❌ psycopg 模組找不到 → 安裝 `psycopg[binary]`
- ❌ ProactorEventLoop 不相容 → 設定 `WindowsSelectorEventLoopPolicy`
- ✅ 所有資料表成功建立

---

## 技術決策記錄

### 資料庫架構
- **PostgreSQL**: 主要關聯式資料庫，使用 asyncpg 驅動
- **Redis**: 快取和 Celery 訊息佇列
- **Qdrant**: 向量資料庫，儲存文件嵌入向量

### ORM 框架
- **SQLAlchemy 2.0**: 使用 async API 和現代化的 `select()` 語法
- **Alembic**: 資料庫遷移工具，配置支援 async

### 資料模型設計原則
1. 所有模型繼承 `TimestampMixin` 自動管理時間戳記
2. 使用 `Mapped` 型別提示提升型別安全
3. 外鍵設定 `ondelete` 策略管理關聯刪除
4. 使用 Enum 類型約束狀態和角色欄位
5. 索引優化：在外鍵和常用查詢欄位建立索引

---

### 22:21 - 資料庫遷移修正與預設資料初始化完成 ✅

#### 問題解決：
1. **Base 類別重複定義問題**
   - ❌ 問題：`app/models/base.py` 和 `app/core/database.py` 中有兩個不同的 Base 類別
   - ✅ 解決：統一使用 `app/core/database.py` 中的 Base (SQLAlchemy 2.0 DeclarativeBase)
   - 修改所有模型文件的導入：`from app.core.database import Base`

2. **Alembic 無法偵測模型問題**
   - ❌ 問題：第一次 `alembic revision --autogenerate` 生成空遷移（只有 pass）
   - ✅ 解決：修正 Base 類別導入後重新生成遷移，成功偵測所有 5 個表和索引

3. **bcrypt 版本兼容性問題**
   - ❌ 問題：bcrypt 5.0.0 與 passlib 1.7.4 不兼容，報錯 "password cannot be longer than 72 bytes"
   - ✅ 解決：降級到 bcrypt 4.2.0

#### 建立的檔案：
1. **scripts/init_db.py** - 資料庫預設資料初始化腳本
   - `init_departments()`: 建立 3 個處室（人事室、會計室、總務處）
   - `init_categories()`: 建立 7 個分類（政策法規、操作手冊、會議記錄等）
   - `init_admin_users()`: 建立預設管理員（username: admin, password: admin123）
   - 支援重複執行（已存在的資料會跳過）

2. **app/core/security.py** - 完整的認證與安全功能
   - `get_password_hash()`: 密碼加密 (bcrypt)
   - `verify_password()`: 密碼驗證
   - `create_access_token()`: 建立 JWT Token
   - `authenticate_user()`: 使用者帳號密碼驗證
   - `get_current_user()`: JWT Token 驗證與使用者取得（依賴注入）
   - `get_current_active_user()`: 檢查使用者是否啟用
   - `require_role()`: 權限檢查裝飾器工廠

3. **scripts/check_tables.py** - 資料庫表檢查工具腳本

#### 執行的操作：
```bash
# 重新生成正確的遷移
alembic revision --autogenerate -m "Create all database tables"

# 執行遷移
alembic upgrade head

# 驗證表建立
python scripts/check_tables.py
# 結果：['alembic_version', 'departments', 'users', 'categories', 'files', 'activities']

# 執行預設資料初始化
python scripts/init_db.py
```

#### 初始化結果：
✅ **3 個處室**：人事室、會計室、總務處
✅ **7 個分類**：政策法規、操作手冊、會議記錄、財務報表、人事資料、採購文件、其他
✅ **1 個管理員**：
   - 帳號：admin
   - 密碼：admin123
   - Email：admin@example.com
   - 角色：ADMIN
   - 所屬：人事室

#### 套件版本更新：
```
bcrypt==4.2.0  # 從 5.0.0 降級
```

---

## 階段性總結

### 已完成的核心功能 ✅

1. **資料庫層 (100%)**
   - ✅ PostgreSQL 異步連線池 (asyncpg)
   - ✅ Redis 連線管理
   - ✅ Qdrant 向量資料庫連線
   - ✅ SQLAlchemy 2.0 ORM 模型（5個表）
   - ✅ Alembic 資料庫遷移
   - ✅ 預設資料初始化腳本

2. **認證與安全 (100%)**
   - ✅ 密碼加密/驗證 (bcrypt)
   - ✅ JWT Token 生成/驗證
   - ✅ 使用者身份驗證
   - ✅ 依賴注入系統
   - ✅ 權限檢查機制

3. **專案基礎設施 (100%)**
   - ✅ FastAPI 應用程式架構
   - ✅ 環境配置管理 (Pydantic Settings)
   - ✅ Docker Compose 開發/生產環境
   - ✅ 生命週期管理 (lifespan)
   - ✅ CORS 中介軟體

---

## 下一步計畫

### 待完成項目
- [ ] 建立預設資料初始化腳本 (scripts/init_db.py)
- [ ] 實作認證核心功能 (app/core/security.py)
- [ ] 實作使用者 API 端點
- [ ] 實作檔案上傳 API
- [ ] 實作 RAG 查詢功能
- [ ] Celery 背景任務設定

---

## 開發環境資訊

### Python 套件版本
```
fastapi==0.115.0
uvicorn==0.30.0
sqlalchemy==2.0.35
asyncpg==0.29.0
alembic==1.13.0
redis==5.0.0
qdrant-client==1.11.0
psycopg==3.2.12
psycopg-binary==3.2.12
pydantic==2.9.0
```

### 資料庫連線資訊
- PostgreSQL: `localhost:5432` (Docker 容器)
- Redis: `localhost:6379` (Docker 容器)
- Qdrant: `localhost:6333` (Docker 容器)

### 開發工具
- Python 3.13.9
- Docker Desktop
- VS Code
- Git

---

## 2025-11-13 (星期三)

### Step 12: 檔案上傳與管理 API 實作 ✅

#### 🎯 目標
實作檔案上傳、管理、下載等核心功能，包含檔案儲存服務、分類管理和活動記錄。

#### ✅ 完成項目

**1. 檔案與分類 Schema** (`app/schemas/`)
- `file.py`: 8 個 Schema (Base, Create, Update, Upload, Detail, List, Stats)
- `category.py`: 5 個 Schema (Base, Create, Update, List, Stats)

**2. 檔案儲存服務** (`app/services/file_storage.py`)
- 唯一檔名生成 (`YYYYMMDD_HHMMSS_uuid8_原檔名`)
- 處室隔離儲存 (按 `department_id` 分目錄)
- 檔案驗證 (大小 50MB, 格式 .pdf/.docx/.txt)
- 非同步檔案操作 (aiofiles, 1MB 分塊)
- 儲存空間統計

**3. 檔案管理 API** (`app/api/files.py` - 8 個端點)
- `GET /api/files`: 列表查詢 (分頁/搜尋/排序/篩選)
- `POST /api/files/upload`: 檔案上傳
- `GET /api/files/{id}`: 詳情查詢
- `PUT /api/files/{id}`: 更新資訊
- `DELETE /api/files/{id}`: 刪除檔案
- `GET /api/files/{id}/download`: 檔案下載
- `GET /api/files/stats`: 統計資訊

**4. 分類管理 API** (`app/api/categories.py` - 6 個端點)
- `GET /api/categories`: 列表查詢
- `GET /api/categories/{id}`: 詳情查詢
- `POST /api/categories`: 新增分類
- `PUT /api/categories/{id}`: 更新分類
- `DELETE /api/categories/{id}`: 刪除分類
- `GET /api/categories/stats`: 統計資訊

**5. 活動記錄服務** (`app/services/activity.py`)
- 記錄所有使用者操作
- 支援 login, logout, upload, download, delete, update, create, view

**6. 安全性增強** (`app/core/security.py`)
- `get_current_active_user()`: 檢查使用者啟用狀態
- `get_current_active_admin()`: 檢查管理員權限
- `get_current_super_admin()`: 檢查超級管理員權限

**7. 測試腳本** (`scripts/test_file_api.py`)
- 完整的 API 自動化測試 (9 個測試場景)
- 彩色終端輸出與測試報告

#### 📊 統計
- **新增檔案**: 7 個
- **修改檔案**: 3 個
- **新增代碼**: ~1,540 行
- **新增 API 端點**: 16 個

#### 🐛 解決的問題
1. 模組導入路徑錯誤 (`app.core.auth` → `app.core.security`)
2. 缺少權限檢查函數 (新增 3 個權限函數)
3. 缺少 activity service (創建服務)

#### 🔜 待完成
- Celery 背景任務整合 (檔案處理)
- Qdrant 向量儲存整合
- RAG 查詢 API (Step 13)

---

### 14:30 - 檔案處理接口與模擬實現完成 ✅

#### 🎯 目標
完善檔案處理流程，為外部檔案處理模組（文字擷取、向量化等）預留標準接口，支援未來整合。

#### ✅ 完成項目

**1. 檔案處理接口定義** (`app/services/file_processor_interface.py` - 200 行)
- `IFileProcessor` 抽象基類 (ABC)：定義 5 個標準方法
  * `process_file()`: 處理單個檔案
  * `get_processing_status()`: 查詢處理狀態
  * `cancel_processing()`: 取消處理
  * `retry_processing()`: 重試失敗的處理
  * `batch_process()`: 批次處理多個檔案
- `ProcessingStatus` 枚舉：6 種狀態 (pending, queued, processing, completed, failed, cancelled)
- `ProcessingStep` 枚舉：5 個處理步驟 (validation, text_extraction, chunking, embedding, indexing)
- `FileProcessingResult` 類：封裝處理結果
- `FileProcessorRegistry` 註冊器：支援多種處理器並存

**2. 模擬檔案處理器** (`app/services/mock_file_processor.py` - 200 行)
- 完整實現 `IFileProcessor` 接口
- 模擬 5 個處理步驟：驗證 → 文字擷取 → 分塊 → 嵌入 → 索引
- 可配置延遲時間和成功率（用於測試）
- 生成模擬文本內容和統計數據
- 包含詳細日誌輸出

**3. File 模型增強** (`app/models/file.py`)
新增 8 個欄位：
- `original_filename`: 原始檔案名稱
- `mime_type`: MIME 類型
- `description`: 檔案描述
- `vector_count`: 向量數量
- `processing_step`: 當前處理步驟
- `processing_progress`: 處理進度 (0-100)
- `processing_started_at`: 處理開始時間
- `processing_completed_at`: 處理完成時間

**4. 資料庫遷移** (`alembic/versions/20240115_add_file_processing_fields.py`)
- 添加所有新欄位的遷移腳本
- 包含向下遷移 (rollback) 支援

**5. 檔案上傳流程增強** (`app/api/files.py`)
- 整合模擬處理器到上傳端點
- 記錄處理開始和完成時間
- 更新處理狀態和進度
- 記錄錯誤訊息

**6. 新增 API 端點** (2 個)
- `GET /api/files/{id}/processing-status`: 查詢檔案處理狀態
  * 返回當前步驟、進度、時間等詳細資訊
  * 計算處理持續時間
- `POST /api/files/batch-upload`: 批次上傳檔案
  * 支援一次上傳最多 10 個檔案
  * 所有檔案共用分類和描述
  * 返回每個檔案的處理結果
  * 部分失敗不影響其他檔案

**7. 測試增強** (`scripts/test_file_api.py`)
- 新增 `test_processing_status()`: 測試處理狀態查詢
- 新增 `test_batch_upload()`: 測試批次上傳（3 個檔案）
- 測試場景從 9 個擴展到 11 個
- 更新測試執行順序

**8. 整合文檔** (`backend_docs/FILE_PROCESSOR_INTEGRATION.md` - 600 行)
- 詳細的架構設計說明
- 完整的接口定義和使用範例
- 三種接入方式：直接替換、註冊器模式、配置檔案
- 背景任務建議 (Celery, BackgroundTasks)
- 注意事項和後續計劃

#### 🎨 技術亮點

1. **開放封閉原則**：使用 ABC 定義接口，核心系統無需修改即可接入不同實現
2. **註冊器模式**：支援多種處理器動態註冊和切換
3. **異步優先**：所有方法都是 async，支援並發處理
4. **詳細追蹤**：記錄處理的每個步驟和時間戳
5. **靈活接入**：提供三種接入方式適應不同場景
6. **完整測試**：模擬處理器可用於開發和測試階段

#### 🔧 三種接入方式

**方式一：直接替換（最簡單）**
```python
from your_module import YourFileProcessor
file_processor = YourFileProcessor(config)
```

**方式二：註冊器模式（推薦）**
```python
registry = FileProcessorRegistry()
registry.register("real_processor", YourFileProcessor())
processor = registry.get("real_processor")
```

**方式三：配置檔案（最靈活）**
```python
processor_type = config.FILE_PROCESSOR_TYPE
processor = load_processor_from_config(processor_type)
```

#### 📊 統計
- **新增檔案**: 4 個核心文件
- **修改檔案**: 3 個（模型、API、測試）
- **新增代碼**: ~1,100 行
- **新增 API 端點**: 2 個
- **文檔**: 600 行整合文檔

#### 🐛 解決的問題
1. 缺少 `datetime` 導入 → 添加到 `app/api/files.py`
2. File 模型欠缺追蹤欄位 → 新增 8 個欄位
3. 上傳流程缺少處理整合 → 整合模擬處理器

#### ⚠️ 重要提醒
當前使用**模擬處理器**進行同步演示，生產環境必須：
1. 改用真實的檔案處理模組
2. 使用 Celery 或 BackgroundTasks 進行背景處理
3. 避免阻塞 API 響應

#### 🔜 後續建議
1. **背景任務整合**: 將同步處理改為 Celery 背景任務
2. **WebSocket 支援**: 實現處理進度即時推送
3. **重試機制**: 實現智能重試策略
4. **隊列管理**: 實現優先級隊列
5. **監控儀表板**: 顯示處理統計和性能指標

#### 📝 相關文檔
- 整合文檔：`backend_docs/FILE_PROCESSOR_INTEGRATION.md`
- 接口定義：`app/services/file_processor_interface.py`
- 模擬實現：`app/services/mock_file_processor.py`

---

## 備註

所有資料庫連線已測試成功，FastAPI 應用程式可正常啟動並連接到所有資料庫服務。
檔案上傳與管理 API 已完成實作，檔案處理接口已就緒，待 Docker 環境測試和真實處理器整合。
