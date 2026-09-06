"""Create/patch project, team, member, resource, capability tables.

All tables already exist in Supabase. This migration is idempotent.

Revision ID: 20260906_projects
Revises: 20260906_fr_match
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_projects"
down_revision: Union[str, None] = "20260906_fr_match"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tbl: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(tbl, schema="public")}


def _idxs(conn, tbl: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(tbl, schema="public")}


def _add_idx(conn, name: str, tbl: str, col: str) -> None:
    if name not in _idxs(conn, tbl):
        op.create_index(name, tbl, [col])


def _add_ts(tbl: str, col: str) -> None:
    op.add_column(tbl, sa.Column(col, sa.DateTime(timezone=False), nullable=True))
    op.execute(text(f"UPDATE {tbl} SET {col} = NOW() WHERE {col} IS NULL"))
    op.execute(text(
        f"ALTER TABLE {tbl} "
        f"ALTER COLUMN {col} SET DEFAULT now(), "
        f"ALTER COLUMN {col} SET NOT NULL"
    ))


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # ── project ────────────────────────────────────────────────────────────────
    if "project" not in existing:
        op.create_table(
            "project",
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("objective", sa.Text(), nullable=True),
            sa.Column("solution_summary", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="Proposed"),
            sa.Column("current_stage", sa.Text(), nullable=False, server_default="Proposal"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("expected_end_date", sa.Date(), nullable=True),
            sa.Column("completion_date", sa.Date(), nullable=True),
            sa.Column("project_lead", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["problem_id"], ["problem.problem_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("project_id"),
        )
        op.create_index("ix_project_problem_id", "project", ["problem_id"])
        op.create_index("ix_project_hei_id", "project", ["hei_id"])
        op.create_index("ix_project_status", "project", ["status"])
    else:
        _add_idx(conn, "ix_project_problem_id", "project", "problem_id")
        _add_idx(conn, "ix_project_hei_id", "project", "hei_id")
        _add_idx(conn, "ix_project_status", "project", "status")

    # ── project_team ──────────────────────────────────────────────────────────
    if "project_team" not in existing:
        op.create_table(
            "project_team",
            sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("faculty_lead", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("formation_date", sa.Date(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True, server_default="Active"),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["faculty_lead"], ["faculty_expert_profile.faculty_expert_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("team_id"),
        )
        op.create_index("ix_team_project_id", "project_team", ["project_id"])
    else:
        _add_idx(conn, "ix_team_project_id", "project_team", "project_id")

    # ── project_team_member ───────────────────────────────────────────────────
    if "project_team_member" not in existing:
        op.create_table(
            "project_team_member",
            sa.Column("team_member_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("member_type", sa.Text(), nullable=False),
            sa.Column("role", sa.Text(), nullable=True),
            sa.Column("joined_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("left_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("status", sa.Text(), nullable=True, server_default="Active"),
            sa.ForeignKeyConstraint(["team_id"], ["project_team.team_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("team_member_id"),
        )
        op.create_index("ix_team_member_team_id", "project_team_member", ["team_id"])
        op.create_index("ix_team_member_user_id", "project_team_member", ["user_id"])
    else:
        _add_idx(conn, "ix_team_member_team_id", "project_team_member", "team_id")
        _add_idx(conn, "ix_team_member_user_id", "project_team_member", "user_id")

    # ── project_resource ──────────────────────────────────────────────────────
    if "project_resource" not in existing:
        op.create_table(
            "project_resource",
            sa.Column("project_resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("usage", sa.Text(), nullable=True),
            sa.Column("access_status", sa.Text(), nullable=True, server_default="Requested"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["resource_id"], ["institutional_resource.resource_id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("project_resource_id"),
        )
        op.create_index("ix_proj_res_project_id", "project_resource", ["project_id"])
        op.create_index("ix_proj_res_resource_id", "project_resource", ["resource_id"])
    else:
        _add_idx(conn, "ix_proj_res_project_id", "project_resource", "project_id")
        _add_idx(conn, "ix_proj_res_resource_id", "project_resource", "resource_id")

    # ── project_capability ────────────────────────────────────────────────────
    if "project_capability" not in existing:
        op.create_table(
            "project_capability",
            sa.Column("project_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_type", sa.Text(), nullable=True),
            sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("strength_level", sa.Numeric(5, 2), nullable=True),
            sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("project_capability_id"),
        )
        op.create_index("ix_proj_cap_project_id", "project_capability", ["project_id"])
        op.create_index("ix_proj_cap_capability_id", "project_capability", ["capability_id"])
    else:
        _add_idx(conn, "ix_proj_cap_project_id", "project_capability", "project_id")
        _add_idx(conn, "ix_proj_cap_capability_id", "project_capability", "capability_id")


def downgrade() -> None:
    pass
