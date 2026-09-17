#!/usr/bin/env python3
"""Routing a class 3 application specific integrated circuit to its own standard.

Anchor: ECSS-Q-ST-60C clause 6.6.2 (a class 3 application specific integrated
circuit is developed and reused under the dedicated ASIC and programmable
device development standard). Paraphrased into an implementable procedure; no
standard text is reproduced.

The referral is the easy half. A class 3 device is allowed to enter that
standard's flow tailored, and the tailoring is the part that has to be
defended: which activities may be dropped, what is offered in their place, who
is entitled to grant the drop, and how much of the assurance set is left
standing when every granted waiver is counted.

Procedure implemented here
--------------------------
1. Route the device. A new development enters the full flow. A reuse claim is
   weighed on flight heritage — units flown, cumulative hours and whether the
   environment it flew in was at least as harsh as the one it is going into.
2. Build the flow's activity plan for the device category.
3. Grade every requested waiver: a core activity is never waivable, a waiver
   without a justification reference and a compensating measure is not a
   waiver, and each waivable activity names the authority entitled to grant it.
4. Take the residual risk index as the weighted share of the waivable plan
   that was actually given up, and test it against the limit the function
   criticality sets.
5. Return one verdict naming the first thing that stops the tailoring.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "ASIC_CATEGORIES",
    "DEVELOPMENT_FLOWS",
    "FULL_DEVELOPMENT",
    "DELTA_DEVELOPMENT",
    "REVIEWED_REUSE",
    "BASE_ACTIVITIES",
    "CATEGORY_EXTRA_ACTIVITIES",
    "CORE_ACTIVITIES",
    "ACTIVITY_WEIGHT",
    "FUNCTION_CRITICALITIES",
    "APPROVAL_AUTHORITIES",
    "AUTHORITY_RANK",
    "WAIVER_AUTHORITY",
    "CRITICALITY_RISK_LIMIT",
    "REQUIRED_WAIVER_FIELDS",
    "DEFAULT_TAILORING_POLICY",
    "TAILORING_ACCEPTED",
    "HERITAGE_EVIDENCE_INSUFFICIENT",
    "WAIVER_ON_CORE_ACTIVITY",
    "WAIVER_JUSTIFICATION_MISSING",
    "APPROVAL_AUTHORITY_INSUFFICIENT",
    "RESIDUAL_RISK_ABOVE_LIMIT",
    "validate_tailoring_policy",
    "validate_heritage_record",
    "validate_waiver",
    "validate_waivers",
    "authority_rank",
    "activity_plan",
    "waivable_activities",
    "environment_severity_ratio",
    "heritage_is_sufficient",
    "route_development",
    "waiver_findings",
    "granted_waivers",
    "tailored_plan",
    "residual_risk_index",
    "assess_asic_tailoring",
]

ASIC_CATEGORIES = (
    "full-custom",
    "gate-array",
    "structured-array",
    "mixed-signal",
    "system-on-chip",
)

FULL_DEVELOPMENT = "full-development-flow"
DELTA_DEVELOPMENT = "delta-development-flow"
REVIEWED_REUSE = "reviewed-reuse-flow"

DEVELOPMENT_FLOWS = (FULL_DEVELOPMENT, DELTA_DEVELOPMENT, REVIEWED_REUSE)

# The activity set the dedicated standard carries, before any tailoring.
BASE_ACTIVITIES = (
    "requirements-review",
    "design-rule-verification",
    "functional-simulation",
    "timing-verification",
    "prototype-manufacturing",
    "prototype-validation",
    "radiation-evaluation",
    "qualification-testing",
    "lot-acceptance-definition",
    "design-data-archiving",
)

CATEGORY_EXTRA_ACTIVITIES = {
    "full-custom": ("layout-verification",),
    "gate-array": ("configuration-verification",),
    "structured-array": ("configuration-verification",),
    "mixed-signal": ("analogue-characterisation", "isolation-analysis"),
    "system-on-chip": ("embedded-core-verification", "isolation-analysis"),
}

# Activities that stay whatever the class is. The requirements belong to this
# order, the lot acceptance to this lot, and an unarchived design cannot be
# maintained by anybody later.
CORE_ACTIVITIES = (
    "requirements-review",
    "functional-simulation",
    "lot-acceptance-definition",
    "design-data-archiving",
)

# How much assurance each activity carries, used to weight a waiver rather than
# counting waivers as if they cost the same.
ACTIVITY_WEIGHT = {
    "requirements-review": 4,
    "design-rule-verification": 3,
    "functional-simulation": 5,
    "timing-verification": 4,
    "prototype-manufacturing": 3,
    "prototype-validation": 5,
    "radiation-evaluation": 5,
    "qualification-testing": 5,
    "lot-acceptance-definition": 4,
    "design-data-archiving": 2,
    "layout-verification": 3,
    "configuration-verification": 3,
    "analogue-characterisation": 4,
    "isolation-analysis": 3,
    "embedded-core-verification": 4,
}

FUNCTION_CRITICALITIES = (
    "mission-critical",
    "mission-important",
    "non-critical",
)

APPROVAL_AUTHORITIES = (
    "customer-authority",
    "product-assurance-manager",
    "project-authority",
)

# 1 is the highest authority.
AUTHORITY_RANK = {name: index + 1 for index, name in enumerate(APPROVAL_AUTHORITIES)}

# The authority entitled to grant a waiver on each waivable activity.
WAIVER_AUTHORITY = {
    "design-rule-verification": "product-assurance-manager",
    "timing-verification": "product-assurance-manager",
    "prototype-manufacturing": "project-authority",
    "prototype-validation": "customer-authority",
    "radiation-evaluation": "customer-authority",
    "qualification-testing": "customer-authority",
    "layout-verification": "product-assurance-manager",
    "configuration-verification": "project-authority",
    "analogue-characterisation": "product-assurance-manager",
    "isolation-analysis": "product-assurance-manager",
    "embedded-core-verification": "product-assurance-manager",
}

# How much of the waivable assurance a class 3 device may give up, by the
# criticality of the function the device performs.
CRITICALITY_RISK_LIMIT = {
    "mission-critical": 0.20,
    "mission-important": 0.45,
    "non-critical": 0.70,
}

REQUIRED_WAIVER_FIELDS = ("justification_reference", "compensating_measure")

DEFAULT_TAILORING_POLICY = {
    # Units of the referenced build that flew before the claim is weighable.
    "minimum_units_flown": 4,
    # Cumulative flight hours behind the reuse claim.
    "minimum_flight_hours": 2000,
}

TAILORING_ACCEPTED = "class-3-asic-tailoring-accepted"
HERITAGE_EVIDENCE_INSUFFICIENT = "reuse-heritage-evidence-insufficient"
WAIVER_ON_CORE_ACTIVITY = "waiver-requested-on-core-activity"
WAIVER_JUSTIFICATION_MISSING = "waiver-justification-record-missing"
APPROVAL_AUTHORITY_INSUFFICIENT = "waiver-approval-authority-insufficient"
RESIDUAL_RISK_ABOVE_LIMIT = "residual-risk-index-above-limit"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def validate_tailoring_policy(policy=None):
    """Validate the tailoring policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_TAILORING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_TAILORING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_TAILORING_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    for key in ("minimum_units_flown", "minimum_flight_hours"):
        if not _is_int(merged[key]) or merged[key] < 0:
            raise ValueError(
                "%s must be a non-negative integer, got %r" % (key, merged[key])
            )
    return merged


