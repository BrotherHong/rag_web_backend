"""檔案儲存服務 (File Storage Service)"""

import os
import uuid
import aiofiles
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.system_settings import system_settings_service


class FileStorageService:
    """檔案儲存服務"""

    def __init__(self):
        """初始化檔案儲存服務"""
        self.base_path = Path(settings.UPLOAD_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_department_path(self, department_id: int, subdirectory: str = "unprocessed") -> Path:
        """取得處室的檔案儲存路徑
        
        Args:
            department_id: 處室 ID
            subdirectory: 子目錄名稱 (unprocessed 或 processed)
        """
        dept_path = self.base_path / str(department_id) / subdirectory
        dept_path.mkdir(parents=True, exist_ok=True)
        return dept_path
    
    def _get_processed_path(self, department_id: int, process_type: str) -> Path:
        """取得處理後檔案的路徑
        
        Args:
            department_id: 處室 ID
            process_type: 處理類型 (data, output_md, summaries, embeddings)
        """
        processed_path = self.base_path / str(department_id) / "processed" / process_type
        processed_path.mkdir(parents=True, exist_ok=True)
        return processed_path

    def generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一檔名
        
        格式: 原檔名 (如果重複則加上時間戳記)
        例如: 人事規章.pdf 或 人事規章_20251113_143000.pdf
        """
        # 分離檔名和副檔名
        name, ext = os.path.splitext(original_filename)
        
        # 清理檔名中的特殊字元
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        
        # 基本檔名
        base_filename = f"{safe_name}{ext}"
        
        # 如果檔案已存在，加上時間戳記
        # 這個檢查會在 save_upload_file 中進行
        return base_filename

    async def save_upload_file(
        self,
        upload_file: UploadFile,
        department_id: int
    ) -> tuple[str, str, int]:
        """儲存上傳的檔案到 unprocessed 目錄
        
        Args:
            upload_file: FastAPI UploadFile 物件
            department_id: 處室 ID
            
        Returns:
            tuple: (unique_filename, file_path, file_size)
        """
        # 生成檔名
        unique_filename = self.generate_unique_filename(upload_file.filename)
        
        # 取得 unprocessed 儲存路徑
        dept_path = self._get_department_path(department_id, "unprocessed")
        file_path = dept_path / unique_filename
        
        # 如果檔案已存在，加上時間戳記避免衝突
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(unique_filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            file_path = dept_path / unique_filename
        
        # 儲存檔案
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            # 分塊讀取和寫入，避免記憶體溢出
            chunk_size = 1024 * 1024  # 1MB
            while chunk := await upload_file.read(chunk_size):
                await f.write(chunk)
                file_size += len(chunk)
        
        return unique_filename, str(file_path), file_size
    
    def move_to_processed(
        self,
        source_path: str,
        department_id: int,
        process_type: str = "data"
    ) -> str:
        """將檔案從 unprocessed 移動到 processed 目錄
        
        Args:
            source_path: 來源檔案路徑
            department_id: 處室 ID
            process_type: 處理類型 (data, output_md, summaries, embeddings)
            
        Returns:
            str: 新的檔案路徑
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"來源檔案不存在: {source_path}")
        
        # 取得目標路徑
        target_dir = self._get_processed_path(department_id, process_type)
        target_path = target_dir / source.name
        
        # 移動檔案
        shutil.move(str(source), str(target_path))
        
        return str(target_path)

    def delete_file(self, file_path: str) -> bool:
        """刪除檔案
        
        Args:
            file_path: 檔案完整路徑
            
        Returns:
            bool: 是否刪除成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"刪除檔案失敗: {file_path}, 錯誤: {str(e)}")
            return False

    def get_file_size(self, file_path: str) -> int:
        """取得檔案大小（bytes）"""
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0

    async def validate_file(
        self, 
        upload_file: UploadFile,
        db: AsyncSession
    ) -> tuple[bool, Optional[str]]:
        """驗證檔案
        
        Args:
            upload_file: 上傳的檔案
            db: 資料庫 session
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # 從資料庫取得檔案大小限制
        max_file_size = await system_settings_service.get_max_file_size(db)
        
        # 檢查檔案大小
        if hasattr(upload_file, 'size') and upload_file.size:
            if upload_file.size > max_file_size:
                return False, f"檔案大小超過限制 ({max_file_size / (1024**2):.0f} MB)"
        
        # 從資料庫取得允許的檔案類型
        allowed_exts = await system_settings_service.get_allowed_file_types(db)
        
        # 檢查檔案類型
        ext = os.path.splitext(upload_file.filename)[1].lower()
        if ext not in allowed_exts:
            return False, f"不支援的檔案格式: {ext}，允許的格式: {', '.join(allowed_exts)}"
        
        return True, None

    def get_file_info(self, file_path: str) -> dict:
        """取得檔案資訊"""
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "exists": True
        }

    def get_storage_stats(self, department_id: Optional[int] = None) -> dict:
        """取得儲存空間統計
        
        Args:
            department_id: 處室 ID（可選，None 表示所有處室）
            
        Returns:
            dict: 儲存統計資訊
        """
        if department_id:
            path = self._get_department_path(department_id)
        else:
            path = self.base_path
        
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1
        
        return {
            "total_size": total_size,
            "file_count": file_count,
            "total_size_mb": round(total_size / (1024**2), 2),
            "total_size_gb": round(total_size / (1024**3), 2)
        }


# 建立全域檔案儲存服務實例
file_storage = FileStorageService()
