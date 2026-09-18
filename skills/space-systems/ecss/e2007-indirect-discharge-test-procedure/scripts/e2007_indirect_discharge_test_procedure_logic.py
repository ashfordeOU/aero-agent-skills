#!/usr/bin/env python3
"""Indirect discharge test procedure, ECSS-E-ST-20-07C clause 5.4.12.4.

Paraphrased procedure, no verbatim standard text. The clause runs the
indirect discharge exposure itself: the generator is allowed to settle,
its output is checked into the calibration fixture, and the discharges
are then applied to the coupling plane in a defined order. This module
turns that into a deterministic plan and assessment:

  achieved dwell        -> is the generator settled
  fixture measurement   -> calibration passed, out of tolerance, omitted
  plane bleed constant  -> the interval each repeat has to leave
  levels and polarities -> the ordered application plan and its duration

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Dwells, intervals and derived bounds are
# floats, so a value that exactly meets a bound can land a few units in
# the last place off it. The tolerances absorb that representation
# error only; they never relax a requirement.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Time constants the coupling plane has to bleed through before the
# next discharge is applied.
BLEED_MULTIPLE = 5.0

# Largest departure of the fixture measurement from the target first
# peak, in percent, that still counts as a passed calibration.
CALIBRATION_TOLERANCE_PCT = 10.0

# Band the measured rise time has to fall in for the delivered event to
# be the one the method defines.
RISE_TIME_BAND_S = (0.7e-9, 1.0e-9)

# Fewest discharges at one point, one polarity and one level before the
# absence of an upset means anything.
MINIMUM_DISCHARGES_PER_POINT = 10

POLARITIES = ("negative", "positive")

CALIBRATION_STATES = ("measured", "omitted")

CALIBRATION_PASSED = "calibration-passed"
CALIBRATION_OUT_OF_TOLERANCE = "calibration-out-of-tolerance"
CALIBRATION_OMITTED = "calibration-omitted"

VERDICT_COMPLIANT = "procedure-compliant"
VERDICT_WITH_LIMITATIONS = "procedure-compliant-with-limitations"
VERDICT_NONCOMPLIANT = "procedure-noncompliant"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_levels(levels):
    """Validate the severity levels and return them in application order."""
    if isinstance(levels, (str, bytes)) or not isinstance(levels, (tuple, list)):
        raise ValueError("levels: must be a sequence of severity voltages")
    if not levels:
        raise ValueError("levels: at least one severity level is required")
    ordered = []
    for index, level in enumerate(levels):
        value = _scalar(level, "levels[%d]" % index)
        if value <= 0.0:
            raise ValueError("levels[%d] must be > 0, got %g" % (index, value))
        if ordered and not value > ordered[-1]:
            raise ValueError(
                "levels: severity must ascend so the unit meets the lower level "
                "first; levels[%d] is %g after %g" % (index, value, ordered[-1])
            )
        ordered.append(value)
    return tuple(ordered)


def validate_polarities(polarities):
    """Validate the polarity list and return it in a deterministic order."""
    if isinstance(polarities, (str, bytes)) or not isinstance(
        polarities, (tuple, list, set)
    ):
        raise ValueError("polarities: must be a sequence of polarity tokens")
    seen = set()
    for polarity in polarities:
        if not isinstance(polarity, str):
            raise ValueError("polarities: %r is not a polarity token" % (polarity,))
        token = polarity.strip().lower()
        if token not in POLARITIES:
            raise ValueError(
                "polarities: unrecognized %r; recognized: %s"
                % (polarity, ", ".join(POLARITIES))
            )
        if token in seen:
            raise ValueError("polarities: %r is listed twice" % token)
        seen.add(token)
    if not seen:
        raise ValueError("polarities: at least one polarity is required")
    return tuple(p for p in POLARITIES if p in seen)


def validate_procedure(spec):
    """Validate the procedure record and return it normalized."""
    where = "procedure"
    if not isinstance(spec, dict):
        raise ValueError("%s: record must be a mapping" % where)

    values = {}
    for key in ("achieved_warm_up_s", "required_warm_up_s"):
        value = _number(spec, key, where)
        if value < 0.0:
            raise ValueError("%s: %s must be >= 0, got %g" % (where, key, value))
        values[key] = value

    for key in (
        "discharge_interval_s",
        "plane_time_constant_s",
        "target_first_peak_a",
    ):
        value = _number(spec, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    for key in ("discharge_points", "discharges_per_point"):
        value = _number(spec, key, where)
        if value < 1.0 or value != math.floor(value):
            raise ValueError(
                "%s: %s must be a whole number >= 1, got %g" % (where, key, value)
            )
        values[key] = value

    state = _word(spec, "calibration_state", where, CALIBRATION_STATES)
    values["calibration_state"] = state
    if state == "measured":
        for key in ("measured_first_peak_a", "measured_rise_time_s"):
            value = _number(spec, key, where)
            if value <= 0.0:
                raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
            values[key] = value

    monitored = spec.get("unit_monitored", True)
    if not isinstance(monitored, bool):
        raise ValueError("%s: unit_monitored must be a boolean" % where)
    values["unit_monitored"] = monitored

    values["levels_v"] = validate_levels(spec.get("levels_v", ()))
    values["polarities"] = validate_polarities(spec.get("polarities", ()))
    return values


def stabilisation_is_complete(achieved_s, required_s):
    """True when the generator dwelled long enough to settle."""
    achieved = _scalar(achieved_s, "achieved_s")
    required = _scalar(required_s, "required_s")
    if achieved < 0.0:
        raise ValueError("achieved_s must be >= 0, got %g" % achieved)
    if required < 0.0:
        raise ValueError("required_s must be >= 0, got %g" % required)
    return at_least(achieved, required)


def calibration_deviation_pct(measured_a, target_a):
    """Departure of the fixture measurement from the target first peak."""
    measured = _scalar(measured_a, "measured_a")
    target = _scalar(target_a, "target_a")
    if target <= 0.0:
        raise ValueError("target_a must be > 0, got %g" % target)
    if measured <= 0.0:
        raise ValueError("measured_a must be > 0, got %g" % measured)
    return 100.0 * abs(measured - target) / target


def rise_time_is_in_band(rise_time_s, band=RISE_TIME_BAND_S):
    """True when the measured rise time falls inside the method's band."""
    rise = _scalar(rise_time_s, "rise_time_s")
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("band: must be a (minimum, maximum) pair")
    low = _scalar(band[0], "band.minimum")
    high = _scalar(band[1], "band.maximum")
    if high <= low:
        raise ValueError(
            "band: maximum (%g) must exceed its minimum (%g)" % (high, low)
        )
    if rise <= 0.0:
        raise ValueError("rise_time_s must be > 0, got %g" % rise)
    return at_least(rise, low) and at_most(rise, high)


