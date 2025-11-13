# 檔案處理接口說明文檔

## 概述

本系統提供了標準的檔案處理接口，用於整合外部檔案處理模組（如文字擷取、向量化等）。該接口設計遵循**開放封閉原則**，允許在不修改核心系統的情況下接入不同的處理實現。

## 架構設計

### 1. 接口定義 (`IFileProcessor`)

位於：`app/services/file_processor_interface.py`

這是一個抽象基類 (ABC)，定義了檔案處理器必須實現的標準方法：

```python
class IFileProcessor(ABC):
    """檔案處理器標準接口"""
    
    @abstractmethod
    async def process_file(
        self,
        file_id: int,
        file_path: str,
        file_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> FileProcessingResult:
        """處理單個檔案"""
        pass
    
    @abstractmethod
    async def get_processing_status(self, file_id: int) -> ProcessingStatus:
        """取得處理狀態"""
        pass
    
    @abstractmethod
    async def cancel_processing(self, file_id: int) -> bool:
        """取消處理"""
        pass
    
    @abstractmethod
    async def retry_processing(self, file_id: int) -> FileProcessingResult:
        """重試處理"""
        pass
    
    @abstractmethod
    async def batch_process(
        self,
        file_ids: List[int],
        options: Optional[Dict[str, Any]] = None
    ) -> List[FileProcessingResult]:
        """批次處理"""
        pass
```

### 2. 處理狀態定義

```python
class ProcessingStatus(str, Enum):
    """處理狀態"""
    PENDING = "pending"          # 等待處理
    QUEUED = "queued"            # 已加入隊列
    PROCESSING = "processing"    # 處理中
    COMPLETED = "completed"      # 處理完成
    FAILED = "failed"            # 處理失敗
    CANCELLED = "cancelled"      # 已取消

class ProcessingStep(str, Enum):
    """處理步驟"""
    VALIDATION = "validation"               # 檔案驗證
    TEXT_EXTRACTION = "text_extraction"     # 文字擷取
    CHUNKING = "chunking"                   # 文本分塊
    EMBEDDING = "embedding"                 # 向量嵌入
    INDEXING = "indexing"                   # 向量索引
```

### 3. 處理結果類

```python
class FileProcessingResult:
    """檔案處理結果"""
    
    def __init__(
        self,
        file_id: int,
        status: ProcessingStatus,
        current_step: Optional[ProcessingStep] = None,
        text_content: Optional[str] = None,
        chunk_count: int = 0,
        vector_count: int = 0,
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
```

## 實現示例

### 模擬處理器 (`MockFileProcessor`)

位於：`app/services/mock_file_processor.py`

這是一個完整的實現示例，用於開發和測試階段：

```python
class MockFileProcessor(IFileProcessor):
    """模擬檔案處理器"""
    
    def __init__(
        self,
        processing_delay: float = 2.0,
        success_rate: float = 0.95,
        enable_logging: bool = True
    ):
        self.processing_delay = processing_delay
        self.success_rate = success_rate
        self.enable_logging = enable_logging
        self._processing_cache = {}
    
    async def process_file(
        self,
        file_id: int,
        file_path: str,
        file_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> FileProcessingResult:
        """模擬檔案處理流程"""
        
        # 步驟 1: 檔案驗證
        await self._simulate_step(file_id, ProcessingStep.VALIDATION, 0.5)
        
        # 步驟 2: 文字擷取
        await self._simulate_step(file_id, ProcessingStep.TEXT_EXTRACTION, 1.0)
        text_content = self._generate_mock_text(file_type)
        
        # 步驟 3: 文本分塊
        await self._simulate_step(file_id, ProcessingStep.CHUNKING, 0.8)
        chunk_count = random.randint(5, 50)
        
        # 步驟 4: 向量嵌入
        await self._simulate_step(file_id, ProcessingStep.EMBEDDING, 1.5)
        
        # 步驟 5: 向量索引
        await self._simulate_step(file_id, ProcessingStep.INDEXING, 0.7)
        vector_count = chunk_count
        
        return FileProcessingResult(
            file_id=file_id,
            status=ProcessingStatus.COMPLETED,
            current_step=ProcessingStep.INDEXING,
            text_content=text_content[:500],
            chunk_count=chunk_count,
            vector_count=vector_count,
            metadata={
                "processed_at": datetime.now().isoformat(),
                "processing_time": self.processing_delay,
                "file_type": file_type
            }
        )
```

## 接入方式

### 方式一：直接替換實例

最簡單的接入方式，適用於單一實現：

```python
# 在 app/services/file_processor.py 中
from your_module import YourFileProcessor

# 直接創建實例
file_processor = YourFileProcessor(
    api_key="your_api_key",
    model_name="your_model",
    # ... 其他配置
)
```

然後在 `app/api/files.py` 中導入：

```python
from app.services.file_processor import file_processor
```

### 方式二：使用註冊器

適用於需要支援多種處理器的場景：

```python
# 1. 註冊處理器
from app.services.file_processor_interface import FileProcessorRegistry
from your_module import YourFileProcessor

registry = FileProcessorRegistry()
registry.register("your_processor", YourFileProcessor())

# 2. 在需要時取得處理器
processor = registry.get("your_processor")
result = await processor.process_file(...)
```

### 方式三：透過配置檔案

最靈活的方式，支援動態切換：

