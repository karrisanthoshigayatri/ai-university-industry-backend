"""Patch collaboration_request — add requested_by, response_message, created_at.
Also add project_partner unique constraint and indexes.

Revision ID: 20260906_collab_patch
Revises: 20260906_cap_gap_patch
Create Date: 2026-09-06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_collab_patch"
down_revision: Union[str, None] = "20260906_cap_gap_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tbl): return {c["name"] for c in inspect(conn).get_columns(tbl, schema="public")}
def _idxs(conn, tbl): return {i["name"] for i in inspect(conn).get_indexes(tbl, schema="public")}
def _uqs(conn, tbl): return {u["name"] for u in inspect(conn).get_unique_constraints(tbl, schema="public")}
def _add_idx(conn, name, tbl, col):
    if name not in _idxs(conn, tbl): op.create_index(name, tbl, [col])


def upgrade():
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    if "collaboration_request" in existing:
        cols = _cols(conn, "collaboration_request")
        if "requested_by" not in cols:
            op.add_column("collaboration_request",
                          sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True))
        if "response_message" not in cols:
            op.add_column("collaboration_request",
                          sa.Column("response_message", sa.Text(), nullable=True))
        if "created_at" not in cols:
            op.add_column("collaboration_request",
                          sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
            op.execute(text("UPDATE collaboration_request SET created_at=NOW() WHERE created_at IS NULL"))
            op.execute(text("ALTER TABLE collaboration_request ALTER COLUMN created_at SET DEFAULT now(), ALTER COLUMN created_at SET NOT NULL"))
        _add_idx(conn, "ix_collab_project_id", "collaboration_request", "project_id")
        _add_idx(conn, "ix_collab_partner_id", "collaboration_request", "partner_id")
        _add_idx(conn, "ix_collab_status", "collaboration_request", "status")
    else:
        op.create_table(
            "collaboration_request",
            sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("request_type", sa.Text(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="Requested"),
            sa.Column("sent_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("responded_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("response_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["partner_id"], ["partner_profile.partner_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("request_id"),
        )
        op.create_index("ix_collab_project_id", "collaboration_request", ["project_id"])
        op.create_index("ix_collab_partner_id", "collaboration_request", ["partner_id"])
        op.create_index("ix_collab_status", "collaboration_request", ["status"])

    if "project_partner" in existing:
        _add_idx(conn, "ix_proj_partner_project_id", "project_partner", "project_id")
        _add_idx(conn, "ix_proj_partner_partner_id", "project_partner", "partner_id")
        uqs = _uqs(conn, "project_partner")
        if "uq_project_partner" not in uqs:
            dup = conn.execute(text(
                "SELECT project_id, partner_id, count(*) FROM project_partner "
                "GROUP BY project_id, partner_id HAVING count(*)>1"
            )).fetchone()
            if dup is None:
                op.execute(text("ALTER TABLE project_partner ADD CONSTRAINT uq_project_partner UNIQUE (project_id, partner_id)"))
    else:
        op.create_table(
            "project_partner",
            sa.Column("project_partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("contribution_type", sa.Text(), nullable=True),
            sa.Column("contribution_details", sa.Text(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="Active"),
            sa.ForeignKeyConstraint(["project_id"], ["project.project_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["partner_id"], ["partner_profile.partner_id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("project_id", "partner_id", name="uq_project_partner"),
            sa.PrimaryKeyConstraint("project_partner_id"),
        )
        op.create_index("ix_proj_partner_project_id", "project_partner", ["project_id"])
        op.create_index("ix_proj_partner_partner_id", "project_partner", ["partner_id"])


def downgrade():
    pass
