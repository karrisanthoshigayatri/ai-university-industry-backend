"""Create organization and user tables.

Revision ID: 20260906_organization_user
Revises:
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision: str = "20260906_organization_user"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create only the organization and user tables."""

    connection = op.get_bind()
    existing_tables = set(inspect(connection).get_table_names(schema="public"))

    organization_created = "organization" not in existing_tables
    if organization_created:
        op.create_table(
            "organization",
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("organization_type", sa.String(length=50), nullable=False),
            sa.Column("official_identifier", sa.String(length=150), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("district", sa.String(length=100), nullable=True),
            sa.Column("state", sa.String(length=100), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("contact_details", postgresql.JSONB(), nullable=True),
            sa.Column("website", sa.String(length=500), nullable=True),
            sa.Column("verification_status", sa.String(length=30), server_default="Pending", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "organization_type IN ('Government', 'PRI', 'ULB', 'HEI', 'Industry', 'MSME', 'Startup', 'Research Institution', 'CSR Organization')",
                name="ck_organization_type",
            ),
            sa.PrimaryKeyConstraint("organization_id"),
            sa.UniqueConstraint("official_identifier", name="uq_organization_official_identifier"),
        )

    existing_indexes = {
        index["name"] for index in inspect(connection).get_indexes("organization")
    }
    if not organization_created and "uq_organization_official_identifier" not in existing_indexes:
        op.create_index(
            "uq_organization_official_identifier",
            "organization",
            ["official_identifier"],
            unique=True,
        )
    for index_name, columns in (
        ("ix_organization_name", ["name"]),
        ("ix_organization_type", ["organization_type"]),
        ("ix_organization_location", ["state", "district"]),
    ):
        if index_name not in existing_indexes:
            op.create_index(index_name, "organization", columns)

    if "user" not in existing_tables:
        op.create_table(
            "user",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "role IN ('Citizen', 'Government Officer', 'HEI Administrator', 'Faculty / Expert', 'Student', 'Industry / MSME / Startup', 'Research Institution', 'CSR Organization', 'System Administrator')",
                name="ck_user_role",
            ),
            sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_user_status"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organization.organization_id"],
                name="fk_user_organization_id",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("user_id"),
            sa.UniqueConstraint("email", name="uq_user_email"),
        )
        op.create_index("ix_user_organization_id", "user", ["organization_id"])
        op.create_index("ix_user_role", "user", ["role"])
        op.create_index("ix_user_status", "user", ["status"])


def downgrade() -> None:
    """Remove only the tables created by this revision."""

    op.drop_index("ix_user_status", table_name="user")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_index("ix_user_organization_id", table_name="user")
    op.drop_table("user")
    op.drop_index("ix_organization_location", table_name="organization")
    op.drop_index("ix_organization_type", table_name="organization")
    op.drop_index("ix_organization_name", table_name="organization")
    op.drop_table("organization")