"""CapabilityTaxonomy and Capability service operations."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.capability import Capability, CapabilityTaxonomy
from app.schemas.capability import (
    CapabilityCreate,
    CapabilityUpdate,
    TaxonomyCreate,
    TaxonomyUpdate,
)


# ── Taxonomy helpers ──────────────────────────────────────────────────────────

def _get_taxonomy_or_404(db: Session, taxonomy_id: UUID) -> CapabilityTaxonomy:
    t = db.get(CapabilityTaxonomy, taxonomy_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy not found")
    return t


# ── Taxonomy CRUD ─────────────────────────────────────────────────────────────

def create_taxonomy(db: Session, payload: TaxonomyCreate) -> CapabilityTaxonomy:
    # Validate parent exists if provided
    if payload.parent_id is not None:
        _get_taxonomy_or_404(db, payload.parent_id)

    # Prevent duplicate names
    existing = db.scalar(
        select(CapabilityTaxonomy).where(CapabilityTaxonomy.name == payload.name)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Taxonomy '{payload.name}' already exists.",
        )

    taxonomy = CapabilityTaxonomy(**payload.model_dump())
    db.add(taxonomy)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Taxonomy already exists.") from exc
    db.refresh(taxonomy)
    return taxonomy


def get_taxonomies(db: Session) -> list[CapabilityTaxonomy]:
    return list(db.scalars(select(CapabilityTaxonomy).order_by(CapabilityTaxonomy.name)).all())


def get_taxonomy(db: Session, taxonomy_id: UUID) -> CapabilityTaxonomy:
    return _get_taxonomy_or_404(db, taxonomy_id)


def update_taxonomy(db: Session, taxonomy_id: UUID, payload: TaxonomyUpdate) -> CapabilityTaxonomy:
    taxonomy = _get_taxonomy_or_404(db, taxonomy_id)
    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates and updates["parent_id"] is not None:
        _get_taxonomy_or_404(db, updates["parent_id"])
    for field, value in updates.items():
        setattr(taxonomy, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Taxonomy name already exists.") from exc
    db.refresh(taxonomy)
    return taxonomy


# ── Capability helpers ────────────────────────────────────────────────────────

def _get_capability_or_404(db: Session, capability_id: UUID) -> Capability:
    c = db.get(Capability, capability_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
    return c


# ── Capability CRUD ───────────────────────────────────────────────────────────

def create_capability(db: Session, payload: CapabilityCreate) -> Capability:
    # Validate taxonomy exists if provided
    if payload.taxonomy_id is not None:
        _get_taxonomy_or_404(db, payload.taxonomy_id)

    # Validate parent capability exists if provided
    if payload.parent_capability_id is not None:
        _get_capability_or_404(db, payload.parent_capability_id)

    # Prevent duplicate name+type combos
    existing = db.scalar(
        select(Capability).where(
            Capability.name == payload.name,
            Capability.capability_type == payload.capability_type,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Capability '{payload.name}' with type '{payload.capability_type}' already exists.",
        )

    capability = Capability(**payload.model_dump())
    db.add(capability)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Capability already exists.") from exc
    db.refresh(capability)
    return capability


def get_capabilities(
    db: Session,
    capability_type: str | None = None,
    taxonomy_id: UUID | None = None,
    status: str | None = None,
) -> list[Capability]:
    stmt = select(Capability)
    if capability_type:
        stmt = stmt.where(Capability.capability_type == capability_type)
    if taxonomy_id:
        stmt = stmt.where(Capability.taxonomy_id == taxonomy_id)
    if status:
        stmt = stmt.where(Capability.status == status)
    stmt = stmt.order_by(Capability.capability_type, Capability.name)
    return list(db.scalars(stmt).all())


def get_capability(db: Session, capability_id: UUID) -> Capability:
    return _get_capability_or_404(db, capability_id)


def update_capability(
    db: Session, capability_id: UUID, payload: CapabilityUpdate
) -> Capability:
    capability = _get_capability_or_404(db, capability_id)
    updates = payload.model_dump(exclude_unset=True)

    if "taxonomy_id" in updates and updates["taxonomy_id"] is not None:
        _get_taxonomy_or_404(db, updates["taxonomy_id"])
    if "parent_capability_id" in updates and updates["parent_capability_id"] is not None:
        parent = _get_capability_or_404(db, updates["parent_capability_id"])
        if parent.capability_id == capability_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A capability cannot be its own parent.",
            )

    # Check duplicate if name or type changes
    new_name = updates.get("name", capability.name)
    new_type = updates.get("capability_type", capability.capability_type)
    if new_name != capability.name or new_type != capability.capability_type:
        existing = db.scalar(
            select(Capability).where(
                Capability.name == new_name,
                Capability.capability_type == new_type,
                Capability.capability_id != capability_id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Capability '{new_name}' with type '{new_type}' already exists.",
            )

    for field, value in updates.items():
        setattr(capability, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Capability update conflict.") from exc
    db.refresh(capability)
    return capability
