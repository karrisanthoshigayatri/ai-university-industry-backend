"""Service layer for CapabilityEvidence, Availability, and EntityConstraint."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.models.evidence import (
    Availability,
    CapabilityEvidence,
    EntityConstraint,
)
from app.models.hei import (
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
)
from app.models.user import User
from app.schemas.evidence import (
    AvailabilityCreate,
    AvailabilityUpdate,
    ConstraintCreate,
    ConstraintUpdate,
    EvidenceCreate,
    EvidenceUpdate,
    EvidenceVerify,
)


# ── Role sets ──────────────────────────────────────────────────────────────────

_SYS_ADMIN = {"System Administrator"}
_HEI_WRITE = {"HEI Administrator", "System Administrator"}
_VERIFY_ROLES = {"Government Officer", "System Administrator"}
_WRITE_ROLES = {"HEI Administrator", "Government Officer", "System Administrator"}

# ── Allowed entity types ───────────────────────────────────────────────────────

_ALLOWED_ENTITY_TYPES = {
    "hei_capability",
    "faculty_expertise",
    "institutional_resource",
    "partner_capability",
}


# ══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get_or_404(db: Session, model, pk_value, label: str):
    obj = db.get(model, pk_value)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _validate_entity_type(entity_type: str) -> None:
    if entity_type not in _ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. "
                   f"Allowed: {sorted(_ALLOWED_ENTITY_TYPES)}",
        )


def _resolve_entity_hei(db: Session, entity_type: str, entity_id: UUID) -> HeiProfile:
    """Return the HeiProfile that owns the given entity, or raise 404/400."""
    if entity_type == "hei_capability":
        obj = db.get(HeiCapability, entity_id)
        if obj is None:
            raise HTTPException(status_code=404, detail="HEI capability not found")
        return _get_or_404(db, HeiProfile, obj.hei_id, "HEI profile")

    if entity_type == "faculty_expertise":
        obj = db.get(FacultyExpertProfile, entity_id)
        if obj is None:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
        return _get_or_404(db, HeiProfile, obj.hei_id, "HEI profile")

    if entity_type == "institutional_resource":
        obj = db.get(InstitutionalResource, entity_id)
        if obj is None:
            raise HTTPException(status_code=404, detail="Institutional resource not found")
        return _get_or_404(db, HeiProfile, obj.hei_id, "HEI profile")

    # partner_capability — no HEI link yet, skip ownership check
    return None  # type: ignore[return-value]


def _assert_entity_exists(db: Session, entity_type: str, entity_id: UUID) -> None:
    """Raise 404 if the entity_id does not exist for the given entity_type."""
    _validate_entity_type(entity_type)
    if entity_type == "hei_capability":
        if db.get(HeiCapability, entity_id) is None:
            raise HTTPException(status_code=404, detail="HEI capability not found")
    elif entity_type == "faculty_expertise":
        if db.get(FacultyExpertProfile, entity_id) is None:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
    elif entity_type == "institutional_resource":
        if db.get(InstitutionalResource, entity_id) is None:
            raise HTTPException(status_code=404, detail="Institutional resource not found")
    # partner_capability: existence not validated until partner registry exists


def _assert_write_permission(
    db: Session, current_user: User, entity_type: str, entity_id: UUID
) -> None:
    """Enforce HEI-scoped write permission."""
    if current_user.role in _SYS_ADMIN:
        return
    if current_user.role == "HEI Administrator":
        hei = _resolve_entity_hei(db, entity_type, entity_id)
        if hei is None:
            # partner_capability — only System Admin for now
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        if current_user.organization_id != hei.organization_id:
            raise HTTPException(
                status_code=403,
                detail="HEI Administrators can only manage their own HEI entities.",
            )
        return
    if current_user.role == "Government Officer":
        # Gov officers can write evidence (for verification) but not availability/constraints
        # Granular check done in callers
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions.")


# ══════════════════════════════════════════════════════════════════════════════
# CapabilityEvidence
# ══════════════════════════════════════════════════════════════════════════════

def create_evidence(
    db: Session, payload: EvidenceCreate, current_user: User
) -> CapabilityEvidence:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    _validate_entity_type(payload.entity_type)
    _assert_entity_exists(db, payload.entity_type, payload.entity_id)

    if payload.capability_id is not None:
        if db.get(Capability, payload.capability_id) is None:
            raise HTTPException(status_code=404, detail="Capability not found")

    # HEI Admins: scope check
    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, payload.entity_type, payload.entity_id)

    obj = CapabilityEvidence(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_evidence_for_entity(
    db: Session, entity_type: str, entity_id: UUID
) -> list[CapabilityEvidence]:
    _validate_entity_type(entity_type)
    return list(
        db.scalars(
            select(CapabilityEvidence).where(
                CapabilityEvidence.entity_type == entity_type,
                CapabilityEvidence.entity_id == entity_id,
            ).order_by(CapabilityEvidence.created_at.desc())
        ).all()
    )


def update_evidence(
    db: Session, evidence_id: UUID, payload: EvidenceUpdate, current_user: User
) -> CapabilityEvidence:
    obj = _get_or_404(db, CapabilityEvidence, evidence_id, "Evidence")

    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, obj.entity_type, obj.entity_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def verify_evidence(
    db: Session, evidence_id: UUID, payload: EvidenceVerify, current_user: User
) -> CapabilityEvidence:
    """Government Officer or System Admin verifies evidence.

    verified_by and verified_at are set server-side from the authenticated user.
    """
    if current_user.role not in _VERIFY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only Government Officers or System Administrators can verify evidence.",
        )
    obj = _get_or_404(db, CapabilityEvidence, evidence_id, "Evidence")
    obj.verification_status = payload.verification_status
    # Server-side injection — never taken from client payload
    obj.verified_by = current_user.user_id
    obj.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# Availability
# ══════════════════════════════════════════════════════════════════════════════

def create_availability(
    db: Session, payload: AvailabilityCreate, current_user: User
) -> Availability:
    if current_user.role not in _HEI_WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    _validate_entity_type(payload.entity_type)
    _assert_entity_exists(db, payload.entity_type, payload.entity_id)

    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, payload.entity_type, payload.entity_id)

    obj = Availability(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_availability_for_entity(
    db: Session, entity_type: str, entity_id: UUID
) -> list[Availability]:
    _validate_entity_type(entity_type)
    return list(
        db.scalars(
            select(Availability).where(
                Availability.entity_type == entity_type,
                Availability.entity_id == entity_id,
            ).order_by(Availability.created_at.desc())
        ).all()
    )


def update_availability(
    db: Session, availability_id: UUID, payload: AvailabilityUpdate, current_user: User
) -> Availability:
    obj = _get_or_404(db, Availability, availability_id, "Availability")

    if current_user.role not in _HEI_WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, obj.entity_type, obj.entity_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# EntityConstraint
# ══════════════════════════════════════════════════════════════════════════════

def create_constraint(
    db: Session, payload: ConstraintCreate, current_user: User
) -> EntityConstraint:
    if current_user.role not in _HEI_WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    _validate_entity_type(payload.entity_type)
    _assert_entity_exists(db, payload.entity_type, payload.entity_id)

    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, payload.entity_type, payload.entity_id)

    obj = EntityConstraint(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_constraints_for_entity(
    db: Session, entity_type: str, entity_id: UUID
) -> list[EntityConstraint]:
    _validate_entity_type(entity_type)
    return list(
        db.scalars(
            select(EntityConstraint).where(
                EntityConstraint.entity_type == entity_type,
                EntityConstraint.entity_id == entity_id,
            ).order_by(EntityConstraint.created_at.desc())
        ).all()
    )


def update_constraint(
    db: Session, constraint_id: UUID, payload: ConstraintUpdate, current_user: User
) -> EntityConstraint:
    obj = _get_or_404(db, EntityConstraint, constraint_id, "Constraint")

    if current_user.role not in _HEI_WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    if current_user.role == "HEI Administrator":
        _assert_write_permission(db, current_user, obj.entity_type, obj.entity_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj
