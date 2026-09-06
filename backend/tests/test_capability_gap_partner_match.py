"""
STEPS 19–20 — Capability Gap Analysis + Partner Matching
12 test scenarios against the live Supabase database.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.capability_gap import CapabilityGap, PartnerMatch
from app.models.hei import HeiProfile
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
from app.models.problem import Problem
from app.models.project import Project, ProjectCapability
from app.models.user import User

client = TestClient(app, raise_server_exceptions=True)


def _uid(): return uuid.uuid4().hex[:8]
def _bearer(u): return {"Authorization": f"Bearer {create_access_token(str(u.user_id), u.role)}"}


class _S:
    pass

_s = _S()


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    db = SessionLocal()

    # Users / Orgs
    gov_org = Organization(name=f"G {_uid()}", organization_type="Government", official_identifier=f"G-{_uid()}")
    db.add(gov_org); db.flush()
    gov = User(organization_id=gov_org.organization_id, name="Gov", email=f"g{_uid()}@x.com",
               password_hash=hash_password("P1"), role="Government Officer", status="active")
    citizen = User(organization_id=gov_org.organization_id, name="Cit", email=f"c{_uid()}@x.com",
                   password_hash=hash_password("P1"), role="Citizen", status="active")
    db.add(gov); db.add(citizen); db.flush()
    _s.gov = gov; _s.citizen = citizen
    _s._gov_id = str(gov.user_id)

    # HEI
    hei_org = Organization(name=f"H {_uid()}", organization_type="HEI", official_identifier=f"H-{_uid()}", state="Karnataka")
    db.add(hei_org); db.flush()
    hei = HeiProfile(organization_id=hei_org.organization_id, institution_type="University", verification_status="Verified")
    db.add(hei); db.flush()
    _s.hei = hei; _s._hei_id = str(hei.hei_id)

    # Capabilities
    caps = []
    for name, ctype in [("IoT GS", "Technology"), ("Agriculture GS", "Domain"), ("Water GS", "Resource")]:
        c = Capability(name=f"{name} {_uid()}", capability_type=ctype, status="Active")
        db.add(c); caps.append(c)
    db.flush()
    _s.caps = caps
    _s._cap_ids = [str(c.capability_id) for c in caps]

    # Problem + requirements (for proj)
    prob = Problem(title=f"Gap Test {_uid()}", description="Test",
                   submitter_id=gov.user_id, source_type="Government", current_status="Validated")
    db.add(prob); db.flush()
    prof = ProblemRequirementProfile(problem_id=prob.problem_id, confidence=0.9, model_version="test")
    db.add(prof); db.flush()
    reqs = [
        (caps[0].capability_id, "Technology", 3.0, 1.0),
        (caps[1].capability_id, "Domain",     1.0, 0.6),
        (caps[2].capability_id, "Resource",   2.0, 0.8),
    ]
    req_objs = []
    for cap_id, rtype, level, crit in reqs:
        r = ProblemRequirementCapability(requirement_profile_id=prof.requirement_profile_id,
                                          capability_id=cap_id, requirement_type=rtype,
                                          required_level=level, criticality=crit, confidence=0.85)
        db.add(r); req_objs.append(r)
    db.flush()

    # Separate problem for proj2
    prob2 = Problem(title=f"Partial Gap {_uid()}", description="Test2",
                    submitter_id=gov.user_id, source_type="Government", current_status="Validated")
    db.add(prob2); db.flush()
    prof2 = ProblemRequirementProfile(problem_id=prob2.problem_id, confidence=0.9, model_version="test")
    db.add(prof2); db.flush()
    for cap_id, rtype, level, crit in reqs:
        db.add(ProblemRequirementCapability(requirement_profile_id=prof2.requirement_profile_id,
                                             capability_id=cap_id, requirement_type=rtype,
                                             required_level=level, criticality=crit, confidence=0.85))
    db.flush()

    # Project (no capabilities → all gaps)
    proj = Project(problem_id=prob.problem_id, hei_id=hei.hei_id,
                   title="Gap Project", status="Active", current_stage="Development")
    db.add(proj); db.flush()
    _s.proj = proj; _s._proj_id = str(proj.project_id)
    _s.prob = prob; _s.prof = prof

    # Project with one capability filled (IoT at level 3)
    proj2 = Project(problem_id=prob2.problem_id, hei_id=hei.hei_id,
                    title="Partial Gap Project", status="Active", current_stage="Development")
    db.add(proj2); db.flush()
    pc = ProjectCapability(project_id=proj2.project_id, capability_id=caps[0].capability_id,
                           source_type="HEI", strength_level=3.0)
    db.add(pc); db.flush()
    _s.proj2 = proj2; _s._proj2_id = str(proj2.project_id)
    _s.prob2 = prob2; _s.prof2 = prof2

    # Partner
    partner_org = Organization(name=f"P {_uid()}", organization_type="Industry",
                               official_identifier=f"P-{_uid()}", state="Karnataka")
    db.add(partner_org); db.flush()
    partner = PartnerProfile(organization_id=partner_org.organization_id,
                              partner_type="Industry", verification_status="Verified")
    db.add(partner); db.flush()
    # Partner has IoT (level 4) + Agriculture (level 2)
    pcap1 = PartnerCapability(partner_id=partner.partner_id, capability_id=caps[0].capability_id,
                               proficiency_level=4, verification_status="Verified")
    pcap2 = PartnerCapability(partner_id=partner.partner_id, capability_id=caps[1].capability_id,
                               proficiency_level=2, verification_status="Verified")
    db.add(pcap1); db.add(pcap2)
    offering = PartnerSupportOffering(partner_id=partner.partner_id, support_type="Technology",
                                       title="IoT Platform", status="Active")
    db.add(offering); db.flush()
    _s.partner = partner; _s._partner_id = str(partner.partner_id)

    db.commit()
    yield

    # Cleanup
    for m in [PartnerMatch, CapabilityGap, ProjectCapability, Project, PartnerSupportOffering,
              PartnerCapability, PartnerProfile]:
        try:
            db.execute(delete(m)); db.commit()
        except Exception:
            db.rollback()
    for obj in [prof2, prof, prob2, prob, hei, hei_org, partner_org] + caps + [citizen, gov, gov_org]:
        try:
            db.delete(obj); db.commit()
        except Exception:
            db.rollback()
    db.close()


# ── GAP TESTS ──────────────────────────────────────────────────────────────────

def test_01_gap_analysis_runs():
    resp = client.post(f"/api/projects/{_s._proj_id}/capability-gaps/analyze",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["total_requirements"] == 3
    assert d["gaps_found"] == 3   # no caps available → all gaps


def test_02_no_gap_when_capability_filled():
    resp = client.post(f"/api/projects/{_s._proj2_id}/capability-gaps/analyze",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    d = resp.json()
    # IoT is filled; Agriculture + Water are gaps
    assert d["no_gap_count"] >= 1
    assert d["gaps_found"] <= 2


def test_03_missing_capability_shown_in_gaps():
    resp = client.post(f"/api/projects/{_s._proj_id}/capability-gaps/analyze",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    gap_cap_ids = [g["capability_id"] for g in resp.json()["gaps"]]
    # Water (caps[2]) should appear — not available in project
    assert _s._cap_ids[2] in gap_cap_ids


def test_04_critical_gap_has_high_criticality():
    resp = client.post(f"/api/projects/{_s._proj_id}/capability-gaps/analyze",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    gaps = resp.json()["gaps"]
    iot_gap = next((g for g in gaps if g["capability_id"] == _s._cap_ids[0]), None)
    assert iot_gap is not None
    assert iot_gap["criticality"] >= 0.8   # criticality=1.0 from requirement


def test_05_list_gaps():
    resp = client.get(f"/api/projects/{_s._proj_id}/capability-gaps",
                      headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) >= 1


def test_06_get_single_gap():
    db = SessionLocal()
    try:
        gap = db.scalar(select(CapabilityGap).where(CapabilityGap.project_id == _s.proj.project_id))
        assert gap is not None
        resp = client.get(f"/api/projects/{_s._proj_id}/capability-gaps/{gap.gap_id}",
                          headers=_bearer(_s.gov))
        assert resp.status_code == 200, resp.text
        assert resp.json()["gap_id"] == str(gap.gap_id)
    finally:
        db.close()


# ── PARTNER MATCH TESTS ────────────────────────────────────────────────────────

def test_07_partner_matching_runs():
    resp = client.post(f"/api/matching/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["total_matches"] >= 1
    assert d["model_version"] == "partner-matching-v1"


def test_08_partner_capability_matched():
    resp = client.post(f"/api/matching/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    top = resp.json()["matches"][0]
    # Partner has IoT + Agriculture → should show matched capabilities
    assert len(top["matched_capabilities"]) >= 1


def test_09_support_offerings_in_result():
    resp = client.post(f"/api/matching/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    top = resp.json()["matches"][0]
    assert isinstance(top["support_matches"], list)
    assert len(top["support_matches"]) >= 1


def test_10_ranking_and_scores():
    resp = client.post(f"/api/matching/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.gov))
    assert resp.status_code == 200, resp.text
    matches = resp.json()["matches"]
    ranks = [m["rank"] for m in matches]
    assert ranks == sorted(ranks)
    for m in matches:
        assert 0 <= m["match_score"] <= 100


def test_11_snapshots_persisted():
    client.post(f"/api/matching/projects/{_s._proj_id}/partners", headers=_bearer(_s.gov))
    db = SessionLocal()
    try:
        records = list(db.scalars(
            select(PartnerMatch).where(PartnerMatch.project_id == _s.proj.project_id)
        ).all())
        assert len(records) >= 1
        assert all(r.model_version == "partner-matching-v1" for r in records)
    finally:
        db.close()


def test_12_unauthorized_returns_403():
    resp = client.post(f"/api/matching/projects/{_s._proj_id}/partners",
                       headers=_bearer(_s.citizen))
    assert resp.status_code == 403, resp.text
