#!/usr/bin/env python3
"""Purpose of the before-and-after output-power measurement on an assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An environmental test on a photovoltaic assembly is bracketed by two
output-power measurements: one before the exposure, one after it. The
pair exists for one reason -- so that degradation caused by the exposure
becomes visible as a loss of output power. That makes the purpose a
measurement-capability question, not only a pass/fail question.

Two things decide whether the pair serves that purpose:

    what the pair brackets   thermal cycling, humidity exposure, a
                             discharge run, vibration, ultraviolet or
                             particle exposure each drive a different
                             mechanism, and each turns into a
                             degradation the pair is meant to expose
    what the pair resolves   a power loss smaller than the combined
                             uncertainty of the two measurements cannot
                             be told apart from measurement noise, so
                             the pair must resolve a loss at the
                             allowable limit before it can detect one

A pair that cannot resolve the allowable degradation reports a clean
result for a degraded article, which is the failure mode this clause
exists to prevent. The allowance, the coverage factor and the resolution
margin below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Bracketed test -> the degradation the power pair is meant to expose.
BRACKETED_TESTS = {
    "solar-array-thermal-cycling": "interconnect-fatigue-power-loss",
    "solar-array-humidity-exposure": "bondline-adhesion-power-loss",
    "solar-array-coupon-discharge": "arc-site-shunting-power-loss",
    "solar-array-mechanical-vibration": "cell-cracking-power-loss",
    "solar-array-ultraviolet-exposure": "coverglass-transmission-power-loss",
    "solar-array-particle-irradiation": "cell-output-degradation-power-loss",
}

RECOGNISED_TESTS = tuple(sorted(BRACKETED_TESTS))

COMMON_OBJECTIVE = "assembly-output-power-retention"

BASELINE_NOT_MEASURED = "baseline-not-measured"
DEGRADATION_NOT_RESOLVABLE = "degradation-not-resolvable"
DEGRADATION_WITHIN_ALLOWANCE = "degradation-within-allowance"
DEGRADATION_EXCEEDS_ALLOWANCE = "degradation-exceeds-allowance"

DEFAULT_POWER_MEASUREMENT_POLICY = {
    "allowable_degradation_pct": 2.0,
    "coverage_factor": 2.0,
    "resolution_margin": 1.0,
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


def _require_percentage(name, value):
    number = _require_non_negative(name, value)
    if number > 100.0:
        raise ValueError(
            "%s must be a percentage between 0 and 100, got %r" % (name, value)
        )
    return number


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


def validate_power_measurement_policy(policy):
    """Check a degradation-detection policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_percentage(
        "allowable_degradation_pct", policy.get("allowable_degradation_pct")
    )
    _require_positive("coverage_factor", policy.get("coverage_factor"))
    margin = _require_positive("resolution_margin", policy.get("resolution_margin"))
    if margin < 1.0:
        raise ValueError(
            "resolution_margin %g lets a loss inside the measurement noise count "
            "as detected" % margin
        )
    return policy


def relative_degradation_pct(pre_test_power_w, post_test_power_w):
    """Power lost across the exposure, as a percentage of the baseline.

    A negative result means the article measured higher after the
    exposure than before it, which is a measurement question rather than
    an improvement, so the sign is preserved instead of being clipped.
    """
    pre = _require_positive("pre_test_power_w", pre_test_power_w)
    post = _require_non_negative("post_test_power_w", post_test_power_w)
    return (pre - post) / pre * 100.0


def combined_uncertainty_pct(pre_uncertainty_pct, post_uncertainty_pct):
    """Root-sum-square of the two independent measurement uncertainties."""
    pre = _require_non_negative("pre_uncertainty_pct", pre_uncertainty_pct)
    post = _require_non_negative("post_uncertainty_pct", post_uncertainty_pct)
    return math.sqrt(pre * pre + post * post)


def resolvable_degradation_pct(
    pre_uncertainty_pct,
    post_uncertainty_pct,
    policy=DEFAULT_POWER_MEASUREMENT_POLICY,
):
    """Smallest power loss the bracketing pair can tell apart from noise."""
    validate_power_measurement_policy(policy)
    combined = combined_uncertainty_pct(pre_uncertainty_pct, post_uncertainty_pct)
    return (
        combined
        * float(policy["coverage_factor"])
        * float(policy["resolution_margin"])
    )


