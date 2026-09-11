#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.2 systems engineering (SE) planning
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering process is planned in a System Engineering Plan
(SEP) that lays out the SE activities and the project's technical
review milestones, and that integrates every technical discipline's
own plan (product assurance, verification, configuration management,
software engineering, assembly/integration/verification) into that
single schedule so each discipline's inputs are ready before the
review milestone that consumes them. This module implements the
canonical review-milestone sequencing check, the discipline-plan
integration and delivery-timing check against that sequence, and the
required-discipline coverage check; it does not define the SEP
document template itself or the discipline plans' internal content.
"""

from datetime import date

# Canonical ECSS-E-ST-10C technical review sequence used to phase SE
# activities against the project schedule (simplified from clause 5.6.2
# guidance: System Requirements Review, Preliminary Design Review,
# Critical Design Review, Qualification Review, Acceptance Review).
CANONICAL_MILESTONES = ("SRR", "PDR", "CDR", "QR", "AR")
MILESTONE_ORDER = {milestone: index for index, milestone in enumerate(CANONICAL_MILESTONES)}

# Technical discipline plans that clause 5.6.2 requires the SE plan to
# integrate into the project schedule.
REQUIRED_DISCIPLINES = frozenset(
    {
        "product_assurance",
        "verification",
        "configuration_management",
        "software_engineering",
        "aiv",
    }
)


def milestone_sequence_index(milestone_id):
    """Canonical order index (0-based) of a review milestone id.
    Raises ValueError for a milestone id outside CANONICAL_MILESTONES."""
    if milestone_id not in MILESTONE_ORDER:
        raise ValueError(
            "unrecognized SE review milestone %r under E-ST-10C clause 5.6.2"
            % (milestone_id,)
        )
    return MILESTONE_ORDER[milestone_id]


def parse_plan_date(value):
    """ISO 'YYYY-MM-DD' string (or a date instance) to a date. Raises
    ValueError for anything else, including a malformed string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("plan date must be an ISO date string or a date, got %r" % (value,))


def validate_milestone_order(milestones):
    """Sequence-violation list (empty if compliant) for a project's
    planned review milestones. milestones: iterable of
    {"milestone_id": str, "planned_date": str|date}. Flags a duplicate
    milestone_id and flags a pair of consecutive (in canonical order)
    milestones whose planned dates run backwards. Raises ValueError for
    an unrecognized milestone_id or an unparseable planned_date. Does
    not mutate milestones."""
    seen = {}
    violations = []
    for entry in milestones:
        milestone_id = entry["milestone_id"]
        milestone_sequence_index(milestone_id)
        planned_date = parse_plan_date(entry["planned_date"])
        if milestone_id in seen:
            violations.append(
                {"issue": "duplicate_milestone", "milestone": milestone_id}
            )
            continue
        seen[milestone_id] = planned_date

    ordered_ids = sorted(seen, key=milestone_sequence_index)
    for earlier, later in zip(ordered_ids, ordered_ids[1:]):
        if seen[later] < seen[earlier]:
            violations.append(
                {
                    "issue": "milestone_out_of_sequence",
                    "earlier_milestone": earlier,
                    "later_milestone": later,
                    "earlier_date": seen[earlier].isoformat(),
                    "later_date": seen[later].isoformat(),
                }
            )
    return violations


def discipline_integration_violations(discipline_plans, milestones):
    """Integration-violation list (empty if compliant) checking each
    discipline plan is linked to a planned review milestone and
    delivered on or before that milestone's date.

    discipline_plans: iterable of {"discipline_id": str,
    "contributes_to_milestone": str, "delivery_date": str|date}.
    milestones: iterable of {"milestone_id": str, "planned_date":
    str|date} (same shape as validate_milestone_order's argument).
    Raises ValueError for an unparseable delivery_date. Does not
    mutate either argument."""
    milestone_dates = {}
    for entry in milestones:
        milestone_dates[entry["milestone_id"]] = parse_plan_date(entry["planned_date"])

    violations = []
    for plan in discipline_plans:
        discipline_id = plan["discipline_id"]
        target_milestone = plan["contributes_to_milestone"]
        delivery_date = parse_plan_date(plan["delivery_date"])
        if target_milestone not in milestone_dates:
            violations.append(
                {
                    "issue": "missing_milestone_linkage",
                    "discipline": discipline_id,
                    "target_milestone": target_milestone,
                }
            )
            continue
        milestone_date = milestone_dates[target_milestone]
        if delivery_date > milestone_date:
            violations.append(
                {
                    "issue": "late_discipline_input",
                    "discipline": discipline_id,
                    "target_milestone": target_milestone,
                    "delivery_date": delivery_date.isoformat(),
                    "milestone_date": milestone_date.isoformat(),
                }
            )
    return violations


def missing_required_disciplines(discipline_plans):
    """Sorted list of REQUIRED_DISCIPLINES ids that have no entry in
    discipline_plans -- each is a "missing_discipline_plan" finding
    (clause 5.6.2 requires every listed discipline's plan to be
    integrated, not just the ones supplied)."""
    present = {plan["discipline_id"] for plan in discipline_plans}
    return sorted(REQUIRED_DISCIPLINES - present)


def se_planning_review(se_plan):
    """Full clause 5.6.2 SE planning review.

    se_plan: {"milestones": [...], "discipline_plans": [...]} using the
    shapes documented on validate_milestone_order and
    discipline_integration_violations. Returns {"sequence": [...],
    "integration": [...], "coverage": [...]}, each a violation/finding
    list. "coverage" holds one {"issue": "missing_discipline_plan",
    "discipline": id} entry per required discipline with no plan.
    Raises ValueError for an unrecognized milestone id or an
    unparseable date."""
    milestones = se_plan.get("milestones", [])
    discipline_plans = se_plan.get("discipline_plans", [])
    return {
        "sequence": validate_milestone_order(milestones),
        "integration": discipline_integration_violations(discipline_plans, milestones),
        "coverage": [
            {"issue": "missing_discipline_plan", "discipline": discipline_id}
            for discipline_id in missing_required_disciplines(discipline_plans)
        ],
    }


def is_se_plan_compliant(review):
    """True when every category in a se_planning_review result is
    empty -- the SE plan satisfies clause 5.6.2 for this assessment."""
    return all(len(findings) == 0 for findings in review.values())
