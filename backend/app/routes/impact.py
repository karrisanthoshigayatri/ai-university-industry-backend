"""Impact, Beneficiary, Feedback, Notification, AuditLog routes — Steps 23–25."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.impact import (
    AuditLogResponse, BeneficiaryCreate, BeneficiaryResponse, BeneficiaryUpdate,
    FeedbackCreate, FeedbackResponse, ImpactCreate, ImpactResponse,
    ImpactUpdate, NotificationResponse,
)
from app.services.impact import (
    audit_event, beneficiary_summary, create_beneficiary, create_feedback,
    create_impact, delete_beneficiary, delete_impact,
    feedback_summary, get_audit_log, get_impact,
    get_notifications, get_unread_notifications,
    impact_summary, list_audit_logs, list_beneficiaries,
    list_feedback, list_impacts, mark_all_read,
    mark_notification_read, update_beneficiary, update_impact,
)

router = APIRouter(tags=["impact-notifications-audit"])
DB = Annotated[Session, Depends(get_db)]
CU = Annotated[User, Depends(get_current_user)]


# ── Impact Records ─────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/impact", response_model=ImpactResponse, status_code=201)
def create_i(project_id: UUID, p: ImpactCreate, db: DB, cu: CU):
    return create_impact(db, project_id, p, cu)


@router.get("/api/projects/{project_id}/impact", response_model=list[ImpactResponse])
def list_i(project_id: UUID, db: DB, _: CU):
    return list_impacts(db, project_id)


@router.get("/api/projects/{project_id}/impact/summary")
def summary_i(project_id: UUID, db: DB, _: CU):
    return impact_summary(db, project_id)


@router.get("/api/projects/{project_id}/impact/{impact_id}", response_model=ImpactResponse)
def get_i(project_id: UUID, impact_id: UUID, db: DB, _: CU):
    return get_impact(db, project_id, impact_id)


@router.put("/api/projects/{project_id}/impact/{impact_id}", response_model=ImpactResponse)
def update_i(project_id: UUID, impact_id: UUID, p: ImpactUpdate, db: DB, cu: CU):
    return update_impact(db, project_id, impact_id, p, cu)


@router.delete("/api/projects/{project_id}/impact/{impact_id}")
def delete_i(project_id: UUID, impact_id: UUID, db: DB, cu: CU):
    return delete_impact(db, project_id, impact_id, cu)


# ── Beneficiaries ──────────────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/beneficiaries",
             response_model=BeneficiaryResponse, status_code=201)
def create_b(project_id: UUID, p: BeneficiaryCreate, db: DB, cu: CU):
    return create_beneficiary(db, project_id, p, cu)


@router.get("/api/projects/{project_id}/beneficiaries",
            response_model=list[BeneficiaryResponse])
def list_b(project_id: UUID, db: DB, _: CU):
    return list_beneficiaries(db, project_id)


@router.get("/api/projects/{project_id}/beneficiaries/summary")
def summary_b(project_id: UUID, db: DB, _: CU):
    return beneficiary_summary(db, project_id)


@router.put("/api/projects/{project_id}/beneficiaries/{ben_id}",
            response_model=BeneficiaryResponse)
def update_b(project_id: UUID, ben_id: UUID, p: BeneficiaryUpdate, db: DB, cu: CU):
    return update_beneficiary(db, project_id, ben_id, p, cu)


@router.delete("/api/projects/{project_id}/beneficiaries/{ben_id}")
def delete_b(project_id: UUID, ben_id: UUID, db: DB, cu: CU):
    return delete_beneficiary(db, project_id, ben_id, cu)


# ── Feedback ───────────────────────────────────────────────────────────────────

@router.post("/api/feedback", response_model=FeedbackResponse, status_code=201)
def create_fb(p: FeedbackCreate, db: DB, cu: CU):
    return create_feedback(db, p, cu)


@router.get("/api/feedback", response_model=list[FeedbackResponse])
def list_fb(db: DB, _: CU,
            project_id: UUID | None = Query(default=None),
            problem_id: UUID | None = Query(default=None)):
    return list_feedback(db, project_id, problem_id)


@router.get("/api/feedback/summary")
def fb_summary(db: DB, _: CU,
               project_id: UUID | None = Query(default=None),
               problem_id: UUID | None = Query(default=None)):
    return feedback_summary(db, project_id, problem_id)


# ── Notifications ──────────────────────────────────────────────────────────────

@router.get("/api/notifications", response_model=list[NotificationResponse])
def get_notifs(db: DB, cu: CU):
    return get_notifications(db, cu)


@router.get("/api/notifications/unread", response_model=list[NotificationResponse])
def get_unread(db: DB, cu: CU):
    return get_unread_notifications(db, cu)


@router.put("/api/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notif(notification_id: UUID, db: DB, cu: CU):
    return mark_notification_read(db, notification_id, cu)


@router.put("/api/notifications/read-all")
def read_all(db: DB, cu: CU):
    return mark_all_read(db, cu)


# ── Audit Logs ─────────────────────────────────────────────────────────────────

@router.get("/api/audit-logs", response_model=list[AuditLogResponse])
def list_audit(db: DB, cu: CU,
               entity_type: str | None = Query(default=None)):
    return list_audit_logs(db, cu, entity_type)


@router.get("/api/audit-logs/{audit_id}", response_model=AuditLogResponse)
def get_audit(audit_id: UUID, db: DB, cu: CU):
    return get_audit_log(db, audit_id, cu)
