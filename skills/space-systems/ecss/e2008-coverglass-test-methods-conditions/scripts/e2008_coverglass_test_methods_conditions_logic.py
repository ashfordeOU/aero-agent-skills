#!/usr/bin/env python3
"""Coverglass acceptance testing run at the defined methods and conditions.

Anchor: ECSS-E-ST-20-08C clause 8.5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not define how a coverglass acceptance test is run. It
points at the method and condition definitions that appear further down
clause 8 and says acceptance uses those. Everything that can go wrong
here is a pointer problem rather than a measurement problem, so this
leaf grades a declared acceptance procedure against the definitions it
claims to be reusing, activity by activity and condition by condition.

A pointer that resolves to nothing is the worst state and the easiest
one to miss, because a procedure naming an activity the downstream
clause never defined still reads as a complete procedure. Nothing in
the paperwork is blank; the reference simply has no other end.

A substituted method is next, and it is settled before any condition is
looked at. Swapping a magnified examination for an unaided one, or a
spectrophotometer scan for a quicker probe, invalidates every condition
underneath it, so comparing conditions across two different methods
produces a tidy table about nothing.

Conditions are compared under their own sense, because the same numeric
gap means opposite things depending on what the condition is:

    floor    the referenced value is a minimum severity -- points per
             piece, magnification, probe sites. Declaring less is a
             relaxation; declaring more is an escalation.
    ceiling  the referenced value is a maximum permitted -- gauge
             resolution, wavelength step, humidity. Declaring more is a
             relaxation; declaring less is an escalation.
    nominal  the referenced value is a set point with a tolerance.
             Outside the band is off-baseline in either direction.

A relaxation leaves acceptance weaker than the definition it inherits
and is the finding the clause exists to prevent. An escalation
over-tests delivered hardware, costs money and can reject good pieces,
so it is reported rather than ignored -- but whether it blocks is a
project position. A condition the procedure omitted and a condition it
invented are both changes to the defined test, not details.

The referenced definitions and the carry positions below are declared
project policy, not physical constants; a project may substitute its
own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SENSE_FLOOR = "floor"
SENSE_CEILING = "ceiling"
SENSE_NOMINAL = "nominal"
SENSES = (SENSE_FLOOR, SENSE_CEILING, SENSE_NOMINAL)

REFERENCE_DEFINITIONS = {
    "coverglass-dimensional-measurement": {
        "method": "contact-gauge-dimensional-measurement",
        "conditions": {
            "measurement-points-per-piece": {"sense": SENSE_FLOOR, "value": 5.0},
            "gauge-resolution-micrometre": {"sense": SENSE_CEILING, "value": 1.0},
            "ambient-temperature-celsius": {
                "sense": SENSE_NOMINAL,
                "value": 23.0,
                "tolerance": 2.0,
            },
        },
    },
    "coverglass-visual-inspection": {
        "method": "magnified-visual-examination",
        "conditions": {
            "inspection-magnification": {"sense": SENSE_FLOOR, "value": 10.0},
            "inspection-illuminance-lux": {"sense": SENSE_FLOOR, "value": 1000.0},
        },
    },
    "coverglass-optical-transmission-measurement": {
        "method": "spectrophotometer-transmission-scan",
        "conditions": {
            "wavelength-points": {"sense": SENSE_FLOOR, "value": 50.0},
            "wavelength-step-nanometre": {"sense": SENSE_CEILING, "value": 10.0},
            "ambient-temperature-celsius": {
                "sense": SENSE_NOMINAL,
                "value": 23.0,
                "tolerance": 2.0,
            },
        },
    },
    "coverglass-surface-conductivity-measurement": {
        "method": "four-point-collinear-probe-sheet-resistance",
        "conditions": {
            "probe-sites-per-piece": {"sense": SENSE_FLOOR, "value": 3.0},
            "measurement-humidity-percent": {"sense": SENSE_CEILING, "value": 50.0},
        },
    },
}

CONDITION_CONFORMING = "condition-reused"
CONDITION_RELAXED = "condition-relaxed"
CONDITION_ESCALATED = "condition-escalated"
CONDITION_OFF_BASELINE = "condition-off-baseline"

ACTIVITY_REFERENCE_UNRESOLVED = "coverglass-method-reference-unresolved"
ACTIVITY_METHOD_SUBSTITUTED = "coverglass-method-substituted"
ACTIVITY_CONDITION_OMITTED = "coverglass-condition-omitted"
ACTIVITY_CONDITION_INVENTED = "coverglass-condition-invented"
ACTIVITY_CONDITION_RELAXED = "coverglass-condition-relaxed"
ACTIVITY_CONDITION_OFF_BASELINE = "coverglass-condition-off-baseline"
ACTIVITY_CONDITION_ESCALATED = "coverglass-condition-escalated"
ACTIVITY_CONFORMING = "coverglass-acceptance-definition-reused"

ACTIVITY_RANK = {
    ACTIVITY_REFERENCE_UNRESOLVED: 0,
    ACTIVITY_METHOD_SUBSTITUTED: 1,
    ACTIVITY_CONDITION_OMITTED: 2,
    ACTIVITY_CONDITION_INVENTED: 3,
    ACTIVITY_CONDITION_RELAXED: 4,
    ACTIVITY_CONDITION_OFF_BASELINE: 5,
    ACTIVITY_CONDITION_ESCALATED: 6,
    ACTIVITY_CONFORMING: 7,
}

PROCEDURE_REUSES_DEFINITIONS = "coverglass-acceptance-reuses-definitions"
PROCEDURE_DEPARTS_FROM_DEFINITIONS = "coverglass-acceptance-departs-from-definitions"

DEFAULT_REUSE_POLICY = {
    "carry_escalation": True,
    "carry_off_baseline": False,
    "min_activity_coverage": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_number(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(
            "%s must sit between zero and one inclusive, got %r" % (name, value)
        )
    return number


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A declared condition is frequently arrived at by arithmetic -- a step
    count multiplied out, a band summed up -- and a value that should sit
    exactly on its referenced bound can evaluate a unit in the last place
    either side of it. The comparison absorbs that; the referenced value
    is untouched.
    """
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def resolve_reuse_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_REUSE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_flag("carry_escalation", settings.get("carry_escalation"))
    _require_flag("carry_off_baseline", settings.get("carry_off_baseline"))
    _require_fraction("min_activity_coverage", settings.get("min_activity_coverage"))
    return settings


