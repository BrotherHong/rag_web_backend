# 檔案處理功能整合測試指南

## 完成的工作

已成功將 `main/` 中的檔案處理功能遷移到 `web/rag_web_backend`：

### 1. 路徑結構調整
- ✅ 上傳檔案存放於 `uploads/{department_id}/unprocessed/`
- ✅ 處理後檔案存放於 `uploads/{department_id}/processed/{data,output_md,summaries,embeddings}/`

### 2. 模組遷移
- ✅ `app/models/llm/` - Ollama 客戶端與 prompts
- ✅ `app/utils/document_converter.py` - 文件轉 Markdown
- ✅ `app/utils/summarizer.py` - 摘要生成器
- ✅ `app/utils/embedding_processor.py` - 向量嵌入生成器

### 3. 處理服務
- ✅ `app/services/file_processor.py` - 四階段處理流程

### 4. 資料庫更新
- ✅ 新增欄位：`markdown_path`, `summary_path`, `embedding_path`
- ✅ 執行 Alembic 遷移

### 5. API 整合
- ✅ `POST /api/upload/batch` 新增 `startProcessing` 參數
- ✅ 背景任務自動觸發處理流程

### 6. 依賴套件
- ✅ markitdown, python-docx, openpyxl
- ✅ opencc-python-reimplemented
- ✅ requests, numpy, tqdm

---

## 階段性驗證步驟

### 步驟 1: 路徑驗證

```bash
# 啟動後端服務
cd /home/brick2/NCKU_rag/web/rag_web_backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**測試：**
1. 使用前端或 Postman 上傳一個測試檔案
2. 檢查檔案是否存在於 `uploads/1/unprocessed/`
3. 查詢資料庫確認 `file_path` 欄位正確

```sql
SELECT id, filename, original_filename, file_path, status 
FROM files 
ORDER BY id DESC LIMIT 5;
```

---

### 步驟 2: 模組匯入驗證

```bash
# 測試模組是否能正常匯入
cd /home/brick2/NCKU_rag/web/rag_web_backend
python3 -c "
from app.models.llm.ollama_client import OllamaClient
from app.utils.document_converter import DocumentConverter
from app.utils.summarizer import SummaryProcessor
from app.utils.embedding_processor import EmbeddingProcessor
print('✅ 所有模組匯入成功')
"
```

**預期輸出：**
```
✅ 所有模組匯入成功
```

---

### 步驟 3: Markdown 轉換驗證

**準備測試檔案：**
- 上傳一個 PDF 檔案 (測試 mineru)
- 上傳一個 DOCX 檔案 (測試 LibreOffice + markitdown)
- 上傳一個 XLSX 檔案 (測試 markitdown)

**測試轉換：**
```python
# 手動測試轉換功能
from pathlib import Path
from app.utils.document_converter import DocumentConverter

converter = DocumentConverter()

# 測試 PDF 轉換
pdf_file = Path("uploads/1/unprocessed/test.pdf")
md_output = Path("uploads/1/processed/output_md/test.md")
success = converter.convert_to_markdown(pdf_file, md_output, use_mineru_for_pdf=True)
print(f"PDF 轉換: {'成功' if success else '失敗'}")

# 檢查輸出
if md_output.exists():
    print(f"✅ Markdown 檔案已生成: {md_output}")
    print(f"檔案大小: {md_output.stat().st_size} bytes")
```

---

### 步驟 4: 摘要生成驗證

**前置條件：**
- Ollama 服務運行中
- 模型 `qwen2.5:14b` 已下載

**檢查 Ollama：**
```bash
# 測試 Ollama 連線
curl https://primehub.aic.ncku.edu.tw/console/apps/ollama-0-11-10-z0s7s/api/tags

# 或在 Python 中測試
python3 -c "
from app.models.llm.ollama_client import OllamaClient
client = OllamaClient()
response = client.generate('你好，請回覆「測試成功」')
print(f'Ollama 回應: {response}')
"
```

**測試摘要生成：**
```python
from pathlib import Path
from app.utils.summarizer import SummaryProcessor

summarizer = SummaryProcessor()

md_file = Path("uploads/1/processed/output_md/test.md")
summary_output = Path("uploads/1/processed/summaries/test_summary.json")

success = summarizer.process_markdown_file(md_file, summary_output)
print(f"摘要生成: {'成功' if success else '失敗'}")

# 檢查輸出
if summary_output.exists():
    import json
    with open(summary_output) as f:
        data = json.load(f)
    print(f"✅ 摘要檔案已生成")
    print(f"文檔類型: {data.get('doc_type')}")
    print(f"摘要長度: {data.get('summary_length')} 字")
    print(f"摘要內容: {data.get('summary')[:100]}...")
```

---

### 步驟 5: 向量嵌入驗證

**檢查嵌入模型：**
```bash
# 確認 bge-m3 模型可用
curl https://primehub.aic.ncku.edu.tw/console/apps/ollama-0-11-10-z0s7s/api/tags | grep bge-m3
```

**測試嵌入生成：**
```python
from pathlib import Path
from app.utils.embedding_processor import EmbeddingProcessor

embedder = EmbeddingProcessor()

summary_file = Path("uploads/1/processed/summaries/test_summary.json")
embedding_output = Path("uploads/1/processed/embeddings/test_embedding.json")

