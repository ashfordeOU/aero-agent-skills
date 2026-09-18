#!/usr/bin/env python3
"""Contact discharge test procedure, ECSS-E-ST-20-07C clause 5.4.14.4.

Paraphrased procedure, no verbatim standard text. The clause covers two
things: proving the generator delivers the discharge current waveform
the severity level names, and then applying the discharges to the unit
in an order that makes the outcome readable. This module turns that into
a deterministic plan and assessment:

  charge level + waveform coefficients -> the nominal current target
  measured target readings             -> passed / out of tolerance / omitted
  declared interval + recharge time    -> the interval the run is held to
  points x polarities x levels         -> the ordered application sequence
  sequence + interval + overheads      -> discharge total and bench time

The waveform coefficients and tolerances are inputs with documented
defaults, so a campaign working to a different current target supplies
its own rather than editing this module.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Targets and deviations are floats, so a reading
# that exactly meets a limit can land a few units in the last place off
# it. These absorb representation error only; they never relax a limit.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Current-target coefficients, in amperes per kilovolt of charge
# voltage, for the first peak and for the two decay sample points.
DEFAULT_WAVEFORM_COEFFICIENTS = {
    "first_peak_a_per_kv": 3.75,
    "current_at_30ns_a_per_kv": 2.0,
    "current_at_60ns_a_per_kv": 1.0,
}

# Fractional tolerance each reading is allowed against its nominal.
DEFAULT_AMPLITUDE_TOLERANCES = {
    "first_peak_a": 0.15,
    "current_at_30ns_a": 0.30,
    "current_at_60ns_a": 0.30,
}

# Admissible rise time of the delivered edge, in seconds.
DEFAULT_RISE_TIME_BAND_S = (0.6e-9, 1.0e-9)

# A calibration older than this has stopped describing the generator.
DEFAULT_CALIBRATION_VALIDITY_H = 24.0

# Floor on the interval between events, whatever the generator can do.
MIN_INTERVAL_S = 1.0

# Below this many discharges at a point, polarity and level, the absence
# of an upset is not evidence of anything.
MIN_DISCHARGES_PER_POINT = 10

WAVEFORM_READINGS = ("first_peak_a", "current_at_30ns_a", "current_at_60ns_a")

CALIBRATION_STATES = ("measured", "omitted")

CALIBRATION_PASSED = "calibration-passed"
CALIBRATION_OUT_OF_TOLERANCE = "calibration-out-of-tolerance"
CALIBRATION_OMITTED = "calibration-omitted"

WITHIN_TOLERANCE = "within-tolerance"
OUT_OF_TOLERANCE = "out-of-tolerance"

POLARITY_TOKENS = {
    "+": "positive",
    "pos": "positive",
    "positive": "positive",
    "-": "negative",
    "neg": "negative",
    "negative": "negative",
}

STEP_STABILISE = "stabilise"
STEP_CALIBRATE = "calibrate"
STEP_APPLY = "apply"
STEP_RECOVER = "recover"

VERDICT_CONFORMING = "procedure-conforming"
VERDICT_WITH_LIMITATIONS = "procedure-conforming-with-limitations"
VERDICT_NONCONFORMING = "procedure-nonconforming"


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


def _label(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty label" % (where, key))
    return value.strip()


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


def normalize_polarity(token):
    """Map a polarity cell onto 'positive' or 'negative'."""
    if not isinstance(token, str):
        raise ValueError("polarity must be a string, got %r" % (token,))
    key = token.strip().lower()
    if key not in POLARITY_TOKENS:
        raise ValueError(
            "unrecognized polarity %r; recognized: %s"
            % (token, ", ".join(sorted(set(POLARITY_TOKENS))))
        )
    return POLARITY_TOKENS[key]


def resolve_coefficients(coefficients=None):
    """Validate the amperes-per-kilovolt current-target coefficients."""
    if coefficients is None:
        return dict(DEFAULT_WAVEFORM_COEFFICIENTS)
    if not isinstance(coefficients, dict):
        raise ValueError("coefficients: must be a mapping")
    resolved = {}
    for key in DEFAULT_WAVEFORM_COEFFICIENTS:
        value = _number(coefficients, key, "coefficients")
        if value <= 0.0:
            raise ValueError("coefficients: %s must be > 0, got %g" % (key, value))
        resolved[key] = value
    for key in coefficients:
        if key not in DEFAULT_WAVEFORM_COEFFICIENTS:
            raise ValueError(
                "coefficients: unknown key %r; known: %s"
                % (key, ", ".join(sorted(DEFAULT_WAVEFORM_COEFFICIENTS)))
            )
    return resolved


def resolve_tolerances(tolerances=None):
    """Validate the fractional tolerance allowed on each waveform reading."""
    if tolerances is None:
        return dict(DEFAULT_AMPLITUDE_TOLERANCES)
    if not isinstance(tolerances, dict):
        raise ValueError("tolerances: must be a mapping")
    resolved = {}
    for key in DEFAULT_AMPLITUDE_TOLERANCES:
        value = _number(tolerances, key, "tolerances")
        if value <= 0.0 or value >= 1.0:
            raise ValueError(
                "tolerances: %s must be a fraction in (0, 1), got %g" % (key, value)
            )
        resolved[key] = value
    for key in tolerances:
        if key not in DEFAULT_AMPLITUDE_TOLERANCES:
            raise ValueError(
                "tolerances: unknown key %r; known: %s"
                % (key, ", ".join(sorted(DEFAULT_AMPLITUDE_TOLERANCES)))
            )
    return resolved


def nominal_waveform(level_kv, coefficients=None):
    """Current target the generator has to deliver at a charge level."""
    level = _scalar(level_kv, "level_kv")
    if level <= 0.0:
        raise ValueError("level_kv must be > 0, got %g" % level)
    resolved = resolve_coefficients(coefficients)
    return {
        "first_peak_a": level * resolved["first_peak_a_per_kv"],
        "current_at_30ns_a": level * resolved["current_at_30ns_a_per_kv"],
        "current_at_60ns_a": level * resolved["current_at_60ns_a_per_kv"],
    }


def relative_deviation(measured, nominal):
    """Signed fractional departure of a reading from its nominal value."""
    m = _scalar(measured, "measured")
    n = _scalar(nominal, "nominal")
    if n <= 0.0:
        raise ValueError("nominal must be > 0, got %g" % n)
    if m < 0.0:
        raise ValueError("measured must be >= 0, got %g" % m)
    return (m - n) / n


def categorize_amplitude(measured, nominal, tolerance_fraction):
    """Group one waveform reading against its allowed fractional tolerance."""
    tol = _scalar(tolerance_fraction, "tolerance_fraction")
    if tol <= 0.0 or tol >= 1.0:
        raise ValueError("tolerance_fraction must be in (0, 1), got %g" % tol)
    deviation = abs(relative_deviation(measured, nominal))
    return WITHIN_TOLERANCE if at_most(deviation, tol) else OUT_OF_TOLERANCE


def validate_rise_time_band(band=None):
    """Validate the admissible rise-time band and return it."""
    if band is None:
        return tuple(DEFAULT_RISE_TIME_BAND_S)
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("rise_time_band: must be a (minimum, maximum) pair")
    low = _scalar(band[0], "rise_time_band.minimum")
    high = _scalar(band[1], "rise_time_band.maximum")
    if low <= 0.0:
        raise ValueError("rise_time_band minimum must be > 0, got %g" % low)
    if high <= low:
        raise ValueError(
            "rise_time_band maximum (%g) must exceed its minimum (%g)" % (high, low)
        )
    return (low, high)


def rise_time_is_admissible(measured_s, band=None):
    """True when the delivered edge sits inside its admissible band."""
    low, high = validate_rise_time_band(band)
    value = _scalar(measured_s, "measured_s")
    if value <= 0.0:
        raise ValueError("measured rise time must be > 0, got %g" % value)
    return at_least(value, low) and at_most(value, high)


def grade_calibration(calibration, coefficients=None, tolerances=None,
                      rise_time_band=None, validity_h=None):
    """Group the waveform calibration and report what it costs the run."""
    where = "calibration"
    if not isinstance(calibration, dict):
        raise ValueError("%s: record must be a mapping" % where)
    state = calibration.get("state")
    if not isinstance(state, str) or state.strip().lower() not in CALIBRATION_STATES:
        raise ValueError(
            "%s: state must be one of %s" % (where, ", ".join(CALIBRATION_STATES))
        )
    state = state.strip().lower()
    if state == "omitted":
        return {
            "state": CALIBRATION_OMITTED,
            "readings": {},
            "deviations": {},
            "rise_time_admissible": None,
            "age_h": None,
            "expired": False,
            "findings": [],
            "limitations": [
                "the discharge current waveform was not measured, so every "
                "amplitude in this run rests on the generator's own record"
            ],
        }

    level_kv = _number(calibration, "level_kv", where)
    if level_kv <= 0.0:
        raise ValueError("%s: level_kv must be > 0, got %g" % (where, level_kv))
    nominal = nominal_waveform(level_kv, coefficients)
    tol = resolve_tolerances(tolerances)

    readings = {}
    deviations = {}
    categories = {}
    for key in WAVEFORM_READINGS:
        measured = _number(calibration, "measured_" + key, where)
        if measured <= 0.0:
            raise ValueError(
                "%s: measured_%s must be > 0, got %g" % (where, key, measured)
            )
        readings[key] = measured
        deviations[key] = relative_deviation(measured, nominal[key])
        categories[key] = categorize_amplitude(measured, nominal[key], tol[key])

    rise_time = _number(calibration, "measured_rise_time_s", where)
    if rise_time <= 0.0:
        raise ValueError(
            "%s: measured_rise_time_s must be > 0, got %g" % (where, rise_time)
        )
    edge_ok = rise_time_is_admissible(rise_time, rise_time_band)

    age = _number(calibration, "age_h", where)
    if age < 0.0:
        raise ValueError("%s: age_h must be >= 0, got %g" % (where, age))
    validity = DEFAULT_CALIBRATION_VALIDITY_H if validity_h is None else _scalar(
        validity_h, "validity_h"
    )
    if validity <= 0.0:
        raise ValueError("validity_h must be > 0, got %g" % validity)
    expired = not at_most(age, validity)

    findings = []
    for key in WAVEFORM_READINGS:
        if categories[key] == OUT_OF_TOLERANCE:
            findings.append(
                "calibrated %s is %g A against a %g A target, %.1f%% out of "
                "tolerance" % (
                    key.replace("_", " "),
                    readings[key],
                    nominal[key],
                    100.0 * abs(deviations[key]),
                )
            )
    if not edge_ok:
        low, high = validate_rise_time_band(rise_time_band)
        findings.append(
            "delivered edge rises in %g s, outside the %g s to %g s band, so the "
            "event has a different spectrum from the one the level names"
            % (rise_time, low, high)
        )
    if expired:
        findings.append(
            "calibration is %g h old against a %g h validity window, so it no "
            "longer describes the generator this run used" % (age, validity)
        )

    passed = not findings
    return {
        "state": CALIBRATION_PASSED if passed else CALIBRATION_OUT_OF_TOLERANCE,
        "nominal": nominal,
        "readings": readings,
        "deviations": deviations,
        "categories": categories,
        "rise_time_s": rise_time,
        "rise_time_admissible": edge_ok,
        "age_h": age,
        "expired": expired,
        "findings": findings,
        "limitations": [],
    }


def effective_interval_s(declared_s, recharge_s, minimum_s=MIN_INTERVAL_S):
    """The interval the run is actually held to: the slowest of the three."""
    declared = _scalar(declared_s, "declared_s")
    recharge = _scalar(recharge_s, "recharge_s")
    floor_s = _scalar(minimum_s, "minimum_s")
    if declared <= 0.0:
        raise ValueError("declared_s must be > 0, got %g" % declared)
    if recharge <= 0.0:
        raise ValueError("recharge_s must be > 0, got %g" % recharge)
    if floor_s <= 0.0:
        raise ValueError("minimum_s must be > 0, got %g" % floor_s)
    return max(declared, recharge, floor_s)


def validate_levels(levels_kv):
    """Validate a strictly ascending, positive set of charge levels."""
    if isinstance(levels_kv, (str, bytes)) or not isinstance(levels_kv, (list, tuple)):
        raise ValueError("levels_kv: must be a sequence of charge levels")
    if not levels_kv:
        raise ValueError("levels_kv: at least one level must be declared")
    values = []
    for index, level in enumerate(levels_kv):
        value = _number({"v": level}, "v", "levels_kv[%d]" % index)
        if value <= 0.0:
            raise ValueError("levels_kv[%d] must be > 0, got %g" % (index, value))
        values.append(value)
    for index in range(1, len(values)):
        if values[index] <= values[index - 1]:
            raise ValueError(
                "levels_kv must ascend strictly; %g follows %g at index %d"
                % (values[index], values[index - 1], index)
            )
    return values


def validate_points(points):
    """Validate the declared contact application points."""
    if isinstance(points, (str, bytes)) or not isinstance(points, (list, tuple)):
        raise ValueError("discharge_points: must be a sequence of point labels")
    if not points:
        raise ValueError("discharge_points: at least one point must be declared")
    labels = []
    for index, point in enumerate(points):
        label = _label({"p": point}, "p", "discharge_points[%d]" % index)
        if label in labels:
            raise ValueError("discharge_points: %r appears twice" % label)
        labels.append(label)
    return labels


def validate_polarities(polarities):
    """Validate and normalize the polarity set the run covers."""
    if isinstance(polarities, (str, bytes)) or not isinstance(
        polarities, (list, tuple)
    ):
        raise ValueError("polarities: must be a sequence of polarity tokens")
    if not polarities:
        raise ValueError("polarities: at least one polarity must be declared")
    seen = []
    for token in polarities:
        value = normalize_polarity(token)
        if value in seen:
            raise ValueError("polarities: %s appears twice" % value)
        seen.append(value)
    return sorted(seen)


def validate_run(run):
    """Validate a declared contact discharge run and return it normalized."""
    where = "run"
    if not isinstance(run, dict):
        raise ValueError("%s: record must be a mapping" % where)

    dwell = _number(run, "stabilisation_dwell_s", where)
    if dwell < 0.0:
        raise ValueError("%s: stabilisation_dwell_s must be >= 0" % where)
    required_dwell = _number(run, "required_stabilisation_s", where)
    if required_dwell < 0.0:
        raise ValueError("%s: required_stabilisation_s must be >= 0" % where)

    declared_interval = _number(run, "declared_interval_s", where)
    recharge = _number(run, "generator_recharge_s", where)
    if declared_interval <= 0.0:
        raise ValueError("%s: declared_interval_s must be > 0" % where)
    if recharge <= 0.0:
        raise ValueError("%s: generator_recharge_s must be > 0" % where)

    per_point = _number(run, "discharges_per_point", where)
    if per_point < 1.0 or per_point != math.floor(per_point):
        raise ValueError(
            "%s: discharges_per_point must be a whole number >= 1, got %g"
            % (where, per_point)
        )

    overhead = _number(run, "per_point_overhead_s", where)
    if overhead < 0.0:
        raise ValueError("%s: per_point_overhead_s must be >= 0" % where)

    monitored = run.get("unit_monitored", True)
    if not isinstance(monitored, bool):
        raise ValueError("%s: unit_monitored must be true or false" % where)

    return {
        "stabilisation_dwell_s": dwell,
        "required_stabilisation_s": required_dwell,
        "declared_interval_s": declared_interval,
        "generator_recharge_s": recharge,
        "discharges_per_point": int(per_point),
        "per_point_overhead_s": overhead,
        "unit_monitored": monitored,
        "discharge_points": validate_points(run.get("discharge_points")),
        "polarities": validate_polarities(run.get("polarities")),
        "levels_kv": validate_levels(run.get("levels_kv")),
    }


def build_application_plan(run, calibration_state=CALIBRATION_PASSED):
    """Order the stabilise, calibrate, apply and recover steps of the run."""
    record = validate_run(run)
    if calibration_state not in (
        CALIBRATION_PASSED,
        CALIBRATION_OUT_OF_TOLERANCE,
        CALIBRATION_OMITTED,
    ):
        raise ValueError("unrecognized calibration state %r" % (calibration_state,))
    steps = [{"step": STEP_STABILISE, "dwell_s": record["stabilisation_dwell_s"]}]
    if calibration_state != CALIBRATION_OMITTED:
        steps.append({"step": STEP_CALIBRATE, "state": calibration_state})
    for level in record["levels_kv"]:
        for point in record["discharge_points"]:
            for polarity in record["polarities"]:
                steps.append(
                    {
                        "step": STEP_APPLY,
                        "level_kv": level,
                        "point": point,
                        "polarity": polarity,
                        "discharges": record["discharges_per_point"],
                    }
                )
    steps.append({"step": STEP_RECOVER})
    return steps


def total_discharges(run):
    """Number of individual events the ordered plan calls for."""
    record = validate_run(run)
    return (
        len(record["discharge_points"])
        * len(record["polarities"])
        * len(record["levels_kv"])
        * record["discharges_per_point"]
    )


def bench_time_s(run, interval_s):
    """Bench time the plan occupies at the interval it is held to."""
    record = validate_run(run)
    interval = _scalar(interval_s, "interval_s")
    if interval <= 0.0:
        raise ValueError("interval_s must be > 0, got %g" % interval)
    application_blocks = (
        len(record["discharge_points"])
        * len(record["polarities"])
        * len(record["levels_kv"])
    )
    return (
        record["stabilisation_dwell_s"]
        + total_discharges(run) * interval
        + application_blocks * record["per_point_overhead_s"]
    )


def assess_contact_discharge_procedure(run, calibration, coefficients=None,
                                       tolerances=None, rise_time_band=None,
                                       validity_h=None):
    """Full clause 5.4.14.4 assessment of a contact discharge run."""
    record = validate_run(run)
    graded = grade_calibration(
        calibration, coefficients, tolerances, rise_time_band, validity_h
    )

    findings = list(graded["findings"])
    limitations = list(graded["limitations"])

    dwell_ok = at_least(
        record["stabilisation_dwell_s"], record["required_stabilisation_s"]
    )
    if not dwell_ok:
        findings.append(
            "generator dwelled %g s against the %g s it needs to settle, so the "
            "charge voltage was still moving when the first events were taken"
            % (record["stabilisation_dwell_s"], record["required_stabilisation_s"])
        )

    interval = effective_interval_s(
        record["declared_interval_s"], record["generator_recharge_s"]
    )
    interval_stretched = not at_least(record["declared_interval_s"], interval)
    if interval_stretched:
        findings.append(
            "declared interval of %g s is shorter than the %g s the generator "
            "recharge and the floor impose; the run is held to the longer one"
            % (record["declared_interval_s"], interval)
        )

    repeats_ok = record["discharges_per_point"] >= MIN_DISCHARGES_PER_POINT
    if not repeats_ok:
        findings.append(
            "%d discharges at a point, polarity and level is below the %d needed "
            "before the absence of an upset means anything"
            % (record["discharges_per_point"], MIN_DISCHARGES_PER_POINT)
        )

    if not record["unit_monitored"]:
        findings.append(
            "the unit is not watched through the application steps, so an upset "
            "that clears between events leaves no trace"
        )

    if len(record["polarities"]) < 2:
        limitations.append(
            "only the %s polarity is applied, so half of the exposure is not "
            "covered by this run" % record["polarities"][0]
        )

    plan = build_application_plan(run, graded["state"])
    events = total_discharges(run)
    duration = bench_time_s(run, interval)

    if findings:
        verdict = VERDICT_NONCONFORMING
    elif limitations:
        verdict = VERDICT_WITH_LIMITATIONS
    else:
        verdict = VERDICT_CONFORMING

    return {
        "run": record,
        "calibration": graded,
        "stabilisation_is_adequate": dwell_ok,
        "effective_interval_s": interval,
        "interval_was_stretched": interval_stretched,
        "discharges_per_point_is_adequate": repeats_ok,
        "plan": plan,
        "total_discharges": events,
        "bench_time_s": duration,
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
