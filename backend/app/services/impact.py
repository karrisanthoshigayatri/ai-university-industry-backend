"""Services for Impact, Beneficiary, Feedback, Notification, AuditLog."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.impact import Beneficiary, Feedback, ImpactRecord
from app.models.milestone import AuditLog
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.schemas.impact import (
    BeneficiaryCreate, BeneficiaryUpdate,
    FeedbackCreate, ImpactCreate, ImpactUpdate,
)

_WRITE = {"Government Officer", "HEI Administrator", "System Administrator",
          "Industry / MSME / Startup", "Research Institution", "CSR Organization"}
_ADMIN = {"System Administrator"}
_SENSITIVE = {"password", "password_hash", "secret_key", "token", "jwt", "credential"}


def _get_or_404(db, model, pk, label):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _now_tz() -> datetime:
    return datetime.now(timezone.utc)


# ── Reusable notification helper ───────────────────────────────────────────────

def create_notification(
    db: Session,
    recipient_id: UUID,
    event_type: str,
    message: str,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        event_type=event_type,
        message=message,
        reference_type=reference_type,
        reference_id=reference_id,
        status="Unread",
        created_at=_now_naive(),
    )
    db.add(n)
    return n


# ── Reusable audit helper ──────────────────────────────────────────────────────

def audit_event(
    db: Session,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
) -> None:
    """Write an audit entry. Silently ignores any DB error."""
    if new_value:
        new_value = {k: v for k, v in new_value.items()
                     if k.lower() not in _SENSITIVE}
    if old_value:
        old_value = {k: v for k, v in old_value.items()
                     if k.lower() not in _SENSITIVE}
    try:
        db.add(AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            timestamp=_now_naive(),
        ))
        db.flush()
    except Exception:
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════
# Impact Records
# ══════════════════════════════════════════════════════════════════════════════

def create_impact(db: Session, project_id: UUID, payload: ImpactCreate,
                  current_user: User) -> ImpactRecord:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    now = _now_tz()
    obj = ImpactRecord(project_id=project_id, created_at=now, updated_at=now,
                       **payload.model_dump())
    db.add(obj)
    db.commit(); db.refresh(obj)
    audit_event(db, None, "create", "impact_record", obj.impact_id,
                new_value={"metric": obj.metric})
    db.commit()
    return obj


def list_impacts(db: Session, project_id: UUID) -> list[ImpactRecord]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(select(ImpactRecord).where(ImpactRecord.project_id == project_id)).all())


def get_impact(db: Session, project_id: UUID, impact_id: UUID) -> ImpactRecord:
    obj = _get_or_404(db, ImpactRecord, impact_id, "Impact record")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Impact record not found")
    return obj


def update_impact(db: Session, project_id: UUID, impact_id: UUID,
                  payload: ImpactUpdate, current_user: User) -> ImpactRecord:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = get_impact(db, project_id, impact_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


def delete_impact(db: Session, project_id: UUID, impact_id: UUID,
                  current_user: User) -> dict:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = get_impact(db, project_id, impact_id)
    db.delete(obj); db.commit()
    return {"detail": "Impact record deleted."}


def impact_summary(db: Session, project_id: UUID) -> dict:
    _get_or_404(db, Project, project_id, "Project")
    records = list_impacts(db, project_id)
    metrics = []
    for r in records:
        if r.target_value and r.target_value > 0 and r.achieved_value is not None:
            pct = round(float(r.achieved_value) / float(r.target_value) * 100, 1)
        else:
            pct = None
        metrics.append({"metric": r.metric, "achieved_pct": pct,
                         "achieved_value": float(r.achieved_value) if r.achieved_value else None,
                         "target_value": float(r.target_value) if r.target_value else None,
                         "unit": r.unit})
    return {"project_id": str(project_id), "total_records": len(records), "metrics": metrics}


# ══════════════════════════════════════════════════════════════════════════════
# Beneficiaries
# ══════════════════════════════════════════════════════════════════════════════

def create_beneficiary(db: Session, project_id: UUID, payload: BeneficiaryCreate,
                       current_user: User) -> Beneficiary:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _get_or_404(db, Project, project_id, "Project")
    now = _now_tz()
    obj = Beneficiary(project_id=project_id, created_at=now, updated_at=now,
                      **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def list_beneficiaries(db: Session, project_id: UUID) -> list[Beneficiary]:
    _get_or_404(db, Project, project_id, "Project")
    return list(db.scalars(select(Beneficiary).where(Beneficiary.project_id == project_id)).all())


def update_beneficiary(db: Session, project_id: UUID, ben_id: UUID,
                       payload: BeneficiaryUpdate, current_user: User) -> Beneficiary:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, Beneficiary, ben_id, "Beneficiary")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


def delete_beneficiary(db: Session, project_id: UUID, ben_id: UUID,
                       current_user: User) -> dict:
    if current_user.role not in _WRITE:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    obj = _get_or_404(db, Beneficiary, ben_id, "Beneficiary")
    if obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    db.delete(obj); db.commit()
    return {"detail": "Beneficiary deleted."}


def beneficiary_summary(db: Session, project_id: UUID) -> dict:
    _get_or_404(db, Project, project_id, "Project")
    rows = list_beneficiaries(db, project_id)
    total = sum(r.estimated_count or 0 for r in rows)
    breakdown = {}
    for r in rows:
        breakdown[r.beneficiary_type] = breakdown.get(r.beneficiary_type, 0) + (r.estimated_count or 0)
    return {"project_id": str(project_id), "total_beneficiaries": total,
            "breakdown": [{"type": k, "count": v} for k, v in breakdown.items()]}


# ══════════════════════════════════════════════════════════════════════════════
# Feedback
# ══════════════════════════════════════════════════════════════════════════════

def create_feedback(db: Session, payload: FeedbackCreate, current_user: User) -> Feedback:
    if not payload.project_id and not payload.problem_id:
        raise HTTPException(status_code=400, detail="Either project_id or problem_id is required.")
    data = payload.model_dump()
    obj = Feedback(submitted_by=None,
                   submitted_at=_now_naive(), **data)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def list_feedback(db: Session, project_id: UUID | None = None,
                  problem_id: UUID | None = None) -> list[Feedback]:
    stmt = select(Feedback)
    if project_id:
        stmt = stmt.where(Feedback.project_id == project_id)
    if problem_id:
        stmt = stmt.where(Feedback.problem_id == problem_id)
    return list(db.scalars(stmt.order_by(Feedback.submitted_at.desc())).all())


def feedback_summary(db: Session, project_id: UUID | None = None,
                     problem_id: UUID | None = None) -> dict:
    rows = list_feedback(db, project_id, problem_id)
    rated = [r for r in rows if r.rating is not None]
    avg = round(sum(r.rating for r in rated) / len(rated), 2) if rated else None
    dist = {str(i): sum(1 for r in rated if r.rating == i) for i in range(1, 6)}
    return {"total": len(rows), "average_rating": avg, "rating_distribution": dist}


# ══════════════════════════════════════════════════════════════════════════════
# Notifications
# ══════════════════════════════════════════════════════════════════════════════

def get_notifications(db: Session, current_user: User) -> list[Notification]:
    return list(db.scalars(
        select(Notification).where(Notification.recipient_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
    ).all())


def get_unread_notifications(db: Session, current_user: User) -> list[Notification]:
    return list(db.scalars(
        select(Notification).where(
            Notification.recipient_id == current_user.user_id,
            Notification.status == "Unread",
        ).order_by(Notification.created_at.desc())
    ).all())


def mark_notification_read(db: Session, notif_id: UUID, current_user: User) -> Notification:
    obj = _get_or_404(db, Notification, notif_id, "Notification")
    if obj.recipient_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your notification.")
    obj.status = "Read"
    obj.read_at = _now_naive()
    db.commit(); db.refresh(obj)
    return obj


def mark_all_read(db: Session, current_user: User) -> dict:
    rows = list(db.scalars(
        select(Notification).where(
            Notification.recipient_id == current_user.user_id,
            Notification.status == "Unread",
        )
    ).all())
    now = _now_naive()
    for r in rows:
        r.status = "Read"
        r.read_at = now
    db.commit()
    return {"detail": f"{len(rows)} notification(s) marked as read."}


# ══════════════════════════════════════════════════════════════════════════════
# Audit Log
# ══════════════════════════════════════════════════════════════════════════════

def list_audit_logs(db: Session, current_user: User,
                    entity_type: str | None = None) -> list[AuditLog]:
    if current_user.role not in _ADMIN:
        raise HTTPException(status_code=403, detail="System Administrators only.")
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    return list(db.scalars(stmt.limit(500)).all())


def get_audit_log(db: Session, audit_id: UUID, current_user: User) -> AuditLog:
    if current_user.role not in _ADMIN:
        raise HTTPException(status_code=403, detail="System Administrators only.")
    return _get_or_404(db, AuditLog, audit_id, "Audit log")
