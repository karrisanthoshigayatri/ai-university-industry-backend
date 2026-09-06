"""Capability Gap Analysis and Partner Matching services — Steps 19–20.

Gap scoring
-----------
  gap_level = max(0, required_level - available_level)
  status    = Open | Partially Filled | Filled

Partner matching weights
------------------------
  Capability fit       40 pts
  Support offering     25 pts
  Domain relevance     15 pts
  Availability         10 pts
  Location/constraints 10 pts
  Total               100 pts
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.capability_gap import PARTNER_MATCH_MODEL_VERSION, CapabilityGap, PartnerMatch
from app.models.evidence import Availability, EntityConstraint
from app.models.hei import HeiCapability, HeiProfile
from app.models.organization import Organization
from app.models.partner import PartnerCapability, PartnerProfile, PartnerSupportOffering
from app.models.problem import Problem
from app.models.project import Project, ProjectCapability
from app.models.user import User
from app.schemas.capability_gap import (
    CapabilityGapResponse, GapAnalysisResponse, GapDetail,
    PartnerCapDetail, PartnerMatchResponse, PartnerMatchResult,
    SupportOfferingDetail,
)

_WRITE_ROLES = {"Government Officer", "System Administrator", "HEI Administrator"}
_PROFICIENCY: dict[str, float] = {
    "beginner": 1.0, "basic": 1.0,
    "intermediate": 2.0, "advanced": 3.0, "expert": 4.0,
}

W_CAP = 40.0; W_SUP = 25.0; W_DOM = 15.0; W_AVAIL = 10.0; W_CON = 10.0


def _prof(v) -> float:
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    try:
        return float(v)   # handles Decimal from NUMERIC columns
    except (TypeError, ValueError):
        return _PROFICIENCY.get(str(v).lower().strip(), 0.0)


def _get_or_404(db, model, pk, label):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# STEP 19 — Capability Gap Analysis
# ══════════════════════════════════════════════════════════════════════════════

def analyze_gaps(db: Session, project_id: UUID, current_user: User) -> GapAnalysisResponse:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    proj = _get_or_404(db, Project, project_id, "Project")

    # Load problem requirements
    req_profile = db.scalar(
        select(ProblemRequirementProfile).where(
            ProblemRequirementProfile.problem_id == proj.problem_id
        )
    )
    reqs: list[ProblemRequirementCapability] = []
    if req_profile:
        reqs = list(db.scalars(
            select(ProblemRequirementCapability).where(
                ProblemRequirementCapability.requirement_profile_id == req_profile.requirement_profile_id
            )
        ).all())

    if not reqs:
        return GapAnalysisResponse(
            project_id=project_id,
            total_requirements=0,
            gaps_found=0,
            no_gap_count=0,
            gaps=[],
            generated_at=datetime.now(timezone.utc),
        )

    # Build available capability map from multiple sources
    available: dict[UUID, float] = {}

    # 1. Project capabilities
    for pc in db.scalars(select(ProjectCapability).where(ProjectCapability.project_id == project_id)).all():
        if pc.capability_id:
            lvl = _prof(pc.strength_level)
            available[pc.capability_id] = max(available.get(pc.capability_id, 0.0), lvl)

    # 2. HEI capabilities
    hei = db.get(HeiProfile, proj.hei_id)
    if hei:
        for hc in db.scalars(select(HeiCapability).where(HeiCapability.hei_id == hei.hei_id)).all():
            if hc.capability_id:
                lvl = _prof(hc.proficiency_level)
                available[hc.capability_id] = max(available.get(hc.capability_id, 0.0), lvl)

    # Load capability names
    cap_ids = {r.capability_id for r in reqs if r.capability_id}
    caps_by_id = {c.capability_id: c for c in db.scalars(
        select(Capability).where(Capability.capability_id.in_(cap_ids))
    ).all()}

    # Compute gaps and upsert records
    now = datetime.now(timezone.utc)
    gaps: list[GapDetail] = []
    no_gap = 0

    for req in reqs:
        if not req.capability_id:
            continue
        cap_name = caps_by_id[req.capability_id].name if req.capability_id in caps_by_id else str(req.capability_id)
        req_lvl = float(req.required_level or 1.0)
        avail_lvl = available.get(req.capability_id, 0.0)
        gap_lvl = max(0.0, req_lvl - avail_lvl)
        crit = float(req.criticality or 0.5)

        if gap_lvl <= 0:
            status = "Filled"
            rec_sup = None
            no_gap += 1
        elif avail_lvl > 0:
            status = "Partially Filled"
            rec_sup = f"Upgrade {cap_name} from level {avail_lvl:.0f} to {req_lvl:.0f}"
        else:
            status = "Open"
            rec_sup = f"Acquire {cap_name} capability at level {req_lvl:.0f}"

        # Upsert gap record
        existing = db.scalar(
            select(CapabilityGap).where(
                CapabilityGap.project_id == project_id,
                CapabilityGap.capability_id == req.capability_id,
            )
        )
        if existing:
            existing.required_level = req_lvl
            existing.available_level = avail_lvl
            existing.gap_level = gap_lvl
            existing.criticality = crit
            existing.recommended_support = rec_sup
            existing.status = status
        else:
            db.add(CapabilityGap(
                project_id=project_id,
                capability_id=req.capability_id,
                required_level=req_lvl,
                available_level=avail_lvl,
                gap_level=gap_lvl,
                criticality=crit,
                recommended_support=rec_sup,
                status=status,
                created_at=now,
                updated_at=now,
            ))

        if gap_lvl > 0:
            gaps.append(GapDetail(
                capability_id=str(req.capability_id),
                capability_name=cap_name,
                required_level=req_lvl,
                available_level=avail_lvl,
                gap_level=gap_lvl,
                criticality=crit,
                status=status,
                recommended_support=rec_sup,
            ))

    db.commit()

    return GapAnalysisResponse(
        project_id=project_id,
        total_requirements=len(reqs),
        gaps_found=len(gaps),
        no_gap_count=no_gap,
        gaps=gaps,
        generated_at=now,
    )


def list_gaps(db: Session, project_id: UUID) -> list[CapabilityGapResponse]:
    _get_or_404(db, Project, project_id, "Project")
    rows = list(db.scalars(select(CapabilityGap).where(CapabilityGap.project_id == project_id)).all())
    return [CapabilityGapResponse.model_validate(r) for r in rows]


def get_gap(db: Session, project_id: UUID, gap_id: UUID) -> CapabilityGapResponse:
    gap = _get_or_404(db, CapabilityGap, gap_id, "Capability gap")
    if gap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Capability gap not found")
    return CapabilityGapResponse.model_validate(gap)


def update_gap(db, project_id: UUID, gap_id: UUID, payload, current_user: User) -> CapabilityGapResponse:
    if current_user.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    gap = _get_or_404(db, CapabilityGap, gap_id, "Capability gap")
    if gap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Capability gap not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(gap, field, value)
    db.commit(); db.refresh(gap)
    return CapabilityGapResponse.model_validate(gap)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 20 — Partner Matching
# ══════════════════════════════════════════════════════════════════════════════

def run_partner_matching(
    db: Session, project_id: UUID, current_user: User, top_n: int = 10
) -> PartnerMatchResponse:
    if current_user.role not in {"Government Officer", "System Administrator",
                                  "HEI Administrator"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    proj = _get_or_404(db, Project, project_id, "Project")

    # Use capability gaps as primary requirements
    gaps = list(db.scalars(select(CapabilityGap).where(
        CapabilityGap.project_id == project_id,
        CapabilityGap.gap_level > 0,
    )).all())

    # Build gap map: cap_id -> gap record
    gap_map: dict[UUID, CapabilityGap] = {g.capability_id: g for g in gaps}
    gap_cap_ids = set(gap_map.keys())

    # Fall back to problem requirements if no gaps computed
    if not gap_map:
        req_profile = db.scalar(select(ProblemRequirementProfile).where(
            ProblemRequirementProfile.problem_id == proj.problem_id))
        if req_profile:
            for req in db.scalars(select(ProblemRequirementCapability).where(
                ProblemRequirementCapability.requirement_profile_id == req_profile.requirement_profile_id
            )).all():
                if req.capability_id:
                    # synthetic gap
                    g = CapabilityGap(
                        gap_id=req.requirement_capability_id,
                        project_id=project_id,
                        capability_id=req.capability_id,
                        required_level=req.required_level or 1.0,
                        available_level=0.0,
                        gap_level=req.required_level or 1.0,
                        criticality=req.criticality or 0.5,
                        status="Open",
                    )
                    gap_map[req.capability_id] = g
                    gap_cap_ids.add(req.capability_id)

    # Cap names
    caps_by_id = {}
    if gap_cap_ids:
        caps_by_id = {c.capability_id: c for c in db.scalars(
            select(Capability).where(Capability.capability_id.in_(gap_cap_ids))
        ).all()}

    # Load all partners
    partners = list(db.scalars(select(PartnerProfile)).all())
    if not partners:
        return PartnerMatchResponse(project_id=project_id, total_matches=0,
                                    matches=[], model_version=PARTNER_MATCH_MODEL_VERSION,
                                    generated_at=datetime.now(timezone.utc))

    partner_ids = [p.partner_id for p in partners]
    org_ids = [p.organization_id for p in partners]

    # Pre-load partner capabilities
    p_caps_all = list(db.scalars(
        select(PartnerCapability).where(PartnerCapability.partner_id.in_(partner_ids))
    ).all())
    p_cap_map: dict[UUID, list[PartnerCapability]] = {}
    for pc in p_caps_all:
        p_cap_map.setdefault(pc.partner_id, []).append(pc)

    # Pre-load offerings
    offerings_all = list(db.scalars(
        select(PartnerSupportOffering).where(
            PartnerSupportOffering.partner_id.in_(partner_ids),
            PartnerSupportOffering.status == "Active",
        )
    ).all())
    offering_map: dict[UUID, list[PartnerSupportOffering]] = {}
    for o in offerings_all:
        offering_map.setdefault(o.partner_id, []).append(o)

    # Pre-load orgs for location
    orgs_by_id = {o.organization_id: o for o in db.scalars(
        select(Organization).where(Organization.organization_id.in_(org_ids))
    ).all()}

    # HEI org for location comparison
    hei = db.get(HeiProfile, proj.hei_id)
    hei_org = db.get(Organization, hei.organization_id) if hei else None
    hei_state = (hei_org.state or "").lower() if hei_org else ""

    # Pre-load availability + constraints for partners
    avail_map: dict[UUID, list[Availability]] = {}
    for av in db.scalars(select(Availability).where(
        Availability.entity_id.in_(partner_ids)
    )).all():
        avail_map.setdefault(av.entity_id, []).append(av)

    constraint_map: dict[UUID, list[EntityConstraint]] = {}
    for ec in db.scalars(select(EntityConstraint).where(
        EntityConstraint.entity_id.in_(partner_ids)
    )).all():
        constraint_map.setdefault(ec.entity_id, []).append(ec)

    # Score each partner
    now = datetime.now(timezone.utc)
    raw = []
    for partner in partners:
        raw.append(_score_partner(
            partner=partner,
            org=orgs_by_id.get(partner.organization_id),
            gap_map=gap_map,
            caps_by_id=caps_by_id,
            p_caps=p_cap_map.get(partner.partner_id, []),
            offerings=offering_map.get(partner.partner_id, []),
            avail=avail_map.get(partner.partner_id, []),
            constraints=constraint_map.get(partner.partner_id, []),
            hei_state=hei_state,
        ))

    raw.sort(key=lambda r: (r["constraints_passed"], r["score"]), reverse=True)
    raw = raw[:top_n]

    results = []
    for rank, r in enumerate(raw, 1):
        # Delete stale snapshot
        old = db.scalar(select(PartnerMatch).where(
            PartnerMatch.project_id == project_id,
            PartnerMatch.partner_id == r["partner_id"],
        ))
        if old:
            db.delete(old); db.flush()

        snap = PartnerMatch(
            project_id=project_id,
            partner_id=r["partner_id"],
            match_score=round(r["score"], 4),
            rank=rank,
            matched_capabilities=[c.model_dump() for c in r["matched_caps"]],
            support_matches=[s.model_dump() for s in r["support_matches"]],
            unmet_requirements=[c.model_dump() for c in r["unmet_caps"]],
            constraint_results={"passed": r["constraints_passed"],
                                 "results": r["constraint_results"]},
            match_reasons=r["reasons"],
            model_version=PARTNER_MATCH_MODEL_VERSION,
            decision_status="Recommended",
            generated_at=now.replace(tzinfo=None),
            created_at=now,
        )
        db.add(snap); db.flush(); db.refresh(snap)

        results.append(PartnerMatchResult(
            match_id=snap.match_id,
            partner_id=r["partner_id"],
            partner_name=r["partner_name"],
            partner_type=r["partner_type"],
            rank=rank,
            match_score=round(r["score"], 2),
            score_breakdown=r["breakdown"],
            matched_capabilities=r["matched_caps"],
            unmet_requirements=r["unmet_caps"],
            support_matches=r["support_matches"],
            constraint_results=r["constraint_results"],
            match_reasons=r["reasons"],
            model_version=PARTNER_MATCH_MODEL_VERSION,
            constraints_passed=r["constraints_passed"],
        ))

    db.commit()
    return PartnerMatchResponse(project_id=project_id, total_matches=len(results),
                                matches=results, model_version=PARTNER_MATCH_MODEL_VERSION,
                                generated_at=now)


def get_partner_matches(db: Session, project_id: UUID, current_user: User) -> PartnerMatchResponse:
    _get_or_404(db, Project, project_id, "Project")
    rows = list(db.scalars(
        select(PartnerMatch).where(PartnerMatch.project_id == project_id).order_by(PartnerMatch.rank)
    ).all())

    results = []
    for row in rows:
        partner = db.get(PartnerProfile, row.partner_id)
        org = db.get(Organization, partner.organization_id) if partner else None
        results.append(PartnerMatchResult(
            match_id=row.match_id,
            partner_id=row.partner_id,
            partner_name=org.name if org else str(row.partner_id),
            partner_type=partner.partner_type if partner else "Unknown",
            rank=row.rank or 0,
            match_score=float(row.match_score or 0),
            score_breakdown={},
            matched_capabilities=[PartnerCapDetail(**c) for c in (row.matched_capabilities or [])],
            unmet_requirements=[PartnerCapDetail(**c) for c in (row.unmet_requirements or [])],
            support_matches=[SupportOfferingDetail(**s) for s in (row.support_matches or [])],
            constraint_results=(row.constraint_results or {}).get("results", []),
            match_reasons=row.match_reasons or [],
            model_version=row.model_version or PARTNER_MATCH_MODEL_VERSION,
            constraints_passed=(row.constraint_results or {}).get("passed", True),
        ))
    return PartnerMatchResponse(project_id=project_id, total_matches=len(results),
                                matches=results, model_version=PARTNER_MATCH_MODEL_VERSION,
                                generated_at=datetime.now(timezone.utc))


def _score_partner(*, partner, org, gap_map, caps_by_id, p_caps,
                   offerings, avail, constraints, hei_state) -> dict:
    reasons = []
    constraint_results = []
    constraints_passed = True

    for ec in constraints:
        if ec.severity in ("High", "Critical") and ec.constraint_type.lower() in (
            "unavailable", "geographic", "eligibility"
        ):
            constraint_results.append({"constraint_name": ec.constraint_type,
                                        "passed": False, "reason": ec.value or ec.constraint_type})
            constraints_passed = False
            reasons.append(f"Hard constraint: {ec.constraint_type}")
    if constraints_passed:
        constraint_results.append({"constraint_name": "Hard constraints",
                                    "passed": True, "reason": "No blocking constraints"})

    # Partner capability level map
    p_level: dict[UUID, float] = {}
    for pc in p_caps:
        if pc.capability_id:
            lvl = _prof(pc.proficiency_level)
            p_level[pc.capability_id] = max(p_level.get(pc.capability_id, 0.0), lvl)

    # Capability fit (40 pts)
    matched_caps, unmet_caps, cap_score = [], [], 0.0
    if gap_map:
        total_w = sum(max(float(g.criticality or 0.5), 0.01) for g in gap_map.values())
        weighted = 0.0
        for cap_id, gap in gap_map.items():
            cap_name = caps_by_id[cap_id].name if cap_id in caps_by_id else str(cap_id)
            req_lvl = float(gap.gap_level or gap.required_level or 1.0)
            w = max(float(gap.criticality or 0.5), 0.01)
            if cap_id in p_level:
                avail_lvl = p_level[cap_id]
                if avail_lvl >= req_lvl:
                    weighted += w
                    matched_caps.append(PartnerCapDetail(
                        capability_id=str(cap_id), capability_name=cap_name,
                        required_level=req_lvl, partner_level=avail_lvl, match_status="matched"))
                    reasons.append(f"Covers {cap_name}")
                else:
                    weighted += w * (avail_lvl / req_lvl)
                    matched_caps.append(PartnerCapDetail(
                        capability_id=str(cap_id), capability_name=cap_name,
                        required_level=req_lvl, partner_level=avail_lvl, match_status="partial"))
                    reasons.append(f"Partial {cap_name}")
            else:
                unmet_caps.append(PartnerCapDetail(
                    capability_id=str(cap_id), capability_name=cap_name,
                    required_level=req_lvl, partner_level=None, match_status="unmet"))
        cap_score = W_CAP * (weighted / total_w) if total_w else 0.0
    else:
        cap_score = W_CAP * 0.5

    # Support offering fit (25 pts)
    support_matches = []
    if offerings:
        support_score = W_SUP
        for o in offerings[:5]:
            support_matches.append(SupportOfferingDetail(
                offering_id=str(o.offering_id), support_type=o.support_type,
                title=o.title, status=o.status))
        reasons.append(f"{len(offerings)} support offering(s) available")
    else:
        support_score = 0.0

    # Domain relevance (15 pts) — simple: partner type matches
    domain_score = W_DOM * 0.5
    if partner.partner_type in ("Industry", "Research Institution") and matched_caps:
        domain_score = W_DOM
        reasons.append(f"Domain-relevant partner type: {partner.partner_type}")

    # Availability (10 pts)
    if avail:
        active_av = [a for a in avail if a.status.lower() in ("available", "partially available")]
        avail_score = W_AVAIL if active_av else W_AVAIL * 0.2
        if active_av:
            reasons.append("Partner availability confirmed")
    else:
        avail_score = W_AVAIL * 0.5

    # Location/constraints (10 pts)
    partner_state = (org.state or "").lower() if org else ""
    if hei_state and partner_state and hei_state == partner_state:
        con_score = W_CON
        reasons.append(f"Same state: {hei_state}")
    elif constraints_passed:
        con_score = W_CON * 0.5
    else:
        con_score = 0.0

    total = min(cap_score + support_score + domain_score + avail_score + con_score, 100.0)
    breakdown = {
        "capability_score": round(cap_score, 2), "support_score": round(support_score, 2),
        "domain_score": round(domain_score, 2), "availability_score": round(avail_score, 2),
        "constraint_score": round(con_score, 2), "total": round(total, 2),
    }

    return {
        "partner_id": partner.partner_id,
        "partner_name": org.name if org else str(partner.partner_id),
        "partner_type": partner.partner_type,
        "score": total,
        "breakdown": breakdown,
        "matched_caps": matched_caps,
        "unmet_caps": unmet_caps,
        "support_matches": support_matches,
        "constraint_results": constraint_results,
        "constraints_passed": constraints_passed,
        "reasons": reasons,
    }
