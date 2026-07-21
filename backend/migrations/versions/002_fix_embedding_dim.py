"""Fix embedding dimension 768→1024 for BGE-M3

Revision ID: 002
Revises: 001
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # noqa: F401


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 768 → 1024 for BGE-M3
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    op.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768)")
