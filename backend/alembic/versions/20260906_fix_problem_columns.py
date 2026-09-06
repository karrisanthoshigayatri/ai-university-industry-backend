"""Fix problem table column types to match the model.

The pre-existing problem table was created with location as JSONB and
timestamps without timezone. This migration corrects both.

Revision ID: 20260906_fix_problem_columns
Revises: 20260906_problem_evidence
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "20260906_fix_problem_columns"
down_revision: Union[str, None] = "20260906_problem_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_type(connection, table: str, column: str) -> str:
    """Return the current SQL type name of a column (upper-cased)."""
    cols = {c["name"]: c for c in inspect(connection).get_columns(table, schema="public")}
    return str(cols[column]["type"]).upper() if column in cols else ""


def upgrade() -> None:
    """Correct column types on the problem table."""

    connection = op.get_bind()

    # Fix location: JSONB → VARCHAR(500)
    loc_type = _column_type(connection, "problem", "location")
    if "JSONB" in loc_type or "JSON" in loc_type:
        op.execute(
            text(
                "ALTER TABLE problem "
                "ALTER COLUMN location TYPE VARCHAR(500) "
                "USING location::text"
            )
        )

    # Fix timestamps to include timezone if they don't already
    for col in ("submission_date", "created_at", "updated_at"):
        col_type = _column_type(connection, "problem", col)
        if "TIME ZONE" not in col_type and "TIMEZONE" not in col_type:
            op.execute(
                text(
                    f"ALTER TABLE problem "
                    f"ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE "
                    f"USING {col} AT TIME ZONE 'UTC'"
                )
            )


def downgrade() -> None:
    """Revert column types (best-effort)."""

    op.execute(
        text(
            "ALTER TABLE problem "
            "ALTER COLUMN location TYPE JSONB "
            "USING location::jsonb"
        )
    )
