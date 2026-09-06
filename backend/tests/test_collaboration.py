"""Step 21 — Collaboration Request + Project Partner tests."""

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

    gov_org = Organization(name=f"G{_uid()}", organization_type="Government", official_identifier=f"G-{_uid()}")
    db.add(gov_org); db.flush()
    gov = User(organization_id=gov_org.organization_id, name="Gov",
               email=f"g{_uid()}@x.com", password_hash=hash_password("P1"),
               role="Government Officer", status="active")
    citizen = User(organization_id=gov_org.organization_id, name="Cit",
                   email=f"c{_uid()}@x.com", password_hash=hash_password("P1"),
                   role="Citizen", status="active")
    db.add(gov); db.add(citizen); db.flush()
    _s.gov = gov; _s.citizen = citizen

    hei_org = Organization(name=f"H{_uid()}", organization_type="HEI", official_identifier=f"H-{_uid()}")
    db.add(hei_org); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id, institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()

    prob = Problem(title=f"CollabProb {_uid()}", description="test",
                   submitter_id=gov.user_id, source_type="Government", current_status="Validated")
    db.add(prob); db.flush()
    proj = Project(problem_id=prob.problem_id, hei_id=hei.hei_id,
                   title="Collab Project", status="Active", current_stage="Development")
    db.add(proj); db.flush()
    _s.proj = proj; _s._proj_id = str(proj.project_id)

    partner_org = Organization(name=f"P{_uid()}", organization_type="Industry", official_identifier=f"P-{_uid()}")
    db.add(partner_org); db.flush()
    partner = PartnerProfile(organization_id=partner_org.organization_id,
                              partner_type="Industry", verification_status="Verified")
    db.add(partner); db.flush()
    _s.partner = partner; _s._partner_id = str(partner.partner_id)

    partner2_org = Organization(name=f"P2{_uid()}", organization_type="MSME", official_identifier=f"P2-{_uid()}")
    db.add(partner2_org); db.flush()
    partner2 = PartnerProfile(organization_id=partner2_org.organization_id,
                               partner_type="MSME", verification_status="Verified")
    db.add(partner2); db.flush()
    _s.partner2 = partner2; _s._partner2_id = str(partner2.partner_id)

    db.commit()
    _s.db = db
    _s.prob = prob; _s.hei = hei
    _s.gov_org = gov_org; _s.hei_org = hei_org
    _s.partner_org = partner_org; _s.partner2_org = partner2_org

    yield

    for m in [CollaborationRequest, ProjectPartner, Project]:
        try: db.execute(delete(m)); db.commit()
        except: db.rollback()
    for obj in [partner2, partner2_org, partner, partner_org,
                prob, hei, hei_org, citizen, gov, gov_org]:
        try: db.delete(obj); db.commit()
        except: db.rollback()
    db.close()


def test_01_create_collaboration_request():
    resp = client.post(f"/api/projects/{_s._proj_id}/collaboration-requests",
                       headers=_bearer(_s.gov),
                       json={"partner_id": _s._partner_id,
                             "contribution_type": "Technology",
                             "message": "We need IoT expertise"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["partner_id"] == _s._partner_id
    assert d["status"] == "Requested"
    assert d["requested_by"] == str(_s.gov.user_id)
    _s._req_id = d["request_id"]


def test_02_list_collaboration_requests():
    resp = client.get(f"/api/projects/{_s._proj_id}/collaboration-requests",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    ids = [r["request_id"] for r in resp.json()]
    assert _s._req_id in ids


def test_03_get_collaboration_request():
    resp = client.get(f"/api/collaboration-requests/{_s._req_id}",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    assert resp.json()["request_id"] == _s._req_id


def test_04_update_request_status_accepted():
    resp = client.put(f"/api/collaboration-requests/{_s._req_id}/status",
                      headers=_bearer(_s.gov),
                      json={"status": "Accepted", "response_message": "Welcome aboard"})
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["status"] == "Accepted"
    assert d["responded_at"] is not None


def test_05_add_project_partner():
    resp = client.post(f"/api/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.gov),
                       json={"partner_id": _s._partner_id,
                             "contribution_type": "Technology",
                             "status": "Active"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["partner_id"] == _s._partner_id
    assert d["status"] == "Active"


def test_06_list_project_partners():
    resp = client.get(f"/api/projects/{_s._proj_id}/partners",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    ids = [p["partner_id"] for p in resp.json()]
    assert _s._partner_id in ids


def test_07_update_project_partner():
    resp = client.put(f"/api/projects/{_s._proj_id}/partners/{_s._partner_id}",
                      headers=_bearer(_s.gov),
                      json={"contribution_details": "Providing IoT sensors", "status": "Active"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["contribution_details"] == "Providing IoT sensors"


def test_08_duplicate_active_partnership_rejected():
    r1 = client.post(f"/api/projects/{_s._proj_id}/partners",
                     headers=_bearer(_s.gov),
                     json={"partner_id": _s._partner_id, "status": "Active"})
    assert r1.status_code == 409, r1.text


def test_09_unauthorized_returns_403():
    resp = client.post(f"/api/projects/{_s._proj_id}/collaboration-requests",
                       headers=_bearer(_s.citizen),
                       json={"partner_id": _s._partner2_id})
    assert resp.status_code == 403, resp.text


def test_10_delete_project_partner():
    resp = client.delete(f"/api/projects/{_s._proj_id}/partners/{_s._partner_id}",
                         headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "Partnership removed."
