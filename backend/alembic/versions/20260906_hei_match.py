"""Patch hei_match table — add missing created_at column.

The hei_match table already exists in Supabase. This migration adds the
created_at column (timestamptz) required by the HeiMatch model.

Revision ID: 20260906_hei_match
Revises: 20260906_partner_registry
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_hei_match"
down_revision: Union[str, None] = "20260906_partner_registry"
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

    if "hei_match" not in existing:
        op.create_table(
            "hei_match",
            sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("match_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("matched_capabilities", postgresql.JSONB(), nullable=True),
            sa.Column("unmet_requirements", postgresql.JSONB(), nullable=True),
            sa.Column("constraint_results", postgresql.JSONB(), nullable=True),
            sa.Column("reasons", postgresql.JSONB(), nullable=True),
            sa.Column("model_version", sa.Text(), nullable=True),
            sa.Column("decision_status", sa.Text(), nullable=True),
            sa.Column("generated_at", sa.DateTime(timezone=False),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"],
                                    name="fk_hei_match_problem", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"],
                                    name="fk_hei_match_hei", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("match_id"),
        )
        op.create_index("ix_hei_match_problem_id", "hei_match", ["problem_id"])
        op.create_index("ix_hei_match_hei_id", "hei_match", ["hei_id"])
    else:
        cols = _cols(conn, "hei_match")
        if "created_at" not in cols:
            op.add_column("hei_match",
                          sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
            op.execute(text("UPDATE hei_match SET created_at = NOW() WHERE created_at IS NULL"))
            op.execute(text(
                "ALTER TABLE hei_match "
                "ALTER COLUMN created_at SET DEFAULT now(), "
                "ALTER COLUMN created_at SET NOT NULL"
            ))
        _add_idx(conn, "ix_hei_match_problem_id", "hei_match", "problem_id")
        _add_idx(conn, "ix_hei_match_hei_id", "hei_match", "hei_id")


def downgrade() -> None:
    pass
