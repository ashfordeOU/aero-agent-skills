#!/usr/bin/env python3
"""Mapping a protection diode's electrical parameters across the whole
temperature range it is expected to work over.

Anchor: ECSS-E-ST-20-08C clause 9.6.14. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A protection diode on a solar array does not sit at one temperature. It sees
whatever the wing sees, which on a low orbit is a swing of well over a hundred
kelvin every revolution, and its forward drop, its leakage and its knee all
move with it. This clause is the one that produces the map: a sweep of
measurements taken across the declared operating range so that the device's
behaviour at any point in that range is a read rather than a guess.

The map is only worth what its sweep is worth, and four things decide that:

    the reach         the coldest and hottest points have to reach the ends of
                      the declared operating range. A sweep that stops short
                      produces a map of a narrower device than the one flying
    the resolution    the gap between neighbouring points. Past some step the
                      curve between them is an assumption, and a knee that
                      falls inside a wide step is simply not in the map
    the ordering      one reading per temperature. A duplicated temperature
                      is two readings of one point, and a fit run over it
                      weights that point twice for no reason
    the fit           the forward voltage moves close enough to linearly with
                      temperature that a least squares slope over the sweep is
                      the device's temperature coefficient. Leakage does not:
                      it moves in decades, so what characterises it is the
                      temperature interval over which it doubles

Both derived numbers land inside a band rather than above or below a single
limit -- a coefficient far from the expected one is as much a finding as a
coefficient out of family, because it usually means the fixture rather than
the diode was measured.

Logarithms and least squares divisions land a few units in the last place
either side of a limit on different hosts, so every comparison here absorbs
that error while the bands themselves are never relaxed.

The bands, floors and ceilings below are a declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ABSOLUTE_ZERO_C = -273.15

OPERATING_RANGE_NOT_COVERED = "diode-operating-range-not-covered"
TEMPERATURE_COEFFICIENT_OUT_OF_BAND = "diode-temperature-coefficient-out-of-band"
SWEEP_PLAN_DEFICIENT = "diode-temperature-sweep-plan-deficient"
BEHAVIOUR_MAP_ACCEPTED = "diode-temperature-behaviour-map-accepted"

BEHAVIOUR_VERDICTS = (
    OPERATING_RANGE_NOT_COVERED,
    TEMPERATURE_COEFFICIENT_OUT_OF_BAND,
    SWEEP_PLAN_DEFICIENT,
    BEHAVIOUR_MAP_ACCEPTED,
)

DEFAULT_DIODE_SWEEP_POLICY = {
    "min_sweep_points": 5,
    "max_step_k": 30.0,
    "max_endpoint_gap_k": 2.0,
    "min_operating_span_k": 150.0,
    "min_forward_coefficient_mv_per_k": -3.5,
    "max_forward_coefficient_mv_per_k": -1.0,
    "min_leakage_doubling_interval_k": 5.0,
    "max_leakage_doubling_interval_k": 20.0,
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


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (name, value))
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


def _in_band(value, low, high):
    return _at_least(value, low) and _at_most(value, high)


def validate_sweep_policy(policy):
    """Check a diode temperature sweep policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    points = _require_count("min_sweep_points", policy.get("min_sweep_points"))
    if points < 3:
        raise ValueError(
            "min_sweep_points must be at least 3 for a slope to mean anything, "
            "got %r" % (policy.get("min_sweep_points"),)
        )
    _require_positive("max_step_k", policy.get("max_step_k"))
    _require_positive("max_endpoint_gap_k", policy.get("max_endpoint_gap_k"))
    _require_positive("min_operating_span_k", policy.get("min_operating_span_k"))
    low_coeff = _require_number(
        "min_forward_coefficient_mv_per_k",
        policy.get("min_forward_coefficient_mv_per_k"),
    )
    high_coeff = _require_number(
        "max_forward_coefficient_mv_per_k",
        policy.get("max_forward_coefficient_mv_per_k"),
    )
    if not low_coeff < high_coeff:
        raise ValueError(
            "min_forward_coefficient_mv_per_k %g must sit below "
            "max_forward_coefficient_mv_per_k %g" % (low_coeff, high_coeff)
        )
    low_double = _require_positive(
        "min_leakage_doubling_interval_k",
        policy.get("min_leakage_doubling_interval_k"),
    )
    high_double = _require_positive(
        "max_leakage_doubling_interval_k",
        policy.get("max_leakage_doubling_interval_k"),
    )
    if not low_double < high_double:
        raise ValueError(
            "min_leakage_doubling_interval_k %g must sit below "
            "max_leakage_doubling_interval_k %g" % (low_double, high_double)
        )
    return policy


