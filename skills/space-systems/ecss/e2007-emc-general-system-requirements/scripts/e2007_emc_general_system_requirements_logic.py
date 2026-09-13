#!/usr/bin/env python3
"""System-level electromagnetic policy and charging-protection audit.

Anchor: ECSS-E-ST-20-07C clause 4.1 (general system requirements). The
clause is paraphrased into an implementable procedure; no standard text
is reproduced.

The clause is a pointer clause: it requires that a system-level
electromagnetic policy exists and that a spacecraft-charging protection
programme is declared. The auditable objects are therefore policy
elements (documents with an owner, a release state and a baselining
milestone), unit electromagnetic roles, and the charging-protection task
set driven by the mission orbit-regime.

Stdlib only, deterministic, offline.
"""

import math

# --- programme vocabulary ---------------------------------------------------

MANDATORY_ELEMENTS = (
    "emc-control-plan",
    "electromagnetic-effects-verification-plan",
    "grounding-and-bonding-policy",
    "magnetic-cleanliness-policy",
    "radiation-hazard-policy",
    "charging-protection-programme",
)

OPTIONAL_ELEMENTS = (
    "intersystem-compatibility-policy",
    "lightning-protection-policy",
)

KNOWN_ELEMENTS = MANDATORY_ELEMENTS + OPTIONAL_ELEMENTS

RELEASE_STATES = ("draft", "released", "baselined", "withdrawn")
ON_RECORD_STATES = ("released", "baselined")

MILESTONES = ("srr", "pdr", "cdr", "qr", "ar")

# Latest milestone by which each mandatory element must be on record.
LATEST_BASELINE_MILESTONE = {
    "emc-control-plan": "pdr",
    "grounding-and-bonding-policy": "pdr",
    "electromagnetic-effects-verification-plan": "cdr",
    "magnetic-cleanliness-policy": "cdr",
    "charging-protection-programme": "cdr",
    "radiation-hazard-policy": "qr",
}

# --- unit roles -------------------------------------------------------------

ROLE_INTENTIONAL_EMITTER = "intentional-emitter"
ROLE_INTENTIONAL_RECEIVER = "intentional-receiver"
ROLE_NON_INTENTIONAL_SOURCE = "non-intentional-source"
ROLE_SUSCEPTIBLE_VICTIM = "susceptible-victim"

ROLE_ORDER = (
    ROLE_INTENTIONAL_EMITTER,
    ROLE_INTENTIONAL_RECEIVER,
    ROLE_NON_INTENTIONAL_SOURCE,
    ROLE_SUSCEPTIBLE_VICTIM,
)

# --- charging-protection tasks ---------------------------------------------

TASK_SURFACE = "surface-charging-protection"
TASK_INTERNAL = "internal-charging-protection"
TASK_AURORAL = "auroral-charging-protection"
TASK_GROUNDING_RETURN = "structure-return-bonding-verification"
TASK_ESD_SUSCEPTIBILITY = "esd-susceptibility-demonstration"

BASELINE_CHARGING_TASKS = (TASK_GROUNDING_RETURN, TASK_ESD_SUSCEPTIBILITY)

ORBIT_REGIME_TASKS = {
    "leo-low-inclination": BASELINE_CHARGING_TASKS,
    "leo-polar": BASELINE_CHARGING_TASKS + (TASK_SURFACE, TASK_AURORAL),
    "meo": BASELINE_CHARGING_TASKS + (TASK_SURFACE, TASK_INTERNAL),
    "geo": BASELINE_CHARGING_TASKS + (TASK_SURFACE, TASK_INTERNAL),
    "heo": BASELINE_CHARGING_TASKS + (TASK_SURFACE, TASK_INTERNAL, TASK_AURORAL),
}

RATIO_TOLERANCE = 1e-9


# --- normalization ----------------------------------------------------------