```python
# config.py
FILE_PROCESSOR_TYPE = "your_processor"
FILE_PROCESSOR_CONFIG = {
    "api_key": "...",
    "model_name": "...",
}

# 在初始化時根據配置載入
from importlib import import_module

processor_module = import_module(f"processors.{config.FILE_PROCESSOR_TYPE}")
processor_class = getattr(processor_module, "FileProcessor")
file_processor = processor_class(**config.FILE_PROCESSOR_CONFIG)
```

## 整合到上傳流程

目前的檔案上傳端點已經整合了處理器調用：

```python
@router.post("/upload")
async def upload_file(...):
    # ... 儲存檔案 ...
    
    # 觸發檔案處理
    try:
        db_file.processing_started_at = datetime.now()
        db_file.status = "processing"
        await db.commit()
        
        # 呼叫處理器
        processing_result = await file_processor.process_file(
            file_id=db_file.id,
            file_path=file_path,
            file_type=db_file.file_type,
            options={"description": description}
        )
        
        # 更新檔案狀態
        db_file.processing_completed_at = datetime.now()
        
        if processing_result.status == ProcessingStatus.COMPLETED:
            db_file.status = "active"
            db_file.chunk_count = processing_result.chunk_count
            db_file.vector_count = processing_result.vector_count
            db_file.is_vectorized = True
            db_file.processing_progress = 100
            db_file.processing_step = "completed"
        
        await db.commit()
        
    except Exception as e:
        db_file.status = "failed"
        db_file.error_message = str(e)
        await db.commit()
    
    return FileUploadResponse(...)
```

## 背景任務建議

**重要：** 當前實現是同步處理，僅用於演示。在生產環境中，強烈建議使用背景任務：

### 使用 Celery

```python
# tasks.py
from celery import Celery

celery_app = Celery("tasks", broker="redis://localhost:6379")

@celery_app.task
def process_file_task(file_id: int, file_path: str, file_type: str):
    """背景處理檔案"""
    result = await file_processor.process_file(
        file_id=file_id,
        file_path=file_path,
        file_type=file_type
    )
    
    # 更新資料庫狀態
    # ...

# 在上傳端點中觸發
process_file_task.delay(db_file.id, file_path, db_file.file_type)
```

### 使用 FastAPI BackgroundTasks

```python
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    ...
):
    # ... 儲存檔案 ...
    
    # 添加背景任務
    background_tasks.add_task(
        process_file_in_background,
        db_file.id,
        file_path,
        db_file.file_type
    )
    
    return FileUploadResponse(...)

async def process_file_in_background(file_id, file_path, file_type):
    """背景處理函數"""
    # ... 處理邏輯 ...
```

## API 端點

系統提供以下端點支援檔案處理：

### 1. 上傳檔案
```
POST /api/files/upload
```

### 2. 批次上傳
```
POST /api/files/batch-upload
```

### 3. 查詢處理狀態
```
GET /api/files/{file_id}/processing-status
```

返回格式：
```json
{
  "file_id": 1,
  "filename": "example.pdf",
  "status": "completed",
  "processing_step": "indexing",
  "processing_progress": 100,
  "processing_started_at": "2024-01-15T10:00:00",
  "processing_completed_at": "2024-01-15T10:00:15",
  "processing_duration_seconds": 15.0,
  "chunk_count": 25,
  "vector_count": 25,
  "error_message": null,
  "is_vectorized": true
}
```

## 資料庫欄位

File 模型包含以下處理相關欄位：

```python
class File(Base):
    # 處理狀態
    status: FileStatus                    # pending/processing/completed/failed
    error_message: Optional[str]          # 錯誤訊息
    
    # 向量化資訊
    is_vectorized: bool                   # 是否已向量化
    chunk_count: int                      # 文本區塊數量
    vector_count: int                     # 向量數量
    
    # 處理進度追蹤
    processing_step: Optional[str]        # 當前步驟
    processing_progress: int              # 進度 (0-100)
    processing_started_at: Optional[datetime]    # 開始時間
    processing_completed_at: Optional[datetime]  # 完成時間
```

## 測試

使用測試腳本驗證整合：

```bash
# 啟動服務
docker-compose up -d

# 執行測試
python scripts/test_file_api.py
```

測試將驗證：
1. 檔案上傳
2. 處理狀態查詢
3. 批次上傳
4. 完整的處理流程

## 注意事項

1. **異步處理**：實際處理器應該支援 `async/await`
2. **錯誤處理**：必須妥善處理各種異常情況
3. **資源清理**：處理完成或失敗後要清理臨時資源
4. **日誌記錄**：建議使用 Python logging 而非 print
5. **性能監控**：記錄處理時間、成功率等指標
6. **重試機制**：實現智能重試策略
7. **並發控制**：避免同時處理過多檔案

## 後續計劃

- [ ] 完整的 Celery 整合
- [ ] 進度即時推送 (WebSocket)
- [ ] 處理隊列優先級
- [ ] 處理失敗自動重試
- [ ] 處理結果快取
- [ ] 多種處理器並存支援

## 聯繫與支援

如有問題或需要協助，請查閱：
- 開發文檔：`backend_docs/`
- API 文檔：http://localhost:8000/docs
- 開發日誌：`backend_docs/08_DEVELOPMENT_GUIDE.md`
