#!/usr/bin/env python3
"""Calibration and upkeep fitness check for a solar simulator.

Anchor: ECSS-E-ST-20-08C clause 10.2.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar simulator is measuring equipment, and its output is only worth
what its last upkeep says it is. Three beam qualities decide whether it
can stand in for sunlight at all, and two upkeep counters decide
whether the value it last reported is still the value it reports:

    beam qualities
        spatial non-uniformity   how far the irradiance varies over the
                                 test plane, percent
        temporal instability     how far the irradiance moves during a
                                 measurement, percent
        spectral match           the ratio of measured to reference
                                 irradiance in each wavelength band

    upkeep counters
        lamp hours run against the rated life of the lamp
        days elapsed since the beam was set against a reference cell

Each beam quality earns a grade of A, B or C from its bounds, and the
simulator takes the worst of the three: a beam that is uniform and
steady but spectrally wrong is a spectrally wrong beam. A measurement
in turn demands a grade, and a simulator that does not reach it is not
broken -- it is usable for the work its own grade supports, and no
further.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SIMULATOR_GRADES = ("A", "B", "C")
GRADE_OUT_OF_RANGE = "out-of-range"
_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, GRADE_OUT_OF_RANGE: 3}

BEAM_QUALITIES = (
    "spatial-non-uniformity",
    "temporal-instability",
    "spectral-match",
)

UPKEEP_SERVICEABLE = "serviceable"
UPKEEP_DUE_SOON = "due-soon"
UPKEEP_DUE = "due"

VERDICT_FIT = "fit-for-measurement"
VERDICT_CONDITIONAL = "conditional-use"
VERDICT_RECALIBRATE = "recalibration-required"
VERDICT_SERVICE = "service-required"

DEFAULT_SIMULATOR_BOUNDS = {
    "spatial_non_uniformity_percent": {"A": 2.0, "B": 5.0, "C": 10.0},
    "temporal_instability_percent": {"A": 2.0, "B": 5.0, "C": 10.0},
    "spectral_match_ratio": {
        "A": (0.75, 1.25),
        "B": (0.60, 1.40),
        "C": (0.40, 2.00),
    },
}

DEFAULT_UPKEEP_POLICY = {
    "lamp_rated_hours": 1000.0,
    "lamp_warning_fraction": 0.8,
    "reference_calibration_interval_days": 180.0,
    "calibration_warning_fraction": 0.9,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A beam quality sitting exactly on a grade bound must earn the same
    grade on every platform. The bound is never loosened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_simulator_bounds(bounds):
    """Check a beam-grade table is complete and monotone across grades."""
    if not isinstance(bounds, dict):
        raise ValueError("bounds must be a mapping, got %r" % (bounds,))
    for key in ("spatial_non_uniformity_percent", "temporal_instability_percent"):
        table = bounds.get(key)
        if not isinstance(table, dict):
            raise ValueError("bounds %s must be a mapping" % key)
        missing = set(SIMULATOR_GRADES) - set(table)
        if missing:
            raise ValueError(
                "bounds %s is missing grades: %s" % (key, ", ".join(sorted(missing)))
            )
        previous = 0.0
        for grade in SIMULATOR_GRADES:
            limit = _require_positive("bounds %s[%s]" % (key, grade), table[grade])
            if limit < previous:
                raise ValueError(
                    "bounds %s is not monotone: grade %s tightens on its predecessor"
                    % (key, grade)
                )
            previous = limit
    spectral = bounds.get("spectral_match_ratio")
    if not isinstance(spectral, dict):
        raise ValueError("bounds spectral_match_ratio must be a mapping")
    missing = set(SIMULATOR_GRADES) - set(spectral)
    if missing:
        raise ValueError(
            "bounds spectral_match_ratio is missing grades: %s"
            % ", ".join(sorted(missing))
        )
    for grade in SIMULATOR_GRADES:
        window = spectral[grade]
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError(
                "bounds spectral_match_ratio[%s] must be a low/high pair" % grade
            )
        low = _require_positive("spectral low bound %s" % grade, window[0])
        high = _require_positive("spectral high bound %s" % grade, window[1])
        if high <= low:
            raise ValueError(
                "bounds spectral_match_ratio[%s] has a high bound at or below its low"
                % grade
            )
    return bounds


def validate_upkeep_policy(policy):
    """Check the lamp-life and calibration-interval counters are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("lamp_rated_hours", policy.get("lamp_rated_hours"))
    _require_positive(
        "reference_calibration_interval_days",
        policy.get("reference_calibration_interval_days"),
    )
    for key in ("lamp_warning_fraction", "calibration_warning_fraction"):
        fraction = _require_positive(key, policy.get(key))
        if fraction > 1.0:
            raise ValueError("%s must not exceed one, got %r" % (key, fraction))
    return policy


