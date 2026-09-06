"""Routes for CapabilityEvidence, Availability, and EntityConstraint."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.evidence import (
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
    ConstraintCreate,
    ConstraintResponse,
    ConstraintUpdate,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    EvidenceVerify,
)
from app.services.evidence import (
    create_availability,
    create_constraint,
    create_evidence,
    get_availability_for_entity,
    get_constraints_for_entity,
    get_evidence_for_entity,
    update_availability,
    update_constraint,
    update_evidence,
    verify_evidence,
)

router = APIRouter(tags=["capability-evidence"])

DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Capability Evidence ────────────────────────────────────────────────────────

@router.post(
    "/api/capability-evidence",
    response_model=EvidenceResponse,
    status_code=201,
    summary="Create capability evidence",
)
def create_evidence_route(payload: EvidenceCreate, db: DB, current_user: CU) -> EvidenceResponse:
    """Create evidence for any supported entity type."""
    return create_evidence(db, payload, current_user)


@router.get(
    "/api/capability-evidence/{entity_type}/{entity_id}",
    response_model=list[EvidenceResponse],
    summary="List evidence for an entity",
)
def list_evidence(entity_type: str, entity_id: UUID, db: DB, _: CU) -> list[EvidenceResponse]:
    """Return all evidence records for the given entity."""
    return get_evidence_for_entity(db, entity_type, entity_id)


@router.put(
    "/api/capability-evidence/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Update capability evidence",
)
def update_evidence_route(
    evidence_id: UUID, payload: EvidenceUpdate, db: DB, current_user: CU
) -> EvidenceResponse:
    return update_evidence(db, evidence_id, payload, current_user)


@router.put(
    "/api/capability-evidence/{evidence_id}/verify",
    response_model=EvidenceResponse,
    summary="Verify evidence (Government Officer / System Admin)",
)
def verify_evidence_route(
    evidence_id: UUID, payload: EvidenceVerify, db: DB, current_user: CU
) -> EvidenceResponse:
    """Set verification status. verified_by and verified_at are server-side only."""
    return verify_evidence(db, evidence_id, payload, current_user)


# ── Availability ───────────────────────────────────────────────────────────────

@router.post(
    "/api/availability",
    response_model=AvailabilityResponse,
    status_code=201,
    summary="Create availability record",
)
def create_availability_route(
    payload: AvailabilityCreate, db: DB, current_user: CU
) -> AvailabilityResponse:
    return create_availability(db, payload, current_user)


@router.get(
    "/api/availability/{entity_type}/{entity_id}",
    response_model=list[AvailabilityResponse],
    summary="List availability for an entity",
)
def list_availability(
    entity_type: str, entity_id: UUID, db: DB, _: CU
) -> list[AvailabilityResponse]:
    return get_availability_for_entity(db, entity_type, entity_id)


@router.put(
    "/api/availability/{availability_id}",
    response_model=AvailabilityResponse,
    summary="Update availability record",
)
def update_availability_route(
    availability_id: UUID, payload: AvailabilityUpdate, db: DB, current_user: CU
) -> AvailabilityResponse:
    return update_availability(db, availability_id, payload, current_user)


# ── Constraints ────────────────────────────────────────────────────────────────

@router.post(
    "/api/constraints",
    response_model=ConstraintResponse,
    status_code=201,
    summary="Create entity constraint",
)
def create_constraint_route(
    payload: ConstraintCreate, db: DB, current_user: CU
) -> ConstraintResponse:
    return create_constraint(db, payload, current_user)


@router.get(
    "/api/constraints/{entity_type}/{entity_id}",
    response_model=list[ConstraintResponse],
    summary="List constraints for an entity",
)
def list_constraints(
    entity_type: str, entity_id: UUID, db: DB, _: CU
) -> list[ConstraintResponse]:
    return get_constraints_for_entity(db, entity_type, entity_id)


@router.put(
    "/api/constraints/{constraint_id}",
    response_model=ConstraintResponse,
    summary="Update entity constraint",
)
def update_constraint_route(
    constraint_id: UUID, payload: ConstraintUpdate, db: DB, current_user: CU
) -> ConstraintResponse:
    return update_constraint(db, constraint_id, payload, current_user)
