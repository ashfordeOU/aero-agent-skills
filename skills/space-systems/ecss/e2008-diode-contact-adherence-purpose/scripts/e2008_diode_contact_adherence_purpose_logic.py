#!/usr/bin/env python3
"""Why the attachment strength of protection diode contacts is verified,
and only where contacts are actually present.

Anchor: ECSS-E-ST-20-08C clause 9.6.6.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause carries a condition before it carries a requirement. A
protection diode reaches the panel in more than one construction: some
devices arrive with terminals attached to the die, ready to be welded
into the interconnect run, and some arrive as a bare die or as a
diffused region with nothing attached at all. Only the first kind has an
attachment whose strength can be pulled, and applying the check to the
second kind produces a number about the grip of the tooling.

Where contacts are present, the strength has to survive everything the
device meets after acceptance:

    interconnect welding    a terminal is welded into the string, and
                            the weld schedule heats the attachment it
                            is being made to
    bonding and cure        adhesive shrinks as it cures and puts a
                            standing load on the attachment before the
                            panel has moved at all
    panel handling          the device is touched, masked, probed and
                            moved through integration
    launch vibration        broadband random loading, at the worst
                            moment to lose a protection path
    thermal cycling         the attachment takes the coefficient
                            mismatch as a shear, cycle after cycle, for
                            the whole mission

Each of those is only worth declaring if something is recorded against
it, so each maps onto the evidence parameter it is watched through.
Their weights sum to one, which makes the demand index a share of the
downstream life the pull is being asked to stand for: a device meeting
almost none of them does not earn the destructive check, and a device
meeting most of them does.

Two numbers then decide whether the planned check can produce a usable
result: the pull load, which is the service peak multiplied by a
declared margin, and the sample, which has to be large enough as both a
share of the lot and an absolute device count for a result to speak for
anything beyond the devices pulled.

The margin, floors and weights below are a declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTACTS_PRESENT = "attached-contacts-present"
NO_ATTACHED_CONTACTS = "no-attached-contacts"

CONTACT_PRESENCE_CATEGORIES = (CONTACTS_PRESENT, NO_ATTACHED_CONTACTS)

# Downstream stressor -> the evidence parameter it is watched through.
DOWNSTREAM_STRESSORS = {
    "interconnect-welding-to-diode-terminal": "terminal-weld-pull-strength",
    "diode-bonding-cure-shrinkage": "die-attach-shear-strength",
    "panel-integration-handling": "terminal-peel-strength",
    "launch-random-vibration": "terminal-fatigue-margin",
    "orbital-thermal-cycling": "attachment-resistance-drift",
}

RECOGNISED_STRESSORS = tuple(sorted(DOWNSTREAM_STRESSORS))

# Share of the downstream life each stressor accounts for. Sums to one.
STRESSOR_WEIGHTS = {
    "interconnect-welding-to-diode-terminal": 0.30,
    "diode-bonding-cure-shrinkage": 0.15,
    "panel-integration-handling": 0.15,
    "launch-random-vibration": 0.20,
    "orbital-thermal-cycling": 0.20,
}

COMMON_OBJECTIVE = "protection-diode-attachment-integrity-evidence"

ADHERENCE_NOT_APPLICABLE = "diode-contact-adherence-not-applicable"
STRESSORS_NOT_DECLARED = "diode-contact-stressors-not-declared"
DEMAND_BELOW_THRESHOLD = "diode-contact-adherence-demand-below-threshold"
PULL_LOAD_INSUFFICIENT = "diode-contact-pull-load-insufficient"
SAMPLE_COVERAGE_INSUFFICIENT = "diode-contact-sample-coverage-insufficient"
ADHERENCE_JUSTIFIED = "diode-contact-adherence-verification-justified"

PURPOSE_VERDICTS = (
    ADHERENCE_NOT_APPLICABLE,
    STRESSORS_NOT_DECLARED,
    DEMAND_BELOW_THRESHOLD,
    PULL_LOAD_INSUFFICIENT,
    SAMPLE_COVERAGE_INSUFFICIENT,
    ADHERENCE_JUSTIFIED,
)

DEFAULT_DIODE_ADHERENCE_POLICY = {
    "pull_load_margin": 1.5,
    "min_demand_index": 0.25,
    "min_sample_coverage": 0.10,
    "min_sample_devices": 3,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_diode_adherence_policy(policy):
    """Check a diode contact adherence purpose policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive("pull_load_margin", policy.get("pull_load_margin"))
    if margin < 1.0:
        raise ValueError(
            "pull_load_margin %g would pull below the service peak it is a "
            "margin on" % (margin,)
        )
    _require_fraction("min_demand_index", policy.get("min_demand_index"))
    _require_fraction("min_sample_coverage", policy.get("min_sample_coverage"))
    _require_count("min_sample_devices", policy.get("min_sample_devices"))
    return policy


def contact_presence_category(diode):
    """Whether this device carries attached contacts the check can pull."""
    if not isinstance(diode, dict):
        raise ValueError("diode must be a mapping, got %r" % (diode,))
    count = diode.get("attached_contact_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(
            "diode attached_contact_count must be a whole number of zero or "
            "more, got %r" % (count,)
        )
    if count == 0:
        return NO_ATTACHED_CONTACTS
    return CONTACTS_PRESENT


