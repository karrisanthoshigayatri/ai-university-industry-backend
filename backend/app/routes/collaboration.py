"""Collaboration Request and Project Partner routes — Step 21."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.collaboration import (
    CollabRequestCreate, CollabRequestResponse, CollabStatusUpdate,
    ProjectPartnerCreate, ProjectPartnerResponse, ProjectPartnerUpdate,
)
from app.services.collaboration import (
    add_partner, create_request, delete_partner,
    get_request, list_partners, list_requests,
    update_partner, update_request_status,
)

router = APIRouter(tags=["collaboration"])
DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Collaboration Requests ─────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/collaboration-requests",
             response_model=CollabRequestResponse, status_code=201)
def create_collab_request(project_id: UUID, payload: CollabRequestCreate, db: DB, cu: CU):
    return create_request(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/collaboration-requests",
            response_model=list[CollabRequestResponse])
def list_collab_requests(project_id: UUID, db: DB, _: CU):
    return list_requests(db, project_id)


@router.get("/api/collaboration-requests/{request_id}",
            response_model=CollabRequestResponse)
def get_collab_request(request_id: UUID, db: DB, _: CU):
    return get_request(db, request_id)


@router.put("/api/collaboration-requests/{request_id}/status",
            response_model=CollabRequestResponse)
def update_collab_status(request_id: UUID, payload: CollabStatusUpdate, db: DB, cu: CU):
    return update_request_status(db, request_id, payload, cu)


# ── Project Partners ───────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/partners",
             response_model=ProjectPartnerResponse, status_code=201)
def add_project_partner(project_id: UUID, payload: ProjectPartnerCreate, db: DB, cu: CU):
    return add_partner(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/partners",
            response_model=list[ProjectPartnerResponse])
def list_project_partners(project_id: UUID, db: DB, _: CU):
    return list_partners(db, project_id)


@router.put("/api/projects/{project_id}/partners/{partner_id}",
            response_model=ProjectPartnerResponse)
def update_project_partner(project_id: UUID, partner_id: UUID,
                           payload: ProjectPartnerUpdate, db: DB, cu: CU):
    return update_partner(db, project_id, partner_id, payload, cu)


@router.delete("/api/projects/{project_id}/partners/{partner_id}")
def delete_project_partner(project_id: UUID, partner_id: UUID, db: DB, cu: CU):
    return delete_partner(db, project_id, partner_id, cu)
