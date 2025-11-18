"""
使用者管理測試
測試使用者 CRUD、權限管理、統計等功能
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.integration
class TestUserManagement:
    """使用者管理測試類"""
    
    def test_list_users(self, client: TestClient, admin_headers):
        """測試列出使用者"""
        response = client.get("/api/users", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert len(data["items"]) > 0
    
    def test_list_users_with_pagination(self, client: TestClient, admin_headers):
        """測試分頁功能"""
        response = client.get(
            "/api/users?page=1&limit=5",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    def test_list_users_with_filter(self, client: TestClient, admin_headers):
        """測試角色篩選"""
        response = client.get(
            "/api/users?role=admin",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        for user in data["items"]:
            assert user["role"] == "admin"
    
    def test_list_users_with_search(self, client: TestClient, admin_headers):
        """測試搜尋功能"""
        response = client.get(
            "/api/users?search=admin",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
    
    def test_get_user(self, client: TestClient, admin_headers, test_admin_user):
        """測試獲取使用者詳情"""
        response = client.get(
            f"/api/users/{test_admin_user.id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_admin_user.id
        assert data["username"] == "admin"
    
    def test_create_user(self, client: TestClient, admin_headers, test_department):
        """測試創建使用者"""
        response = client.post(
            "/api/users",
            headers=admin_headers,
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "password123",
                "full_name": "新使用者",
                "department_id": test_department.id,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@test.com"
    
    def test_create_user_duplicate_username(self, client: TestClient, admin_headers, test_admin_user, test_department):
        """測試創建重複使用者名稱"""
        response = client.post(
            "/api/users",
            headers=admin_headers,
            json={
                "username": "admin",  # 已存在
                "email": "another@test.com",
                "password": "password123",
                "full_name": "另一個使用者",
                "role": "USER",
                "department_id": test_department.id,
            },
        )
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_update_user(self, client: TestClient, admin_headers, test_normal_user):
        """測試更新使用者"""
        response = client.patch(
            f"/api/users/{test_normal_user.id}",
            headers=admin_headers,
            json={
                "full_name": "更新後的名稱",
                "email": "updated@test.com",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "更新後的名稱"
        assert data["email"] == "updated@test.com"
    
    def test_change_password(self, client: TestClient, user_headers, test_normal_user):
        """測試修改密碼"""
        response = client.put(
            f"/api/users/{test_normal_user.id}/password",
            headers=user_headers,
            json={
                "old_password": "user123",
                "new_password": "newpassword123",
            },
        )
        
        assert response.status_code == 200
        
        # 驗證新密碼可以登入
        login_response = client.post(
            "/api/auth/token",
            data={
                "username": "user",
                "password": "newpassword123",
            },
        )
        assert login_response.status_code == 200
    
    def test_change_password_wrong_old_password(self, client: TestClient, user_headers, test_normal_user):
        """測試錯誤的舊密碼"""
        response = client.put(
            f"/api/users/{test_normal_user.id}/password",
            headers=user_headers,
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123",
            },
        )
        
        assert response.status_code == 400
    
    def test_delete_user(self, client: TestClient, admin_headers, test_normal_user):
        """測試刪除使用者"""
        response = client.delete(
            f"/api/users/{test_normal_user.id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        
        # 驗證使用者已被刪除
        get_response = client.get(
            f"/api/users/{test_normal_user.id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404
    
    def test_get_user_stats(self, client: TestClient, admin_headers):
        """測試使用者統計"""
        response = client.get("/api/users/stats/summary", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "users_by_role" in data
        assert "users_by_department" in data