def authority_rank(authority):
    """Position of an approval authority; 1 is the highest."""
    if authority not in AUTHORITY_RANK:
        raise ValueError(
            "unknown approval authority %r (known: %s)"
            % (authority, ", ".join(APPROVAL_AUTHORITIES))
        )
    return AUTHORITY_RANK[authority]


def validate_heritage_record(record):
    """Validate the flight heritage offered behind a reuse claim."""
    if not isinstance(record, dict):
        raise ValueError(
            "heritage record must be a mapping, got %r" % (type(record).__name__,)
        )
    _require_text("heritage part_number", record.get("part_number"))
    units = record.get("units_flown")
    if not _is_int(units) or units < 0:
        raise ValueError("units_flown must be a non-negative integer, got %r" % (units,))
    hours = record.get("cumulative_flight_hours")
    if not _is_number(hours) or hours < 0:
        raise ValueError(
            "cumulative_flight_hours must be a non-negative number, got %r" % (hours,)
        )
    for key in ("referenced_environment_severity", "candidate_environment_severity"):
        value = record.get(key)
        if not _is_number(value) or value <= 0:
            raise ValueError("%s must be a positive number, got %r" % (key, value))
    modified = record.get("design_modified")
    if not isinstance(modified, bool):
        raise ValueError("design_modified must be a boolean, got %r" % (modified,))
    return {
        "part_number": record["part_number"],
        "units_flown": units,
        "cumulative_flight_hours": float(hours),
        "referenced_environment_severity": float(
            record["referenced_environment_severity"]
        ),
        "candidate_environment_severity": float(
            record["candidate_environment_severity"]
        ),
        "design_modified": modified,
    }


