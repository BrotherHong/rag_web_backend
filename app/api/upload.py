"""上傳管理 API 路由 - 處理批次上傳和進度追蹤"""

from typing import List, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/upload", tags=["上傳管理"])

# 模擬的上傳任務儲存（實際應用中應該使用 Redis 或資料庫）
upload_tasks: Dict[str, dict] = {}


# Pydantic Models
class CheckDuplicatesRequest(BaseModel):
    """檢查重複檔案的請求模型"""
    filenames: List[str]


@router.post("/batch", summary="批次上傳檔案")
async def batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    categories: str = Form("{}"),  # JSON 字串格式的分類對應
    removeFileIds: str = Form("[]"),  # 要刪除的舊檔案 ID 列表
    startProcessing: str = Form("false"),  # 是否立即開始處理
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批次上傳多個檔案
    
    前端發送格式:
    - files: 檔案列表
    - categories: JSON 字串 {"filename1.pdf": "分類名稱1", ...}
    - removeFileIds: JSON 字串 [1, 2, 3, ...]
    
    返回格式:
    {
      success: true,
      taskId: "uuid",
      message: "上傳任務已建立"
    }
    """
    import uuid
    import json
    import os
    from app.models import File as FileModel, Category
    from app.services.file_storage import file_storage
    from app.services.activity import activity_service
    
    # Debug: 輸出接收到的參數
    print(f"\n{'='*60}")
    print(f"📤 收到上傳請求")
    print(f"檔案數量: {len(files)}")
    print(f"startProcessing 參數: {startProcessing}")
    print(f"{'='*60}\n")
    
    # 解析參數
    try:
        category_map = json.loads(categories)
        remove_ids = json.loads(removeFileIds)
    except:
        category_map = {}
        remove_ids = []
    
    # 生成任務 ID
    task_id = str(uuid.uuid4())
    
    # 1. 先刪除要移除的舊檔案
    if remove_ids:
        for file_id in remove_ids:
            try:
                old_file = await db.get(FileModel, file_id)
                if old_file and old_file.department_id == current_user.department_id:
                    # 刪除實體檔案
                    if os.path.exists(old_file.file_path):
                        os.remove(old_file.file_path)
                    # 刪除資料庫記錄
                    await db.delete(old_file)
            except Exception as e:
                print(f"刪除檔案 {file_id} 失敗: {str(e)}")
        
        await db.commit()
    
    # 2. 初始化任務記錄（用於前端輪詢）
    file_list = []
    for file in files:
        file_list.append({
            "name": file.filename,
            "status": "pending",
            "progress": 0,
            "error": None
        })
    
    task = {
        "task_id": task_id,
        "user_id": current_user.id,
        "status": "processing",
        "totalFiles": len(files),
        "processedFiles": 0,
        "successFiles": 0,
        "failedFiles": 0,
        "deletedFiles": len(remove_ids),
        "files": file_list,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    upload_tasks[task_id] = task
    
    # 3. 處理新檔案上傳
    success_count = 0
    
    for idx, file in enumerate(files):
        # 更新當前檔案狀態為處理中
        task["files"][idx]["status"] = "processing"
        task["files"][idx]["progress"] = 50
        task["updated_at"] = datetime.now().isoformat()
        
        try:
            # 驗證檔案
            is_valid, error_msg = await file_storage.validate_file(file, db)
            if not is_valid:
                task["files"][idx]["status"] = "failed"
                task["files"][idx]["error"] = error_msg
                task["failedFiles"] += 1
                continue
            
            # 取得分類
            category_name = category_map.get(file.filename)
            category_id = None
            if category_name:
                category_query = select(Category).where(
                    Category.name == category_name,
                    Category.department_id == current_user.department_id
                )
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_id = category.id
            
            # 儲存檔案
            unique_filename, file_path, file_size = await file_storage.save_upload_file(
                file,
                current_user.department_id
            )
            
            # 建立資料庫記錄
            ext = os.path.splitext(file.filename)[1].lower()
            db_file = FileModel(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=ext[1:] if ext else "unknown",
                mime_type=file.content_type,
                category_id=category_id,
                department_id=current_user.department_id,
                uploader_id=current_user.id,
                status="completed"  # 使用 FileStatus.COMPLETED
            )
            
            db.add(db_file)
            await db.flush()
            
            # 更新檔案狀態為完成
            task["files"][idx]["status"] = "completed"
            task["files"][idx]["progress"] = 100
            task["successFiles"] += 1
            success_count += 1
            
        except Exception as e:
            task["files"][idx]["status"] = "failed"
            task["files"][idx]["error"] = str(e)
            task["failedFiles"] += 1
        
        # 更新已處理檔案數
        task["processedFiles"] = idx + 1
        task["updated_at"] = datetime.now().isoformat()
    
    await db.commit()
    
    # 記錄活動（包含檔案名稱列表）
    if success_count > 0:
        # 收集成功上傳的檔案名稱
        success_files = [f["name"] for f in task["files"] if f["status"] == "completed"]
        file_list_str = "、".join(success_files[:5])  # 最多顯示 5 個檔案名
        if len(success_files) > 5:
            file_list_str += f" 等 {len(success_files)} 個檔案"
        
        await activity_service.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="UPLOAD",
            description=f"批次上傳檔案: {file_list_str}",
            department_id=current_user.department_id
        )
        await db.commit()  # 提交活動記錄
    
    # 更新任務最終狀態
    task["status"] = "completed" if task["failedFiles"] == 0 else "partial"
    task["updated_at"] = datetime.now().isoformat()
    
    # 如果需要開始處理，觸發背景任務
    should_process = startProcessing.lower() == "true"
    
    print(f"\n{'='*60}")
    print(f"🔍 檢查是否需要觸發處理")
    print(f"startProcessing: '{startProcessing}'")
    print(f"should_process: {should_process}")
    print(f"success_count: {success_count}")
    print(f"{'='*60}\n")
    
    if should_process and success_count > 0:
        # 收集成功上傳的檔案 ID
        uploaded_file_ids = []
        for idx, file in enumerate(files):
            if task["files"][idx]["status"] == "completed":
                # 從資料庫查詢檔案 ID
                result = await db.execute(
                    select(FileModel).where(
                        FileModel.original_filename == file.filename,
                        FileModel.department_id == current_user.department_id
                    ).order_by(FileModel.id.desc()).limit(1)
                )
                file_record = result.scalar_one_or_none()
                if file_record:
                    uploaded_file_ids.append(file_record.id)
        
        if uploaded_file_ids and background_tasks:
            # 啟動背景處理任務
            from app.services.file_processor import file_processing_service
            
            print(f"🚀 啟動背景處理任務，檔案 IDs: {uploaded_file_ids}")
            
            background_tasks.add_task(
                process_files_in_background,
                uploaded_file_ids,
                task_id
            )
            task["status"] = "processing"
            task["message"] = "檔案上傳完成，開始處理中..."
    
    return {
        "success": True,
        "taskId": task_id,
        "message": f"成功上傳 {success_count} 個檔案" + (" (處理中...)" if should_process and success_count > 0 else "")
    }


async def process_files_in_background(file_ids: List[int], task_id: str):
    """背景任務：處理檔案"""
    from app.services.file_processor import file_processing_service
    from app.core.database import AsyncSessionLocal
    
    print(f"\n{'='*60}")
    print(f"🔄 背景處理開始")
    print(f"任務 ID: {task_id}")
    print(f"檔案 IDs: {file_ids}")
    print(f"{'='*60}\n")
    
    # 建立新的 DB session
    async with AsyncSessionLocal() as session:
        try:
            results = await file_processing_service.process_files_batch(
                file_ids=file_ids,
                task_id=task_id,
                db=session
            )
            
            print(f"\n{'='*60}")
            print(f"✅ 背景處理完成")
            print(f"成功: {results['success']}, 失敗: {results['failed']}")
            print(f"{'='*60}\n")
            
            # 更新任務狀態
            if task_id in upload_tasks:
                task = upload_tasks[task_id]
                task["processing_results"] = results
                task["status"] = "completed" if results["failed"] == 0 else "partial"
                task["updated_at"] = datetime.now().isoformat()
                
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ 背景處理失敗: {e}")
            print(f"{'='*60}\n")
            
            import traceback
            traceback.print_exc()
            
            if task_id in upload_tasks:
                task = upload_tasks[task_id]
                task["status"] = "failed"
                task["error"] = str(e)
                task["updated_at"] = datetime.now().isoformat()


@router.get("/progress/{task_id}", summary="查詢上傳進度")
async def get_upload_progress(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    查詢批次上傳的進度
    
    返回格式:
    {
      task_id: string,
      status: "processing" | "completed" | "failed" | "partial",
      total_files: number,
      completed_files: number,
      failed_files: number,
      progress: number (0-100),
      results: [{filename, success, error}]
    }
    """
    # 查找任務
    task = upload_tasks.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="上傳任務不存在"
        )
    
    # 權限檢查
    if task["user_id"] != current_user.id:
        from app.models.user import UserRole
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限查看此任務"
            )
    
    # 返回格式匹配前端期待
    return {
        "success": True,
        "data": {
            "taskId": task_id,
            "status": task["status"],
            "totalFiles": task["totalFiles"],
            "processedFiles": task["processedFiles"],
            "successFiles": task["successFiles"],
            "failedFiles": task["failedFiles"],
            "deletedFiles": task.get("deletedFiles", 0),
            "files": task["files"],
            "updatedAt": task["updated_at"]
        }
    }