def normalize_element(raw):
    """Normalize one declared policy element record.

    Raises ValueError on a non-mapping record, a blank identifier, an
    unrecognised element type, an unrecognised release state, a blank
    owner or an unrecognised milestone.
    """
    if not isinstance(raw, dict):
        raise ValueError("policy element record must be a mapping")
    ident = str(raw.get("id", "")).strip()
    if not ident:
        raise ValueError("policy element needs a non-blank id")
    kind = str(raw.get("kind", "")).strip().lower()
    if kind not in KNOWN_ELEMENTS:
        raise ValueError("unrecognised policy element type: %r" % (raw.get("kind"),))
    state = str(raw.get("state", "")).strip().lower()
    if state not in RELEASE_STATES:
        raise ValueError("unrecognised release state: %r" % (raw.get("state"),))
    owner = str(raw.get("owner", "")).strip()
    if not owner:
        raise ValueError("policy element %s needs a named owner" % ident)
    milestone = str(raw.get("milestone", "")).strip().lower()
    if milestone not in MILESTONES:
        raise ValueError("unrecognised milestone: %r" % (raw.get("milestone"),))
    return {
        "id": ident,
        "kind": kind,
        "state": state,
        "owner": owner,
        "milestone": milestone,
        "on_record": state in ON_RECORD_STATES,
    }


def normalize_elements(records):
    """Normalize a sequence of element records, rejecting duplicate types."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("policy elements must be given as a list or tuple")
    out = []
    seen = set()
    for rec in records:
        element = normalize_element(rec)
        if element["kind"] in seen:
            raise ValueError("duplicate policy element type: %s" % element["kind"])
        seen.add(element["kind"])
        out.append(element)
    return tuple(out)


# --- coverage checks --------------------------------------------------------


def missing_mandatory_elements(elements):
    """Mandatory element types with no declared entry at all."""
    present = {e["kind"] for e in elements}
    return tuple(k for k in MANDATORY_ELEMENTS if k not in present)


def unapproved_mandatory_elements(elements):
    """Mandatory element types that exist but are not on record."""
    out = []
    for element in elements:
        if element["kind"] in MANDATORY_ELEMENTS and not element["on_record"]:
            out.append(element["kind"])
    return tuple(sorted(out))


def milestone_index(milestone):
    """Position of a review milestone in the programme sequence."""
    key = str(milestone).strip().lower()
    if key not in MILESTONES:
        raise ValueError("unrecognised milestone: %r" % (milestone,))
    return MILESTONES.index(key)


def late_baseline_elements(elements):
    """Mandatory on-record elements baselined later than allowed."""
    out = []
    for element in elements:
        kind = element["kind"]
        if kind not in LATEST_BASELINE_MILESTONE or not element["on_record"]:
            continue
        allowed = LATEST_BASELINE_MILESTONE[kind]
        if milestone_index(element["milestone"]) > milestone_index(allowed):
            out.append((kind, element["milestone"], allowed))
    return tuple(sorted(out))


def policy_coverage_ratio(elements):
    """Fraction of mandatory element types that are on record."""
    on_record = {e["kind"] for e in elements if e["on_record"]}
    hits = sum(1 for k in MANDATORY_ELEMENTS if k in on_record)
    return hits / float(len(MANDATORY_ELEMENTS))


def coverage_meets_target(ratio, target, tolerance=RATIO_TOLERANCE):
    """True when the coverage ratio reaches the target.

    The ratio is a quotient of small integers and the target a decimal,
    so an exactly-met target can land a few units in the last place
    below it. The representation error is absorbed here; the engineering
    target itself is never lowered.
    """
    if not isinstance(target, (int, float)) or isinstance(target, bool):
        raise ValueError("coverage target must be numeric")
    if not 0.0 <= float(target) <= 1.0:
        raise ValueError("coverage target must lie between 0 and 1")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    return ratio > target or math.isclose(
        ratio, target, rel_tol=0.0, abs_tol=tolerance
    )


# --- unit roles -------------------------------------------------------------


def categorize_unit(raw):
    """Derive the electromagnetic roles of one unit from its attributes.

    Raises ValueError on a non-mapping record, a blank identifier, a
    negative transmit power, or a unit that declares no attribute
    mapping to any role (an uncategorized unit escapes the control
    plan and is therefore rejected, not defaulted).
    """
    if not isinstance(raw, dict):
        raise ValueError("unit record must be a mapping")
    ident = str(raw.get("id", "")).strip()
    if not ident:
        raise ValueError("unit needs a non-blank id")
    roles = []
    transmit_w = raw.get("transmit_power_w")
    if transmit_w is not None:
        if not isinstance(transmit_w, (int, float)) or isinstance(transmit_w, bool):
            raise ValueError("unit %s transmit_power_w must be numeric" % ident)
        if transmit_w < 0.0:
            raise ValueError("unit %s transmit_power_w must not be negative" % ident)
        if transmit_w > 0.0:
            roles.append(ROLE_INTENTIONAL_EMITTER)
    sensitivity = raw.get("receive_sensitivity_dbm")
    if sensitivity is not None:
        if not isinstance(sensitivity, (int, float)) or isinstance(sensitivity, bool):
            raise ValueError("unit %s receive_sensitivity_dbm must be numeric" % ident)
        roles.append(ROLE_INTENTIONAL_RECEIVER)
    if bool(raw.get("switching_converter")) or bool(raw.get("clocked_digital")):
        roles.append(ROLE_NON_INTENTIONAL_SOURCE)
    threshold = raw.get("susceptibility_threshold_dbm")
    if threshold is not None:
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise ValueError(
                "unit %s susceptibility_threshold_dbm must be numeric" % ident
            )
        roles.append(ROLE_SUSCEPTIBLE_VICTIM)
    if not roles:
        raise ValueError("unit %s is uncategorized: no electromagnetic role" % ident)
    ordered = tuple(r for r in ROLE_ORDER if r in roles)
    return {"id": ident, "roles": ordered}


def role_inventory(units):
    """Count units per electromagnetic role across a unit list."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be given as a list or tuple")
    counts = dict((role, 0) for role in ROLE_ORDER)
    for raw in units:
        for role in categorize_unit(raw)["roles"]:
            counts[role] += 1
    return counts


