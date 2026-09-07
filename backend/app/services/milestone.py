"""Service layer for ProjectMilestone, ProjectOutput and AuditLog helper."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.milestone import AuditLog, ProjectMilestone, ProjectOutput
from app.models.project import Project
from app.models.user import User
from app.schemas.milestone import (
    MilestoneCreate, MilestoneStatusUpdate, MilestoneUpdate,
    OutputCreate, OutputUpdate,
)

_WRITE = {"Government Officer", "HEI Administrator", "System Administrator",
          "Industry / MSME / Startup", "Research Institution", "CSR Organization"}


def _get_or_404(db, model, pk, label):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _audit(db: Session, actor_id: UUID, action: str, entity_type: str,
           entity_id: UUID, new_value: dict | None = None) -> None:
    """Write a lightweight audit entry if the audit_log table exists."""
    try:
        db.add(AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            new_value=new_value,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db.flush()
    except Exception:
        db.rollback()


# ── Milestones ─────────────────────────────────────────────────────────────────

def create_milestone(db: Session, project_id: UUID, payload: MilestoneCreate,
                     current_user: User) -> ProjectMilestone:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    now = datetime.now(timezone.utc)
    obj = ProjectMilestone(project_id=project_id, created_at=now, updated_at=now,
                           **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    _audit(db, current_user.user_id, "create", "project_milestone", obj.milestone_id,
           {"name": obj.name, "status": obj.status})
    db.commit()
    return obj


def list_milestones(db: Session, project_id: UUID) -> list[ProjectMilestone]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(
        select(ProjectMilestone).where(ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.due_date.asc().nullslast())
    ).all())


def get_milestone(db: Session, project_id: UUID, milestone_id: UUID) -> ProjectMilestone:
    m = _get_or_404(db, ProjectMilestone, milestone_id, "Milestone")
    if m.project_id != project_id:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return m


def update_milestone(db: Session, project_id: UUID, milestone_id: UUID,
                     payload: MilestoneUpdate, current_user: User) -> ProjectMilestone:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    m = get_milestone(db, project_id, milestone_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return m


def delete_milestone(db: Session, project_id: UUID, milestone_id: UUID,
                     current_user: User) -> dict:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    m = get_milestone(db, project_id, milestone_id)
    db.delete(m); db.commit()
    return {"detail": "Milestone deleted."}


def update_milestone_status(db: Session, project_id: UUID, milestone_id: UUID,
                             payload: MilestoneStatusUpdate,
                             current_user: User) -> ProjectMilestone:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    m = get_milestone(db, project_id, milestone_id)
    old_status = m.status
    m.status = payload.status
    if payload.completion_date:
        m.completion_date = payload.completion_date
    if payload.remarks:
        m.remarks = payload.remarks
    db.commit(); db.refresh(m)
    _audit(db, current_user.user_id, "status_change", "project_milestone", m.milestone_id,
           {"old_status": old_status, "new_status": m.status})
    db.commit()
    return m


# ── Outputs ────────────────────────────────────────────────────────────────────

def create_output(db: Session, project_id: UUID, payload: OutputCreate,
                  current_user: User) -> ProjectOutput:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    now = datetime.now(timezone.utc)
    obj = ProjectOutput(project_id=project_id, created_at=now, updated_at=now,
                        output_type=payload.output_type,
                        title=payload.title,
                        description=payload.description,
                        evidence=payload.evidence,
                        date=payload.output_date)
    db.add(obj); db.commit(); db.refresh(obj)
    _audit(db, current_user.user_id, "create", "project_output", obj.output_id,
           {"output_type": obj.output_type, "title": obj.title})
    db.commit()
    return obj


def list_outputs(db: Session, project_id: UUID) -> list[ProjectOutput]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(
        select(ProjectOutput).where(ProjectOutput.project_id == project_id)
        .order_by(ProjectOutput.created_at.desc())
    ).all())


def get_output(db: Session, project_id: UUID, output_id: UUID) -> ProjectOutput:
    o = _get_or_404(db, ProjectOutput, output_id, "Output")
    if o.project_id != project_id:
        raise HTTPException(status_code=404, detail="Output not found")
    return o


def update_output(db: Session, project_id: UUID, output_id: UUID,
                  payload: OutputUpdate, current_user: User) -> ProjectOutput:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    o = get_output(db, project_id, output_id)
    for k, v in payload.model_dump(exclude_unset=True, by_alias=False).items():
        db_key = "date" if k == "output_date" else k
        setattr(o, db_key, v)
    db.commit(); db.refresh(o)
    return o


def delete_output(db: Session, project_id: UUID, output_id: UUID,
                  current_user: User) -> dict:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    o = get_output(db, project_id, output_id)
    db.delete(o); db.commit()
    return {"detail": "Output deleted."}
