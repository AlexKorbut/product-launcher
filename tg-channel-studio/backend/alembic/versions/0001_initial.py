"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-12

"""
from alembic import op

from app.db import Base
from app import models  # noqa: F401 — register tables on Base.metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First revision mirrors the ORM exactly; later revisions use explicit ops.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
