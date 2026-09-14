"""Class 2 ASIC assurance tailoring under the dedicated microelectronics rules.

Anchor: ECSS-Q-ST-60-13C clause 5.6.2 (an application-specific device on an
intermediate assurance part programme is still governed by the dedicated ASIC
assurance rules, and only the reductions that class admits may be taken).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Route the declared device kind. A full-custom, standard-cell, gate-array,
   structured or programmed hard-macro part is application specific and carries
   the dedicated ASIC assurance rules even at the intermediate class. A
   catalogue part stays on the generic component route and this clause does not
   move it.
2. Take the dedicated assurance activity set. Each activity carries a class 2
   disposition -- mandatory, reduction only against a named customer approval,
   or reducible on programme authority -- and an assurance weight.
3. Grade the proposed reductions against those dispositions. A reduction of a
   mandatory activity is refused outright. A reduction of an approval-bearing
   activity is admitted only where the approval is on record; without it the
   activity is retained and the approval is reported as outstanding.
4. Compute the residual assurance coverage from the weights still retained and
   compare it with the declared floor, absorbing the representation error at an
   exact equality rather than loosening the floor.
5. Return one verdict with every refused reduction, every outstanding approval
   and the residual coverage behind it.
"""

import math

__all__ = [
    "ASIC_KINDS",
    "GENERIC_KINDS",
    "DEDICATED_ASIC_ROUTE",
    "GENERIC_COMPONENT_ROUTE",
    "ASIC_ASSURANCE_ACTIVITIES",
    "MANDATORY",
    "APPROVAL_REQUIRED",
    "REDUCIBLE",
    "DEFAULT_TAILORING_POLICY",
    "COVERAGE_TOLERANCE",
    "NOT_AN_ASIC",
    "TAILORING_ACCEPTED",
    "TAILORING_ACCEPTED_WITH_APPROVALS",
    "TAILORING_REFUSED",
    "activity_names",
    "activity_disposition",
    "activity_weight",
    "total_assurance_weight",
    "validate_tailoring_policy",
    "validate_activity_list",
    "route_for_kind",
    "residual_coverage",
    "coverage_meets_floor",
    "grade_reductions",
    "assess_asic_tailoring",
]

# Devices whose function is fixed by a design the programme owns or specifies.
ASIC_KINDS = (
    "full-custom-asic",
    "standard-cell-asic",
    "gate-array",
    "structured-asic",
    "programmed-hard-macro",
)

# Devices that stay on the generic commercial-component procurement route.
GENERIC_KINDS = (
    "standard-microcircuit",
    "discrete-semiconductor",
    "hybrid-microcircuit",
    "passive-component",
)

DEDICATED_ASIC_ROUTE = "dedicated-asic-assurance-rules"
GENERIC_COMPONENT_ROUTE = "generic-component-route"

MANDATORY = "mandatory"
APPROVAL_REQUIRED = "approval-required"
REDUCIBLE = "reducible"

NOT_AN_ASIC = "not-an-asic"
TAILORING_ACCEPTED = "tailoring-accepted"
TAILORING_ACCEPTED_WITH_APPROVALS = "tailoring-accepted-with-approvals"
TAILORING_REFUSED = "tailoring-refused"

# The dedicated assurance activity set, in report order: name, the disposition
# the intermediate class gives it, and the assurance weight it carries.
ASIC_ASSURANCE_ACTIVITIES = (
    ("design-rule-compliance-review", MANDATORY, 3.0),
    ("functional-verification-coverage", MANDATORY, 3.0),
    ("process-qualification", MANDATORY, 3.0),
    ("prototype-evaluation", APPROVAL_REQUIRED, 2.0),
    ("package-qualification", APPROVAL_REQUIRED, 2.0),
    ("radiation-verification", APPROVAL_REQUIRED, 2.0),
    ("lot-acceptance-testing", REDUCIBLE, 1.0),
    ("destructive-physical-analysis", REDUCIBLE, 1.0),
)

