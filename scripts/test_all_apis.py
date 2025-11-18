"""全面測試所有已實作的 API 端點"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
token = None

async def test_auth_apis():
    """測試認證相關 API"""
    global token
    print("\n" + "="*60)
    print("【認證模組測試】")
    print("="*60)
    
    # 1. 登入
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True) as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ 登入成功")
        else:
            print(f"❌ 登入失敗: {response.status_code}")
            return False
    
    # 2. 取得當前使用者資訊
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        response = await client.get("/api/auth/me")
        if response.status_code == 200:
            user = response.json()
            print(f"✅ 取得使用者資訊: {user.get('username')}")
        else:
            print(f"❌ 取得使用者資訊失敗: {response.status_code}")
    
    return True


async def test_user_apis():
    """測試使用者管理 API"""
    print("\n" + "="*60)
    print("【使用者管理測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得使用者列表
        response = await client.get("/api/users")
        if response.status_code == 200:
            users = response.json()["items"]
            print(f"✅ 使用者列表: {len(users)} 位使用者")
        else:
            print(f"❌ 使用者列表失敗: {response.status_code}")
        
        # 2. 取得單一使用者
        if users:
            user_id = users[0]["id"]
            response = await client.get(f"/api/users/{user_id}")
            if response.status_code == 200:
                print(f"✅ 取得使用者詳情: {response.json()['username']}")
            else:
                print(f"❌ 取得使用者詳情失敗: {response.status_code}")


async def test_category_apis():
    """測試分類管理 API"""
    print("\n" + "="*60)
    print("【分類管理測試】")
    print("="*60)
    
    category_id = None
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得分類列表
        response = await client.get("/api/categories")
        if response.status_code == 200:
            categories = response.json()["items"]
            print(f"✅ 分類列表: {len(categories)} 個分類")
            if categories:
                category_id = categories[0]["id"]
        else:
            print(f"❌ 分類列表失敗: {response.status_code}")
        
        # 2. 取得單一分類
        if category_id:
            response = await client.get(f"/api/categories/{category_id}")
            if response.status_code == 200:
                print(f"✅ 取得分類詳情: {response.json()['name']}")
            else:
                print(f"❌ 取得分類詳情失敗: {response.status_code}")
        
        # 3. 建立新分類
        test_category_name = f"測試分類_{datetime.now().strftime('%H%M%S')}"
        response = await client.post(
            "/api/categories",
            json={"name": test_category_name, "color": "red"}
        )
        if response.status_code == 201:
            new_category = response.json()
            new_category_id = new_category["id"]
            print(f"✅ 建立分類成功: {new_category['name']}")
            
            # 4. 更新分類
            response = await client.put(
                f"/api/categories/{new_category_id}",
                json={"name": f"{test_category_name}_updated", "color": "green"}
            )
            if response.status_code == 200:
                print(f"✅ 更新分類成功")
            else:
                print(f"❌ 更新分類失敗: {response.status_code}")
            
            # 5. 刪除分類
            response = await client.delete(f"/api/categories/{new_category_id}")
            if response.status_code == 200:
                print(f"✅ 刪除分類成功")
            else:
                print(f"❌ 刪除分類失敗: {response.status_code}")
        else:
            print(f"❌ 建立分類失敗: {response.status_code}")
        
        # 6. 分類統計
        response = await client.get("/api/categories/stats")
        if response.status_code == 200:
            stats = response.json()["stats"]
            print(f"✅ 分類統計: {len(stats)} 個分類的統計資料")
        else:
            print(f"❌ 分類統計失敗: {response.status_code}")


async def test_file_apis():
    """測試檔案管理 API"""
    print("\n" + "="*60)
    print("【檔案管理測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得檔案列表
        response = await client.get("/api/files")
        if response.status_code == 200:
            files = response.json()["items"]
            print(f"✅ 檔案列表: {len(files)} 個檔案")
            
            # 2. 取得單一檔案詳情
            if files:
                file_id = files[0]["id"]
                response = await client.get(f"/api/files/{file_id}")
                if response.status_code == 200:
                    print(f"✅ 取得檔案詳情: {response.json()['filename']}")
                else:
                    print(f"❌ 取得檔案詳情失敗: {response.status_code}")
        else:
            print(f"❌ 檔案列表失敗: {response.status_code}")
        
        # 3. 檔案統計
        response = await client.get("/api/files/statistics")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 檔案統計: 總共 {stats['total_files']} 個檔案")
        else:
            print(f"❌ 檔案統計失敗: {response.status_code}")


async def test_department_apis():
    """測試處室管理 API"""
    print("\n" + "="*60)
    print("【處室管理測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得處室列表
        response = await client.get("/api/departments")
        if response.status_code == 200:
            departments = response.json()["items"]
            print(f"✅ 處室列表: {len(departments)} 個處室")
            
            # 2. 取得單一處室詳情
            if departments:
                dept_id = departments[0]["id"]
                response = await client.get(f"/api/departments/{dept_id}")
                if response.status_code == 200:
                    print(f"✅ 取得處室詳情: {response.json()['name']}")
                else:
                    print(f"❌ 取得處室詳情失敗: {response.status_code}")
        else:
            print(f"❌ 處室列表失敗: {response.status_code}")


async def test_activity_apis():
    """測試活動記錄 API"""
    print("\n" + "="*60)
    print("【活動記錄測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得活動記錄
        response = await client.get("/api/activities")
        if response.status_code == 200:
            activities = response.json()["items"]
            print(f"✅ 活動記錄: {len(activities)} 條記錄")
            if activities:
                print(f"   最新活動: {activities[0].get('description', 'N/A')}")
        else:
            print(f"❌ 活動記錄失敗: {response.status_code}")


async def test_rag_apis():
    """測試 RAG 查詢 API"""
    print("\n" + "="*60)
    print("【RAG 查詢測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,
        timeout=30.0
    ) as client:
        # 1. RAG 查詢
        response = await client.post(
            "/api/rag/query",
            json={"query": "測試查詢", "top_k": 5}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ RAG 查詢成功")
        else:
            print(f"❌ RAG 查詢失敗: {response.status_code}")
        
        # 2. 查詢歷史
        response = await client.get("/api/rag/history")
        if response.status_code == 200:
            history = response.json()["items"]
            print(f"✅ 查詢歷史: {len(history)} 條記錄")
        else:
            print(f"❌ 查詢歷史失敗: {response.status_code}")


async def test_settings_apis():
    """測試系統設定 API"""
    print("\n" + "="*60)
    print("【系統設定測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        # 1. 取得所有設定
        response = await client.get("/api/settings")
        if response.status_code == 200:
            settings = response.json()["items"]
            print(f"✅ 系統設定: {len(settings)} 個設定項目")
        else:
            print(f"❌ 系統設定失敗: {response.status_code}")


async def test_logout():
    """測試登出"""
    print("\n" + "="*60)
    print("【登出測試】")
    print("="*60)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True
    ) as client:
        response = await client.post("/api/auth/logout")
        if response.status_code == 200:
            print(f"✅ 登出成功")
        else:
            print(f"❌ 登出失敗: {response.status_code}")


async def main():
    """執行所有測試"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "全面 API 功能測試" + " "*26 + "║")
    print("╚" + "="*58 + "╝")
    
    # 執行測試
    if await test_auth_apis():
        await test_user_apis()
        await test_category_apis()
        await test_file_apis()
        await test_department_apis()
        await test_activity_apis()
        await test_rag_apis()
        await test_settings_apis()
        await test_logout()
    
    print("\n" + "="*60)
    print("【測試完成】")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
