"""Project, Team, Member, Resource, Capability routes — Steps 16–18."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import (
    MemberCreate, MemberResponse, MemberUpdate,
    ProjectCapabilityCreate, ProjectCapabilityResponse, ProjectCapabilityUpdate,
    ProjectCreate, ProjectResourceCreate, ProjectResourceResponse,
    ProjectResourceUpdate, ProjectResponse, ProjectStatusUpdate, ProjectStageUpdate,
    ProjectUpdate, TeamCreate, TeamResponse, TeamUpdate,
)
from app.services.project import (
    add_capability, add_member, add_resource,
    create_project, create_team,
    delete_capability, delete_member, delete_project, delete_resource,
    get_project, get_team, list_capabilities, list_members,
    list_projects, list_resources,
    update_capability, update_member, update_project,
    update_project_stage, update_project_status,
    update_resource, update_team,
)

router = APIRouter(tags=["projects"])
DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Projects ───────────────────────────────────────────────────────────────────

@router.post("/api/projects", response_model=ProjectResponse, status_code=201,
             summary="Create a project")
def create_project_route(payload: ProjectCreate, db: DB, cu: CU) -> ProjectResponse:
    return create_project(db, payload, cu)


@router.get("/api/projects", response_model=list[ProjectResponse],
            summary="List all projects")
def list_projects_route(db: DB, cu: CU) -> list[ProjectResponse]:
    return list_projects(db, cu)


@router.get("/api/projects/{project_id}", response_model=ProjectResponse,
            summary="Get project by ID")
def get_project_route(project_id: UUID, db: DB, _: CU) -> ProjectResponse:
    return get_project(db, project_id)


@router.put("/api/projects/{project_id}", response_model=ProjectResponse,
            summary="Update project")
def update_project_route(project_id: UUID, payload: ProjectUpdate, db: DB, cu: CU) -> ProjectResponse:
    return update_project(db, project_id, payload, cu)


@router.delete("/api/projects/{project_id}", summary="Delete project")
def delete_project_route(project_id: UUID, db: DB, cu: CU) -> dict:
    return delete_project(db, project_id, cu)


@router.put("/api/projects/{project_id}/status", response_model=ProjectResponse,
            summary="Update project status")
def update_status_route(project_id: UUID, payload: ProjectStatusUpdate, db: DB, cu: CU) -> ProjectResponse:
    return update_project_status(db, project_id, payload, cu)


@router.put("/api/projects/{project_id}/stage", response_model=ProjectResponse,
            summary="Update project stage")
def update_stage_route(project_id: UUID, payload: ProjectStageUpdate, db: DB, cu: CU) -> ProjectResponse:
    return update_project_stage(db, project_id, payload, cu)


# ── Team ───────────────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/team", response_model=TeamResponse,
             status_code=201, summary="Create project team")
def create_team_route(project_id: UUID, payload: TeamCreate, db: DB, cu: CU) -> TeamResponse:
    return create_team(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/team", response_model=TeamResponse,
            summary="Get project team")
def get_team_route(project_id: UUID, db: DB, _: CU) -> TeamResponse:
    return get_team(db, project_id)


@router.put("/api/projects/{project_id}/team", response_model=TeamResponse,
            summary="Update project team")
def update_team_route(project_id: UUID, payload: TeamUpdate, db: DB, cu: CU) -> TeamResponse:
    return update_team(db, project_id, payload, cu)


# ── Team Members ───────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/team/members", response_model=MemberResponse,
             status_code=201, summary="Add team member")
def add_member_route(project_id: UUID, payload: MemberCreate, db: DB, cu: CU) -> MemberResponse:
    return add_member(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/team/members", response_model=list[MemberResponse],
            summary="List team members")
def list_members_route(project_id: UUID, db: DB, _: CU) -> list[MemberResponse]:
    return list_members(db, project_id)


@router.put("/api/projects/{project_id}/team/members/{member_id}",
            response_model=MemberResponse, summary="Update team member")
def update_member_route(project_id: UUID, member_id: UUID, payload: MemberUpdate,
                        db: DB, cu: CU) -> MemberResponse:
    return update_member(db, project_id, member_id, payload, cu)


@router.delete("/api/projects/{project_id}/team/members/{member_id}",
               summary="Remove team member")
def delete_member_route(project_id: UUID, member_id: UUID, db: DB, cu: CU) -> dict:
    return delete_member(db, project_id, member_id, cu)


# ── Resources ──────────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/resources",
             response_model=ProjectResourceResponse, status_code=201,
             summary="Assign resource to project")
def add_resource_route(project_id: UUID, payload: ProjectResourceCreate,
                       db: DB, cu: CU) -> ProjectResourceResponse:
    return add_resource(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/resources",
            response_model=list[ProjectResourceResponse],
            summary="List project resources")
def list_resources_route(project_id: UUID, db: DB, _: CU) -> list[ProjectResourceResponse]:
    return list_resources(db, project_id)


@router.put("/api/projects/{project_id}/resources/{pr_id}",
            response_model=ProjectResourceResponse, summary="Update project resource")
def update_resource_route(project_id: UUID, pr_id: UUID, payload: ProjectResourceUpdate,
                          db: DB, cu: CU) -> ProjectResourceResponse:
    return update_resource(db, project_id, pr_id, payload, cu)


@router.delete("/api/projects/{project_id}/resources/{pr_id}",
               summary="Remove resource from project")
def delete_resource_route(project_id: UUID, pr_id: UUID, db: DB, cu: CU) -> dict:
    return delete_resource(db, project_id, pr_id, cu)


# ── Capabilities ───────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/capabilities",
             response_model=ProjectCapabilityResponse, status_code=201,
             summary="Add capability to project")
def add_capability_route(project_id: UUID, payload: ProjectCapabilityCreate,
                         db: DB, cu: CU) -> ProjectCapabilityResponse:
    return add_capability(db, project_id, payload, cu)


@router.get("/api/projects/{project_id}/capabilities",
            response_model=list[ProjectCapabilityResponse],
            summary="List project capabilities")
def list_capabilities_route(project_id: UUID, db: DB, _: CU) -> list[ProjectCapabilityResponse]:
    return list_capabilities(db, project_id)


@router.put("/api/projects/{project_id}/capabilities/{pc_id}",
            response_model=ProjectCapabilityResponse, summary="Update project capability")
def update_capability_route(project_id: UUID, pc_id: UUID, payload: ProjectCapabilityUpdate,
                            db: DB, cu: CU) -> ProjectCapabilityResponse:
    return update_capability(db, project_id, pc_id, payload, cu)


@router.delete("/api/projects/{project_id}/capabilities/{pc_id}",
               summary="Remove capability from project")
def delete_capability_route(project_id: UUID, pc_id: UUID, db: DB, cu: CU) -> dict:
    return delete_capability(db, project_id, pc_id, cu)