def validate_waiver(raw):
    """Validate one requested tailoring waiver."""
    if not isinstance(raw, dict):
        raise ValueError("waiver must be a mapping, got %r" % (type(raw).__name__,))
    activity = raw.get("activity")
    if activity not in ACTIVITY_WEIGHT:
        raise ValueError(
            "unknown activity %r (known: %s)"
            % (activity, ", ".join(sorted(ACTIVITY_WEIGHT)))
        )
    authority = raw.get("approved_by")
    authority_rank(authority)
    record = {"activity": activity, "approved_by": authority}
    for field in REQUIRED_WAIVER_FIELDS:
        value = raw.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError("%s must be a string or None, got %r" % (field, value))
        # A blank justification is a missing one, not a present empty string.
        record[field] = value.strip() or None if isinstance(value, str) else None
    return record


def validate_waivers(waivers):
    """Validate a waiver list and reject the same activity waived twice."""
    if not isinstance(waivers, (list, tuple)):
        raise ValueError(
            "waivers must be a list or tuple, got %r" % (type(waivers).__name__,)
        )
    records = [validate_waiver(raw) for raw in waivers]
    seen = set()
    for record in records:
        if record["activity"] in seen:
            raise ValueError("duplicate waiver on activity %r" % (record["activity"],))
        seen.add(record["activity"])
    return records


def activity_plan(category, flow):
    """Full activity set the flow carries for a device category."""
    if category not in CATEGORY_EXTRA_ACTIVITIES:
        raise ValueError(
            "unknown ASIC category %r (known: %s)"
            % (category, ", ".join(ASIC_CATEGORIES))
        )
    if flow not in DEVELOPMENT_FLOWS:
        raise ValueError(
            "unknown development flow %r (known: %s)"
            % (flow, ", ".join(DEVELOPMENT_FLOWS))
        )
    plan = list(BASE_ACTIVITIES) + list(CATEGORY_EXTRA_ACTIVITIES[category])
    if flow == REVIEWED_REUSE:
        # A reviewed reuse re-runs what belongs to this order and this lot and
        # takes the rest from the referenced build.
        plan = [name for name in plan if name in CORE_ACTIVITIES]
    return tuple(plan)


def waivable_activities(category, flow):
    """Activities in the plan that class 3 tailoring is allowed to touch."""
    return tuple(
        name
        for name in activity_plan(category, flow)
        if name not in CORE_ACTIVITIES and name in WAIVER_AUTHORITY
    )


def environment_severity_ratio(record):
    """Candidate environment severity divided by the referenced one."""
    validated = validate_heritage_record(record)
    return (
        validated["candidate_environment_severity"]
        / validated["referenced_environment_severity"]
    )


def heritage_is_sufficient(record, policy=None):
    """Whether the flight heritage is weighable at all for a reuse claim."""
    merged = validate_tailoring_policy(policy)
    validated = validate_heritage_record(record)
    return (
        validated["units_flown"] >= merged["minimum_units_flown"]
        and validated["cumulative_flight_hours"] >= merged["minimum_flight_hours"]
    )


