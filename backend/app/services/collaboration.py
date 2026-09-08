"""Service layer for CollaborationRequest and ProjectPartner."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.collaboration import CollaborationRequest, ProjectPartner
from app.models.partner import PartnerProfile
from app.models.project import Project
from app.models.user import User
from app.schemas.collaboration import (
    CollabRequestCreate, CollabStatusUpdate,
    ProjectPartnerCreate, ProjectPartnerUpdate,
)

_WRITE = {"Government Officer", "HEI Administrator", "System Administrator",
          "Industry / MSME / Startup", "Research Institution", "CSR Organization"}
_RESPOND = {"Industry / MSME / Startup", "Research Institution", "CSR Organization",
            "System Administrator"}


def _get_or_404(db, model, pk, label):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


# ── Collaboration Requests ─────────────────────────────────────────────────────

def create_request(db: Session, project_id: UUID, payload: CollabRequestCreate,
                   current_user: User) -> CollaborationRequest:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    _get_or_404(db, PartnerProfile, payload.partner_id, "Partner")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    obj = CollaborationRequest(
        project_id=project_id,
        partner_id=payload.partner_id,
        contribution_type=payload.contribution_type,
        message=payload.message,
        status="Requested",
        requested_by=current_user.user_id,
        requested_at=now,
        created_at=datetime.now(timezone.utc),
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def list_requests(db: Session, project_id: UUID) -> list[CollaborationRequest]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(
        select(CollaborationRequest).where(CollaborationRequest.project_id == project_id)
        .order_by(CollaborationRequest.created_at.desc())
    ).all())


def get_request(db: Session, request_id: UUID) -> CollaborationRequest:
    return _get_or_404(db, CollaborationRequest, request_id, "Collaboration request")


def update_request_status(db: Session, request_id: UUID, payload: CollabStatusUpdate,
                           current_user: User) -> CollaborationRequest:
    obj = _get_or_404(db, CollaborationRequest, request_id, "Collaboration request")

    if current_user.role not in _RESPOND | {"Government Officer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    # Partner-role users may only respond to requests directed at their own organisation
    if current_user.role in _RESPOND and current_user.role != "System Administrator":
        partner = db.get(PartnerProfile, obj.partner_id)
        if partner is None or current_user.organization_id != partner.organization_id:
            raise HTTPException(
                status_code=403,
                detail="You can only respond to collaboration requests directed at your organisation.",
            )

    obj.status = payload.status
    obj.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.response_message:
        obj.response_message = payload.response_message
    db.commit(); db.refresh(obj)
    return obj


# ── Project Partners ───────────────────────────────────────────────────────────

def add_partner(db: Session, project_id: UUID, payload: ProjectPartnerCreate,
                current_user: User) -> ProjectPartner:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    _get_or_404(db, PartnerProfile, payload.partner_id, "Partner")

    existing = db.scalar(select(ProjectPartner).where(
        ProjectPartner.project_id == project_id,
        ProjectPartner.partner_id == payload.partner_id,
        ProjectPartner.status == "Active",
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Active partnership already exists.")

    obj = ProjectPartner(project_id=project_id, **payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate partnership.") from e
    db.refresh(obj)
    return obj


def list_partners(db: Session, project_id: UUID) -> list[ProjectPartner]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(
        select(ProjectPartner).where(ProjectPartner.project_id == project_id)
    ).all())


def update_partner(db: Session, project_id: UUID, partner_id: UUID,
                   payload: ProjectPartnerUpdate, current_user: User) -> ProjectPartner:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = db.scalar(select(ProjectPartner).where(
        ProjectPartner.project_id == project_id,
        ProjectPartner.partner_id == partner_id,
    ))
    if obj is None:
        raise HTTPException(status_code=404, detail="Project partner not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


def delete_partner(db: Session, project_id: UUID, partner_id: UUID,
                   current_user: User) -> dict:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = db.scalar(select(ProjectPartner).where(
        ProjectPartner.project_id == project_id,
        ProjectPartner.partner_id == partner_id,
    ))
    if obj is None:
        raise HTTPException(status_code=404, detail="Project partner not found")
    db.delete(obj); db.commit()
    return {"detail": "Partnership removed."}
