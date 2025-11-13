"""測試檔案上傳與管理 API

測試項目:
1. 檔案上傳
2. 檔案列表查詢
3. 檔案詳情查詢
4. 檔案更新
5. 檔案下載
6. 檔案刪除
7. 分類管理
"""

import requests
import json
import os
from pathlib import Path

# API 基礎 URL
BASE_URL = "http://localhost:8000/api"

# 測試使用者帳號
TEST_USER = {
    "username": "admin",
    "password": "admin123"
}

# 顏色輸出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


class FileAPITester:
    """檔案 API 測試器"""
    
    def __init__(self):
        self.token = None
        self.headers = {}
        self.test_file_id = None
        self.test_category_id = None
        
    def login(self):
        """登入並取得 Token"""
        print_info("測試 1: 使用者登入")
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json=TEST_USER
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print_success(f"登入成功，Token: {self.token[:20]}...")
                return True
            else:
                print_error(f"登入失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"登入錯誤: {str(e)}")
            return False
    
    def test_create_category(self):
        """測試建立分類"""
        print_info("\n測試 2: 建立測試分類")
        
        try:
            response = requests.post(
                f"{BASE_URL}/categories",
                headers=self.headers,
                json={
                    "name": "測試文件",
                    "color": "purple"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                self.test_category_id = data["id"]
                print_success(f"建立分類成功，ID: {self.test_category_id}, 名稱: {data['name']}")
                return True
            elif response.status_code == 400 and "已存在" in response.text:
                print_warning("分類已存在，嘗試使用現有分類")
                # 取得現有分類
                categories = self.get_categories()
                if categories:
                    self.test_category_id = categories[0]["id"]
                    print_info(f"使用現有分類 ID: {self.test_category_id}")
                    return True
            else:
                print_error(f"建立分類失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"建立分類錯誤: {str(e)}")
            return False
    
    def get_categories(self):
        """取得分類列表"""
        try:
            response = requests.get(
                f"{BASE_URL}/categories",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            return []
        except:
            return []
    
    def test_upload_file(self):
        """測試檔案上傳"""
        print_info("\n測試 3: 上傳測試檔案")
        
        # 建立測試檔案
        test_file_path = "test_upload.txt"
        test_content = "這是一個測試檔案\n用於測試檔案上傳功能\nRAG Knowledge Base System"
        
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        try:
            with open(test_file_path, "rb") as f:
                files = {"file": ("測試文件.txt", f, "text/plain")}
                data = {
                    "category_id": str(self.test_category_id) if self.test_category_id else "",
                    "description": "這是一個測試上傳的檔案"
                }
                
                response = requests.post(
                    f"{BASE_URL}/files/upload",
                    headers=self.headers,
                    files=files,
                    data=data
                )
            
            # 刪除測試檔案
            os.remove(test_file_path)
            
            if response.status_code == 201:
                data = response.json()
                self.test_file_id = data["id"]
                print_success(f"上傳檔案成功")
                print_info(f"  檔案 ID: {data['id']}")
                print_info(f"  檔案名稱: {data['original_filename']}")
                print_info(f"  檔案大小: {data['file_size']} bytes")
                print_info(f"  狀態: {data['status']}")
                return True
            else:
                print_error(f"上傳檔案失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"上傳檔案錯誤: {str(e)}")
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            return False
    
    def test_get_files(self):
        """測試取得檔案列表"""
        print_info("\n測試 4: 取得檔案列表")
        
        try:
            response = requests.get(
                f"{BASE_URL}/files",
                headers=self.headers,
                params={"page": 1, "limit": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"取得檔案列表成功")
                print_info(f"  總檔案數: {data['total']}")
                print_info(f"  當前頁: {data['page']}/{data['pages']}")
                print_info(f"  本頁檔案數: {len(data['items'])}")
                
                if data['items']:
                    print_info(f"\n  最近的檔案:")
                    for file in data['items'][:3]:
                        print(f"    - {file['original_filename']} ({file['file_size']} bytes)")
                
                return True
            else:
                print_error(f"取得檔案列表失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"取得檔案列表錯誤: {str(e)}")
            return False
    
    def test_get_file_detail(self):
        """測試取得檔案詳情"""
        print_info("\n測試 5: 取得檔案詳情")
        
        if not self.test_file_id:
            print_warning("沒有測試檔案 ID，跳過此測試")
            return True
        
        try:
            response = requests.get(
                f"{BASE_URL}/files/{self.test_file_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"取得檔案詳情成功")
                print_info(f"  檔案 ID: {data['id']}")
                print_info(f"  原始檔名: {data['original_filename']}")
                print_info(f"  檔案大小: {data['file_size']} bytes")
                print_info(f"  檔案類型: {data['file_type']}")
                print_info(f"  上傳者: {data['uploader']['full_name']}")
                print_info(f"  狀態: {data['status']}")
                print_info(f"  下載次數: {data['download_count']}")
                
                if data.get('category'):
                    print_info(f"  分類: {data['category']['name']} ({data['category']['color']})")
                
                return True
            else:
                print_error(f"取得檔案詳情失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"取得檔案詳情錯誤: {str(e)}")
            return False
    
    def test_processing_status(self):
        """測試取得處理狀態"""
        print_info("\n測試 6: 取得檔案處理狀態")
        
        if not self.test_file_id:
            print_warning("沒有測試檔案 ID，跳過此測試")
            return True
        
        try:
            response = requests.get(
                f"{BASE_URL}/files/{self.test_file_id}/processing-status",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("取得處理狀態成功")
                print_info(f"  狀態: {data.get('status')}")
                print_info(f"  處理步驟: {data.get('processing_step')}")
                print_info(f"  處理進度: {data.get('processing_progress')}%")
                
                if data.get('chunk_count'):
                    print_info(f"  文本區塊數: {data['chunk_count']}")
                if data.get('vector_count'):
                    print_info(f"  向量數量: {data['vector_count']}")
                if data.get('processing_duration_seconds'):
                    print_info(f"  處理時間: {data['processing_duration_seconds']:.2f} 秒")
                
                return True
            else:
                print_error(f"取得處理狀態失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"取得處理狀態錯誤: {str(e)}")
            return False
    
    def test_batch_upload(self):
        """測試批次上傳檔案"""
        print_info("\n測試 7: 批次上傳檔案")
        
        try:
            # 準備測試檔案
            test_files = []
            temp_files = []
            
            for i in range(3):
                temp_file = Path(f"temp_test_file_{i+1}.txt")
                temp_file.write_text(f"這是測試檔案 {i+1} 的內容\n批次上傳測試")
                temp_files.append(temp_file)
                test_files.append(
                    ('files', (temp_file.name, open(temp_file, 'rb'), 'text/plain'))
                )
            
            data = {}
            if self.test_category_id:
                data['category_id'] = str(self.test_category_id)
            data['description'] = "批次上傳的測試檔案"
            
            response = requests.post(
                f"{BASE_URL}/files/batch-upload",
                headers=self.headers,
                files=test_files,
                data=data
            )
            
            # 清理臨時檔案
            for f in temp_files:
                f.unlink()
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"批次上傳成功: {data.get('success')} 個檔案")
                print_info(f"  總共: {data.get('total')}")
                print_info(f"  成功: {data.get('success')}")
                print_info(f"  失敗: {data.get('failed')}")
                
                # 顯示每個檔案的結果
                for result in data.get('results', []):
                    status_icon = "✓" if result['success'] else "✗"
                    print_info(f"  {status_icon} {result['filename']}")
                
                return True
            else:
                print_error(f"批次上傳失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"批次上傳錯誤: {str(e)}")
            return False
    
    def test_update_file(self):
        """測試更新檔案資訊"""
        print_info("\n測試 8: 更新檔案資訊")
        
        if not self.test_file_id:
            print_warning("沒有測試檔案 ID，跳過此測試")
            return True
        
        try:
            response = requests.put(
                f"{BASE_URL}/files/{self.test_file_id}",
                headers=self.headers,
                json={
                    "description": "更新後的描述：這是一個測試檔案",
                    "tags": ["測試", "範例", "檔案上傳"]
                }
            )
            
            if response.status_code == 200:
                print_success("更新檔案資訊成功")
                return True
            else:
                print_error(f"更新檔案資訊失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"更新檔案資訊錯誤: {str(e)}")
            return False
    
    def test_download_file(self):
        """測試下載檔案"""
        print_info("\n測試 9: 下載檔案")
        
        if not self.test_file_id:
            print_warning("沒有測試檔案 ID，跳過此測試")
            return True
        
        try:
            response = requests.get(
                f"{BASE_URL}/files/{self.test_file_id}/download",
                headers=self.headers
            )
            
            if response.status_code == 200:
                print_success("下載檔案成功")
                print_info(f"  檔案大小: {len(response.content)} bytes")
                print_info(f"  Content-Type: {response.headers.get('content-type')}")
                return True
            else:
                print_error(f"下載檔案失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"下載檔案錯誤: {str(e)}")
            return False
    
    def test_file_stats(self):
        """測試取得檔案統計"""
        print_info("\n測試 10: 取得檔案統計")
        
        try:
            response = requests.get(
                f"{BASE_URL}/files/stats",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("取得檔案統計成功")
                print_info(f"  總檔案數: {data['total_files']}")
                print_info(f"  總大小: {data['total_size']} bytes ({data['total_size'] / 1024:.2f} KB)")
                
                if data.get('by_status'):
                    print_info(f"  狀態分佈: {data['by_status']}")
                
                if data.get('by_type'):
                    print_info(f"  類型分佈: {data['by_type']}")
                
                return True
            else:
                print_error(f"取得檔案統計失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"取得檔案統計錯誤: {str(e)}")
            return False
    
    def test_delete_file(self):
        """測試刪除檔案"""
        print_info("\n測試 11: 刪除檔案")
        
        if not self.test_file_id:
            print_warning("沒有測試檔案 ID，跳過此測試")
            return True
        
        try:
            response = requests.delete(
                f"{BASE_URL}/files/{self.test_file_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                print_success("刪除檔案成功")
                return True
            else:
                print_error(f"刪除檔案失敗: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"刪除檔案錯誤: {str(e)}")
            return False
    
    def run_all_tests(self):
        """執行所有測試"""
        print("=" * 70)
        print("開始測試檔案上傳與管理 API")
        print("=" * 70)
        
        results = []
        
        # 1. 登入
        results.append(("登入", self.login()))
        if not results[-1][1]:
            print_error("\n登入失敗，無法繼續測試")
            return
        
        # 2. 建立分類
        results.append(("建立分類", self.test_create_category()))
        
        # 3. 上傳檔案
        results.append(("上傳檔案", self.test_upload_file()))
        
        # 4. 取得檔案列表
        results.append(("取得檔案列表", self.test_get_files()))
        
        # 5. 取得檔案詳情
        results.append(("取得檔案詳情", self.test_get_file_detail()))
        
        # 6. 取得處理狀態
        results.append(("取得處理狀態", self.test_processing_status()))
        
        # 7. 批次上傳
        results.append(("批次上傳檔案", self.test_batch_upload()))
        
        # 8. 更新檔案
        results.append(("更新檔案", self.test_update_file()))
        
        # 9. 下載檔案
        results.append(("下載檔案", self.test_download_file()))
        
        # 10. 檔案統計
        results.append(("檔案統計", self.test_file_stats()))
        
        # 11. 刪除檔案
        results.append(("刪除檔案", self.test_delete_file()))
        
        # 顯示測試結果
        print("\n" + "=" * 70)
        print("測試結果總覽")
        print("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✓ 通過" if result else "✗ 失敗"
            color = Colors.GREEN if result else Colors.RED
            print(f"{color}{status}{Colors.END} - {name}")
        
        print("=" * 70)
        print(f"測試通過: {passed}/{total} ({passed/total*100:.1f}%)")
        print("=" * 70)


if __name__ == "__main__":
    tester = FileAPITester()
    tester.run_all_tests()