def route_development(case, policy=None):
    """Pick the flow of the dedicated standard this device enters."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    declared = case.get("declared_route")
    if declared not in ("new-development", "reuse"):
        raise ValueError(
            "declared_route must be 'new-development' or 'reuse', got %r" % (declared,)
        )
    if declared == "new-development":
        return {"flow": FULL_DEVELOPMENT, "reason": "no-heritage-to-weigh"}
    record = case.get("heritage")
    if record is None:
        raise ValueError("a reuse claim needs a heritage record")
    validated = validate_heritage_record(record)
    if not heritage_is_sufficient(validated, policy):
        return {"flow": FULL_DEVELOPMENT, "reason": HERITAGE_EVIDENCE_INSUFFICIENT}
    ratio = environment_severity_ratio(validated)
    if validated["design_modified"]:
        return {"flow": DELTA_DEVELOPMENT, "reason": "design-modified-since-reference"}
    if ratio > 1.0:
        return {"flow": DELTA_DEVELOPMENT, "reason": "candidate-environment-harsher"}
    return {"flow": REVIEWED_REUSE, "reason": "heritage-covers-the-application"}


def waiver_findings(waivers, category, flow):
    """Findings raised by the requested waivers against the tailored plan."""
    records = validate_waivers(waivers)
    allowed = set(waivable_activities(category, flow))
    plan = set(activity_plan(category, flow))
    findings = []
    for record in records:
        activity = record["activity"]
        if activity in CORE_ACTIVITIES:
            findings.append(
                {
                    "activity": activity,
                    "finding": WAIVER_ON_CORE_ACTIVITY,
                    "required": "activity-is-not-waivable-at-any-class",
                    "declared": record["approved_by"],
                }
            )
            continue
        if activity not in plan:
            # Waiving something the plan never carried is noise, not a finding.
            continue
        missing = [
            field for field in REQUIRED_WAIVER_FIELDS if not record.get(field)
        ]
        if missing:
            findings.append(
                {
                    "activity": activity,
                    "finding": WAIVER_JUSTIFICATION_MISSING,
                    "required": ", ".join(missing),
                    "declared": None,
                }
            )
            continue
        if activity in allowed:
            needed = WAIVER_AUTHORITY[activity]
            if authority_rank(record["approved_by"]) > authority_rank(needed):
                findings.append(
                    {
                        "activity": activity,
                        "finding": APPROVAL_AUTHORITY_INSUFFICIENT,
                        "required": needed,
                        "declared": record["approved_by"],
                    }
                )
    return tuple(findings)


def granted_waivers(waivers, category, flow):
    """Activities actually given up: requested, in plan, justified and approved."""
    records = validate_waivers(waivers)
    blocked = {item["activity"] for item in waiver_findings(waivers, category, flow)}
    allowed = set(waivable_activities(category, flow))
    return tuple(
        record["activity"]
        for record in records
        if record["activity"] in allowed and record["activity"] not in blocked
    )


def tailored_plan(waivers, category, flow):
    """The activity set that survives the granted waivers."""
    given_up = set(granted_waivers(waivers, category, flow))
    return tuple(
        name for name in activity_plan(category, flow) if name not in given_up
    )


def residual_risk_index(waivers, category, flow):
    """Weighted share of the waivable assurance the tailoring gave up."""
    waivable = waivable_activities(category, flow)
    total = sum(ACTIVITY_WEIGHT[name] for name in waivable)
    if total == 0:
        return 0.0
    given_up = granted_waivers(waivers, category, flow)
    return sum(ACTIVITY_WEIGHT[name] for name in given_up) / total


def assess_asic_tailoring(case, policy=None):
    """Grade a whole class 3 ASIC referral and the tailoring it carries."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    for key in ("part_number", "category", "function_criticality", "declared_route",
                "waivers"):
        if key not in case:
            raise ValueError("case has no %r" % (key,))
    _require_text("case part_number", case["part_number"])
    category = case["category"]
    if category not in CATEGORY_EXTRA_ACTIVITIES:
        raise ValueError(
            "unknown ASIC category %r (known: %s)"
            % (category, ", ".join(ASIC_CATEGORIES))
        )
    criticality = case["function_criticality"]
    if criticality not in CRITICALITY_RISK_LIMIT:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    routing = route_development(case, policy)
    flow = routing["flow"]
    findings = list(waiver_findings(case["waivers"], category, flow))
    if routing["reason"] == HERITAGE_EVIDENCE_INSUFFICIENT:
        findings.insert(
            0,
            {
                "activity": None,
                "finding": HERITAGE_EVIDENCE_INSUFFICIENT,
                "required": "units-flown-and-cumulative-hours-above-the-floor",
                "declared": case["heritage"].get("part_number"),
            },
        )
    index = residual_risk_index(case["waivers"], category, flow)
    limit = CRITICALITY_RISK_LIMIT[criticality]
    over_limit = index > limit
    if over_limit:
        findings.append(
            {
                "activity": None,
                "finding": RESIDUAL_RISK_ABOVE_LIMIT,
                "required": limit,
                "declared": index,
            }
        )
    order = (
        WAIVER_ON_CORE_ACTIVITY,
        WAIVER_JUSTIFICATION_MISSING,
        APPROVAL_AUTHORITY_INSUFFICIENT,
        RESIDUAL_RISK_ABOVE_LIMIT,
        HERITAGE_EVIDENCE_INSUFFICIENT,
    )
    verdict = TAILORING_ACCEPTED
    for name in order:
        if any(item["finding"] == name for item in findings):
            verdict = name
            break
    return {
        "verdict": verdict,
        "part_number": case["part_number"],
        "category": category,
        "flow": flow,
        "routing_reason": routing["reason"],
        "activity_plan": activity_plan(category, flow),
        "tailored_plan": tailored_plan(case["waivers"], category, flow),
        "granted_waivers": granted_waivers(case["waivers"], category, flow),
        "residual_risk_index": index,
        "residual_risk_limit": limit,
        "findings": findings,
        "acceptable": verdict == TAILORING_ACCEPTED,
    }
