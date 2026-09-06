"""AI analysis orchestration service.

Coordinates:
1. Validating that the problem is government-validated before analysis.
2. Calling the AI service (mock or real Qwen2.5).
3. Mapping AI-suggested capability names to canonical Capability records.
4. Persisting results into the four AI tables.
5. Returning a combined response schema.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_analysis import (
    ProblemCategory,
    ProblemPriority,
    ProblemRequirementCapability,
    ProblemRequirementProfile,
)
from app.models.problem import Problem
from app.models.user import User
from app.services.ai_service import AIAnalysisOutput, get_ai_service


logger = logging.getLogger(__name__)

# Problem statuses that mean the problem has been government validated
_VALIDATED_STATUSES = {"Validated"}

# Roles that can see any problem (needed for visibility check)
_PRIVILEGED_ROLES = {"Government Officer", "System Administrator"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_problem_or_404(db: Session, problem_id: UUID) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return problem


def _assert_can_access(problem: Problem, current_user: User) -> None:
    if current_user.role in _PRIVILEGED_ROLES:
        return
    if problem.submitter_id == current_user.user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this problem.",
    )


def _lookup_capability(db: Session, name: str) -> UUID | None:
    """Try to find an existing Capability by name (case-insensitive).
    Returns the UUID if found, None otherwise.
    """
    from app.models.ai_analysis import ProblemCategory  # noqa: F401 — ensure model loaded
    # Capability model lives in a different table; use raw SQL-ish query
    from sqlalchemy import text
    result = db.execute(
        text(
            "SELECT capability_id FROM capability "
            "WHERE lower(name) = lower(:name) LIMIT 1"
        ),
        {"name": name},
    ).fetchone()
    return UUID(str(result[0])) if result else None


def _audit(event: str, actor_id: UUID, detail: str) -> None:
    logger.info("[AUDIT] event=%s actor=%s detail=%s", event, actor_id, detail)


# ── Main analysis function ────────────────────────────────────────────────────

def run_ai_analysis(
    db: Session,
    problem_id: UUID,
    current_user: User,
) -> dict:
    """Run Qwen2.5 analysis on a validated problem.

    Business rules:
    - Problem must exist and be in 'Validated' status.
    - User must have access to the problem.
    - AI output is validated via Pydantic before any DB write.
    - If AI returns invalid output, nothing is written to the DB.
    - Re-running analysis adds new records (history is preserved).
    - AI does NOT change PROBLEM.current_status.
    """
    settings = get_settings()
    problem = _get_problem_or_404(db, problem_id)
    _assert_can_access(problem, current_user)

    # Enforce: must be government-validated first
    if problem.current_status not in _VALIDATED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Problem must be government validated before AI analysis. "
                f"Current status: '{problem.current_status}'. "
                "Please submit for government validation first."
            ),
        )

    # Call AI service
    ai_service = get_ai_service()
    model_version = settings.qwen_model

    try:
        output: AIAnalysisOutput = ai_service.analyse(
            title=problem.title,
            description=problem.description,
            location=problem.location or "",
            source_type=problem.source_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    now = datetime.now(timezone.utc)

    # ── Persist ProblemCategory records ───────────────────────────────────────
    saved_categories = []
    for cat_item in output.categories:
        cap_id = _lookup_capability(db, cat_item.capability_name)
        cat = ProblemCategory(
            problem_id=problem_id,
            capability_id=cap_id,
            category_role=cat_item.category_role,
            confidence=cat_item.confidence,
            model_version=model_version,
            generated_at=now,
        )
        db.add(cat)
        saved_categories.append({
            "capability_name": cat_item.capability_name,
            "capability_id": str(cap_id) if cap_id else None,
            "mapped": cap_id is not None,
            "category_role": cat_item.category_role,
            "confidence": cat_item.confidence,
        })

    # ── Persist ProblemPriority ────────────────────────────────────────────────
    pri = ProblemPriority(
        problem_id=problem_id,
        priority_level=output.priority.priority_level,
        priority_score=output.priority.priority_score,
        severity_score=output.priority.severity_score,
        urgency_score=output.priority.urgency_score,
        affected_population=output.priority.affected_population,
        geographic_spread=output.priority.geographic_spread,
        feasibility_score=output.priority.feasibility_score,
        strategic_relevance=output.priority.strategic_relevance,
        factors=output.priority.factors,
        model_version=model_version,
        generated_at=now,
    )
    db.add(pri)

    # ── Persist ProblemRequirementProfile ─────────────────────────────────────
    profile = ProblemRequirementProfile(
        problem_id=problem_id,
        required_support=output.requirements.required_support,
        geographic_requirements=output.requirements.geographic_requirements,
        eligibility_requirements=output.requirements.eligibility_requirements,
        timeline=output.requirements.timeline,
        constraints=output.requirements.constraints,
        confidence=0.85 if settings.ai_enabled else 0.70,
        model_version=model_version,
        generated_at=now,
    )
    db.add(profile)
    db.flush()  # get profile PK before adding children

    # ── Persist ProblemRequirementCapability records ───────────────────────────
    saved_capabilities = []
    for cap_item in output.capabilities:
        cap_id = _lookup_capability(db, cap_item.capability_name)
        req_cap = ProblemRequirementCapability(
            requirement_profile_id=profile.requirement_profile_id,
            capability_id=cap_id,
            requirement_type=cap_item.requirement_type,
            required_level=cap_item.required_level,
            criticality=cap_item.criticality,
            confidence=cap_item.confidence,
        )
        db.add(req_cap)
        saved_capabilities.append({
            "capability_name": cap_item.capability_name,
            "capability_id": str(cap_id) if cap_id else None,
            "mapped": cap_id is not None,
            "requirement_type": cap_item.requirement_type,
            "required_level": cap_item.required_level,
            "criticality": cap_item.criticality,
            "confidence": cap_item.confidence,
        })

    db.commit()
    db.refresh(pri)
    db.refresh(profile)

    _audit(
        "AI_PROBLEM_ANALYSIS",
        current_user.user_id,
        f"problem={problem_id} model={model_version} categories={len(saved_categories)} caps={len(saved_capabilities)}",
    )

    return {
        "problem_id": str(problem_id),
        "categories": saved_categories,
        "priority": {
            "priority_id": str(pri.priority_id),
            "priority_level": pri.priority_level,
            "priority_score": pri.priority_score,
            "severity_score": pri.severity_score,
            "urgency_score": pri.urgency_score,
            "affected_population": pri.affected_population,
            "geographic_spread": pri.geographic_spread,
            "feasibility_score": pri.feasibility_score,
            "strategic_relevance": pri.strategic_relevance,
            "factors": pri.factors,
        },
        "requirements": {
            "requirement_profile_id": str(profile.requirement_profile_id),
            "required_support": profile.required_support,
            "geographic_requirements": profile.geographic_requirements,
            "eligibility_requirements": profile.eligibility_requirements,
            "timeline": profile.timeline,
            "constraints": profile.constraints,
            "confidence": profile.confidence,
        },
        "capabilities": saved_capabilities,
        "model_version": model_version,
        "generated_at": now.isoformat(),
    }
