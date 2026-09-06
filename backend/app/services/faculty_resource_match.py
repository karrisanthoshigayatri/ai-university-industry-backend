"""Faculty / Resource contextual matching service — Step 15.

Scoring weights
---------------
Capability Match      50 pts  (50%)
Domain Relevance      20 pts  (20%)
Evidence / Experience 10 pts  (10%)
Availability          10 pts  (10%)
Constraints / Other   10 pts  (10%)
                    ─────────
Total               100 pts

Fully deterministic — no opaque AI score.
Results are persisted to faculty_resource_match as snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import ProblemRequirementCapability, ProblemRequirementProfile
from app.models.capability import Capability
from app.models.evidence import Availability, EntityConstraint
from app.models.faculty_resource_match import FR_MODEL_VERSION, FacultyResourceMatch
from app.models.hei import (
    FacultyExpertCapability,
    FacultyExpertProfile,
    HeiCapability,
    HeiProfile,
    InstitutionalResource,
    ResourceCapability,
)
from app.models.problem import Problem
from app.models.user import User
from app.schemas.faculty_resource_match import (
    FRCapabilityDetail,
    FRConstraintResult,
    FRScoreBreakdown,
    FacultyResourceMatchResponse,
    FacultyResourceMatchResult,
)

# Scoring weights
W_CAPABILITY  = 50.0
W_DOMAIN      = 20.0
W_EVIDENCE    = 10.0
W_AVAIL       = 10.0
W_CONSTRAINT  = 10.0

DEFAULT_TOP_N = 10

_PROFICIENCY_MAP: dict[str, float] = {
    "beginner": 1.0, "basic": 1.0,
    "intermediate": 2.0,
    "advanced": 3.0,
    "expert": 4.0,
}

# Problem statuses that allow matching
_VALID_STATUSES = {
    "Validated", "Matched", "Accepted", "Active",
}


def _prof(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return _PROFICIENCY_MAP.get(str(value).lower().strip(), 0.0)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def run_fr_matching(
    db: Session,
    problem_id: UUID,
    current_user: User,
    hei_id: UUID | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> FacultyResourceMatchResponse:

    # 1. Load problem
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    # 2. Require validated problem
    if problem.current_status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Problem status is '{problem.current_status}'. "
                f"Matching requires one of: {sorted(_VALID_STATUSES)}"
            ),
        )

    # 3. Load requirement profile
    req_profile = db.scalar(
        select(ProblemRequirementProfile).where(
            ProblemRequirementProfile.problem_id == problem_id
        )
    )
    req_caps: list[ProblemRequirementCapability] = []
    if req_profile:
        req_caps = list(db.scalars(
            select(ProblemRequirementCapability).where(
                ProblemRequirementCapability.requirement_profile_id
                == req_profile.requirement_profile_id
            )
        ).all())

    req_cap_map: dict[UUID, ProblemRequirementCapability] = {
        rc.capability_id: rc for rc in req_caps if rc.capability_id
    }
    domain_cap_ids: set[UUID] = {
        rc.capability_id for rc in req_caps
        if rc.requirement_type == "Domain" and rc.capability_id
    }

    # 4. Select HEIs to search
    if hei_id:
        hei = db.get(HeiProfile, hei_id)
        if hei is None:
            raise HTTPException(status_code=404, detail="HEI not found")
        heis = [hei]
    else:
        heis = list(db.scalars(select(HeiProfile)).all())

    if not heis:
        return _empty_response(problem_id, problem.title, hei_id)

    hei_ids = [h.hei_id for h in heis]

    # 5. Pre-load all capability names
    all_cap_ids = set(req_cap_map.keys()) | domain_cap_ids
    caps_by_id: dict[UUID, Capability] = {}
    if all_cap_ids:
        caps_by_id = {
            c.capability_id: c
            for c in db.scalars(
                select(Capability).where(Capability.capability_id.in_(all_cap_ids))
            ).all()
        }

    # 6. Pre-load faculty + capabilities
    faculty_all = list(db.scalars(
        select(FacultyExpertProfile).where(FacultyExpertProfile.hei_id.in_(hei_ids))
    ).all())
    faculty_ids = [f.faculty_id for f in faculty_all]
    fac_by_id = {f.faculty_id: f for f in faculty_all}

    fac_caps_all: list[FacultyExpertCapability] = []
    if faculty_ids:
        fac_caps_all = list(db.scalars(
            select(FacultyExpertCapability).where(
                FacultyExpertCapability.faculty_id.in_(faculty_ids)
            )
        ).all())
    # map: faculty_id -> list[FacultyExpertCapability]
    fac_cap_map: dict[UUID, list[FacultyExpertCapability]] = {}
    for fc in fac_caps_all:
        fac_cap_map.setdefault(fc.faculty_id, []).append(fc)

    # 7. Pre-load resources + capabilities
    resources_all = list(db.scalars(
        select(InstitutionalResource).where(InstitutionalResource.hei_id.in_(hei_ids))
    ).all())
    resource_ids = [r.resource_id for r in resources_all]
    res_by_id = {r.resource_id: r for r in resources_all}

    res_caps_all: list[ResourceCapability] = []
    if resource_ids:
        res_caps_all = list(db.scalars(
            select(ResourceCapability).where(
                ResourceCapability.resource_id.in_(resource_ids)
            )
        ).all())
    res_cap_map: dict[UUID, list[ResourceCapability]] = {}
    for rc in res_caps_all:
        res_cap_map.setdefault(rc.resource_id, []).append(rc)

    # 8. Pre-load availability and constraints
    entity_ids = set(faculty_ids) | set(resource_ids)
    avail_map: dict[UUID, list[Availability]] = {}
    if entity_ids:
        for av in db.scalars(
            select(Availability).where(Availability.entity_id.in_(entity_ids))
        ).all():
            avail_map.setdefault(av.entity_id, []).append(av)

    constraint_map: dict[UUID, list[EntityConstraint]] = {}
    if entity_ids:
        for ec in db.scalars(
            select(EntityConstraint).where(EntityConstraint.entity_id.in_(entity_ids))
        ).all():
            constraint_map.setdefault(ec.entity_id, []).append(ec)

    # 9. Score every faculty member
    raw: list[dict] = []
    for fac in faculty_all:
        raw.append(_score_faculty(
            fac=fac,
            req_cap_map=req_cap_map,
            domain_cap_ids=domain_cap_ids,
            caps_by_id=caps_by_id,
            fac_caps=fac_cap_map.get(fac.faculty_id, []),
            avail=avail_map.get(fac.faculty_id, []),
            constraints=constraint_map.get(fac.faculty_id, []),
        ))

    # 10. Score every resource
    for res in resources_all:
        raw.append(_score_resource(
            res=res,
            req_cap_map=req_cap_map,
            domain_cap_ids=domain_cap_ids,
            caps_by_id=caps_by_id,
            res_caps=res_cap_map.get(res.resource_id, []),
            avail=avail_map.get(res.resource_id, []),
            constraints=constraint_map.get(res.resource_id, []),
        ))

    # 11. Sort: constraints_passed desc, score desc; trim
    raw.sort(key=lambda r: (r["constraints_passed"], r["score"]), reverse=True)
    raw = raw[:top_n]

    # 12. Persist + build response
    now = datetime.now(timezone.utc)
    results: list[FacultyResourceMatchResult] = []

    for rank, r in enumerate(raw, start=1):
        # Upsert: delete stale snapshot for same problem+faculty or problem+resource
        _delete_stale(db, problem_id, r.get("faculty_id"), r.get("resource_id"))

        snap = FacultyResourceMatch(
            problem_id=problem_id,
            hei_id=r["hei_id"],
            faculty_id=r.get("faculty_id"),
            resource_id=r.get("resource_id"),
            match_type=r["match_type"],
            match_score=round(r["score"], 4),
            matched_capabilities=[c.model_dump() for c in r["matched_caps"]],
            unmet_requirements=[c.model_dump() for c in r["unmet_caps"]],
            constraint_results={
                "passed": r["constraints_passed"],
                "results": [cr.model_dump() for cr in r["constraint_results"]],
            },
            match_reasons=r["reasons"],
            model_version=FR_MODEL_VERSION,
            generated_at=now.replace(tzinfo=None),
            created_at=now,
        )
        db.add(snap)
        db.flush()
        db.refresh(snap)

        fac_obj = fac_by_id.get(r["faculty_id"]) if r.get("faculty_id") else None
        res_obj = res_by_id.get(r["resource_id"]) if r.get("resource_id") else None

        results.append(FacultyResourceMatchResult(
            match_id=snap.match_id,
            hei_id=r["hei_id"],
            match_type=r["match_type"],
            faculty_id=r.get("faculty_id"),
            faculty_name=fac_obj.designation if fac_obj else None,
            faculty_designation=fac_obj.designation if fac_obj else None,
            resource_id=r.get("resource_id"),
            resource_name=res_obj.name if res_obj else None,
            resource_type=res_obj.resource_type if res_obj else None,
            rank=rank,
            match_score=round(r["score"], 2),
            score_breakdown=r["score_breakdown"],
            matched_capabilities=r["matched_caps"],
            unmet_requirements=r["unmet_caps"],
            constraint_results=r["constraint_results"],
            match_reasons=r["reasons"],
            model_version=FR_MODEL_VERSION,
            constraints_passed=r["constraints_passed"],
        ))

    db.commit()

    fac_count = sum(1 for r in results if r.match_type == "Faculty")
    res_count = sum(1 for r in results if r.match_type == "Resource")

    return FacultyResourceMatchResponse(
        problem_id=problem_id,
        problem_title=problem.title,
        hei_id=hei_id,
        total_matches=len(results),
        faculty_matches=fac_count,
        resource_matches=res_count,
        matches=results,
        model_version=FR_MODEL_VERSION,
        generated_at=now,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Faculty scoring
# ══════════════════════════════════════════════════════════════════════════════

def _score_faculty(
    *,
    fac: FacultyExpertProfile,
    req_cap_map: dict[UUID, ProblemRequirementCapability],
    domain_cap_ids: set[UUID],
    caps_by_id: dict[UUID, Capability],
    fac_caps: list[FacultyExpertCapability],
    avail: list[Availability],
    constraints: list[EntityConstraint],
) -> dict:
    reasons: list[str] = []
    constraint_results: list[FRConstraintResult] = []
    constraints_passed = True

    # Hard constraints
    for ec in constraints:
        if ec.severity in ("High", "Critical") and ec.constraint_type.lower() in (
            "unavailable", "geographic", "eligibility"
        ):
            constraint_results.append(FRConstraintResult(
                constraint_name=ec.constraint_type,
                passed=False,
                reason=ec.value or f"{ec.constraint_type} hard constraint",
            ))
            constraints_passed = False
            reasons.append(f"Hard constraint failed: {ec.constraint_type}")

    if constraints_passed:
        constraint_results.append(FRConstraintResult(
            constraint_name="Hard constraints",
            passed=True,
            reason="No blocking constraints",
        ))

    # Build capability level map from faculty
    fac_level: dict[UUID, float] = {}
    for fc in fac_caps:
        if fc.capability_id:
            lvl = _prof(fc.proficiency_level)
            fac_level[fc.capability_id] = max(fac_level.get(fc.capability_id, 0.0), lvl)

    # Capability score (50 pts)
    matched_caps, unmet_caps, cap_score = _calc_cap_score(
        req_cap_map, fac_level, caps_by_id, reasons
    )

    # Domain score (20 pts)
    domain_score = _calc_domain_score(domain_cap_ids, fac_level, caps_by_id, reasons)

    # Evidence / experience score (10 pts)
    has_evidence = any(
        fc.evidence_description or fc.evidence_id
        for fc in fac_caps
        if fc.capability_id in req_cap_map
    )
    has_experience = bool(fac.experience_years and fac.experience_years > 0)
    if has_evidence and has_experience:
        evidence_score = W_EVIDENCE
        reasons.append(f"Documented evidence and {fac.experience_years} years experience")
    elif has_evidence or has_experience:
        evidence_score = W_EVIDENCE * 0.6
        if has_experience:
            reasons.append(f"{fac.experience_years} years of experience")
        else:
            reasons.append("Supporting evidence documentation present")
    else:
        evidence_score = W_EVIDENCE * 0.2

    # Availability score (10 pts)
    avail_score = _calc_avail_score(avail, reasons)

    # Constraint score (10 pts)
    c_score = W_CONSTRAINT if constraints_passed else 0.0

    total = min(cap_score + domain_score + evidence_score + avail_score + c_score, 100.0)

    return {
        "match_type": "Faculty",
        "hei_id": fac.hei_id,
        "faculty_id": fac.faculty_id,
        "resource_id": None,
        "score": total,
        "score_breakdown": FRScoreBreakdown(
            capability_score=round(cap_score, 2),
            domain_score=round(domain_score, 2),
            evidence_score=round(evidence_score, 2),
            availability_score=round(avail_score, 2),
            constraint_score=round(c_score, 2),
            total=round(total, 2),
        ),
        "matched_caps": matched_caps,
        "unmet_caps": unmet_caps,
        "constraint_results": constraint_results,
        "constraints_passed": constraints_passed,
        "reasons": reasons,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Resource scoring
# ══════════════════════════════════════════════════════════════════════════════

def _score_resource(
    *,
    res: InstitutionalResource,
    req_cap_map: dict[UUID, ProblemRequirementCapability],
    domain_cap_ids: set[UUID],
    caps_by_id: dict[UUID, Capability],
    res_caps: list[ResourceCapability],
    avail: list[Availability],
    constraints: list[EntityConstraint],
) -> dict:
    reasons: list[str] = []
    constraint_results: list[FRConstraintResult] = []
    constraints_passed = True

    for ec in constraints:
        if ec.severity in ("High", "Critical") and ec.constraint_type.lower() in (
            "unavailable", "geographic", "eligibility", "capacity"
        ):
            constraint_results.append(FRConstraintResult(
                constraint_name=ec.constraint_type,
                passed=False,
                reason=ec.value or f"{ec.constraint_type} constraint",
            ))
            constraints_passed = False
            reasons.append(f"Hard constraint: {ec.constraint_type}")

    if constraints_passed:
        constraint_results.append(FRConstraintResult(
            constraint_name="Hard constraints",
            passed=True,
            reason="No blocking constraints",
        ))

    # Build capability level map from resource
    res_level: dict[UUID, float] = {}
    for rc in res_caps:
        if rc.capability_id:
            lvl = _prof(rc.proficiency_level)
            res_level[rc.capability_id] = max(res_level.get(rc.capability_id, 0.0), lvl)

    # Capability score (50 pts)
    matched_caps, unmet_caps, cap_score = _calc_cap_score(
        req_cap_map, res_level, caps_by_id, reasons
    )

    # Domain score (20 pts)
    domain_score = _calc_domain_score(domain_cap_ids, res_level, caps_by_id, reasons)

    # Evidence score — resources don't have experience, use evidence descriptions
    has_ev = any(rc.evidence_description for rc in res_caps if rc.capability_id in req_cap_map)
    evidence_score = W_EVIDENCE * 0.7 if has_ev else W_EVIDENCE * 0.3
    if has_ev:
        reasons.append(f"Resource '{res.name}' has supporting evidence")

    # Availability (10 pts)
    # Also consider the resource's own availability_status field
    res_avail_status = (res.availability_status or "").lower()
    if res_avail_status == "available":
        avail_score = W_AVAIL
        reasons.append(f"Resource '{res.name}' is Available")
    elif res_avail_status in ("partially available",):
        avail_score = W_AVAIL * 0.5
        reasons.append(f"Resource '{res.name}' is Partially Available")
    else:
        avail_score = _calc_avail_score(avail, reasons)

    # Constraint score
    c_score = W_CONSTRAINT if constraints_passed else 0.0

    total = min(cap_score + domain_score + evidence_score + avail_score + c_score, 100.0)

    return {
        "match_type": "Resource",
        "hei_id": res.hei_id,
        "faculty_id": None,
        "resource_id": res.resource_id,
        "score": total,
        "score_breakdown": FRScoreBreakdown(
            capability_score=round(cap_score, 2),
            domain_score=round(domain_score, 2),
            evidence_score=round(evidence_score, 2),
            availability_score=round(avail_score, 2),
            constraint_score=round(c_score, 2),
            total=round(total, 2),
        ),
        "matched_caps": matched_caps,
        "unmet_caps": unmet_caps,
        "constraint_results": constraint_results,
        "constraints_passed": constraints_passed,
        "reasons": reasons,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Shared sub-scorers
# ══════════════════════════════════════════════════════════════════════════════

def _calc_cap_score(
    req_cap_map: dict[UUID, ProblemRequirementCapability],
    level_map: dict[UUID, float],
    caps_by_id: dict[UUID, Capability],
    reasons: list[str],
) -> tuple[list[FRCapabilityDetail], list[FRCapabilityDetail], float]:
    matched: list[FRCapabilityDetail] = []
    unmet: list[FRCapabilityDetail] = []

    if not req_cap_map:
        return matched, unmet, W_CAPABILITY * 0.5

    total_w = sum(max(rc.criticality or 0.5, 0.01) for rc in req_cap_map.values())
    weighted = 0.0

    for cap_id, req in req_cap_map.items():
        cap_name = caps_by_id[cap_id].name if cap_id in caps_by_id else str(cap_id)
        req_lvl = req.required_level or 1.0
        w = max(req.criticality or 0.5, 0.01)

        if cap_id in level_map:
            avail_lvl = level_map[cap_id]
            if avail_lvl >= req_lvl:
                status = "matched"
                weighted += w
                reasons.append(f"Meets {cap_name} (level {avail_lvl:.0f})")
            else:
                status = "partial"
                weighted += w * (avail_lvl / req_lvl)
                reasons.append(f"Partial {cap_name} ({avail_lvl:.0f}/{req_lvl:.0f})")
            detail = FRCapabilityDetail(
                capability_id=str(cap_id),
                capability_name=cap_name,
                required_level=req_lvl,
                available_level=avail_lvl,
                match_status=status,
            )
            if status == "matched":
                matched.append(detail)
            else:
                unmet.append(detail)
        else:
            unmet.append(FRCapabilityDetail(
                capability_id=str(cap_id),
                capability_name=cap_name,
                required_level=req_lvl,
                available_level=None,
                match_status="unmet",
            ))
            reasons.append(f"Missing: {cap_name}")

    score = W_CAPABILITY * (weighted / total_w) if total_w else 0.0
    return matched, unmet, score


def _calc_domain_score(
    domain_cap_ids: set[UUID],
    level_map: dict[UUID, float],
    caps_by_id: dict[UUID, Capability],
    reasons: list[str],
) -> float:
    if not domain_cap_ids:
        return W_DOMAIN * 0.5
    matched_d = domain_cap_ids & set(level_map.keys())
    ratio = len(matched_d) / len(domain_cap_ids)
    if matched_d:
        names = [caps_by_id[d].name for d in matched_d if d in caps_by_id]
        reasons.append(f"Domain match: {', '.join(names[:3])}")
    return W_DOMAIN * ratio


def _calc_avail_score(avail: list[Availability], reasons: list[str]) -> float:
    if not avail:
        return W_AVAIL * 0.5
    active = [a for a in avail if a.status.lower() in ("available", "partially available")]
    if active:
        reasons.append("Availability confirmed")
        return W_AVAIL
    reasons.append("Marked unavailable or no availability window")
    return W_AVAIL * 0.1


def _delete_stale(
    db: Session,
    problem_id: UUID,
    faculty_id: UUID | None,
    resource_id: UUID | None,
) -> None:
    if faculty_id:
        existing = db.scalar(
            select(FacultyResourceMatch).where(
                FacultyResourceMatch.problem_id == problem_id,
                FacultyResourceMatch.faculty_id == faculty_id,
            )
        )
        if existing:
            db.delete(existing)
            db.flush()
    if resource_id:
        existing = db.scalar(
            select(FacultyResourceMatch).where(
                FacultyResourceMatch.problem_id == problem_id,
                FacultyResourceMatch.resource_id == resource_id,
            )
        )
        if existing:
            db.delete(existing)
            db.flush()


def _empty_response(problem_id: UUID, title: str, hei_id: UUID | None) -> FacultyResourceMatchResponse:
    now = datetime.now(timezone.utc)
    return FacultyResourceMatchResponse(
        problem_id=problem_id,
        problem_title=title,
        hei_id=hei_id,
        total_matches=0,
        faculty_matches=0,
        resource_matches=0,
        matches=[],
        model_version=FR_MODEL_VERSION,
        generated_at=now,
    )
