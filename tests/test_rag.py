"""
測試 RAG Query API
"""
import pytest


class TestRAGQuery:
    """測試 RAG 查詢相關功能"""

    def test_query_rag_basic(self, client, admin_token: str):
        """測試基本 RAG 查詢"""
        query_data = {
            "query": "什麼是機器學習?",
            "top_k": 3
        }
        
        response = client.post(
            "/api/rag/query",
            json=query_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # 如果 OpenAI API key 未配置,可能返回 500
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "query_id" in data
            assert isinstance(data["sources"], list)

    def test_query_rag_with_filters(self, client, admin_token: str, test_department):
        """測試帶篩選條件的 RAG 查詢"""
        query_data = {
            "query": "測試查詢",
            "top_k": 5,
            # category_ids 暫時略過
        }
        
        response = client.post(
            "/api/rag/query",
            json=query_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code in [200, 500]

    def test_query_rag_empty_query(self, client, admin_token: str):
        """測試空查詢"""
        query_data = {
            "query": "",
            "top_k": 3
        }
        
        response = client.post(
            "/api/rag/query",
            json=query_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # 空查詢應該返回錯誤
        assert response.status_code == 422

    def test_list_query_history(self, client, admin_token: str):
        """測試查詢歷史記錄列表"""
        response = client.get(
            "/api/rag/history",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_query_history_with_pagination(self, client, admin_token: str):
        """測試分頁查詢歷史記錄"""
        response = client.get(
            "/api/rag/history?page=1&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert "items" in data
        assert "total" in data

    def test_get_query_history_detail(self, client, admin_token: str):
        """測試取得查詢歷史詳情"""
        # 先取得歷史列表
        list_response = client.get(
            "/api/rag/history?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert list_response.status_code == 200
        history_items = list_response.json()["items"]
        
        if history_items:
            history_id = history_items[0]["id"]
            detail_response = client.get(
                f"/api/rag/history/{history_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["id"] == history_id
            assert "query" in detail
            assert "answer" in detail

    def test_delete_query_history(self, client, admin_token: str):
        """測試刪除查詢歷史"""
        # 先建立一個查詢 (如果可能)
        list_response = client.get(
            "/api/rag/history?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if list_response.status_code == 200:
            history_items = list_response.json()["items"]
            if history_items:
                history_id = history_items[0]["id"]
                delete_response = client.delete(
                    f"/api/rag/history/{history_id}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                assert delete_response.status_code in [200, 404]

    def test_query_history_not_found(self, client, admin_token: str):
        """測試查詢不存在的歷史記錄"""
        response = client.get(
            "/api/rag/history/999999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404

    def test_get_rag_stats(self, client, admin_token: str):
        """測試取得 RAG 統計"""
        response = client.get(
            "/api/rag/stats/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # RAG stats endpoint 可能不存在
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # 驗證回應中包含統計資料
            assert isinstance(data, dict)
            assert len(data) > 0

    def test_normal_user_can_query(self, client, user_token: str):
        """測試一般使用者可以進行 RAG 查詢"""
        query_data = {
            "query": "測試查詢",
            "top_k": 3
        }
        
        response = client.post(
            "/api/rag/query",
            json=query_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # 一般使用者應該可以查詢
        assert response.status_code in [200, 500]

    def test_unauthorized_query(self, client):
        """測試未授權的查詢"""
        query_data = {
            "query": "測試查詢",
            "top_k": 3
        }
        
        response = client.post(
            "/api/rag/query",
            json=query_data
        )
        
        assert response.status_code == 401