success = embedder.process_summary_file(summary_file, embedding_output)
print(f"嵌入生成: {'成功' if success else '失敗'}")

# 檢查輸出
if embedding_output.exists():
    import json
    with open(embedding_output) as f:
        data = json.load(f)
    print(f"✅ 嵌入檔案已生成")
    print(f"向量維度: {data.get('embedding_dim')}")
    print(f"向量前10個值: {data.get('embedding')[:10]}")
```

---

### 步驟 6: 端到端流程驗證

**使用 Postman 或 cURL 測試完整流程：**

```bash
# 1. 登入取得 token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"

# 2. 上傳檔案並觸發處理
curl -X POST "http://localhost:8000/api/upload/batch" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test.pdf" \
  -F "startProcessing=true" \
  -F "categories={}"

# 回應會包含 taskId，例如: {"success": true, "taskId": "abc-123", ...}

# 3. 查詢處理進度
curl -X GET "http://localhost:8000/api/upload/progress/abc-123" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 檢查檔案狀態
curl -X GET "http://localhost:8000/api/files?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**檢查資料庫：**
```sql
-- 查看最新上傳的檔案及其處理狀態
SELECT 
    id,
    original_filename,
    status,
    processing_step,
    processing_progress,
    markdown_path IS NOT NULL as has_markdown,
    summary_path IS NOT NULL as has_summary,
    embedding_path IS NOT NULL as has_embedding,
    is_vectorized
FROM files 
ORDER BY created_at DESC 
LIMIT 5;
```

---

### 步驟 7: 錯誤處理驗證

**測試錯誤情況：**

1. **關閉 Ollama 服務後上傳**
   - 預期：檔案狀態變為 `failed`
   - `error_message` 記錄連線錯誤

2. **上傳損壞的 PDF**
   - 預期：轉換階段失敗
   - `processing_step` 停留在 `convert`

3. **上傳不支援的檔案格式**
   - 預期：在上傳階段就被拒絕

```sql
-- 查看失敗的檔案
SELECT id, original_filename, status, processing_step, error_message
FROM files 
WHERE status = 'failed'
ORDER BY created_at DESC;
```

---

## 常見問題排除

### 問題 1: ModuleNotFoundError

**症狀：**
```
ImportError: cannot import name 'OllamaClient' from 'app.models.llm.ollama_client'
```

**解決：**
```bash
# 確認檔案存在
ls -la app/models/llm/

# 檢查 __init__.py 檔案
cat app/models/llm/__init__.py

# 重啟服務
pkill -f uvicorn
uvicorn app.main:app --reload
```

---

### 問題 2: Ollama 連線失敗

**症狀：**
```
錯誤: 無法連接到 Ollama 服務器
```

**解決：**
```bash
# 1. 檢查 Ollama URL
curl https://primehub.aic.ncku.edu.tw/console/apps/ollama-0-11-10-z0s7s/api/tags

# 2. 檢查 config.py 中的設定
grep OLLAMA app/config.py

# 3. 確認環境變數
env | grep OLLAMA

# 4. 測試直接連線
python3 -c "
import requests
url = 'https://primehub.aic.ncku.edu.tw/console/apps/ollama-0-11-10-z0s7s/api/tags'
response = requests.get(url)
print(response.status_code)
print(response.json())
"
```

---

### 問題 3: LibreOffice 或 Pandoc 未安裝

**症狀：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'soffice'
```

**解決：**
```bash
# 安裝 LibreOffice
sudo apt update
sudo apt install libreoffice

# 驗證安裝
soffice --version

# 安裝 Pandoc
sudo apt install pandoc

# 驗證安裝
pandoc --version
```

---

### 問題 4: Mineru 不可用

**症狀：**
```
FileNotFoundError: 'magic-pdf' command not found
```

**解決：**
```bash
# 安裝 mineru (如果需要)
pip install mineru

# 或者在程式碼中設定使用 markitdown 作為後備
# document_converter.py 已經實作了自動降級到 markitdown
```

---

## 預期結果總結

完整處理流程成功後，應該看到：

1. **檔案系統：**
   ```
   uploads/1/
   ├── unprocessed/      (空的，檔案已移動)
   └── processed/
       ├── data/         (原始檔案)
       ├── output_md/    (Markdown 檔案)
       ├── summaries/    (JSON 摘要)
       └── embeddings/   (JSON 嵌入)
   ```

2. **資料庫記錄：**
   - `status` = 'completed'
   - `processing_step` = 'completed'
   - `processing_progress` = 100
   - `is_vectorized` = true
   - 所有路徑欄位都有值

3. **API 回應：**
   - 進度查詢顯示 100%
   - 檔案列表顯示向量化完成

---

## 下一步建議

如果所有驗證都通過，可以考慮：

1. **效能優化：**
   - 實作並發控制（限制同時處理的檔案數）
   - 使用 Redis 持久化處理進度
   - 實作任務佇列（Celery）

2. **功能增強：**
   - 實作「從失敗階段繼續」功能
   - 加入處理重試機制
   - 實作處理日誌記錄

3. **監控與告警：**
   - 加入 Prometheus metrics
   - 實作健康檢查端點
   - 建立 Grafana 監控面板

4. **文件完善：**
   - 撰寫 API 文件
   - 建立系統部署指南
   - 編寫故障排除手冊
