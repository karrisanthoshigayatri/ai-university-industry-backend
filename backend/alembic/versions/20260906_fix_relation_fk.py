"""Fix problem_relation foreign keys to point to the 'user' table.

The pre-existing problem_relation table had decided_by FK pointing to app_user.
This migration drops those constraints and recreates them pointing to user.

Revision ID: 20260906_fix_relation_fk
Revises: 20260906_problem_relation
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


revision: str = "20260906_fix_relation_fk"
down_revision: Union[str, None] = "20260906_problem_relation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Repoint problem_relation.decided_by FK from app_user to user."""

    connection = op.get_bind()
    fks = inspect(connection).get_foreign_keys("problem_relation", schema="public")

    for fk in fks:
        if fk["constrained_columns"] == ["decided_by"] and fk["referred_table"] != "user":
            # Drop the old constraint
            op.drop_constraint(fk["name"], "problem_relation", type_="foreignkey")
            # Create correct one
            op.create_foreign_key(
                "fk_relation_decided_by",
                "problem_relation",
                "user",
                ["decided_by"],
                ["user_id"],
                ondelete="SET NULL",
            )
            break

    # Also fix source/target problem FKs if they point elsewhere
    for fk in fks:
        if fk["constrained_columns"] == ["source_problem_id"] and fk["referred_table"] != "problem":
            op.drop_constraint(fk["name"], "problem_relation", type_="foreignkey")
            op.create_foreign_key(
                "fk_relation_source_problem_id",
                "problem_relation",
                "problem",
                ["source_problem_id"],
                ["problem_id"],
                ondelete="CASCADE",
            )
        if fk["constrained_columns"] == ["target_problem_id"] and fk["referred_table"] != "problem":
            op.drop_constraint(fk["name"], "problem_relation", type_="foreignkey")
            op.create_foreign_key(
                "fk_relation_target_problem_id",
                "problem_relation",
                "problem",
                ["target_problem_id"],
                ["problem_id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    """Revert decided_by FK back to app_user (best-effort)."""
    op.drop_constraint("fk_relation_decided_by", "problem_relation", type_="foreignkey")
    op.create_foreign_key(
        "problem_relation_decided_by_fkey",
        "problem_relation",
        "app_user",
        ["decided_by"],
        ["user_id"],
        ondelete="SET NULL",
    )