def group_calibration(state, deviation_pct=None, tolerance_pct=CALIBRATION_TOLERANCE_PCT):
    """Group the fixture calibration as passed, out of tolerance or omitted."""
    if state not in CALIBRATION_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (", ".join(CALIBRATION_STATES), state)
        )
    if state == "omitted":
        return CALIBRATION_OMITTED
    if deviation_pct is None:
        raise ValueError("a measured calibration needs a deviation to group")
    deviation = _scalar(deviation_pct, "deviation_pct")
    tolerance = _scalar(tolerance_pct, "tolerance_pct")
    if deviation < 0.0:
        raise ValueError("deviation_pct must be >= 0, got %g" % deviation)
    if tolerance <= 0.0:
        raise ValueError("tolerance_pct must be > 0, got %g" % tolerance)
    return CALIBRATION_PASSED if at_most(deviation, tolerance) else CALIBRATION_OUT_OF_TOLERANCE


def minimum_discharge_interval_s(plane_time_constant_s, multiple=BLEED_MULTIPLE):
    """Shortest interval that lets the coupling plane bleed between events."""
    tau = _scalar(plane_time_constant_s, "plane_time_constant_s")
    count = _scalar(multiple, "multiple")
    if tau <= 0.0:
        raise ValueError("plane_time_constant_s must be > 0, got %g" % tau)
    if count < 1.0:
        raise ValueError("multiple must be >= 1, got %g" % count)
    return count * tau


def total_discharge_count(levels, polarities, points, per_point):
    """Total discharges the declared matrix comes to."""
    for name, value in (("points", points), ("per_point", per_point)):
        number = _scalar(value, name)
        if number < 1.0 or number != math.floor(number):
            raise ValueError("%s must be a whole number >= 1, got %g" % (name, number))
    if not levels:
        raise ValueError("levels: at least one severity level is required")
    if not polarities:
        raise ValueError("polarities: at least one polarity is required")
    return int(len(levels) * len(polarities) * int(points) * int(per_point))


def estimated_duration_s(total_discharges, interval_s):
    """Bench time the application steps take at the effective interval."""
    total = _scalar(total_discharges, "total_discharges")
    interval = _scalar(interval_s, "interval_s")
    if total < 1.0 or total != math.floor(total):
        raise ValueError("total_discharges must be a whole number >= 1, got %g" % total)
    if interval <= 0.0:
        raise ValueError("interval_s must be > 0, got %g" % interval)
    return (total - 1.0) * interval


