"""Patch faculty_resource_match — add missing columns.

The table already exists in Supabase. This migration adds:
  match_type, unmet_requirements, constraint_results, created_at

Revision ID: 20260906_fr_match
Revises: 20260906_hei_match
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_fr_match"
down_revision: Union[str, None] = "20260906_hei_match"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))
    tbl = "faculty_resource_match"

    if tbl not in existing:
        op.create_table(
            tbl,
            sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("faculty_expert_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("match_type", sa.String(20), nullable=True),
            sa.Column("match_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("matched_capabilities", postgresql.JSONB(), nullable=True),
            sa.Column("unmet_requirements", postgresql.JSONB(), nullable=True),
            sa.Column("constraint_results", postgresql.JSONB(), nullable=True),
            sa.Column("reasons", postgresql.JSONB(), nullable=True),
            sa.Column("model_version", sa.Text(), nullable=True),
            sa.Column("generated_at", sa.DateTime(timezone=False),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"],
                                    ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"],
                                    ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["faculty_expert_id"],
                                    ["faculty_expert_profile.faculty_expert_id"],
                                    ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["resource_id"],
                                    ["institutional_resource.resource_id"],
                                    ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("match_id"),
        )
        op.create_index("ix_fr_match_problem_id", tbl, ["problem_id"])
        op.create_index("ix_fr_match_hei_id", tbl, ["hei_id"])
    else:
        cols = _cols(conn, tbl)
        if "match_type" not in cols:
            op.add_column(tbl, sa.Column("match_type", sa.String(20), nullable=True))
        if "unmet_requirements" not in cols:
            op.add_column(tbl, sa.Column("unmet_requirements", postgresql.JSONB(), nullable=True))
        if "constraint_results" not in cols:
            op.add_column(tbl, sa.Column("constraint_results", postgresql.JSONB(), nullable=True))
        if "created_at" not in cols:
            op.add_column(tbl, sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
            op.execute(text(f"UPDATE {tbl} SET created_at = NOW() WHERE created_at IS NULL"))
            op.execute(text(
                f"ALTER TABLE {tbl} "
                f"ALTER COLUMN created_at SET DEFAULT now(), "
                f"ALTER COLUMN created_at SET NOT NULL"
            ))
        _add_idx(conn, "ix_fr_match_problem_id", tbl, "problem_id")
        _add_idx(conn, "ix_fr_match_hei_id", tbl, "hei_id")


def downgrade() -> None:
    pass
