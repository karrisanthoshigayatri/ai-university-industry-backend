"""Create or fix the problem_relation table.

Revision ID: 20260906_problem_relation
Revises: 20260906_fix_problem_fk
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "20260906_problem_relation"
down_revision: Union[str, None] = "20260906_fix_problem_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(connection, table: str) -> set[str]:
    return {c["name"] for c in inspect(connection).get_columns(table, schema="public")}


def _existing_indexes(connection, table: str) -> set[str]:
    return {i["name"] for i in inspect(connection).get_indexes(table, schema="public")}


def _existing_constraints(connection, table: str) -> set[str]:
    result = connection.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
            "WHERE pg_class.relname = :tbl AND pg_class.relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public')"
        ),
        {"tbl": table},
    )
    return {row[0] for row in result}


def upgrade() -> None:
    """Create problem_relation table if missing, or patch the existing one."""

    connection = op.get_bind()
    existing_tables = set(inspect(connection).get_table_names(schema="public"))

    if "problem_relation" not in existing_tables:
        # ── Fresh create ───────────────────────────────────────────────────────
        op.create_table(
            "problem_relation",
            sa.Column("relation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("target_problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("relation_type", sa.String(length=20), nullable=False,
                      server_default="Similar"),
            sa.Column("similarity_score", sa.Float(), nullable=True),
            sa.Column("ai_reason", sa.Text(), nullable=True),
            sa.Column("human_confirmation", sa.Boolean(), nullable=False,
                      server_default="false"),
            sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "relation_type IN ('Similar','Duplicate','Related','Consolidated','Linked')",
                name="ck_problem_relation_type",
            ),
            sa.CheckConstraint(
                "source_problem_id <> target_problem_id",
                name="ck_problem_relation_no_self",
            ),
            sa.ForeignKeyConstraint(
                ["source_problem_id"], ["problem.problem_id"],
                name="fk_relation_source_problem_id", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["target_problem_id"], ["problem.problem_id"],
                name="fk_relation_target_problem_id", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["decided_by"], ["user.user_id"],
                name="fk_relation_decided_by", ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("relation_id"),
        )
        op.create_index("ix_problem_relation_source", "problem_relation", ["source_problem_id"])
        op.create_index("ix_problem_relation_target", "problem_relation", ["target_problem_id"])
        op.create_index("ix_problem_relation_type", "problem_relation", ["relation_type"])
        op.create_index(
            "ix_problem_relation_human_confirmation",
            "problem_relation",
            ["human_confirmation"],
        )
    else:
        # ── Patch the pre-existing table ───────────────────────────────────────
        cols = _existing_columns(connection, "problem_relation")

        # Add created_at if missing
        if "created_at" not in cols:
            op.add_column(
                "problem_relation",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=True,          # nullable first so existing rows don't fail
                ),
            )
            op.execute(
                text("UPDATE problem_relation SET created_at = NOW() WHERE created_at IS NULL")
            )
            # Make it NOT NULL with a server default
            op.execute(
                text(
                    "ALTER TABLE problem_relation "
                    "ALTER COLUMN created_at SET DEFAULT now(), "
                    "ALTER COLUMN created_at SET NOT NULL"
                )
            )

        # Fix decided_at timezone if needed
        op.execute(
            text(
                "ALTER TABLE problem_relation "
                "ALTER COLUMN decided_at TYPE TIMESTAMP WITH TIME ZONE "
                "USING decided_at AT TIME ZONE 'UTC'"
            )
        )

        # Fix similarity_score: NUMERIC → FLOAT
        op.execute(
            text(
                "ALTER TABLE problem_relation "
                "ALTER COLUMN similarity_score TYPE FLOAT "
                "USING similarity_score::FLOAT"
            )
        )

        # Add CHECK constraint if missing
        constraints = _existing_constraints(connection, "problem_relation")
        if "ck_problem_relation_type" not in constraints:
            op.execute(
                text(
                    "ALTER TABLE problem_relation ADD CONSTRAINT ck_problem_relation_type "
                    "CHECK (relation_type IN "
                    "('Similar','Duplicate','Related','Consolidated','Linked'))"
                )
            )
        if "ck_problem_relation_no_self" not in constraints:
            op.execute(
                text(
                    "ALTER TABLE problem_relation ADD CONSTRAINT ck_problem_relation_no_self "
                    "CHECK (source_problem_id <> target_problem_id)"
                )
            )

        # Add missing FK: decided_by → user
        if "fk_relation_decided_by" not in constraints:
            # Check if the column exists and has a usable FK already
            fks = inspect(connection).get_foreign_keys("problem_relation", schema="public")
            db_fk = any(fk["constrained_columns"] == ["decided_by"] for fk in fks)
            if not db_fk:
                op.create_foreign_key(
                    "fk_relation_decided_by",
                    "problem_relation",
                    "user",
                    ["decided_by"],
                    ["user_id"],
                    ondelete="SET NULL",
                )

        # Add missing indexes
        indexes = _existing_indexes(connection, "problem_relation")
        index_defs = [
            ("ix_problem_relation_source", ["source_problem_id"]),
            ("ix_problem_relation_target", ["target_problem_id"]),
            ("ix_problem_relation_type", ["relation_type"]),
            ("ix_problem_relation_human_confirmation", ["human_confirmation"]),
        ]
        for idx_name, idx_cols in index_defs:
            if idx_name not in indexes:
                op.create_index(idx_name, "problem_relation", idx_cols)


def downgrade() -> None:
    """Drop problem_relation table."""
    op.drop_index("ix_problem_relation_human_confirmation", table_name="problem_relation")
    op.drop_index("ix_problem_relation_type", table_name="problem_relation")
    op.drop_index("ix_problem_relation_target", table_name="problem_relation")
    op.drop_index("ix_problem_relation_source", table_name="problem_relation")
    op.drop_table("problem_relation")