def resolve_reference(activity):
    """Follow the clause pointer; return None when it has no other end."""
    name = _require_label("activity", activity)
    return REFERENCE_DEFINITIONS.get(name)


def validate_activity_record(entry):
    """Check one declared acceptance activity names a method and numbers."""
    _require_mapping("activity entry", entry)
    activity = _require_label("activity", entry.get("activity"))
    method = _require_label("method", entry.get("method"))
    declared = entry.get("conditions")
    if declared is None:
        declared = {}
    _require_mapping("conditions", declared)
    cleaned = {}
    for label, value in declared.items():
        name = _require_label("condition", label)
        if name in cleaned:
            raise ValueError("condition %r appears twice in one activity" % name)
        cleaned[name] = _require_number("condition %r" % name, value)
    return {"activity": activity, "method": method, "conditions": cleaned}


def compare_condition(name, declared, reference):
    """Compare one declared condition against its reference under its sense."""
    label = _require_label("condition", name)
    _require_mapping("reference condition", reference)
    sense = reference.get("sense")
    if sense not in SENSES:
        raise ValueError(
            "condition %r declares sense %r, not one of %s"
            % (label, sense, ", ".join(SENSES))
        )
    value = _require_number("reference value for %r" % label, reference.get("value"))
    observed = _require_number("declared value for %r" % label, declared)

    if sense == SENSE_FLOOR:
        margin = observed - value
        if _close(observed, value):
            state = CONDITION_CONFORMING
        elif _at_least(observed, value):
            state = CONDITION_ESCALATED
        else:
            state = CONDITION_RELAXED
    elif sense == SENSE_CEILING:
        margin = value - observed
        if _close(observed, value):
            state = CONDITION_CONFORMING
        elif _at_most(observed, value):
            state = CONDITION_ESCALATED
        else:
            state = CONDITION_RELAXED
    else:
        tolerance = _require_number(
            "tolerance for %r" % label, reference.get("tolerance")
        )
        if tolerance < 0.0:
            raise ValueError(
                "tolerance for %r must not be negative, got %r" % (label, tolerance)
            )
        margin = observed - value
        state = (
            CONDITION_CONFORMING
            if _at_most(abs(margin), tolerance)
            else CONDITION_OFF_BASELINE
        )
    return {
        "condition": label,
        "sense": sense,
        "declared": observed,
        "reference": value,
        "margin": margin,
        "state": state,
    }


