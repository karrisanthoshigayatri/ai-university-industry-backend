"""Fix capability_evidence.verified_by FK: app_user -> user table.

Revision ID: 20260906_ev_fk_patch
Revises: 20260906_ev_ts_patch
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260906_ev_fk_patch"
down_revision: Union[str, None] = "20260906_ev_ts_patch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fks(conn, table: str) -> list[dict]:
    return inspect(conn).get_foreign_keys(table, schema="public")


def upgrade() -> None:
    conn = op.get_bind()
    for fk in _fks(conn, "capability_evidence"):
        if (
            fk["constrained_columns"] == ["verified_by"]
            and fk["referred_table"] == "app_user"
        ):
            op.drop_constraint(fk["name"], "capability_evidence", type_="foreignkey")
            op.create_foreign_key(
                "fk_evidence_verified_by_user",
                "capability_evidence",
                "user",
                ["verified_by"],
                ["user_id"],
                ondelete="SET NULL",
            )
            break


def downgrade() -> None:
    conn = op.get_bind()
    for fk in _fks(conn, "capability_evidence"):
        if fk["name"] == "fk_evidence_verified_by_user":
            op.drop_constraint(fk["name"], "capability_evidence", type_="foreignkey")
            op.create_foreign_key(
                "capability_evidence_verified_by_fkey",
                "capability_evidence",
                "app_user",
                ["verified_by"],
                ["user_id"],
                ondelete="SET NULL",
            )
            break
