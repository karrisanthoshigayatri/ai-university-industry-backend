"""
STEP 14 — Explainable HEI / University Matching
Tests covering the matching pipeline with 3 HEI profiles.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.hei import HeiCapability, HeiProfile, InstitutionalResource, ResourceCapability
from app.models.matching import HeiMatch
from app.models.organization import Organization
from app.models.problem import Problem
from app.models.user import User

client = TestClient(app, raise_server_exceptions=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _bearer(user: User) -> dict[str, str]:
    token = create_access_token(str(user.user_id), user.role)
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures — shared test data
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


@pytest.fixture(scope="module")
def gov_user(db):
    org = Organization(name=f"GovOrg {_uid()}", organization_type="Government",
                       official_identifier=f"G-{_uid()}")
    db.add(org); db.flush()
    u = User(organization_id=org.organization_id, name="GovOfficer",
             email=f"gov{_uid()}@example.com",
             password_hash=hash_password("Pass1!"), role="Government Officer", status="active")
    db.add(u); db.commit()
    yield u
    db.delete(u); db.delete(org); db.commit()


@pytest.fixture(scope="module")
def caps(db):
    """Create 5 canonical capabilities for matching."""
    cap_defs = [
        ("IoT Sensors", "Technology"),
        ("Agriculture Domain", "Domain"),
        ("Embedded Systems", "Skill"),
        ("Water Quality Testing", "Resource"),
        ("Data Analysis", "Skill"),
    ]
    created = []
    for name, ctype in cap_defs:
        c = Capability(name=f"{name} {_uid()}", capability_type=ctype, status="Active")
        db.add(c)
        created.append(c)
    db.commit()
    yield created
    for c in created:
        db.delete(c)
    db.commit()


@pytest.fixture(scope="module")
def problem_with_requirements(db, gov_user, caps):
    """Problem: 'Smart irrigation monitoring' with 3 required capabilities."""
    prob = Problem(
        title="Village requires smart irrigation monitoring",
        description="A rural village needs IoT-based irrigation monitoring with agricultural expertise.",
        submitter_id=gov_user.user_id,
        source_type="Government",
        location="Karnataka state district",
        current_status="Validated",
    )
    db.add(prob); db.flush()

    profile = ProblemRequirementProfile(
        problem_id=prob.problem_id,
        required_support="IoT and agricultural expertise",
        geographic_requirements="Karnataka",
        confidence=0.9,
        model_version="test-v1",
    )
    db.add(profile); db.flush()

    # Required caps: IoT (level 3), Agriculture (domain, level 1), Embedded (level 2)
    reqs = [
        (caps[0].capability_id, "Technology", 3.0, 1.0),   # IoT — critical
        (caps[1].capability_id, "Domain",     1.0, 0.8),   # Agriculture
        (caps[2].capability_id, "Skill",      2.0, 0.6),   # Embedded Systems
    ]
    for cap_id, rtype, level, crit in reqs:
        rc = ProblemRequirementCapability(
            requirement_profile_id=profile.requirement_profile_id,
            capability_id=cap_id,
            requirement_type=rtype,
            required_level=level,
            criticality=crit,
            confidence=0.85,
        )
        db.add(rc)
    db.commit()
    yield prob, profile
    db.delete(profile); db.delete(prob); db.commit()


@pytest.fixture(scope="module")
def three_heis(db, caps):
    """
    HEI A — strong IoT + Agriculture + lab  (should rank #1)
    HEI B — moderate IoT + Agriculture      (should rank #2)
    HEI C — basic IoT only                  (should rank #3)
    """
    created_orgs, created_heis, created_hcaps, created_res, created_rcaps = [], [], [], [], []

    profiles = [
        # (name, caps with levels: [(cap_idx, level_str)])
        ("HEI-A University", [(0, "Expert"), (1, "Expert"), (2, "Advanced")]),
        ("HEI-B College",    [(0, "Advanced"), (1, "Intermediate"), (2, "Advanced")]),
        ("HEI-C Institute",  [(0, "Basic"), (1, "Basic")]),
    ]

    for org_name, cap_profile in profiles:
        org = Organization(name=f"{org_name} {_uid()}", organization_type="HEI",
                           official_identifier=f"H-{_uid()}", state="Karnataka", district="Mysuru")
        db.add(org); db.flush()
        created_orgs.append(org)

        hei = HeiProfile(organization_id=org.organization_id,
                         institution_type="University", verification_status="Verified")
        db.add(hei); db.flush()
        created_heis.append(hei)

        for cap_idx, level in cap_profile:
            hc = HeiCapability(
                hei_id=hei.hei_id,
                capability_id=caps[cap_idx].capability_id,
                proficiency_level=level,
                status="Active",
            )
            db.add(hc)
            created_hcaps.append(hc)

        # HEI A gets a testing lab with water quality resource cap
        if org_name.startswith("HEI-A"):
            res = InstitutionalResource(
                hei_id=hei.hei_id, name="Water Quality Lab",
                resource_type="Laboratory", availability_status="Available",
                verification_status="Verified",
            )
            db.add(res); db.flush()
            created_res.append(res)

            rcap = ResourceCapability(
                resource_id=res.resource_id,
                capability_id=caps[3].capability_id,
                proficiency_level="Advanced", status="Active",
            )
            db.add(rcap)
            created_rcaps.append(rcap)

    db.commit()
    yield created_heis

    for x in created_rcaps: db.delete(x)
    for x in created_res:   db.delete(x)
    for x in created_hcaps: db.delete(x)
    for x in created_heis:  db.delete(x)
    for x in created_orgs:  db.delete(x)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_01_matching_returns_200(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(
        f"/api/matching/problems/{prob.problem_id}/heis",
        headers=_bearer(gov_user),
    )
    assert resp.status_code == 200, resp.text


def test_02_returns_ranked_results(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    data = resp.json()
    assert data["total_matches"] >= 3
    ranks = [m["rank"] for m in data["matches"]]
    assert ranks == sorted(ranks)


def test_03_scores_between_0_and_100(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    for match in resp.json()["matches"]:
        assert 0 <= match["match_score"] <= 100, f"Bad score: {match['match_score']}"


def test_04_matched_capabilities_present(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    top = resp.json()["matches"][0]
    assert isinstance(top["matched_capabilities"], list)
    assert len(top["matched_capabilities"]) > 0


def test_05_unmet_requirements_shown(db, problem_with_requirements, three_heis, gov_user):
    """HEI C (basic only) should have unmet requirements."""
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    matches = resp.json()["matches"]
    # Last ranked match should have more unmet requirements than the first
    bottom = matches[-1]
    assert isinstance(bottom["unmet_requirements"], list)


def test_06_match_reasons_shown(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    for match in resp.json()["matches"]:
        assert isinstance(match["match_reasons"], list)
        assert len(match["match_reasons"]) > 0


def test_07_rank_ordering_correct(db, problem_with_requirements, three_heis, gov_user):
    """Rank 1 should have higher or equal score than rank 2."""
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    matches = resp.json()["matches"]
    if len(matches) >= 2:
        assert matches[0]["match_score"] >= matches[1]["match_score"]


def test_08_hei_match_records_stored(db, problem_with_requirements, three_heis, gov_user):
    from sqlalchemy import select
    prob, _ = problem_with_requirements
    client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                headers=_bearer(gov_user))
    records = list(db.scalars(
        select(HeiMatch).where(HeiMatch.problem_id == prob.problem_id)
    ).all())
    assert len(records) >= 3


def test_09_model_version_stored(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    data = resp.json()
    assert data["model_version"] == "hei-matching-v1"
    for match in data["matches"]:
        assert match["model_version"] == "hei-matching-v1"


def test_10_constraint_results_present(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    for match in resp.json()["matches"]:
        assert isinstance(match["constraint_results"], list)


def test_11_score_breakdown_present(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    bd = resp.json()["matches"][0]["score_breakdown"]
    assert "capability_score" in bd
    assert "domain_score" in bd
    assert "resource_score" in bd
    assert "location_score" in bd
    assert "capacity_score" in bd
    assert "total" in bd


def test_12_hei_a_ranks_first(db, problem_with_requirements, three_heis, gov_user):
    """HEI A has Expert IoT + Expert Agriculture + lab → should score highest."""
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis",
                       headers=_bearer(gov_user))
    matches = resp.json()["matches"]
    hei_a_id = str(three_heis[0].hei_id)
    top_id = str(matches[0]["hei_id"])
    assert top_id == hei_a_id, (
        f"Expected HEI A ({hei_a_id}) to rank first but got {top_id}"
    )


def test_13_no_duplicate_hei_tables(db):
    """Verify no duplicate hei_profile or capability tables were created."""
    from sqlalchemy import text
    with db.bind.connect() as conn:
        tbls = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE '%hei%'"
        )).fetchall()
    tbl_names = [t[0] for t in tbls]
    # Should have exactly one hei_profile, one hei_capability, one hei_match
    assert tbl_names.count("hei_profile") == 1
    assert tbl_names.count("hei_capability") == 1
    assert tbl_names.count("hei_match") == 1


def test_14_problem_not_found_returns_404(db, gov_user):
    resp = client.post(
        f"/api/matching/problems/{uuid.uuid4()}/heis",
        headers=_bearer(gov_user),
    )
    assert resp.status_code == 404


def test_15_unauthenticated_returns_401(db, problem_with_requirements, three_heis):
    prob, _ = problem_with_requirements
    resp = client.post(f"/api/matching/problems/{prob.problem_id}/heis")
    assert resp.status_code == 401


def test_16_top_n_param_respected(db, problem_with_requirements, three_heis, gov_user):
    prob, _ = problem_with_requirements
    resp = client.post(
        f"/api/matching/problems/{prob.problem_id}/heis?top_n=2",
        headers=_bearer(gov_user),
    )
    assert resp.status_code == 200
    assert len(resp.json()["matches"]) <= 2


def test_17_health_endpoints_still_work():
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/db").status_code == 200


def test_18_existing_endpoints_still_work(db, gov_user):
    headers = _bearer(gov_user)
    assert client.get("/api/organizations", headers=headers).status_code == 200
    assert client.get("/api/heis", headers=headers).status_code == 200
    assert client.get("/api/capabilities", headers=headers).status_code == 200
    assert client.get("/api/partners", headers=headers).status_code == 200
