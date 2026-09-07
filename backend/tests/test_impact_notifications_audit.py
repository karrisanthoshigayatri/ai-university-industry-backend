"""
STEPS 23–25 — Impact, Notifications, Audit Log
10 test scenarios.

Notes on Supabase constraints:
  - feedback.submitted_by  → FK to app_user  → set to NULL (nullable)
  - notification.recipient_id → FK to app_user → test endpoints only (no direct insert)
  - audit_log.actor_id     → FK to app_user  → set to NULL in audit_event()
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.hei import HeiProfile
from app.models.impact import Beneficiary, Feedback, ImpactRecord
from app.models.milestone import AuditLog
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.problem import Problem
from app.models.project import Project
from app.models.user import User

client = TestClient(app, raise_server_exceptions=True)


def _uid(): return uuid.uuid4().hex[:8]
def _bearer(u): return {"Authorization": f"Bearer {create_access_token(str(u.user_id), u.role)}"}


class _S: pass
_s = _S()


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    db = SessionLocal()

    gov_org = Organization(name=f"G{_uid()}", organization_type="Government",
                           official_identifier=f"G-{_uid()}")
    db.add(gov_org); db.flush()
    gov = User(organization_id=gov_org.organization_id, name="Gov",
               email=f"g{_uid()}@x.com", password_hash=hash_password("P1"),
               role="Government Officer", status="active")
    sys_admin = User(organization_id=gov_org.organization_id, name="Sys",
                     email=f"s{_uid()}@x.com", password_hash=hash_password("P1"),
                     role="System Administrator", status="active")
    citizen = User(organization_id=gov_org.organization_id, name="Cit",
                   email=f"c{_uid()}@x.com", password_hash=hash_password("P1"),
                   role="Citizen", status="active")
    db.add(gov); db.add(sys_admin); db.add(citizen); db.flush()
    _s.gov = gov; _s.sys_admin = sys_admin; _s.citizen = citizen

    hei_org = Organization(name=f"H{_uid()}", organization_type="HEI",
                           official_identifier=f"H-{_uid()}")
    db.add(hei_org); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id,
                     institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()

    prob = Problem(title=f"IP Prob {_uid()}", description="t",
                   submitter_id=gov.user_id, source_type="Government",
                   current_status="Validated")
    db.add(prob); db.flush()

    proj = Project(problem_id=prob.problem_id, hei_id=hei.hei_id,
                   title="Impact Project", status="Active", current_stage="Pilot")
    db.add(proj); db.flush()
    _s.proj = proj; _s._proj_id = str(proj.project_id)
    _s.prob = prob; _s._prob_id = str(prob.problem_id)

    db.commit()
    _s.hei = hei; _s.hei_org = hei_org; _s.gov_org = gov_org

    yield

    for m in [AuditLog, Feedback, Beneficiary, ImpactRecord, Project]:
        try: db.execute(delete(m)); db.commit()
        except: db.rollback()
    for obj in [prob, hei, hei_org, citizen, sys_admin, gov, gov_org]:
        try: db.delete(obj); db.commit()
        except: db.rollback()
    db.close()


# ── TEST 1 — Impact Record CRUD ────────────────────────────────────────────────

def test_01_impact_crud():
    r = client.post(f"/api/projects/{_s._proj_id}/impact",
                    headers=_bearer(_s.gov),
                    json={"metric": "Farmers benefited",
                          "baseline_value": 0, "target_value": 500,
                          "achieved_value": 350, "unit": "people"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["metric"] == "Farmers benefited"
    _s._impact_id = d["impact_id"]

    r2 = client.get(f"/api/projects/{_s._proj_id}/impact", headers=_bearer(_s.gov))
    assert any(i["impact_id"] == _s._impact_id for i in r2.json())

    r3 = client.put(f"/api/projects/{_s._proj_id}/impact/{_s._impact_id}",
                    headers=_bearer(_s.gov), json={"achieved_value": 420})
    assert r3.status_code == 200, r3.text
    assert float(r3.json()["achieved_value"]) == 420.0


# ── TEST 2 — Impact summary ────────────────────────────────────────────────────

def test_02_impact_summary():
    r = client.get(f"/api/projects/{_s._proj_id}/impact/summary",
                   headers=_bearer(_s.gov))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_records"] >= 1
    m = next((x for x in d["metrics"] if x["metric"] == "Farmers benefited"), None)
    assert m is not None
    assert m["achieved_pct"] is not None and m["achieved_pct"] > 0


# ── TEST 3 — Beneficiary CRUD ─────────────────────────────────────────────────

def test_03_beneficiary_crud():
    r = client.post(f"/api/projects/{_s._proj_id}/beneficiaries",
                    headers=_bearer(_s.gov),
                    json={"beneficiary_type": "Farmer",
                          "estimated_count": 500,
                          "affected_domain": "Agriculture"})
    assert r.status_code == 201, r.text
    _s._ben_id = r.json()["beneficiary_id"]

    r2 = client.get(f"/api/projects/{_s._proj_id}/beneficiaries/summary",
                    headers=_bearer(_s.gov))
    assert r2.status_code == 200, r2.text
    assert r2.json()["total_beneficiaries"] >= 500


# ── TEST 4 — Feedback (submitted_by is NULL due to app_user FK constraint) ─────

def test_04_feedback():
    # submitted_by is set to NULL by the service to avoid app_user FK violation
    r = client.post("/api/feedback", headers=_bearer(_s.gov),
                    json={"project_id": _s._proj_id, "rating": 4,
                          "comment": "Good progress", "feedback_type": "citizen"})
    assert r.status_code == 201, r.text
    assert r.json()["rating"] == 4
    # submitted_by is NULL (app_user FK isolation)
    assert r.json()["submitted_by"] is None

    r2 = client.get("/api/feedback/summary", headers=_bearer(_s.gov),
                    params={"project_id": _s._proj_id})
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["total"] >= 1
    assert d["average_rating"] is not None


# ── TEST 5 — Notification endpoints reachable ─────────────────────────────────

def test_05_notifications():
    # Notification endpoints work; recipient_id FK is to app_user so we
    # cannot insert test notifications directly, but GET endpoints must return 200
    r = client.get("/api/notifications", headers=_bearer(_s.gov))
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)

    r2 = client.get("/api/notifications/unread", headers=_bearer(_s.gov))
    assert r2.status_code == 200, r2.text
    assert isinstance(r2.json(), list)


# ── TEST 6 — Mark all read (empty set OK) ─────────────────────────────────────

def test_06_mark_all_read():
    r = client.put("/api/notifications/read-all", headers=_bearer(_s.gov))
    assert r.status_code == 200, r.text
    assert "marked as read" in r.json()["detail"]


# ── TEST 7 — Audit log entries exist from impact creation ─────────────────────

def test_07_audit_log_created():
    r = client.get("/api/audit-logs", headers=_bearer(_s.sys_admin),
                   params={"entity_type": "impact_record"})
    assert r.status_code == 200, r.text
    # actor_id is NULL (app_user FK isolation) but records should exist
    assert len(r.json()) >= 1


# ── TEST 8 — Audit log authorization (SysAdmin only) ──────────────────────────

def test_08_audit_log_authorization():
    assert client.get("/api/audit-logs", headers=_bearer(_s.gov)).status_code == 403
    assert client.get("/api/audit-logs", headers=_bearer(_s.citizen)).status_code == 403


# ── TEST 9 — Sensitive data never in audit log ────────────────────────────────

def test_09_no_sensitive_data_in_audit():
    r = client.get("/api/audit-logs", headers=_bearer(_s.sys_admin))
    assert r.status_code == 200, r.text
    for entry in r.json():
        for field in ["new_value", "old_value"]:
            val = entry.get(field) or {}
            for key in val:
                assert key.lower() not in {
                    "password", "password_hash", "secret_key",
                    "token", "jwt", "credential"
                }, f"Sensitive key '{key}' found in audit log"


# ── TEST 10 — Invalid IDs + persistence ───────────────────────────────────────

def test_10_invalid_ids_and_persistence():
    fake = str(uuid.uuid4())
    assert client.get(f"/api/projects/{fake}/impact",
                      headers=_bearer(_s.gov)).status_code == 404
    assert client.get(f"/api/projects/{_s._proj_id}/impact/{fake}",
                      headers=_bearer(_s.gov)).status_code == 404

    db = SessionLocal()
    try:
        impact = db.get(ImpactRecord, uuid.UUID(_s._impact_id))
        assert impact is not None
        assert impact.metric == "Farmers benefited"
    finally:
        db.close()
