"""
檔案處理服務 - 處理上傳檔案的完整流程
"""

import asyncio
import shutil
from pathlib import Path
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File, FileStatus
from app.services.file_storage import file_storage
from app.utils.document_converter import DocumentConverter
from app.utils.summarizer import SummaryProcessor
from app.utils.embedding_processor import EmbeddingProcessor
from app.models.llm.ollama_client import OllamaClient


class FileProcessingService:
    """檔案處理服務 - 負責完整的處理流程"""
    
    def __init__(self):
        self.converter = DocumentConverter()
        self.ollama_client = OllamaClient()
        self.summarizer = SummaryProcessor(self.ollama_client)
        self.embedder = EmbeddingProcessor(self.ollama_client)
        self.last_temp_dir = None  # 保存最近一次的暫存目錄路徑
    
    async def process_files_batch(
        self,
        file_ids: List[int],
        task_id: str,
        db: AsyncSession,
        progress_callback = None
    ) -> Dict:
        """
        批次處理檔案
        
        參數:
            file_ids: 檔案 ID 列表
            task_id: 任務 ID（用於更新前端進度）
            db: 資料庫 session
            progress_callback: 進度回呼函數
            
        返回:
            處理結果統計
        """
        results = {
            'total': len(file_ids),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for idx, file_id in enumerate(file_ids):
            try:
                # 獲取檔案記錄
                file_record = await db.get(File, file_id)
                if not file_record:
                    results['failed'] += 1
                    results['errors'].append(f"檔案 ID {file_id} 不存在")
                    continue
                
                # 更新狀態為處理中
                file_record.status = FileStatus.PROCESSING
                file_record.processing_step = "classify"
                file_record.processing_progress = 0
                await db.commit()
                
                # 執行四階段處理
                success = await self._process_single_file(file_record, db, progress_callback)
                
                if success:
                    file_record.status = FileStatus.COMPLETED
                    file_record.processing_step = "completed"
                    file_record.processing_progress = 100
                    results['success'] += 1
                else:
                    file_record.status = FileStatus.FAILED
                    results['failed'] += 1
                
                await db.commit()
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"檔案 ID {file_id}: {str(e)}")
                
                # 更新為失敗狀態
                try:
                    file_record = await db.get(File, file_id)
                    if file_record:
                        file_record.status = FileStatus.FAILED
                        file_record.error_message = str(e)
                        await db.commit()
                except:
                    pass
        
        return results
    
    async def _process_single_file(
        self,
        file_record: File,
        db: AsyncSession,
        progress_callback = None
    ) -> bool:
        """
        處理單一檔案的四階段流程
        使用暫存資料夾，全部成功才移動到正確位置
        
        返回:
            bool: 是否成功
        """
        import tempfile
        temp_dir = None
        
        try:
            file_path = Path(file_record.file_path)
            department_id = file_record.department_id
            
            # 清理上一次的暫存目錄（如果存在）
            if self.last_temp_dir and Path(self.last_temp_dir).exists():
                try:
                    shutil.rmtree(self.last_temp_dir)
                    print(f"🗑️ 已清理上次暫存目錄: {self.last_temp_dir}")
                except Exception as e:
                    print(f"⚠️ 清理上次暫存目錄失敗: {e}")
            
            # 創建新的暫存目錄
            temp_dir = Path(tempfile.mkdtemp(prefix="rag_process_"))
            self.last_temp_dir = str(temp_dir)  # 保存路徑
            print(f"\n🗂️ 使用暫存目錄: {temp_dir}")
            print(f"💡 此暫存目錄將保留到下次處理時才清理")
            
            # 階段 1: 準備處理 (0-25%)
            print(f"\n📂 階段 1: 準備處理 - {file_record.original_filename}")
            file_record.processing_step = "classify"
            file_record.processing_progress = 10
            await db.commit()
            
            # 複製檔案到暫存目錄（不移動原檔案）
            temp_data_file = temp_dir / "data" / file_path.name
            temp_data_file.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, str(file_path), str(temp_data_file))
            
            file_record.processing_progress = 25
            await db.commit()
            
            # 階段 2: 轉換為 Markdown (25-50%)
            print(f"\n📝 階段 2: 轉換為 Markdown")
            file_record.processing_step = "convert"
            file_record.processing_progress = 30
            await db.commit()
            
            temp_md_path = temp_dir / "output_md" / f"{file_path.stem}.md"
            temp_md_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = await asyncio.to_thread(
                self.converter.convert_to_markdown,
                temp_data_file,
                temp_md_path,
                use_mineru_for_pdf=True
            )
            
            if not success:
                file_record.error_message = "Markdown 轉換失敗"
                raise Exception("Markdown 轉換失敗")
            
            file_record.processing_progress = 50
            await db.commit()
            
            # 階段 3: 生成摘要 (50-75%)
            print(f"\n💡 階段 3: 生成摘要")
            file_record.processing_step = "summarize"
            file_record.processing_progress = 55
            await db.commit()
            
            temp_summary_path = temp_dir / "summaries" / f"{file_path.stem}_summary.json"
            temp_summary_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = await asyncio.to_thread(
                self.summarizer.process_markdown_file,
                temp_md_path,
                temp_summary_path
            )
            
            if not success:
                file_record.error_message = "摘要生成失敗"
                raise Exception("摘要生成失敗")
            
            file_record.processing_progress = 75
            await db.commit()
            
            # 階段 4: 生成嵌入 (75-100%)
            print(f"\n🔢 階段 4: 生成向量嵌入")
            file_record.processing_step = "embed"
            file_record.processing_progress = 80
            await db.commit()
            
            temp_embedding_path = temp_dir / "embeddings" / f"{file_path.stem}_embedding.json"
            temp_embedding_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = await asyncio.to_thread(
                self.embedder.process_summary_file,
                temp_summary_path,
                temp_embedding_path
            )
            
            if not success:
                file_record.error_message = "嵌入生成失敗"
                raise Exception("嵌入生成失敗")
            
            file_record.processing_progress = 90
            await db.commit()
            
            # 所有階段成功，移動檔案到正確位置
            print(f"\n📦 移動檔案到正確位置...")
            
            # 移動到 processed/data
            final_data_path = file_storage._get_processed_path(department_id, "data") / file_path.name
            await asyncio.to_thread(shutil.move, str(temp_data_file), str(final_data_path))
            
            # 移動 markdown
            final_md_path = file_storage._get_processed_path(department_id, "output_md") / temp_md_path.name
            await asyncio.to_thread(shutil.move, str(temp_md_path), str(final_md_path))
            
            # 移動 summary
            final_summary_path = file_storage._get_processed_path(department_id, "summaries") / temp_summary_path.name
            await asyncio.to_thread(shutil.move, str(temp_summary_path), str(final_summary_path))
            
            # 移動 embedding
            final_embedding_path = file_storage._get_processed_path(department_id, "embeddings") / temp_embedding_path.name
            await asyncio.to_thread(shutil.move, str(temp_embedding_path), str(final_embedding_path))
            
            # 更新資料庫記錄
            file_record.file_path = str(final_data_path)
            file_record.markdown_path = str(final_md_path)
            file_record.summary_path = str(final_summary_path)
            file_record.embedding_path = str(final_embedding_path)
            file_record.is_vectorized = True
            file_record.processing_progress = 100
            await db.commit()
            
            print(f"✅ 檔案處理完成: {file_record.original_filename}")
            
            # 刪除 unprocessed 中的原始檔案
            if file_path.exists() and 'unprocessed' in str(file_path):
                try:
                    file_path.unlink()
                    print(f"🗑️ 已刪除原始檔案: {file_path}")
                except Exception as e:
                    print(f"⚠️ 刪除原始檔案失敗: {e}")
            
            # 保留暫存目錄供檢查（下次處理時才清理）
            print(f"📁 暫存目錄已保留: {temp_dir}")
            print(f"   可使用以下命令查看: ls -la {temp_dir}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ 處理失敗: {e}")
            file_record.error_message = str(e)
            
            # 失敗時清理當前的暫存目錄
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    print(f"🗑️ 已清理暫存目錄（處理失敗）")
                    self.last_temp_dir = None  # 清除記錄
                except Exception as cleanup_error:
                    print(f"⚠️ 清理暫存目錄失敗: {cleanup_error}")
            
            return False


# 建立全域實例
file_processing_service = FileProcessingService()
