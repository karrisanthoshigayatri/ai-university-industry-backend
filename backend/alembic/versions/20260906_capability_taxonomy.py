"""Create or patch capability_taxonomy and capability tables.

Both tables already exist in Supabase. This migration adds missing indexes,
CHECK constraints, and UNIQUE constraints so the SQLAlchemy model and the DB
are fully in sync.

Revision ID: 20260906_capability_taxonomy
Revises: 20260906_fix_ai_nullable
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "20260906_capability_taxonomy"
down_revision: Union[str, None] = "20260906_fix_ai_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _has_constraint(conn, table: str, name: str) -> bool:
    row = conn.execute(
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
    return row is not None


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # ── capability_taxonomy ───────────────────────────────────────────────────
    if "capability_taxonomy" not in existing:
        op.create_table(
            "capability_taxonomy",
            sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("type", sa.String(100), nullable=False),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("synonyms", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("version", sa.String(50), nullable=True),
            sa.Column("active_status", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["capability_taxonomy.taxonomy_id"],
                name="fk_taxonomy_parent", ondelete="SET NULL",
            ),
            sa.UniqueConstraint("name", name="uq_capability_taxonomy_name"),
            sa.PrimaryKeyConstraint("taxonomy_id"),
        )
        op.create_index("ix_capability_taxonomy_parent_id", "capability_taxonomy", ["parent_id"])
        op.create_index("ix_capability_taxonomy_active",    "capability_taxonomy", ["active_status"])
    else:
        # Add missing indexes only
        _add_idx(conn, "ix_capability_taxonomy_parent_id", "capability_taxonomy", "parent_id")
        _add_idx(conn, "ix_capability_taxonomy_active",    "capability_taxonomy", "active_status")
        # Add UNIQUE constraint if missing
        if not _has_constraint(conn, "capability_taxonomy", "uq_capability_taxonomy_name"):
            op.execute(
                text(
                    "ALTER TABLE capability_taxonomy "
                    "ADD CONSTRAINT uq_capability_taxonomy_name UNIQUE (name)"
                )
            )

    # ── capability ────────────────────────────────────────────────────────────
    if "capability" not in existing:
        op.create_table(
            "capability",
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("parent_capability_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("capability_type", sa.String(30), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
            sa.CheckConstraint(
                "capability_type IN ('Domain','Skill','Expertise','Technology','Resource','Support Capability')",
                name="ck_capability_type",
            ),
            sa.CheckConstraint(
                "status IN ('Active','Inactive','Deprecated')",
                name="ck_capability_status",
            ),
            sa.ForeignKeyConstraint(
                ["taxonomy_id"], ["capability_taxonomy.taxonomy_id"],
                name="fk_capability_taxonomy", ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["parent_capability_id"], ["capability.capability_id"],
                name="fk_capability_parent", ondelete="SET NULL",
            ),
            sa.UniqueConstraint("name", "capability_type", name="uq_capability_name_type"),
            sa.PrimaryKeyConstraint("capability_id"),
        )
        op.create_index("ix_capability_taxonomy_id",        "capability", ["taxonomy_id"])
        op.create_index("ix_capability_parent_id",          "capability", ["parent_capability_id"])
        op.create_index("ix_capability_type",               "capability", ["capability_type"])
        op.create_index("ix_capability_status",             "capability", ["status"])
    else:
        # Add missing indexes
        _add_idx(conn, "ix_capability_taxonomy_id", "capability", "taxonomy_id")
        _add_idx(conn, "ix_capability_parent_id",   "capability", "parent_capability_id")
        _add_idx(conn, "ix_capability_type",        "capability", "capability_type")
        _add_idx(conn, "ix_capability_status",      "capability", "status")

        # Add CHECK constraints if missing
        if not _has_constraint(conn, "capability", "ck_capability_type"):
            op.execute(
                text(
                    "ALTER TABLE capability ADD CONSTRAINT ck_capability_type "
                    "CHECK (capability_type IN "
                    "('Domain','Skill','Expertise','Technology','Resource','Support Capability'))"
                )
            )
        if not _has_constraint(conn, "capability", "ck_capability_status"):
            op.execute(
                text(
                    "ALTER TABLE capability ADD CONSTRAINT ck_capability_status "
                    "CHECK (status IN ('Active','Inactive','Deprecated'))"
                )
            )
        # UNIQUE constraint on name+type (only if not exists and no duplicates)
        if not _has_constraint(conn, "capability", "uq_capability_name_type"):
            # Check for duplicates first
            dup = conn.execute(
                text(
                    "SELECT name, capability_type, count(*) "
                    "FROM capability GROUP BY name, capability_type HAVING count(*) > 1"
                )
            ).fetchone()
            if dup is None:
                op.execute(
                    text(
                        "ALTER TABLE capability "
                        "ADD CONSTRAINT uq_capability_name_type UNIQUE (name, capability_type)"
                    )
                )


def downgrade() -> None:
    op.drop_table("capability")
    op.drop_table("capability_taxonomy")
