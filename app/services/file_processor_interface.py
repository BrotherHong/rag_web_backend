"""檔案處理接口定義 (File Processing Interface)

此模組定義檔案處理的標準接口，供外部檔案處理服務實作。
檔案上傳後，會透過此接口進行非同步處理（文字擷取、向量化等）。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class ProcessingStatus(str, Enum):
    """檔案處理狀態"""
    PENDING = "pending"           # 等待處理
    QUEUED = "queued"             # 已加入佇列
    PROCESSING = "processing"     # 處理中
    COMPLETED = "completed"       # 完成
    FAILED = "failed"             # 失敗
    CANCELLED = "cancelled"       # 已取消


class ProcessingStep(str, Enum):
    """處理步驟"""
    VALIDATION = "validation"           # 檔案驗證
    TEXT_EXTRACTION = "text_extraction" # 文字擷取
    CHUNKING = "chunking"               # 文本分塊
    EMBEDDING = "embedding"             # 向量嵌入
    INDEXING = "indexing"               # 向量索引


class FileProcessingResult:
    """檔案處理結果"""
    
    def __init__(
        self,
        file_id: int,
        status: ProcessingStatus,
        current_step: Optional[ProcessingStep] = None,
        text_content: Optional[str] = None,
        chunk_count: Optional[int] = None,
        vector_count: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file_id = file_id
        self.status = status
        self.current_step = current_step
        self.text_content = text_content
        self.chunk_count = chunk_count
        self.vector_count = vector_count
        self.error_message = error_message
        self.metadata = metadata or {}


class IFileProcessor(ABC):
    """檔案處理器接口
    
    外部檔案處理模組需實作此接口，以便與主系統整合。
    
    使用範例：
        processor = YourFileProcessor()
        result = await processor.process_file(file_id=123)
    """
    
    @abstractmethod
    async def process_file(
        self,
        file_id: int,
        file_path: str,
        file_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> FileProcessingResult:
        """處理單一檔案
        
        Args:
            file_id: 檔案 ID
            file_path: 檔案完整路徑
            file_type: 檔案類型 (pdf, docx, txt, md)
            options: 處理選項（如：chunk_size, overlap 等）
            
        Returns:
            FileProcessingResult: 處理結果
        """
        pass
    
    @abstractmethod
    async def get_processing_status(self, file_id: int) -> ProcessingStatus:
        """取得檔案處理狀態
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            ProcessingStatus: 當前處理狀態
        """
        pass
    
    @abstractmethod
    async def cancel_processing(self, file_id: int) -> bool:
        """取消檔案處理
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            bool: 是否成功取消
        """
        pass
    
    @abstractmethod
    async def retry_processing(self, file_id: int) -> FileProcessingResult:
        """重試檔案處理
        
        Args:
            file_id: 檔案 ID
            
        Returns:
            FileProcessingResult: 處理結果
        """
        pass
    
    @abstractmethod
    async def batch_process(
        self,
        file_ids: List[int],
        options: Optional[Dict[str, Any]] = None
    ) -> List[FileProcessingResult]:
        """批次處理多個檔案
        
        Args:
            file_ids: 檔案 ID 列表
            options: 處理選項
            
        Returns:
            List[FileProcessingResult]: 處理結果列表
        """
        pass


class FileProcessorRegistry:
    """檔案處理器註冊中心
    
    用於註冊和取得檔案處理器實例。
    支援多種處理器並可動態切換。
    """
    
    _processors: Dict[str, IFileProcessor] = {}
    _default_processor: Optional[str] = None
    
    @classmethod
    def register(cls, name: str, processor: IFileProcessor):
        """註冊檔案處理器
        
        Args:
            name: 處理器名稱
            processor: 處理器實例
        """
        cls._processors[name] = processor
        if cls._default_processor is None:
            cls._default_processor = name
    
    @classmethod
    def get_processor(cls, name: Optional[str] = None) -> Optional[IFileProcessor]:
        """取得檔案處理器
        
        Args:
            name: 處理器名稱（None 則使用預設）
            
        Returns:
            Optional[IFileProcessor]: 處理器實例
        """
        if name is None:
            name = cls._default_processor
        return cls._processors.get(name)
    
    @classmethod
    def set_default(cls, name: str):
        """設定預設處理器
        
        Args:
            name: 處理器名稱
        """
        if name in cls._processors:
            cls._default_processor = name
    
    @classmethod
    def list_processors(cls) -> List[str]:
        """列出所有已註冊的處理器
        
        Returns:
            List[str]: 處理器名稱列表
        """
        return list(cls._processors.keys())


# 全域註冊中心實例
file_processor_registry = FileProcessorRegistry()