def build_step_plan(procedure, calibration_group, effective_interval_s):
    """Order the stabilisation, calibration and application steps."""
    interval = _scalar(effective_interval_s, "effective_interval_s")
    if interval <= 0.0:
        raise ValueError("effective_interval_s must be > 0, got %g" % interval)
    if calibration_group not in (
        CALIBRATION_PASSED,
        CALIBRATION_OUT_OF_TOLERANCE,
        CALIBRATION_OMITTED,
    ):
        raise ValueError("calibration_group %r is not a group" % (calibration_group,))

    plan = [
        {
            "action": "stabilise",
            "detail": "hold the generator powered for the settling dwell",
            "duration_s": procedure["required_warm_up_s"],
        }
    ]
    if calibration_group != CALIBRATION_OMITTED:
        plan.append(
            {
                "action": "calibrate",
                "detail": "discharge into the calibration fixture and record the "
                "first peak and the rise time",
                "duration_s": 0.0,
            }
        )
    for level in procedure["levels_v"]:
        for polarity in procedure["polarities"]:
            for point in range(1, int(procedure["discharge_points"]) + 1):
                plan.append(
                    {
                        "action": "expose",
                        "detail": "apply the discharges to the coupling plane at "
                        "this point and watch the unit through each one",
                        "level_v": level,
                        "polarity": polarity,
                        "point": point,
                        "repeats": int(procedure["discharges_per_point"]),
                        "interval_s": interval,
                    }
                )
    plan.append(
        {
            "action": "recover",
            "detail": "return the unit to its reference state and record any "
            "upset that did not clear on its own",
            "duration_s": 0.0,
        }
    )
    for index, step in enumerate(plan):
        step["index"] = index
    return tuple(plan)


def assess_indirect_discharge_procedure(spec):
    """Full clause 5.4.12.4 assessment of an indirect discharge run."""
    procedure = validate_procedure(spec)

    findings = []
    limitations = []

    settled = stabilisation_is_complete(
        procedure["achieved_warm_up_s"], procedure["required_warm_up_s"]
    )
    if not settled:
        findings.append(
            "generator dwelled %g s against the %g s it needs to settle, so the "
            "first discharges are delivered by an unsettled source"
            % (procedure["achieved_warm_up_s"], procedure["required_warm_up_s"])
        )

    deviation = None
    rise_ok = None
    if procedure["calibration_state"] == "measured":
        deviation = calibration_deviation_pct(
            procedure["measured_first_peak_a"], procedure["target_first_peak_a"]
        )
        rise_ok = rise_time_is_in_band(procedure["measured_rise_time_s"])
    group = group_calibration(procedure["calibration_state"], deviation)
    if group == CALIBRATION_OUT_OF_TOLERANCE:
        findings.append(
            "fixture calibration reads %g percent from the target first peak, "
            "past the %g percent the method allows" % (deviation, CALIBRATION_TOLERANCE_PCT)
        )
    if group == CALIBRATION_OMITTED:
        limitations.append(
            "the fixture calibration was skipped, so the delivered amplitudes "
            "rest on the generator's own record alone"
        )
    if rise_ok is False:
        findings.append(
            "measured rise time %g s is outside the band the method defines, so "
            "the delivered event is not the one the levels refer to"
            % procedure["measured_rise_time_s"]
        )

    minimum_interval = minimum_discharge_interval_s(procedure["plane_time_constant_s"])
    interval_ok = at_least(procedure["discharge_interval_s"], minimum_interval)
    if not interval_ok:
        findings.append(
            "discharge interval %g s is shorter than the %g s the coupling plane "
            "needs to bleed, so later events start on a charged plane"
            % (procedure["discharge_interval_s"], minimum_interval)
        )
    effective_interval = max(procedure["discharge_interval_s"], minimum_interval)

    repeats_ok = procedure["discharges_per_point"] >= MINIMUM_DISCHARGES_PER_POINT
    if not repeats_ok:
        findings.append(
            "%d discharges per point is below the %d the method needs before an "
            "absence of upset means anything"
            % (int(procedure["discharges_per_point"]), MINIMUM_DISCHARGES_PER_POINT)
        )

    if not procedure["unit_monitored"]:
        findings.append(
            "the unit is not watched through the application steps, so an upset "
            "that clears on its own leaves no trace in the run"
        )

    if len(procedure["polarities"]) < len(POLARITIES):
        limitations.append(
            "only the %s polarity is exercised, so the run covers half the "
            "exposure the method describes" % procedure["polarities"][0]
        )

    total = total_discharge_count(
        procedure["levels_v"],
        procedure["polarities"],
        procedure["discharge_points"],
        procedure["discharges_per_point"],
    )
    plan = build_step_plan(procedure, group, effective_interval)

    if findings:
        verdict = VERDICT_NONCOMPLIANT
    elif limitations:
        verdict = VERDICT_WITH_LIMITATIONS
    else:
        verdict = VERDICT_COMPLIANT

    return {
        "procedure": procedure,
        "stabilisation_is_complete": settled,
        "calibration_group": group,
        "calibration_deviation_pct": deviation,
        "rise_time_is_in_band": rise_ok,
        "minimum_discharge_interval_s": minimum_interval,
        "effective_interval_s": effective_interval,
        "interval_is_adequate": interval_ok,
        "repeats_are_adequate": repeats_ok,
        "total_discharges": total,
        "estimated_duration_s": estimated_duration_s(total, effective_interval),
        "step_plan": plan,
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
