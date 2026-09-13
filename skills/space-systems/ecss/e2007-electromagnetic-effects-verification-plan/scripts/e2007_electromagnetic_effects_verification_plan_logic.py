#!/usr/bin/env python3
"""Electromagnetic effects verification plan logic (ECSS-E-ST-20-07C, 5.1.2).

Offline, deterministic, standard-library only. The module supports the
planning document that directs every activity used to show electromagnetic
effects compliance:

* mandatory plan-section completeness,
* admissibility of the verification-method chosen for each requirement
  family (a substitution is admissible only with a recorded
  tailoring-justification),
* well-formedness of each planned activity (facility, equipment-under-test
  configuration, duration, closure milestone),
* schedule ordering against the plan baseline and the closure milestone,
* schedule feasibility once schedule contingency is applied,
* requirement coverage of the plan requirement-list.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math
from datetime import date, timedelta

__all__ = [
    "REL_TOL",
    "MANDATORY_PLAN_SECTIONS",
    "VERIFICATION_METHODS",
    "ADMISSIBLE_METHODS",
    "MILESTONE_ORDER",
    "normalize_method",
    "normalize_requirement_family",
    "normalize_milestone",
    "parse_plan_date",
    "method_admissible",
    "missing_plan_sections",
    "validate_activity",
    "check_schedule_ordering",
    "check_schedule_feasibility",
    "compute_requirement_coverage",
    "assess_verification_plan",
]

# Absorbs binary-representation error when a summed schedule lands a few
# ULPs above an exactly-satisfied window. It never widens the window itself.
REL_TOL = 1e-9

MANDATORY_PLAN_SECTIONS = (
    "scope-and-applicability",
    "requirement-list",
    "verification-method-assignment",
    "facility-and-configuration",
    "schedule-and-milestones",
    "responsibility-assignment",
    "nonconformance-handling",
    "tailoring-justification",
)

VERIFICATION_METHODS = frozenset(
    {"test", "analysis", "review-of-design", "inspection", "similarity"}
)

_METHOD_SYNONYMS = {
    "t": "test",
    "a": "analysis",
    "r": "review-of-design",
    "rod": "review-of-design",
    "review of design": "review-of-design",
    "design-review": "review-of-design",
    "i": "inspection",
    "s": "similarity",
    "heritage": "similarity",
}

# Method families admissible per electromagnetic-effects requirement family
# without a recorded tailoring-justification. Emission and susceptibility
# behaviour is measurable only on hardware; magnetic-moment, discharge and
# radiation-hazard families accept a modelled demonstration; the
# bonding-and-grounding family is largely a build-state check.
ADMISSIBLE_METHODS = {
    "radiated-emission": frozenset({"test"}),
    "conducted-emission": frozenset({"test"}),
    "radiated-susceptibility": frozenset({"test"}),
    "conducted-susceptibility": frozenset({"test"}),
    "magnetic-moment": frozenset({"test", "analysis"}),
    "electrostatic-discharge": frozenset({"test", "analysis"}),
    "bonding-and-grounding": frozenset({"test", "inspection", "review-of-design"}),
    "intra-system-compatibility": frozenset({"analysis", "test"}),
    "electromagnetic-radiation-hazard": frozenset({"analysis", "test"}),
    "lightning-protection": frozenset({"analysis", "review-of-design", "test"}),
}

MILESTONE_ORDER = {"srr": 0, "pdr": 1, "cdr": 2, "qr": 3, "ar": 4}

_REQUIRED_ACTIVITY_KEYS = (
    "id",
    "requirement_id",
    "family",
    "method",
    "planned_start",
    "duration_days",
    "closure_milestone",
)

_REQUIRED_PLAN_KEYS = (
    "baseline_date",
    "sections",
    "requirements",
    "activities",
    "milestone_dates",
)


def _finding(code, subject, detail):
    """Build one plan finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _norm_token(value, label):
    """Lower-case, hyphenate and squeeze one free-text token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    token = " ".join(value.strip().lower().replace("_", "-").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _as_positive_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def normalize_method(method):
    """Return the canonical verification-method token."""
    token = _norm_token(method, "verification method")
    token = _METHOD_SYNONYMS.get(token, token)
    if token not in VERIFICATION_METHODS:
        raise ValueError(
            "unknown verification method %r; expected one of %s"
            % (method, ", ".join(sorted(VERIFICATION_METHODS)))
        )
    return token


def normalize_requirement_family(family):
    """Return the canonical electromagnetic-effects requirement family."""
    token = _norm_token(family, "requirement family")
    if token not in ADMISSIBLE_METHODS:
        raise ValueError(
            "unknown requirement family %r; expected one of %s"
            % (family, ", ".join(sorted(ADMISSIBLE_METHODS)))
        )
    return token


def normalize_milestone(milestone):
    """Return the canonical programme-milestone token."""
    token = _norm_token(milestone, "closure milestone")
    if token not in MILESTONE_ORDER:
        raise ValueError(
            "unknown closure milestone %r; expected one of %s"
            % (milestone, ", ".join(sorted(MILESTONE_ORDER, key=MILESTONE_ORDER.get)))
        )
    return token


def parse_plan_date(value):
    """Accept a date object or an ISO-8601 day string; reject anything else."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(
            "plan date must be an ISO-8601 string or a date, got %s"
            % type(value).__name__
        )
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("plan date %r is not an ISO-8601 calendar day" % value)


