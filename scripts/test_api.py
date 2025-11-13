"""
API 測試腳本
用於測試所有 API 端點是否正常運作
"""
import httpx
import asyncio
from datetime import datetime


BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"


async def test_health():
    """測試健康檢查端點"""
    print("\n=== 測試健康檢查 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/health")
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.json()}")
        return response.status_code == 200


async def test_login():
    """測試登入功能"""
    print("\n=== 測試登入 ===")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={
                "email": "admin@example.com",
                "password": "admin123"
            }
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"取得 Token: {data['access_token'][:20]}...")
            return data['access_token']
        else:
            print(f"錯誤: {response.text}")
            return None


async def test_get_current_user(token: str):
    """測試獲取當前用戶資訊"""
    print("\n=== 測試獲取當前用戶 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"用戶: {data['username']} ({data['email']})")
            print(f"角色: {data['role']}")
            print(f"部門: {data['department']['name']}")
            return True
        else:
            print(f"錯誤: {response.text}")
            return False


async def test_list_departments():
    """測試列出所有部門（公開端點）"""
    print("\n=== 測試列出部門 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/departments/")
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"找到 {len(data)} 個部門:")
            for dept in data:
                print(f"  - {dept['name']} ({dept['code']})")
            return True
        else:
            print(f"錯誤: {response.text}")
            return False


async def test_list_users(token: str):
    """測試列出所有用戶（需要認證）"""
    print("\n=== 測試列出用戶 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"找到 {len(data)} 個用戶:")
            for user in data:
                print(f"  - {user['username']} ({user['email']}) - {user['role']}")
            return True
        else:
            print(f"錯誤: {response.text}")
            return False


async def test_create_user(token: str):
    """測試創建新用戶（需要管理員權限）"""
    print("\n=== 測試創建用戶 ===")
    async with httpx.AsyncClient() as client:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/users/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": f"testuser_{timestamp}",
                "email": f"test_{timestamp}@example.com",
                "password": "Test123456",
                "full_name": "測試用戶",
                "role": "USER",
                "department_id": 1
            }
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"成功創建用戶: {data['username']} (ID: {data['id']})")
            return data['id']
        else:
            print(f"錯誤: {response.text}")
            return None


async def test_unauthorized_access():
    """測試未授權訪問"""
    print("\n=== 測試未授權訪問 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/auth/me")
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 401:
            print("✓ 正確拒絕未授權訪問")
            return True
        else:
            print("✗ 應該返回 401 狀態碼")
            return False


async def main():
    """執行所有測試"""
    print("=" * 60)
    print("開始 API 測試")
    print("=" * 60)
    
    results = {}
    
    # 測試 1: 健康檢查
    results['health'] = await test_health()
    
    # 測試 2: 未授權訪問
    results['unauthorized'] = await test_unauthorized_access()
    
    # 測試 3: 登入
    token = await test_login()
    results['login'] = token is not None
    
    if not token:
        print("\n❌ 登入失敗，無法繼續後續測試")
        return
    
    # 測試 4: 獲取當前用戶
    results['current_user'] = await test_get_current_user(token)
    
    # 測試 5: 列出部門
    results['list_departments'] = await test_list_departments()
    
    # 測試 6: 列出用戶
    results['list_users'] = await test_list_users(token)
    
    # 測試 7: 創建用戶
    new_user_id = await test_create_user(token)
    results['create_user'] = new_user_id is not None
    
    # 顯示測試結果
    print("\n" + "=" * 60)
    print("測試結果摘要")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ 通過" if passed_test else "✗ 失敗"
        print(f"{test_name:20s} {status}")
    
    print("-" * 60)
    print(f"總計: {passed}/{total} 個測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過!")
    else:
        print(f"\n⚠️  有 {total - passed} 個測試失敗")


if __name__ == "__main__":
    asyncio.run(main())