def degradation_is_resolvable(
    pre_uncertainty_pct,
    post_uncertainty_pct,
    policy=DEFAULT_POWER_MEASUREMENT_POLICY,
):
    """True when a loss at the allowable limit would be distinguishable."""
    validate_power_measurement_policy(policy)
    resolution = resolvable_degradation_pct(
        pre_uncertainty_pct, post_uncertainty_pct, policy
    )
    return _at_least(float(policy["allowable_degradation_pct"]), resolution)


def bracketed_test_inventory(tests):
    """Group the declared bracketed tests, rejecting an unrecognised one."""
    if not isinstance(tests, (list, tuple, set, frozenset)):
        raise ValueError("tests must be a collection of bracketed test names")
    grouped = []
    for test in tests:
        if test not in BRACKETED_TESTS:
            raise ValueError(
                "unknown bracketed test %r; recognised tests are %s"
                % (test, ", ".join(RECOGNISED_TESTS))
            )
        if test not in grouped:
            grouped.append(test)
    return tuple(sorted(grouped))


def degradation_objectives(tests):
    """What the bracketing power pair is meant to expose, given the tests."""
    grouped = bracketed_test_inventory(tests)
    if not grouped:
        return ()
    objectives = [BRACKETED_TESTS[test] for test in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_power_measurement_purpose(
    case, policy=DEFAULT_POWER_MEASUREMENT_POLICY
):
    """Full clause 5.5.3.4.1 judgement for one bracketed power measurement."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_power_measurement_policy(policy)
    if "bracketed_tests" not in case:
        raise ValueError(
            "case is missing bracketed_tests; an absent inventory is not an "
            "empty one"
        )
    tests = bracketed_test_inventory(case["bracketed_tests"])
    objectives = degradation_objectives(case["bracketed_tests"])
    allowable = float(policy["allowable_degradation_pct"])
    findings = []
    result = {
        "bracketed_tests": tests,
        "objectives": objectives,
        "allowable_degradation_pct": allowable,
        "degradation_pct": None,
        "resolution_pct": None,
        "resolvable": None,
        "findings": findings,
    }

    pre_measurement = case.get("pre_test_measurement")
    if pre_measurement is None:
        findings.append(
            "no pre-test output power was measured, so any post-test power has "
            "nothing to be compared against"
        )
        result["verdict"] = BASELINE_NOT_MEASURED
        return result
    if not isinstance(pre_measurement, dict):
        raise ValueError("pre_test_measurement must be a mapping")
    post_measurement = case.get("post_test_measurement")
    if post_measurement is None:
        findings.append(
            "no post-test output power was measured, so the exposure is not "
            "bracketed and no degradation can be detected"
        )
        result["verdict"] = BASELINE_NOT_MEASURED
        return result
    if not isinstance(post_measurement, dict):
        raise ValueError("post_test_measurement must be a mapping")

    pre_power = _require_positive(
        "pre_test power_w", pre_measurement.get("power_w")
    )
    post_power = _require_non_negative(
        "post_test power_w", post_measurement.get("power_w")
    )
    pre_uncertainty = _require_percentage(
        "pre_test uncertainty_pct", pre_measurement.get("uncertainty_pct")
    )
    post_uncertainty = _require_percentage(
        "post_test uncertainty_pct", post_measurement.get("uncertainty_pct")
    )

    degradation = relative_degradation_pct(pre_power, post_power)
    resolution = resolvable_degradation_pct(
        pre_uncertainty, post_uncertainty, policy
    )
    resolvable = _at_least(allowable, resolution)

    result["pre_test_power_w"] = pre_power
    result["post_test_power_w"] = post_power
    result["degradation_pct"] = degradation
    result["resolution_pct"] = resolution
    result["resolvable"] = resolvable

    if not resolvable:
        findings.append(
            "the pair resolves only %.3f percent while the allowance is %.3f "
            "percent, so a degraded article can report a clean result"
            % (resolution, allowable)
        )
        result["verdict"] = DEGRADATION_NOT_RESOLVABLE
        return result

    if _at_most(degradation, allowable):
        result["verdict"] = DEGRADATION_WITHIN_ALLOWANCE
    else:
        findings.append(
            "measured power loss %.3f percent is above the %.3f percent "
            "allowance" % (degradation, allowable)
        )
        result["verdict"] = DEGRADATION_EXCEEDS_ALLOWANCE
    return result
