"""
STEP 12 — Capability Evidence + Availability + Constraint
20 test scenarios against the live Supabase database.
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
from app.models.evidence import Availability, CapabilityEvidence, EntityConstraint
from app.models.hei import FacultyExpertProfile, HeiCapability, HeiProfile, InstitutionalResource
from app.models.organization import Organization
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


def _make_org(db: Session, org_type: str = "HEI") -> Organization:
    org = Organization(
        name=f"Org {_uid()}",
        organization_type=org_type,
        official_identifier=f"ID-{_uid()}",
    )
    db.add(org)
    db.flush()
    return org


def _make_user(db: Session, org: Organization, role: str = "HEI Administrator") -> User:
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
        name=f"Cap {_uid()}",
        capability_type="Domain",
        status="Active",
    )
    db.add(cap)
    db.flush()
    return cap


def _make_hei(db: Session, org: Organization) -> HeiProfile:
    hei = HeiProfile(
        organization_id=org.organization_id,
        institution_type="University",
        verification_status="Pending",
    )
    db.add(hei)
    db.flush()
    return hei


def _make_hei_capability(db: Session, hei: HeiProfile, cap: Capability) -> HeiCapability:
    hc = HeiCapability(
        hei_id=hei.hei_id,
        capability_id=cap.capability_id,
        status="Active",
    )
    db.add(hc)
    db.flush()
    return hc


def _make_faculty(db: Session, hei: HeiProfile) -> FacultyExpertProfile:
    fp = FacultyExpertProfile(
        hei_id=hei.hei_id,
        designation="Lecturer",
        department="CS",
        verification_status="Pending",
    )
    db.add(fp)
    db.flush()
    return fp


def _make_resource(db: Session, hei: HeiProfile) -> InstitutionalResource:
    r = InstitutionalResource(
        hei_id=hei.hei_id,
        name=f"Lab {_uid()}",
        resource_type="Laboratory",
        availability_status="Available",
        verification_status="Pending",
    )
    db.add(r)
    db.flush()
    return r


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
def hei_org(db):
    org = _make_org(db, "HEI")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def gov_org(db):
    org = _make_org(db, "Government")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def hei_admin(db, hei_org):
    u = _make_user(db, hei_org, "HEI Administrator")
    db.commit()
    yield u
    db.delete(u); db.commit()


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
def other_hei_org(db):
    org = _make_org(db, "HEI")
    db.commit()
    yield org
    db.delete(org); db.commit()


@pytest.fixture()
def other_hei_admin(db, other_hei_org):
    u = _make_user(db, other_hei_org, "HEI Administrator")
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
def hei_profile(db, hei_org):
    hei = _make_hei(db, hei_org)
    db.commit()
    yield hei
    db.delete(hei); db.commit()


@pytest.fixture()
def hei_cap(db, hei_profile, capability):
    hc = _make_hei_capability(db, hei_profile, capability)
    db.commit()
    yield hc
    db.delete(hc); db.commit()


@pytest.fixture()
def faculty(db, hei_profile):
    fp = _make_faculty(db, hei_profile)
    db.commit()
    yield fp
    db.delete(fp); db.commit()


@pytest.fixture()
def resource(db, hei_profile):
    r = _make_resource(db, hei_profile)
    db.commit()
    yield r
    db.delete(r); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Create capability evidence
# ══════════════════════════════════════════════════════════════════════════════

def test_01_create_evidence(db, hei_cap, capability, hei_admin):
    resp = client.post(
        "/api/capability-evidence",
        json={
            "entity_type": "hei_capability",
            "entity_id": str(hei_cap.hei_capability_id),
            "capability_id": str(capability.capability_id),
            "evidence_type": "Certification",
            "source": "NAAC",
            "description": "Accredited laboratory",
            "recency": "2025-01-01",
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["entity_type"] == "hei_capability"
    assert data["evidence_type"] == "Certification"
    assert data["verification_status"] == "Pending"
    assert "evidence_id" in data
    ev = db.get(CapabilityEvidence, uuid.UUID(data["evidence_id"]))
    if ev:
        db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Retrieve evidence
# ══════════════════════════════════════════════════════════════════════════════

def test_02_retrieve_evidence(db, hei_cap, hei_admin):
    ev = CapabilityEvidence(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        evidence_type="Project",
        verification_status="Pending",
    )
    db.add(ev); db.commit()

    resp = client.get(
        f"/api/capability-evidence/hei_capability/{hei_cap.hei_capability_id}",
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    ids = [e["evidence_id"] for e in resp.json()]
    assert str(ev.evidence_id) in ids

    db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Update evidence
# ══════════════════════════════════════════════════════════════════════════════

def test_03_update_evidence(db, hei_cap, hei_admin):
    ev = CapabilityEvidence(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        evidence_type="Publication",
        verification_status="Pending",
    )
    db.add(ev); db.commit()

    resp = client.put(
        f"/api/capability-evidence/{ev.evidence_id}",
        json={"source": "IEEE", "recency": "2026-06-01"},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "IEEE"
    assert data["recency"] == "2026-06-01"

    db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Invalid capability_id rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_04_invalid_capability_rejected(db, hei_cap, hei_admin):
    resp = client.post(
        "/api/capability-evidence",
        json={
            "entity_type": "hei_capability",
            "entity_id": str(hei_cap.hei_capability_id),
            "capability_id": str(uuid.uuid4()),   # non-existent
            "evidence_type": "Patent",
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 404, resp.text
    assert "Capability" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Evidence verification (Government Officer)
# ══════════════════════════════════════════════════════════════════════════════

def test_05_evidence_verification(db, hei_cap, gov_officer):
    ev = CapabilityEvidence(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        evidence_type="Certification",
        verification_status="Pending",
    )
    db.add(ev); db.commit()

    resp = client.put(
        f"/api/capability-evidence/{ev.evidence_id}/verify",
        json={"verification_status": "Verified"},
        headers=_bearer(gov_officer),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["verification_status"] == "Verified"

    db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — verified_by is set server-side (not from client)
# ══════════════════════════════════════════════════════════════════════════════

def test_06_server_side_verified_by(db, hei_cap, gov_officer):
    ev = CapabilityEvidence(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        evidence_type="Project",
        verification_status="Pending",
    )
    db.add(ev); db.commit()

    resp = client.put(
        f"/api/capability-evidence/{ev.evidence_id}/verify",
        json={"verification_status": "Verified"},
        headers=_bearer(gov_officer),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # verified_by must equal the Gov Officer's user_id (server-injected)
    assert data["verified_by"] == str(gov_officer.user_id)

    db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — verified_at is set server-side
# ══════════════════════════════════════════════════════════════════════════════

def test_07_server_side_verified_at(db, hei_cap, gov_officer):
    ev = CapabilityEvidence(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        evidence_type="Official Document",
        verification_status="Pending",
    )
    db.add(ev); db.commit()

    resp = client.put(
        f"/api/capability-evidence/{ev.evidence_id}/verify",
        json={"verification_status": "Verified"},
        headers=_bearer(gov_officer),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # verified_at must be a non-null timestamp set by the server
    assert data["verified_at"] is not None

    db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — Create availability
# ══════════════════════════════════════════════════════════════════════════════

def test_08_create_availability(db, resource, hei_admin):
    today = date.today()
    resp = client.post(
        "/api/availability",
        json={
            "entity_type": "institutional_resource",
            "entity_id": str(resource.resource_id),
            "status": "Available",
            "capacity": 2,
            "start_date": str(today),
            "end_date": str(today + timedelta(days=180)),
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "Available"
    assert data["capacity"] == 2
    av = db.get(Availability, uuid.UUID(data["availability_id"]))
    if av:
        db.delete(av); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 — Retrieve availability
# ══════════════════════════════════════════════════════════════════════════════

def test_09_retrieve_availability(db, resource, hei_admin):
    av = Availability(
        entity_type="institutional_resource",
        entity_id=resource.resource_id,
        status="Available",
        capacity=5,
    )
    db.add(av); db.commit()

    resp = client.get(
        f"/api/availability/institutional_resource/{resource.resource_id}",
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    ids = [a["availability_id"] for a in resp.json()]
    assert str(av.availability_id) in ids

    db.delete(av); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10 — Update availability
# ══════════════════════════════════════════════════════════════════════════════

def test_10_update_availability(db, resource, hei_admin):
    av = Availability(
        entity_type="institutional_resource",
        entity_id=resource.resource_id,
        status="Available",
    )
    db.add(av); db.commit()

    resp = client.put(
        f"/api/availability/{av.availability_id}",
        json={"status": "Partially Available", "capacity": 1},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "Partially Available"
    assert data["capacity"] == 1

    db.delete(av); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11 — Invalid date range rejected (end_date before start_date)
# ══════════════════════════════════════════════════════════════════════════════

def test_11_invalid_date_range_rejected(db, resource, hei_admin):
    today = date.today()
    resp = client.post(
        "/api/availability",
        json={
            "entity_type": "institutional_resource",
            "entity_id": str(resource.resource_id),
            "status": "Available",
            "start_date": str(today + timedelta(days=10)),
            "end_date": str(today),   # before start — invalid
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 422, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12 — Negative capacity rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_12_negative_capacity_rejected(db, resource, hei_admin):
    resp = client.post(
        "/api/availability",
        json={
            "entity_type": "institutional_resource",
            "entity_id": str(resource.resource_id),
            "status": "Available",
            "capacity": -5,   # invalid
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 422, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 13 — Create constraint
# ══════════════════════════════════════════════════════════════════════════════

def test_13_create_constraint(db, hei_cap, hei_admin):
    """Create a constraint on an hei_capability entity."""
    resp = client.post(
        "/api/constraints",
        json={
            "entity_type": "hei_capability",
            "entity_id": str(hei_cap.hei_capability_id),
            "constraint_type": "Geographic",
            "value": "Field visit required",
            "severity": "Medium",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["constraint_type"] == "Geographic"
    assert data["severity"] == "Medium"
    assert data["value"] == "Field visit required"
    c = db.get(EntityConstraint, uuid.UUID(data["constraint_id"]))
    if c:
        db.delete(c); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 14 — Retrieve constraint
# ══════════════════════════════════════════════════════════════════════════════

def test_14_retrieve_constraint(db, resource, hei_admin):
    c = EntityConstraint(
        entity_type="institutional_resource",
        entity_id=resource.resource_id,
        constraint_type="Capacity",
        value="Maximum 2 simultaneous projects",
        severity="High",
    )
    db.add(c); db.commit()

    resp = client.get(
        f"/api/constraints/institutional_resource/{resource.resource_id}",
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    ids = [x["constraint_id"] for x in resp.json()]
    assert str(c.constraint_id) in ids

    db.delete(c); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 15 — Update constraint
# ══════════════════════════════════════════════════════════════════════════════

def test_15_update_constraint(db, hei_cap, hei_admin):
    c = EntityConstraint(
        entity_type="hei_capability",
        entity_id=hei_cap.hei_capability_id,
        constraint_type="Geographic",
        value="Field visit required",
        severity="Low",
    )
    db.add(c); db.commit()

    resp = client.put(
        f"/api/constraints/{c.constraint_id}",
        json={"severity": "High", "value": "Remote only"},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["severity"] == "High"
    assert data["value"] == "Remote only"

    db.delete(c); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 16 — Invalid entity_type rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_16_invalid_entity_type_rejected(db, hei_admin):
    resp = client.post(
        "/api/capability-evidence",
        json={
            "entity_type": "invalid_entity",   # not in allowed set
            "entity_id": str(uuid.uuid4()),
            "evidence_type": "Project",
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 422, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 17 — Cross-organization modification blocked
# ══════════════════════════════════════════════════════════════════════════════

def test_17_cross_org_modification_blocked(db, hei_cap, other_hei_admin):
    """An HEI Admin from a different org cannot create evidence for another HEI's entity."""
    resp = client.post(
        "/api/capability-evidence",
        json={
            "entity_type": "hei_capability",
            "entity_id": str(hei_cap.hei_capability_id),
            "evidence_type": "Project",
            "verification_status": "Pending",
        },
        headers=_bearer(other_hei_admin),
    )
    assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 18 — Authorization rules
