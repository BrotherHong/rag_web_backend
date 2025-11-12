# 🗄️ 資料庫設計

## 資料庫選擇：PostgreSQL 16

### 為什麼選擇 PostgreSQL？
- ✅ **ACID 保證** - 完整的交易支援
- ✅ **JSON 支援** - 處理彈性資料結構
- ✅ **全文檢索** - 內建 FTS (pg_trgm)
- ✅ **成熟穩定** - 企業級資料庫
- ✅ **開源免費** - 無授權費用

---

## 資料表設計

> **注意**: 此設計根據前端實際使用的資料結構設計（參考 `src/services/mock/database.js`）

### 1. departments (處室表)

處室/部門資訊，用於資料隔離。

```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(20) DEFAULT 'blue',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_departments_name ON departments(name);
CREATE INDEX idx_departments_active ON departments(is_active);

-- 範例資料（對應前端 mock data）
INSERT INTO departments (id, name, description, color, created_at) VALUES
(1, '人事室', '負責人事相關業務', 'red', '2025-10-01'),
(2, '會計室', '負責會計相關業務', 'blue', '2025-10-01'),
(3, '總務處', '負責總務相關業務', 'green', '2025-10-01');
```

---

### 2. users (使用者表)

系統使用者資訊，包含認證與權限。

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    department_id INTEGER REFERENCES departments(id) ON DELETE RESTRICT,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    status VARCHAR(20) DEFAULT 'active',
    is_super_admin BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_role CHECK (role IN ('super_admin', 'admin', 'viewer')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'suspended'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department ON users(department_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- 預設使用者（對應前端 mock data）
-- 密碼: super123, admin123 (實際部署時請修改)
INSERT INTO users (id, username, email, hashed_password, name, department_id, role, status, is_super_admin) VALUES
(1, 'superadmin', 'superadmin@ncku.edu.tw', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oQN5YvEz5QGK', '系統管理員', NULL, 'super_admin', 'active', TRUE),
(2, 'hr_admin', 'hr_admin@ncku.edu.tw', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oQN5YvEz5QGK', '人事室管理員', 1, 'admin', 'active', FALSE),
(3, 'acc_admin', 'acc_admin@ncku.edu.tw', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oQN5YvEz5QGK', '會計室管理員', 2, 'admin', 'active', FALSE),
(4, 'gen_admin', 'gen_admin@ncku.edu.tw', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oQN5YvEz5QGK', '總務處管理員', 3, 'admin', 'active', FALSE);
```

---

### 3. categories (分類表)

檔案分類管理。

```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20) DEFAULT 'blue',
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    file_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_category_per_department UNIQUE (name, department_id)
);

CREATE INDEX idx_categories_department ON categories(department_id);
CREATE INDEX idx_categories_name ON categories(name);

-- 預設分類（對應前端 mock data）
INSERT INTO categories (id, name, color, department_id, created_at) VALUES
-- 人事室
(101, '規章制度', 'blue', 1, '2025-10-01'),
(102, '請假相關', 'green', 1, '2025-10-01'),
(103, '薪資福利', 'yellow', 1, '2025-10-01'),
(104, '未分類', 'gray', 1, '2025-10-01'),
-- 會計室
(201, '會計準則', 'blue', 2, '2025-10-01'),
(202, '報表範本', 'purple', 2, '2025-10-01'),
(203, '未分類', 'gray', 2, '2025-10-01'),
-- 總務處
(301, '採購流程', 'orange', 3, '2025-10-01'),
(302, '維修管理', 'red', 3, '2025-10-01'),
(303, '未分類', 'gray', 3, '2025-10-01');
```

---

### 4. files (檔案表)

檔案元資料與管理資訊。

```sql
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    uploader_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    description TEXT,
    tags TEXT[],
    status VARCHAR(20) DEFAULT 'pending',
    is_vectorized BOOLEAN DEFAULT FALSE,
    vector_count INTEGER DEFAULT 0,
    processing_error TEXT,
    download_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_files_department ON files(department_id);
CREATE INDEX idx_files_category ON files(category_id);
CREATE INDEX idx_files_uploader ON files(uploader_id);
CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_files_created ON files(created_at DESC);
CREATE INDEX idx_files_filename ON files(filename);

-- GIN 索引用於陣列搜尋
CREATE INDEX idx_files_tags ON files USING GIN(tags);

-- 全文檢索索引
CREATE INDEX idx_files_fulltext ON files USING GIN(
    to_tsvector('english', 
        COALESCE(original_filename, '') || ' ' || 
        COALESCE(description, '')
    )
);
```

---

### 5. activities (活動記錄表)

系統操作記錄，用於稽核追蹤。

```sql
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    description TEXT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_action CHECK (action IN (
        'login', 'logout',
        'upload', 'download', 'delete', 'update',
        'create', 'view',
        'backup', 'restore'
    ))
);

CREATE INDEX idx_activities_user ON activities(user_id);
CREATE INDEX idx_activities_action ON activities(action);
CREATE INDEX idx_activities_created ON activities(created_at DESC);
CREATE INDEX idx_activities_department ON activities(department_id);
CREATE INDEX idx_activities_entity ON activities(entity_type, entity_id);

-- JSONB 索引
CREATE INDEX idx_activities_metadata ON activities USING GIN(metadata);
```

---

### 6. system_settings (系統設定表)

全域系統設定。

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_value_type CHECK (value_type IN ('string', 'number', 'boolean', 'json'))
);

CREATE INDEX idx_settings_key ON system_settings(key);
CREATE INDEX idx_settings_public ON system_settings(is_public);

-- 預設設定
INSERT INTO system_settings (key, value, value_type, description, is_public) VALUES
('system_name', 'RAG 知識庫管理系統', 'string', '系統名稱', TRUE),
('max_file_size', '52428800', 'number', '最大檔案大小 (50MB)', TRUE),
('allowed_extensions', '.pdf,.docx,.txt', 'string', '允許的檔案類型', TRUE),
('enable_auto_vectorize', 'true', 'boolean', '自動向量化', FALSE),
('maintenance_mode', 'false', 'boolean', '維護模式', FALSE),
('backup_retention_days', '30', 'number', '備份保留天數', FALSE);
```

---

### 7. backups (備份記錄表)

系統備份記錄。

```sql
CREATE TABLE backups (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    backup_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_backup_type CHECK (backup_type IN ('full', 'incremental', 'manual')),
    CONSTRAINT chk_backup_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
);

CREATE INDEX idx_backups_created ON backups(created_at DESC);
CREATE INDEX idx_backups_type ON backups(backup_type);
CREATE INDEX idx_backups_status ON backups(status);
```

---

## 資料表關聯圖

```
┌─────────────────┐
│   departments   │
└────────┬────────┘
         │
         │ 1:N
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌─────────────────┐        ┌─────────────────┐
│     users       │        │   categories    │
└────────┬────────┘        └────────┬────────┘
         │                          │
         │ 1:N                      │ 1:N
         │                          │
         └──────────┬───────────────┘
                    ▼
           ┌─────────────────┐
           │     files       │
           └────────┬────────┘
                    │
                    │ 1:N
                    ▼
           ┌─────────────────┐
           │   activities    │
           └─────────────────┘
```

---

## SQLAlchemy 模型定義

### Base 配置
```python
# app/models/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, func

Base = declarative_base()

class TimestampMixin:
    """時間戳記混入類別"""
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### Department 模型
```python
# app/models/department.py
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Department(Base, TimestampMixin):
    __tablename__ = 'departments'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    color = Column(String(20), default='blue')
    is_active = Column(Boolean, default=True, index=True)
    
    # 關聯
    users = relationship('User', back_populates='department')
    categories = relationship('Category', back_populates='department', cascade='all, delete-orphan')
    files = relationship('File', back_populates='department', cascade='all, delete-orphan')
```

### User 模型
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100))  # 對應前端的 name 欄位
    department_id = Column(Integer, ForeignKey('departments.id', ondelete='RESTRICT'), index=True)  # 超級管理員可為 NULL
    role = Column(String(20), nullable=False, default='viewer', index=True)
    status = Column(String(20), default='active', index=True)  # active, inactive, suspended
    is_super_admin = Column(Boolean, default=False)
    last_login = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("role IN ('super_admin', 'admin', 'viewer')", name='chk_role'),
        CheckConstraint("status IN ('active', 'inactive', 'suspended')", name='chk_status'),
    )
    
    # 關聯
    department = relationship('Department', back_populates='users')
    files = relationship('File', back_populates='uploader')
    activities = relationship('Activity', back_populates='user')
```

### Category 模型
```python
# app/models/category.py
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Category(Base, TimestampMixin):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default='blue')
    department_id = Column(Integer, ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, index=True)
    file_count = Column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint('name', 'department_id', name='unique_category_per_department'),
    )
    
    # 關聯
    department = relationship('Department', back_populates='categories')
    files = relationship('File', back_populates='category')
```

### File 模型
```python
# app/models/file.py
from sqlalchemy import Column, Integer, String, BigInteger, Text, Boolean, DateTime, ForeignKey, ARRAY, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from .base import Base, TimestampMixin

class File(Base, TimestampMixin):
    __tablename__ = 'files'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100))
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), index=True)
    department_id = Column(Integer, ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, index=True)
    uploader_id = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    description = Column(Text)
    tags = Column(PG_ARRAY(Text))
    status = Column(String(20), default='pending', index=True)
    is_vectorized = Column(Boolean, default=False)
    vector_count = Column(Integer, default=0)
    processing_error = Column(Text)
    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='chk_status'),
    )
    
    # 關聯
    category = relationship('Category', back_populates='files')
    department = relationship('Department', back_populates='files')
    uploader = relationship('User', back_populates='files')
```

### Activity 模型
```python
# app/models/activity.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base

class Activity(Base):
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    username = Column(String(50))
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    description = Column(Text, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    department_id = Column(Integer, ForeignKey('departments.id', ondelete='SET NULL'), index=True)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=func.now(), index=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('login', 'logout', 'upload', 'download', 'delete', 'update', 'create', 'view', 'backup', 'restore')",
            name='chk_action'
        ),
    )
    
    # 關聯
    user = relationship('User', back_populates='activities')
    department = relationship('Department')
```

---

## 資料庫遷移 (Alembic)

### 初始化
```bash
# 安裝 Alembic
pip install alembic

# 初始化 Alembic
alembic init alembic

# 編輯 alembic.ini
# sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/rag_db
```

### 配置 env.py
```python
# alembic/env.py
from app.models.base import Base
from app.models.department import Department
from app.models.user import User
from app.models.category import Category
from app.models.file import File
from app.models.activity import Activity
from app.models.settings import SystemSetting
from app.models.backup import Backup

target_metadata = Base.metadata

# 異步遷移支援
from sqlalchemy.ext.asyncio import create_async_engine

async def run_migrations_online():
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
```

### 建立遷移
```bash
# 自動生成遷移檔案
alembic revision --autogenerate -m "Initial tables"

# 執行遷移
alembic upgrade head

# 回滾
alembic downgrade -1
```

---

## 查詢最佳化

### 複合索引
```sql
-- 常見查詢組合
CREATE INDEX idx_files_dept_status ON files(department_id, status);
CREATE INDEX idx_files_dept_category ON files(department_id, category_id);
CREATE INDEX idx_activities_user_action ON activities(user_id, action);
```

### 分區表 (大量資料時)
```sql
-- 按月份分區 activities 表
CREATE TABLE activities (
    -- 欄位定義...
) PARTITION BY RANGE (created_at);

CREATE TABLE activities_2025_01 PARTITION OF activities
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### 資料清理政策
```sql
-- 定期清理舊活動記錄 (保留 6 個月)
DELETE FROM activities 
WHERE created_at < NOW() - INTERVAL '6 months';

-- 或使用 PostgreSQL 自動清理
-- pg_cron 擴展
```

---

**下一步**: 閱讀 [04_API_DESIGN.md](./04_API_DESIGN.md) 了解 API 端點設計
