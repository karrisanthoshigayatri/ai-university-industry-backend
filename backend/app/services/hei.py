"""HEI registry service operations."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas.hei import (
    FacultyCapabilityCreate,
    FacultyCapabilityUpdate,
    FacultyCreate,
    FacultyUpdate,
    HeiCapabilityCreate,
    HeiCapabilityUpdate,
    HeiCreate,
    HeiUpdate,
    ResourceCapabilityCreate,
    ResourceCapabilityUpdate,
    ResourceCreate,
    ResourceUpdate,
)


_ADMIN_ROLES = {"System Administrator"}
_HEI_WRITE_ROLES = {"HEI Administrator", "System Administrator"}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _get_or_404(db: Session, model, pk_value, label: str):
    obj = db.get(model, pk_value)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _get_capability_or_404(db: Session, capability_id: UUID) -> Capability:
    cap = db.get(Capability, capability_id)
    if cap is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    return cap


def _assert_hei_write(current_user: User, hei: HeiProfile) -> None:
    """Allow System Admin unrestricted; HEI Admin only for their own HEI."""
    if current_user.role in _ADMIN_ROLES:
        return
    if current_user.role == "HEI Administrator":
        # Must belong to the same organization as the HEI
        if current_user.organization_id != hei.organization_id:
            raise HTTPException(
                status_code=403,
                detail="HEI Administrators can only manage their own HEI.",
            )
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions.")


def _assert_read(current_user: User) -> None:
    """Any authenticated user may read."""
    pass  # get_current_user dependency already ensures authentication


# ── HEI Profile ────────────────────────────────────────────────────────────────

def create_hei(db: Session, payload: HeiCreate, current_user: User) -> HeiProfile:
    if current_user.role not in _HEI_WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    org = db.get(Organization, payload.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.organization_type != "HEI":
        raise HTTPException(
            status_code=400,
            detail="Only organizations with type 'HEI' can have an HEI profile.",
        )

    existing = db.scalar(
        select(HeiProfile).where(HeiProfile.organization_id == payload.organization_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="This organization already has an HEI profile.")

    hei = HeiProfile(**payload.model_dump())
    db.add(hei)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="HEI profile already exists.") from exc
    db.refresh(hei)
    return hei


def get_heis(db: Session) -> list[HeiProfile]:
    return list(db.scalars(select(HeiProfile).order_by(HeiProfile.created_at.desc())).all())


def get_hei(db: Session, hei_id: UUID) -> HeiProfile:
    return _get_or_404(db, HeiProfile, hei_id, "HEI profile")


def update_hei(db: Session, hei_id: UUID, payload: HeiUpdate, current_user: User) -> HeiProfile:
    hei = _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(hei, field, value)
    db.commit()
    db.refresh(hei)
    return hei


# ── HEI Capability ─────────────────────────────────────────────────────────────

def add_hei_capability(
    db: Session, hei_id: UUID, payload: HeiCapabilityCreate, current_user: User
) -> HeiCapability:
    hei = _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    _get_capability_or_404(db, payload.capability_id)

    existing = db.scalar(
        select(HeiCapability).where(
            HeiCapability.hei_id == hei_id,
            HeiCapability.capability_id == payload.capability_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="This HEI already has this capability.")

    obj = HeiCapability(hei_id=hei_id, **payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate HEI capability.") from exc
    db.refresh(obj)
    return obj


def get_hei_capabilities(db: Session, hei_id: UUID) -> list[HeiCapability]:
    _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    return list(db.scalars(select(HeiCapability).where(HeiCapability.hei_id == hei_id)).all())


def update_hei_capability(
    db: Session, hei_id: UUID, hei_capability_id: UUID, payload: HeiCapabilityUpdate, current_user: User
) -> HeiCapability:
    hei = _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    obj = _get_or_404(db, HeiCapability, hei_capability_id, "HEI capability")
    if obj.hei_id != hei_id:
        raise HTTPException(status_code=404, detail="HEI capability not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── Faculty ────────────────────────────────────────────────────────────────────

def create_faculty(
    db: Session, hei_id: UUID, payload: FacultyCreate, current_user: User
) -> FacultyExpertProfile:
    hei = _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)

    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

    obj = FacultyExpertProfile(hei_id=hei_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_faculty_list(db: Session, hei_id: UUID) -> list[FacultyExpertProfile]:
    _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    return list(db.scalars(select(FacultyExpertProfile).where(FacultyExpertProfile.hei_id == hei_id)).all())


def get_faculty(db: Session, faculty_id: UUID) -> FacultyExpertProfile:
    return _get_or_404(db, FacultyExpertProfile, faculty_id, "Faculty profile")


def update_faculty(
    db: Session, faculty_id: UUID, payload: FacultyUpdate, current_user: User
) -> FacultyExpertProfile:
    faculty = _get_or_404(db, FacultyExpertProfile, faculty_id, "Faculty profile")
    hei = _get_or_404(db, HeiProfile, faculty.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(faculty, field, value)
    db.commit()
    db.refresh(faculty)
    return faculty


# ── Faculty Capability ─────────────────────────────────────────────────────────

def add_faculty_capability(
    db: Session, faculty_id: UUID, payload: FacultyCapabilityCreate, current_user: User
) -> FacultyExpertCapability:
    faculty = _get_or_404(db, FacultyExpertProfile, faculty_id, "Faculty profile")
    hei = _get_or_404(db, HeiProfile, faculty.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    _get_capability_or_404(db, payload.capability_id)

    existing = db.scalar(
        select(FacultyExpertCapability).where(
            FacultyExpertCapability.faculty_id == faculty_id,
            FacultyExpertCapability.capability_id == payload.capability_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="This faculty already has this capability.")

    obj = FacultyExpertCapability(faculty_id=faculty_id, **payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate faculty capability.") from exc
    db.refresh(obj)
    return obj


def get_faculty_capabilities(db: Session, faculty_id: UUID) -> list[FacultyExpertCapability]:
    _get_or_404(db, FacultyExpertProfile, faculty_id, "Faculty profile")
    return list(db.scalars(
        select(FacultyExpertCapability).where(FacultyExpertCapability.faculty_id == faculty_id)
    ).all())


def update_faculty_capability(
    db: Session, faculty_id: UUID, faculty_capability_id: UUID,
    payload: FacultyCapabilityUpdate, current_user: User
) -> FacultyExpertCapability:
    faculty = _get_or_404(db, FacultyExpertProfile, faculty_id, "Faculty profile")
    hei = _get_or_404(db, HeiProfile, faculty.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    obj = _get_or_404(db, FacultyExpertCapability, faculty_capability_id, "Faculty capability")
    if obj.faculty_id != faculty_id:
        raise HTTPException(status_code=404, detail="Faculty capability not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── Institutional Resource ─────────────────────────────────────────────────────

def create_resource(
    db: Session, hei_id: UUID, payload: ResourceCreate, current_user: User
) -> InstitutionalResource:
    hei = _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    obj = InstitutionalResource(hei_id=hei_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_resources(db: Session, hei_id: UUID) -> list[InstitutionalResource]:
    _get_or_404(db, HeiProfile, hei_id, "HEI profile")
    return list(db.scalars(select(InstitutionalResource).where(InstitutionalResource.hei_id == hei_id)).all())


def get_resource(db: Session, resource_id: UUID) -> InstitutionalResource:
    return _get_or_404(db, InstitutionalResource, resource_id, "Resource")


def update_resource(
    db: Session, resource_id: UUID, payload: ResourceUpdate, current_user: User
) -> InstitutionalResource:
    resource = _get_or_404(db, InstitutionalResource, resource_id, "Resource")
    hei = _get_or_404(db, HeiProfile, resource.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)
    db.commit()
    db.refresh(resource)
    return resource


# ── Resource Capability ────────────────────────────────────────────────────────

def add_resource_capability(
    db: Session, resource_id: UUID, payload: ResourceCapabilityCreate, current_user: User
) -> ResourceCapability:
    resource = _get_or_404(db, InstitutionalResource, resource_id, "Resource")
    hei = _get_or_404(db, HeiProfile, resource.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    _get_capability_or_404(db, payload.capability_id)

    existing = db.scalar(
        select(ResourceCapability).where(
            ResourceCapability.resource_id == resource_id,
            ResourceCapability.capability_id == payload.capability_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="This resource already has this capability.")

    obj = ResourceCapability(resource_id=resource_id, **payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate resource capability.") from exc
    db.refresh(obj)
    return obj


def get_resource_capabilities(db: Session, resource_id: UUID) -> list[ResourceCapability]:
    _get_or_404(db, InstitutionalResource, resource_id, "Resource")
    return list(db.scalars(
        select(ResourceCapability).where(ResourceCapability.resource_id == resource_id)
    ).all())


def update_resource_capability(
    db: Session, resource_id: UUID, resource_capability_id: UUID,
    payload: ResourceCapabilityUpdate, current_user: User
) -> ResourceCapability:
    resource = _get_or_404(db, InstitutionalResource, resource_id, "Resource")
    hei = _get_or_404(db, HeiProfile, resource.hei_id, "HEI profile")
    _assert_hei_write(current_user, hei)
    obj = _get_or_404(db, ResourceCapability, resource_capability_id, "Resource capability")
    if obj.resource_id != resource_id:
        raise HTTPException(status_code=404, detail="Resource capability not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj
