"""應用程式配置管理"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 應用設定
    APP_NAME: str = "RAG Knowledge Base"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api"
    
    # 安全設定
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # 資料庫
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # Redis (可選)
    REDIS_URL: Optional[str] = None
    
    # 檔案上傳（預設值，實際使用資料庫系統設定）
    MAX_FILE_SIZE: int = 52428800  # 50MB - 作為預設值/備援
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"  # 作為預設值/備援
    UPLOAD_DIR: str = "./uploads"  # 實際儲存路徑
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略額外的環境變數（向後兼容）
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """將 CORS_ORIGINS 字串轉換為列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """將 ALLOWED_EXTENSIONS 字串轉換為列表"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]


# 建立全域設定實例
settings = Settings()
