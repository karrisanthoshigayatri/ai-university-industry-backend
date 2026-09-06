"""Schemas for similarity check and relation decision endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


RelationType = Literal["Similar", "Duplicate", "Related", "Consolidated", "Linked"]


# ── Similarity check ───────────────────────────────────────────────────────────

class SimilarityCandidate(BaseModel):
    """One candidate problem returned by the similarity check."""

    candidate_problem_id: UUID
    similarity_score: float = Field(ge=0.0, le=1.0)
    relation_type: RelationType
    ai_reason: str
    candidate_title: str
    candidate_status: str


class SimilarityCheckResponse(BaseModel):
    """Full response from POST /api/problems/{id}/similarity-check."""

    problem_id: UUID
    candidates: list[SimilarityCandidate]
    threshold_used: float
    top_k_used: int
    embedding_mode: Literal["bge", "mock"]


# ── Relation response ──────────────────────────────────────────────────────────

class RelationResponse(BaseModel):
    """Full PROBLEM_RELATION record returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    relation_id: UUID
    source_problem_id: UUID
    target_problem_id: UUID
    relation_type: RelationType
    similarity_score: float | None
    ai_reason: str | None
    human_confirmation: bool
    decided_by: UUID | None
    decided_at: datetime | None
    created_at: datetime


# ── Human decision request ─────────────────────────────────────────────────────

class RelationDecisionRequest(BaseModel):
    """Payload for PUT /api/problems/relations/{relation_id}/decision."""

    relation_type: RelationType
    confirmed: bool = Field(
        description=(
            "True = human confirms this relationship. "
            "False = human rejects the AI recommendation."
        )
    )
