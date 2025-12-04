"""公開 API 路由（無需認證）"""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="", tags=["公開 API"])


@router.get("/faq/list")
async def get_faq_list(db: AsyncSession = Depends(get_db)):
    """
    獲取常見問題列表（公開端點）
    
    返回常見問題和解答
    """
    # TODO: 從資料庫獲取 FAQ
    # 目前返回範例資料
    faq_list = [
        {
            "id": 1,
            "category": "基本操作",
            "question": "如何上傳文件？",
            "answer": "請點擊上傳按鈕，選擇您的文件，系統支援 PDF、Word 和 TXT 格式。",
            "order": 1
        },
        {
            "id": 2,
            "category": "基本操作",
            "question": "如何進行查詢？",
            "answer": "在搜尋框中輸入您的問題，系統會自動搜尋相關文檔並提供答案。",
            "order": 2
        },
        {
            "id": 3,
            "category": "系統功能",
            "question": "系統支援哪些文件格式？",
            "answer": "系統支援 PDF、Word（.docx）和純文字（.txt）格式的文件。",
            "order": 3
        },
        {
            "id": 4,
            "category": "系統功能",
            "question": "如何查看歷史查詢？",
            "answer": "登入後，您可以在「歷史記錄」頁面查看過去的查詢記錄。",
            "order": 4
        }
    ]
    
    return {
        "success": True,
        "data": faq_list
    }


@router.get("/questions/quick")
async def get_quick_questions(db: AsyncSession = Depends(get_db)):
    """
    獲取快速問題列表（公開端點）
    
    返回常用的快速問題範例
    """
    # TODO: 從資料庫獲取快速問題，可以根據處室過濾
    quick_questions = [
        {
            "id": 1,
            "question": "請假規定是什麼？",
            "category": "人事",
            "icon": "📋"
        },
        {
            "id": 2,
            "question": "如何申請加班費？",
            "category": "人事",
            "icon": "💰"
        },
        {
            "id": 3,
            "question": "年假天數如何計算？",
            "category": "人事",
            "icon": "📅"
        },
        {
            "id": 4,
            "question": "出差申請流程？",
            "category": "人事",
            "icon": "✈️"
        }
    ]
    
    return {
        "success": True,
        "data": quick_questions
    }


@router.get("/public/info")
async def get_public_system_info():
    """
    獲取公開系統資訊（無需認證）
    
    返回系統基本資訊和歡迎訊息
    """
    return {
        "success": True,
        "data": {
            "app_name": "RAG 知識庫查詢系統",
            "version": "1.0.0",
            "description": "基於 RAG 技術的智能問答系統",
            "welcome_message": "歡迎使用 RAG 知識庫查詢系統！您可以在這裡查詢相關文檔和資訊。",
            "features": [
                "智能文檔搜尋",
                "自然語言問答",
                "多處室資料管理",
                "查詢歷史記錄"
            ],
            "support_email": "support@ncku.edu.tw",
            "support_phone": "(06) 275-7575"
        }
    }


@router.get("/public/files/{file_id}/download")
async def download_file_public(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    公開下載端點（無需認證）
    
    用於 RAG 查詢結果的檔案下載
    """
    from app.models.file import File as FileModel
    
    # 取得檔案記錄
    file = await db.get(FileModel, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 構建 processed/data 路徑
    file_path = f"uploads/{file.department_id}/processed/data/{file.filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="檔案實體不存在")
    
    # 返回檔案（使用原始檔名）
    # 注意：公開下載不記錄活動，因為 activities 表的 user_id 是必填
    return FileResponse(
        path=file_path,
        filename=file.original_filename,
        media_type=file.mime_type or "application/octet-stream"
    )


@router.get("/public/welcome")
async def get_welcome_message():
    """
    獲取歡迎訊息（公開端點，無需認證）
    """
    return {
        "success": True,
        "data": {
            "title": "歡迎使用 RAG 知識庫查詢系統",
            "message": "您好！我是 AI 助手 👋\n\n我可以協助您查詢相關文檔和資訊。請問有什麼我可以幫助您的嗎？",
            "tips": [
                "盡量使用完整的問句",
                "可以參考右側的常見問題",
                "點擊快速問題快速開始"
            ]
        }
    }
