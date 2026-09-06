"""Patch HEI tables to add columns required by the SQLAlchemy models.

The Supabase schema was created with a different column set than the models
expect.  This migration adds only the missing columns — it does NOT drop or
rename any existing columns, so it is fully backwards-compatible.

Revision ID: 20260906_hei_schema_patch
Revises: 20260906_hei_registry
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_hei_schema_patch"
down_revision: Union[str, None] = "20260906_hei_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def upgrade() -> None:
    conn = op.get_bind()

    # ── hei_profile ────────────────────────────────────────────────────────────
    hp_cols = _cols(conn, "hei_profile")
    if "accreditation" not in hp_cols:
        op.add_column("hei_profile", sa.Column("accreditation", sa.Text(), nullable=True))
    if "website" not in hp_cols:
        op.add_column("hei_profile", sa.Column("website", sa.String(500), nullable=True))
    if "contact_details" not in hp_cols:
        op.add_column("hei_profile", sa.Column("contact_details", postgresql.JSONB(), nullable=True))

    # ── faculty_expert_profile ─────────────────────────────────────────────────
    fp_cols = _cols(conn, "faculty_expert_profile")
    if "specialization" not in fp_cols:
        op.add_column(
            "faculty_expert_profile",
            sa.Column("specialization", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    fp_cols = _cols(conn, "faculty_expert_profile")
    if "specialization" in fp_cols:
        op.drop_column("faculty_expert_profile", "specialization")

    hp_cols = _cols(conn, "hei_profile")
    if "contact_details" in hp_cols:
        op.drop_column("hei_profile", "contact_details")
    if "website" in hp_cols:
        op.drop_column("hei_profile", "website")
    if "accreditation" in hp_cols:
        op.drop_column("hei_profile", "accreditation")
