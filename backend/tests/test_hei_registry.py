"""
STEP 11 — HEI / University Capability Registry
Tests covering all 20 required scenarios.

Uses FastAPI TestClient against the real Supabase database so migrations,
FKs, and constraints are exercised.  Each test creates its own isolated
data (unique names / e-mails) and cleans up in the same transaction block or
via explicit teardown so tests can be run repeatedly without residual state.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

# ── App imports ────────────────────────────────────────────────────────────────
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.capability import Capability
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.organization import Organization
from app.models.user import User


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

client = TestClient(app, raise_server_exceptions=True)


def _uid() -> str:
    """Short unique suffix to avoid name collisions across runs."""
    return uuid.uuid4().hex[:8]


def _bearer(user: User) -> dict[str, str]:
    token = create_access_token(str(user.user_id), user.role)
    return {"Authorization": f"Bearer {token}"}


def _make_org(db: Session, org_type: str = "HEI") -> Organization:
    suffix = _uid()
    org = Organization(
        name=f"Test Org {suffix}",
        organization_type=org_type,
        official_identifier=f"ORG-{suffix}",
    )
    db.add(org)
    db.flush()
    return org


def _make_user(db: Session, org: Organization, role: str = "HEI Administrator") -> User:
    suffix = _uid()
    u = User(
        organization_id=org.organization_id,
        name=f"User {suffix}",
        email=f"user-{suffix}@test.invalid",
        password_hash=hash_password("Test1234!"),
        role=role,
        status="active",
    )
    db.add(u)
    db.flush()
    return u


def _make_capability(db: Session) -> Capability:
    suffix = _uid()
    cap = Capability(
        name=f"Water Management {suffix}",
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
        established_year=1980,
        website="https://test.edu",
        verification_status="Pending",
    )
    db.add(hei)
    db.flush()
    return hei


def _make_faculty(db: Session, hei: HeiProfile, user: User | None = None) -> FacultyExpertProfile:
    fp = FacultyExpertProfile(
        hei_id=hei.hei_id,
        user_id=user.user_id if user else None,
        designation="Assistant Professor",
        department="Civil Engineering",
        specialization="Water Quality",
        experience_years=5,
        verification_status="Pending",
    )
    db.add(fp)
    db.flush()
    return fp


def _make_resource(db: Session, hei: HeiProfile) -> InstitutionalResource:
    r = InstitutionalResource(
        hei_id=hei.hei_id,
        name=f"Water Quality Lab {_uid()}",
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
    """Provide a real database session; rollback after each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def hei_org(db):
    org = _make_org(db, "HEI")
    db.commit()
    yield org
    # cleanup
    db.delete(org)
    db.commit()


@pytest.fixture()
def non_hei_org(db):
    org = _make_org(db, "Government")
    db.commit()
    yield org
    db.delete(org)
    db.commit()


@pytest.fixture()
def hei_admin(db, hei_org):
    u = _make_user(db, hei_org, "HEI Administrator")
    db.commit()
    yield u
    db.delete(u)
    db.commit()


@pytest.fixture()
def sys_admin_org(db):
    org = _make_org(db, "Government")
    db.commit()
    yield org
    db.delete(org)
    db.commit()


@pytest.fixture()
def sys_admin(db, sys_admin_org):
    u = _make_user(db, sys_admin_org, "System Administrator")
    db.commit()
    yield u
    db.delete(u)
    db.commit()


@pytest.fixture()
def other_hei_org(db):
    org = _make_org(db, "HEI")
    db.commit()
    yield org
    db.delete(org)
    db.commit()


@pytest.fixture()
def other_hei_admin(db, other_hei_org):
    u = _make_user(db, other_hei_org, "HEI Administrator")
    db.commit()
    yield u
    db.delete(u)
    db.commit()


@pytest.fixture()
def capability(db):
    cap = _make_capability(db)
    db.commit()
    yield cap
    db.delete(cap)
    db.commit()


@pytest.fixture()
def hei_profile(db, hei_org):
    hei = _make_hei(db, hei_org)
    db.commit()
    yield hei
    db.delete(hei)
    db.commit()


@pytest.fixture()
def faculty_profile(db, hei_profile, hei_admin):
    fp = _make_faculty(db, hei_profile, hei_admin)
    db.commit()
    yield fp
    db.delete(fp)
    db.commit()


@pytest.fixture()
def resource(db, hei_profile):
    r = _make_resource(db, hei_profile)
    db.commit()
    yield r
    db.delete(r)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Create HEI profile
# ══════════════════════════════════════════════════════════════════════════════

