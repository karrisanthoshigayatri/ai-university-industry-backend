"""
STEPS 16–18 — Project, Team, Resources, Capabilities
10 test scenarios against the live Supabase database.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.capability import Capability
from app.models.hei import HeiProfile, InstitutionalResource
from app.models.organization import Organization
from app.models.problem import Problem
from app.models.project import Project, ProjectCapability, ProjectResource, ProjectTeam, ProjectTeamMember
from app.models.user import User

client = TestClient(app, raise_server_exceptions=True)


def _uid():
    return uuid.uuid4().hex[:8]


def _bearer(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.user_id), user.role)}"}


class _S:
    db: Session
    gov_user: User
    sys_admin: User
    hei: HeiProfile
    resource: InstitutionalResource
    cap: Capability
    validated_problem: Problem
    submitted_problem: Problem
    project_id: str | None = None  # set after test_01


_s = _S()


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    db = SessionLocal()
    _s.db = db

    # Government org + officer
    gov_org = Organization(name=f"GovOrg {_uid()}", organization_type="Government",
                           official_identifier=f"G-{_uid()}")
    db.add(gov_org); db.flush()
    gov_user = User(organization_id=gov_org.organization_id, name="GovUser",
                    email=f"gov{_uid()}@example.com",
                    password_hash=hash_password("P@ss1"),
                    role="Government Officer", status="active")
    sys_admin = User(organization_id=gov_org.organization_id, name="SysAdmin",
                     email=f"sys{_uid()}@example.com",
                     password_hash=hash_password("P@ss1"),
                     role="System Administrator", status="active")
    db.add(gov_user); db.add(sys_admin); db.flush()
    _s.gov_user = gov_user; _s.sys_admin = sys_admin
    _s._gov_user_id = str(gov_user.user_id)

    # HEI
    hei_org = Organization(name=f"HEI {_uid()}", organization_type="HEI",
                           official_identifier=f"H-{_uid()}")
    db.add(hei_org); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id,
                     institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()
    _s.hei = hei
    _s._hei_id = str(hei.hei_id)

    # Resource
    res = InstitutionalResource(hei_id=hei.hei_id, name=f"Lab {_uid()}",
                                 resource_type="Laboratory",
                                 availability_status="Available",
                                 verification_status="Verified")
    db.add(res); db.flush()
    _s.resource = res
    _s._resource_id = str(res.resource_id)

    # Capability
    cap = Capability(name=f"TestCap {_uid()}", capability_type="Technology", status="Active")
    db.add(cap); db.flush()
    _s.cap = cap
    _s._cap_id = str(cap.capability_id)

    # Validated problem
    prob = Problem(title="Test Project Problem",
                   description="Needs a project.",
                   submitter_id=gov_user.user_id,
                   source_type="Government",
                   current_status="Validated")
    db.add(prob); db.flush()
    _s.validated_problem = prob
    _s._validated_problem_id = str(prob.problem_id)  # store as string

    # Non-validated problem
    submitted = Problem(title="Submitted Problem",
                        description="Not validated.",
                        submitter_id=gov_user.user_id,
                        source_type="Government",
                        current_status="Submitted")
    db.add(submitted); db.flush()
    _s.submitted_problem = submitted
    _s._submitted_problem_id = str(submitted.problem_id)

    db.commit()
    yield

    # Cleanup
    for m in [ProjectTeamMember, ProjectTeam, ProjectResource,
              ProjectCapability, Project]:
        db.execute(__import__("sqlalchemy", fromlist=["delete"]).delete(m))
        db.commit()
    for obj in [submitted, prob, cap, res, hei, hei_org,
                sys_admin, gov_user, gov_org]:
        try:
            db.delete(obj); db.commit()
        except Exception:
            db.rollback()
    db.close()


# ══════════════════════════════════════════════════════════════════════════════

def _get_project_id() -> str:
    """Return the project_id stored after test_01, or look it up."""
    pid = getattr(_s, "_project_id", None)
    if pid:
        return pid
    db = SessionLocal()
    try:
        import uuid as _uuid
        prob_id = _uuid.UUID(_s._validated_problem_id)
        proj = db.scalar(select(Project).where(Project.problem_id == prob_id))
        if proj:
            _s._project_id = str(proj.project_id)
            return _s._project_id
        return None
    finally:
        db.close()


def test_01_create_project():
    resp = client.post("/api/projects", headers=_bearer(_s.gov_user), json={
        "problem_id": _s._validated_problem_id,
        "hei_id": _s._hei_id,
        "title": "Smart Irrigation Project",
        "description": "IoT-based irrigation solution",
        "status": "Proposed",
        "current_stage": "Proposal",
    })
    assert resp.status_code == 201, resp.text
    d = resp.json()
    _s._project_id = d["project_id"]   # store for subsequent tests
    assert d["title"] == "Smart Irrigation Project"
    assert d["status"] == "Proposed"
    assert d["current_stage"] == "Proposal"


def test_02_non_validated_problem_rejected():
    resp = client.post("/api/projects", headers=_bearer(_s.gov_user), json={
        "problem_id": _s._submitted_problem_id,
        "hei_id": str(_s.hei.hei_id),
        "title": "Should Fail",
        "status": "Proposed",
        "current_stage": "Proposal",
    })
    assert resp.status_code == 400, resp.text


def test_03_get_project():
    pid = _get_project_id()
    assert pid is not None
    resp = client.get(f"/api/projects/{pid}", headers=_bearer(_s.gov_user))
    assert resp.status_code == 200, resp.text
    assert resp.json()["project_id"] == pid


def test_04_update_project_status_and_stage():
    pid = _get_project_id()
    r1 = client.put(f"/api/projects/{pid}/status",
                    headers=_bearer(_s.gov_user), json={"status": "Active"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "Active"

    r2 = client.put(f"/api/projects/{pid}/stage",
                    headers=_bearer(_s.gov_user), json={"current_stage": "Development"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["current_stage"] == "Development"


def test_05_create_team():
    pid = _get_project_id()
    resp = client.post(f"/api/projects/{pid}/team",
                       headers=_bearer(_s.gov_user),
                       json={"hei_id": _s._hei_id, "status": "Active"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["project_id"] == pid


def _get_app_user_id() -> str | None:
    """Get a user_id that exists in app_user (Supabase auth table)."""
    db = SessionLocal()
    try:
        row = db.execute(__import__("sqlalchemy", fromlist=["text"]).text(
            "SELECT user_id FROM app_user LIMIT 1"
        )).fetchone()
        return str(row[0]) if row else None
    finally:
        db.close()


def test_06_add_team_member():
    pid = _get_project_id()
    app_uid = _get_app_user_id()
    if app_uid is None:
        pytest.skip("No rows in app_user — cannot test team member FK constraint")
    resp = client.post(f"/api/projects/{pid}/team/members",
                       headers=_bearer(_s.gov_user),
                       json={"user_id": app_uid,
                             "member_type": "Expert",
                             "role": "Advisor",
                             "status": "Active"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["member_type"] == "Expert"
    _s._member_user_id = app_uid  # store for test_07


def test_07_duplicate_member_rejected():
    pid = _get_project_id()
    app_uid = getattr(_s, "_member_user_id", None) or _get_app_user_id()
    if app_uid is None:
        pytest.skip("No rows in app_user — cannot test duplicate member")
    payload = {"user_id": app_uid,
               "member_type": "Expert", "role": "Advisor", "status": "Active"}
    r1 = client.post(f"/api/projects/{pid}/team/members",
                     headers=_bearer(_s.gov_user), json=payload)
    r2 = client.post(f"/api/projects/{pid}/team/members",
                     headers=_bearer(_s.gov_user), json=payload)
    assert r1.status_code == 409 or r2.status_code == 409


def test_08_resource_assignment():
    pid = _get_project_id()
    resp = client.post(f"/api/projects/{pid}/resources",
                       headers=_bearer(_s.gov_user),
                       json={"resource_id": _s._resource_id,
                             "usage": "Testing", "access_status": "Requested"})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["resource_id"] == str(_s.resource.resource_id)


def test_09_capability_assignment():
    pid = _get_project_id()
    resp = client.post(f"/api/projects/{pid}/capabilities",
                       headers=_bearer(_s.gov_user),
                       json={"capability_id": _s._cap_id,
                             "source_type": "HEI", "strength_level": 3.5})
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["capability_id"] == str(_s.cap.capability_id)


def test_10_invalid_project_id_returns_404():
    resp = client.get(f"/api/projects/{uuid.uuid4()}", headers=_bearer(_s.gov_user))
    assert resp.status_code == 404, resp.text
