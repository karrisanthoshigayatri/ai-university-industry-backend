"""Patch impact_record, beneficiary — add created_at/updated_at + indexes.

Revision ID: 20260906_impact_patch
Revises: 20260906_ms_patch
Create Date: 2026-09-06
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20260906_impact_patch"
down_revision: Union[str, None] = "20260906_ms_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tbl): return {c["name"] for c in inspect(conn).get_columns(tbl, schema="public")}
def _idxs(conn, tbl): return {i["name"] for i in inspect(conn).get_indexes(tbl, schema="public")}
def _add_idx(conn, name, tbl, col):
    if name not in _idxs(conn, tbl): op.create_index(name, tbl, [col])
def _add_ts(tbl, col, tz=True):
    op.add_column(tbl, sa.Column(col, sa.DateTime(timezone=tz), nullable=True))
    op.execute(text(f"UPDATE {tbl} SET {col}=NOW() WHERE {col} IS NULL"))
    op.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN {col} SET DEFAULT now(), ALTER COLUMN {col} SET NOT NULL"))


def upgrade():
    conn = op.get_bind()
    for tbl in ["impact_record", "beneficiary"]:
        cols = _cols(conn, tbl)
        if "created_at" not in cols: _add_ts(tbl, "created_at")
        if "updated_at" not in cols: _add_ts(tbl, "updated_at")
    _add_idx(conn, "ix_impact_project_id", "impact_record", "project_id")
    _add_idx(conn, "ix_beneficiary_project_id", "beneficiary", "project_id")
    _add_idx(conn, "ix_notification_recipient_id", "notification", "recipient_id")
    _add_idx(conn, "ix_notification_status", "notification", "status")
    _add_idx(conn, "ix_audit_entity_id", "audit_log", "entity_id")
    _add_idx(conn, "ix_feedback_project_id", "feedback", "project_id")


def downgrade():
    pass