def test_01_create_hei_profile(db, hei_org, hei_admin):
    """POST /api/heis — creates a profile for an HEI org."""
    resp = client.post(
        "/api/heis",
        json={
            "organization_id": str(hei_org.organization_id),
            "institution_type": "University",
            "established_year": 1985,
            "website": "https://uni.edu",
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["organization_id"] == str(hei_org.organization_id)
    assert data["institution_type"] == "University"
    assert "hei_id" in data
    # cleanup
    hei_id = data["hei_id"]
    hei = db.get(HeiProfile, uuid.UUID(hei_id))
    if hei:
        db.delete(hei)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Reject non-HEI organization
# ══════════════════════════════════════════════════════════════════════════════

def test_02_reject_non_hei_organization(db, non_hei_org, sys_admin):
    """POST /api/heis — 400 when organization_type is not HEI."""
    resp = client.post(
        "/api/heis",
        json={
            "organization_id": str(non_hei_org.organization_id),
            "institution_type": "Government Agency",
            "verification_status": "Pending",
        },
        headers=_bearer(sys_admin),
    )
    assert resp.status_code == 400, resp.text
    assert "HEI" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Get HEI
# ══════════════════════════════════════════════════════════════════════════════

def test_03_get_hei(db, hei_profile, hei_admin):
    """GET /api/heis/{hei_id} — returns the HEI profile."""
    resp = client.get(
        f"/api/heis/{hei_profile.hei_id}",
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["hei_id"] == str(hei_profile.hei_id)
    assert data["institution_type"] == "University"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Update HEI
# ══════════════════════════════════════════════════════════════════════════════

def test_04_update_hei(db, hei_profile, hei_admin):
    """PUT /api/heis/{hei_id} — updates fields."""
    resp = client.put(
        f"/api/heis/{hei_profile.hei_id}",
        json={"institution_type": "Deemed University", "established_year": 1990},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["institution_type"] == "Deemed University"
    assert data["established_year"] == 1990


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Add HEI capability
# ══════════════════════════════════════════════════════════════════════════════

def test_05_add_hei_capability(db, hei_profile, capability, hei_admin):
    """POST /api/heis/{hei_id}/capabilities — links a capability to HEI."""
    resp = client.post(
        f"/api/heis/{hei_profile.hei_id}/capabilities",
        json={
            "capability_id": str(capability.capability_id),
            "proficiency_level": "Advanced",
            "status": "Active",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["capability_id"] == str(capability.capability_id)
    assert data["proficiency_level"] == "Advanced"
    # cleanup
    obj = db.get(HeiCapability, uuid.UUID(data["hei_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Reject invalid capability_id
# ══════════════════════════════════════════════════════════════════════════════

def test_06_reject_invalid_capability(db, hei_profile, hei_admin):
    """POST /api/heis/{hei_id}/capabilities — 404 for non-existent capability."""
    fake_cap_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/heis/{hei_profile.hei_id}/capabilities",
        json={"capability_id": fake_cap_id, "status": "Active"},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 404, resp.text
    assert "Capability" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Prevent duplicate HEI capability
# ══════════════════════════════════════════════════════════════════════════════

def test_07_prevent_duplicate_hei_capability(db, hei_profile, capability, hei_admin):
    """POST /api/heis/{hei_id}/capabilities — 409 on duplicate."""
    payload = {
        "capability_id": str(capability.capability_id),
        "status": "Active",
    }
    r1 = client.post(
        f"/api/heis/{hei_profile.hei_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        f"/api/heis/{hei_profile.hei_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r2.status_code == 409, r2.text

    # cleanup
    obj = db.get(HeiCapability, uuid.UUID(r1.json()["hei_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — Create faculty
# ══════════════════════════════════════════════════════════════════════════════

def test_08_create_faculty(db, hei_profile, hei_admin):
    """POST /api/heis/{hei_id}/faculty — creates a faculty profile."""
    resp = client.post(
        f"/api/heis/{hei_profile.hei_id}/faculty",
        json={
            "user_id": str(hei_admin.user_id),
            "designation": "Professor",
            "department": "Environmental Science",
            "specialization": "Water Treatment",
            "experience_years": 12,
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["hei_id"] == str(hei_profile.hei_id)
    assert data["designation"] == "Professor"
    assert "faculty_id" in data
    # cleanup
    fp = db.get(FacultyExpertProfile, uuid.UUID(data["faculty_id"]))
    if fp:
        db.delete(fp)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 — Reject faculty belonging to another HEI
# ══════════════════════════════════════════════════════════════════════════════

def test_09_reject_faculty_from_another_hei(db, hei_profile, other_hei_admin):
    """POST /api/heis/{hei_id}/faculty — 403 when user belongs to a different HEI org."""
    resp = client.post(
        f"/api/heis/{hei_profile.hei_id}/faculty",
        json={
            "designation": "Lecturer",
            "department": "Physics",
            "experience_years": 3,
            "verification_status": "Pending",
        },
        headers=_bearer(other_hei_admin),
    )
    assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10 — Add faculty capability
# ══════════════════════════════════════════════════════════════════════════════

def test_10_add_faculty_capability(db, faculty_profile, capability, hei_admin):
    """POST /api/faculty/{faculty_id}/capabilities — links capability to faculty."""
    resp = client.post(
        f"/api/faculty/{faculty_profile.faculty_id}/capabilities",
        json={
            "capability_id": str(capability.capability_id),
            "proficiency_level": "Expert",
            "status": "Active",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["capability_id"] == str(capability.capability_id)
    assert data["proficiency_level"] == "Expert"
    # cleanup
    obj = db.get(FacultyExpertCapability, uuid.UUID(data["faculty_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 11 — Prevent duplicate faculty capability
# ══════════════════════════════════════════════════════════════════════════════

def test_11_prevent_duplicate_faculty_capability(db, faculty_profile, capability, hei_admin):
    """POST /api/faculty/{faculty_id}/capabilities — 409 on duplicate."""
    payload = {
        "capability_id": str(capability.capability_id),
        "status": "Active",
    }
    r1 = client.post(
        f"/api/faculty/{faculty_profile.faculty_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        f"/api/faculty/{faculty_profile.faculty_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r2.status_code == 409, r2.text

    # cleanup
    obj = db.get(FacultyExpertCapability, uuid.UUID(r1.json()["faculty_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 12 — Create institutional resource
# ══════════════════════════════════════════════════════════════════════════════

def test_12_create_institutional_resource(db, hei_profile, hei_admin):
    """POST /api/heis/{hei_id}/resources — creates a lab/resource."""
    resp = client.post(
        f"/api/heis/{hei_profile.hei_id}/resources",
        json={
            "name": f"IoT Lab {_uid()}",
            "resource_type": "Laboratory",
            "description": "IoT sensors and embedded systems lab",
            "capacity": 30,
            "availability_status": "Available",
            "verification_status": "Pending",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["hei_id"] == str(hei_profile.hei_id)
    assert data["resource_type"] == "Laboratory"
    assert data["capacity"] == 30
    # cleanup
    r = db.get(InstitutionalResource, uuid.UUID(data["resource_id"]))
    if r:
        db.delete(r)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 13 — Add resource capability
# ══════════════════════════════════════════════════════════════════════════════

def test_13_add_resource_capability(db, resource, capability, hei_admin):
    """POST /api/resources/{resource_id}/capabilities — links capability to resource."""
    resp = client.post(
        f"/api/resources/{resource.resource_id}/capabilities",
        json={
            "capability_id": str(capability.capability_id),
            "proficiency_level": "Advanced",
            "status": "Active",
        },
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["resource_id"] == str(resource.resource_id)
    assert data["capability_id"] == str(capability.capability_id)
    # cleanup
    obj = db.get(ResourceCapability, uuid.UUID(data["resource_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 14 — Prevent duplicate resource capability
# ══════════════════════════════════════════════════════════════════════════════

def test_14_prevent_duplicate_resource_capability(db, resource, capability, hei_admin):
    """POST /api/resources/{resource_id}/capabilities — 409 on duplicate."""
    payload = {
        "capability_id": str(capability.capability_id),
        "status": "Active",
    }
    r1 = client.post(
        f"/api/resources/{resource.resource_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        f"/api/resources/{resource.resource_id}/capabilities",
        json=payload,
        headers=_bearer(hei_admin),
    )
    assert r2.status_code == 409, r2.text

    # cleanup
    obj = db.get(ResourceCapability, uuid.UUID(r1.json()["resource_capability_id"]))
    if obj:
        db.delete(obj)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 15 — HEI Administrator authorization
# ══════════════════════════════════════════════════════════════════════════════

def test_15_hei_admin_authorization(db, hei_profile, hei_admin):
    """An HEI Administrator can update their own HEI."""
    resp = client.put(
        f"/api/heis/{hei_profile.hei_id}",
        json={"description": "Updated by HEI admin"},
        headers=_bearer(hei_admin),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] == "Updated by HEI admin"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 16 — Cross-HEI modification blocked
# ══════════════════════════════════════════════════════════════════════════════

def test_16_cross_hei_modification_blocked(db, hei_profile, other_hei_admin):
    """An HEI Administrator cannot update a different HEI's profile."""
    resp = client.put(
        f"/api/heis/{hei_profile.hei_id}",
        json={"description": "Attempted cross-HEI update"},
        headers=_bearer(other_hei_admin),
    )
    assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 17 — System Administrator access
# ══════════════════════════════════════════════════════════════════════════════

def test_17_system_admin_can_update_any_hei(db, hei_profile, sys_admin):
    """System Administrator can update any HEI profile."""
    resp = client.put(
        f"/api/heis/{hei_profile.hei_id}",
        json={"verification_status": "Verified"},
        headers=_bearer(sys_admin),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "Verified"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 18 — Read access (any authenticated user)
# ══════════════════════════════════════════════════════════════════════════════

def test_18_read_access_any_authenticated_user(db, hei_profile):
    """Any authenticated user can list and get HEI profiles."""
    # Create a plain citizen user
    citizen_org = _make_org(db, "Government")
    db.commit()
    citizen = _make_user(db, citizen_org, "Citizen")
    db.commit()

    try:
        # List HEIs
        list_resp = client.get("/api/heis", headers=_bearer(citizen))
        assert list_resp.status_code == 200, list_resp.text
        hei_ids = [h["hei_id"] for h in list_resp.json()]
        assert str(hei_profile.hei_id) in hei_ids

        # Get single HEI
        get_resp = client.get(f"/api/heis/{hei_profile.hei_id}", headers=_bearer(citizen))
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["hei_id"] == str(hei_profile.hei_id)
    finally:
        db.delete(citizen)
        db.commit()
        db.delete(citizen_org)
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 19 — Database migration (tables exist with correct columns)
# ══════════════════════════════════════════════════════════════════════════════

def test_19_database_migration(db):
    """All 6 HEI tables exist with required columns."""
    expected: dict[str, list[str]] = {
        "hei_profile": [
            "hei_id", "organization_id", "institution_type", "accreditation",
            "established_year", "website", "contact_details", "description",
            "verification_status", "created_at", "updated_at",
        ],
        "hei_capability": [
            "hei_capability_id", "hei_id", "capability_id",
            "proficiency_level", "evidence_description", "status",
            "created_at", "updated_at",
        ],
        "faculty_expert_profile": [
            "faculty_expert_id", "hei_id", "user_id", "designation", "department",
            "specialization", "experience_years", "profile_description",
            "verification_status", "created_at", "updated_at",
        ],
        "faculty_expert_capability": [
            "faculty_capability_id", "faculty_expert_id", "capability_id",
            "proficiency_level", "evidence_description", "status",
            "created_at", "updated_at",
        ],
        "institutional_resource": [
            "resource_id", "hei_id", "name", "resource_type", "description",
            "location", "capacity", "availability_status", "verification_status",
            "created_at", "updated_at",
        ],
        "resource_capability": [
            "resource_capability_id", "resource_id", "capability_id",
            "proficiency_level", "evidence_description", "status",
            "created_at", "updated_at",
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
        actual_cols = {r[0] for r in rows}
        assert actual_cols, f"Table '{table}' not found in database"
        for col in cols:
            assert col in actual_cols, (
                f"Column '{col}' missing from table '{table}'. "
                f"Found: {sorted(actual_cols)}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 20 — Existing health / auth / problem / AI endpoints still work
# ══════════════════════════════════════════════════════════════════════════════

def test_20_existing_endpoints_still_work(db):
    """Smoke-test existing endpoints to confirm nothing was broken."""
    # 20a — health
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 20b — db health
    r = client.get("/api/health/db")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 20c — auth: register + login
    suffix = _uid()
    test_org = _make_org(db, "Government")
    db.commit()
    try:
        register_payload = {
            "name": f"Smoke User {suffix}",
            "email": f"smoke-{suffix}@testdomain.example.com",
            "password": "Smoke1234!",
            "role": "Citizen",
            "organization_id": str(test_org.organization_id),
        }
        reg = client.post("/api/auth/register", json=register_payload)
        assert reg.status_code in (200, 201), reg.text

        login = client.post(
            "/api/auth/login",
            json={"email": f"smoke-{suffix}@testdomain.example.com", "password": "Smoke1234!"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 20d — GET /api/auth/me
        me = client.get("/api/auth/me", headers=auth_headers)
        assert me.status_code == 200, me.text

        # 20e — GET /api/organizations
        orgs = client.get("/api/organizations", headers=auth_headers)
        assert orgs.status_code == 200, orgs.text

        # 20f — GET /api/capabilities
        caps = client.get("/api/capabilities", headers=auth_headers)
        assert caps.status_code == 200, caps.text

        # 20g — GET /api/heis (registered at step 11)
        heis = client.get("/api/heis", headers=auth_headers)
        assert heis.status_code == 200, heis.text

    finally:
        # cleanup smoke user
        from app.models.user import User as UserModel
        from sqlalchemy import select as sa_select
        u = db.scalar(
            sa_select(UserModel).where(UserModel.email == f"smoke-{suffix}@testdomain.example.com")
        )
        if u:
            db.delete(u)
            db.commit()
        db.delete(test_org)
        db.commit()
