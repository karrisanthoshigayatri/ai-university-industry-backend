"""Demo seed script — STEP 27.

Creates a complete realistic dataset for the end-to-end demo workflow:
  Problem → HEI Match → Faculty Match → Capability Gap → Partner Match
  → Collaboration → Project → Milestones → Output → Impact

Usage (run from backend/ directory):
    python -m app.services.demo_seed

This script is IDEMPOTENT — safe to run multiple times.
It does NOT run automatically at startup.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.capability import Capability
from app.models.evidence import Availability
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
from app.models.problem import Problem
from app.models.user import User
from app.core.security import hash_password

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

NOW = datetime.now(timezone.utc)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_or_create_org(db: Session, name: str, org_type: str, identifier: str,
                       state: str = "Karnataka") -> Organization:
    existing = db.scalar(select(Organization).where(Organization.name == name))
    if existing:
        return existing
    org = Organization(name=name, organization_type=org_type,
                       official_identifier=identifier, state=state,
                       district="Mysuru", verification_status="Verified")
    db.add(org); db.flush()
    logger.info("Created org: %s (%s)", name, org_type)
    return org


def _get_or_create_user(db: Session, email: str, name: str, role: str,
                         org: Organization) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing
    u = User(organization_id=org.organization_id, name=name, email=email,
             password_hash=hash_password("Demo@1234"), role=role, status="active")
    db.add(u); db.flush()
    logger.info("Created user: %s (%s)", email, role)
    return u


def _get_cap(db: Session, name: str) -> Capability | None:
    return db.scalar(select(Capability).where(Capability.name == name))


def _get_or_create_hei(db: Session, org: Organization) -> HeiProfile:
    existing = db.scalar(select(HeiProfile).where(HeiProfile.organization_id == org.organization_id))
    if existing:
        return existing
    hei = HeiProfile(organization_id=org.organization_id, institution_type="University",
                     established_year=1985, website=f"https://{org.name.lower().replace(' ', '')}.edu.in",
                     verification_status="Verified",
                     description=f"Premier engineering institution in Karnataka.")
    db.add(hei); db.flush()
    logger.info("Created HEI: %s", org.name)
    return hei


def _get_or_create_partner(db: Session, org: Organization,
                             partner_type: str) -> PartnerProfile:
    existing = db.scalar(select(PartnerProfile).where(
        PartnerProfile.organization_id == org.organization_id))
    if existing:
        return existing
    p = PartnerProfile(organization_id=org.organization_id, partner_type=partner_type,
                       description=f"A leading {partner_type} organisation in agri-tech.",
                       verification_status="Verified")
    db.add(p); db.flush()
    logger.info("Created partner: %s (%s)", org.name, partner_type)
    return p


def _add_hei_cap(db: Session, hei: HeiProfile, cap: Capability, level: str) -> None:
    existing = db.scalar(select(HeiCapability).where(
        HeiCapability.hei_id == hei.hei_id,
        HeiCapability.capability_id == cap.capability_id))
    if not existing:
        db.add(HeiCapability(hei_id=hei.hei_id, capability_id=cap.capability_id,
                              proficiency_level=level, status="Active",
                              verification_status="Verified"))


def _add_partner_cap(db: Session, partner: PartnerProfile, cap: Capability,
                      level: int) -> None:
    existing = db.scalar(select(PartnerCapability).where(
        PartnerCapability.partner_id == partner.partner_id,
        PartnerCapability.capability_id == cap.capability_id))
    if not existing:
        db.add(PartnerCapability(partner_id=partner.partner_id,
                                  capability_id=cap.capability_id,
                                  proficiency_level=level,
                                  verification_status="Verified"))


# ══════════════════════════════════════════════════════════════════════════════
# Main seed function
# ══════════════════════════════════════════════════════════════════════════════

def run_demo_seed(db: Session) -> None:
    logger.info("═══ Starting demo seed ═══")

    # ── 1. Government org + officer ───────────────────────────────────────────
    gov_org = _get_or_create_org(db, "Karnataka State Government", "Government",
                                  "GOV-KA-001", state="Karnataka")
    gov_user = _get_or_create_user(db, "officer@demo.gov.in", "Ravi Kumar",
                                    "Government Officer", gov_org)
    db.commit()

    # ── 2. HEIs ───────────────────────────────────────────────────────────────
    hei_a_org = _get_or_create_org(db, "National Institute of Technology Karnataka",
                                    "HEI", "NITK-001", state="Karnataka")
    hei_b_org = _get_or_create_org(db, "Indian Institute of Science",
                                    "HEI", "IISC-001", state="Karnataka")
    hei_c_org = _get_or_create_org(db, "University of Agricultural Sciences",
                                    "HEI", "UAS-001", state="Karnataka")
    db.commit()

    hei_a = _get_or_create_hei(db, hei_a_org)
    hei_b = _get_or_create_hei(db, hei_b_org)
    hei_c = _get_or_create_hei(db, hei_c_org)
    db.commit()

    # ── 3. Faculty users ──────────────────────────────────────────────────────
    fac_a_user = _get_or_create_user(db, "driot@nitk.edu.in", "Dr. Priya Sharma",
                                      "Faculty / Expert", hei_a_org)
    fac_b_user = _get_or_create_user(db, "drsensor@iisc.edu.in", "Dr. Arjun Nair",
                                      "Faculty / Expert", hei_b_org)
    db.commit()

    # ── 4. Required capabilities (from seed) ──────────────────────────────────
    cap_names = ["Agriculture", "IoT Sensors", "Data Analysis",
                 "IoT Development", "Testing", "Field Research"]
    caps = {n: _get_cap(db, n) for n in cap_names}
    missing = [n for n, c in caps.items() if c is None]
    if missing:
        logger.warning("Missing capabilities (run startup seed first): %s", missing)
    caps = {n: c for n, c in caps.items() if c is not None}

    # ── 5. HEI capabilities ───────────────────────────────────────────────────
    hei_a_caps = {
        "Agriculture": "Expert", "IoT Sensors": "Expert",
        "IoT Development": "Expert", "Data Analysis": "Advanced", "Testing": "Advanced",
    }
    for cap_name, level in hei_a_caps.items():
        if cap_name in caps:
            _add_hei_cap(db, hei_a, caps[cap_name], level)

    hei_b_caps = {
        "IoT Sensors": "Advanced", "Data Analysis": "Expert",
        "IoT Development": "Advanced", "Testing": "Intermediate",
    }
    for cap_name, level in hei_b_caps.items():
        if cap_name in caps:
            _add_hei_cap(db, hei_b, caps[cap_name], level)

    hei_c_caps = {
        "Agriculture": "Expert", "Field Research": "Expert",
        "Data Analysis": "Intermediate",
    }
    for cap_name, level in hei_c_caps.items():
        if cap_name in caps:
            _add_hei_cap(db, hei_c, caps[cap_name], level)

    db.commit()

    # ── 6. Faculty profiles + capabilities ────────────────────────────────────
    fac_a_existing = db.scalar(select(FacultyExpertProfile).where(
        FacultyExpertProfile.user_id == fac_a_user.user_id))
    if not fac_a_existing:
        fac_a = FacultyExpertProfile(
            hei_id=hei_a.hei_id, user_id=fac_a_user.user_id,
            designation="Professor", department="Electronics & Communication",
            specialization="IoT and Embedded Systems",
            experience_years=12, verification_status="Verified")
        db.add(fac_a); db.flush()
        for cap_name, lvl in [("IoT Sensors", "Expert"), ("IoT Development", "Expert"),
                                ("Data Analysis", "Advanced")]:
            if cap_name in caps:
                db.add(FacultyExpertCapability(
                    faculty_id=fac_a.faculty_id,
                    capability_id=caps[cap_name].capability_id,
                    proficiency_level=lvl, status="Active"))
        db.commit()
        logger.info("Created faculty: Dr. Priya Sharma")

    fac_b_existing = db.scalar(select(FacultyExpertProfile).where(
        FacultyExpertProfile.user_id == fac_b_user.user_id))
    if not fac_b_existing:
        fac_b = FacultyExpertProfile(
            hei_id=hei_b.hei_id, user_id=fac_b_user.user_id,
            designation="Associate Professor", department="Electrical Engineering",
            specialization="Sensor Networks", experience_years=8,
            verification_status="Verified")
        db.add(fac_b); db.flush()
        for cap_name, lvl in [("IoT Sensors", "Advanced"), ("Data Analysis", "Expert")]:
            if cap_name in caps:
                db.add(FacultyExpertCapability(
                    faculty_id=fac_b.faculty_id,
                    capability_id=caps[cap_name].capability_id,
                    proficiency_level=lvl, status="Active"))
        db.commit()
        logger.info("Created faculty: Dr. Arjun Nair")

    # ── 7. Institutional resources ────────────────────────────────────────────
    existing_res = db.scalar(select(InstitutionalResource).where(
        InstitutionalResource.hei_id == hei_a.hei_id,
        InstitutionalResource.name == "IoT Research Laboratory"))
    if not existing_res:
        res_a = InstitutionalResource(
            hei_id=hei_a.hei_id, name="IoT Research Laboratory",
            resource_type="Laboratory",
            description="State-of-the-art IoT and embedded systems lab",
            availability_status="Available", verification_status="Verified")
        db.add(res_a); db.flush()
        if "IoT Sensors" in caps:
            db.add(ResourceCapability(resource_id=res_a.resource_id,
                                       capability_id=caps["IoT Sensors"].capability_id,
                                       proficiency_level="Expert", status="Active"))
        db.add(Availability(entity_type="institutional_resource",
                             entity_id=res_a.resource_id, status="Available",
                             capacity=5, start_date=date(2026, 10, 1),
                             end_date=date(2027, 6, 30)))
        db.commit()
        logger.info("Created resource: IoT Research Laboratory")

    existing_res2 = db.scalar(select(InstitutionalResource).where(
        InstitutionalResource.hei_id == hei_c.hei_id,
        InstitutionalResource.name == "Agricultural Field Station"))
    if not existing_res2:
        res_c = InstitutionalResource(
            hei_id=hei_c.hei_id, name="Agricultural Field Station",
            resource_type="Field Facility",
            description="70-acre experimental agricultural field",
            availability_status="Available", verification_status="Verified")
        db.add(res_c); db.flush()
        if "Agriculture" in caps:
            db.add(ResourceCapability(resource_id=res_c.resource_id,
                                       capability_id=caps["Agriculture"].capability_id,
                                       proficiency_level="Expert", status="Active"))
        db.commit()
        logger.info("Created resource: Agricultural Field Station")

    # ── 8. Partners ───────────────────────────────────────────────────────────
    ind_org = _get_or_create_org(db, "AgroTech Solutions Pvt Ltd", "Industry",
                                  "AGROTECH-001", state="Karnataka")
    startup_org = _get_or_create_org(db, "SmartFarm Startup", "Startup",
                                      "SMARTFARM-001", state="Karnataka")
    csr_org = _get_or_create_org(db, "Rural Development Foundation",
                                  "CSR Organization", "RDF-001", state="Karnataka")
    db.commit()

    partner_ind = _get_or_create_partner(db, ind_org, "Industry")
    partner_startup = _get_or_create_partner(db, startup_org, "Startup")
    partner_csr = _get_or_create_partner(db, csr_org, "CSR Organization")
    db.commit()

    # Partner capabilities
    for cap_name, lvl in [("IoT Sensors", 4), ("IoT Development", 3), ("Testing", 4)]:
        if cap_name in caps:
            _add_partner_cap(db, partner_ind, caps[cap_name], lvl)

    for cap_name, lvl in [("Agriculture", 3), ("IoT Development", 3)]:
        if cap_name in caps:
            _add_partner_cap(db, partner_startup, caps[cap_name], lvl)

    for cap_name, lvl in [("Agriculture", 4), ("Field Research", 3)]:
        if cap_name in caps:
            _add_partner_cap(db, partner_csr, caps[cap_name], lvl)

    db.commit()

    # Support offerings
    existing_off = db.scalar(select(PartnerSupportOffering).where(
        PartnerSupportOffering.partner_id == partner_ind.partner_id,
        PartnerSupportOffering.support_type == "Technology"))
    if not existing_off:
        db.add(PartnerSupportOffering(
            partner_id=partner_ind.partner_id, support_type="Technology",
            title="IoT Platform and Sensor Supply",
            description="End-to-end IoT deployment including hardware",
            status="Active", availability_start=date(2026, 10, 1),
            availability_end=date(2027, 12, 31)))
        db.add(PartnerSupportOffering(
            partner_id=partner_startup.partner_id, support_type="Deployment",
            title="Smart Irrigation App",
            description="Mobile app for farmer irrigation control",
            status="Active"))
        db.add(PartnerSupportOffering(
            partner_id=partner_csr.partner_id, support_type="Funding",
            title="Rural Technology Grant",
            description="Up to ₹25 lakh for rural IoT deployments",
            status="Active"))
        db.commit()
        logger.info("Created support offerings")

    # ── 9. The demo problem ───────────────────────────────────────────────────
    existing_prob = db.scalar(select(Problem).where(
        Problem.title == "Village requires smart irrigation monitoring"))
    if not existing_prob:
        prob = Problem(
            title="Village requires smart irrigation monitoring",
            description=(
                "A rural village is facing inefficient irrigation and excessive water usage. "
                "The community needs an affordable smart irrigation monitoring solution."
            ),
            submitter_id=gov_user.user_id,
            source_type="Government",
            location="Karnataka Mysuru",
            current_status="Validated",
        )
        db.add(prob); db.commit()
        logger.info("Created demo problem: %s", prob.problem_id)
    else:
        logger.info("Demo problem already exists: %s", existing_prob.problem_id)

    logger.info("═══ Demo seed complete ═══")
    logger.info("Demo credentials:")
    logger.info("  Government Officer: officer@demo.gov.in / Demo@1234")
    logger.info("  Faculty (NITK):     driot@nitk.edu.in  / Demo@1234")
    logger.info("  Faculty (IISc):     drsensor@iisc.edu.in / Demo@1234")
    logger.info("")
    logger.info("Workflow entry point: POST /api/matching/problems/<prob_id>/heis")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_demo_seed(db)
    finally:
        db.close()