def method_admissible(family, method, tailoring_justified=False):
    """True when the method may close the family, or a tailoring is recorded."""
    fam = normalize_requirement_family(family)
    met = normalize_method(method)
    if met in ADMISSIBLE_METHODS[fam]:
        return True
    return bool(tailoring_justified)


def missing_plan_sections(sections):
    """Return the mandatory plan sections absent from the supplied outline."""
    if isinstance(sections, (str, bytes)) or not hasattr(sections, "__iter__"):
        raise ValueError("sections must be an iterable of section names")
    seen = []
    for raw in sections:
        token = _norm_token(raw, "plan section")
        if token in seen:
            raise ValueError("plan section %r is listed twice" % token)
        seen.append(token)
    return [name for name in MANDATORY_PLAN_SECTIONS if name not in seen]


def validate_activity(activity):
    """Normalize one planned verification activity; raise on malformed input."""
    if not isinstance(activity, dict):
        raise ValueError(
            "activity must be a mapping, got %s" % type(activity).__name__
        )
    absent = [key for key in _REQUIRED_ACTIVITY_KEYS if key not in activity]
    if absent:
        raise ValueError(
            "activity is missing required key(s): %s" % ", ".join(absent)
        )
    record = {
        "id": _norm_token(activity["id"], "activity id"),
        "requirement_id": _norm_token(activity["requirement_id"], "requirement id"),
        "family": normalize_requirement_family(activity["family"]),
        "method": normalize_method(activity["method"]),
        "planned_start": parse_plan_date(activity["planned_start"]),
        "duration_days": _as_positive_float(
            activity["duration_days"], "duration_days"
        ),
        "closure_milestone": normalize_milestone(activity["closure_milestone"]),
    }
    for key in ("facility", "configuration"):
        raw = activity.get(key, "")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            raise ValueError(
                "%s must be a string when present, got %s" % (key, type(raw).__name__)
            )
        record[key] = raw.strip()
    record["tailoring_justification"] = bool(
        activity.get("tailoring_justification", False)
    )
    return record


def check_schedule_ordering(baseline_date, activities, milestone_dates):
    """Flag activities that start before baseline or overrun their milestone."""
    base = parse_plan_date(baseline_date)
    if not isinstance(milestone_dates, dict):
        raise ValueError("milestone_dates must be a mapping of milestone to date")
    dated = {}
    for key, value in milestone_dates.items():
        dated[normalize_milestone(key)] = parse_plan_date(value)
    findings = []
    for raw in activities:
        act = validate_activity(raw)
        if act["planned_start"] < base:
            findings.append(
                _finding(
                    "activity-precedes-plan-baseline",
                    act["id"],
                    "planned start %s precedes the plan baseline %s"
                    % (act["planned_start"].isoformat(), base.isoformat()),
                )
            )
        milestone = act["closure_milestone"]
        if milestone not in dated:
            findings.append(
                _finding(
                    "closure-milestone-undated",
                    act["id"],
                    "closure milestone %s carries no date in the plan schedule"
                    % milestone,
                )
            )
            continue
        end = act["planned_start"] + timedelta(
            days=int(math.ceil(act["duration_days"]))
        )
        if end > dated[milestone]:
            findings.append(
                _finding(
                    "activity-overruns-closure-milestone",
                    act["id"],
                    "activity ends %s, after milestone %s on %s"
                    % (end.isoformat(), milestone, dated[milestone].isoformat()),
                )
            )
    return findings


def check_schedule_feasibility(activities, window_days, contingency_fraction=0.0):
    """Sum activity durations, apply contingency, compare with the window."""
    window = _as_positive_float(window_days, "window_days")
    if isinstance(contingency_fraction, bool) or not isinstance(
        contingency_fraction, (int, float)
    ):
        raise ValueError(
            "contingency_fraction must be a number, got %s"
            % type(contingency_fraction).__name__
        )
    contingency = float(contingency_fraction)
    if not math.isfinite(contingency) or contingency < 0.0 or contingency > 1.0:
        raise ValueError(
            "contingency_fraction must lie in [0, 1], got %r" % (contingency_fraction,)
        )
    activity_days = 0.0
    count = 0
    for raw in activities:
        activity_days += validate_activity(raw)["duration_days"]
        count += 1
    if count == 0:
        raise ValueError("a verification plan must contain at least one activity")
    required = activity_days * (1.0 + contingency)
    feasible = required <= window or math.isclose(required, window, rel_tol=REL_TOL)
    return {
        "activity_days": activity_days,
        "required_days": required,
        "window_days": window,
        "contingency_fraction": contingency,
        "slack_days": window - required,
        "feasible": feasible,
    }


