"""Create or patch HEI registry tables.

All 6 tables already exist in Supabase. This migration:
- Adds missing columns (created_at, updated_at, etc.)
- Fixes FK references from app_user → user where needed
- Adds missing indexes and constraints

Revision ID: 20260906_hei_registry
Revises: 20260906_capability_taxonomy
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "20260906_hei_registry"
down_revision: Union[str, None] = "20260906_capability_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, table: str) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns(table, schema="public")}


def _idxs(conn, table: str) -> set[str]:
    return {i["name"] for i in inspect(conn).get_indexes(table, schema="public")}


def _fks(conn, table: str) -> list[dict]:
    return inspect(conn).get_foreign_keys(table, schema="public")


def _has_constraint(conn, table: str, name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
            "WHERE pg_class.relname = :tbl "
            "AND pg_class.relnamespace = "
            "(SELECT oid FROM pg_namespace WHERE nspname = 'public') "
            "AND conname = :cname"
        ),
        {"tbl": table, "cname": name},
    ).fetchone()
    return row is not None


def _add_idx(conn, name: str, table: str, col: str) -> None:
    if name not in _idxs(conn, table):
        op.create_index(name, table, [col])


def _add_ts_col(table: str, col: str) -> None:
    """Add a nullable timestamp column, then backfill and make NOT NULL."""
    op.add_column(table, sa.Column(col, sa.DateTime(timezone=True), nullable=True))
    op.execute(text(f"UPDATE {table} SET {col} = NOW() WHERE {col} IS NULL"))
    op.execute(text(f"ALTER TABLE {table} ALTER COLUMN {col} SET DEFAULT now(), ALTER COLUMN {col} SET NOT NULL"))


def _fix_fk_to_user(conn, table: str, col: str, fk_name: str) -> None:
    """Drop FK pointing to app_user, recreate pointing to user."""
    for fk in _fks(conn, table):
        if fk["constrained_columns"] == [col] and fk["referred_table"] == "app_user":
            op.drop_constraint(fk["name"], table, type_="foreignkey")
            op.create_foreign_key(fk_name, table, "user", [col], ["user_id"], ondelete="SET NULL")
            break


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names(schema="public"))

    # ── hei_profile ────────────────────────────────────────────────────────────
    if "hei_profile" not in existing:
        op.create_table(
            "hei_profile",
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("institution_type", sa.String(100), nullable=True),
            sa.Column("accreditation", sa.Text(), nullable=True),
            sa.Column("established_year", sa.Integer(), nullable=True),
            sa.Column("website", sa.String(500), nullable=True),
            sa.Column("contact_details", postgresql.JSONB(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("verification_status", sa.String(20), nullable=False, server_default="Pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.organization_id"],
                                    name="fk_hei_organization", ondelete="CASCADE"),
            sa.UniqueConstraint("organization_id", name="uq_hei_profile_organization_id"),
            sa.PrimaryKeyConstraint("hei_id"),
        )
        op.create_index("ix_hei_profile_org_id", "hei_profile", ["organization_id"])
        op.create_index("ix_hei_profile_verification", "hei_profile", ["verification_status"])
    else:
        cols = _cols(conn, "hei_profile")
        if "created_at" not in cols:
            _add_ts_col("hei_profile", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("hei_profile", "updated_at")
        if "institution_type" not in cols:
            op.add_column("hei_profile", sa.Column("institution_type", sa.String(100), nullable=True))
        if "established_year" not in cols:
            op.add_column("hei_profile", sa.Column("established_year", sa.Integer(), nullable=True))
        if "description" not in cols:
            op.add_column("hei_profile", sa.Column("description", sa.Text(), nullable=True))
        _add_idx(conn, "ix_hei_profile_org_id", "hei_profile", "organization_id")
        _add_idx(conn, "ix_hei_profile_verification", "hei_profile", "verification_status")
        _add_idx(conn, "ix_hei_profile_institution_type", "hei_profile", "institution_type")

    # ── hei_capability ─────────────────────────────────────────────────────────
    if "hei_capability" not in existing:
        op.create_table(
            "hei_capability",
            sa.Column("hei_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("proficiency_level", sa.String(20), nullable=True),
            sa.Column("evidence_description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"], name="fk_hei_cap_hei", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], name="fk_hei_cap_capability", ondelete="RESTRICT"),
            sa.UniqueConstraint("hei_id", "capability_id", name="uq_hei_capability"),
            sa.PrimaryKeyConstraint("hei_capability_id"),
        )
        op.create_index("ix_hei_capability_hei_id", "hei_capability", ["hei_id"])
        op.create_index("ix_hei_capability_capability_id", "hei_capability", ["capability_id"])
    else:
        cols = _cols(conn, "hei_capability")
        if "proficiency_level" not in cols:
            op.add_column("hei_capability", sa.Column("proficiency_level", sa.String(20), nullable=True))
        if "evidence_description" not in cols:
            op.add_column("hei_capability", sa.Column("evidence_description", sa.Text(), nullable=True))
        if "status" not in cols:
            op.add_column("hei_capability", sa.Column("status", sa.String(20), nullable=True))
            op.execute(text("UPDATE hei_capability SET status = 'Active' WHERE status IS NULL"))
            op.execute(text("ALTER TABLE hei_capability ALTER COLUMN status SET DEFAULT 'Active', ALTER COLUMN status SET NOT NULL"))
        if "created_at" not in cols:
            _add_ts_col("hei_capability", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("hei_capability", "updated_at")
        if not _has_constraint(conn, "hei_capability", "uq_hei_capability"):
            dup = conn.execute(text("SELECT hei_id, capability_id, count(*) FROM hei_capability GROUP BY hei_id, capability_id HAVING count(*) > 1")).fetchone()
            if dup is None:
                op.execute(text("ALTER TABLE hei_capability ADD CONSTRAINT uq_hei_capability UNIQUE (hei_id, capability_id)"))
        _add_idx(conn, "ix_hei_capability_hei_id", "hei_capability", "hei_id")
        _add_idx(conn, "ix_hei_capability_capability_id", "hei_capability", "capability_id")

    # ── faculty_expert_profile ─────────────────────────────────────────────────
    if "faculty_expert_profile" not in existing:
        op.create_table(
            "faculty_expert_profile",
            sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("designation", sa.String(200), nullable=True),
            sa.Column("department", sa.String(200), nullable=True),
            sa.Column("specialization", sa.Text(), nullable=True),
            sa.Column("experience_years", sa.Integer(), nullable=True),
            sa.Column("profile_description", sa.Text(), nullable=True),
            sa.Column("verification_status", sa.String(20), nullable=False, server_default="Pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"], name="fk_faculty_hei", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], name="fk_faculty_user", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("faculty_id"),
        )
        op.create_index("ix_faculty_hei_id", "faculty_expert_profile", ["hei_id"])
        op.create_index("ix_faculty_user_id", "faculty_expert_profile", ["user_id"])
    else:
        cols = _cols(conn, "faculty_expert_profile")
        if "created_at" not in cols:
            _add_ts_col("faculty_expert_profile", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("faculty_expert_profile", "updated_at")
        if "experience_years" not in cols:
            op.add_column("faculty_expert_profile", sa.Column("experience_years", sa.Integer(), nullable=True))
        if "profile_description" not in cols:
            op.add_column("faculty_expert_profile", sa.Column("profile_description", sa.Text(), nullable=True))
        _fix_fk_to_user(conn, "faculty_expert_profile", "user_id", "fk_faculty_user")
        _add_idx(conn, "ix_faculty_hei_id", "faculty_expert_profile", "hei_id")
        _add_idx(conn, "ix_faculty_user_id", "faculty_expert_profile", "user_id")
        _add_idx(conn, "ix_faculty_verification", "faculty_expert_profile", "verification_status")

    # ── faculty_expert_capability ──────────────────────────────────────────────
    if "faculty_expert_capability" not in existing:
        op.create_table(
            "faculty_expert_capability",
            sa.Column("faculty_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("proficiency_level", sa.String(20), nullable=True),
            sa.Column("evidence_description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["faculty_id"], ["faculty_expert_profile.faculty_id"], name="fk_faculty_cap_faculty", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], name="fk_faculty_cap_capability", ondelete="RESTRICT"),
            sa.UniqueConstraint("faculty_id", "capability_id", name="uq_faculty_capability"),
            sa.PrimaryKeyConstraint("faculty_capability_id"),
        )
        op.create_index("ix_faculty_cap_faculty_id", "faculty_expert_capability", ["faculty_id"])
        op.create_index("ix_faculty_cap_capability_id", "faculty_expert_capability", ["capability_id"])
    else:
        cols = _cols(conn, "faculty_expert_capability")
        if "proficiency_level" not in cols:
            op.add_column("faculty_expert_capability", sa.Column("proficiency_level", sa.String(20), nullable=True))
        if "evidence_description" not in cols:
            op.add_column("faculty_expert_capability", sa.Column("evidence_description", sa.Text(), nullable=True))
        if "status" not in cols:
            op.add_column("faculty_expert_capability", sa.Column("status", sa.String(20), nullable=True))
            op.execute(text("UPDATE faculty_expert_capability SET status = 'Active' WHERE status IS NULL"))
            op.execute(text("ALTER TABLE faculty_expert_capability ALTER COLUMN status SET DEFAULT 'Active', ALTER COLUMN status SET NOT NULL"))
        if "created_at" not in cols:
            _add_ts_col("faculty_expert_capability", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("faculty_expert_capability", "updated_at")
        if not _has_constraint(conn, "faculty_expert_capability", "uq_faculty_capability"):
            dup = conn.execute(text("SELECT faculty_expert_id, capability_id, count(*) FROM faculty_expert_capability GROUP BY faculty_expert_id, capability_id HAVING count(*) > 1")).fetchone()
            if dup is None:
                op.execute(text("ALTER TABLE faculty_expert_capability ADD CONSTRAINT uq_faculty_capability UNIQUE (faculty_expert_id, capability_id)"))
        _add_idx(conn, "ix_faculty_cap_faculty_id", "faculty_expert_capability", "faculty_expert_id")
        _add_idx(conn, "ix_faculty_cap_capability_id", "faculty_expert_capability", "capability_id")

    # ── institutional_resource ─────────────────────────────────────────────────
    if "institutional_resource" not in existing:
        op.create_table(
            "institutional_resource",
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hei_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(500), nullable=False),
            sa.Column("resource_type", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.String(500), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=True),
            sa.Column("availability_status", sa.String(30), nullable=False, server_default="Available"),
            sa.Column("verification_status", sa.String(20), nullable=False, server_default="Pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["hei_id"], ["hei_profile.hei_id"], name="fk_resource_hei", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("resource_id"),
        )
        op.create_index("ix_resource_hei_id", "institutional_resource", ["hei_id"])
        op.create_index("ix_resource_type", "institutional_resource", ["resource_type"])
    else:
        cols = _cols(conn, "institutional_resource")
        if "created_at" not in cols:
            _add_ts_col("institutional_resource", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("institutional_resource", "updated_at")
        if "availability_status" not in cols:
            op.add_column("institutional_resource", sa.Column("availability_status", sa.String(30), nullable=True))
            op.execute(text("UPDATE institutional_resource SET availability_status = 'Available' WHERE availability_status IS NULL"))
            op.execute(text("ALTER TABLE institutional_resource ALTER COLUMN availability_status SET DEFAULT 'Available', ALTER COLUMN availability_status SET NOT NULL"))
        _add_idx(conn, "ix_resource_hei_id", "institutional_resource", "hei_id")
        _add_idx(conn, "ix_resource_type", "institutional_resource", "resource_type")
        _add_idx(conn, "ix_resource_verification", "institutional_resource", "verification_status")

    # ── resource_capability ────────────────────────────────────────────────────
    if "resource_capability" not in existing:
        op.create_table(
            "resource_capability",
            sa.Column("resource_capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("proficiency_level", sa.String(20), nullable=True),
            sa.Column("evidence_description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["resource_id"], ["institutional_resource.resource_id"], name="fk_res_cap_resource", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["capability_id"], ["capability.capability_id"], name="fk_res_cap_capability", ondelete="RESTRICT"),
            sa.UniqueConstraint("resource_id", "capability_id", name="uq_resource_capability"),
            sa.PrimaryKeyConstraint("resource_capability_id"),
        )
        op.create_index("ix_resource_cap_resource_id", "resource_capability", ["resource_id"])
        op.create_index("ix_resource_cap_capability_id", "resource_capability", ["capability_id"])
    else:
        cols = _cols(conn, "resource_capability")
        if "proficiency_level" not in cols:
            op.add_column("resource_capability", sa.Column("proficiency_level", sa.String(20), nullable=True))
        if "evidence_description" not in cols:
            op.add_column("resource_capability", sa.Column("evidence_description", sa.Text(), nullable=True))
        if "status" not in cols:
            op.add_column("resource_capability", sa.Column("status", sa.String(20), nullable=True))
            op.execute(text("UPDATE resource_capability SET status = 'Active' WHERE status IS NULL"))
            op.execute(text("ALTER TABLE resource_capability ALTER COLUMN status SET DEFAULT 'Active', ALTER COLUMN status SET NOT NULL"))
        if "created_at" not in cols:
            _add_ts_col("resource_capability", "created_at")
        if "updated_at" not in cols:
            _add_ts_col("resource_capability", "updated_at")
        if not _has_constraint(conn, "resource_capability", "uq_resource_capability"):
            dup = conn.execute(text("SELECT resource_id, capability_id, count(*) FROM resource_capability GROUP BY resource_id, capability_id HAVING count(*) > 1")).fetchone()
            if dup is None:
                op.execute(text("ALTER TABLE resource_capability ADD CONSTRAINT uq_resource_capability UNIQUE (resource_id, capability_id)"))
        _add_idx(conn, "ix_resource_cap_resource_id", "resource_capability", "resource_id")
        _add_idx(conn, "ix_resource_cap_capability_id", "resource_capability", "capability_id")


def downgrade() -> None:
    for t in ["resource_capability", "faculty_expert_capability", "hei_capability",
              "institutional_resource", "faculty_expert_profile", "hei_profile"]:
        op.drop_table(t)