# --- charging-protection programme ------------------------------------------


def required_charging_tasks(orbit_regime):
    """Charging-protection tasks driven by the mission orbit-regime."""
    key = str(orbit_regime).strip().lower()
    if key not in ORBIT_REGIME_TASKS:
        raise ValueError("unrecognised orbit regime: %r" % (orbit_regime,))
    return tuple(sorted(ORBIT_REGIME_TASKS[key]))


def charging_programme_findings(declared_tasks, orbit_regime):
    """Compare the declared charging tasks against the regime-driven set."""
    if not isinstance(declared_tasks, (list, tuple, set, frozenset)):
        raise ValueError("declared charging tasks must be a list, tuple or set")
    declared = set()
    for task in declared_tasks:
        name = str(task).strip().lower()
        if not name:
            raise ValueError("charging task name must not be blank")
        declared.add(name)
    required = set(required_charging_tasks(orbit_regime))
    return {
        "required": tuple(sorted(required)),
        "missing": tuple(sorted(required - declared)),
        "over_declared": tuple(sorted(declared - required)),
    }


# --- top-level assessment ---------------------------------------------------


def assess_emc_policy(
    element_records,
    units,
    orbit_regime,
    declared_charging_tasks,
    coverage_target=1.0,
):
    """Run the full clause 4.1 system-level policy audit."""
    elements = normalize_elements(element_records)
    missing = missing_mandatory_elements(elements)
    unapproved = unapproved_mandatory_elements(elements)
    late = late_baseline_elements(elements)
    ratio = policy_coverage_ratio(elements)
    charging = charging_programme_findings(declared_charging_tasks, orbit_regime)
    inventory = role_inventory(units)
    findings = []
    for kind in missing:
        findings.append("missing-policy-element:%s" % kind)
    for kind in unapproved:
        findings.append("policy-element-not-on-record:%s" % kind)
    for kind, actual, allowed in late:
        findings.append("late-baseline:%s:%s-after-%s" % (kind, actual, allowed))
    for task in charging["missing"]:
        findings.append("missing-charging-task:%s" % task)
    if not coverage_meets_target(ratio, coverage_target):
        findings.append("coverage-below-target:%.4f" % ratio)
    return {
        "orbit_regime": str(orbit_regime).strip().lower(),
        "coverage_ratio": ratio,
        "missing_elements": missing,
        "unapproved_elements": unapproved,
        "late_baseline_elements": late,
        "charging": charging,
        "role_inventory": inventory,
        "findings": tuple(findings),
        "compliant": not findings,
    }
