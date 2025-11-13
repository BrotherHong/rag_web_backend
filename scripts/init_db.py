"""資料庫預設資料初始化腳本

執行方式：
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Department, User, Category, UserRole
from app.core.security import get_password_hash


async def init_departments(session: AsyncSession):
    """初始化預設處室"""
    print("🏢 正在初始化處室...")
    
    departments_data = [
        {"name": "人事室", "description": "負責人事管理、招聘、培訓等業務"},
        {"name": "會計室", "description": "負責財務管理、預算編制、會計核算等業務"},
        {"name": "總務處", "description": "負責行政總務、資產管理、採購等業務"},
    ]
    
    created_count = 0
    for dept_data in departments_data:
        # 檢查是否已存在
        result = await session.execute(
            select(Department).where(Department.name == dept_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⏭️  處室 '{dept_data['name']}' 已存在，跳過")
        else:
            dept = Department(**dept_data)
            session.add(dept)
            created_count += 1
            print(f"  ✅ 建立處室: {dept_data['name']}")
    
    await session.commit()
    print(f"✨ 處室初始化完成！建立 {created_count} 個處室\n")


async def init_categories(session: AsyncSession):
    """初始化預設分類"""
    print("📁 正在初始化分類...")
    
    categories_data = [
        {"name": "政策法規", "description": "各類政策文件、法規條例"},
        {"name": "操作手冊", "description": "系統操作指南、使用手冊"},
        {"name": "會議記錄", "description": "各類會議紀錄、決議事項"},
        {"name": "財務報表", "description": "財務報告、預算表、決算書"},
        {"name": "人事資料", "description": "員工資料、考勤記錄、薪資表"},
        {"name": "採購文件", "description": "採購申請、合約、驗收單"},
        {"name": "其他", "description": "其他未分類文件"},
    ]
    
    created_count = 0
    for cat_data in categories_data:
        # 檢查是否已存在
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⏭️  分類 '{cat_data['name']}' 已存在，跳過")
        else:
            category = Category(**cat_data)
            session.add(category)
            created_count += 1
            print(f"  ✅ 建立分類: {cat_data['name']}")
    
    await session.commit()
    print(f"✨ 分類初始化完成！建立 {created_count} 個分類\n")


async def init_admin_users(session: AsyncSession):
    """初始化管理員帳號"""
    print("👤 正在初始化管理員帳號...")
    
    # 取得人事室（預設管理員所屬處室）
    result = await session.execute(
        select(Department).where(Department.name == "人事室")
    )
    hr_dept = result.scalar_one_or_none()
    
    if not hr_dept:
        print("  ❌ 錯誤：找不到人事室，請先執行處室初始化")
        return
    
    # 建立超級管理員
    admin_data = {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "系統管理員",
        "hashed_password": get_password_hash("admin123"),  # 預設密碼
        "role": UserRole.ADMIN,
        "is_active": True,
        "department_id": hr_dept.id,
    }
    
    # 檢查是否已存在
    result = await session.execute(
        select(User).where(User.username == admin_data["username"])
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"  ⏭️  管理員 '{admin_data['username']}' 已存在，跳過")
    else:
        admin = User(**admin_data)
        session.add(admin)
        await session.commit()
        print(f"  ✅ 建立管理員: {admin_data['username']}")
        print(f"     📧 Email: {admin_data['email']}")
        print(f"     🔑 密碼: admin123 (請登入後立即修改)")
    
    print(f"✨ 管理員初始化完成！\n")


async def main():
    """執行所有初始化"""
    print("=" * 60)
    print("🚀 RAG 知識庫系統 - 資料庫初始化")
    print("=" * 60)
    print()
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 初始化處室
            await init_departments(session)
            
            # 2. 初始化分類
            await init_categories(session)
            
            # 3. 初始化管理員
            await init_admin_users(session)
            
            print("=" * 60)
            print("🎉 資料庫初始化完成！")
            print("=" * 60)
            print()
            print("📝 預設管理員帳號資訊：")
            print("   帳號：admin")
            print("   密碼：admin123")
            print("   ⚠️  請登入後立即修改密碼！")
            print()
            
        except Exception as e:
            print(f"\n❌ 初始化失敗：{e}")
            raise


if __name__ == "__main__":
    # Windows 平台修正
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
