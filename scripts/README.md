# 資料庫初始化腳本使用指南

## 🎯 快速選擇

### 情況 1：第一次設定開發環境
```bash
python scripts/reset_db.py
```
**說明**：完整重置並初始化所有資料（處室、分類、管理員、系統設定）

---

### 情況 2：只需要新增測試帳號和處室資料
```bash
python scripts/init_db.py
```
**說明**：建立處室、分類、管理員帳號（不影響現有系統設定）

---

### 情況 3：只需要重置系統設定
```bash
python scripts/init_system_settings.py
```
**說明**：初始化系統設定（app, rag, security, feature）

---

### 情況 4：初始化 FAQ 常見問題資料
```bash
python scripts/init_faqs.py
```
**說明**：初始化全站通用的常見問題（8 筆預設資料）

**刪除所有 FAQ**：
```bash
python scripts/init_faqs.py --delete
```

---

### 情況 5：生產環境部署
```bash
# 1. 執行資料庫遷移
alembic upgrade head

# 2. 初始化基本資料
python scripts/init_db.py

# 3. 初始化系統設定
python scripts/init_system_settings.py

# 4. 初始化 FAQ 資料
python scripts/init_faqs.py
```

---

## ⚠️ 注意

- **reset_db.py 會刪除所有資料**，生產環境請勿使用
- 預設密碼統一為 `admin123`，請登入後立即修改
- 所有腳本可重複執行，不會產生重複資料
- FAQ 資料可以在後台管理介面中新增、編輯和刪除
