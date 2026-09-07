"""ProjectMilestone and ProjectOutput routes — Step 22."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.milestone import (
    MilestoneCreate, MilestoneResponse, MilestoneStatusUpdate, MilestoneUpdate,
    OutputCreate, OutputResponse, OutputUpdate,
)
from app.services.milestone import (
    create_milestone, create_output,
    delete_milestone, delete_output,
    get_milestone, get_output,
    list_milestones, list_outputs,
    update_milestone, update_milestone_status, update_output,
)

router = APIRouter(tags=["milestones-outputs"])
DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Milestones ─────────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/milestones",
             response_model=MilestoneResponse, status_code=201)
def create_m(project_id: UUID, p: MilestoneCreate, db: DB, cu: CU):
    return create_milestone(db, project_id, p, cu)


@router.get("/api/projects/{project_id}/milestones",
            response_model=list[MilestoneResponse])
def list_m(project_id: UUID, db: DB, _: CU):
    return list_milestones(db, project_id)


@router.get("/api/projects/{project_id}/milestones/{milestone_id}",
            response_model=MilestoneResponse)
def get_m(project_id: UUID, milestone_id: UUID, db: DB, _: CU):
    return get_milestone(db, project_id, milestone_id)


@router.put("/api/projects/{project_id}/milestones/{milestone_id}",
            response_model=MilestoneResponse)
def update_m(project_id: UUID, milestone_id: UUID, p: MilestoneUpdate, db: DB, cu: CU):
    return update_milestone(db, project_id, milestone_id, p, cu)


@router.delete("/api/projects/{project_id}/milestones/{milestone_id}")
def delete_m(project_id: UUID, milestone_id: UUID, db: DB, cu: CU):
    return delete_milestone(db, project_id, milestone_id, cu)


@router.put("/api/projects/{project_id}/milestones/{milestone_id}/status",
            response_model=MilestoneResponse)
def update_m_status(project_id: UUID, milestone_id: UUID, p: MilestoneStatusUpdate,
                    db: DB, cu: CU):
    return update_milestone_status(db, project_id, milestone_id, p, cu)


# ── Outputs ────────────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/outputs",
             response_model=OutputResponse, status_code=201)
def create_o(project_id: UUID, p: OutputCreate, db: DB, cu: CU):
    return create_output(db, project_id, p, cu)


@router.get("/api/projects/{project_id}/outputs",
            response_model=list[OutputResponse])
def list_o(project_id: UUID, db: DB, _: CU):
    return list_outputs(db, project_id)


@router.get("/api/projects/{project_id}/outputs/{output_id}",
            response_model=OutputResponse)
def get_o(project_id: UUID, output_id: UUID, db: DB, _: CU):
    return get_output(db, project_id, output_id)


@router.put("/api/projects/{project_id}/outputs/{output_id}",
            response_model=OutputResponse)
def update_o(project_id: UUID, output_id: UUID, p: OutputUpdate, db: DB, cu: CU):
    return update_output(db, project_id, output_id, p, cu)


@router.delete("/api/projects/{project_id}/outputs/{output_id}")
def delete_o(project_id: UUID, output_id: UUID, db: DB, cu: CU):
    return delete_output(db, project_id, output_id, cu)