# ══════════════════════════════════════════════════════════════════════════════

def test_18_authorization_rules(db, hei_cap, hei_admin, gov_officer, sys_admin):
    """
    - HEI Admin can create evidence for their own entity ✓
    - Government Officer can verify ✓
    - System Admin can do both ✓
    - Unauthenticated request rejected ✓
    """
    ev_payload = {
        "entity_type": "hei_capability",
        "entity_id": str(hei_cap.hei_capability_id),
        "evidence_type": "Website",
        "verification_status": "Pending",
    }

    # HEI Admin can create
    r1 = client.post("/api/capability-evidence", json=ev_payload, headers=_bearer(hei_admin))
    assert r1.status_code == 201, r1.text
    ev_id = r1.json()["evidence_id"]

    # Gov Officer can verify
    r2 = client.put(
        f"/api/capability-evidence/{ev_id}/verify",
        json={"verification_status": "Verified"},
        headers=_bearer(gov_officer),
    )
    assert r2.status_code == 200, r2.text

    # System Admin can update
    r3 = client.put(
        f"/api/capability-evidence/{ev_id}",
        json={"source": "admin-edit"},
        headers=_bearer(sys_admin),
    )
    assert r3.status_code == 200, r3.text

    # Unauthenticated → 401
    r4 = client.get(
        f"/api/capability-evidence/hei_capability/{hei_cap.hei_capability_id}"
    )
    assert r4.status_code == 401, r4.text

    ev = db.get(CapabilityEvidence, uuid.UUID(ev_id))
    if ev:
        db.delete(ev); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 19 — Alembic migration (tables + columns exist)
