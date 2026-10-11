"""Initial schema for Belief Stress Test

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-11 22:50:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.database import Base
import app.models  # noqa: F401

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # Ensure questions.status column exists if upgrading from an older table revision
    inspector = inspect(bind)
    if "questions" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("questions")]
        if "status" not in cols:
            op.add_column(
                "questions",
                sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
