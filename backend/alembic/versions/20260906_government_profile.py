"""Create the government_profile table.

Revision ID: 20260906_government_profile
Revises: 20260906_organization_user
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260906_government_profile"
down_revision: Union[str, None] = "20260906_organization_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create only the government_profile table."""

    op.create_table(
        "government_profile",
        sa.Column("government_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_name", sa.String(length=255), nullable=False),
        sa.Column("administrative_level", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column("nodal_officer", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=150), nullable=False),
        sa.Column("contact_details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.organization_id"],
            name="fk_government_profile_organization_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("government_id"),
        sa.UniqueConstraint("organization_id", name="uq_government_profile_organization_id"),
    )
    op.create_index(
        "ix_government_profile_administrative_level",
        "government_profile",
        ["administrative_level"],
    )
    op.create_index(
        "ix_government_profile_jurisdiction",
        "government_profile",
        ["jurisdiction"],
    )


def downgrade() -> None:
    """Remove only the government_profile table."""

    op.drop_index(
        "ix_government_profile_jurisdiction", table_name="government_profile"
    )
    op.drop_index(
        "ix_government_profile_administrative_level", table_name="government_profile"
    )
    op.drop_table("government_profile")