"""Service layer for External Partner Registry."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
from app.models.user import User
from app.schemas.partner import (
    PartnerCapabilityCreate,
    PartnerCapabilityUpdate,
    PartnerProfileCreate,
    PartnerProfileUpdate,
    PartnerSupportOfferingCreate,
    PartnerSupportOfferingUpdate,
    PartnerVerifyRequest,
)

# ── Role constants ─────────────────────────────────────────────────────────────
_SYS_ADMIN = {"System Administrator"}
_VERIFY_ROLES = {"Government Officer", "System Administrator"}
_PARTNER_WRITE_ROLES = {
    "Industry / MSME / Startup",
    "Research Institution",
    "CSR Organization",
    "System Administrator",
}

# partner_type → organization_type mapping
_PARTNER_ORG_TYPES = {
    "Industry",
    "MSME",
    "Startup",
    "Research Institution",
    "CSR Organization",
}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _get_or_404(db: Session, model, pk, label: str):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _assert_partner_write(current_user: User, partner: PartnerProfile) -> None:
    """System Admin unrestricted; others only for their own org's partner."""
    if current_user.role in _SYS_ADMIN:
        return
    if current_user.organization_id != partner.organization_id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own organisation's partner profile.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# Partner Profile
# ══════════════════════════════════════════════════════════════════════════════

def create_partner(
    db: Session, payload: PartnerProfileCreate, current_user: User
) -> PartnerProfile:
    # Any authenticated user whose org is a partner-type may create
    # System Admins may create on behalf of any org
    if current_user.role not in _SYS_ADMIN:
        if current_user.organization_id != payload.organization_id:
            raise HTTPException(
                status_code=403,
                detail="You can only create a partner profile for your own organisation.",
            )

    org = db.get(Organization, payload.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.organization_type not in _PARTNER_ORG_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Organization type '{org.organization_type}' is not eligible for a partner profile. "
                   f"Allowed: {sorted(_PARTNER_ORG_TYPES)}",
        )

    existing = db.scalar(
        select(PartnerProfile).where(
            PartnerProfile.organization_id == payload.organization_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This organisation already has a partner profile."
        )

    partner = PartnerProfile(**payload.model_dump())
    db.add(partner)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Partner profile already exists.") from exc
    db.refresh(partner)
    return partner


def list_partners(
    db: Session,
    current_user: User,
    partner_type: str | None = None,
    verification_status: str | None = None,
) -> list[PartnerProfile]:
    stmt = select(PartnerProfile)
    # Normal users only see Verified partners; admins/gov see all
    if current_user.role not in {"System Administrator", "Government Officer"}:
        stmt = stmt.where(PartnerProfile.verification_status == "Verified")
    if partner_type:
        stmt = stmt.where(PartnerProfile.partner_type == partner_type)
    if verification_status:
        stmt = stmt.where(PartnerProfile.verification_status == verification_status)
    return list(db.scalars(stmt.order_by(PartnerProfile.created_at.desc())).all())


def get_partner(db: Session, partner_id: UUID) -> PartnerProfile:
    return _get_or_404(db, PartnerProfile, partner_id, "Partner profile")


def update_partner(
    db: Session, partner_id: UUID, payload: PartnerProfileUpdate, current_user: User
) -> PartnerProfile:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner


def delete_partner(
    db: Session, partner_id: UUID, current_user: User
) -> dict[str, str]:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    try:
        db.delete(partner)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete partner: related records exist.",
        ) from exc
    return {"detail": "Partner profile deleted."}


def verify_partner(
    db: Session, partner_id: UUID, payload: PartnerVerifyRequest, current_user: User
) -> PartnerProfile:
    if current_user.role not in _VERIFY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only Government Officers or System Administrators can verify partners.",
        )
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    partner.verification_status = payload.verification_status
    db.commit()
    db.refresh(partner)
    return partner


