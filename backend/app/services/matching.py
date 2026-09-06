"""Explainable HEI Matching Service — Step 14.

Scoring weights
---------------
Capability / Skill Match   40 pts  (40%)
Domain Match               20 pts  (20%)
Resource Match             15 pts  (15%)
Location Match             10 pts  (10%)
Capacity Match             10 pts  (10%)
Eligibility / Other         5 pts  ( 5%)
                         ─────────
Total                     100 pts

The result is fully deterministic and explainable — no opaque AI score.
Each match record is persisted to hei_match as a snapshot.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.evidence import Availability, EntityConstraint
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.matching import HeiMatch, MODEL_VERSION
from app.models.organization import Organization
from app.models.problem import Problem
from app.models.user import User
from app.schemas.matching import (
    CapabilityMatchDetail,
    ConstraintResult,
    HeiMatchResponse,
    HeiMatchResult,
    ResourceMatchDetail,
    ScoreBreakdown,
)

# ── Scoring weights ────────────────────────────────────────────────────────────
W_CAPABILITY = 40.0
W_DOMAIN     = 20.0
W_RESOURCE   = 15.0
W_LOCATION   = 10.0
W_CAPACITY   = 10.0
W_OTHER      =  5.0

DEFAULT_TOP_N = 10

# ── Proficiency text → numeric mapping ────────────────────────────────────────
_PROFICIENCY_MAP: dict[str, float] = {
    "beginner":     1.0,
    "basic":        1.0,
    "intermediate": 2.0,
    "advanced":     3.0,
    "expert":       4.0,
}


def _prof_to_num(value: str | float | None) -> float:
    """Convert a proficiency string or numeric value to a 1–4 float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return _PROFICIENCY_MAP.get(str(value).lower().strip(), 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def run_hei_matching(
    db: Session,
    problem_id: UUID,
    current_user: User,
    top_n: int = DEFAULT_TOP_N,
) -> HeiMatchResponse:
    """Run the full matching pipeline and return ranked HEI results."""

    # ── 1. Load problem ───────────────────────────────────────────────────────
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    # ── 2. Load requirement profile + capabilities ────────────────────────────
    req_profile = db.scalar(
        select(ProblemRequirementProfile).where(
            ProblemRequirementProfile.problem_id == problem_id
        )
    )
    required_caps: list[ProblemRequirementCapability] = []
    if req_profile:
        required_caps = list(
            db.scalars(
                select(ProblemRequirementCapability).where(
                    ProblemRequirementCapability.requirement_profile_id
                    == req_profile.requirement_profile_id
                )
            ).all()
        )

    # Build set of required capability_ids with levels
    req_cap_map: dict[UUID, ProblemRequirementCapability] = {
        rc.capability_id: rc for rc in required_caps if rc.capability_id
    }
    req_cap_ids = set(req_cap_map.keys())

    # ── 3. Load all domain categories from problem ────────────────────────────
    domain_cap_ids: set[UUID] = set()
    for rc in required_caps:
        if rc.requirement_type == "Domain" and rc.capability_id:
            domain_cap_ids.add(rc.capability_id)

    # ── 4. Load all active HEIs ────────────────────────────────────────────────
    heis = list(db.scalars(select(HeiProfile)).all())
    if not heis:
        return HeiMatchResponse(
            problem_id=problem_id,
            problem_title=problem.title,
            total_matches=0,
            matches=[],
            model_version=MODEL_VERSION,
            generated_at=datetime.now(timezone.utc),
        )

    # Pre-load org data for HEIs (for name + location)
    hei_org_map: dict[UUID, Organization] = {}
    org_ids = {h.organization_id for h in heis}
    orgs = list(db.scalars(select(Organization).where(Organization.organization_id.in_(org_ids))).all())
    for org in orgs:
        hei_org_map[org.organization_id] = org

    # ── 5. Pre-load all capabilities once ────────────────────────────────────
    all_cap_ids = req_cap_ids | domain_cap_ids
    caps_by_id: dict[UUID, Capability] = {}
    if all_cap_ids:
        caps = list(db.scalars(select(Capability).where(Capability.capability_id.in_(all_cap_ids))).all())
        caps_by_id = {c.capability_id: c for c in caps}

    # ── 6. Pre-load HEI capabilities for all HEIs ────────────────────────────
    hei_ids = [h.hei_id for h in heis]
    hei_caps_all = list(
        db.scalars(select(HeiCapability).where(HeiCapability.hei_id.in_(hei_ids))).all()
    )
    # map: hei_id -> list of HeiCapability
    hei_cap_map: dict[UUID, list[HeiCapability]] = {}
    for hc in hei_caps_all:
        hei_cap_map.setdefault(hc.hei_id, []).append(hc)

    # ── 7. Pre-load faculty capabilities ─────────────────────────────────────
    faculty_all = list(
        db.scalars(select(FacultyExpertProfile).where(FacultyExpertProfile.hei_id.in_(hei_ids))).all()
    )
    faculty_ids = [f.faculty_id for f in faculty_all]
    faculty_cap_all: list[FacultyExpertCapability] = []
    if faculty_ids:
        faculty_cap_all = list(
            db.scalars(
                select(FacultyExpertCapability).where(
                    FacultyExpertCapability.faculty_id.in_(faculty_ids)
                )
            ).all()
        )
    # map: hei_id -> list of FacultyExpertCapability
    fac_hei_map: dict[UUID, UUID] = {f.faculty_id: f.hei_id for f in faculty_all}
    faculty_cap_hei: dict[UUID, list[FacultyExpertCapability]] = {}
    for fc in faculty_cap_all:
        hid = fac_hei_map.get(fc.faculty_id)
        if hid:
            faculty_cap_hei.setdefault(hid, []).append(fc)

    # ── 8. Pre-load resources + resource capabilities ─────────────────────────
    resources_all = list(
        db.scalars(select(InstitutionalResource).where(InstitutionalResource.hei_id.in_(hei_ids))).all()
    )
    resource_ids = [r.resource_id for r in resources_all]
    res_cap_all: list[ResourceCapability] = []
    if resource_ids:
        res_cap_all = list(
            db.scalars(
                select(ResourceCapability).where(
                    ResourceCapability.resource_id.in_(resource_ids)
                )
            ).all()
        )
    # map: hei_id -> list of InstitutionalResource
    res_hei_map: dict[UUID, UUID] = {r.resource_id: r.hei_id for r in resources_all}
    res_by_hei: dict[UUID, list[InstitutionalResource]] = {}
    for r in resources_all:
        res_by_hei.setdefault(r.hei_id, []).append(r)
    res_cap_hei: dict[UUID, list[ResourceCapability]] = {}
    for rc in res_cap_all:
        hid = res_hei_map.get(rc.resource_id)
        if hid:
            res_cap_hei.setdefault(hid, []).append(rc)

    # ── 9. Pre-load availability for all HEI entities ─────────────────────────
    entity_ids_all = set(hei_ids) | set(faculty_ids) | set(resource_ids)
    avail_all = list(
        db.scalars(
            select(Availability).where(Availability.entity_id.in_(entity_ids_all))
        ).all()
    )
    avail_map: dict[UUID, list[Availability]] = {}
    for av in avail_all:
        avail_map.setdefault(av.entity_id, []).append(av)

    # ── 10. Pre-load constraints for all HEI entities ─────────────────────────
    constraints_all = list(
        db.scalars(
            select(EntityConstraint).where(EntityConstraint.entity_id.in_(entity_ids_all))
        ).all()
    )
    constraint_map: dict[UUID, list[EntityConstraint]] = {}
    for ec in constraints_all:
        constraint_map.setdefault(ec.entity_id, []).append(ec)

    # ── 11. Score each HEI ────────────────────────────────────────────────────
    raw_results: list[dict] = []
    for hei in heis:
        result = _score_hei(
            hei=hei,
            org=hei_org_map.get(hei.organization_id),
            problem=problem,
            req_profile=req_profile,
            req_cap_map=req_cap_map,
            domain_cap_ids=domain_cap_ids,
            caps_by_id=caps_by_id,
            hei_caps=hei_cap_map.get(hei.hei_id, []),
            faculty_caps=faculty_cap_hei.get(hei.hei_id, []),
            resources=res_by_hei.get(hei.hei_id, []),
            resource_caps=res_cap_hei.get(hei.hei_id, []),
            avail_map=avail_map,
            constraint_map=constraint_map,
        )
        raw_results.append(result)

    # ── 12. Sort: constraints_passed desc, score desc ─────────────────────────
    raw_results.sort(key=lambda r: (r["constraints_passed"], r["score"]), reverse=True)
    raw_results = raw_results[:top_n]

    # ── 13. Assign ranks and persist ──────────────────────────────────────────
    now = datetime.now(timezone.utc)
    match_results: list[HeiMatchResult] = []

    for rank, r in enumerate(raw_results, start=1):
        # Upsert: delete previous snapshot for same problem+hei then insert fresh
        existing = db.scalar(
            select(HeiMatch).where(
                HeiMatch.problem_id == problem_id,
                HeiMatch.hei_id == r["hei_id"],
            )
        )
        if existing:
            db.delete(existing)
            db.flush()

        snapshot = HeiMatch(
            problem_id=problem_id,
            hei_id=r["hei_id"],
            match_score=round(r["score"], 4),
            rank=rank,
            matched_capabilities=[c.model_dump() for c in r["matched_caps"]],
            unmet_requirements=[c.model_dump() for c in r["unmet_caps"]],
            constraint_results={
                "results": [cr.model_dump() for cr in r["constraint_results"]],
                "passed": r["constraints_passed"],
            },
            match_reasons=r["reasons"],
            model_version=MODEL_VERSION,
            decision_status="Recommended",
            generated_at=now.replace(tzinfo=None),
            created_at=now,
        )
        db.add(snapshot)
        db.flush()
        db.refresh(snapshot)

        score_bd = r["score_breakdown"]
        match_results.append(
            HeiMatchResult(
                match_id=snapshot.match_id,
                hei_id=r["hei_id"],
                hei_name=r["hei_name"],
                match_score=round(r["score"], 2),
                rank=rank,
                score_breakdown=score_bd,
                matched_capabilities=r["matched_caps"],
                unmet_requirements=r["unmet_caps"],
                matched_resources=r["matched_resources"],
                constraint_results=r["constraint_results"],
                match_reasons=r["reasons"],
                model_version=MODEL_VERSION,
                constraints_passed=r["constraints_passed"],
            )
        )

    db.commit()

    return HeiMatchResponse(
        problem_id=problem_id,
        problem_title=problem.title,
        total_matches=len(match_results),
        matches=match_results,
        model_version=MODEL_VERSION,
        generated_at=now,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Per-HEI scoring
# ══════════════════════════════════════════════════════════════════════════════

def _score_hei(
    *,
    hei: HeiProfile,
    org: Organization | None,
    problem: Problem,
    req_profile: ProblemRequirementProfile | None,
    req_cap_map: dict[UUID, ProblemRequirementCapability],
    domain_cap_ids: set[UUID],
    caps_by_id: dict[UUID, Capability],
    hei_caps: list[HeiCapability],
    faculty_caps: list[FacultyExpertCapability],
    resources: list[InstitutionalResource],
    resource_caps: list[ResourceCapability],
    avail_map: dict[UUID, list[Availability]],
    constraint_map: dict[UUID, list[EntityConstraint]],
) -> dict:
    reasons: list[str] = []
    constraint_results: list[ConstraintResult] = []

    # ── Hard constraints ───────────────────────────────────────────────────────
    constraints_passed = True
    hei_constraints = constraint_map.get(hei.hei_id, [])
    for ec in hei_constraints:
        if ec.severity in ("High", "Critical") and ec.constraint_type.lower() in (
            "geographic", "eligibility", "unavailable",
        ):
            constraint_results.append(
                ConstraintResult(
                    constraint_name=ec.constraint_type,
                    passed=False,
                    reason=ec.value or f"{ec.constraint_type} hard constraint active",
                )
            )
            constraints_passed = False
            reasons.append(f"Hard constraint failed: {ec.constraint_type}")
    if constraints_passed:
        constraint_results.append(
            ConstraintResult(
                constraint_name="Hard constraints",
                passed=True,
                reason="No blocking constraints found",
            )
        )

    # ── Build HEI capability lookup (cap_id -> best level across sources) ─────
    hei_level: dict[UUID, tuple[float, str]] = {}  # cap_id -> (level, source)

    for hc in hei_caps:
        if hc.capability_id:
            lvl = _prof_to_num(hc.proficiency_level)
            if lvl > hei_level.get(hc.capability_id, (0.0, ""))[0]:
                hei_level[hc.capability_id] = (lvl, "hei")

    for fc in faculty_caps:
        if fc.capability_id:
            lvl = _prof_to_num(fc.proficiency_level)
            if lvl > hei_level.get(fc.capability_id, (0.0, ""))[0]:
                hei_level[fc.capability_id] = (lvl, "faculty")

    for rc in resource_caps:
        if rc.capability_id:
            lvl = _prof_to_num(rc.proficiency_level)
            if lvl > hei_level.get(rc.capability_id, (0.0, ""))[0]:
                hei_level[rc.capability_id] = (lvl, "resource")

    # ── Capability scoring (40 pts) ────────────────────────────────────────────
    matched_caps: list[CapabilityMatchDetail] = []
    unmet_caps: list[CapabilityMatchDetail] = []

    if req_cap_map:
        total_weight = sum(
            max(rc.criticality or 0.5, 0.01) for rc in req_cap_map.values()
        )
        weighted_score = 0.0

        for cap_id, req in req_cap_map.items():
            cap_obj = caps_by_id.get(cap_id)
            cap_name = cap_obj.name if cap_obj else str(cap_id)
            req_lvl = req.required_level or 1.0
            weight = max(req.criticality or 0.5, 0.01)

            if cap_id in hei_level:
                avail_lvl, source = hei_level[cap_id]
                if avail_lvl >= req_lvl:
                    status = "matched"
                    contrib = weight
                    reasons.append(f"Strong {cap_name} capability (level {avail_lvl:.0f})")
                else:
                    status = "partial"
                    contrib = weight * (avail_lvl / req_lvl)
                    reasons.append(f"Partial {cap_name} match ({avail_lvl:.0f}/{req_lvl:.0f})")
                weighted_score += contrib
                detail = CapabilityMatchDetail(
                    capability_id=str(cap_id),
                    capability_name=cap_name,
                    required_level=req_lvl,
                    available_level=avail_lvl,
                    match_status=status,
                    source=source,
                )
                if status == "matched":
                    matched_caps.append(detail)
                else:
                    unmet_caps.append(detail)
            else:
                unmet_caps.append(CapabilityMatchDetail(
                    capability_id=str(cap_id),
                    capability_name=cap_name,
                    required_level=req_lvl,
                    available_level=None,
                    match_status="unmet",
                    source="none",
                ))
                reasons.append(f"Missing required capability: {cap_name}")

        cap_score = W_CAPABILITY * (weighted_score / total_weight) if total_weight else 0.0
    else:
        cap_score = W_CAPABILITY * 0.5  # no requirements specified → neutral
        reasons.append("No specific capability requirements defined")

    # ── Domain scoring (20 pts) ────────────────────────────────────────────────
    if domain_cap_ids:
        matched_domains = domain_cap_ids & set(hei_level.keys())
        domain_ratio = len(matched_domains) / len(domain_cap_ids)
        domain_score = W_DOMAIN * domain_ratio
        if matched_domains:
            names = [
                caps_by_id[d].name if d in caps_by_id else str(d)
                for d in matched_domains
            ]
            reasons.append(f"Relevant domain expertise: {', '.join(names)}")
    else:
        domain_score = W_DOMAIN * 0.5
        reasons.append("Problem domain not specified — neutral domain score")

    # ── Resource scoring (15 pts) ──────────────────────────────────────────────
    matched_resources: list[ResourceMatchDetail] = []
    resource_cap_ids = {rc.capability_id for rc in resource_caps if rc.capability_id}

    if req_cap_map:
        resource_req_ids = {
            cap_id for cap_id, req in req_cap_map.items()
            if req.requirement_type == "Resource"
        }
        if resource_req_ids:
            matched_res_ids = resource_req_ids & resource_cap_ids
            res_ratio = len(matched_res_ids) / len(resource_req_ids)
            resource_score = W_RESOURCE * res_ratio
        else:
            resource_score = W_RESOURCE * 0.5
    else:
        resource_score = W_RESOURCE * 0.5

    for res in resources:
        cap_ids_for_res = {rc.capability_id for rc in resource_caps if rc.resource_id == res.resource_id}
        matched = bool(cap_ids_for_res & req_cap_map.keys()) if req_cap_map else False
        matched_resources.append(ResourceMatchDetail(
            resource_id=str(res.resource_id),
            resource_name=res.name,
            resource_type=res.resource_type,
            matched=matched,
        ))

    if any(r.matched for r in matched_resources):
        matched_names = [r.resource_name for r in matched_resources if r.matched]
        reasons.append(f"Required resources available: {', '.join(matched_names[:3])}")

    # ── Location scoring (10 pts) ──────────────────────────────────────────────
    problem_loc = (problem.location or "").lower().strip()
    if org:
        hei_state = (org.state or "").lower().strip()
        hei_district = (org.district or "").lower().strip()
        hei_loc = f"{hei_state} {hei_district}".strip()
    else:
        hei_loc = ""

    if not problem_loc or not hei_loc:
        location_score = W_LOCATION * 0.5
        reasons.append("Location information unavailable — neutral location score")
    else:
        # Exact token overlap
        prob_tokens = set(problem_loc.split())
        hei_tokens = set(hei_loc.split())
        overlap = prob_tokens & hei_tokens
        if overlap:
            location_score = W_LOCATION
            reasons.append(f"Location match: {', '.join(overlap)}")
        else:
            location_score = W_LOCATION * 0.2
            # partial: same state
            if hei_state and hei_state in problem_loc:
                location_score = W_LOCATION * 0.7
                reasons.append(f"Same state: {hei_state}")

    # ── Capacity / Availability scoring (10 pts) ───────────────────────────────
    hei_avail = avail_map.get(hei.hei_id, [])
    if not hei_avail:
        # check faculty/resource availability
        fac_avail = any(avail_map.get(fid) for fid in
                        [fc.faculty_id for fc in faculty_caps[:5]])
        res_avail = any(avail_map.get(rid) for rid in
                        [res.resource_id for res in resources[:5]])
        if fac_avail or res_avail:
            capacity_score = W_CAPACITY * 0.8
            reasons.append("Faculty/resource availability confirmed")
        else:
            capacity_score = W_CAPACITY * 0.5
            reasons.append("Availability status unknown")
    else:
        active = [a for a in hei_avail if a.status.lower() in ("available", "partially available")]
        if active:
            capacity_score = W_CAPACITY
            reasons.append("HEI capacity available")
        else:
            capacity_score = W_CAPACITY * 0.2
            reasons.append("HEI marked as unavailable or fully booked")
            constraint_results.append(ConstraintResult(
                constraint_name="Availability",
                passed=False,
                reason="HEI availability status is not Available",
            ))

    # ── Other / eligibility (5 pts) ───────────────────────────────────────────
    other_score = W_OTHER * 0.5  # neutral default for MVP
    if req_profile and req_profile.eligibility_requirements:
        other_score = W_OTHER * 0.5
    else:
        other_score = W_OTHER

    # ── Total ─────────────────────────────────────────────────────────────────
    total = cap_score + domain_score + resource_score + location_score + capacity_score + other_score
    total = min(max(total, 0.0), 100.0)

    score_breakdown = ScoreBreakdown(
        capability_score=round(cap_score, 2),
        domain_score=round(domain_score, 2),
        resource_score=round(resource_score, 2),
        location_score=round(location_score, 2),
        capacity_score=round(capacity_score, 2),
        other_score=round(other_score, 2),
        total=round(total, 2),
    )

    hei_name = org.name if org else f"HEI {hei.hei_id}"

    return {
        "hei_id": hei.hei_id,
        "hei_name": hei_name,
        "score": total,
        "score_breakdown": score_breakdown,
        "matched_caps": matched_caps,
        "unmet_caps": unmet_caps,
        "matched_resources": matched_resources,
        "constraint_results": constraint_results,
        "constraints_passed": constraints_passed,
        "reasons": reasons,
    }