# ══════════════════════════════════════════════════════════════════════════════

def test_19_alembic_migration(db):
    expected = {
        "capability_evidence": [
            "evidence_id", "entity_type", "entity_id", "capability_id",
            "evidence_type", "source", "reference", "description", "recency",
            "verified_by", "verified_at", "verification_status",
            "created_at", "updated_at",
        ],
        "availability": [
            "availability_id", "entity_type", "entity_id", "status",
            "capacity", "start_date", "end_date", "conditions",
            "created_at", "updated_at",
        ],
        "entity_constraint": [
            "constraint_id", "entity_type", "entity_id", "constraint_type",
            "value", "severity", "validity_period", "created_at", "updated_at",
        ],
    }
    for table, cols in expected.items():
        rows = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :tbl"
            ),
            {"tbl": table},
        ).fetchall()
        actual = {r[0] for r in rows}
        assert actual, f"Table '{table}' not found in database"
        for col in cols:
            assert col in actual, (
                f"Column '{col}' missing from table '{table}'. Found: {sorted(actual)}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 20 — Existing endpoints still work
# ══════════════════════════════════════════════════════════════════════════════

def test_20_existing_endpoints_still_work(db):
    """Smoke-test all previously implemented endpoint groups."""
    # create a temporary user for auth
    org = _make_org(db, "Government")
    db.commit()
    u = _make_user(db, org, "System Administrator")
    db.commit()
    headers = _bearer(u)

    try:
        # health
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health/db").status_code == 200

        # organizations
        assert client.get("/api/organizations", headers=headers).status_code == 200

        # capabilities
        assert client.get("/api/capabilities", headers=headers).status_code == 200

        # HEI endpoints
        assert client.get("/api/heis", headers=headers).status_code == 200

        # new Step-12 endpoints reachable
        assert client.get(
            f"/api/capability-evidence/hei_capability/{uuid.uuid4()}",
            headers=headers,
        ).status_code in (200, 400)   # 400 if invalid entity_type resolution

        assert client.get(
            f"/api/availability/institutional_resource/{uuid.uuid4()}",
            headers=headers,
        ).status_code == 200

        assert client.get(
            f"/api/constraints/faculty_expertise/{uuid.uuid4()}",
            headers=headers,
        ).status_code == 200

    finally:
        db.delete(u); db.commit()
        db.delete(org); db.commit()