def normalise_sweep(points):
    """Order a sweep by temperature and refuse a duplicated point."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence, got %r" % (points,))
    rows = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("sweep point %d must be a mapping, got %r" % (index, point))
        temperature = _require_temperature_c(
            "sweep point %d temperature_c" % index, point.get("temperature_c")
        )
        forward = _require_positive(
            "sweep point %d forward_voltage_v" % index, point.get("forward_voltage_v")
        )
        leakage = _require_positive(
            "sweep point %d reverse_leakage_a" % index, point.get("reverse_leakage_a")
        )
        rows.append(
            {
                "temperature_c": temperature,
                "forward_voltage_v": forward,
                "reverse_leakage_a": leakage,
            }
        )
    rows.sort(key=lambda row: row["temperature_c"])
    for earlier, later in zip(rows, rows[1:]):
        if math.isclose(
            earlier["temperature_c"],
            later["temperature_c"],
            rel_tol=_REL_TOL,
            abs_tol=_ABS_TOL,
        ):
            raise ValueError(
                "the sweep reads %g C twice; one reading per temperature"
                % (earlier["temperature_c"],)
            )
    return rows


def sweep_span_k(points):
    """How wide a temperature window the sweep actually covers."""
    rows = normalise_sweep(points)
    if len(rows) < 2:
        raise ValueError("a span needs at least two sweep points")
    return rows[-1]["temperature_c"] - rows[0]["temperature_c"]


def largest_step_k(points):
    """The widest gap between neighbouring sweep points."""
    rows = normalise_sweep(points)
    if len(rows) < 2:
        raise ValueError("a step needs at least two sweep points")
    return max(
        later["temperature_c"] - earlier["temperature_c"]
        for earlier, later in zip(rows, rows[1:])
    )


def endpoint_gaps_k(points, min_operating_c, max_operating_c):
    """How far the sweep ends sit inside the declared operating range."""
    low = _require_temperature_c("min_operating_c", min_operating_c)
    high = _require_temperature_c("max_operating_c", max_operating_c)
    if not low < high:
        raise ValueError(
            "min_operating_c %g must sit below max_operating_c %g" % (low, high)
        )
    rows = normalise_sweep(points)
    cold_gap = rows[0]["temperature_c"] - low
    hot_gap = high - rows[-1]["temperature_c"]
    return {
        "cold_gap_k": max(cold_gap, 0.0),
        "hot_gap_k": max(hot_gap, 0.0),
    }


def forward_coefficient_mv_per_k(points):
    """Least squares slope of forward voltage against temperature, mV/K."""
    rows = normalise_sweep(points)
    if len(rows) < 2:
        raise ValueError("a temperature coefficient needs at least two points")
    n = float(len(rows))
    mean_t = sum(row["temperature_c"] for row in rows) / n
    mean_v = sum(row["forward_voltage_v"] for row in rows) / n
    numerator = sum(
        (row["temperature_c"] - mean_t) * (row["forward_voltage_v"] - mean_v)
        for row in rows
    )
    denominator = sum((row["temperature_c"] - mean_t) ** 2 for row in rows)
    if denominator <= 0.0:
        raise ValueError("the sweep has no temperature spread to fit a slope over")
    return 1000.0 * numerator / denominator


def leakage_doubling_interval_k(points):
    """Temperature interval over which the reverse leakage doubles."""
    rows = normalise_sweep(points)
    if len(rows) < 2:
        raise ValueError("a doubling interval needs at least two points")
    cold, hot = rows[0], rows[-1]
    ratio = hot["reverse_leakage_a"] / cold["reverse_leakage_a"]
    if ratio <= 1.0:
        raise ValueError(
            "the reverse leakage did not grow across the sweep (ratio %g), so no "
            "doubling interval exists" % (ratio,)
        )
    span = hot["temperature_c"] - cold["temperature_c"]
    return span * math.log(2.0) / math.log(ratio)


def assess_diode_temperature_behaviour(case, policy=DEFAULT_DIODE_SWEEP_POLICY):
    """Full clause 9.6.14 judgement for one protection diode sweep."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_sweep_policy(policy)
    operating = case.get("operating_range")
    if not isinstance(operating, dict):
        raise ValueError("case is missing an operating_range block")
    points = case.get("sweep")
    rows = normalise_sweep(points)

    low = _require_temperature_c(
        "operating_range min_operating_c", operating.get("min_operating_c")
    )
    high = _require_temperature_c(
        "operating_range max_operating_c", operating.get("max_operating_c")
    )
    gaps = endpoint_gaps_k(rows, low, high)
    operating_span = high - low
    span = sweep_span_k(rows)
    step = largest_step_k(rows)
    coefficient = forward_coefficient_mv_per_k(rows)
    doubling = leakage_doubling_interval_k(rows)

    findings = []
    result = {
        "sweep_points": len(rows),
        "operating_span_k": operating_span,
        "sweep_span_k": span,
        "largest_step_k": step,
        "cold_gap_k": gaps["cold_gap_k"],
        "hot_gap_k": gaps["hot_gap_k"],
        "forward_coefficient_mv_per_k": coefficient,
        "leakage_doubling_interval_k": doubling,
        "findings": findings,
    }

    not_covered = False
    if not _at_most(gaps["cold_gap_k"], float(policy["max_endpoint_gap_k"])):
        not_covered = True
        findings.append(
            "the coldest reading stops %.3f K short of the %.2f C cold end "
            "against the %.3f K allowed"
            % (gaps["cold_gap_k"], low, float(policy["max_endpoint_gap_k"]))
        )
    if not _at_most(gaps["hot_gap_k"], float(policy["max_endpoint_gap_k"])):
        not_covered = True
        findings.append(
            "the hottest reading stops %.3f K short of the %.2f C hot end "
            "against the %.3f K allowed"
            % (gaps["hot_gap_k"], high, float(policy["max_endpoint_gap_k"]))
        )
    if not _at_least(operating_span, float(policy["min_operating_span_k"])):
        not_covered = True
        findings.append(
            "the declared operating range spans %.2f K against the %.2f K this "
            "map is required to cover"
            % (operating_span, float(policy["min_operating_span_k"]))
        )

    coefficient_out = not _in_band(
        coefficient,
        float(policy["min_forward_coefficient_mv_per_k"]),
        float(policy["max_forward_coefficient_mv_per_k"]),
    )
    if coefficient_out:
        findings.append(
            "the forward voltage coefficient fits at %.5f mV/K, outside the "
            "%.3f to %.3f mV/K band a protection diode is expected in"
            % (
                coefficient,
                float(policy["min_forward_coefficient_mv_per_k"]),
                float(policy["max_forward_coefficient_mv_per_k"]),
            )
        )
    doubling_out = not _in_band(
        doubling,
        float(policy["min_leakage_doubling_interval_k"]),
        float(policy["max_leakage_doubling_interval_k"]),
    )
    if doubling_out:
        findings.append(
            "the reverse leakage doubles every %.4f K, outside the %.3f to "
            "%.3f K band"
            % (
                doubling,
                float(policy["min_leakage_doubling_interval_k"]),
                float(policy["max_leakage_doubling_interval_k"]),
            )
        )

    if not _at_least(len(rows), int(policy["min_sweep_points"])):
        findings.append(
            "the sweep holds %d points against the %d the policy asks for"
            % (len(rows), int(policy["min_sweep_points"]))
        )
    if not _at_most(step, float(policy["max_step_k"])):
        findings.append(
            "the widest gap between neighbouring points is %.3f K against the "
            "%.3f K allowed, so the curve across it is an assumption"
            % (step, float(policy["max_step_k"]))
        )

    if not_covered:
        result["verdict"] = OPERATING_RANGE_NOT_COVERED
    elif coefficient_out or doubling_out:
        result["verdict"] = TEMPERATURE_COEFFICIENT_OUT_OF_BAND
    elif findings:
        result["verdict"] = SWEEP_PLAN_DEFICIENT
    else:
        result["verdict"] = BEHAVIOUR_MAP_ACCEPTED
    return result