def assess_activity_reuse(entry, policy=None):
    """Grade one acceptance activity against the definition it points at."""
    settings = resolve_reuse_policy(policy)
    record = validate_activity_record(entry)
    activity = record["activity"]
    reference = resolve_reference(activity)

    if reference is None:
        return {
            "activity": activity,
            "method": record["method"],
            "reference_method": None,
            "method_reused": False,
            "conditions": [],
            "omitted": [],
            "invented": sorted(record["conditions"]),
            "verdict": ACTIVITY_REFERENCE_UNRESOLVED,
            "findings": [
                "%s: the acceptance procedure points at a definition the clause "
                "never carries, so the reference has no other end" % activity
            ],
        }

    reference_method = reference["method"]
    method_reused = record["method"] == reference_method
    if not method_reused:
        return {
            "activity": activity,
            "method": record["method"],
            "reference_method": reference_method,
            "method_reused": False,
            "conditions": [],
            "omitted": [],
            "invented": [],
            "verdict": ACTIVITY_METHOD_SUBSTITUTED,
            "findings": [
                "%s: the procedure runs %s where the definition fixes %s; every "
                "condition underneath a substituted method is a tidy table "
                "about nothing"
                % (activity, record["method"], reference_method)
            ],
        }

    reference_conditions = reference["conditions"]
    omitted = sorted(
        name for name in reference_conditions if name not in record["conditions"]
    )
    invented = sorted(
        name for name in record["conditions"] if name not in reference_conditions
    )
    compared = [
        compare_condition(
            name, record["conditions"][name], reference_conditions[name]
        )
        for name in sorted(reference_conditions)
        if name in record["conditions"]
    ]

    findings = []
    for name in omitted:
        findings.append(
            "%s: the procedure omits the referenced condition %s" % (activity, name)
        )
    for name in invented:
        findings.append(
            "%s: the procedure adds condition %s, which the referenced "
            "definition does not carry" % (activity, name)
        )
    for item in compared:
        if item["state"] == CONDITION_RELAXED:
            findings.append(
                "%s: %s is relaxed against the referenced %.6g by %.6g, leaving "
                "acceptance weaker than the definition it inherits"
                % (activity, item["condition"], item["reference"], abs(item["margin"]))
            )
        elif item["state"] == CONDITION_OFF_BASELINE:
            findings.append(
                "%s: %s sits %.6g from the referenced set point of %.6g, outside "
                "its tolerance band"
                % (activity, item["condition"], item["margin"], item["reference"])
            )
        elif item["state"] == CONDITION_ESCALATED:
            findings.append(
                "%s: %s over-tests against the referenced %.6g by %.6g"
                % (activity, item["condition"], item["reference"], abs(item["margin"]))
            )

    states = {item["state"] for item in compared}
    if omitted:
        verdict = ACTIVITY_CONDITION_OMITTED
    elif invented:
        verdict = ACTIVITY_CONDITION_INVENTED
    elif CONDITION_RELAXED in states:
        verdict = ACTIVITY_CONDITION_RELAXED
    elif CONDITION_OFF_BASELINE in states and not settings["carry_off_baseline"]:
        verdict = ACTIVITY_CONDITION_OFF_BASELINE
    elif CONDITION_ESCALATED in states and not settings["carry_escalation"]:
        verdict = ACTIVITY_CONDITION_ESCALATED
    else:
        verdict = ACTIVITY_CONFORMING
    return {
        "activity": activity,
        "method": record["method"],
        "reference_method": reference_method,
        "method_reused": True,
        "conditions": compared,
        "omitted": omitted,
        "invented": invented,
        "verdict": verdict,
        "findings": findings,
    }


def assess_coverglass_reuse(case):
    """Full clause 8.5.3 roll-up over one declared acceptance procedure."""
    _require_mapping("case", case)
    procedure_id = _require_label("procedure_id", case.get("procedure_id"))
    activities = case.get("activities")
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("case must carry a non-empty activities sequence")
    settings = resolve_reuse_policy(case.get("policy"))

    seen = set()
    assessments = []
    for entry in activities:
        assessment = assess_activity_reuse(entry, settings)
        if assessment["activity"] in seen:
            raise ValueError(
                "activity %r appears twice in one procedure" % assessment["activity"]
            )
        seen.add(assessment["activity"])
        assessments.append(assessment)

    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    unreferenced = sorted(name for name in REFERENCE_DEFINITIONS if name not in seen)
    coverage = (len(REFERENCE_DEFINITIONS) - len(unreferenced)) / len(
        REFERENCE_DEFINITIONS
    )
    meets_coverage = _at_least(coverage, settings["min_activity_coverage"])
    if unreferenced and not meets_coverage:
        findings.append(
            "the procedure never picks up %s, so those definitions are pointed "
            "at by the clause and reached by nobody" % ", ".join(unreferenced)
        )

    grouped = {}
    for assessment in assessments:
        grouped.setdefault(assessment["verdict"], []).append(assessment["activity"])
    for names in grouped.values():
        names.sort()

    weakest = min(
        assessments, key=lambda a: (ACTIVITY_RANK[a["verdict"]], a["activity"])
    )
    reused = [a for a in assessments if a["verdict"] == ACTIVITY_CONFORMING]
    reuse_fraction = len(reused) / len(assessments)

    if len(reused) == len(assessments) and meets_coverage:
        verdict = PROCEDURE_REUSES_DEFINITIONS
    else:
        verdict = PROCEDURE_DEPARTS_FROM_DEFINITIONS
    return {
        "procedure_id": procedure_id,
        "activities": assessments,
        "grouped_activities": grouped,
        "unreferenced_definitions": unreferenced,
        "definition_coverage": coverage,
        "meets_coverage": meets_coverage,
        "reuse_fraction": reuse_fraction,
        "weakest_activity": weakest["activity"],
        "verdict": verdict,
        "findings": findings,
    }
