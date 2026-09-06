"""
STEP 15 — Faculty and Resource Contextual Matching
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
from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.evidence import Availability
from app.models.faculty_resource_match import FacultyResourceMatch
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.organization import Organization
from app.models.problem import Problem
from app.models.user import User

client = TestClient(app, raise_server_exceptions=True)


def _uid():
    return uuid.uuid4().hex[:8]


def _bearer(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.user_id), user.role)}"}


# ══════════════════════════════════════════════════════════════════════════════
# Shared test state (created once, cleaned up once)
# ══════════════════════════════════════════════════════════════════════════════

class _SharedState:
    """Holds all created objects for the test session."""
    db: Session
    gov_user: User
    caps: list[Capability]
    hei: HeiProfile
    hei_user: User
    fac: FacultyExpertProfile
    res: InstitutionalResource
    validated_problem: Problem
    submitted_problem: Problem
    gov_org: Organization
    hei_org: Organization
    req_profile: ProblemRequirementProfile


_state = _SharedState()


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """Create all test data once; tear it down after all tests."""
    db = SessionLocal()
    _state.db = db

    # Gov org + user
    gov_org = Organization(name=f"GovOrg {_uid()}", organization_type="Government",
                           official_identifier=f"G-{_uid()}")
    db.add(gov_org); db.flush()
    gov_user = User(organization_id=gov_org.organization_id, name="GovOfficer",
                    email=f"gov{_uid()}@example.com",
                    password_hash=hash_password("P@ss1"),
                    role="Government Officer", status="active")
    db.add(gov_user); db.flush()
    _state.gov_user = gov_user
    _state.gov_org = gov_org

    # Capabilities
    cap_defs = [("IoT FR", "Technology"), ("Agriculture FR", "Domain"), ("WaterTest FR", "Resource")]
    caps = []
    for name, ctype in cap_defs:
        c = Capability(name=f"{name} {_uid()}", capability_type=ctype, status="Active")
        db.add(c); caps.append(c)
    db.flush()
    _state.caps = caps

    # HEI org + user + profile
    hei_org = Organization(name=f"HEI {_uid()}", organization_type="HEI",
                           official_identifier=f"H-{_uid()}", state="Karnataka")
    db.add(hei_org); db.flush()
    hei_user = User(organization_id=hei_org.organization_id, name="FacultyUser",
                    email=f"fac{_uid()}@example.com",
                    password_hash=hash_password("P@ss1"),
                    role="Faculty / Expert", status="active")
    db.add(hei_user); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id,
                     institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()
    _state.hei = hei
    _state.hei_user = hei_user
    _state.hei_org = hei_org

    # HEI capability
    hc = HeiCapability(hei_id=hei.hei_id, capability_id=caps[0].capability_id,
                       proficiency_level="Expert", status="Active")
    db.add(hc); db.flush()

    # Faculty
    fac = FacultyExpertProfile(hei_id=hei.hei_id, user_id=hei_user.user_id,
                                designation="Dr. IoT Expert", department="Electronics",
                                specialization="IoT", experience_years=8,
                                verification_status="Verified")
    db.add(fac); db.flush()
    _state.fac = fac

    fc1 = FacultyExpertCapability(faculty_id=fac.faculty_id,
                                   capability_id=caps[0].capability_id,
                                   proficiency_level="Expert",
                                   evidence_description="IoT papers",
                                   status="Active")
    fc2 = FacultyExpertCapability(faculty_id=fac.faculty_id,
                                   capability_id=caps[1].capability_id,
                                   proficiency_level="Advanced",
                                   status="Active")
    db.add(fc1); db.add(fc2); db.flush()

    # Resource
    res = InstitutionalResource(hei_id=hei.hei_id, name="Water Testing Lab",
                                 resource_type="Laboratory",
                                 availability_status="Available",
                                 verification_status="Verified")
    db.add(res); db.flush()
    _state.res = res

    rc = ResourceCapability(resource_id=res.resource_id,
                             capability_id=caps[2].capability_id,
                             proficiency_level="Advanced", status="Active")
    db.add(rc); db.flush()

    # Validated problem
    prob = Problem(
        title="Smart Irrigation Monitoring",
        description="IoT-based irrigation with water quality testing.",
        submitter_id=gov_user.user_id,
        source_type="Government",
        location="Karnataka",
        current_status="Validated",
    )
    db.add(prob); db.flush()
    _state.validated_problem = prob

    profile = ProblemRequirementProfile(
        problem_id=prob.problem_id,
        required_support="IoT + water testing",
        confidence=0.9, model_version="test-v1",
    )
    db.add(profile); db.flush()
    _state.req_profile = profile

    for cap_id, rtype, level, crit in [
        (caps[0].capability_id, "Technology", 3.0, 1.0),
        (caps[1].capability_id, "Domain",     1.0, 0.7),
        (caps[2].capability_id, "Resource",   2.0, 0.8),
    ]:
        db.add(ProblemRequirementCapability(
            requirement_profile_id=profile.requirement_profile_id,
            capability_id=cap_id, requirement_type=rtype,
            required_level=level, criticality=crit, confidence=0.85,
        ))

    # Submitted (non-validated) problem
    submitted = Problem(
        title="Non-Validated Problem",
        description="Pending.",
        submitter_id=gov_user.user_id,
        source_type="Government",
        current_status="Submitted",
    )
    db.add(submitted); db.flush()
    _state.submitted_problem = submitted

    db.commit()

    yield  # ── tests run here ─────────────────────────────────────────────

    # Cleanup: delete in dependency order
    db.execute(
        __import__("sqlalchemy", fromlist=["delete"]).delete(FacultyResourceMatch).where(
            FacultyResourceMatch.problem_id.in_(
                [prob.problem_id, submitted.problem_id]
            )
        )
    )
    db.commit()
    for obj in [submitted, profile, prob, rc, res, fc2, fc1, fac, hc,
                hei, hei_user, hei_org] + caps + [gov_user, gov_org]:
        try:
            db.delete(obj)
            db.commit()
        except Exception:
            db.rollback()
    db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_01_validated_problem_matches():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_matches"] >= 1


def test_02_non_validated_problem_rejected():
    resp = client.post(
        f"/api/matching/problems/{_state.submitted_problem.problem_id}/faculty-resources",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 400, resp.text
    assert "status" in resp.json()["detail"].lower() or "Validated" in resp.json()["detail"]


def test_03_faculty_matches_returned():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
        f"?hei_id={_state.hei.hei_id}",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["faculty_matches"] >= 1
    fac_m = [m for m in data["matches"] if m["match_type"] == "Faculty"]
    assert len(fac_m) >= 1
    assert any(c["match_status"] == "matched" for m in fac_m
               for c in m["matched_capabilities"])


def test_04_resource_matches_returned():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
        f"?hei_id={_state.hei.hei_id}",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["resource_matches"] >= 1
    res_m = [m for m in data["matches"] if m["match_type"] == "Resource"]
    assert len(res_m) >= 1


def test_05_scores_valid_range():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
        f"?hei_id={_state.hei.hei_id}",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 200, resp.text
    for m in resp.json()["matches"]:
        assert 0 <= m["match_score"] <= 100
        bd = m["score_breakdown"]
        assert 0 <= bd["total"] <= 100
        assert abs(
            bd["capability_score"] + bd["domain_score"] + bd["evidence_score"]
            + bd["availability_score"] + bd["constraint_score"] - bd["total"]
        ) < 0.1


def test_06_results_are_ranked():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
        f"?hei_id={_state.hei.hei_id}",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 200, resp.text
    matches = resp.json()["matches"]
    ranks = [m["rank"] for m in matches]
    assert ranks == sorted(ranks)
    if len(matches) >= 2:
        assert matches[0]["match_score"] >= matches[1]["match_score"]


def test_07_availability_affects_scoring():
    """Add an availability record and verify it appears in reasons."""
    db = SessionLocal()
    try:
        av = Availability(entity_type="faculty_expertise",
                          entity_id=_state.fac.faculty_id, status="Available")
        db.add(av); db.commit()

        resp = client.post(
            f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
            f"?hei_id={_state.hei.hei_id}",
            headers=_bearer(_state.gov_user),
        )
        assert resp.status_code == 200, resp.text
        fac_m = [m for m in resp.json()["matches"] if m["match_type"] == "Faculty"]
        assert len(fac_m) >= 1
        all_reasons = [r for m in fac_m for r in m["match_reasons"]]
        assert any("avail" in r.lower() or "confirm" in r.lower() for r in all_reasons)

        db.delete(av); db.commit()
    finally:
        db.close()


def test_08_unauthenticated_returns_401():
    resp = client.post(
        f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
    )
    assert resp.status_code == 401, resp.text


def test_09_snapshots_persisted_with_model_version():
    db = SessionLocal()
    try:
        client.post(
            f"/api/matching/problems/{_state.validated_problem.problem_id}/faculty-resources"
            f"?hei_id={_state.hei.hei_id}",
            headers=_bearer(_state.gov_user),
        )
        records = list(db.scalars(
            select(FacultyResourceMatch).where(
                FacultyResourceMatch.problem_id == _state.validated_problem.problem_id
            )
        ).all())
        assert len(records) >= 1
        assert all(r.model_version == "faculty-resource-matching-v1" for r in records)
        assert all(r.match_type in ("Faculty", "Resource") for r in records)
    finally:
        db.close()


def test_10_problem_not_found_returns_404():
    resp = client.post(
        f"/api/matching/problems/{uuid.uuid4()}/faculty-resources",
        headers=_bearer(_state.gov_user),
    )
    assert resp.status_code == 404, resp.text
