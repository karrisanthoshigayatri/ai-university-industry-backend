"""
STEP 13 — External Partner Registry
18 test scenarios against the live Supabase database.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.capability import Capability
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
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


def _make_org(db: Session, org_type: str = "Industry") -> Organization:
    org = Organization(
        name=f"Org {_uid()}",
        organization_type=org_type,
        official_identifier=f"ID-{_uid()}",
    )
    db.add(org)
    db.flush()
    return org


def _make_user(db: Session, org: Organization, role: str = "Industry / MSME / Startup") -> User:
    u = User(
        organization_id=org.organization_id,
        name=f"User {_uid()}",
        email=f"u{_uid()}@example.com",
        password_hash=hash_password("Pass1234!"),
        role=role,
        status="active",
    )
    db.add(u)
    db.flush()
    return u


def _make_capability(db: Session) -> Capability:
    cap = Capability(
        name=f"PartnerCap {_uid()}",
        capability_type="Technology",
        status="Active",
    )
    db.add(cap)
    db.flush()
    return cap


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture()
def industry_org(db):
    org = _make_org(db, "Industry")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def partner_user(db, industry_org):
    u = _make_user(db, industry_org, "Industry / MSME / Startup")
    db.commit()
    yield u
    db.delete(u); db.commit()


@pytest.fixture()
def gov_org(db):
    org = _make_org(db, "Government")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def gov_officer(db, gov_org):
    u = _make_user(db, gov_org, "Government Officer")
    db.commit()
    yield u
    db.delete(u); db.commit()


@pytest.fixture()
def sys_admin_org(db):
    org = _make_org(db, "Government")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def sys_admin(db, sys_admin_org):
    u = _make_user(db, sys_admin_org, "System Administrator")
    db.commit()
    yield u
    db.delete(u); db.commit()


@pytest.fixture()
def other_org(db):
    org = _make_org(db, "MSME")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def other_user(db, other_org):
    u = _make_user(db, other_org, "Industry / MSME / Startup")
    db.commit()
    yield u
    db.delete(u); db.commit()


@pytest.fixture()
def capability(db):
    cap = _make_capability(db)
    db.commit()
    yield cap
    db.delete(cap); db.commit()


@pytest.fixture()
def partner_profile(db, industry_org):
    p = PartnerProfile(
        organization_id=industry_org.organization_id,
        partner_type="Industry",
        description="Test partner",
        verification_status="Pending",
    )
    db.add(p); db.commit()
    yield p
    db.delete(p); db.commit()


@pytest.fixture()
def verified_partner(db, sys_admin_org):
    """A separate org + Verified partner for access-control tests."""
    org = _make_org(db, "Startup")
    db.commit()
    p = PartnerProfile(
        organization_id=org.organization_id,
        partner_type="Startup",
        verification_status="Verified",
    )
    db.add(p); db.commit()
    yield p
    db.delete(p); db.commit()
    db.delete(org); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Create organisation with type Industry and partner profile
# ══════════════════════════════════════════════════════════════════════════════

def test_01_create_partner_profile(db, industry_org, partner_user):
    resp = client.post(
        "/api/partners",
        json={
            "organization_id": str(industry_org.organization_id),
            "partner_type": "Industry",
            "description": "A test industry partner",
        },
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["organization_id"] == str(industry_org.organization_id)
    assert data["partner_type"] == "Industry"
    assert "partner_id" in data
    p = db.get(PartnerProfile, uuid.UUID(data["partner_id"]))
    if p:
        db.delete(p); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Initial verification_status is Pending
# ══════════════════════════════════════════════════════════════════════════════

def test_02_initial_status_pending(db, industry_org, partner_user):
    resp = client.post(
        "/api/partners",
        json={
            "organization_id": str(industry_org.organization_id),
            "partner_type": "Industry",
        },
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["verification_status"] == "Pending"
    p = db.get(PartnerProfile, uuid.UUID(resp.json()["partner_id"]))
    if p:
        db.delete(p); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Get partner profile
# ══════════════════════════════════════════════════════════════════════════════

def test_03_get_partner(db, partner_profile, partner_user):
    # sys_admin can always see; use partner_user but partner is Pending
    # make it verified first so partner_user can see it via list
    # For GET by ID, any authenticated user sees it
    resp = client.get(
        f"/api/partners/{partner_profile.partner_id}",
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["partner_id"] == str(partner_profile.partner_id)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Add capabilities to partner
# ══════════════════════════════════════════════════════════════════════════════

def test_04_add_capability(db, partner_profile, capability, partner_user):
    resp = client.post(
        f"/api/partners/{partner_profile.partner_id}/capabilities",
        json={
            "capability_id": str(capability.capability_id),
            "proficiency_level": 3,
            "experience_description": "5 years in IoT",
            "verification_status": "Pending",
        },
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["capability_id"] == str(capability.capability_id)
    assert data["proficiency_level"] == 3
    pc = db.get(PartnerCapability, uuid.UUID(data["partner_capability_id"]))
    if pc:
        db.delete(pc); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Add multiple support offerings
# ══════════════════════════════════════════════════════════════════════════════

def test_05_add_multiple_offerings(db, partner_profile, partner_user):
    today = date.today()
    ids = []
    for support_type in ["Funding", "Mentorship"]:
        resp = client.post(
            f"/api/partners/{partner_profile.partner_id}/offerings",
            json={
                "support_type": support_type,
                "title": f"{support_type} offering",
                "capacity": 10,
                "availability_start": str(today),
                "availability_end": str(today + timedelta(days=90)),
            },
            headers=_bearer(partner_user),
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["offering_id"])

    assert len(ids) == 2
    for oid in ids:
        o = db.get(PartnerSupportOffering, uuid.UUID(oid))
        if o:
            db.delete(o); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Retrieve partner profile
# ══════════════════════════════════════════════════════════════════════════════

def test_06_retrieve_partner(db, partner_profile, sys_admin):
    resp = client.get(f"/api/partners/{partner_profile.partner_id}", headers=_bearer(sys_admin))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["partner_id"] == str(partner_profile.partner_id)
    assert data["partner_type"] == "Industry"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Retrieve partner capabilities
# ══════════════════════════════════════════════════════════════════════════════

def test_07_retrieve_capabilities(db, partner_profile, capability, partner_user):
    pc = PartnerCapability(
        partner_id=partner_profile.partner_id,
        capability_id=capability.capability_id,
        verification_status="Pending",
    )
    db.add(pc); db.commit()

    resp = client.get(
        f"/api/partners/{partner_profile.partner_id}/capabilities",
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    ids = [c["partner_capability_id"] for c in resp.json()]
    assert str(pc.partner_capability_id) in ids

    db.delete(pc); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — Retrieve partner offerings
# ══════════════════════════════════════════════════════════════════════════════

def test_08_retrieve_offerings(db, partner_profile, partner_user):
    o = PartnerSupportOffering(
        partner_id=partner_profile.partner_id,
        support_type="Technology",
        status="Active",
    )
    db.add(o); db.commit()

    resp = client.get(
        f"/api/partners/{partner_profile.partner_id}/offerings",
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    ids = [x["offering_id"] for x in resp.json()]
    assert str(o.offering_id) in ids

    db.delete(o); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 — Update partner information
# ══════════════════════════════════════════════════════════════════════════════

def test_09_update_partner(db, partner_profile, partner_user):
    resp = client.put(
        f"/api/partners/{partner_profile.partner_id}",
        json={"description": "Updated description", "website": "https://updated.example.com"},
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["description"] == "Updated description"
    assert data["website"] == "https://updated.example.com"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10 — Update a capability
# ══════════════════════════════════════════════════════════════════════════════

def test_10_update_capability(db, partner_profile, capability, partner_user):
    pc = PartnerCapability(
        partner_id=partner_profile.partner_id,
        capability_id=capability.capability_id,
        proficiency_level=2,
        verification_status="Pending",
    )
    db.add(pc); db.commit()

    resp = client.put(
        f"/api/partners/{partner_profile.partner_id}/capabilities/{pc.partner_capability_id}",
        json={"proficiency_level": 4, "experience_description": "10 years"},
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["proficiency_level"] == 4
    assert data["experience_description"] == "10 years"

    db.delete(pc); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11 — Update an offering
# ══════════════════════════════════════════════════════════════════════════════

def test_11_update_offering(db, partner_profile, partner_user):
    o = PartnerSupportOffering(
        partner_id=partner_profile.partner_id,
        support_type="Funding",
        status="Active",
    )
    db.add(o); db.commit()

    resp = client.put(
        f"/api/partners/{partner_profile.partner_id}/offerings/{o.offering_id}",
        json={"title": "Seed Grant", "status": "Inactive"},
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Seed Grant"
    assert data["status"] == "Inactive"

    db.delete(o); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12 — Unauthorized access blocked
# ══════════════════════════════════════════════════════════════════════════════

def test_12_unauthorized_access(db, partner_profile, other_user):
    """A user from a different org cannot update another org's partner profile."""
    resp = client.put(
        f"/api/partners/{partner_profile.partner_id}",
        json={"description": "Hacked"},
        headers=_bearer(other_user),
    )
    assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 13 — Invalid capability_id rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_13_invalid_capability_id(db, partner_profile, partner_user):
    resp = client.post(
        f"/api/partners/{partner_profile.partner_id}/capabilities",
        json={
            "capability_id": str(uuid.uuid4()),  # does not exist
            "verification_status": "Pending",
        },
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 404, resp.text
    assert "Capability" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# TEST 14 — Invalid partner_id returns 404
# ══════════════════════════════════════════════════════════════════════════════

def test_14_invalid_partner_id(db, partner_user):
    resp = client.get(
        f"/api/partners/{uuid.uuid4()}",
        headers=_bearer(partner_user),
    )
    assert resp.status_code == 404, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 15 — Duplicate partner-capability mapping rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_15_duplicate_capability_rejected(db, partner_profile, capability, partner_user):
    payload = {
        "capability_id": str(capability.capability_id),
        "verification_status": "Pending",
    }
    r1 = client.post(
        f"/api/partners/{partner_profile.partner_id}/capabilities",
        json=payload,
        headers=_bearer(partner_user),
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        f"/api/partners/{partner_profile.partner_id}/capabilities",
        json=payload,
        headers=_bearer(partner_user),
    )
    assert r2.status_code == 409, r2.text

    pc = db.get(PartnerCapability, uuid.UUID(r1.json()["partner_capability_id"]))
    if pc:
        db.delete(pc); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 16 — Government Officer can verify partner
# ══════════════════════════════════════════════════════════════════════════════

def test_16_gov_officer_verifies_partner(db, partner_profile, gov_officer):
    resp = client.put(
        f"/api/partners/{partner_profile.partner_id}/verification",
        json={"verification_status": "Verified"},
        headers=_bearer(gov_officer),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "Verified"
    # reset
    partner_profile.verification_status = "Pending"
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 17 — Normal users only see Verified partners in list
# ══════════════════════════════════════════════════════════════════════════════

def test_17_normal_user_sees_only_verified(db, partner_profile, verified_partner, partner_user):
    """
    partner_profile is Pending → not visible to partner_user via /api/partners list.
    verified_partner is Verified → visible.
    """
    resp = client.get("/api/partners", headers=_bearer(partner_user))
    assert resp.status_code == 200, resp.text
    ids = [p["partner_id"] for p in resp.json()]
    # Pending partner should NOT appear for normal user
    assert str(partner_profile.partner_id) not in ids
    # Verified partner SHOULD appear
    assert str(verified_partner.partner_id) in ids


# ══════════════════════════════════════════════════════════════════════════════
# TEST 18 — Existing health endpoints still work
# ══════════════════════════════════════════════════════════════════════════════

def test_18_existing_endpoints_still_work(db, sys_admin):
    headers = _bearer(sys_admin)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/db").status_code == 200
    assert client.get("/api/organizations", headers=headers).status_code == 200
    assert client.get("/api/capabilities", headers=headers).status_code == 200
    assert client.get("/api/heis", headers=headers).status_code == 200
    assert client.get("/api/partners", headers=headers).status_code == 200
