"""Demo seed script — STEP 27.

Creates a complete realistic dataset for the end-to-end demo:
  Problem → HEI Match → Faculty Match → Capability Gap → Partner Match
  → Collaboration → Project → Milestones → Output → Impact

Usage (from backend/ directory):
    python -m app.services.demo_seed

IDEMPOTENT — safe to run multiple times.
Does NOT run at application startup.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.capability import Capability
from app.models.evidence import Availability
from app.models.hei import (
    FacultyExpertCapability, FacultyExpertProfile,
    HeiCapability, HeiProfile,
    InstitutionalResource, ResourceCapability,
)
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
from app.models.problem import Problem
from app.models.user import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _org(db, name, org_type, identifier, state="Karnataka"):
    ex = db.scalar(select(Organization).where(Organization.name == name))
    if ex: return ex
    o = Organization(name=name, organization_type=org_type,
                     official_identifier=identifier, state=state,
                     district="Mysuru", verification_status="Verified")
    db.add(o); db.flush()
    logger.info("org: %s", name)
    return o


def _user(db, email, name, role, org):
    ex = db.scalar(select(User).where(User.email == email))
    if ex: return ex
    u = User(organization_id=org.organization_id, name=name, email=email,
             password_hash=hash_password("Demo@1234"), role=role, status="active")
    db.add(u); db.flush()
    logger.info("user: %s (%s)", email, role)
    return u


def _cap(db, name):
    return db.scalar(select(Capability).where(Capability.name == name))


def _hei(db, org):
    ex = db.scalar(select(HeiProfile).where(HeiProfile.organization_id == org.organization_id))
    if ex: return ex
    h = HeiProfile(organization_id=org.organization_id, institution_type="University",
                   established_year=1985, verification_status="Verified")
    db.add(h); db.flush()
    logger.info("hei: %s", org.name)
    return h


def _partner(db, org, ptype):
    ex = db.scalar(select(PartnerProfile).where(PartnerProfile.organization_id == org.organization_id))
    if ex: return ex
    p = PartnerProfile(organization_id=org.organization_id, partner_type=ptype,
                       verification_status="Verified")
    db.add(p); db.flush()
    logger.info("partner: %s (%s)", org.name, ptype)
    return p


def _hei_cap(db, hei, cap, level):
    ex = db.scalar(select(HeiCapability).where(
        HeiCapability.hei_id == hei.hei_id,
        HeiCapability.capability_id == cap.capability_id))
    if not ex:
        db.add(HeiCapability(hei_id=hei.hei_id, capability_id=cap.capability_id,
                              proficiency_level=level, status="Active",
                              verification_status="Verified"))


def _partner_cap(db, partner, cap, level):
    ex = db.scalar(select(PartnerCapability).where(
        PartnerCapability.partner_id == partner.partner_id,
        PartnerCapability.capability_id == cap.capability_id))
    if not ex:
        db.add(PartnerCapability(partner_id=partner.partner_id,
                                  capability_id=cap.capability_id,
                                  proficiency_level=level,
                                  verification_status="Verified"))


# ══════════════════════════════════════════════════════════════════════════════

def run_demo_seed(db: Session) -> None:
    logger.info("=== Demo seed starting ===")

    # 1. Government
    gov_org = _org(db, "Karnataka State Government", "Government", "GOV-KA-001")
    gov_user = _user(db, "officer@demo.gov.in", "Ravi Kumar", "Government Officer", gov_org)
    db.commit()

    # 2. HEIs
    hei_a_org = _org(db, "National Institute of Technology Karnataka", "HEI", "NITK-001")
    hei_b_org = _org(db, "Indian Institute of Science", "HEI", "IISC-001")
    hei_c_org = _org(db, "University of Agricultural Sciences", "HEI", "UAS-001")
    db.commit()

    hei_a = _hei(db, hei_a_org)
    hei_b = _hei(db, hei_b_org)
    hei_c = _hei(db, hei_c_org)

    fac_a_user = _user(db, "driot@nitk.edu.in", "Dr. Priya Sharma", "Faculty / Expert", hei_a_org)
    fac_b_user = _user(db, "drsensor@iisc.edu.in", "Dr. Arjun Nair", "Faculty / Expert", hei_b_org)
    db.commit()

    # 3. Capabilities (seeded at startup)
    caps = {}
    for name in ["Agriculture", "IoT Sensors", "Data Analysis", "IoT Development",
                 "Testing", "Field Research"]:
        c = _cap(db, name)
        if c:
            caps[name] = c
        else:
            logger.warning("Missing capability '%s' — run startup seed first", name)

    # 4. HEI capabilities
    for name, level in [("Agriculture", "Expert"), ("IoT Sensors", "Expert"),
                         ("IoT Development", "Expert"), ("Data Analysis", "Advanced"),
                         ("Testing", "Advanced")]:
        if name in caps: _hei_cap(db, hei_a, caps[name], level)

    for name, level in [("IoT Sensors", "Advanced"), ("Data Analysis", "Expert"),
                         ("IoT Development", "Advanced")]:
        if name in caps: _hei_cap(db, hei_b, caps[name], level)

    for name, level in [("Agriculture", "Expert"), ("Field Research", "Expert"),
                         ("Data Analysis", "Intermediate")]:
        if name in caps: _hei_cap(db, hei_c, caps[name], level)

    db.commit()

    # 5. Faculty
    if not db.scalar(select(FacultyExpertProfile).where(FacultyExpertProfile.user_id == fac_a_user.user_id)):
        fac_a = FacultyExpertProfile(hei_id=hei_a.hei_id, user_id=fac_a_user.user_id,
                                      designation="Professor", department="Electronics",
                                      specialization="IoT and Embedded Systems",
                                      experience_years=12, verification_status="Verified")
        db.add(fac_a); db.flush()
        for name, lvl in [("IoT Sensors", "Expert"), ("IoT Development", "Expert"),
                            ("Data Analysis", "Advanced")]:
            if name in caps:
                db.add(FacultyExpertCapability(faculty_id=fac_a.faculty_id,
                                               capability_id=caps[name].capability_id,
                                               proficiency_level=lvl, status="Active"))
        logger.info("faculty: Dr. Priya Sharma")

    if not db.scalar(select(FacultyExpertProfile).where(FacultyExpertProfile.user_id == fac_b_user.user_id)):
        fac_b = FacultyExpertProfile(hei_id=hei_b.hei_id, user_id=fac_b_user.user_id,
                                      designation="Associate Professor", department="Electrical Engineering",
                                      specialization="Sensor Networks",
                                      experience_years=8, verification_status="Verified")
        db.add(fac_b); db.flush()
        for name, lvl in [("IoT Sensors", "Advanced"), ("Data Analysis", "Expert")]:
            if name in caps:
                db.add(FacultyExpertCapability(faculty_id=fac_b.faculty_id,
                                               capability_id=caps[name].capability_id,
                                               proficiency_level=lvl, status="Active"))
        logger.info("faculty: Dr. Arjun Nair")

    db.commit()

    # 6. Resources
    if not db.scalar(select(InstitutionalResource).where(
            InstitutionalResource.hei_id == hei_a.hei_id,
            InstitutionalResource.name == "IoT Research Laboratory")):
        res = InstitutionalResource(hei_id=hei_a.hei_id, name="IoT Research Laboratory",
                                     resource_type="Laboratory", availability_status="Available",
                                     verification_status="Verified")
        db.add(res); db.flush()
        if "IoT Sensors" in caps:
            db.add(ResourceCapability(resource_id=res.resource_id,
                                       capability_id=caps["IoT Sensors"].capability_id,
                                       proficiency_level="Expert", status="Active"))
        db.add(Availability(entity_type="institutional_resource", entity_id=res.resource_id,
                             status="Available", capacity=5,
                             start_date=date(2026, 10, 1), end_date=date(2027, 6, 30)))
        logger.info("resource: IoT Research Laboratory")

    if not db.scalar(select(InstitutionalResource).where(
            InstitutionalResource.hei_id == hei_c.hei_id,
            InstitutionalResource.name == "Agricultural Field Station")):
        res2 = InstitutionalResource(hei_id=hei_c.hei_id, name="Agricultural Field Station",
                                      resource_type="Field Facility", availability_status="Available",
                                      verification_status="Verified")
        db.add(res2); db.flush()
        if "Agriculture" in caps:
            db.add(ResourceCapability(resource_id=res2.resource_id,
                                       capability_id=caps["Agriculture"].capability_id,
                                       proficiency_level="Expert", status="Active"))
        logger.info("resource: Agricultural Field Station")

    db.commit()

    # 7. Partners
    ind_org = _org(db, "AgroTech Solutions Pvt Ltd", "Industry", "AGROTECH-001")
    startup_org = _org(db, "SmartFarm Startup", "Startup", "SMARTFARM-001")
    csr_org = _org(db, "Rural Development Foundation", "CSR Organization", "RDF-001")
    db.commit()

    partner_ind = _partner(db, ind_org, "Industry")
    partner_startup = _partner(db, startup_org, "Startup")
    partner_csr = _partner(db, csr_org, "CSR Organization")
    db.commit()

    for name, lvl in [("IoT Sensors", 4), ("IoT Development", 3), ("Testing", 4)]:
        if name in caps: _partner_cap(db, partner_ind, caps[name], lvl)
    for name, lvl in [("Agriculture", 3), ("IoT Development", 3)]:
        if name in caps: _partner_cap(db, partner_startup, caps[name], lvl)
    for name, lvl in [("Agriculture", 4), ("Field Research", 3)]:
        if name in caps: _partner_cap(db, partner_csr, caps[name], lvl)
    db.commit()

    if not db.scalar(select(PartnerSupportOffering).where(
            PartnerSupportOffering.partner_id == partner_ind.partner_id)):
        db.add(PartnerSupportOffering(partner_id=partner_ind.partner_id, support_type="Technology",
                                       title="IoT Platform and Sensor Supply", status="Active",
                                       availability_start=date(2026, 10, 1),
                                       availability_end=date(2027, 12, 31)))
        db.add(PartnerSupportOffering(partner_id=partner_startup.partner_id, support_type="Deployment",
                                       title="Smart Irrigation App", status="Active"))
        db.add(PartnerSupportOffering(partner_id=partner_csr.partner_id, support_type="Funding",
                                       title="Rural Technology Grant", status="Active"))
        db.commit()
        logger.info("support offerings created")

    # 8. Demo problem
    if not db.scalar(select(Problem).where(
            Problem.title == "Village requires smart irrigation monitoring")):
        prob = Problem(
            title="Village requires smart irrigation monitoring",
            description=(
                "A rural village is facing inefficient irrigation and excessive water usage. "
                "The community needs an affordable smart irrigation monitoring solution."
            ),
            submitter_id=gov_user.user_id, source_type="Government",
            location="Karnataka Mysuru", current_status="Validated",
        )
        db.add(prob); db.commit()
        logger.info("demo problem created: %s", prob.problem_id)
    else:
        prob = db.scalar(select(Problem).where(
            Problem.title == "Village requires smart irrigation monitoring"))
        logger.info("demo problem exists: %s", prob.problem_id)

    logger.info("=== Demo seed complete ===")
    logger.info("Login: officer@demo.gov.in / Demo@1234")
    logger.info("Workflow: POST /api/matching/problems/%s/heis", prob.problem_id)


if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_demo_seed(db)
    finally:
        db.close()