# A coverage comparison is a ratio of two declared sums. An exact equality can
# land a few units in the last place on the wrong side; absorb that here
# instead of softening the floor.
COVERAGE_TOLERANCE = 1e-9

DEFAULT_TAILORING_POLICY = {
    # Share of the assurance weight that has to survive the tailoring.
    "min_residual_coverage": 0.6,
    # How many activities the intermediate class lets one tailoring drop.
    "max_reduced_activities": 3,
}

_BY_NAME = {name: (disposition, weight)
            for name, disposition, weight in ASIC_ASSURANCE_ACTIVITIES}


def activity_names():
    """Return the dedicated assurance activities in report order."""
    return tuple(name for name, _, _ in ASIC_ASSURANCE_ACTIVITIES)


def activity_disposition(activity):
    """Return the class 2 disposition of one dedicated assurance activity."""
    if not isinstance(activity, str) or not activity.strip():
        raise ValueError("activity must be a non-empty string")
    key = activity.strip().lower()
    if key not in _BY_NAME:
        raise ValueError(
            "unknown assurance activity %r; declare one of %s"
            % (activity, ", ".join(activity_names()))
        )
    return _BY_NAME[key][0]


def activity_weight(activity):
    """Return the assurance weight one dedicated activity carries."""
    if not isinstance(activity, str) or not activity.strip():
        raise ValueError("activity must be a non-empty string")
    key = activity.strip().lower()
    if key not in _BY_NAME:
        raise ValueError(
            "unknown assurance activity %r; declare one of %s"
            % (activity, ", ".join(activity_names()))
        )
    return _BY_NAME[key][1]


def total_assurance_weight():
    """Return the assurance weight of the untailored activity set."""
    return float(sum(weight for _, _, weight in ASIC_ASSURANCE_ACTIVITIES))


def validate_tailoring_policy(policy=None):
    """Return a complete tailoring policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_TAILORING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("tailoring policy must be a mapping")
    merged = dict(DEFAULT_TAILORING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_TAILORING_POLICY:
            raise ValueError("unknown tailoring policy key %r" % (key,))
        merged[key] = value
    floor = merged["min_residual_coverage"]
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError("min_residual_coverage must be a real number")
    floor = float(floor)
    if not math.isfinite(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError("min_residual_coverage must be finite and lie in 0..1")
    merged["min_residual_coverage"] = floor
    cap = merged["max_reduced_activities"]
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
        raise ValueError("max_reduced_activities must be a non-negative integer")
    return merged


def validate_activity_list(activities, label):
    """Return a normalised, duplicate-free tuple of known activity names."""
    if activities is None:
        return ()
    if isinstance(activities, str) or not isinstance(activities, (list, tuple)):
        raise ValueError("%s must be a sequence of activity names" % label)
    seen = []
    for entry in activities:
        name = entry
        if not isinstance(name, str) or not name.strip():
            raise ValueError("%s carries a non-string activity name" % label)
        key = name.strip().lower()
        if key not in _BY_NAME:
            raise ValueError(
                "%s names unknown assurance activity %r" % (label, name)
            )
        if key in seen:
            raise ValueError("%s repeats activity %r" % (label, key))
        seen.append(key)
    return tuple(name for name in activity_names() if name in seen)


def route_for_kind(kind):
    """Return the assurance route a declared device kind falls on."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("device kind must be a non-empty string")
    name = kind.strip().lower()
    if name in ASIC_KINDS:
        return DEDICATED_ASIC_ROUTE
    if name in GENERIC_KINDS:
        return GENERIC_COMPONENT_ROUTE
    raise ValueError(
        "unknown device kind %r; declare one of %s"
        % (kind, ", ".join(ASIC_KINDS + GENERIC_KINDS))
    )


def residual_coverage(reduced_activities):
    """Return the share of assurance weight surviving the admitted reductions."""
    dropped = validate_activity_list(reduced_activities, "reduced activities")
    total = total_assurance_weight()
    lost = float(sum(activity_weight(name) for name in dropped))
    return (total - lost) / total


