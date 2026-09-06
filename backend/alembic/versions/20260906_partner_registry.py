"""Create / patch External Partner Registry tables.

The three tables already exist in Supabase with a partial schema.
This migration adds all missing columns non-destructively.

Revision ID: 20260906_partner_registry
Revises: 20260906_ev_fk_patch
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "20260906_partner_registry"
down_revision: Union[str, None] = "20260906_ev_fk_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def _add_ts(table: str, col: str) -> None:
    """Add a timestamptz column, backfill NOW(), set NOT NULL + default."""
    op.add_column(table, sa.Column(col, sa.DateTime(timezone=True), nullable=True))
    op.execute(text(f"UPDATE {table} SET {col} = NOW() WHERE {col} IS NULL"))
    op.execute(
        text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {col} SET DEFAULT now(), "
            f"ALTER COLUMN {col} SET NOT NULL"
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # ── partner_profile ────────────────────────────────────────────────────────
    if "partner_profile" not in existing:
        op.create_table(
            "partner_profile",
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_type", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("website", sa.String(500), nullable=True),
            sa.Column("contact_details", postgresql.JSONB(), nullable=True),
            sa.Column("verification_status", sa.Text(), nullable=False, server_default="Pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.organization_id"],
                                    name="fk_partner_organization", ondelete="CASCADE"),
            sa.UniqueConstraint("organization_id", name="uq_partner_organization_id"),
            sa.PrimaryKeyConstraint("partner_id"),
        )
        op.create_index("ix_partner_org_id", "partner_profile", ["organization_id"])
        op.create_index("ix_partner_type", "partner_profile", ["partner_type"])
        op.create_index("ix_partner_verification", "partner_profile", ["verification_status"])
    else:
        pp_cols = _cols(conn, "partner_profile")
        if "description" not in pp_cols:
            op.add_column("partner_profile", sa.Column("description", sa.Text(), nullable=True))
        if "website" not in pp_cols:
            op.add_column("partner_profile", sa.Column("website", sa.String(500), nullable=True))
        if "contact_details" not in pp_cols:
            op.add_column("partner_profile", sa.Column("contact_details", postgresql.JSONB(), nullable=True))
        if "created_at" not in pp_cols:
            _add_ts("partner_profile", "created_at")
        if "updated_at" not in pp_cols:
            _add_ts("partner_profile", "updated_at")
        _add_idx(conn, "ix_partner_org_id", "partner_profile", "organization_id")
        _add_idx(conn, "ix_partner_type", "partner_profile", "partner_type")
        _add_idx(conn, "ix_partner_verification", "partner_profile", "verification_status")

    # ── partner_capability ─────────────────────────────────────────────────────
    if "partner_capability" not in existing:
        op.create_table(
            "partner_capability",
            sa.Column("partner_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("proficiency_level", sa.Integer(), nullable=True),
            sa.Column("experience_description", sa.Text(), nullable=True),
            sa.Column("evidence_reference", sa.Text(), nullable=True),
            sa.Column("verification_status", sa.Text(), nullable=False, server_default="Pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["partner_id"], ["partner_profile.partner_id"],
                                    name="fk_partner_cap_partner", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"],
                                    name="fk_partner_cap_capability", ondelete="RESTRICT"),
            sa.UniqueConstraint("partner_id", "capability_id", name="uq_partner_capability"),
            sa.PrimaryKeyConstraint("partner_capability_id"),
        )
        op.create_index("ix_partner_cap_partner_id", "partner_capability", ["partner_id"])
        op.create_index("ix_partner_cap_capability_id", "partner_capability", ["capability_id"])
    else:
        pc_cols = _cols(conn, "partner_capability")
        if "proficiency_level" not in pc_cols:
            op.add_column("partner_capability", sa.Column("proficiency_level", sa.Integer(), nullable=True))
        if "experience_description" not in pc_cols:
            op.add_column("partner_capability", sa.Column("experience_description", sa.Text(), nullable=True))
        if "evidence_reference" not in pc_cols:
            op.add_column("partner_capability", sa.Column("evidence_reference", sa.Text(), nullable=True))
        if "created_at" not in pc_cols:
            _add_ts("partner_capability", "created_at")
        if "updated_at" not in pc_cols:
            _add_ts("partner_capability", "updated_at")
        # ensure verification_status NOT NULL
        if "verification_status" not in pc_cols:
            op.add_column("partner_capability", sa.Column("verification_status", sa.Text(), nullable=True))
            op.execute(text("UPDATE partner_capability SET verification_status = 'Pending' WHERE verification_status IS NULL"))
            op.execute(text("ALTER TABLE partner_capability ALTER COLUMN verification_status SET DEFAULT 'Pending', ALTER COLUMN verification_status SET NOT NULL"))
        _add_idx(conn, "ix_partner_cap_partner_id", "partner_capability", "partner_id")
        _add_idx(conn, "ix_partner_cap_capability_id", "partner_capability", "capability_id")
        # add unique constraint if missing
        existing_uqs = {u["name"] for u in inspect(conn).get_unique_constraints("partner_capability", schema="public")}
        if "uq_partner_capability" not in existing_uqs:
            dup = conn.execute(text(
                "SELECT partner_id, capability_id, count(*) FROM partner_capability "
                "GROUP BY partner_id, capability_id HAVING count(*) > 1"
            )).fetchone()
            if dup is None:
                op.execute(text("ALTER TABLE partner_capability ADD CONSTRAINT uq_partner_capability UNIQUE (partner_id, capability_id)"))

    # ── partner_support_offering ───────────────────────────────────────────────
    if "partner_support_offering" not in existing:
        op.create_table(
            "partner_support_offering",
            sa.Column("offering_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("support_type", sa.Text(), nullable=False),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("capacity", postgresql.JSONB(), nullable=True),
            sa.Column("eligibility", sa.Text(), nullable=True),
            sa.Column("availability_start", sa.Date(), nullable=True),
            sa.Column("availability_end", sa.Date(), nullable=True),
            sa.Column("location", sa.Text(), nullable=True),
            sa.Column("estimated_value", sa.Numeric(15, 2), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["partner_id"], ["partner_profile.partner_id"],
                                    name="fk_offering_partner", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("offering_id"),
        )
        op.create_index("ix_offering_partner_id", "partner_support_offering", ["partner_id"])
        op.create_index("ix_offering_support_type", "partner_support_offering", ["support_type"])
        op.create_index("ix_offering_status", "partner_support_offering", ["status"])
    else:
        po_cols = _cols(conn, "partner_support_offering")
        if "title" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("title", sa.String(500), nullable=True))
        if "availability_start" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("availability_start", sa.Date(), nullable=True))
        if "availability_end" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("availability_end", sa.Date(), nullable=True))
        if "location" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("location", sa.Text(), nullable=True))
        if "estimated_value" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("estimated_value", sa.Numeric(15, 2), nullable=True))
        if "status" not in po_cols:
            op.add_column("partner_support_offering", sa.Column("status", sa.String(20), nullable=True))
            op.execute(text("UPDATE partner_support_offering SET status = 'Active' WHERE status IS NULL"))
            op.execute(text("ALTER TABLE partner_support_offering ALTER COLUMN status SET DEFAULT 'Active', ALTER COLUMN status SET NOT NULL"))
        if "created_at" not in po_cols:
            _add_ts("partner_support_offering", "created_at")
        if "updated_at" not in po_cols:
            _add_ts("partner_support_offering", "updated_at")
        _add_idx(conn, "ix_offering_partner_id", "partner_support_offering", "partner_id")
        _add_idx(conn, "ix_offering_support_type", "partner_support_offering", "support_type")
        _add_idx(conn, "ix_offering_status", "partner_support_offering", "status")


def downgrade() -> None:
    # Only drop tables if they were created fresh by this migration.
    # We do NOT drop pre-existing Supabase tables.
    pass
