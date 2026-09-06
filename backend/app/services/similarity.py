"""Similarity search and PROBLEM_RELATION management.

Business rules enforced here:
- The AI may ONLY create 'Similar' relation records (human_confirmation=False).
- Duplicate / Consolidated / Linked decisions require a human (Government
  Officer or System Administrator) via the decision endpoint.
- Duplicate relation records for the same source↔target pair are never created.
- When a human confirms Duplicate or Linked, the relevant problem status is
  updated to match.
- An audit hook is provided for a future Audit Log step.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.problem import Problem, ProblemRelation
from app.models.user import User
from app.schemas.similarity import (
    RelationDecisionRequest,
    RelationResponse,
    SimilarityCandidate,
    SimilarityCheckResponse,
)
from app.services.embedding import get_embedding_service


logger = logging.getLogger(__name__)

# Roles allowed to make final Duplicate / Consolidated / Linked decisions
_DECISION_ROLES = {"Government Officer", "System Administrator"}

# Problem statuses that map to human-confirmed relation types
_RELATION_STATUS_MAP = {
    "Duplicate": "Linked to Existing Problem",
    "Linked": "Linked to Existing Problem",
    "Consolidated": "Linked to Existing Problem",
}


# ── Audit hook (placeholder for Step N) ───────────────────────────────────────

def _audit(event: str, actor_id: UUID | None, detail: str) -> None:
    """Log an auditable event.  Replace with Audit Log service when ready."""
    logger.info("[AUDIT] event=%s actor=%s detail=%s", event, actor_id, detail)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_problem_or_404(db: Session, problem_id: UUID) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found",
        )
    return problem


def _get_relation_or_404(db: Session, relation_id: UUID) -> ProblemRelation:
    relation = db.get(ProblemRelation, relation_id)
    if relation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem relation not found",
        )
    return relation


def _build_text(problem: Problem) -> str:
    """Combine problem fields into a single text for embedding."""
    parts = [problem.title, problem.description]
    if problem.location:
        parts.append(problem.location)
    return " ".join(parts)


def _relation_exists(
    db: Session, source_id: UUID, target_id: UUID
) -> bool:
    """Return True if a relation (in either direction) already exists."""
    stmt = select(ProblemRelation).where(
        or_(
            and_(
                ProblemRelation.source_problem_id == source_id,
                ProblemRelation.target_problem_id == target_id,
            ),
            and_(
                ProblemRelation.source_problem_id == target_id,
                ProblemRelation.target_problem_id == source_id,
            ),
        )
    )
    return db.scalar(stmt) is not None


# ── Similarity check ───────────────────────────────────────────────────────────

def run_similarity_check(
    db: Session,
    problem_id: UUID,
    current_user: User,
) -> SimilarityCheckResponse:
    """Compare *problem_id* against all other Submitted problems.

    - Fetches all candidate problems (excluding the source itself).
    - Embeds each using the configured embedding service.
    - Returns the top-K candidates above the similarity threshold.
    - Persists 'Similar' PROBLEM_RELATION records for new matches.
    - Never marks any problem as Duplicate automatically.
    """
    settings = get_settings()
    source = _get_problem_or_404(db, problem_id)

    # Visibility check — reuse existing logic
    _assert_can_view(source, current_user)

    emb_service = get_embedding_service()
    source_vec = emb_service.embed(_build_text(source))

    # Load all other problems that are candidates for comparison
    candidates_stmt = select(Problem).where(Problem.problem_id != problem_id)
    candidates: list[Problem] = list(db.scalars(candidates_stmt).all())

    scored: list[tuple[float, Problem]] = []
    for candidate in candidates:
        candidate_vec = emb_service.embed(_build_text(candidate))
        score = emb_service.cosine_similarity(source_vec, candidate_vec)
        if score >= settings.similarity_threshold:
            scored.append((score, candidate))

    # Sort descending by score, take top-K
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[: settings.similarity_top_k]

    # Persist new Similar relations (idempotent — skip if already exists)
    new_relations: list[ProblemRelation] = []
    for score, candidate in top:
        if not _relation_exists(db, problem_id, candidate.problem_id):
            reason = (
                f"Cosine similarity {score:.3f} between "
                f"'{source.title[:60]}' and '{candidate.title[:60]}'."
            )
            relation = ProblemRelation(
                source_problem_id=problem_id,
                target_problem_id=candidate.problem_id,
                relation_type="Similar",
                similarity_score=round(score, 4),
                ai_reason=reason,
                human_confirmation=False,
                decided_by=None,
                decided_at=None,
            )
            db.add(relation)
            new_relations.append(relation)

    if new_relations:
        # Update source problem status to 'Similar Found' if matches exist
        if source.current_status == "Submitted":
            source.current_status = "Similar Found"
        db.commit()
        for r in new_relations:
            db.refresh(r)
    elif not top:
        db.commit()  # no-op but keeps session clean

    _audit(
        "AI_SIMILARITY_CHECK",
        current_user.user_id,
        f"problem={problem_id} candidates_found={len(top)} new_relations={len(new_relations)}",
    )

    result_candidates = [
        SimilarityCandidate(
            candidate_problem_id=candidate.problem_id,
            similarity_score=round(score, 4),
            relation_type="Similar",
            ai_reason=(
                f"Cosine similarity {score:.3f} — "
                f"'{candidate.title[:80]}'"
            ),
            candidate_title=candidate.title,
            candidate_status=candidate.current_status,
        )
        for score, candidate in top
    ]

    return SimilarityCheckResponse(
        problem_id=problem_id,
        candidates=result_candidates,
        threshold_used=settings.similarity_threshold,
        top_k_used=settings.similarity_top_k,
        embedding_mode="bge" if settings.embedding_enabled else "mock",
    )


# ── Human decision ─────────────────────────────────────────────────────────────

def decide_relation(
    db: Session,
    relation_id: UUID,
    payload: RelationDecisionRequest,
    current_user: User,
) -> RelationResponse:
    """Record a human decision on an AI-generated or existing relation.

    Authorization:
    - Any authenticated user can confirm 'Similar' or 'Related'.
    - Only Government Officers and System Administrators may confirm
      'Duplicate', 'Consolidated', or 'Linked'.

    Status side-effects:
    - Confirming Duplicate / Linked / Consolidated sets the SOURCE problem
      status to 'Linked to Existing Problem'.
    """
    privileged_types = {"Duplicate", "Consolidated", "Linked"}

    if payload.relation_type in privileged_types and current_user.role not in _DECISION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only Government Officers or System Administrators may confirm "
                "Duplicate, Consolidated, or Linked relationships."
            ),
        )

    relation = _get_relation_or_404(db, relation_id)

    relation.relation_type = payload.relation_type
    relation.human_confirmation = payload.confirmed
    relation.decided_by = current_user.user_id
    relation.decided_at = datetime.now(timezone.utc)

    # Side-effect: update source problem status for privileged confirmations
    if payload.confirmed and payload.relation_type in privileged_types:
        source = db.get(Problem, relation.source_problem_id)
        if source is not None:
            source.current_status = _RELATION_STATUS_MAP[payload.relation_type]

    db.commit()
    db.refresh(relation)

    _audit(
        "HUMAN_RELATION_DECISION",
        current_user.user_id,
        (
            f"relation={relation_id} type={payload.relation_type} "
            f"confirmed={payload.confirmed}"
        ),
    )

    return RelationResponse.model_validate(relation)


# ── Visibility helper (shared with problem service) ────────────────────────────

def _assert_can_view(problem: Problem, current_user: User) -> None:
    privileged = current_user.role in {"Government Officer", "System Administrator"}
    if not privileged and problem.submitter_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this problem.",
        )
