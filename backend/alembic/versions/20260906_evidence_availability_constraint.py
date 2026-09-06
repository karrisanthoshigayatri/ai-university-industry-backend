"""Create capability_evidence, availability, and entity_constraint tables.

Revision ID: 20260906_ev_avail_constraint
Revises: 20260906_hei_schema_patch
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_ev_avail_constraint"
down_revision: Union[str, None] = "20260906_hei_schema_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> set[str]:
    return set(inspect(conn).get_table_names(schema="public"))


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def upgrade() -> None:
    conn = op.get_bind()
    existing = _tables(conn)

    # ── capability_evidence ────────────────────────────────────────────────────
    if "capability_evidence" not in existing:
        op.create_table(
            "capability_evidence",
            sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(50), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("evidence_type", sa.String(50), nullable=False),
            sa.Column("source", sa.String(500), nullable=True),
            sa.Column("reference", sa.String(1000), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("recency", sa.String(100), nullable=True),
            sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "verification_status",
                sa.String(20),
                nullable=False,
                server_default="Pending",
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
                "entity_type IN ('hei_capability','faculty_expertise',"
                "'institutional_resource','partner_capability')",
                name="ck_evidence_entity_type",
            ),
            sa.CheckConstraint(
                "evidence_type IN ('Certification','Publication','Project','Patent',"
                "'Laboratory','Infrastructure','Experience','Official Document','Website')",
                name="ck_evidence_type",
            ),
            sa.CheckConstraint(
                "verification_status IN ('Pending','Verified','Rejected')",
                name="ck_evidence_verification_status",
            ),
            sa.PrimaryKeyConstraint("evidence_id"),
        )
        op.create_index("ix_evidence_entity_type", "capability_evidence", ["entity_type"])
        op.create_index("ix_evidence_entity_id", "capability_evidence", ["entity_id"])
        op.create_index("ix_evidence_capability_id", "capability_evidence", ["capability_id"])
        op.create_index(
            "ix_evidence_verification_status", "capability_evidence", ["verification_status"]
        )
    else:
        cols = _cols(conn, "capability_evidence")
        if "recency" not in cols:
            op.add_column(
                "capability_evidence", sa.Column("recency", sa.String(100), nullable=True)
            )
        if "verified_by" not in cols:
            op.add_column(
                "capability_evidence",
                sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
            )
        if "verified_at" not in cols:
            op.add_column(
                "capability_evidence",
                sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            )
        _add_idx(conn, "ix_evidence_entity_type", "capability_evidence", "entity_type")
        _add_idx(conn, "ix_evidence_entity_id", "capability_evidence", "entity_id")
        _add_idx(conn, "ix_evidence_capability_id", "capability_evidence", "capability_id")
        _add_idx(
            conn,
            "ix_evidence_verification_status",
            "capability_evidence",
            "verification_status",
        )

    # ── availability ───────────────────────────────────────────────────────────
    if "availability" not in existing:
        op.create_table(
            "availability",
            sa.Column("availability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(50), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="Available"),
            sa.Column("capacity", sa.Integer(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("conditions", postgresql.JSONB(), nullable=True),
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
                "entity_type IN ('hei_capability','faculty_expertise',"
                "'institutional_resource','partner_capability')",
                name="ck_availability_entity_type",
            ),
            sa.PrimaryKeyConstraint("availability_id"),
        )
        op.create_index("ix_availability_entity_type", "availability", ["entity_type"])
        op.create_index("ix_availability_entity_id", "availability", ["entity_id"])
    else:
        _add_idx(conn, "ix_availability_entity_type", "availability", "entity_type")
        _add_idx(conn, "ix_availability_entity_id", "availability", "entity_id")

    # ── entity_constraint ──────────────────────────────────────────────────────
    if "entity_constraint" not in existing:
        op.create_table(
            "entity_constraint",
            sa.Column("constraint_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(50), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("constraint_type", sa.String(100), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("severity", sa.String(20), nullable=False, server_default="Medium"),
            sa.Column("validity_period", postgresql.JSONB(), nullable=True),
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
                "entity_type IN ('hei_capability','faculty_expertise',"
                "'institutional_resource','partner_capability')",
                name="ck_constraint_entity_type",
            ),
            sa.CheckConstraint(
                "severity IN ('Low','Medium','High','Critical')",
                name="ck_constraint_severity",
            ),
            sa.PrimaryKeyConstraint("constraint_id"),
        )
        op.create_index("ix_constraint_entity_type", "entity_constraint", ["entity_type"])
        op.create_index("ix_constraint_entity_id", "entity_constraint", ["entity_id"])
    else:
        _add_idx(conn, "ix_constraint_entity_type", "entity_constraint", "entity_type")
        _add_idx(conn, "ix_constraint_entity_id", "entity_constraint", "entity_id")


def downgrade() -> None:
    conn = op.get_bind()
    existing = _tables(conn)
    if "entity_constraint" in existing:
        op.drop_table("entity_constraint")
    if "availability" in existing:
        op.drop_table("availability")
    if "capability_evidence" in existing:
        op.drop_table("capability_evidence")