def compute_requirement_coverage(requirements, activities):
    """Map each plan requirement to the activities that address it."""
    if isinstance(requirements, (str, bytes)) or not hasattr(requirements, "__iter__"):
        raise ValueError("requirements must be an iterable of requirement records")
    families = {}
    for raw in requirements:
        if not isinstance(raw, dict):
            raise ValueError(
                "requirement must be a mapping, got %s" % type(raw).__name__
            )
        for key in ("id", "family"):
            if key not in raw:
                raise ValueError("requirement is missing required key %r" % key)
        rid = _norm_token(raw["id"], "requirement id")
        if rid in families:
            raise ValueError("requirement %r is listed twice" % rid)
        families[rid] = normalize_requirement_family(raw["family"])
    if not families:
        raise ValueError("the plan requirement-list must not be empty")
    covered = {}
    orphans = []
    mismatched = []
    for raw in activities:
        act = validate_activity(raw)
        rid = act["requirement_id"]
        if rid not in families:
            orphans.append(act["id"])
            continue
        if act["family"] != families[rid]:
            mismatched.append(act["id"])
            continue
        covered.setdefault(rid, []).append(act["id"])
    uncovered = sorted(rid for rid in families if rid not in covered)
    return {
        "requirement_count": len(families),
        "covered": {rid: sorted(ids) for rid, ids in covered.items()},
        "uncovered": uncovered,
        "orphan_activities": sorted(orphans),
        "family_mismatch_activities": sorted(mismatched),
        "coverage_fraction": len(covered) / float(len(families)),
    }


def assess_verification_plan(plan):
    """Assess one electromagnetic-effects verification plan end to end."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %s" % type(plan).__name__)
    absent = [key for key in _REQUIRED_PLAN_KEYS if key not in plan]
    if absent:
        raise ValueError("plan is missing required key(s): %s" % ", ".join(absent))
    findings = []
    for section in missing_plan_sections(plan["sections"]):
        findings.append(
            _finding(
                "plan-section-missing", section, "mandatory plan section is absent"
            )
        )
    activities = [validate_activity(raw) for raw in plan["activities"]]
    if not activities:
        raise ValueError("a verification plan must contain at least one activity")
    seen_ids = set()
    for act in activities:
        if act["id"] in seen_ids:
            raise ValueError("activity id %r is listed twice" % act["id"])
        seen_ids.add(act["id"])
        if not method_admissible(
            act["family"], act["method"], act["tailoring_justification"]
        ):
            findings.append(
                _finding(
                    "method-not-admissible",
                    act["id"],
                    "%s is not closable by %s without a recorded "
                    "tailoring-justification" % (act["family"], act["method"]),
                )
            )
        if act["method"] == "test":
            if not act["facility"]:
                findings.append(
                    _finding(
                        "test-facility-unnamed",
                        act["id"],
                        "a measured activity must name the facility it runs in",
                    )
                )
            if not act["configuration"]:
                findings.append(
                    _finding(
                        "eut-configuration-unnamed",
                        act["id"],
                        "a measured activity must name its equipment-under-test "
                        "configuration",
                    )
                )
    coverage = compute_requirement_coverage(plan["requirements"], activities)
    for rid in coverage["uncovered"]:
        findings.append(
            _finding(
                "requirement-uncovered",
                rid,
                "no planned activity addresses this requirement",
            )
        )
    for aid in coverage["orphan_activities"]:
        findings.append(
            _finding(
                "activity-orphan",
                aid,
                "activity addresses a requirement absent from the requirement-list",
            )
        )
    for aid in coverage["family_mismatch_activities"]:
        findings.append(
            _finding(
                "requirement-family-mismatch",
                aid,
                "activity family differs from the family of its requirement",
            )
        )
    findings.extend(
        check_schedule_ordering(
            plan["baseline_date"], activities, plan["milestone_dates"]
        )
    )
    schedule = None
    if plan.get("window_days") is not None:
        schedule = check_schedule_feasibility(
            activities, plan["window_days"], plan.get("contingency_fraction", 0.0)
        )
        if not schedule["feasible"]:
            findings.append(
                _finding(
                    "schedule-infeasible",
                    "verification-plan",
                    "activities plus contingency need %.3f days against a %.3f day "
                    "window" % (schedule["required_days"], schedule["window_days"]),
                )
            )
    return {
        "verdict": "compliant" if not findings else "non-compliant",
        "release_ready": not findings,
        "findings": findings,
        "coverage": coverage,
        "schedule": schedule,
        "activity_count": len(activities),
    }
