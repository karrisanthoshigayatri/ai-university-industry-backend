"""Seed the CAPABILITY_TAXONOMY and CAPABILITY tables with MVP data.

Run once via the migration or manually. Idempotent — skips existing entries.
"""

from sqlalchemy.orm import Session
from app.models.capability import Capability, CapabilityTaxonomy


def seed_capabilities(db: Session) -> None:
    """Insert MVP taxonomy and capabilities if not already present."""

    # ── Taxonomies ─────────────────────────────────────────────────────────────
    taxonomies = [
        {"name": "Domain Knowledge", "type": "Domain", "version": "1.0"},
        {"name": "Technical Skills", "type": "Skill", "version": "1.0"},
        {"name": "Technologies", "type": "Technology", "version": "1.0"},
        {"name": "Support Capabilities", "type": "Support Capability", "version": "1.0"},
        {"name": "Research Expertise", "type": "Expertise", "version": "1.0"},
        {"name": "Resources", "type": "Resource", "version": "1.0"},
    ]
    taxonomy_map: dict[str, CapabilityTaxonomy] = {}
    for td in taxonomies:
        existing = db.query(CapabilityTaxonomy).filter_by(name=td["name"], version=td["version"]).first()
        if not existing:
            t = CapabilityTaxonomy(**td, active_status=True)
            db.add(t)
            db.flush()
            taxonomy_map[td["name"]] = t
        else:
            taxonomy_map[td["name"]] = existing
    db.commit()

    # ── Domain capabilities ────────────────────────────────────────────────────
    domain_tax = taxonomy_map["Domain Knowledge"]
    domains = [
        "Agriculture", "Water Management", "Waste Management",
        "Renewable Energy", "Public Health", "Smart Cities",
        "Education", "Infrastructure Management", "Environmental Management",
        "Urban Planning", "Civil Engineering", "Public Health Services",
    ]
    domain_map: dict[str, Capability] = {}
    for dname in domains:
        existing = db.query(Capability).filter_by(name=dname, capability_type="Domain").first()
        if not existing:
            c = Capability(name=dname, capability_type="Domain", taxonomy_id=domain_tax.taxonomy_id, status="Active")
            db.add(c)
            db.flush()
            domain_map[dname] = c
        else:
            domain_map[dname] = existing

    # Water Management sub-capabilities
    wm = domain_map.get("Water Management")
    if wm:
        for sub in ["Water Quality Monitoring", "Wastewater Treatment", "IoT Water Sensors"]:
            if not db.query(Capability).filter_by(name=sub, capability_type="Domain").first():
                db.add(Capability(name=sub, capability_type="Domain",
                                  taxonomy_id=domain_tax.taxonomy_id,
                                  parent_capability_id=wm.capability_id, status="Active"))

    db.commit()

    # ── Skill capabilities ────────────────────────────────────────────────────
    skill_tax = taxonomy_map["Technical Skills"]
    skills = [
        "Data Analysis", "Machine Learning", "IoT Development",
        "GIS", "Mobile Application Development", "Project Management",
        "Field Research", "Software Development", "Data Engineering",
    ]
    for sname in skills:
        if not db.query(Capability).filter_by(name=sname, capability_type="Skill").first():
            db.add(Capability(name=sname, capability_type="Skill",
                              taxonomy_id=skill_tax.taxonomy_id, status="Active"))
    db.commit()

    # ── Technology capabilities ───────────────────────────────────────────────
    tech_tax = taxonomy_map["Technologies"]
    techs = [
        "IoT Sensors", "Solar PV", "Computer Vision",
        "GIS Mapping", "Remote Sensing", "Blockchain",
        "Cloud Computing", "Edge Computing",
    ]
    for tname in techs:
        if not db.query(Capability).filter_by(name=tname, capability_type="Technology").first():
            db.add(Capability(name=tname, capability_type="Technology",
                              taxonomy_id=tech_tax.taxonomy_id, status="Active"))
    db.commit()

    # ── Support capabilities ──────────────────────────────────────────────────
    support_tax = taxonomy_map["Support Capabilities"]
    supports = [
        "Funding", "Mentorship", "Testing",
        "Manufacturing", "Deployment", "Training",
    ]
    for spname in supports:
        if not db.query(Capability).filter_by(name=spname, capability_type="Support Capability").first():
            db.add(Capability(name=spname, capability_type="Support Capability",
                              taxonomy_id=support_tax.taxonomy_id, status="Active"))
    db.commit()

    # ── Expertise capabilities ────────────────────────────────────────────────
    exp_tax = taxonomy_map["Research Expertise"]
    expertises = [
        "Academic Research", "Policy Analysis", "Technology Transfer",
        "Community Development", "Impact Assessment",
    ]
    for ename in expertises:
        if not db.query(Capability).filter_by(name=ename, capability_type="Expertise").first():
            db.add(Capability(name=ename, capability_type="Expertise",
                              taxonomy_id=exp_tax.taxonomy_id, status="Active"))
    db.commit()

    # ── Resource capabilities ─────────────────────────────────────────────────
    res_tax = taxonomy_map["Resources"]
    resources = [
        "Laboratory Equipment", "Research Infrastructure",
        "Computing Resources", "Field Vehicles",
    ]
    for rname in resources:
        if not db.query(Capability).filter_by(name=rname, capability_type="Resource").first():
            db.add(Capability(name=rname, capability_type="Resource",
                              taxonomy_id=res_tax.taxonomy_id, status="Active"))
    db.commit()
