"""檔案儲存服務 (File Storage Service)"""

import os
import uuid
import aiofiles
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional
from fastapi import UploadFile, HTTPException

from app.config import settings


class FileStorageService:
    """檔案儲存服務"""

    def __init__(self):
        """初始化檔案儲存服務"""
        self.base_path = Path(settings.UPLOAD_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_department_path(self, department_id: int) -> Path:
        """取得處室的檔案儲存路徑"""
        dept_path = self.base_path / str(department_id)
        dept_path.mkdir(parents=True, exist_ok=True)
        return dept_path

    def generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一檔名
        
        格式: YYYYMMDD_HHMMSS_uuid8_原檔名
        例如: 20251113_143000_a1b2c3d4_人事規章.pdf
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        
        # 分離檔名和副檔名
        name, ext = os.path.splitext(original_filename)
        
        # 清理檔名中的特殊字元
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        
        return f"{timestamp}_{unique_id}_{safe_name}{ext}"

    async def save_upload_file(
        self,
        upload_file: UploadFile,
        department_id: int
    ) -> tuple[str, str, int]:
        """儲存上傳的檔案
        
        Args:
            upload_file: FastAPI UploadFile 物件
            department_id: 處室 ID
            
        Returns:
            tuple: (unique_filename, file_path, file_size)
        """
        # 生成唯一檔名
        unique_filename = self.generate_unique_filename(upload_file.filename)
        
        # 取得儲存路徑
        dept_path = self._get_department_path(department_id)
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

    def validate_file(self, upload_file: UploadFile) -> tuple[bool, Optional[str]]:
        """驗證檔案
        
        Args:
            upload_file: 上傳的檔案
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # 檢查檔案大小
        if hasattr(upload_file, 'size') and upload_file.size:
            if upload_file.size > settings.MAX_FILE_SIZE:
                return False, f"檔案大小超過限制 ({settings.MAX_FILE_SIZE / (1024**2):.0f} MB)"
        
        # 檢查檔案類型
        ext = os.path.splitext(upload_file.filename)[1].lower()
        allowed_exts = settings.allowed_extensions_list
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
