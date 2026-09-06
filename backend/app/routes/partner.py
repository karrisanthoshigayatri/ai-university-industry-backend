"""Routes for the External Partner Registry."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.partner import (
    PartnerCapabilityCreate,
    PartnerCapabilityResponse,
    PartnerCapabilityUpdate,
    PartnerProfileCreate,
    PartnerProfileResponse,
    PartnerProfileUpdate,
    PartnerSupportOfferingCreate,
    PartnerSupportOfferingResponse,
    PartnerSupportOfferingUpdate,
    PartnerVerifyRequest,
)
from app.services.partner import (
    add_capability,
    add_offering,
    create_partner,
    delete_capability,
    delete_offering,
    delete_partner,
    get_offering,
    get_partner,
    list_capabilities,
    list_offerings,
    list_partners,
    update_capability,
    update_offering,
    update_partner,
    verify_partner,
)

router = APIRouter(tags=["partners"])

DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Partner Profile ────────────────────────────────────────────────────────────

@router.post(
    "/api/partners",
    response_model=PartnerProfileResponse,
    status_code=201,
    summary="Create partner profile",
)
def create_partner_route(
    payload: PartnerProfileCreate, db: DB, current_user: CU
) -> PartnerProfileResponse:
    """Create a partner profile. The organisation must exist and be a partner type."""
    return create_partner(db, payload, current_user)


@router.get(
    "/api/partners",
    response_model=list[PartnerProfileResponse],
    summary="List partner profiles",
)
def list_partners_route(
    db: DB,
    current_user: CU,
    partner_type: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
) -> list[PartnerProfileResponse]:
    """List partners. Normal users only see Verified partners."""
    return list_partners(db, current_user, partner_type, verification_status)


@router.get(
    "/api/partners/{partner_id}",
    response_model=PartnerProfileResponse,
    summary="Get partner profile",
)
def get_partner_route(partner_id: UUID, db: DB, _: CU) -> PartnerProfileResponse:
    return get_partner(db, partner_id)


@router.put(
    "/api/partners/{partner_id}",
    response_model=PartnerProfileResponse,
    summary="Update partner profile",
)
def update_partner_route(
    partner_id: UUID, payload: PartnerProfileUpdate, db: DB, current_user: CU
) -> PartnerProfileResponse:
    return update_partner(db, partner_id, payload, current_user)


@router.delete(
    "/api/partners/{partner_id}",
    summary="Delete partner profile",
)
def delete_partner_route(
    partner_id: UUID, db: DB, current_user: CU
) -> dict[str, str]:
    return delete_partner(db, partner_id, current_user)


@router.put(
    "/api/partners/{partner_id}/verification",
    response_model=PartnerProfileResponse,
    summary="Verify / reject partner (Government Officer / System Admin only)",
)
def verify_partner_route(
    partner_id: UUID, payload: PartnerVerifyRequest, db: DB, current_user: CU
) -> PartnerProfileResponse:
    """Set verification_status. Only Government Officers and System Admins may call this."""
    return verify_partner(db, partner_id, payload, current_user)


# ── Partner Capabilities ───────────────────────────────────────────────────────

@router.post(
    "/api/partners/{partner_id}/capabilities",
    response_model=PartnerCapabilityResponse,
    status_code=201,
    summary="Add capability to partner",
)
def add_capability_route(
    partner_id: UUID,
    payload: PartnerCapabilityCreate,
    db: DB,
    current_user: CU,
) -> PartnerCapabilityResponse:
    return add_capability(db, partner_id, payload, current_user)


@router.get(
    "/api/partners/{partner_id}/capabilities",
    response_model=list[PartnerCapabilityResponse],
    summary="List partner capabilities",
)
def list_capabilities_route(
    partner_id: UUID, db: DB, _: CU
) -> list[PartnerCapabilityResponse]:
    return list_capabilities(db, partner_id)


@router.put(
    "/api/partners/{partner_id}/capabilities/{partner_capability_id}",
    response_model=PartnerCapabilityResponse,
    summary="Update partner capability",
)
def update_capability_route(
    partner_id: UUID,
    partner_capability_id: UUID,
    payload: PartnerCapabilityUpdate,
    db: DB,
    current_user: CU,
) -> PartnerCapabilityResponse:
    return update_capability(db, partner_id, partner_capability_id, payload, current_user)


@router.delete(
    "/api/partners/{partner_id}/capabilities/{partner_capability_id}",
    summary="Remove partner capability",
)
def delete_capability_route(
    partner_id: UUID,
    partner_capability_id: UUID,
    db: DB,
    current_user: CU,
) -> dict[str, str]:
    return delete_capability(db, partner_id, partner_capability_id, current_user)


# ── Support Offerings ──────────────────────────────────────────────────────────

@router.post(
    "/api/partners/{partner_id}/offerings",
    response_model=PartnerSupportOfferingResponse,
    status_code=201,
    summary="Create support offering",
)
def add_offering_route(
    partner_id: UUID,
    payload: PartnerSupportOfferingCreate,
    db: DB,
    current_user: CU,
) -> PartnerSupportOfferingResponse:
    return add_offering(db, partner_id, payload, current_user)


@router.get(
    "/api/partners/{partner_id}/offerings",
    response_model=list[PartnerSupportOfferingResponse],
    summary="List support offerings",
)
def list_offerings_route(
    partner_id: UUID, db: DB, current_user: CU
) -> list[PartnerSupportOfferingResponse]:
    return list_offerings(db, partner_id, current_user)


@router.get(
    "/api/partners/{partner_id}/offerings/{offering_id}",
    response_model=PartnerSupportOfferingResponse,
    summary="Get support offering",
)
def get_offering_route(
    partner_id: UUID, offering_id: UUID, db: DB, _: CU
) -> PartnerSupportOfferingResponse:
    return get_offering(db, partner_id, offering_id)


@router.put(
    "/api/partners/{partner_id}/offerings/{offering_id}",
    response_model=PartnerSupportOfferingResponse,
    summary="Update support offering",
)
def update_offering_route(
    partner_id: UUID,
    offering_id: UUID,
    payload: PartnerSupportOfferingUpdate,
    db: DB,
    current_user: CU,
) -> PartnerSupportOfferingResponse:
    return update_offering(db, partner_id, offering_id, payload, current_user)


@router.delete(
    "/api/partners/{partner_id}/offerings/{offering_id}",
    summary="Remove support offering",
)
def delete_offering_route(
    partner_id: UUID,
    offering_id: UUID,
    db: DB,
    current_user: CU,
) -> dict[str, str]:
    return delete_offering(db, partner_id, offering_id, current_user)
