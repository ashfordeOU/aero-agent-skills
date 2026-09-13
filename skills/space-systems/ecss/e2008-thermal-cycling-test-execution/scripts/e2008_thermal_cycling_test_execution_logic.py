#!/usr/bin/env python3
"""Thermal-cycling test execution for a photovoltaic-assembly coupon.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.1.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two numbers have to be decided before a coupon ever enters the chamber:
how many cycles are run, and between which two temperatures. Both come
from the mission, not from the chamber:

    cycle count      eclipse cycles the array sees over the mission life,
                     multiplied by a qualification factor, floored by a
                     policy minimum so a short or high-orbit mission
                     still earns a fatigue-relevant campaign
    temperature      the predicted on-orbit extremes widened by a
                     qualification margin, and refused outright when the
                     widened extreme lies outside what the coupon
                     materials are declared to survive

The profile that joins them is the third decision: a ramp rate the
chamber and the coupon can both follow, and a dwell at each extreme long
enough for the whole coupon to stabilise rather than just its surface.

Running the profile is not the same as meeting it. A cycle only counts
toward the requirement when the record shows both extremes were actually
reached and both dwells were actually held, so the campaign is graded on
conforming cycles rather than on chamber hours.

The eclipse rates and the margin below are a declared policy, not a
physical constant: a project substitutes its own orbit data.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ORBIT_REGIMES = ("leo", "sso", "meo", "geo", "heo")

DEFAULT_CYCLING_POLICY = {
    "eclipse_cycles_per_year": {
        "leo": 5500.0,
        "sso": 5500.0,
        "meo": 1100.0,
        "geo": 90.0,
        "heo": 730.0,
    },
    "qualification_factor": 1.25,
    "minimum_qualification_cycles": 100,
    "temperature_margin_k": 10.0,
    "stabilisation_tolerance_k": 2.0,
    "minimum_dwell_min": 5.0,
    "maximum_ramp_rate_k_per_min": 20.0,
}

CYCLING_COMPLETE = "cycling-complete"
CYCLING_SHORT = "cycling-short"
CYCLING_NOT_RUN = "cycling-not-run"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12
# ceil() on a product of floats turns an exact 34375.0 into 34376 whenever
# the multiplication lands one unit in the last place high. The nudge below
# is far smaller than one cycle and far larger than that error.
_CEIL_NUDGE = 1e-9


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


def validate_cycling_policy(policy):
    """Check a cycling policy covers every orbit regime with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    rates = policy.get("eclipse_cycles_per_year")
    if not isinstance(rates, dict):
        raise ValueError("policy eclipse_cycles_per_year must be a mapping")
    missing = set(ORBIT_REGIMES) - set(rates)
    if missing:
        raise ValueError(
            "policy eclipse_cycles_per_year is missing regimes: %s"
            % ", ".join(sorted(missing))
        )
    for regime in ORBIT_REGIMES:
        _require_positive("eclipse_cycles_per_year[%s]" % regime, rates[regime])
    factor = _require_number("qualification_factor", policy.get("qualification_factor"))
    if factor < 1.0:
        raise ValueError(
            "qualification_factor must be at least one, got %r" % (factor,)
        )
    minimum = policy.get("minimum_qualification_cycles")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError(
            "minimum_qualification_cycles must be a positive integer, got %r"
            % (minimum,)
        )
    _require_non_negative("temperature_margin_k", policy.get("temperature_margin_k"))
    _require_positive(
        "stabilisation_tolerance_k", policy.get("stabilisation_tolerance_k")
    )
    _require_positive("minimum_dwell_min", policy.get("minimum_dwell_min"))
    _require_positive(
        "maximum_ramp_rate_k_per_min", policy.get("maximum_ramp_rate_k_per_min")
    )
    return policy


def required_cycle_count(orbit_regime, mission_years, policy=DEFAULT_CYCLING_POLICY):
    """Cycles the campaign owes for a mission orbit regime and duration."""
    validate_cycling_policy(policy)
    _require_choice("orbit_regime", orbit_regime, ORBIT_REGIMES)
    years = _require_positive("mission_years", mission_years)
    rate = float(policy["eclipse_cycles_per_year"][orbit_regime])
    derived = rate * years * float(policy["qualification_factor"])
    cycles = int(math.ceil(derived - _CEIL_NUDGE))
    return max(cycles, int(policy["minimum_qualification_cycles"]))


