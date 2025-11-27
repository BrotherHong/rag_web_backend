"""
向量嵌入處理器
"""

import json
from pathlib import Path
from typing import Optional
from app.models.llm.ollama_client import OllamaClient


class EmbeddingProcessor:
    """
    處理文檔摘要的向量化
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        初始化Embedding處理器
        
        參數:
            ollama_client: OllamaClient 實例
        """
        self.client = ollama_client or OllamaClient()
    
    def process_summary_file(
        self,
        summary_json_path: Path,
        output_json_path: Path
    ) -> bool:
        """
        處理摘要檔案生成嵌入
        
        參數:
            summary_json_path: 摘要 JSON 檔案路徑
            output_json_path: 輸出嵌入 JSON 路徑
            
        返回:
            bool: 是否成功
        """
        try:
            # 讀取摘要
            with open(summary_json_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            summary_text = summary_data.get('summary', '')
            if not summary_text:
                print(f"⚠️ 摘要為空")
                return False
            
            # 生成嵌入
            embedding = self.client.generate_embedding(summary_text)
            
            if not embedding:
                print(f"❌ 嵌入生成失敗")
                return False
            
            # 建立嵌入資料
            embedding_data = {
                'filename': summary_data.get('filename', ''),
                'summary_length': summary_data.get('summary_length', 0),
                'doc_type': summary_data.get('doc_type', 'Info Mode'),
                'embedding': embedding,
                'embedding_dim': len(embedding)
            }
            
            # 儲存
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(embedding_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 嵌入生成成功 (維度: {len(embedding)})")
            return True
            
        except Exception as e:
            print(f"❌ 處理失敗: {e}")
            return False
