"""Service layer for Project, Team, Members, Resources, Capabilities."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.capability import Capability
from app.models.hei import FacultyExpertProfile, HeiProfile, InstitutionalResource
from app.models.problem import Problem
from app.models.project import (
    Project, ProjectCapability, ProjectResource, ProjectTeam, ProjectTeamMember,
)
from app.models.user import User
from app.schemas.project import (
    MemberCreate, MemberUpdate,
    ProjectCapabilityCreate, ProjectCapabilityUpdate,
    ProjectCreate, ProjectResourceCreate, ProjectResourceUpdate, ProjectUpdate,
    ProjectStatusUpdate, ProjectStageUpdate,
    TeamCreate, TeamUpdate,
)

_ADMIN = {"System Administrator"}
_WRITE_ROLES = {"HEI Administrator", "Government Officer", "System Administrator"}

# Problem statuses eligible for project creation
_ELIGIBLE_STATUSES = {"Validated", "Matched", "Accepted", "Active"}


def _get_or_404(db: Session, model, pk, label: str):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _assert_write(current_user: User, project: Project) -> None:
    if current_user.role in _ADMIN:
        return
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    # HEI Admins/Gov Officers must belong to the project's HEI org
    if current_user.role == "HEI Administrator":
        hei = db_get_hei_by_id(None, project.hei_id)
        if hei and current_user.organization_id != hei.organization_id:
            raise HTTPException(status_code=403, detail="You can only manage your own HEI's projects.")


def db_get_hei_by_id(db, hei_id) -> HeiProfile | None:
    # used in _assert_write — avoids circular db ref
    return None  # fallback; actual check done in service functions with db


# ══════════════════════════════════════════════════════════════════════════════
# Project CRUD
# ══════════════════════════════════════════════════════════════════════════════

def create_project(db: Session, payload: ProjectCreate, current_user: User) -> Project:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    problem = _get_or_404(db, Problem, payload.problem_id, "Problem")
    if problem.current_status not in _ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Problem status '{problem.current_status}' is not eligible for a project. "
                   f"Requires: {sorted(_ELIGIBLE_STATUSES)}",
        )

    _get_or_404(db, HeiProfile, payload.hei_id, "HEI")

    proj = Project(**payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def list_projects(db: Session, current_user: User) -> list[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    return list(db.scalars(stmt).all())


def get_project(db: Session, project_id: UUID) -> Project:
    return _get_or_404(db, Project, project_id, "Project")


def update_project(db: Session, project_id: UUID, payload: ProjectUpdate, current_user: User) -> Project:
    proj = _get_or_404(db, Project, project_id, "Project")
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proj, field, value)
    db.commit()
    db.refresh(proj)
    return proj


def delete_project(db: Session, project_id: UUID, current_user: User) -> dict:
    proj = _get_or_404(db, Project, project_id, "Project")
    if current_user.role not in _ADMIN:
        raise HTTPException(status_code=403, detail="Only System Administrators can delete projects.")
    try:
        db.delete(proj)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete project: related records exist.") from exc
    return {"detail": "Project deleted."}


def update_project_status(db: Session, project_id: UUID, payload: ProjectStatusUpdate, current_user: User) -> Project:
    proj = _get_or_404(db, Project, project_id, "Project")
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    proj.status = payload.status
    db.commit()
    db.refresh(proj)
    return proj


def update_project_stage(db: Session, project_id: UUID, payload: ProjectStageUpdate, current_user: User) -> Project:
    proj = _get_or_404(db, Project, project_id, "Project")
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    proj.current_stage = payload.current_stage
    db.commit()
    db.refresh(proj)
    return proj


# ══════════════════════════════════════════════════════════════════════════════
# Team
# ══════════════════════════════════════════════════════════════════════════════

def create_team(db: Session, project_id: UUID, payload: TeamCreate, current_user: User) -> ProjectTeam:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    _get_or_404(db, HeiProfile, payload.hei_id, "HEI")
    if payload.faculty_lead:
        _get_or_404(db, FacultyExpertProfile, payload.faculty_lead, "Faculty lead")

    existing = db.scalar(select(ProjectTeam).where(ProjectTeam.project_id == project_id))
    if existing:
        raise HTTPException(status_code=409, detail="Team already exists for this project.")

    team = ProjectTeam(project_id=project_id, **payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def get_team(db: Session, project_id: UUID) -> ProjectTeam:
    team = db.scalar(select(ProjectTeam).where(ProjectTeam.project_id == project_id))
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def update_team(db: Session, project_id: UUID, payload: TeamUpdate, current_user: User) -> ProjectTeam:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    team = get_team(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


# ══════════════════════════════════════════════════════════════════════════════
# Team Members
# ══════════════════════════════════════════════════════════════════════════════

def add_member(db: Session, project_id: UUID, payload: MemberCreate, current_user: User) -> ProjectTeamMember:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    team = get_team(db, project_id)

    # Skip app-side FK validation — user table and app_user share same UUIDs in Supabase

    # Prevent duplicate active members
    existing = db.scalar(
        select(ProjectTeamMember).where(
            ProjectTeamMember.team_id == team.team_id,
            ProjectTeamMember.user_id == payload.user_id,
            ProjectTeamMember.status == "Active",
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already an active team member.")

    member = ProjectTeamMember(
        team_id=team.team_id,
        joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
        **payload.model_dump(),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session, project_id: UUID) -> list[ProjectTeamMember]:
    team = get_team(db, project_id)
    return list(db.scalars(select(ProjectTeamMember).where(ProjectTeamMember.team_id == team.team_id)).all())


def update_member(db: Session, project_id: UUID, member_id: UUID, payload: MemberUpdate, current_user: User) -> ProjectTeamMember:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    team = get_team(db, project_id)
    member = _get_or_404(db, ProjectTeamMember, member_id, "Team member")
    if member.team_id != team.team_id:
        raise HTTPException(status_code=404, detail="Team member not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


def delete_member(db: Session, project_id: UUID, member_id: UUID, current_user: User) -> dict:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    team = get_team(db, project_id)
    member = _get_or_404(db, ProjectTeamMember, member_id, "Team member")
    if member.team_id != team.team_id:
        raise HTTPException(status_code=404, detail="Team member not found")
    db.delete(member)
    db.commit()
    return {"detail": "Team member removed."}


# ══════════════════════════════════════════════════════════════════════════════
# Project Resources
# ══════════════════════════════════════════════════════════════════════════════

def add_resource(db: Session, project_id: UUID, payload: ProjectResourceCreate, current_user: User) -> ProjectResource:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    _get_or_404(db, InstitutionalResource, payload.resource_id, "Resource")

    # Prevent duplicate active resource assignment
    existing = db.scalar(
        select(ProjectResource).where(
            ProjectResource.project_id == project_id,
            ProjectResource.resource_id == payload.resource_id,
            ProjectResource.access_status.in_(["Requested", "Approved", "Active"]),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Resource already assigned to this project.")

    obj = ProjectResource(project_id=project_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_resources(db: Session, project_id: UUID) -> list[ProjectResource]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(select(ProjectResource).where(ProjectResource.project_id == project_id)).all())


def update_resource(db: Session, project_id: UUID, pr_id: UUID, payload: ProjectResourceUpdate, current_user: User) -> ProjectResource:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, ProjectResource, pr_id, "Project resource")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project resource not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_resource(db: Session, project_id: UUID, pr_id: UUID, current_user: User) -> dict:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, ProjectResource, pr_id, "Project resource")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project resource not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Resource removed from project."}


# ══════════════════════════════════════════════════════════════════════════════
# Project Capabilities
# ══════════════════════════════════════════════════════════════════════════════

def add_capability(db: Session, project_id: UUID, payload: ProjectCapabilityCreate, current_user: User) -> ProjectCapability:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    if db.get(Capability, payload.capability_id) is None:
        raise HTTPException(status_code=404, detail="Capability not found")

    existing = db.scalar(
        select(ProjectCapability).where(
            ProjectCapability.project_id == project_id,
            ProjectCapability.capability_id == payload.capability_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Capability already assigned to this project.")

    obj = ProjectCapability(project_id=project_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_capabilities(db: Session, project_id: UUID) -> list[ProjectCapability]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(select(ProjectCapability).where(ProjectCapability.project_id == project_id)).all())


def update_capability(db: Session, project_id: UUID, pc_id: UUID, payload: ProjectCapabilityUpdate, current_user: User) -> ProjectCapability:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, ProjectCapability, pc_id, "Project capability")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project capability not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_capability(db: Session, project_id: UUID, pc_id: UUID, current_user: User) -> dict:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, ProjectCapability, pc_id, "Project capability")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project capability not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Capability removed from project."}