def qualification_temperature_extremes(
    predicted_min_c,
    predicted_max_c,
    coupon_limit_min_c,
    coupon_limit_max_c,
    policy=DEFAULT_CYCLING_POLICY,
):
    """Hot and cold extremes the profile runs to, or a refusal."""
    validate_cycling_policy(policy)
    low = _require_number("predicted_min_c", predicted_min_c)
    high = _require_number("predicted_max_c", predicted_max_c)
    if not high > low:
        raise ValueError(
            "predicted_max_c %g C must be above predicted_min_c %g C" % (high, low)
        )
    limit_low = _require_number("coupon_limit_min_c", coupon_limit_min_c)
    limit_high = _require_number("coupon_limit_max_c", coupon_limit_max_c)
    if not limit_high > limit_low:
        raise ValueError(
            "coupon_limit_max_c %g C must be above coupon_limit_min_c %g C"
            % (limit_high, limit_low)
        )
    margin = float(policy["temperature_margin_k"])
    qual_low = low - margin
    qual_high = high + margin
    if not _at_least(qual_low, limit_low):
        raise ValueError(
            "cold qualification extreme %g C is below the declared coupon limit "
            "%g C; the coupon build or the prediction has to change, not the "
            "margin" % (qual_low, limit_low)
        )
    if not _at_most(qual_high, limit_high):
        raise ValueError(
            "hot qualification extreme %g C is above the declared coupon limit "
            "%g C; the coupon build or the prediction has to change, not the "
            "margin" % (qual_high, limit_high)
        )
    findings = []
    if math.isclose(qual_low, limit_low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        findings.append(
            "cold qualification extreme sits on the declared coupon limit %g C"
            % limit_low
        )
    if math.isclose(qual_high, limit_high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        findings.append(
            "hot qualification extreme sits on the declared coupon limit %g C"
            % limit_high
        )
    return {
        "qual_min_c": qual_low,
        "qual_max_c": qual_high,
        "range_k": qual_high - qual_low,
        "findings": findings,
    }


def cycle_period_min(
    range_k,
    ramp_rate_k_per_min,
    hot_dwell_min,
    cold_dwell_min,
    policy=DEFAULT_CYCLING_POLICY,
):
    """Minutes one full cycle takes: two ramps plus the two dwells."""
    validate_cycling_policy(policy)
    span = _require_positive("range_k", range_k)
    rate = _require_positive("ramp_rate_k_per_min", ramp_rate_k_per_min)
    if not _at_most(rate, float(policy["maximum_ramp_rate_k_per_min"])):
        raise ValueError(
            "ramp_rate_k_per_min %g exceeds the policy ceiling %g"
            % (rate, policy["maximum_ramp_rate_k_per_min"])
        )
    hot = _require_positive("hot_dwell_min", hot_dwell_min)
    cold = _require_positive("cold_dwell_min", cold_dwell_min)
    floor = float(policy["minimum_dwell_min"])
    for name, dwell in (("hot_dwell_min", hot), ("cold_dwell_min", cold)):
        if not _at_least(dwell, floor):
            raise ValueError(
                "%s %g is below the policy stabilisation dwell %g" % (name, dwell, floor)
            )
    return 2.0 * span / rate + hot + cold


def campaign_duration_h(cycle_count, period_min):
    """Chamber hours a campaign of this many cycles occupies."""
    if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
        raise ValueError("cycle_count must be an integer, got %r" % (cycle_count,))
    if cycle_count < 1:
        raise ValueError("cycle_count must be at least one, got %r" % (cycle_count,))
    period = _require_positive("period_min", period_min)
    return cycle_count * period / 60.0


def evaluate_recorded_cycles(
    recorded,
    qual_min_c,
    qual_max_c,
    hot_dwell_min,
    cold_dwell_min,
    policy=DEFAULT_CYCLING_POLICY,
):
    """Count the recorded cycles that actually met the profile."""
    validate_cycling_policy(policy)
    if not isinstance(recorded, (list, tuple)):
        raise ValueError("recorded must be a list of cycle records")
    low = _require_number("qual_min_c", qual_min_c)
    high = _require_number("qual_max_c", qual_max_c)
    if not high > low:
        raise ValueError("qual_max_c must be above qual_min_c")
    hot = _require_positive("hot_dwell_min", hot_dwell_min)
    cold = _require_positive("cold_dwell_min", cold_dwell_min)
    tolerance = float(policy["stabilisation_tolerance_k"])
    conforming = 0
    non_conforming = []
    for index, record in enumerate(recorded, 1):
        if not isinstance(record, dict):
            raise ValueError("cycle record %d must be a mapping" % index)
        reached_low = _require_number("cycle %d min_c" % index, record.get("min_c"))
        reached_high = _require_number("cycle %d max_c" % index, record.get("max_c"))
        held_hot = _require_non_negative(
            "cycle %d hot_dwell_min" % index, record.get("hot_dwell_min")
        )
        held_cold = _require_non_negative(
            "cycle %d cold_dwell_min" % index, record.get("cold_dwell_min")
        )
        reasons = []
        if not _at_most(reached_low, low + tolerance):
            reasons.append("cold extreme not reached")
        if not _at_least(reached_high, high - tolerance):
            reasons.append("hot extreme not reached")
        if not _at_least(held_hot, hot):
            reasons.append("hot dwell short")
        if not _at_least(held_cold, cold):
            reasons.append("cold dwell short")
        if reasons:
            non_conforming.append({"cycle": index, "reasons": reasons})
        else:
            conforming += 1
    return {
        "cycles_recorded": len(recorded),
        "conforming_cycles": conforming,
        "non_conforming": non_conforming,
    }


def plan_and_verify_cycling(case, policy=DEFAULT_CYCLING_POLICY):
    """Full clause 5.5.1.3.4 execution plan with a completion verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_cycling_policy(policy)
    orbit_regime = _require_choice(
        "orbit_regime", case.get("orbit_regime"), ORBIT_REGIMES
    )
    required = required_cycle_count(orbit_regime, case.get("mission_years"), policy)
    extremes = qualification_temperature_extremes(
        case.get("predicted_min_c"),
        case.get("predicted_max_c"),
        case.get("coupon_limit_min_c"),
        case.get("coupon_limit_max_c"),
        policy,
    )
    hot_dwell = case.get("hot_dwell_min", policy["minimum_dwell_min"])
    cold_dwell = case.get("cold_dwell_min", policy["minimum_dwell_min"])
    period = cycle_period_min(
        extremes["range_k"],
        case.get("ramp_rate_k_per_min"),
        hot_dwell,
        cold_dwell,
        policy,
    )
    findings = list(extremes["findings"])
    result = {
        "orbit_regime": orbit_regime,
        "required_cycles": required,
        "qual_min_c": extremes["qual_min_c"],
        "qual_max_c": extremes["qual_max_c"],
        "range_k": extremes["range_k"],
        "cycle_period_min": period,
        "planned_campaign_duration_h": campaign_duration_h(required, period),
        "findings": findings,
    }
    recorded = case.get("recorded_cycles")
    if recorded is None:
        result.update(
            {
                "cycles_recorded": 0,
                "conforming_cycles": 0,
                "non_conforming": [],
                "complete": None,
                "verdict": CYCLING_NOT_RUN,
            }
        )
        findings.append(
            "no cycle records supplied; the profile is defined but the campaign "
            "is not yet demonstrated"
        )
        return result
    run = evaluate_recorded_cycles(
        recorded,
        extremes["qual_min_c"],
        extremes["qual_max_c"],
        hot_dwell,
        cold_dwell,
        policy,
    )
    complete = run["conforming_cycles"] >= required
    result.update(run)
    result.update(
        {
            "complete": complete,
            "verdict": CYCLING_COMPLETE if complete else CYCLING_SHORT,
        }
    )
    if run["non_conforming"]:
        findings.append(
            "%d of %d recorded cycles missed the profile and do not count"
            % (len(run["non_conforming"]), run["cycles_recorded"])
        )
    if not complete:
        findings.append(
            "%d conforming cycles against a required %d"
            % (run["conforming_cycles"], required)
        )
    return result
