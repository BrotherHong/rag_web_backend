"""
認證系統測試
測試登入、登出、Token 驗證等功能
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.auth
class TestAuthentication:
    """認證功能測試類"""
    
    def test_login_success(self, client: TestClient, test_admin_user):
        """測試成功登入"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "admin",
                "password": "admin123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client: TestClient, test_admin_user):
        """測試錯誤密碼"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "admin",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        assert "密碼錯誤" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """測試不存在的使用者"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "nonexistent",
                "password": "password",
            },
        )
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client: TestClient, admin_headers):
        """測試獲取當前使用者資訊"""
        response = client.get("/api/auth/me", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
    
    def test_unauthorized_access(self, client: TestClient):
        """測試未授權訪問"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_invalid_token(self, client: TestClient):
        """測試無效 Token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        assert response.status_code == 401


@pytest.mark.auth
class TestAuthorization:
    """權限控制測試類"""
    
    def test_admin_access(self, client: TestClient, admin_headers):
        """測試管理員權限"""
        response = client.get("/api/users", headers=admin_headers)
        assert response.status_code == 200
    
    def test_dept_admin_limited_access(self, client: TestClient, dept_admin_headers):
        """測試處室管理員有限權限"""
        # 可以訪問使用者列表
        response = client.get("/api/users", headers=dept_admin_headers)
        assert response.status_code == 200
        
        # 但不能創建處室（僅管理員可以）
        response = client.post(
            "/api/departments",
            headers=dept_admin_headers,
            json={"name": "新處室", "description": "測試"},
        )
        assert response.status_code == 403
    
    def test_normal_user_restricted_access(self, client: TestClient, user_headers):
        """測試普通使用者受限權限"""
        # 可以訪問使用者列表(處室管理員只能看自己處室)
        response = client.get("/api/users", headers=user_headers)
        assert response.status_code == 200
        
        # 但可以查看自己的資訊
        response = client.get("/api/auth/me", headers=user_headers)
        assert response.status_code == 200
