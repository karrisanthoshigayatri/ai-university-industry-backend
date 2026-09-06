"""Make capability_id nullable in AI tables to support unmapped capabilities.

Revision ID: 20260906_fix_ai_nullable
Revises: 20260906_ai_analysis
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260906_fix_ai_nullable"
down_revision: Union[str, None] = "20260906_ai_analysis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow capability_id to be NULL in problem_category and problem_requirement_capability.

    This supports the case where AI suggests a capability that doesn't exist
    in the canonical Capability table yet (unmapped capability suggestion).
    """
    op.execute(text("ALTER TABLE problem_category ALTER COLUMN capability_id DROP NOT NULL"))
    op.execute(text("ALTER TABLE problem_requirement_capability ALTER COLUMN capability_id DROP NOT NULL"))


def downgrade() -> None:
    op.execute(text("ALTER TABLE problem_category ALTER COLUMN capability_id SET NOT NULL"))
    op.execute(text("ALTER TABLE problem_requirement_capability ALTER COLUMN capability_id SET NOT NULL"))
