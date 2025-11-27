"""
文檔摘要處理器
"""

import json
from pathlib import Path
from typing import Dict, Optional
from app.models.llm.ollama_client import OllamaClient
from app.models.llm.prompts import (
    RAG_DOCUMENT_SUMMARY,
    DOCUMENT_CLASSIFICATION,
    FORM_DOCUMENT_SUMMARY
)


class SummaryProcessor:
    """
    處理文檔以生成摘要
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        初始化摘要處理器
        
        參數:
            ollama_client: OllamaClient 實例
        """
        self.client = ollama_client or OllamaClient()
        self.chunk_size = 3000  # 字符數
        self.chunk_overlap = 300
    
    def process_markdown_file(
        self,
        md_file_path: Path,
        output_json_path: Path
    ) -> bool:
        """
        處理單一 markdown 檔案生成摘要
        
        參數:
            md_file_path: Markdown 檔案路徑
            output_json_path: 輸出 JSON 路徑
            
        返回:
            bool: 是否成功
        """
        try:
            # 讀取檔案內容
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                print(f"⚠️ 檔案內容為空: {md_file_path.name}")
                return False
            
            filename = md_file_path.name
            
            # 生成摘要
            summary, doc_type, chunk_content = self._generate_summary(
                content, filename
            )
            
            if not summary or summary.startswith('錯誤:'):
                print(f"❌ 摘要生成失敗: {summary}")
                return False
            
            # 建立摘要資料
            summary_data = {
                'filename': filename,
                'summary': summary,
                'summary_length': len(summary),
                'doc_type': doc_type,
                'original_content': chunk_content
            }
            
            # 儲存為 JSON
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 摘要生成成功 ({len(summary)} 字)")
            return True
            
        except Exception as e:
            print(f"❌ 處理失敗: {e}")
            return False
    
    def _classify_document(self, content: str) -> str:
        """分類文檔類型"""
        classification_content = content[:2000]
        prompt = DOCUMENT_CLASSIFICATION.format(text=classification_content)
        response = self.client.generate(prompt).strip()
        
        clean_response = self._extract_final_summary(response)
        
        if "Form Mode" in clean_response:
            return "Form Mode"
        elif "Info Mode" in clean_response:
            return "Info Mode"
        else:
            print(f"⚠️ 無法確定文檔類型，預設為 Info Mode")
            return "Info Mode"
    
    def _generate_summary(
        self,
        content: str,
        filename: str
    ) -> tuple[str, str, str]:
        """
        生成摘要
        
        返回:
            (摘要, 文檔類型, chunk內容)
        """
        doc_type = self._classify_document(content)
        print(f"  文檔分類: {doc_type}")
        
        if doc_type == "Form Mode":
            if len(content) > 1500:
                return self._generate_chunked_summary(content, filename, "Form Mode")
            else:
                prompt = FORM_DOCUMENT_SUMMARY.format(text=content, filename=filename)
                response = self.client.generate(prompt)
                summary = self._extract_final_summary(response)
                return (summary, doc_type, content)
        else:
            if len(content) > 1500:
                return self._generate_chunked_summary(content, filename, "Info Mode")
            else:
                prompt = RAG_DOCUMENT_SUMMARY.format(filename=filename, text=content)
                response = self.client.generate(prompt)
                summary = self._extract_final_summary(response)
                return (summary, doc_type, content)
    
    def _generate_chunked_summary(
        self,
        content: str,
        filename: str,
        doc_type: str
    ) -> tuple[str, str, str]:
        """處理長文檔（分塊）"""
        chunks = self._split_content(content)
        
        if not chunks:
            return ("", doc_type, content)
        
        # 只處理第一塊
        first_chunk = chunks[0]
        
        if doc_type == "Form Mode":
            prompt = FORM_DOCUMENT_SUMMARY.format(text=first_chunk, filename=filename)
        else:
            prompt = RAG_DOCUMENT_SUMMARY.format(filename=filename, text=first_chunk)
        
        response = self.client.generate(prompt)
        summary = self._extract_final_summary(response)
        
        return (summary, doc_type, first_chunk)
    
    def _split_content(self, content: str) -> list[str]:
        """將內容分塊"""
        chunks = []
        start = 0
        content_length = len(content)
        
        while start < content_length:
            end = start + self.chunk_size
            if end >= content_length:
                chunks.append(content[start:])
                break
            else:
                chunks.append(content[start:end])
                start = end - self.chunk_overlap
        
        return chunks
    
    def _extract_final_summary(self, text: str) -> str:
        """提取最終摘要（移除思考過程標籤）"""
        lines = text.strip().split('\n')
        filtered_lines = []
        skip = False
        
        for line in lines:
            if '<思考過程>' in line or '<thinking>' in line.lower():
                skip = True
                continue
            if '</思考過程>' in line or '</thinking>' in line.lower():
                skip = False
                continue
            if not skip and line.strip():
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines).strip()
