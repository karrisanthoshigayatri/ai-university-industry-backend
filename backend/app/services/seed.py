"""Seed data for CapabilityTaxonomy and Capability tables.

Called once at application startup (idempotent — skips existing records).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capability import Capability, CapabilityTaxonomy


logger = logging.getLogger(__name__)

# ── Taxonomy definitions ───────────────────────────────────────────────────────
TAXONOMIES: list[dict] = [
    {"name": "Engineering & Infrastructure",    "type": "Domain"},
    {"name": "Health & Life Sciences",          "type": "Domain"},
    {"name": "Agriculture & Environment",       "type": "Domain"},
    {"name": "Information Technology",          "type": "Domain"},
    {"name": "Social Sciences & Governance",    "type": "Domain"},
    {"name": "Energy & Sustainability",         "type": "Domain"},
    {"name": "Support & Enabling Services",     "type": "Support"},
]

# ── Capability definitions ─────────────────────────────────────────────────────
# Format: (name, type, taxonomy_name, parent_name_or_None)
CAPABILITIES: list[tuple[str, str, str, str | None]] = [
    # ── Domains ──────────────────────────────────────────────────────────────
    ("Agriculture",                 "Domain", "Agriculture & Environment",    None),
    ("Water Management",            "Domain", "Engineering & Infrastructure", None),
    ("Waste Management",            "Domain", "Agriculture & Environment",    None),
    ("Renewable Energy",            "Domain", "Energy & Sustainability",      None),
    ("Public Health",               "Domain", "Health & Life Sciences",       None),
    ("Smart Cities",                "Domain", "Information Technology",       None),
    ("Civil Infrastructure",        "Domain", "Engineering & Infrastructure", None),
    ("Environmental Science",       "Domain", "Agriculture & Environment",    None),
    ("Disaster Management",         "Domain", "Social Sciences & Governance", None),
    ("Urban Planning",              "Domain", "Social Sciences & Governance", None),
    # ── Children of Water Management ─────────────────────────────────────────
    ("Water Quality Monitoring",    "Domain", "Engineering & Infrastructure", "Water Management"),
    ("Wastewater Treatment",        "Domain", "Engineering & Infrastructure", "Water Management"),
    ("IoT Water Sensors",           "Technology", "Information Technology",   "Water Management"),
    # ── Children of Agriculture ───────────────────────────────────────────────
    ("Precision Agriculture",       "Domain", "Agriculture & Environment",    "Agriculture"),
    ("Soil Health Analysis",        "Expertise", "Agriculture & Environment", "Agriculture"),
    # ── Skills ───────────────────────────────────────────────────────────────
    ("Data Analysis",               "Skill", "Information Technology",        None),
    ("Machine Learning",            "Skill", "Information Technology",        None),
    ("IoT Development",             "Skill", "Information Technology",        None),
    ("GIS",                         "Skill", "Information Technology",        None),
    ("Mobile Application Development", "Skill", "Information Technology",    None),
    ("Project Management",          "Skill", "Social Sciences & Governance",  None),
    ("Field Research",              "Skill", "Social Sciences & Governance",  None),
    ("Statistical Modeling",        "Skill", "Information Technology",        None),
    ("Community Engagement",        "Skill", "Social Sciences & Governance",  None),
    # ── Expertise ─────────────────────────────────────────────────────────────
    ("Public Policy",               "Expertise", "Social Sciences & Governance", None),
    ("Environmental Impact Assessment", "Expertise", "Agriculture & Environment", None),
    ("Epidemiology",                "Expertise", "Health & Life Sciences",    None),
    ("Renewable Energy Systems",    "Expertise", "Energy & Sustainability",   None),
    ("Structural Engineering",      "Expertise", "Engineering & Infrastructure", None),
    # ── Technologies ─────────────────────────────────────────────────────────
    ("IoT Sensors",                 "Technology", "Information Technology",   None),
    ("Solar PV",                    "Technology", "Energy & Sustainability",  None),
    ("Computer Vision",             "Technology", "Information Technology",   None),
    ("GIS Mapping",                 "Technology", "Information Technology",   None),
    ("Drone Technology",            "Technology", "Information Technology",   None),
    ("Blockchain",                  "Technology", "Information Technology",   None),
    # ── Resources ─────────────────────────────────────────────────────────────
    ("Laboratory Facilities",       "Resource", "Health & Life Sciences",     None),
    ("Research Equipment",          "Resource", "Engineering & Infrastructure", None),
    ("Computing Infrastructure",    "Resource", "Information Technology",     None),
    ("Field Testing Facilities",    "Resource", "Engineering & Infrastructure", None),
    # ── Support Capability ────────────────────────────────────────────────────
    ("Funding",                     "Support Capability", "Support & Enabling Services", None),
    ("Mentorship",                  "Support Capability", "Support & Enabling Services", None),
    ("Testing",                     "Support Capability", "Support & Enabling Services", None),
    ("Manufacturing",               "Support Capability", "Support & Enabling Services", None),
    ("Deployment",                  "Support Capability", "Support & Enabling Services", None),
    ("Technology Transfer",         "Support Capability", "Support & Enabling Services", None),
    ("Incubation",                  "Support Capability", "Support & Enabling Services", None),
]


def seed_capabilities(db: Session) -> None:
    """Insert seed taxonomy and capabilities. Fully idempotent."""

    # ── Seed taxonomies ────────────────────────────────────────────────────────
    taxonomy_map: dict[str, UUID] = {}
    for t in TAXONOMIES:
        existing = db.scalar(
            select(CapabilityTaxonomy).where(CapabilityTaxonomy.name == t["name"])
        )
        if existing is None:
            obj = CapabilityTaxonomy(name=t["name"], type=t["type"], active_status=True, version="1.0")
            db.add(obj)
            db.flush()
            taxonomy_map[t["name"]] = obj.taxonomy_id
            logger.info("Seeded taxonomy: %s", t["name"])
        else:
            taxonomy_map[t["name"]] = existing.taxonomy_id

    db.commit()

    # ── First pass: seed root capabilities (no parent) ─────────────────────────
    capability_map: dict[str, UUID] = {}
    for name, cap_type, tax_name, parent_name in CAPABILITIES:
        if parent_name is not None:
            continue  # skip children for now

        existing = db.scalar(
            select(Capability).where(
                Capability.name == name,
                Capability.capability_type == cap_type,
            )
        )
        if existing is None:
            tax_id = taxonomy_map.get(tax_name)
            obj = Capability(
                name=name,
                capability_type=cap_type,
                taxonomy_id=tax_id,
                status="Active",
            )
            db.add(obj)
            db.flush()
            capability_map[name] = obj.capability_id
            logger.info("Seeded capability: %s (%s)", name, cap_type)
        else:
            capability_map[name] = existing.capability_id

    db.commit()

    # ── Second pass: seed child capabilities ──────────────────────────────────
    for name, cap_type, tax_name, parent_name in CAPABILITIES:
        if parent_name is None:
            continue

        existing = db.scalar(
            select(Capability).where(
                Capability.name == name,
                Capability.capability_type == cap_type,
            )
        )
        if existing is None:
            tax_id = taxonomy_map.get(tax_name)
            parent_id = capability_map.get(parent_name)
            obj = Capability(
                name=name,
                capability_type=cap_type,
                taxonomy_id=tax_id,
                parent_capability_id=parent_id,
                status="Active",
            )
            db.add(obj)
            db.flush()
            capability_map[name] = obj.capability_id
            logger.info("Seeded child capability: %s -> %s (%s)", parent_name, name, cap_type)
        else:
            capability_map[name] = existing.capability_id

    db.commit()
    logger.info("Capability seed complete. Total mapped: %d", len(capability_map))
