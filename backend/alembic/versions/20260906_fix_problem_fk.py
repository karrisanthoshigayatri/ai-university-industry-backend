"""Fix problem and problem_evidence foreign keys to point to the 'user' table.

The pre-existing problem table had FKs pointing to 'app_user'.
This migration drops those constraints and recreates them pointing to 'user'.

Revision ID: 20260906_fix_problem_fk
Revises: 20260906_fix_problem_columns
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "20260906_fix_problem_fk"
down_revision: Union[str, None] = "20260906_fix_problem_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fk_names(connection, table: str) -> dict[str, str]:
    """Return {constrained_col: constraint_name} for all FKs on a table."""
    return {
        fk["constrained_columns"][0]: fk["name"]
        for fk in inspect(connection).get_foreign_keys(table, schema="public")
        if fk["name"]
    }


def upgrade() -> None:
    """Repoint problem and problem_evidence FKs from app_user to user."""

    connection = op.get_bind()

    # ── problem.submitter_id ──────────────────────────────────────────────────
    problem_fks = _fk_names(connection, "problem")
    submitter_fk = problem_fks.get("submitter_id")
    if submitter_fk:
        # Check if it currently points to app_user
        fk_detail = next(
            (
                fk for fk in inspect(connection).get_foreign_keys("problem", schema="public")
                if fk["constrained_columns"] == ["submitter_id"]
            ),
            None,
        )
        if fk_detail and fk_detail["referred_table"] != "user":
            op.drop_constraint(submitter_fk, "problem", type_="foreignkey")
            op.create_foreign_key(
                "fk_problem_submitter_id",
                "problem",
                "user",
                ["submitter_id"],
                ["user_id"],
                ondelete="RESTRICT",
            )

    # ── problem_evidence.submitted_by ─────────────────────────────────────────
    evidence_fks = _fk_names(connection, "problem_evidence")
    submitted_by_fk = evidence_fks.get("submitted_by")
    if submitted_by_fk:
        fk_detail = next(
            (
                fk for fk in inspect(connection).get_foreign_keys(
                    "problem_evidence", schema="public"
                )
                if fk["constrained_columns"] == ["submitted_by"]
            ),
            None,
        )
        if fk_detail and fk_detail["referred_table"] != "user":
            op.drop_constraint(submitted_by_fk, "problem_evidence", type_="foreignkey")
            op.create_foreign_key(
                "fk_evidence_submitted_by",
                "problem_evidence",
                "user",
                ["submitted_by"],
                ["user_id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    """Revert FKs back to app_user (best-effort)."""

    op.drop_constraint("fk_problem_submitter_id", "problem", type_="foreignkey")
    op.create_foreign_key(
        "problem_submitter_id_fkey",
        "problem",
        "app_user",
        ["submitter_id"],
        ["user_id"],
        ondelete="RESTRICT",
    )