def grade_percent_quality(value, grade_table):
    """Grade a percentage beam quality against its A/B/C bounds."""
    measured = _require_non_negative("quality value", value)
    if not isinstance(grade_table, dict):
        raise ValueError("grade_table must be a mapping, got %r" % (grade_table,))
    for grade in SIMULATOR_GRADES:
        if grade not in grade_table:
            raise ValueError("grade_table is missing grade %s" % grade)
        if _at_most(measured, _require_positive("bound %s" % grade, grade_table[grade])):
            return grade
    return GRADE_OUT_OF_RANGE


def grade_spectral_match(band_ratios, spectral_bounds):
    """Grade the spectral match band by band, worst band winning."""
    if not isinstance(band_ratios, dict) or not band_ratios:
        raise ValueError(
            "band_ratios must be a non-empty mapping of band to ratio, got %r"
            % (band_ratios,)
        )
    if not isinstance(spectral_bounds, dict):
        raise ValueError("spectral_bounds must be a mapping")
    per_band = {}
    for band, ratio in sorted(band_ratios.items()):
        measured = _require_positive("band ratio %s" % band, ratio)
        band_grade = GRADE_OUT_OF_RANGE
        for grade in SIMULATOR_GRADES:
            window = spectral_bounds.get(grade)
            if not isinstance(window, (list, tuple)) or len(window) != 2:
                raise ValueError("spectral_bounds[%s] must be a low/high pair" % grade)
            low = _require_positive("spectral low bound %s" % grade, window[0])
            high = _require_positive("spectral high bound %s" % grade, window[1])
            if _at_least(measured, low) and _at_most(measured, high):
                band_grade = grade
                break
        per_band[band] = band_grade
    worst = worst_grade(per_band.values())
    return {"grade": worst, "per_band": per_band}


def worst_grade(grades):
    """Poorest grade in a collection, out-of-range beating every letter."""
    collected = list(grades)
    if not collected:
        raise ValueError("no grades to compare")
    for grade in collected:
        if grade not in _GRADE_ORDER:
            raise ValueError("unknown grade %r" % (grade,))
    return max(collected, key=lambda grade: _GRADE_ORDER[grade])


def grade_meets_requirement(achieved, required):
    """True when the achieved grade is at least as good as the required one."""
    _require_choice("achieved", achieved, tuple(_GRADE_ORDER))
    _require_choice("required", required, SIMULATOR_GRADES)
    return _GRADE_ORDER[achieved] <= _GRADE_ORDER[required]


def simulator_grade(measurements, bounds=DEFAULT_SIMULATOR_BOUNDS):
    """Grade of the beam as a whole: the worst of the three qualities."""
    if not isinstance(measurements, dict):
        raise ValueError("measurements must be a mapping, got %r" % (measurements,))
    validate_simulator_bounds(bounds)
    spatial = grade_percent_quality(
        measurements.get("spatial_non_uniformity_percent"),
        bounds["spatial_non_uniformity_percent"],
    )
    temporal = grade_percent_quality(
        measurements.get("temporal_instability_percent"),
        bounds["temporal_instability_percent"],
    )
    spectral = grade_spectral_match(
        measurements.get("spectral_match_ratios"), bounds["spectral_match_ratio"]
    )
    per_quality = {
        "spatial-non-uniformity": spatial,
        "temporal-instability": temporal,
        "spectral-match": spectral["grade"],
    }
    return {
        "grade": worst_grade(per_quality.values()),
        "per_quality": per_quality,
        "spectral_per_band": spectral["per_band"],
    }


