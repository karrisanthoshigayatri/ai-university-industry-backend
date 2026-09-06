"""Capability and CapabilityTaxonomy API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.capability import (
    CapabilityCreate,
    CapabilityResponse,
    CapabilityUpdate,
    TaxonomyCreate,
    TaxonomyResponse,
    TaxonomyUpdate,
)
from app.services.capability import (
    create_capability,
    create_taxonomy,
    get_capabilities,
    get_capability,
    get_taxonomies,
    get_taxonomy,
    update_capability,
    update_taxonomy,
)


# ── Taxonomy router ────────────────────────────────────────────────────────────
taxonomy_router = APIRouter(prefix="/api/capability-taxonomy", tags=["capability-taxonomy"])

_WRITE_ROLES = ("Government Officer", "HEI Administrator", "System Administrator")


@taxonomy_router.get("", response_model=list[TaxonomyResponse], summary="List all taxonomies")
def list_taxonomies(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[TaxonomyResponse]:
    """Return all capability taxonomies. Requires authentication."""
    return get_taxonomies(db)


@taxonomy_router.get("/{taxonomy_id}", response_model=TaxonomyResponse, summary="Get a taxonomy by ID")
def get_one_taxonomy(
    taxonomy_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> TaxonomyResponse:
    return get_taxonomy(db, taxonomy_id)


@taxonomy_router.post("", response_model=TaxonomyResponse, status_code=201, summary="Create a taxonomy")
def create_one_taxonomy(
    payload: TaxonomyCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role(*_WRITE_ROLES))],
) -> TaxonomyResponse:
    """Create a new taxonomy. Requires Government Officer, HEI Administrator, or System Administrator."""
    return create_taxonomy(db, payload)


@taxonomy_router.put("/{taxonomy_id}", response_model=TaxonomyResponse, summary="Update a taxonomy")
def update_one_taxonomy(
    taxonomy_id: UUID,
    payload: TaxonomyUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role(*_WRITE_ROLES))],
) -> TaxonomyResponse:
    return update_taxonomy(db, taxonomy_id, payload)


# ── Capability router ──────────────────────────────────────────────────────────
capability_router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


@capability_router.get("", response_model=list[CapabilityResponse], summary="List capabilities")
def list_capabilities(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    capability_type: str | None = Query(default=None, description="Filter by type"),
    taxonomy_id: UUID | None = Query(default=None, description="Filter by taxonomy"),
    status: str | None = Query(default=None, description="Filter by status"),
) -> list[CapabilityResponse]:
    """Return capabilities. Supports optional filters. Requires authentication."""
    return get_capabilities(db, capability_type, taxonomy_id, status)


@capability_router.get("/{capability_id}", response_model=CapabilityResponse, summary="Get a capability by ID")
def get_one_capability(
    capability_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CapabilityResponse:
    return get_capability(db, capability_id)


@capability_router.post("", response_model=CapabilityResponse, status_code=201, summary="Create a capability")
def create_one_capability(
    payload: CapabilityCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role(*_WRITE_ROLES))],
) -> CapabilityResponse:
    """Create a canonical capability. Requires Government Officer, HEI Administrator, or System Administrator."""
    return create_capability(db, payload)


@capability_router.put("/{capability_id}", response_model=CapabilityResponse, summary="Update a capability")
def update_one_capability(
    capability_id: UUID,
    payload: CapabilityUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role(*_WRITE_ROLES))],
) -> CapabilityResponse:
    return update_capability(db, capability_id, payload)
