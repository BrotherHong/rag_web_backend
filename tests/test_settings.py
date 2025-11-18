"""
系統設定測試
測試系統設定 CRUD、公開設定等功能
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.integration
class TestSystemSettings:
    """系統設定測試類"""
    
    def test_get_public_settings(self, client: TestClient):
        """測試獲取公開設定（無需認證）"""
        response = client.get("/api/settings/public")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # 公開設定不應該包含敏感資訊
        for setting in data:
            assert "password" not in setting["key"].lower()
            assert "secret" not in setting["key"].lower()
            assert "api_key" not in setting["key"].lower()
    
    def test_list_settings(self, client: TestClient, admin_headers, test_settings):
        """測試列出所有設定"""
        response = client.get("/api/settings", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 3  # 至少有 3 個測試設定
    
    def test_list_settings_by_category(self, client: TestClient, admin_headers, test_settings):
        """測試按類別篩選設定"""
        response = client.get(
            "/api/settings?category=rag",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        for setting in data["items"]:
            assert setting["category"] == "rag"
    
    def test_list_settings_with_search(self, client: TestClient, admin_headers, test_settings):
        """測試搜尋設定"""
        response = client.get(
            "/api/settings?search=temperature",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        for setting in data["items"]:
            assert "temperature" in setting["key"].lower() or "temperature" in setting["display_name"].lower()
    
    def test_get_setting(self, client: TestClient, admin_headers, test_settings):
        """測試獲取特定設定"""
        response = client.get(
            "/api/settings/app.max_file_size",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "app.max_file_size"
        assert "value" in data
    
    def test_create_setting(self, client: TestClient, admin_headers):
        """測試創建新設定"""
        response = client.post(
            "/api/settings",
            headers=admin_headers,
            json={
                "key": "test.new_setting",
                "value": {"test": "value"},
                "category": "app",
                "display_name": "測試設定",
                "description": "測試設定",
                "is_public": False,
                "is_sensitive": False,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "test.new_setting"
        assert data["value"] == {"test": "value"}
    
    def test_create_setting_duplicate_key(self, client: TestClient, admin_headers, test_settings):
        """測試創建重複的設定鍵"""
        response = client.post(
            "/api/settings",
            headers=admin_headers,
            json={
                "key": "app.max_file_size",  # 已存在
                "value": {"size": 100},
                "category": "app",
                "display_name": "重複的鍵",
                "description": "重複的鍵",
            },
        )
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_update_setting(self, client: TestClient, admin_headers, test_settings):
        """測試更新設定"""
        response = client.put(
            "/api/settings/app.max_file_size",
            headers=admin_headers,
            json={
                "value": {"bytes": 104857600},  # 100MB
                "description": "更新後的檔案大小限制",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["bytes"] == 104857600
    
    def test_batch_update_settings(self, client: TestClient, admin_headers, test_settings):
        """測試批次更新設定"""
        response = client.post(
            "/api/settings/batch",
            headers=admin_headers,
            json={
                "settings": {
                    "rag.temperature": {"value": 0.8},
                    "rag.max_tokens": {"value": 3000}
                }
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_delete_setting(self, client: TestClient, admin_headers):
        """測試刪除設定"""
        # 先創建一個測試設定
        create_response = client.post(
            "/api/settings",
            headers=admin_headers,
            json={
                "key": "test.to_delete",
                "value": {"test": "delete"},
                "category": "app",
                "display_name": "待刪除的設定",
                "description": "待刪除的設定",
            },
        )
        assert create_response.status_code == 201
        
        # 刪除設定
        response = client.delete(
            "/api/settings/test.to_delete",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        
        # 驗證已被刪除
        get_response = client.get(
            "/api/settings/test.to_delete",
            headers=admin_headers,
        )
        assert get_response.status_code == 404
    
    def test_normal_user_cannot_modify_settings(self, client: TestClient, user_headers):
        """測試普通使用者不能修改設定"""
        response = client.put(
            "/api/settings/app.max_file_size",
            headers=user_headers,
            json={
                "value": {"size": 1000},
            },
        )
        
        assert response.status_code == 403
    
    def test_sensitive_setting_hidden_from_public(self, client: TestClient, admin_headers):
        """測試敏感設定不會出現在公開 API"""
        # 創建敏感設定
        create_response = client.post(
            "/api/settings",
            headers=admin_headers,
            json={
                "key": "security.api_key",
                "value": {"key": "secret123"},
                "category": "security",
                "display_name": "API 密鑰",
                "description": "敏感設定",
                "is_sensitive": True,
                "is_public": False,
            },
        )
        assert create_response.status_code == 201
        
        # 檢查公開 API
        public_response = client.get("/api/settings/public")
        assert public_response.status_code == 200
        public_data = public_response.json()
        
        # 敏感且非公開的設定不應該出現
        keys = [s["key"] for s in public_data]
        assert "security.api_key" not in keys