@router.get("/tasks", summary="取得使用者的上傳任務列表")
async def get_user_upload_tasks(
    current_user: User = Depends(get_current_user)
):
    """
    取得當前使用者的所有上傳任務
    
    前端期望格式:
    {
      items: [{
        task_id: string,
        total_files: number,
        completed_files: number,
        status: string,
        created_at: string
      }]
    }
    """
    # 篩選使用者的任務
    user_tasks = [
        {
            "task_id": task_id,
            "total_files": task["total_files"],
            "completed_files": task["completed_files"],
            "failed_files": task["failed_files"],
            "status": task["status"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"]
        }
        for task_id, task in upload_tasks.items()
        if task["user_id"] == current_user.id
    ]
    
    # 按建立時間排序（最新的在前）
    user_tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "success": True,
        "items": user_tasks,
        "total": len(user_tasks)
    }


@router.delete("/tasks/{task_id}", summary="刪除上傳任務")
async def delete_upload_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    刪除指定的上傳任務記錄
    
    只能刪除已完成或失敗的任務
    """
    # 查找任務
    task = upload_tasks.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="上傳任務不存在"
        )
    
    # 權限檢查
    if task["user_id"] != current_user.id and current_user.role.value != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="無權限刪除此任務"
        )
    
    # 檢查任務狀態
    if task["status"] == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法刪除處理中的任務"
        )
    
    # 刪除任務
    del upload_tasks[task_id]
    
    return {
        "success": True,
        "message": "上傳任務已刪除"
    }


@router.post("/check-duplicates", summary="檢查檔案重複")
async def check_duplicates(
    request: CheckDuplicatesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    檢查檔案是否已存在並找出相關檔案
    
    前端期望格式:
    Request: { filenames: ["file1.pdf", "file2.docx"] }
    Response: {
      results: [
        {
          fileName: "file1.pdf",
          isDuplicate: true,
          duplicateFile: { id, name, size, uploadDate, category },
          relatedFiles: [],
          suggestReplace: true
        },
        {
          fileName: "file2.docx",
          isDuplicate: false,
          duplicateFile: null,
          relatedFiles: [{ id, name, size, uploadDate, category }],
          suggestReplace: false
        }
      ]
    }
    """
    from app.models import File as FileModel
    from sqlalchemy.orm import joinedload
    
    results = []
    
    for filename in request.filenames:
        # 檢查完全重複的檔案
        exact_match_query = select(FileModel).options(
            joinedload(FileModel.category)
        ).where(
            FileModel.department_id == current_user.department_id,
            FileModel.original_filename == filename
        )
        exact_match_result = await db.execute(exact_match_query)
        exact_match = exact_match_result.scalar_one_or_none()
        
        # 查找相關檔案（檔名相似但不完全相同）
        base_name = filename.rsplit('.', 1)[0]  # 去掉副檔名
        related_query = select(FileModel).options(
            joinedload(FileModel.category)
        ).where(
            FileModel.department_id == current_user.department_id,
            FileModel.original_filename.like(f"%{base_name}%"),
            FileModel.original_filename != filename
        ).limit(5)
        related_result = await db.execute(related_query)
        related_files = related_result.scalars().all()
        
        # 構建回應
        file_result = {
            "fileName": filename,
            "isDuplicate": exact_match is not None,
            "duplicateFile": None,
            "relatedFiles": [],
            "suggestReplace": exact_match is not None
        }
        
        if exact_match:
            file_result["duplicateFile"] = {
                "id": exact_match.id,
                "name": exact_match.original_filename,
                "size": f"{exact_match.file_size / 1024:.1f} KB" if exact_match.file_size else "未知",
                "uploadDate": exact_match.created_at.strftime("%Y-%m-%d %H:%M"),
                "category": exact_match.category.name if exact_match.category else "未分類"
            }
        
        for related_file in related_files:
            file_result["relatedFiles"].append({
                "id": related_file.id,
                "name": related_file.original_filename,
                "size": f"{related_file.file_size / 1024:.1f} KB" if related_file.file_size else "未知",
                "uploadDate": related_file.created_at.strftime("%Y-%m-%d %H:%M"),
                "category": related_file.category.name if related_file.category else "未分類"
            })
        
        results.append(file_result)
    
    return {
        "success": True,
        "results": results
    }