def coverage_meets_floor(residual, floor):
    """Return whether a residual coverage reaches its floor, equality included."""
    for label, value in (("residual", residual), ("floor", floor)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    have = float(residual)
    need = float(floor)
    return have > need or math.isclose(
        have, need, rel_tol=COVERAGE_TOLERANCE, abs_tol=COVERAGE_TOLERANCE
    )


def grade_reductions(proposed, approvals=None):
    """Return the refused, outstanding and admitted parts of a reduction set."""
    wanted = validate_activity_list(proposed, "proposed reductions")
    granted = validate_activity_list(approvals, "customer approvals")
    refused = []
    outstanding = []
    admitted = []
    for name in wanted:
        disposition = activity_disposition(name)
        if disposition == MANDATORY:
            refused.append(name)
        elif disposition == APPROVAL_REQUIRED and name not in granted:
            outstanding.append(name)
        else:
            admitted.append(name)
    stray = tuple(name for name in granted if name not in wanted)
    return {
        "refused": tuple(refused),
        "outstanding_approvals": tuple(outstanding),
        "admitted": tuple(admitted),
        "unused_approvals": stray,
    }


def assess_asic_tailoring(case):
    """Run the clause 5.6.2 intermediate-class ASIC tailoring assessment.

    case keys: kind, optional proposed_reductions, optional customer_approvals,
    optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "kind" not in case:
        raise ValueError("case missing required key 'kind'")
    settings = validate_tailoring_policy(case.get("policy"))
    route = route_for_kind(case["kind"])
    if route == GENERIC_COMPONENT_ROUTE:
        return {
            "route": route,
            "verdict": NOT_AN_ASIC,
            "refused_reductions": (),
            "outstanding_approvals": (),
            "admitted_reductions": (),
            "retained_activities": activity_names(),
            "residual_coverage": 1.0,
            "findings": [
                "device kind %r is not application specific; the dedicated ASIC "
                "assurance rules of clause 5.6.2 do not reach it" % (case["kind"],)
            ],
        }

    graded = grade_reductions(
        case.get("proposed_reductions"), case.get("customer_approvals")
    )
    admitted = graded["admitted"]
    residual = residual_coverage(admitted)
    floor_met = coverage_meets_floor(residual, settings["min_residual_coverage"])
    retained = tuple(name for name in activity_names() if name not in admitted)

    findings = []
    for name in graded["refused"]:
        findings.append(
            "%s is mandatory at the intermediate class; the proposed reduction "
            "is refused" % name
        )
    for name in graded["outstanding_approvals"]:
        findings.append(
            "%s may be reduced only against a named customer approval, which is "
            "not on record; the activity is retained" % name
        )
    for name in graded["unused_approvals"]:
        findings.append(
            "a customer approval is on record for %s but no reduction of it was "
            "proposed" % name
        )
    if not floor_met:
        findings.append(
            "residual assurance coverage %.4f falls below the declared floor %.4f"
            % (residual, settings["min_residual_coverage"])
        )
    over_cap = len(admitted) > settings["max_reduced_activities"]
    if over_cap:
        findings.append(
            "%d reductions are admitted against an allowance of %d"
            % (len(admitted), settings["max_reduced_activities"])
        )

    if graded["refused"] or not floor_met or over_cap:
        verdict = TAILORING_REFUSED
    elif graded["outstanding_approvals"] or any(
        activity_disposition(name) == APPROVAL_REQUIRED for name in admitted
    ):
        verdict = TAILORING_ACCEPTED_WITH_APPROVALS
    else:
        verdict = TAILORING_ACCEPTED

    return {
        "route": route,
        "verdict": verdict,
        "refused_reductions": graded["refused"],
        "outstanding_approvals": graded["outstanding_approvals"],
        "admitted_reductions": admitted,
        "unused_approvals": graded["unused_approvals"],
        "retained_activities": retained,
        "residual_coverage": residual,
        "coverage_floor": settings["min_residual_coverage"],
        "findings": findings,
    }
