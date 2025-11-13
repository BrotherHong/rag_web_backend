"""模擬檔案處理器 (Mock File Processor)

用於開發和測試階段，模擬檔案處理流程。
實際的檔案處理模組開發完成後，可直接替換此模擬器。
"""

import asyncio
import random
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.file_processor_interface import (
    IFileProcessor,
    FileProcessingResult,
    ProcessingStatus,
    ProcessingStep
)


class MockFileProcessor(IFileProcessor):
    """模擬檔案處理器
    
    模擬檔案處理的各個步驟，用於測試和演示。
    包含隨機延遲和成功率，以模擬真實場景。
    """
    
    def __init__(
        self,
        processing_delay: float = 2.0,
        success_rate: float = 0.95,
        enable_logging: bool = True
    ):
        """初始化模擬處理器
        
        Args:
            processing_delay: 處理延遲時間（秒）
            success_rate: 成功率 (0.0 - 1.0)
            enable_logging: 是否啟用日誌輸出
        """
        self.processing_delay = processing_delay
        self.success_rate = success_rate
        self.enable_logging = enable_logging
        self._processing_cache: Dict[int, Dict[str, Any]] = {}
    
    def _log(self, message: str):
        """日誌輸出"""
        if self.enable_logging:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[MockProcessor {timestamp}] {message}")
    
    async def process_file(
        self,
        file_id: int,
        file_path: str,
        file_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> FileProcessingResult:
        """模擬檔案處理流程
        
        模擬步驟：
        1. 檔案驗證
        2. 文字擷取
        3. 文本分塊
        4. 向量嵌入
        5. 向量索引
        """
        self._log(f"開始處理檔案 ID: {file_id}, 類型: {file_type}")
        
        # 初始化處理狀態
        self._processing_cache[file_id] = {
            "status": ProcessingStatus.PROCESSING,
            "current_step": ProcessingStep.VALIDATION,
            "start_time": datetime.now()
        }
        
        try:
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
            
            # 模擬隨機失敗
            if random.random() > self.success_rate:
                raise Exception("模擬處理失敗：隨機錯誤")
            
            # 處理完成
            self._processing_cache[file_id]["status"] = ProcessingStatus.COMPLETED
            self._log(f"檔案 ID: {file_id} 處理完成")
            
            return FileProcessingResult(
                file_id=file_id,
                status=ProcessingStatus.COMPLETED,
                current_step=ProcessingStep.INDEXING,
                text_content=text_content[:500],  # 只返回前 500 字
                chunk_count=chunk_count,
                vector_count=vector_count,
                metadata={
                    "processed_at": datetime.now().isoformat(),
                    "processing_time": self.processing_delay,
                    "file_type": file_type
                }
            )
            
        except Exception as e:
            self._log(f"檔案 ID: {file_id} 處理失敗: {str(e)}")
            self._processing_cache[file_id]["status"] = ProcessingStatus.FAILED
            
            return FileProcessingResult(
                file_id=file_id,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                metadata={
                    "failed_at": datetime.now().isoformat()
                }
            )
    
    async def _simulate_step(
        self,
        file_id: int,
        step: ProcessingStep,
        delay_factor: float = 1.0
    ):
        """模擬處理步驟
        
        Args:
            file_id: 檔案 ID
            step: 處理步驟
            delay_factor: 延遲係數
        """
        self._processing_cache[file_id]["current_step"] = step
        self._log(f"檔案 ID: {file_id} - 執行步驟: {step.value}")
        
        # 模擬處理時間
        delay = self.processing_delay * delay_factor * random.uniform(0.5, 1.5)
        await asyncio.sleep(delay)
    
    def _generate_mock_text(self, file_type: str) -> str:
        """生成模擬文字內容"""
        templates = {
            "pdf": "這是一份 PDF 文件的模擬內容。包含多個段落和章節...",
            "docx": "這是一份 Word 文件的模擬內容。包含標題、段落和列表...",
            "txt": "這是一份純文字檔案的模擬內容。內容簡潔明瞭...",
            "md": "# 這是一份 Markdown 文件\n\n包含標題、列表和程式碼區塊..."
        }
        
        base_text = templates.get(file_type, "這是檔案的模擬內容...")
        
        # 生成更長的內容
        paragraphs = []
        for i in range(random.randint(3, 10)):
            paragraphs.append(f"{base_text} [段落 {i+1}] " + "內容" * random.randint(10, 50))
        
        return "\n\n".join(paragraphs)
    
    async def get_processing_status(self, file_id: int) -> ProcessingStatus:
        """取得處理狀態"""
        if file_id in self._processing_cache:
            return self._processing_cache[file_id]["status"]
        return ProcessingStatus.PENDING
    
    async def cancel_processing(self, file_id: int) -> bool:
        """取消處理（模擬）"""
        if file_id in self._processing_cache:
            self._processing_cache[file_id]["status"] = ProcessingStatus.CANCELLED
            self._log(f"取消處理檔案 ID: {file_id}")
            return True
        return False
    
    async def retry_processing(self, file_id: int) -> FileProcessingResult:
        """重試處理（模擬）"""
        self._log(f"重試處理檔案 ID: {file_id}")
        # 清除舊的快取
        if file_id in self._processing_cache:
            del self._processing_cache[file_id]
        
        # 這裡需要從資料庫重新取得檔案資訊
        # 暫時返回一個佔位結果
        return FileProcessingResult(
            file_id=file_id,
            status=ProcessingStatus.QUEUED,
            metadata={"retry_at": datetime.now().isoformat()}
        )
    
    async def batch_process(
        self,
        file_ids: List[int],
        options: Optional[Dict[str, Any]] = None
    ) -> List[FileProcessingResult]:
        """批次處理（模擬）"""
        self._log(f"批次處理 {len(file_ids)} 個檔案")
        
        results = []
        for file_id in file_ids:
            # 模擬並行處理（實際上仍是序列，但可以用 asyncio.gather 改為並行）
            result = FileProcessingResult(
                file_id=file_id,
                status=ProcessingStatus.QUEUED,
                metadata={
                    "batch_queued_at": datetime.now().isoformat()
                }
            )
            results.append(result)
        
        return results


# 預設的模擬處理器實例
mock_file_processor = MockFileProcessor(
    processing_delay=1.0,  # 較短的延遲以加快測試
    success_rate=0.95,
    enable_logging=True
)
