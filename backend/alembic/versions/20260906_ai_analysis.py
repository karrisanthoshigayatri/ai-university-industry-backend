"""Create or patch AI analysis tables.

All four tables already exist in Supabase with slightly different types
(NUMERIC instead of FLOAT, no timezone on timestamps).
This migration adds missing columns, fixes types, and adds missing indexes/constraints.

Revision ID: 20260906_ai_analysis
Revises: 20260906_validation
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "20260906_ai_analysis"
down_revision: Union[str, None] = "20260906_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def _fix_ts(table: str, col: str) -> None:
    """Cast a TIMESTAMP column to TIMESTAMP WITH TIME ZONE."""
    op.execute(
        text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {col} AT TIME ZONE 'UTC'"
        )
    )


def _fix_numeric_to_float(table: str, col: str) -> None:
    op.execute(
        text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {col} TYPE FLOAT "
            f"USING {col}::FLOAT"
        )
    )


def _add_check(conn, table: str, name: str, expr: str) -> None:
    result = conn.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
            "WHERE pg_class.relname = :tbl "
            "AND pg_class.relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public') "
            "AND conname = :cname"
        ),
        {"tbl": table, "cname": name},
    ).fetchone()
    if result is None:
        op.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})"))


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # ── problem_category ──────────────────────────────────────────────────────
    if "problem_category" not in existing:
        op.create_table(
            "problem_category",
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category_role", sa.String(20), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("model_version", sa.String(100), nullable=False, server_default="qwen2.5"),
            sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("category_role IN ('Primary','Secondary')", name="ck_problem_category_role"),
            sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_problem_category_confidence"),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"], name="fk_cat_problem", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], name="fk_cat_capability", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("category_id"),
        )
        op.create_index("ix_problem_category_problem_id", "problem_category", ["problem_id"])
        op.create_index("ix_problem_category_capability_id", "problem_category", ["capability_id"])
    else:
        _fix_ts("problem_category", "generated_at")
        _fix_numeric_to_float("problem_category", "confidence")
        _add_check(conn, "problem_category", "ck_problem_category_role", "category_role IN ('Primary','Secondary')")
        _add_check(conn, "problem_category", "ck_problem_category_confidence", "confidence >= 0 AND confidence <= 1")
        _add_idx(conn, "ix_problem_category_problem_id",    "problem_category", "problem_id")
        _add_idx(conn, "ix_problem_category_capability_id", "problem_category", "capability_id")

    # ── problem_priority ──────────────────────────────────────────────────────
    if "problem_priority" not in existing:
        op.create_table(
            "problem_priority",
            sa.Column("priority_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("priority_level", sa.String(20), nullable=False),
            sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("severity_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("urgency_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("affected_population", sa.BigInteger(), nullable=True),
            sa.Column("geographic_spread", sa.Float(), nullable=True),
            sa.Column("feasibility_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("strategic_relevance", sa.Float(), nullable=False, server_default="0"),
            sa.Column("factors", postgresql.JSONB(), nullable=True),
            sa.Column("model_version", sa.String(100), nullable=False, server_default="qwen2.5"),
            sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("priority_level IN ('Low','Medium','High','Critical')", name="ck_problem_priority_level"),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"], name="fk_pri_problem", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("priority_id"),
        )
        op.create_index("ix_problem_priority_problem_id", "problem_priority", ["problem_id"])
        op.create_index("ix_problem_priority_level",      "problem_priority", ["priority_level"])
    else:
        _fix_ts("problem_priority", "generated_at")
        for col in ("priority_score","severity_score","urgency_score","geographic_spread","feasibility_score","strategic_relevance"):
            _fix_numeric_to_float("problem_priority", col)
        _add_check(conn, "problem_priority", "ck_problem_priority_level", "priority_level IN ('Low','Medium','High','Critical')")
        _add_idx(conn, "ix_problem_priority_problem_id", "problem_priority", "problem_id")
        _add_idx(conn, "ix_problem_priority_level",      "problem_priority", "priority_level")

    # ── problem_requirement_profile ───────────────────────────────────────────
    if "problem_requirement_profile" not in existing:
        op.create_table(
            "problem_requirement_profile",
            sa.Column("requirement_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("required_support", sa.Text(), nullable=True),
            sa.Column("geographic_requirements", sa.Text(), nullable=True),
            sa.Column("eligibility_requirements", sa.Text(), nullable=True),
            sa.Column("timeline", sa.Text(), nullable=True),
            sa.Column("constraints", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("model_version", sa.String(100), nullable=False, server_default="qwen2.5"),
            sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_req_profile_confidence"),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"], name="fk_req_profile_problem", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("requirement_profile_id"),
        )
        op.create_index("ix_req_profile_problem_id", "problem_requirement_profile", ["problem_id"])
    else:
        _fix_ts("problem_requirement_profile", "generated_at")
        _fix_numeric_to_float("problem_requirement_profile", "confidence")
        _add_check(conn, "problem_requirement_profile", "ck_req_profile_confidence", "confidence >= 0 AND confidence <= 1")
        _add_idx(conn, "ix_req_profile_problem_id", "problem_requirement_profile", "problem_id")

    # ── problem_requirement_capability ────────────────────────────────────────
    if "problem_requirement_capability" not in existing:
        op.create_table(
            "problem_requirement_capability",
            sa.Column("requirement_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("requirement_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("requirement_type", sa.String(30), nullable=False),
            sa.Column("required_level", sa.Float(), nullable=True),
            sa.Column("criticality", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.CheckConstraint(
                "requirement_type IN ('Domain','Skill','Expertise','Technology','Resource','Support Capability')",
                name="ck_req_capability_type",
            ),
            sa.ForeignKeyConstraint(["requirement_profile_id"], ["problem_requirement_profile.requirement_profile_id"],
                                    name="fk_req_cap_profile", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"],
                                    name="fk_req_cap_capability", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("requirement_capability_id"),
        )
        op.create_index("ix_req_capability_profile_id",    "problem_requirement_capability", ["requirement_profile_id"])
        op.create_index("ix_req_capability_capability_id", "problem_requirement_capability", ["capability_id"])
    else:
        for col in ("required_level","criticality","confidence"):
            _fix_numeric_to_float("problem_requirement_capability", col)
        _add_check(conn, "problem_requirement_capability", "ck_req_capability_type",
                   "requirement_type IN ('Domain','Skill','Expertise','Technology','Resource','Support Capability')")
        _add_idx(conn, "ix_req_capability_profile_id",    "problem_requirement_capability", "requirement_profile_id")
        _add_idx(conn, "ix_req_capability_capability_id", "problem_requirement_capability", "capability_id")


def downgrade() -> None:
    for t in ["problem_requirement_capability","problem_requirement_profile","problem_priority","problem_category"]:
        op.drop_table(t)