def lamp_service_status(hours_run, rated_hours, warning_fraction=0.8):
    """Where the lamp sits against its rated life."""
    run = _require_non_negative("hours_run", hours_run)
    rated = _require_positive("rated_hours", rated_hours)
    fraction_limit = _require_positive("warning_fraction", warning_fraction)
    if fraction_limit > 1.0:
        raise ValueError("warning_fraction must not exceed one")
    fraction = run / rated
    if not _at_most(run, rated):
        status = UPKEEP_DUE
    elif not _at_most(fraction, fraction_limit):
        status = UPKEEP_DUE_SOON
    else:
        status = UPKEEP_SERVICEABLE
    return {
        "hours_run": run,
        "rated_hours": rated,
        "hours_remaining": rated - run,
        "fraction_used": fraction,
        "status": status,
    }


def calibration_due_status(days_since, interval_days, warning_fraction=0.9):
    """Where the reference-cell calibration sits inside its interval."""
    elapsed = _require_non_negative("days_since", days_since)
    interval = _require_positive("interval_days", interval_days)
    fraction_limit = _require_positive("warning_fraction", warning_fraction)
    if fraction_limit > 1.0:
        raise ValueError("warning_fraction must not exceed one")
    fraction = elapsed / interval
    if not _at_most(elapsed, interval):
        status = UPKEEP_DUE
    elif not _at_most(fraction, fraction_limit):
        status = UPKEEP_DUE_SOON
    else:
        status = UPKEEP_SERVICEABLE
    return {
        "days_since": elapsed,
        "interval_days": interval,
        "days_remaining": interval - elapsed,
        "fraction_elapsed": fraction,
        "status": status,
    }


def assess_simulator_fitness(
    case, bounds=DEFAULT_SIMULATOR_BOUNDS, policy=DEFAULT_UPKEEP_POLICY
):
    """Full clause 10.2.6 upkeep and calibration fitness check."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_simulator_bounds(bounds)
    validate_upkeep_policy(policy)
    required = _require_choice(
        "required_grade", case.get("required_grade"), SIMULATOR_GRADES
    )
    beam = simulator_grade(case, bounds)
    lamp = lamp_service_status(
        case.get("lamp_hours_run"),
        case.get("lamp_rated_hours", policy["lamp_rated_hours"]),
        case.get("lamp_warning_fraction", policy["lamp_warning_fraction"]),
    )
    calibration = calibration_due_status(
        case.get("days_since_reference_calibration"),
        case.get(
            "reference_calibration_interval_days",
            policy["reference_calibration_interval_days"],
        ),
        case.get("calibration_warning_fraction", policy["calibration_warning_fraction"]),
    )
    meets = grade_meets_requirement(beam["grade"], required)
    findings = []
    if beam["grade"] == GRADE_OUT_OF_RANGE:
        findings.append(
            "at least one beam quality sits outside every grade bound; the "
            "simulator cannot stand in for sunlight until it is serviced"
        )
    if lamp["status"] == UPKEEP_DUE:
        findings.append(
            "the lamp has run %.1f hours against a rated %.1f; replace it before "
            "the beam is graded again" % (lamp["hours_run"], lamp["rated_hours"])
        )
    elif lamp["status"] == UPKEEP_DUE_SOON:
        findings.append(
            "the lamp is inside its warning fraction with %.1f hours left"
            % lamp["hours_remaining"]
        )
    if calibration["status"] == UPKEEP_DUE:
        findings.append(
            "the reference-cell calibration is %.1f days past its interval"
            % (-calibration["days_remaining"])
        )
    elif calibration["status"] == UPKEEP_DUE_SOON:
        findings.append(
            "the reference-cell calibration is inside its warning fraction with "
            "%.1f days left" % calibration["days_remaining"]
        )
    if not meets:
        findings.append(
            "the beam grades %s against a required %s; it serves only the work "
            "its own grade supports" % (beam["grade"], required)
        )
    if beam["grade"] == GRADE_OUT_OF_RANGE or lamp["status"] == UPKEEP_DUE:
        verdict = VERDICT_SERVICE
    elif calibration["status"] == UPKEEP_DUE:
        verdict = VERDICT_RECALIBRATE
    elif not meets or UPKEEP_DUE_SOON in (lamp["status"], calibration["status"]):
        verdict = VERDICT_CONDITIONAL
    else:
        verdict = VERDICT_FIT
    return {
        "required_grade": required,
        "achieved_grade": beam["grade"],
        "per_quality": beam["per_quality"],
        "spectral_per_band": beam["spectral_per_band"],
        "meets_required_grade": meets,
        "lamp": lamp,
        "reference_calibration": calibration,
        "verdict": verdict,
        "usable_for_measurement": verdict == VERDICT_FIT,
        "findings": findings,
    }
