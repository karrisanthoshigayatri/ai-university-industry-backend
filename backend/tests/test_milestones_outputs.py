"""
STEP 22 — Milestones + Outputs + Collaboration lifecycle
10 test scenarios.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.collaboration import CollaborationRequest, ProjectPartner
from app.models.hei import HeiProfile
from app.models.milestone import ProjectMilestone, ProjectOutput
from app.models.organization import Organization
from app.models.partner import PartnerProfile
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
    citizen = User(organization_id=gov_org.organization_id, name="Cit",
                   email=f"c{_uid()}@x.com", password_hash=hash_password("P1"),
                   role="Citizen", status="active")
    db.add(gov); db.add(citizen); db.flush()
    _s.gov = gov; _s.citizen = citizen

    hei_org = Organization(name=f"H{_uid()}", organization_type="HEI",
                           official_identifier=f"H-{_uid()}")
    db.add(hei_org); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id,
                     institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()

    prob = Problem(title=f"MS Prob {_uid()}", description="t",
                   submitter_id=gov.user_id, source_type="Government",
                   current_status="Validated")
    db.add(prob); db.flush()

    proj = Project(problem_id=prob.problem_id, hei_id=hei.hei_id,
                   title="MS Project", status="Active", current_stage="Development")
    db.add(proj); db.flush()
    _s.proj = proj
    _s._proj_id = str(proj.project_id)

    partner_org = Organization(name=f"P{_uid()}", organization_type="Industry",
                               official_identifier=f"P-{_uid()}")
    db.add(partner_org); db.flush()
    partner = PartnerProfile(organization_id=partner_org.organization_id,
                              partner_type="Industry", verification_status="Verified")
    db.add(partner); db.flush()
    _s.partner = partner
    _s._partner_id = str(partner.partner_id)

    db.commit()
    _s.hei_org = hei_org; _s.gov_org = gov_org
    _s.partner_org = partner_org; _s.hei = hei; _s.prob = prob

    yield

    for m in [CollaborationRequest, ProjectPartner, ProjectMilestone,
              ProjectOutput, Project]:
        try: db.execute(delete(m)); db.commit()
        except: db.rollback()
    for obj in [partner, partner_org, prob, hei, hei_org, citizen, gov, gov_org]:
        try: db.delete(obj); db.commit()
        except: db.rollback()
    db.close()


# ── TEST 1 — Create milestone ──────────────────────────────────────────────────

def test_01_create_milestone():
    resp = client.post(f"/api/projects/{_s._proj_id}/milestones",
                       headers=_bearer(_s.gov),
                       json={"name": "Phase 1 Complete",
                             "description": "Initial design done",
                             "stage": "Development",
                             "status": "Pending"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["name"] == "Phase 1 Complete"
    assert d["status"] == "Pending"
    _s._milestone_id = d["milestone_id"]


# ── TEST 2 — List milestones ───────────────────────────────────────────────────

def test_02_list_milestones():
    resp = client.get(f"/api/projects/{_s._proj_id}/milestones",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    ids = [m["milestone_id"] for m in resp.json()]
    assert _s._milestone_id in ids


# ── TEST 3 — Update milestone status ──────────────────────────────────────────

def test_03_update_milestone_status():
    resp = client.put(
        f"/api/projects/{_s._proj_id}/milestones/{_s._milestone_id}/status",
        headers=_bearer(_s.gov),
        json={"status": "In Progress", "remarks": "Work started"})
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["status"] == "In Progress"
    assert d["remarks"] == "Work started"


# ── TEST 4 — Complete milestone ────────────────────────────────────────────────

def test_04_complete_milestone():
    resp = client.put(
        f"/api/projects/{_s._proj_id}/milestones/{_s._milestone_id}/status",
        headers=_bearer(_s.gov),
        json={"status": "Completed", "completion_date": "2026-09-06"})
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["status"] == "Completed"
    assert d["completion_date"] == "2026-09-06"


# ── TEST 5 — Create project output ────────────────────────────────────────────

def test_05_create_output():
    resp = client.post(f"/api/projects/{_s._proj_id}/outputs",
                       headers=_bearer(_s.gov),
                       json={"output_type": "Prototype",
                             "title": "IoT Irrigation Prototype v1",
                             "description": "First working prototype",
                             "date": "2026-09-06"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["output_type"] == "Prototype"
    assert d["title"] == "IoT Irrigation Prototype v1"
    _s._output_id = d["output_id"]


# ── TEST 6 — List + get output ─────────────────────────────────────────────────

def test_06_list_and_get_output():
    resp = client.get(f"/api/projects/{_s._proj_id}/outputs",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    assert any(o["output_id"] == _s._output_id for o in resp.json())

    resp2 = client.get(f"/api/projects/{_s._proj_id}/outputs/{_s._output_id}",
                       headers=_bearer(_s.gov))
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["output_id"] == _s._output_id


# ── TEST 7 — Collaboration request lifecycle (Requested → Accepted) ────────────

def test_07_collab_request_lifecycle():
    # Create request
    r1 = client.post(f"/api/projects/{_s._proj_id}/collaboration-requests",
                     headers=_bearer(_s.gov),
                     json={"partner_id": _s._partner_id,
                           "contribution_type": "Technology",
                           "message": "Need IoT support"})
    assert r1.status_code == 201, r1.text
    req_id = r1.json()["request_id"]
    assert r1.json()["status"] == "Requested"

    # Accept
    r2 = client.put(f"/api/collaboration-requests/{req_id}/status",
                    headers=_bearer(_s.gov),
                    json={"status": "Accepted",
                          "response_message": "Happy to collaborate"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "Accepted"
    assert r2.json()["responded_at"] is not None


# ── TEST 8 — Add and prevent duplicate project partner ─────────────────────────

def test_08_project_partner_and_duplicate():
    r1 = client.post(f"/api/projects/{_s._proj_id}/partners",
                     headers=_bearer(_s.gov),
                     json={"partner_id": _s._partner_id,
                           "contribution_type": "Technology",
                           "status": "Active"})
    assert r1.status_code == 201, r1.text

    r2 = client.post(f"/api/projects/{_s._proj_id}/partners",
                     headers=_bearer(_s.gov),
                     json={"partner_id": _s._partner_id,
                           "contribution_type": "Technology",
                           "status": "Active"})
    assert r2.status_code == 409, r2.text


# ── TEST 9 — Authorization: citizen gets 403 ──────────────────────────────────

def test_09_authorization():
    resp = client.post(f"/api/projects/{_s._proj_id}/milestones",
                       headers=_bearer(_s.citizen),
                       json={"name": "Unauthorized", "status": "Pending"})
    assert resp.status_code == 403, resp.text

    resp2 = client.post(f"/api/projects/{_s._proj_id}/outputs",
                        headers=_bearer(_s.citizen),
                        json={"output_type": "Software",
                              "title": "Unauthorized Output"})
    assert resp2.status_code == 403, resp2.text


# ── TEST 10 — Invalid IDs return 404 + persistence check ──────────────────────

def test_10_invalid_ids_and_persistence():
    fake = str(uuid.uuid4())

    resp = client.get(f"/api/projects/{fake}/milestones",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 404, resp.text

    resp2 = client.get(f"/api/projects/{_s._proj_id}/milestones/{fake}",
                       headers=_bearer(_s.gov))
    assert resp2.status_code == 404, resp2.text

    # Verify milestone persisted — look up from DB directly
    db = SessionLocal()
    try:
        from sqlalchemy import select
        ms = list(db.scalars(
            select(ProjectMilestone).where(
                ProjectMilestone.project_id == _s.proj.project_id
            )
        ).all())
        assert len(ms) >= 1

        outs = list(db.scalars(
            select(ProjectOutput).where(
                ProjectOutput.project_id == _s.proj.project_id
            )
        ).all())
        assert len(outs) >= 1
        assert any(o.output_type == "Prototype" for o in outs)
    finally:
        db.close()
