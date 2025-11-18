# 測試指南

## 📋 測試結構

```
tests/
├── conftest.py              # 測試配置和 Fixtures
├── test_auth.py             # 認證系統測試
├── test_users.py            # 使用者管理測試
├── test_departments.py      # 處室管理測試
├── test_settings.py         # 系統設定測試
├── test_models.py           # 資料模型單元測試
└── README.md                # 本文件
```

## 🚀 快速開始

### 安裝測試依賴

```bash
pip install -r requirements-dev.txt
```

### 執行所有測試

```bash
pytest
```

或使用便捷腳本：

```bash
python scripts/run_tests.py
```

## 📊 測試類型

### 1. 單元測試 (Unit Tests)

測試獨立的函數、類和模組。

```bash
# 執行所有單元測試
pytest -m unit

# 執行特定模型測試
pytest tests/test_models.py
```

### 2. 整合測試 (Integration Tests)

測試 API 端點和模組之間的交互。

```bash
# 執行所有整合測試
pytest -m integration

# 執行特定 API 測試
pytest tests/test_users.py
pytest tests/test_departments.py
pytest tests/test_settings.py
```

### 3. 認證測試 (Authentication Tests)

測試登入、權限控制等功能。

```bash
# 執行認證相關測試
pytest -m auth

# 或直接執行測試檔案
pytest tests/test_auth.py
```

### 4. 資料庫測試 (Database Tests)

測試資料庫模型和操作。

```bash
# 執行資料庫相關測試
pytest -m database
```

## 🎯 測試標記 (Markers)

測試使用以下標記進行分類：

- `@pytest.mark.unit` - 單元測試
- `@pytest.mark.integration` - 整合測試
- `@pytest.mark.auth` - 認證測試
- `@pytest.mark.api` - API 測試
- `@pytest.mark.database` - 資料庫測試
- `@pytest.mark.slow` - 慢速測試

## 📈 覆蓋率報告

### 生成覆蓋率報告

```bash
# HTML 報告
pytest --cov=app --cov-report=html

# 終端報告
pytest --cov=app --cov-report=term-missing

# 兩者都生成
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### 查看 HTML 報告

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## 🔧 測試配置

### pytest.ini

配置文件位於專案根目錄，包含：

- 測試路徑
- 標記定義
- 輸出選項
- 覆蓋率設置
- 日誌配置

### conftest.py

提供測試所需的 Fixtures：

#### 資料庫 Fixtures
- `test_engine` - 測試資料庫引擎
- `test_session_maker` - Session 工廠
- `db_session` - 資料庫 Session
- `override_get_db` - 覆蓋資料庫依賴

#### 客戶端 Fixtures
- `client` - 同步測試客戶端
- `async_client` - 異步測試客戶端

#### 測試資料 Fixtures
- `test_department` - 測試處室
- `test_admin_user` - 管理員使用者
- `test_dept_admin_user` - 處室管理員
- `test_normal_user` - 普通使用者

#### 認證 Fixtures
- `admin_token` - 管理員 Token
- `dept_admin_token` - 處室管理員 Token
- `user_token` - 普通使用者 Token
- `admin_headers` - 管理員請求標頭
- `dept_admin_headers` - 處室管理員請求標頭
- `user_headers` - 普通使用者請求標頭

## 📝 編寫測試

### 測試類結構

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.api
@pytest.mark.integration
class TestFeature:
    """功能測試類"""
    
    def test_success_case(self, client: TestClient, admin_headers):
        """測試成功情況"""
        response = client.get("/api/endpoint", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
    
    def test_error_case(self, client: TestClient):
        """測試錯誤情況"""
        response = client.get("/api/endpoint")
        
        assert response.status_code == 401
```

### 異步測試

```python
@pytest.mark.asyncio
async def test_async_function(db_session):
    """異步測試"""
    result = await some_async_function(db_session)
    assert result is not None
```

### 使用 Fixtures

```python
def test_with_fixtures(
    client: TestClient,
    admin_headers: dict,
    test_department: Department,
):
    """使用多個 Fixtures 的測試"""
    response = client.get(
        f"/api/departments/{test_department.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
```

## 🐛 除錯測試

### 顯示詳細輸出

```bash
# 顯示 print 語句
pytest -s

# 顯示詳細錯誤
pytest -vv

# 在第一個錯誤時停止
pytest -x

# 顯示最慢的 10 個測試
pytest --durations=10
```

### 執行特定測試

```bash
# 執行特定測試檔案
pytest tests/test_users.py

# 執行特定測試類
pytest tests/test_users.py::TestUserManagement

# 執行特定測試函數
pytest tests/test_users.py::TestUserManagement::test_list_users

# 使用關鍵字過濾
pytest -k "user and not delete"
```

## 📊 測試報告

### 使用便捷腳本

```bash
# 執行所有測試
python scripts/run_tests.py

# 執行特定類型
python scripts/run_tests.py unit
python scripts/run_tests.py integration
python scripts/run_tests.py auth

# 不生成覆蓋率報告
python scripts/run_tests.py --no-coverage

# 安靜模式
python scripts/run_tests.py --quiet
```

## ✅ 測試檢查清單

編寫新功能時，確保包含以下測試：

- [ ] 成功情況測試
- [ ] 錯誤情況測試（400, 401, 403, 404 等）
- [ ] 邊界條件測試
- [ ] 權限控制測試
- [ ] 資料驗證測試
- [ ] 關聯關係測試（如果有）
- [ ] 並發測試（如果需要）

## 🎓 最佳實踐

1. **測試命名**: 使用描述性名稱，說明測試內容
   ```python
   def test_create_user_with_valid_data()  # ✅ 好
   def test_user()  # ❌ 不好
   ```

2. **AAA 模式**: Arrange（準備）、Act（執行）、Assert（斷言）
   ```python
   def test_example(client, admin_headers):
       # Arrange
       data = {"name": "Test"}
       
       # Act
       response = client.post("/api/endpoint", json=data, headers=admin_headers)
       
       # Assert
       assert response.status_code == 201
   ```

3. **獨立測試**: 每個測試應該獨立運行，不依賴其他測試

4. **清理資源**: 使用 Fixtures 自動清理測試資料

5. **有意義的斷言**: 提供清晰的錯誤訊息
   ```python
   assert user.role == "Admin", f"Expected Admin but got {user.role}"
   ```

## 📚 參考資源

- [pytest 文檔](https://docs.pytest.org/)
- [pytest-asyncio 文檔](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

## 🆘 常見問題

### Q: 測試資料庫無法創建？
A: 確保已安裝 `aiosqlite`: `pip install aiosqlite`

### Q: 異步測試失敗？
A: 確保函數標記為 `@pytest.mark.asyncio` 且 pytest.ini 中設置了 `asyncio_mode = auto`

### Q: Fixtures 不可用？
A: 確保 `conftest.py` 在正確的位置，pytest 會自動載入

### Q: 覆蓋率報告不準確？
A: 使用 `--cov-branch` 選項以包含分支覆蓋率

## 📞 需要幫助？

如有問題，請查看：
- 專案文檔: `backend_docs/`
- API 文檔: `API_DOCUMENTATION.md`
- 開發日誌: `DEVELOPMENT_LOG.md`
