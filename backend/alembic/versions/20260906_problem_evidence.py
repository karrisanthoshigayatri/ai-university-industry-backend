"""Create problem and problem_evidence tables.

Revision ID: 20260906_problem_evidence
Revises: 20260906_user_password_hash
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision: str = "20260906_problem_evidence"
down_revision: Union[str, None] = "20260906_user_password_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the problem and problem_evidence tables (idempotent)."""

    connection = op.get_bind()
    existing_tables = set(inspect(connection).get_table_names(schema="public"))

    # ── problem ────────────────────────────────────────────────────────────────
    if "problem" not in existing_tables:
        op.create_table(
            "problem",
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("submitter_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_type", sa.String(length=30), nullable=False),
            sa.Column("location", sa.String(length=500), nullable=True),
            sa.Column(
                "submission_date",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "current_status",
                sa.String(length=50),
                server_default="Submitted",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "source_type IN ('Citizen', 'Community', 'PRI', 'ULB', 'Government')",
                name="ck_problem_source_type",
            ),
            sa.CheckConstraint(
                "current_status IN ("
                "'Submitted', 'Similar Found', 'Pending Validation', 'Validated', "
                "'Rejected', 'Redirected', 'Linked to Existing Problem', "
                "'Matched', 'Accepted', 'Active', 'Completed')",
                name="ck_problem_current_status",
            ),
            sa.ForeignKeyConstraint(
                ["submitter_id"],
                ["user.user_id"],
                name="fk_problem_submitter_id",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("problem_id"),
        )
        op.create_index("ix_problem_submitter_id", "problem", ["submitter_id"])
        op.create_index("ix_problem_current_status", "problem", ["current_status"])
        op.create_index("ix_problem_source_type", "problem", ["source_type"])
        op.create_index("ix_problem_submission_date", "problem", ["submission_date"])

    # ── problem_evidence ───────────────────────────────────────────────────────
    if "problem_evidence" not in existing_tables:
        op.create_table(
            "problem_evidence",
            sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("evidence_type", sa.String(length=30), nullable=False),
            sa.Column("file_reference", sa.String(length=1000), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "verification_status",
                sa.String(length=20),
                server_default="Pending",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "evidence_type IN ("
                "'Photograph', 'Video', 'Document', 'Geo-location', "
                "'Government record', 'Citizen report')",
                name="ck_evidence_type",
            ),
            sa.CheckConstraint(
                "verification_status IN ('Pending', 'Verified', 'Rejected')",
                name="ck_evidence_verification_status",
            ),
            sa.ForeignKeyConstraint(
                ["problem_id"],
                ["problem.problem_id"],
                name="fk_evidence_problem_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["submitted_by"],
                ["user.user_id"],
                name="fk_evidence_submitted_by",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("evidence_id"),
        )
        op.create_index(
            "ix_problem_evidence_problem_id", "problem_evidence", ["problem_id"]
        )
        op.create_index(
            "ix_problem_evidence_submitted_by", "problem_evidence", ["submitted_by"]
        )
        op.create_index(
            "ix_problem_evidence_verification_status",
            "problem_evidence",
            ["verification_status"],
        )


def downgrade() -> None:
    """Drop problem_evidence and problem tables."""

    connection = op.get_bind()
    existing_tables = set(inspect(connection).get_table_names(schema="public"))

    if "problem_evidence" in existing_tables:
        op.drop_index(
            "ix_problem_evidence_verification_status", table_name="problem_evidence"
        )
        op.drop_index(
            "ix_problem_evidence_submitted_by", table_name="problem_evidence"
        )
        op.drop_index(
            "ix_problem_evidence_problem_id", table_name="problem_evidence"
        )
        op.drop_table("problem_evidence")

    if "problem" in existing_tables:
        op.drop_index("ix_problem_submission_date", table_name="problem")
        op.drop_index("ix_problem_source_type", table_name="problem")
        op.drop_index("ix_problem_current_status", table_name="problem")
        op.drop_index("ix_problem_submitter_id", table_name="problem")
        op.drop_table("problem")
