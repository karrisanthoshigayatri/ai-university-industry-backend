"""Problem and ProblemEvidence service operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.problem import Problem, ProblemEvidence
from app.models.user import User
from app.schemas.problem import EvidenceCreate, EvidenceUpdate, ProblemCreate, ProblemUpdate


# ── Role helpers ───────────────────────────────────────────────────────────────

_PRIVILEGED_ROLES = {"Government Officer", "System Administrator"}


def _is_privileged(user: User) -> bool:
    return user.role in _PRIVILEGED_ROLES


# ── Problem helpers ────────────────────────────────────────────────────────────

def _get_problem_or_404(db: Session, problem_id: UUID) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found",
        )
    return problem


def _assert_problem_owner(problem: Problem, current_user: User) -> None:
    if problem.submitter_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the submitter of this problem",
        )


def _assert_problem_editable(problem: Problem) -> None:
    if problem.current_status != "Submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Problem can only be modified while its status is 'Submitted'",
        )


# ── Problem CRUD ───────────────────────────────────────────────────────────────

def create_problem(db: Session, payload: ProblemCreate, current_user: User) -> Problem:
    """Create a new problem owned by the authenticated user."""

    problem = Problem(
        title=payload.title,
        description=payload.description,
        submitter_id=current_user.user_id,
        source_type=payload.source_type,
        location=payload.location,
        current_status="Submitted",
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def get_problems(db: Session, current_user: User) -> list[Problem]:
    """Return problems visible to this user.

    - Citizens see only their own submissions.
    - Government Officers and System Administrators see all problems.
    """

    if _is_privileged(current_user):
        statement = select(Problem).order_by(Problem.submission_date.desc())
    else:
        statement = (
            select(Problem)
            .where(Problem.submitter_id == current_user.user_id)
            .order_by(Problem.submission_date.desc())
        )
    return list(db.scalars(statement).all())


def get_problem(db: Session, problem_id: UUID, current_user: User) -> Problem:
    """Return a single problem, enforcing visibility rules."""

    problem = _get_problem_or_404(db, problem_id)
    if not _is_privileged(current_user) and problem.submitter_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this problem",
        )
    return problem


def update_problem(
    db: Session, problem_id: UUID, payload: ProblemUpdate, current_user: User
) -> Problem:
    """Update a problem — only the submitter can do this, and only when Submitted."""

    problem = _get_problem_or_404(db, problem_id)
    _assert_problem_owner(problem, current_user)
    _assert_problem_editable(problem)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(problem, field, value)
    db.commit()
    db.refresh(problem)
    return problem


def delete_problem(db: Session, problem_id: UUID, current_user: User) -> None:
    """Delete a problem — only the submitter can do this, and only when Submitted."""

    problem = _get_problem_or_404(db, problem_id)
    _assert_problem_owner(problem, current_user)
    _assert_problem_editable(problem)

    db.delete(problem)
    db.commit()


# ── Evidence helpers ───────────────────────────────────────────────────────────

def _get_evidence_or_404(db: Session, evidence_id: UUID, problem_id: UUID) -> ProblemEvidence:
    evidence = db.get(ProblemEvidence, evidence_id)
    if evidence is None or evidence.problem_id != problem_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return evidence


def _assert_evidence_editable(evidence: ProblemEvidence) -> None:
    if evidence.verification_status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence can only be modified while its verification status is 'Pending'",
        )


# ── Evidence CRUD ──────────────────────────────────────────────────────────────

def create_evidence(
    db: Session, problem_id: UUID, payload: EvidenceCreate, current_user: User
) -> ProblemEvidence:
    """Add evidence to a problem. Only the problem submitter may do this."""

    problem = _get_problem_or_404(db, problem_id)
    _assert_problem_owner(problem, current_user)
    _assert_problem_editable(problem)

    evidence = ProblemEvidence(
        problem_id=problem_id,
        evidence_type=payload.evidence_type,
        file_reference=payload.file_reference,
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        captured_at=payload.captured_at,
        submitted_by=current_user.user_id,
        verification_status="Pending",
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def get_evidence_list(
    db: Session, problem_id: UUID, current_user: User
) -> list[ProblemEvidence]:
    """Return all evidence for a problem (enforces problem visibility)."""

    # Reuse problem visibility check
    get_problem(db, problem_id, current_user)
    statement = (
        select(ProblemEvidence)
        .where(ProblemEvidence.problem_id == problem_id)
        .order_by(ProblemEvidence.created_at)
    )
    return list(db.scalars(statement).all())


def get_evidence(
    db: Session, problem_id: UUID, evidence_id: UUID, current_user: User
) -> ProblemEvidence:
    """Return a single evidence record (enforces problem visibility)."""

    get_problem(db, problem_id, current_user)
    return _get_evidence_or_404(db, evidence_id, problem_id)


def update_evidence(
    db: Session,
    problem_id: UUID,
    evidence_id: UUID,
    payload: EvidenceUpdate,
    current_user: User,
) -> ProblemEvidence:
    """Update evidence — only its submitter, only while Pending."""

    get_problem(db, problem_id, current_user)
    evidence = _get_evidence_or_404(db, evidence_id, problem_id)

    if evidence.submitted_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the submitter of this evidence",
        )
    _assert_evidence_editable(evidence)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(evidence, field, value)
    db.commit()
    db.refresh(evidence)
    return evidence


def delete_evidence(
    db: Session,
    problem_id: UUID,
    evidence_id: UUID,
    current_user: User,
) -> None:
    """Delete evidence — only its submitter, only while Pending."""

    get_problem(db, problem_id, current_user)
    evidence = _get_evidence_or_404(db, evidence_id, problem_id)

    if evidence.submitted_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the submitter of this evidence",
        )
    _assert_evidence_editable(evidence)

    db.delete(evidence)
    db.commit()
