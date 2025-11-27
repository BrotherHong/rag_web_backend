"""add_slug_to_departments

Revision ID: ea34120c12e0
Revises: 20251119_add_dept
Create Date: 2025-11-27 14:02:46.318799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea34120c12e0'
down_revision: Union[str, Sequence[str], None] = '20251119_add_dept'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 slug 欄位
    op.add_column('departments', sa.Column('slug', sa.String(50), nullable=True))
    
    # 為現有處室設定 slug 值
    op.execute("UPDATE departments SET slug = 'hr' WHERE name = '人事室'")
    op.execute("UPDATE departments SET slug = 'acc' WHERE name = '會計室'")
    op.execute("UPDATE departments SET slug = 'ga' WHERE name = '總務處'")
    
    # 設定 NOT NULL 約束
    op.alter_column('departments', 'slug', nullable=False)
    
    # 添加唯一索引
    op.create_index('ix_departments_slug', 'departments', ['slug'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # 移除索引和欄位
    op.drop_index('ix_departments_slug', table_name='departments')
    op.drop_column('departments', 'slug')
