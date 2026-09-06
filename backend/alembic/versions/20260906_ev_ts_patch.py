"""Add created_at / updated_at to capability_evidence and availability tables.

These tables existed in Supabase without timestamp columns. This migration
adds them non-destructively — existing rows get NOW() backfilled.

Revision ID: 20260906_ev_ts_patch
Revises: 20260906_ev_avail_constraint
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20260906_ev_ts_patch"
down_revision: Union[str, None] = "20260906_ev_avail_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _add_ts(table: str, col: str) -> None:
    """Add a timestamptz column, backfill with NOW(), then set NOT NULL + default."""
    op.add_column(table, sa.Column(col, sa.DateTime(timezone=True), nullable=True))
    op.execute(text(f"UPDATE {table} SET {col} = NOW() WHERE {col} IS NULL"))
    op.execute(
        text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {col} SET DEFAULT now(), "
            f"ALTER COLUMN {col} SET NOT NULL"
        )
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ── capability_evidence ────────────────────────────────────────────────────
    ev_cols = _cols(conn, "capability_evidence")
    if "created_at" not in ev_cols:
        _add_ts("capability_evidence", "created_at")
    if "updated_at" not in ev_cols:
        _add_ts("capability_evidence", "updated_at")

    # ── availability ───────────────────────────────────────────────────────────
    av_cols = _cols(conn, "availability")
    if "created_at" not in av_cols:
        _add_ts("availability", "created_at")
    if "updated_at" not in av_cols:
        _add_ts("availability", "updated_at")


def downgrade() -> None:
    conn = op.get_bind()
    ev_cols = _cols(conn, "capability_evidence")
    if "updated_at" in ev_cols:
        op.drop_column("capability_evidence", "updated_at")
    if "created_at" in ev_cols:
        op.drop_column("capability_evidence", "created_at")
    av_cols = _cols(conn, "availability")
    if "updated_at" in av_cols:
        op.drop_column("availability", "updated_at")
    if "created_at" in av_cols:
        op.drop_column("availability", "created_at")
