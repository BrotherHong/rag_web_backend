# Scripts 目錄說明

此目錄包含專案的實用腳本和測試工具。

## 測試腳本

### test_all_apis.py
**主要的 API 全面測試腳本**

測試所有已實作的 API 端點，包括：
- 認證模組（登入、取得使用者資訊）
- 使用者管理（列表、詳情）
- 分類管理（CRUD 操作、統計）
- 檔案管理（列表、統計）
- 處室管理（列表、詳情）
- 活動記錄
- RAG 查詢與歷史
- 系統設定
- 登出功能

**使用方式：**
```bash
python scripts/test_all_apis.py
```

**前置條件：**
- FastAPI 伺服器正在運行（http://localhost:8000）
- 資料庫已初始化
- 預設管理員帳號存在（username: admin, password: admin123）

### run_tests.py
**單元測試執行腳本**

執行專案的單元測試套件。

**使用方式：**
```bash
python scripts/run_tests.py
```

## 初始化腳本

### init_db.py
**資料庫初始化腳本**

初始化資料庫結構並建立預設資料，包括：
- 建立所有資料表
- 建立預設處室（人事室、教務處、總務處）
- 建立預設管理員帳號
- 建立預設分類

**使用方式：**
```bash
python scripts/init_db.py
```

### init_system_settings.py
**系統設定初始化腳本**

初始化系統預設設定值。

**使用方式：**
```bash
python scripts/init_system_settings.py
```

## 工具腳本

### check_tables.py
**資料表檢查工具**

檢查資料庫中的資料表結構和資料。

**使用方式：**
```bash
python scripts/check_tables.py
```

## 執行順序建議

1. 首次設定：
   ```bash
   python scripts/init_db.py
   python scripts/init_system_settings.py
   ```

2. 啟動伺服器後測試：
   ```bash
   python scripts/test_all_apis.py
   ```

3. 開發過程中：
   ```bash
   python scripts/run_tests.py  # 執行單元測試
   ```

## 注意事項

- 所有腳本都應該從專案根目錄執行
- 確保 `.env` 文件中的資料庫連線資訊正確
- 測試腳本需要伺服器正在運行
- 初始化腳本會覆蓋現有資料，請謹慎使用
