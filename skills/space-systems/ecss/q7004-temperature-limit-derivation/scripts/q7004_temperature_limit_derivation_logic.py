#!/usr/bin/env python3
"""Derivation of thermal test temperature limits from environmental data.

Anchor: ECSS-Q-ST-70-04C, test condition clauses on temperature limits.
The procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A test limit is never the predicted temperature. It is the predicted
temperature widened by a build-up of declared increments, and every
increment answers a different question.

    uncertainty   how well the prediction itself is known, which follows
                  the data basis: measured hardware, a model correlated
                  against test data, or an uncorrelated model
    acceptance    the workmanship band a delivered item is verified over
    qualification the further band a design is demonstrated over

The build-up runs outward from the prediction: prediction to design
limits, design to acceptance limits, acceptance to qualification limits.
An acceptance run stops at the acceptance limits; a qualification run
goes to the qualification limits.

The build-up is a declared project policy, not a physical constant, and
it is bounded twice. A programme ceiling caps the total widening, and the
hardware's own capability caps it again: a derived limit beyond what the
material or the part can survive is a limit that damages the item in the
chamber rather than demonstrating anything about the mission.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MEASURED_HARDWARE = "measured-hardware"
CORRELATED_MODEL = "correlated-model"
UNCORRELATED_MODEL = "uncorrelated-model"
DATA_BASES = (MEASURED_HARDWARE, CORRELATED_MODEL, UNCORRELATED_MODEL)

ACCEPTANCE = "acceptance"
QUALIFICATION = "qualification"
OBJECTIVES = (ACCEPTANCE, QUALIFICATION)

DEFAULT_LIMIT_POLICY = {
    "uncertainty_margin_k": {
        MEASURED_HARDWARE: 0.0,
        CORRELATED_MODEL: 5.0,
        UNCORRELATED_MODEL: 15.0,
    },
    "acceptance_margin_k": 5.0,
    "qualification_margin_k": 10.0,
    "max_total_margin_k": 25.0,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_limit_policy(policy):
    """Check a limit build-up policy covers every data basis with sane numbers."""
    _require_mapping("policy", policy)
    table = _require_mapping(
        "policy uncertainty_margin_k", policy.get("uncertainty_margin_k")
    )
    missing = set(DATA_BASES) - set(table)
    if missing:
        raise ValueError(
            "policy uncertainty_margin_k is missing: %s" % ", ".join(sorted(missing))
        )
    for basis in DATA_BASES:
        _require_non_negative("policy uncertainty_margin_k[%s]" % basis, table[basis])
    if table[UNCORRELATED_MODEL] < table[CORRELATED_MODEL]:
        raise ValueError(
            "policy gives an uncorrelated model a smaller uncertainty margin than a "
            "correlated one, which inverts the data basis"
        )
    _require_non_negative("acceptance_margin_k", policy.get("acceptance_margin_k"))
    _require_non_negative(
        "qualification_margin_k", policy.get("qualification_margin_k")
    )
    cap = _require_positive("max_total_margin_k", policy.get("max_total_margin_k"))
    if cap < policy["acceptance_margin_k"]:
        raise ValueError("policy max_total_margin_k is below the acceptance margin")
    return policy


def uncertainty_margin_k(data_basis, policy=DEFAULT_LIMIT_POLICY):
    """Widening the prediction owes because of how it was obtained."""
    validate_limit_policy(policy)
    _require_choice("data_basis", data_basis, DATA_BASES)
    return policy["uncertainty_margin_k"][data_basis]


def margin_build_up_k(data_basis, objective, policy=DEFAULT_LIMIT_POLICY):
    """Increments from the prediction out to the test limit, and their total."""
    validate_limit_policy(policy)
    _require_choice("objective", objective, OBJECTIVES)
    uncertainty = uncertainty_margin_k(data_basis, policy)
    acceptance = policy["acceptance_margin_k"]
    qualification = (
        policy["qualification_margin_k"] if objective == QUALIFICATION else 0.0
    )
    raw_total = uncertainty + acceptance + qualification
    cap = policy["max_total_margin_k"]
    capped = not _at_most(raw_total, cap)
    return {
        "uncertainty_k": uncertainty,
        "acceptance_k": acceptance,
        "qualification_k": qualification,
        "raw_total_k": raw_total,
        "total_k": cap if capped else raw_total,
        "capped": capped,
    }


def widen_limits_k(predicted_min_k, predicted_max_k, margin_k):
    """Widen a predicted envelope symmetrically by one increment."""
    low = _require_positive("predicted_min_k", predicted_min_k)
    high = _require_positive("predicted_max_k", predicted_max_k)
    if high < low:
        raise ValueError(
            "predicted_max_k %g K is below predicted_min_k %g K" % (high, low)
        )
    margin = _require_non_negative("margin_k", margin_k)
    widened_low = low - margin
    if widened_low <= 0.0:
        raise ValueError(
            "a margin of %g K takes the cold limit to %g K, which is not an "
            "absolute temperature" % (margin, widened_low)
        )
    return {"min_k": widened_low, "max_k": high + margin}


def limit_ladder_k(predicted_min_k, predicted_max_k, data_basis,
                   policy=DEFAULT_LIMIT_POLICY):
    """Design, acceptance and qualification limits, step by step."""
    validate_limit_policy(policy)
    uncertainty = uncertainty_margin_k(data_basis, policy)
    design = widen_limits_k(predicted_min_k, predicted_max_k, uncertainty)
    acceptance = widen_limits_k(
        design["min_k"], design["max_k"], policy["acceptance_margin_k"]
    )
    qualification = widen_limits_k(
        acceptance["min_k"], acceptance["max_k"], policy["qualification_margin_k"]
    )
    return {
        "predicted": {"min_k": float(predicted_min_k), "max_k": float(predicted_max_k)},
        "design": design,
        "acceptance": acceptance,
        "qualification": qualification,
    }


def capability_check(test_min_k, test_max_k, capability_min_k, capability_max_k):
    """Whether the derived limits stay inside what the hardware can survive."""
    test_min = _require_positive("test_min_k", test_min_k)
    test_max = _require_positive("test_max_k", test_max_k)
    capability_min = _require_positive("capability_min_k", capability_min_k)
    capability_max = _require_positive("capability_max_k", capability_max_k)
    if capability_max <= capability_min:
        raise ValueError(
            "capability_max_k %g K must be above capability_min_k %g K"
            % (capability_max, capability_min)
        )
    cold_ok = _at_least(test_min, capability_min)
    hot_ok = _at_most(test_max, capability_max)
    return {
        "cold_within_capability": cold_ok,
        "hot_within_capability": hot_ok,
        "within_capability": cold_ok and hot_ok,
        "cold_margin_k": test_min - capability_min,
        "hot_margin_k": capability_max - test_max,
        "remaining_margin_k": min(test_min - capability_min, capability_max - test_max),
    }


def margin_reduction_available_k(data_basis, policy=DEFAULT_LIMIT_POLICY):
    """Widening that measuring the hardware would take back off each end."""
    validate_limit_policy(policy)
    return uncertainty_margin_k(data_basis, policy) - uncertainty_margin_k(
        MEASURED_HARDWARE, policy
    )


def derive_test_limits(case, policy=DEFAULT_LIMIT_POLICY):
    """Full derivation: prediction, build-up, test limits, capability verdict."""
    validate_limit_policy(policy)
    _require_mapping("case", case)
    data_basis = _require_choice("data_basis", case.get("data_basis"), DATA_BASES)
    objective = _require_choice("objective", case.get("objective"), OBJECTIVES)
    predicted_min = _require_positive("predicted_min_k", case.get("predicted_min_k"))
    predicted_max = _require_positive("predicted_max_k", case.get("predicted_max_k"))
    build_up = margin_build_up_k(data_basis, objective, policy)
    ladder = limit_ladder_k(predicted_min, predicted_max, data_basis, policy)
    limits = widen_limits_k(predicted_min, predicted_max, build_up["total_k"])
    capability = capability_check(
        limits["min_k"],
        limits["max_k"],
        case.get("capability_min_k"),
        case.get("capability_max_k"),
    )
    findings = []
    duties = []
    if build_up["capped"]:
        findings.append(
            "the build-up of %.2f K is capped at the programme ceiling of %.2f K, so "
            "the test limits are narrower than the increments call for"
            % (build_up["raw_total_k"], build_up["total_k"])
        )
    if not capability["hot_within_capability"]:
        findings.append(
            "the derived hot limit of %.2f K is above the hardware capability of "
            "%.2f K; the run would damage the item rather than demonstrate anything"
            % (limits["max_k"], float(case["capability_max_k"]))
        )
    if not capability["cold_within_capability"]:
        findings.append(
            "the derived cold limit of %.2f K is below the hardware capability of "
            "%.2f K" % (limits["min_k"], float(case["capability_min_k"]))
        )
    reduction = margin_reduction_available_k(data_basis, policy)
    if reduction > 0.0:
        duties.append(
            "record that measuring the flight hardware would take %.2f K off each "
            "end of the test envelope" % reduction
        )
    duties.append(
        "state the build-up with the limits; a test limit quoted without its "
        "increments cannot be traced back to the prediction"
    )
    return {
        "data_basis": data_basis,
        "objective": objective,
        "ladder": ladder,
        "build_up": build_up,
        "test_min_k": limits["min_k"],
        "test_max_k": limits["max_k"],
        "capability": capability,
        "margin_reduction_available_k": reduction,
        "acceptable": capability["within_capability"],
        "duties": duties,
        "findings": findings,
    }
