"""HEI Match model — stores a matching snapshot for a problem↔HEI pair.

Column names align with the existing Supabase hei_match table exactly.
Missing columns (created_at) are added via the 20260906_hei_match migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


MODEL_VERSION = "hei-matching-v1"


class HeiMatch(Base):
    """Snapshot of one HEI match result for a problem."""

    __tablename__ = "hei_match"
    __table_args__ = (
        Index("ix_hei_match_problem_id", "problem_id"),
        Index("ix_hei_match_hei_id", "hei_id"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        nullable=False,
    )
    hei_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hei_profile.hei_id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # JSONB columns — store Python lists/dicts
    matched_capabilities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unmet_requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    constraint_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # DB column is 'reasons'; Python attribute is match_reasons for API clarity
    match_reasons: Mapped[list | None] = mapped_column(
        "reasons", JSONB, nullable=True
    )

    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DB column is 'generated_at' (TIMESTAMP without tz);
    # we also add created_at via migration for consistency
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    problem: Mapped["Problem"] = relationship()  # type: ignore[name-defined]
    hei: Mapped["HeiProfile"] = relationship()  # type: ignore[name-defined]
