#!/usr/bin/env python3
"""Purpose of the bare-cell contact and diode attachment adherence check.

Anchor: ECSS-E-ST-20-08C clause 7.5.7.2.1. The reasoning below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare solar cell arrives with metallised contacts on both faces and,
where it carries one, a bypass diode already attached. None of those
joints is loaded on the cell as delivered. They are loaded later --
when an interconnect is welded or soldered to them, when the coverglass
adhesive cures against them, when the panel is handled, when the launch
shakes it and when the orbit cycles it. So the strength worth knowing is
not the strength of a joint fresh off the line; it is the strength that
is left after the cell has been through the environment that weakens it.

That is what makes this a post-conditioning check. A pull applied to an
unconditioned cell reports the as-built joint, which nobody doubted. The
number the clause is after is the survivable joint, so the assessment
below refuses to sentence a plan whose pull comes before any
conditioning at all -- that plan produces a number, but not this one.

Three questions decide whether the check earns its place:

    demand        which downstream attachment steps and environments
                  actually load the contacts, added into one index
    conditioning  does something weakening happen before the pull
    capability    can the planned pull reach the load the service
                  case demands, with its margin, on the sample size
                  that lets the result speak for the lot

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Downstream steps that put load into a bare-cell contact or diode
# attachment, with the objective the adherence check demonstrates for
# each and the severity it contributes to the demand index. Severities
# are declared engineering policy, not physical constants.
ATTACHMENT_STRESSORS = {
    "interconnect-welding": (
        "contact-survives-the-weld-schedule",
        1.2,
    ),
    "interconnect-soldering": (
        "contact-survives-solder-thermal-shock",
        1.0,
    ),
    "diode-attachment-joining": (
        "diode-attachment-survives-its-own-joining",
        0.8,
    ),
    "coverglass-adhesive-cure": (
        "contact-survives-the-adhesive-cure",
        0.5,
    ),
    "panel-integration-handling": (
        "contact-survives-handling-loads",
        0.6,
    ),
    "launch-vibration": (
        "contact-survives-launch-loads",
        0.9,
    ),
    "orbital-thermal-cycling": (
        "contact-survives-cycling-shear",
        1.4,
    ),
}

RECOGNISED_STRESSORS = tuple(sorted(ATTACHMENT_STRESSORS))

# Steps that weaken a joint, so a pull placed after one of them reports
# a survivable strength rather than an as-built strength.
CONDITIONING_STEPS = (
    "humidity-soak",
    "thermal-cycling",
    "thermal-shock",
    "vacuum-bake",
)

PULL_STEP = "contact-pull-test"

CONTACT_ADHERENCE_PURPOSE_SERVED = "contact-adherence-purpose-served"
CONTACT_ADHERENCE_CHECK_NOT_REQUIRED = "contact-adherence-check-not-required"
CONTACT_ADHERENCE_NOT_CONDITIONED = "contact-adherence-not-conditioned"
CONTACT_ADHERENCE_PLAN_INADEQUATE = "contact-adherence-plan-inadequate"

PURPOSE_VERDICTS = (
    CONTACT_ADHERENCE_PURPOSE_SERVED,
    CONTACT_ADHERENCE_CHECK_NOT_REQUIRED,
    CONTACT_ADHERENCE_NOT_CONDITIONED,
    CONTACT_ADHERENCE_PLAN_INADEQUATE,
)

# Declared scoping policy: project numbers, not physical constants.
DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY = {
    "check_required_demand_index": 1.0,
    "required_pull_safety_factor": 2.0,
    "min_sample_fraction": 0.02,
    "min_samples": 3,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A demand index is a sum of declared severities and a required load is
    a product, so a case built to sit exactly on a threshold can land a
    few units in the last place below it. The threshold is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_contact_adherence_purpose_policy(
    policy=DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY,
):
    """Check a scoping policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    _require_positive(
        "check_required_demand_index", policy.get("check_required_demand_index")
    )
    factor = _require_positive(
        "required_pull_safety_factor", policy.get("required_pull_safety_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "required_pull_safety_factor must be at least 1.0, got %r" % (factor,)
        )
    fraction = _require_non_negative(
        "min_sample_fraction", policy.get("min_sample_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "min_sample_fraction must not exceed 1.0, got %r" % (fraction,)
        )
    _require_count("min_samples", policy.get("min_samples"))
    return policy


def normalise_stressors(stressors):
    """Read a declared stressor list, refusing unknown or repeated tokens."""
    items = _require_sequence("stressors", stressors)
    seen = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError("stressor must be a string, got %r" % (item,))
        token = item.strip().lower()
        if token not in ATTACHMENT_STRESSORS:
            raise ValueError(
                "unknown attachment stressor %r; recognised: %s"
                % (item, ", ".join(RECOGNISED_STRESSORS))
            )
        if token in seen:
            raise ValueError(
                "attachment stressor %r declared twice; it would be counted twice "
                "into the demand index" % (token,)
            )
        seen.append(token)
    return tuple(seen)


def attachment_demand_index(stressors):
    """Add the declared stressors into one demand on the contact joints.

    A cell whose contacts are only ever handled carries a small demand; a
    cell that is welded, cured, launched and then cycled carries a large
    one, and the check is scoped to the total rather than to whichever
    step is remembered first.
    """
    return sum(ATTACHMENT_STRESSORS[token][1] for token in normalise_stressors(stressors))


def demonstration_objectives(stressors):
    """What the adherence check has to demonstrate, one item per stressor."""
    return tuple(
        sorted({ATTACHMENT_STRESSORS[token][0] for token in normalise_stressors(stressors)})
    )


def check_is_required(demand_index, policy=DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY):
    """Does the accumulated demand justify pulling contacts at all?"""
    validate_contact_adherence_purpose_policy(policy)
    index = _require_non_negative("demand_index", demand_index)
    return _at_least(index, float(policy["check_required_demand_index"]))


def required_pull_load_n(
    peak_service_load_n, policy=DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY
):
    """Load the pull has to reach: the service peak times its margin."""
    validate_contact_adherence_purpose_policy(policy)
    peak = _require_positive("peak_service_load_n", peak_service_load_n)
    return peak * float(policy["required_pull_safety_factor"])


def pull_capability_adequacy(planned_pull_load_n, required_load_n):
    """Can the planned pull actually reach the load the service demands?

    A bench that stops below the required load cannot tell a joint that
    would have held from one that would not, so the shortfall is reported
    in newtons and the plan is repaired rather than sentenced.
    """
    planned = _require_positive("planned_pull_load_n", planned_pull_load_n)
    required = _require_positive("required_load_n", required_load_n)
    adequate = _at_least(planned, required)
    findings = []
    if not adequate:
        findings.append(
            "planned pull load %.3f N is below the %.3f N the service case "
            "demands, so a joint that fails in service can still pass the bench"
            % (planned, required)
        )
    return {
        "adequate": adequate,
        "planned_pull_load_n": planned,
        "required_load_n": required,
        "shortfall_n": max(0.0, required - planned),
        "coverage_ratio": planned / required,
        "findings": findings,
    }


def conditioning_before_pull(sequence):
    """Does anything weakening happen before the contacts are pulled?

    The clause asks for the strength that is left after conditioning, so
    the order of the recorded steps is the whole evidence. Conditioning
    logged after the pull is a sequencing error: it weakened nothing that
    the recorded number describes, and it is named rather than credited.
    """
    steps = _require_sequence("sequence", sequence)
    tokens = []
    for step in steps:
        if not isinstance(step, str):
            raise ValueError("sequence step must be a string, got %r" % (step,))
        tokens.append(step.strip().lower())
    if PULL_STEP not in tokens:
        raise ValueError(
            "sequence carries no %r step, so there is no adherence result to "
            "place against the conditioning" % (PULL_STEP,)
        )
    cut = tokens.index(PULL_STEP)
    before = tuple(token for token in tokens[:cut] if token in CONDITIONING_STEPS)
    after = tuple(token for token in tokens[cut + 1 :] if token in CONDITIONING_STEPS)
    findings = []
    if not before:
        findings.append(
            "the pull comes before any conditioning, so it reports the as-built "
            "joint rather than the joint the mission leaves behind"
        )
    if after:
        findings.append(
            "conditioning recorded after the pull (%s) weakened nothing the "
            "recorded adherence describes" % (", ".join(after),)
        )
    return {
        "conditioned": bool(before),
        "conditioning_before_pull": before,
        "conditioning_after_pull": after,
        "findings": findings,
    }


def sample_coverage(
    samples, lot_size, policy=DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY
):
    """Does the planned sample let the result speak for the delivered lot?"""
    validate_contact_adherence_purpose_policy(policy)
    taken = _require_count("samples", samples)
    lot = _require_count("lot_size", lot_size)
    if taken > lot:
        raise ValueError(
            "samples %d exceeds the lot size %d" % (taken, lot)
        )
    fraction = taken / lot
    floor_fraction = float(policy["min_sample_fraction"])
    floor_count = int(policy["min_samples"])
    enough_fraction = _at_least(fraction, floor_fraction)
    enough_count = taken >= floor_count
    findings = []
    if not enough_count:
        findings.append(
            "%d sample(s) is below the floor of %d, so one unlucky cell decides "
            "the lot" % (taken, floor_count)
        )
    if not enough_fraction:
        findings.append(
            "sample fraction %.4f is below the declared floor %.4f"
            % (fraction, floor_fraction)
        )
    return {
        "samples": taken,
        "lot_size": lot,
        "sample_fraction": fraction,
        "sufficient": enough_count and enough_fraction,
        "findings": findings,
    }


def assess_cell_contact_adherence_purpose(
    case, policy=DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY
):
    """Full clause 7.5.7.2.1 scoping assessment with a verdict."""
    validate_contact_adherence_purpose_policy(policy)
    _require_mapping("case", case)

    stressors = normalise_stressors(case.get("attachment_stressors"))
    index = attachment_demand_index(stressors)
    objectives = demonstration_objectives(stressors)
    required = check_is_required(index, policy)

    result = {
        "cell_lot_id": case.get("cell_lot_id"),
        "attachment_stressors": stressors,
        "demand_index": index,
        "demonstration_objectives": objectives,
        "check_required": required,
        "findings": [],
    }

    if not required:
        result.update(
            {
                "adequate": None,
                "verdict": CONTACT_ADHERENCE_CHECK_NOT_REQUIRED,
                "conditioned": None,
                "required_pull_load_n": None,
                "sample_fraction": None,
            }
        )
        result["findings"].append(
            "declared demand index %.3f stays under the %.3f that makes a contact "
            "adherence check worth running" % (index, float(policy["check_required_demand_index"]))
        )
        return result

    conditioning = conditioning_before_pull(case.get("planned_sequence"))
    required_load = required_pull_load_n(case.get("peak_service_load_n"), policy)
    capability = pull_capability_adequacy(
        case.get("planned_pull_load_n"), required_load
    )
    coverage = sample_coverage(
        case.get("samples"), case.get("lot_size"), policy
    )

    findings = result["findings"]
    findings.extend(conditioning["findings"])
    findings.extend(capability["findings"])
    findings.extend(coverage["findings"])

    result.update(
        {
            "conditioned": conditioning["conditioned"],
            "conditioning_before_pull": conditioning["conditioning_before_pull"],
            "conditioning_after_pull": conditioning["conditioning_after_pull"],
            "required_pull_load_n": required_load,
            "planned_pull_load_n": capability["planned_pull_load_n"],
            "pull_shortfall_n": capability["shortfall_n"],
            "pull_capability_adequate": capability["adequate"],
            "sample_fraction": coverage["sample_fraction"],
            "sample_sufficient": coverage["sufficient"],
        }
    )

    if not conditioning["conditioned"]:
        result.update(
            {
                "adequate": False,
                "verdict": CONTACT_ADHERENCE_NOT_CONDITIONED,
            }
        )
        return result

    adequate = capability["adequate"] and coverage["sufficient"]
    result.update(
        {
            "adequate": adequate,
            "verdict": CONTACT_ADHERENCE_PURPOSE_SERVED
            if adequate
            else CONTACT_ADHERENCE_PLAN_INADEQUATE,
        }
    )
    return result
