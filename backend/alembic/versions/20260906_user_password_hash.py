"""Add password hashes to existing users.

Revision ID: 20260906_user_password_hash
Revises: 20260906_government_profile
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260906_user_password_hash"
down_revision: Union[str, None] = "20260906_government_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a nullable hash column so existing users remain valid."""

    op.add_column("user", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove only the password hash column."""

    op.drop_column("user", "password_hash")