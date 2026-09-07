"""Create or patch the validation table.

The table already exists in Supabase with validator_id FK pointing to app_user.
This migration adds missing columns/indexes and re-points the FK to 'user'.

Revision ID: 20260906_validation
Revises: 20260906_fix_relation_fk
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "20260906_validation"
down_revision: Union[str, None] = "20260906_fix_relation_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_names(connection, table: str) -> set[str]:
    return {c["name"] for c in inspect(connection).get_columns(table, schema="public")}


def _idx_names(connection, table: str) -> set[str]:
    return {i["name"] for i in inspect(connection).get_indexes(table, schema="public")}


def _fks(connection, table: str) -> list[dict]:
    return inspect(connection).get_foreign_keys(table, schema="public")


def upgrade() -> None:
    connection = op.get_bind()
    existing_tables = set(inspect(connection).get_table_names(schema="public"))

    # ΓöÇΓöÇ Fresh create ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    if "validation" not in existing_tables:
        op.create_table(
            "validation",
            sa.Column("validation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("validator_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("validation_status", sa.String(length=40), nullable=False),
            sa.Column("field_verification_required", sa.Boolean(), nullable=True),
            sa.Column("field_visit_details", sa.Text(), nullable=True),
            sa.Column("evidence_review", sa.Text(), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("redirect_destination", sa.Text(), nullable=True),
            sa.Column(
                "validated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "validation_status IN ("
                "'Valid Problem','Invalid Problem',"
                "'Redirect','More Information Required')",
                name="ck_validation_status",
            ),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problem.problem_id"],
                name="fk_validation_problem_id", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["validator_id"], ["user.user_id"],
                name="fk_validation_validator_id", ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("validation_id"),
        )
        op.create_index("ix_validation_problem_id",  "validation", ["problem_id"])
        op.create_index("ix_validation_validator_id", "validation", ["validator_id"])
        op.create_index("ix_validation_validated_at", "validation", ["validated_at"])
        op.create_index("ix_validation_status",       "validation", ["validation_status"])
        return

    # ΓöÇΓöÇ Patch existing table ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    cols = _col_names(connection, "validation")

    # Fix validated_at timezone if missing
    op.execute(
        text(
            "ALTER TABLE validation "
            "ALTER COLUMN validated_at TYPE TIMESTAMP WITH TIME ZONE "
            "USING validated_at AT TIME ZONE 'UTC'"
        )
    )

    # Add field_verification_required if missing
    if "field_verification_required" not in cols:
        op.add_column("validation", sa.Column("field_verification_required", sa.Boolean(), nullable=True))

    # Re-point validator_id FK from app_user ΓåÆ user
    existing_fks = _fks(connection, "validation")
    for fk in existing_fks:
        if fk["constrained_columns"] == ["validator_id"] and fk["referred_table"] != "user":
            op.drop_constraint(fk["name"], "validation", type_="foreignkey")
            op.create_foreign_key(
                "fk_validation_validator_id",
                "validation", "user",
                ["validator_id"], ["user_id"],
                ondelete="RESTRICT",
            )
            break

    # Add CHECK constraint if missing
    result = connection.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
            "WHERE pg_class.relname = 'validation' "
            "AND pg_class.relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public') "
            "AND conname = 'ck_validation_status'"
        )
    )
    if result.fetchone() is None:
        op.execute(
            text(
                "ALTER TABLE validation ADD CONSTRAINT ck_validation_status "
                "CHECK (validation_status IN ("
                "'Valid Problem','Invalid Problem',"
                "'Redirect','More Information Required'))"
            )
        )

    # Add missing indexes
    idxs = _idx_names(connection, "validation")
    for idx_name, idx_col in [
        ("ix_validation_problem_id",  "problem_id"),
        ("ix_validation_validator_id", "validator_id"),
        ("ix_validation_validated_at", "validated_at"),
        ("ix_validation_status",       "validation_status"),
    ]:
        if idx_name not in idxs:
            op.create_index(idx_name, "validation", [idx_col])


def downgrade() -> None:
    op.drop_index("ix_validation_status",       table_name="validation")
    op.drop_index("ix_validation_validated_at", table_name="validation")
    op.drop_index("ix_validation_validator_id", table_name="validation")
    op.drop_index("ix_validation_problem_id",   table_name="validation")
    op.drop_table("validation")
