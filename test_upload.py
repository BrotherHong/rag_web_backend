import requests
import sys

# 測試上傳並觸發處理
url = "http://localhost:8000/api/upload/batch"

# 先登入獲取 token（需要替換為實際的帳號密碼）
print("請提供測試用的帳號密碼進行測試...")
print("或者直接使用現有的 token")

# 如果你有 token，可以直接使用
token = input("請輸入 Bearer Token (或按 Enter 跳過): ").strip()

if token:
    headers = {"Authorization": f"Bearer {token}"}
    
    # 測試檔案
    test_file_path = "test_upload.txt"
    with open(test_file_path, "w") as f:
        f.write("這是一個測試檔案，用於驗證處理流程。")
    
    with open(test_file_path, "rb") as f:
        files = {"files": ("test.txt", f, "text/plain")}
        data = {
            "categories": "{}",
            "removeFileIds": "[]",
            "startProcessing": "true"  # 關鍵參數！
        }
        
        print("\n發送上傳請求...")
        response = requests.post(url, headers=headers, files=files, data=data)
        
        print(f"\n狀態碼: {response.status_code}")
        print(f"回應: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("taskId")
            print(f"\n✅ 上傳成功！任務 ID: {task_id}")
            print("檢查後端日誌確認是否觸發處理...")
else:
    print("跳過測試")

