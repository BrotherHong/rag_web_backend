"""
資料模型單元測試
測試 SQLAlchemy 模型的基本功能
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models import User, Department, File, Category, SystemSetting


@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """使用者模型測試"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session, test_department):
        """測試創建使用者"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            role="user",
            department_id=test_department.id,
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.created_at is not None
    
    @pytest.mark.asyncio
    async def test_user_department_relationship(self, db_session, test_department):
        """測試使用者與處室的關聯"""
        user = User(
            username="deptuser",
            email="dept@example.com",
            hashed_password="hashed_password",
            full_name="Department User",
            role="user",
            department_id=test_department.id,
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 載入關聯
        result = await db_session.execute(
            select(User).where(User.id == user.id)
        )
        user_with_dept = result.scalar_one()
        await db_session.refresh(user_with_dept, ["department"])
        
        assert user_with_dept.department is not None
        assert user_with_dept.department.name == "測試處室"


@pytest.mark.unit
@pytest.mark.database
class TestDepartmentModel:
    """處室模型測試"""
    
    @pytest.mark.asyncio
    async def test_create_department(self, db_session):
        """測試創建處室"""
        dept = Department(
            name="IT部門",
            description="資訊技術部門",
        )
        
        db_session.add(dept)
        await db_session.commit()
        await db_session.refresh(dept)
        
        assert dept.id is not None
        assert dept.name == "IT部門"
        assert dept.created_at is not None


@pytest.mark.unit
@pytest.mark.database
class TestFileModel:
    """檔案模型測試"""
    
    @pytest.mark.asyncio
    async def test_create_file(self, db_session, test_admin_user, test_department):
        """測試創建檔案記錄"""
        file = File(
            filename="test.pdf",
            original_filename="測試文件.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf",
            uploader_id=test_admin_user.id,
            department_id=test_department.id,
            status="pending",
        )
        
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)
        
        assert file.id is not None
        assert file.filename == "test.pdf"
        assert file.status == "pending"
        assert file.created_at is not None


@pytest.mark.unit
@pytest.mark.database
class TestCategoryModel:
    """分類模型測試"""
    
    @pytest.mark.asyncio
    async def test_create_category(self, db_session, test_department):
        """測試創建分類"""
        category = Category(
            name="技術文件",
            description="技術相關文件分類",
            department_id=test_department.id,
        )
        
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        assert category.id is not None
        assert category.name == "技術文件"
        assert category.created_at is not None


@pytest.mark.unit
@pytest.mark.database
class TestSystemSettingModel:
    """系統設定模型測試"""
    
    @pytest.mark.asyncio
    async def test_create_setting(self, db_session):
        """測試創建系統設定"""
        setting = SystemSetting(
            key="test.setting",
            value={"test": "value", "number": 123},
            category="app",
            display_name="測試設定",
            description="測試設定",
            is_public=True,
            is_sensitive=False,
        )
        
        db_session.add(setting)
        await db_session.commit()
        await db_session.refresh(setting)
        
        assert setting.id is not None
        assert setting.key == "test.setting"
        assert setting.value == {"test": "value", "number": 123}
        assert setting.is_public is True
    
    @pytest.mark.asyncio
    async def test_setting_json_value(self, db_session):
        """測試 JSON 值的存儲和讀取"""
        complex_value = {
            "string": "text",
            "number": 42,
            "boolean": True,
            "array": [1, 2, 3],
            "nested": {
                "key": "value",
            },
        }
        
        setting = SystemSetting(
            key="test.complex",
            value=complex_value,
            category="app",
            display_name="複雜 JSON",
            description="複雜 JSON 設定",
        )
        
        db_session.add(setting)
        await db_session.commit()
        await db_session.refresh(setting)
        
        assert setting.value == complex_value
        assert setting.value["nested"]["key"] == "value"