# ══════════════════════════════════════════════════════════════════════════════
# Partner Capability
# ══════════════════════════════════════════════════════════════════════════════

def add_capability(
    db: Session, partner_id: UUID, payload: PartnerCapabilityCreate, current_user: User
) -> PartnerCapability:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)

    if db.get(Capability, payload.capability_id) is None:
        raise HTTPException(status_code=404, detail="Capability not found")

    existing = db.scalar(
        select(PartnerCapability).where(
            PartnerCapability.partner_id == partner_id,
            PartnerCapability.capability_id == payload.capability_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This partner already has this capability."
        )

    obj = PartnerCapability(partner_id=partner_id, **payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate partner capability.") from exc
    db.refresh(obj)
    return obj


def list_capabilities(db: Session, partner_id: UUID) -> list[PartnerCapability]:
    _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    return list(
        db.scalars(
            select(PartnerCapability).where(PartnerCapability.partner_id == partner_id)
        ).all()
    )


def update_capability(
    db: Session,
    partner_id: UUID,
    partner_capability_id: UUID,
    payload: PartnerCapabilityUpdate,
    current_user: User,
) -> PartnerCapability:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    obj = _get_or_404(db, PartnerCapability, partner_capability_id, "Partner capability")
    if obj.partner_id != partner_id:
        raise HTTPException(status_code=404, detail="Partner capability not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_capability(
    db: Session,
    partner_id: UUID,
    partner_capability_id: UUID,
    current_user: User,
) -> dict[str, str]:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    obj = _get_or_404(db, PartnerCapability, partner_capability_id, "Partner capability")
    if obj.partner_id != partner_id:
        raise HTTPException(status_code=404, detail="Partner capability not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Partner capability removed."}


# ══════════════════════════════════════════════════════════════════════════════
# Partner Support Offering
# ══════════════════════════════════════════════════════════════════════════════

def add_offering(
    db: Session,
    partner_id: UUID,
    payload: PartnerSupportOfferingCreate,
    current_user: User,
) -> PartnerSupportOffering:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    obj = PartnerSupportOffering(partner_id=partner_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_offerings(
    db: Session, partner_id: UUID, current_user: User
) -> list[PartnerSupportOffering]:
    _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    stmt = select(PartnerSupportOffering).where(
        PartnerSupportOffering.partner_id == partner_id
    )
    # Normal users see only Active offerings; admins/owners see all
    is_admin = current_user.role in _SYS_ADMIN
    partner = db.get(PartnerProfile, partner_id)
    is_owner = partner and current_user.organization_id == partner.organization_id
    if not (is_admin or is_owner):
        stmt = stmt.where(PartnerSupportOffering.status == "Active")
    return list(db.scalars(stmt.order_by(PartnerSupportOffering.created_at.desc())).all())


def get_offering(
    db: Session, partner_id: UUID, offering_id: UUID
) -> PartnerSupportOffering:
    obj = _get_or_404(db, PartnerSupportOffering, offering_id, "Offering")
    if obj.partner_id != partner_id:
        raise HTTPException(status_code=404, detail="Offering not found")
    return obj


def update_offering(
    db: Session,
    partner_id: UUID,
    offering_id: UUID,
    payload: PartnerSupportOfferingUpdate,
    current_user: User,
) -> PartnerSupportOffering:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    obj = _get_or_404(db, PartnerSupportOffering, offering_id, "Offering")
    if obj.partner_id != partner_id:
        raise HTTPException(status_code=404, detail="Offering not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_offering(
    db: Session, partner_id: UUID, offering_id: UUID, current_user: User
) -> dict[str, str]:
    partner = _get_or_404(db, PartnerProfile, partner_id, "Partner profile")
    _assert_partner_write(current_user, partner)
    obj = _get_or_404(db, PartnerSupportOffering, offering_id, "Offering")
    if obj.partner_id != partner_id:
        raise HTTPException(status_code=404, detail="Offering not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Offering removed."}
