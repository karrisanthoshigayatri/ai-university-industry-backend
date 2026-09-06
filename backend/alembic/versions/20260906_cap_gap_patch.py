"""Patch capability_gap and partner_match — add missing columns.

Revision ID: 20260906_cap_gap_patch
Revises: 20260906_projects
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_cap_gap_patch"
down_revision: Union[str, None] = "20260906_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tbl):
    return {c["name"] for c in inspect(conn).get_columns(tbl, schema="public")}


def _idxs(conn, tbl):
    return {i["name"] for i in inspect(conn).get_indexes(tbl, schema="public")}


def _add_idx(conn, name, tbl, col):
    if name not in _idxs(conn, tbl):
        op.create_index(name, tbl, [col])


def _add_ts(tbl, col, tz=True):
    op.add_column(tbl, sa.Column(col, sa.DateTime(timezone=tz), nullable=True))
    op.execute(text(f"UPDATE {tbl} SET {col} = NOW() WHERE {col} IS NULL"))
    op.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN {col} SET DEFAULT now(), ALTER COLUMN {col} SET NOT NULL"))


def upgrade():
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # capability_gap — add created_at / updated_at + indexes
    if "capability_gap" in existing:
        cols = _cols(conn, "capability_gap")
        if "created_at" not in cols: _add_ts("capability_gap", "created_at")
        if "updated_at" not in cols: _add_ts("capability_gap", "updated_at")
        _add_idx(conn, "ix_cap_gap_project_id", "capability_gap", "project_id")
        _add_idx(conn, "ix_cap_gap_capability_id", "capability_gap", "capability_id")
    else:
        op.create_table(
            "capability_gap",
            sa.Column("gap_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("required_level", sa.Numeric(5, 2), nullable=True),
            sa.Column("available_level", sa.Numeric(5, 2), nullable=True),
            sa.Column("gap_level", sa.Numeric(5, 2), nullable=True),
            sa.Column("criticality", sa.Numeric(5, 2), nullable=True),
            sa.Column("recommended_support", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="Open"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("gap_id"),
        )
        op.create_index("ix_cap_gap_project_id", "capability_gap", ["project_id"])
        op.create_index("ix_cap_gap_capability_id", "capability_gap", ["capability_id"])

    # partner_match — add created_at + indexes
    if "partner_match" in existing:
        cols = _cols(conn, "partner_match")
        if "created_at" not in cols: _add_ts("partner_match", "created_at")
        _add_idx(conn, "ix_partner_match_project_id", "partner_match", "project_id")
        _add_idx(conn, "ix_partner_match_partner_id", "partner_match", "partner_id")
    else:
        op.create_table(
            "partner_match",
            sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("match_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("matched_capabilities", postgresql.JSONB(), nullable=True),
            sa.Column("matched_support", postgresql.JSONB(), nullable=True),
            sa.Column("unmet_requirements", postgresql.JSONB(), nullable=True),
            sa.Column("constraint_results", postgresql.JSONB(), nullable=True),
            sa.Column("reasons", postgresql.JSONB(), nullable=True),
            sa.Column("model_version", sa.Text(), nullable=True),
            sa.Column("decision_status", sa.Text(), nullable=True),
            sa.Column("generated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["partner_id"], ["partner_profile.partner_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("match_id"),
        )
        op.create_index("ix_partner_match_project_id", "partner_match", ["project_id"])
        op.create_index("ix_partner_match_partner_id", "partner_match", ["partner_id"])


def downgrade():
    pass