def stressor_evidence_map(stressors):
    """Map each declared stressor onto the parameter it is watched through."""
    if isinstance(stressors, (str, bytes)) or not hasattr(stressors, "__iter__"):
        raise ValueError("stressors must be a sequence, got %r" % (stressors,))
    mapped = {}
    for stressor in stressors:
        if stressor not in DOWNSTREAM_STRESSORS:
            raise ValueError(
                "unrecognised downstream stressor %r; known stressors are %s"
                % (stressor, ", ".join(RECOGNISED_STRESSORS))
            )
        mapped[stressor] = DOWNSTREAM_STRESSORS[stressor]
    if mapped:
        mapped[COMMON_OBJECTIVE] = "protection-diode-attachment-pull-record"
    return mapped


def attachment_demand_index(stressors):
    """Share of the downstream life the declared stressors account for."""
    if isinstance(stressors, (str, bytes)) or not hasattr(stressors, "__iter__"):
        raise ValueError("stressors must be a sequence, got %r" % (stressors,))
    seen = set()
    total = 0.0
    for stressor in stressors:
        if stressor not in STRESSOR_WEIGHTS:
            raise ValueError(
                "unrecognised downstream stressor %r; known stressors are %s"
                % (stressor, ", ".join(RECOGNISED_STRESSORS))
            )
        if stressor in seen:
            continue
        seen.add(stressor)
        total += STRESSOR_WEIGHTS[stressor]
    return total


def required_pull_load_n(
    service_peak_load_n, policy=DEFAULT_DIODE_ADHERENCE_POLICY
):
    """Pull load the service peak and its declared margin together ask for."""
    validate_diode_adherence_policy(policy)
    peak = _require_positive("service_peak_load_n", service_peak_load_n)
    return peak * float(policy["pull_load_margin"])


def adherence_sample_coverage(sample_devices, lot_devices):
    """Share of the lot the planned destructive sample represents."""
    sample = _require_count("sample_devices", sample_devices)
    lot = _require_count("lot_devices", lot_devices)
    if sample > lot:
        raise ValueError(
            "sample_devices %d cannot exceed the %d devices in the lot"
            % (sample, lot)
        )
    return sample / lot


def assess_diode_adherence_purpose(case, policy=DEFAULT_DIODE_ADHERENCE_POLICY):
    """Full clause 9.6.6.2.1 judgement for one adherence verification case."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_diode_adherence_policy(policy)
    diode = case.get("diode")
    if diode is None:
        raise ValueError("case is missing a diode block")

    presence = contact_presence_category(diode)
    findings = []
    result = {
        "contact_presence": presence,
        "demand_index": 0.0,
        "evidence_map": {},
        "findings": findings,
    }

    if presence == NO_ATTACHED_CONTACTS:
        result["verdict"] = ADHERENCE_NOT_APPLICABLE
        result["rationale"] = (
            "the device carries no attached contacts, so there is no "
            "attachment for a pull to describe"
        )
        return result

    stressors = case.get("stressors")
    if stressors is None:
        raise ValueError("case is missing a stressors list")
    demand = attachment_demand_index(stressors)
    result["demand_index"] = demand
    result["evidence_map"] = stressor_evidence_map(stressors)

    if not result["evidence_map"]:
        result["verdict"] = STRESSORS_NOT_DECLARED
        result["rationale"] = (
            "no downstream stressor is declared, so nothing states what the "
            "attachment is being asked to survive"
        )
        findings.append(
            "the case declares no downstream stressor against the attachment"
        )
        return result

    planned = case.get("planned_pull")
    if not isinstance(planned, dict):
        raise ValueError("case is missing a planned_pull block")
    peak = _require_positive(
        "planned_pull service_peak_load_n", planned.get("service_peak_load_n")
    )
    applied = _require_positive(
        "planned_pull planned_pull_load_n", planned.get("planned_pull_load_n")
    )
    required = required_pull_load_n(peak, policy)
    result["required_pull_load_n"] = required
    result["planned_pull_load_n"] = applied

    sample = case.get("sample")
    if not isinstance(sample, dict):
        raise ValueError("case is missing a sample block")
    sample_devices = _require_count("sample devices", sample.get("devices"))
    lot_devices = _require_count("sample lot_devices", sample.get("lot_devices"))
    coverage = adherence_sample_coverage(sample_devices, lot_devices)
    result["sample_coverage"] = coverage
    result["sample_devices"] = sample_devices

    demand_low = not _at_least(demand, float(policy["min_demand_index"]))
    if demand_low:
        findings.append(
            "the declared stressors account for %.4f of the downstream life "
            "against the %.4f that earns a destructive pull"
            % (demand, float(policy["min_demand_index"]))
        )

    pull_low = not _at_least(applied, required)
    if pull_low:
        findings.append(
            "the plan pulls to %.3f N against the %.3f N the %.3f N service "
            "peak and its margin ask for"
            % (applied, required, peak)
        )

    coverage_low = not _at_least(coverage, float(policy["min_sample_coverage"]))
    devices_low = not _at_least(
        sample_devices, float(policy["min_sample_devices"])
    )
    if coverage_low:
        findings.append(
            "the sample covers %.4f of the lot against the %.4f a result needs "
            "to speak for it" % (coverage, float(policy["min_sample_coverage"]))
        )
    if devices_low:
        findings.append(
            "the sample pulls %d devices against the %d minimum"
            % (sample_devices, int(policy["min_sample_devices"]))
        )

    if demand_low:
        result["verdict"] = DEMAND_BELOW_THRESHOLD
    elif pull_low:
        result["verdict"] = PULL_LOAD_INSUFFICIENT
    elif coverage_low or devices_low:
        result["verdict"] = SAMPLE_COVERAGE_INSUFFICIENT
    else:
        result["verdict"] = ADHERENCE_JUSTIFIED
    result["rationale"] = (
        "attached contacts are present and %d downstream stressors are watched "
        "through their evidence parameters"
        % (len(result["evidence_map"]) - 1,)
    )
    return result
