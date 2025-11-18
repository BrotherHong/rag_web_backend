"""
處室管理測試
測試處室 CRUD、統計等功能
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
@pytest.mark.integration
class TestDepartmentManagement:
    """處室管理測試類"""
    
    def test_list_departments(self, client: TestClient, admin_headers):
        """測試列出處室"""
        response = client.get("/api/departments", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0
    
    def test_list_departments_with_search(self, client: TestClient, admin_headers):
        """測試搜尋處室"""
        response = client.get(
            "/api/departments?search=測試",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        for dept in data["items"]:
            assert "測試" in dept["name"] or "測試" in (dept["description"] or "")
    
    def test_get_department(self, client: TestClient, admin_headers, test_department):
        """測試獲取處室詳情"""
        response = client.get(
            f"/api/departments/{test_department.id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_department.id
        assert data["name"] == "測試處室"
    
    def test_create_department(self, client: TestClient, admin_headers):
        """測試創建處室"""
        response = client.post(
            "/api/departments",
            headers=admin_headers,
            json={
                "name": "新處室",
                "description": "這是新創建的處室",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新處室"
        assert data["description"] == "這是新創建的處室"
    
    def test_create_department_duplicate_name(self, client: TestClient, admin_headers, test_department):
        """測試創建重複名稱的處室"""
        response = client.post(
            "/api/departments",
            headers=admin_headers,
            json={
                "name": "測試處室",  # 已存在
                "description": "另一個描述",
            },
        )
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_update_department(self, client: TestClient, admin_headers, test_department):
        """測試更新處室"""
        response = client.put(
            f"/api/departments/{test_department.id}",
            headers=admin_headers,
            json={
                "name": "更新後的處室",
                "description": "更新後的描述",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後的處室"
        assert data["description"] == "更新後的描述"
    
    def test_delete_department(self, client: TestClient, admin_headers):
        """測試刪除處室"""
        # 先創建一個沒有關聯的處室
        create_response = client.post(
            "/api/departments",
            headers=admin_headers,
            json={
                "name": "待刪除處室",
                "description": "將被刪除",
            },
        )
        dept_id = create_response.json()["id"]
        
        # 刪除處室
        response = client.delete(
            f"/api/departments/{dept_id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        
        # 驗證已被刪除
        get_response = client.get(
            f"/api/departments/{dept_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404
    
    def test_delete_department_with_users(self, client: TestClient, admin_headers, test_department):
        """測試刪除有使用者的處室（應該失敗）"""
        response = client.delete(
            f"/api/departments/{test_department.id}",
            headers=admin_headers,
        )
        
        assert response.status_code == 400
        assert "使用者" in response.json()["detail"]
    
    def test_get_department_stats(self, client: TestClient, admin_headers, test_department):
        """測試處室統計"""
        response = client.get(
            f"/api/departments/{test_department.id}/stats",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_count" in data
        assert "file_count" in data
        assert "total_file_size" in data
        assert "activity_count" in data
        assert data["user_count"] >= 0
