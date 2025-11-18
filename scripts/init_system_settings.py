"""初始化系統設定"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import SystemSetting


async def init_system_settings():
    """初始化預設系統設定"""
    
    default_settings = [
        # 應用程式設定
        {
            "key": "app.max_file_size",
            "value": {"bytes": 52428800},  # 50MB
            "category": "app",
            "display_name": "最大檔案大小",
            "description": "單個檔案上傳的最大大小限制（bytes）",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "app.allowed_file_types",
            "value": {"types": [".pdf", ".docx", ".txt", ".doc", ".pptx", ".xlsx"]},
            "category": "app",
            "display_name": "允許的檔案類型",
            "description": "系統允許上傳的檔案格式",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "app.files_per_page",
            "value": {"count": 20},
            "category": "app",
            "display_name": "每頁檔案數",
            "description": "檔案列表每頁顯示的數量",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "app.maintenance_mode",
            "value": {"enabled": False},
            "category": "app",
            "display_name": "維護模式",
            "description": "啟用後系統將進入維護模式，一般使用者無法訪問",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "app.allow_registration",
            "value": {"enabled": False},
            "category": "app",
            "display_name": "開放註冊",
            "description": "是否允許新使用者自行註冊",
            "is_sensitive": False,
            "is_public": True,
        },
        
        # RAG 模型參數
        {
            "key": "rag.model_name",
            "value": {"name": "gpt-4"},
            "category": "rag",
            "display_name": "LLM 模型",
            "description": "使用的大型語言模型名稱",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.temperature",
            "value": {"value": 0.7},
            "category": "rag",
            "display_name": "溫度參數",
            "description": "控制回答的隨機性，0-2 之間，越高越隨機",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.max_tokens",
            "value": {"value": 2000},
            "category": "rag",
            "display_name": "最大 Token 數",
            "description": "生成回答的最大 token 數量",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.top_k",
            "value": {"value": 5},
            "category": "rag",
            "display_name": "檢索文檔數",
            "description": "向量搜尋時返回的最相關文檔數量",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.chunk_size",
            "value": {"value": 500},
            "category": "rag",
            "display_name": "文檔分塊大小",
            "description": "文檔分塊時每個塊的字元數",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.chunk_overlap",
            "value": {"value": 50},
            "category": "rag",
            "display_name": "分塊重疊大小",
            "description": "相鄰文檔塊之間的重疊字元數",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "rag.embedding_model",
            "value": {"name": "text-embedding-ada-002"},
            "category": "rag",
            "display_name": "嵌入模型",
            "description": "用於生成文檔向量的嵌入模型",
            "is_sensitive": False,
            "is_public": False,
        },
        
        # 安全設定
        {
            "key": "security.session_timeout",
            "value": {"seconds": 3600},  # 1 hour
            "category": "security",
            "display_name": "會話超時時間",
            "description": "使用者會話的超時時間（秒）",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "security.max_login_attempts",
            "value": {"count": 5},
            "category": "security",
            "display_name": "最大登入嘗試次數",
            "description": "帳號被鎖定前允許的最大登入失敗次數",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "security.password_min_length",
            "value": {"length": 6},
            "category": "security",
            "display_name": "密碼最小長度",
            "description": "使用者密碼的最小字元數",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "security.require_strong_password",
            "value": {"enabled": False},
            "category": "security",
            "display_name": "需要強密碼",
            "description": "是否要求密碼包含大小寫字母、數字和特殊字元",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "security.enable_2fa",
            "value": {"enabled": False},
            "category": "security",
            "display_name": "啟用雙因素認證",
            "description": "是否啟用雙因素認證功能",
            "is_sensitive": False,
            "is_public": True,
        },
        
        # 功能開關
        {
            "key": "feature.enable_file_upload",
            "value": {"enabled": True},
            "category": "feature",
            "display_name": "啟用檔案上傳",
            "description": "是否允許使用者上傳檔案",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "feature.enable_rag_query",
            "value": {"enabled": True},
            "category": "feature",
            "display_name": "啟用 RAG 查詢",
            "description": "是否啟用 RAG 知識庫查詢功能",
            "is_sensitive": False,
            "is_public": True,
        },
        {
            "key": "feature.enable_activity_log",
            "value": {"enabled": True},
            "category": "feature",
            "display_name": "啟用活動記錄",
            "description": "是否記錄使用者活動日誌",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "feature.enable_email_notification",
            "value": {"enabled": False},
            "category": "feature",
            "display_name": "啟用郵件通知",
            "description": "是否啟用郵件通知功能",
            "is_sensitive": False,
            "is_public": False,
        },
        {
            "key": "feature.enable_websocket",
            "value": {"enabled": False},
            "category": "feature",
            "display_name": "啟用 WebSocket",
            "description": "是否啟用 WebSocket 即時通訊功能",
            "is_sensitive": False,
            "is_public": True,
        },
    ]
    
    async with AsyncSessionLocal() as db:
        created_count = 0
        skipped_count = 0
        
        for setting_data in default_settings:
            # 檢查設定是否已存在
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == setting_data["key"])
            )
            existing_setting = result.scalar_one_or_none()
            
            if existing_setting:
                print(f"⏭️  跳過已存在的設定: {setting_data['key']}")
                skipped_count += 1
                continue
            
            # 建立新設定
            setting = SystemSetting(**setting_data)
            db.add(setting)
            created_count += 1
            print(f"✅ 建立設定: {setting_data['key']}")
        
        await db.commit()
        
        print(f"\n📊 設定初始化完成:")
        print(f"   ✅ 新建: {created_count} 個")
        print(f"   ⏭️  跳過: {skipped_count} 個")
        print(f"   📦 總計: {len(default_settings)} 個預設設定")


if __name__ == "__main__":
    print("=" * 60)
    print("初始化系統設定")
    print("=" * 60)
    asyncio.run(init_system_settings())
