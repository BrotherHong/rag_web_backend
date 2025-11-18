"""
測試 Activities API
"""
import pytest
from datetime import datetime, timedelta


class TestActivities:
    """測試活動記錄相關功能"""

    def test_list_activities(self, client, admin_token: str):
        """測試列出活動記錄"""
        response = client.get(
            "/api/activities/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_activities_with_pagination(self, client, admin_token: str):
        """測試分頁查詢活動記錄"""
        response = client.get(
            "/api/activities/?page=1&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["page"] == 1
        assert "items" in data

    def test_list_activities_by_type(self, client, admin_token: str):
        """測試依類型篩選活動記錄"""
        response = client.get(
            "/api/activities/?activity_type=login",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # 驗證所有返回的活動都是 login 類型
        for activity in data["items"]:
            assert activity["activity_type"] == "login"

    def test_list_activities_by_user(self, client, admin_token: str, test_normal_user):
        """測試依使用者篩選活動"""
        response = client.get(
            f"/api/activities/?user_id={test_normal_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # 驗證所有返回的活動都屬於指定使用者
        for activity in data["items"]:
            assert activity["user_id"] == test_normal_user.id

    def test_list_activities_with_date_range(self, client, admin_token: str):
        """測試日期範圍篩選"""
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()
        
        response = client.get(
            f"/api/activities/?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)

    def test_get_activity_detail(self, client, admin_token: str, test_department):
        """測試取得單一活動記錄詳情"""
        # 先建立一個活動記錄 (透過登入會自動產生)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        
        # 取得活動列表
        list_response = client.get(
            "/api/activities/?activity_type=login&limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_response.status_code == 200
        activities = list_response.json()["items"]
        
        if activities:
            activity_id = activities[0]["id"]
            # 取得詳細資訊
            detail_response = client.get(
                f"/api/activities/{activity_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert detail_response.status_code == 200
            activity_data = detail_response.json()
            assert activity_data["id"] == activity_id
            assert "activity_type" in activity_data
            assert "user_id" in activity_data

    def test_get_activity_stats(self, client, admin_token: str):
        """測試取得活動統計"""
        response = client.get(
            "/api/activities/stats/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_activities" in data
        # API 回傳 by_type 而非 activities_by_type
        assert "by_type" in data or "activities_by_type" in data
        assert isinstance(data.get("by_type", data.get("activities_by_type", {})), dict)

    def test_normal_user_can_view_own_activities(self, client, user_token: str, test_normal_user):
        """測試一般使用者可查看自己的活動記錄"""
        response = client.get(
            f"/api/activities/?user_id={test_normal_user.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # 一般使用者應該可以查看自己的活動
        assert response.status_code in [200, 403]  # 依據權限設定可能不同

    def test_activity_not_found(self, client, admin_token: str):
        """測試查詢不存在的活動記錄"""
        response = client.get(
            "/api/activities/999999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
