#!/usr/bin/env python3
"""Ambient radiated-level baseline check, ECSS-E-ST-20-07C clause 5.2.2.3.

Paraphrased procedure, no verbatim standard text. The clause requires the
facility background to be recorded with the unit-under-test unpowered while
the support-equipment runs in the graded configuration. This module turns
that into a deterministic grading:

  configuration -> valid baseline or rejection
  sweep points  -> headroom per frequency -> category
  sweep         -> narrowband ambient peaks, coverage gaps
  measured/ambient pair -> attribution of a later graded reading

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Headroom is a difference of two float
# levels, so an exactly-satisfied requirement can land a few units in the
# last place short. The tolerance absorbs that representation error only;
# it never lowers the required headroom.
DB_TOL = 1e-9

# Conventional headroom between the recorded ambient floor and the
# applicable radiated-emission-limit, decibels.
DEFAULT_REQUIRED_HEADROOM_DB = 6.0

# A later graded reading is dominated by the unit once it stands this far
# above the ambient floor; equal to the ambient it is ambient-limited.
UNIT_DOMINANCE_DB = 6.0
AMBIENT_LIMITED_DB = 1.0

# Prominence a discrete peak must show over its local neighbourhood to be
# reported as a narrowband ambient signal, decibels.
NARROWBAND_PROMINENCE_DB = 10.0

RECOGNIZED_POLARIZATIONS = ("horizontal", "vertical")

CATEGORY_COMPLIANT = "compliant"
CATEGORY_MARGINAL = "marginal"
CATEGORY_EXCEEDANCE = "exceedance"
CATEGORIES = (CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_EXCEEDANCE)


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


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_least(value_db, requirement_db, tol_db=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value_db >= requirement_db:
        return True
    return math.isclose(value_db, requirement_db, rel_tol=0.0, abs_tol=tol_db)


def validate_ambient_configuration(config, reference_bandwidth_hz=None):
    """Validate the baseline run configuration and return a normalized copy.

    Required: unit_powered (must be False), support_equipment_powered (must
    be True), enclosure_door_closed (must be True), receiver_bandwidth_hz,
    antenna_polarization, standoff_m. When reference_bandwidth_hz is given,
    the baseline bandwidth must match it.
    """
    where = "configuration"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)
    unit_powered = _flag(config, "unit_powered", where)
    if unit_powered:
        raise ValueError(
            "%s: the baseline run requires the unit-under-test unpowered" % where
        )
    if not _flag(config, "support_equipment_powered", where):
        raise ValueError(
            "%s: the support-equipment must stay operating during the baseline run"
            % where
        )
    if not _flag(config, "enclosure_door_closed", where):
        raise ValueError("%s: the enclosure door must be closed" % where)

    bandwidth = _number(config, "receiver_bandwidth_hz", where)
    if bandwidth <= 0.0:
        raise ValueError(
            "%s: receiver_bandwidth_hz must be > 0, got %g" % (where, bandwidth)
        )
    if reference_bandwidth_hz is not None:
        reference = _number(
            {"v": reference_bandwidth_hz}, "v", "%s.reference_bandwidth_hz" % where
        )
        if reference <= 0.0:
            raise ValueError("%s: reference bandwidth must be > 0" % where)
        if not math.isclose(bandwidth, reference, rel_tol=1e-9, abs_tol=DB_TOL):
            raise ValueError(
                "%s: baseline receiver bandwidth %g Hz does not match the graded "
                "run bandwidth %g Hz" % (where, bandwidth, reference)
            )

    polarization = config.get("antenna_polarization")
    if not isinstance(polarization, str):
        raise ValueError("%s: antenna_polarization must be a string" % where)
    polarization = polarization.strip().lower()
    if polarization not in RECOGNIZED_POLARIZATIONS:
        raise ValueError(
            "%s: unrecognized antenna_polarization %r; recognized: %s"
            % (where, config.get("antenna_polarization"),
               ", ".join(RECOGNIZED_POLARIZATIONS))
        )

    standoff = _number(config, "standoff_m", where)
    if standoff <= 0.0:
        raise ValueError("%s: standoff_m must be > 0, got %g" % (where, standoff))

    return {
        "unit_powered": False,
        "support_equipment_powered": True,
        "enclosure_door_closed": True,
        "receiver_bandwidth_hz": bandwidth,
        "antenna_polarization": polarization,
        "standoff_m": standoff,
    }


def validate_sweep(points):
    """Validate the ambient sweep and return a normalized list of points.

    Each point needs frequency_hz (positive, strictly increasing),
    ambient_dbuv_m and limit_dbuv_m.
    """
    where = "sweep"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) == 0:
        raise ValueError("%s: at least one recorded point is required" % where)
    out = []
    previous = None
    for index, point in enumerate(points):
        tag = "%s[%d]" % (where, index)
        if not isinstance(point, dict):
            raise ValueError("%s: point must be a mapping" % tag)
        frequency = _number(point, "frequency_hz", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s: frequencies must increase strictly (%g Hz after %g Hz)"
                % (tag, frequency, previous)
            )
        previous = frequency
        out.append(
            {
                "frequency_hz": frequency,
                "ambient_dbuv_m": _number(point, "ambient_dbuv_m", tag),
                "limit_dbuv_m": _number(point, "limit_dbuv_m", tag),
            }
        )
    return out


def point_headroom_db(point):
    """Headroom of a single point: applicable limit minus recorded ambient."""
    return point["limit_dbuv_m"] - point["ambient_dbuv_m"]


def categorize_point(point, required_headroom_db=DEFAULT_REQUIRED_HEADROOM_DB):
    """Categorize one sweep point by the headroom it leaves."""
    required = _number({"v": required_headroom_db}, "v", "required_headroom_db")
    if required < 0.0:
        raise ValueError("required_headroom_db must be >= 0, got %g" % required)
    headroom = point_headroom_db(point)
    if headroom <= 0.0:
        # Ambient at or above the applicable limit leaves nothing to grade.
        return CATEGORY_EXCEEDANCE
    if at_least(headroom, required):
        return CATEGORY_COMPLIANT
    return CATEGORY_MARGINAL


def identify_narrowband_ambient(points, prominence_db=NARROWBAND_PROMINENCE_DB):
    """Return interior points standing above both neighbours by prominence."""
    prominence = _number({"v": prominence_db}, "v", "prominence_db")
    if prominence <= 0.0:
        raise ValueError("prominence_db must be > 0, got %g" % prominence)
    sweep = validate_sweep(points)
    peaks = []
    for index in range(1, len(sweep) - 1):
        here = sweep[index]["ambient_dbuv_m"]
        left = sweep[index - 1]["ambient_dbuv_m"]
        right = sweep[index + 1]["ambient_dbuv_m"]
        rise = min(here - left, here - right)
        if at_least(rise, prominence):
            peaks.append(
                {
                    "frequency_hz": sweep[index]["frequency_hz"],
                    "ambient_dbuv_m": here,
                    "prominence_db": rise,
                }
            )
    return peaks


def check_band_coverage(points, band_start_hz, band_stop_hz, max_step_ratio=1.5):
    """Report coverage gaps against the declared band and step ratio."""
    start = _number({"v": band_start_hz}, "v", "band_start_hz")
    stop = _number({"v": band_stop_hz}, "v", "band_stop_hz")
    ratio = _number({"v": max_step_ratio}, "v", "max_step_ratio")
    if start <= 0.0:
        raise ValueError("band_start_hz must be > 0, got %g" % start)
    if stop <= start:
        raise ValueError(
            "band_stop_hz (%g) must exceed band_start_hz (%g)" % (stop, start)
        )
    if ratio <= 1.0:
        raise ValueError("max_step_ratio must be > 1.0, got %g" % ratio)
    sweep = validate_sweep(points)
    gaps = []
    if sweep[0]["frequency_hz"] > start and not math.isclose(
        sweep[0]["frequency_hz"], start, rel_tol=1e-12, abs_tol=DB_TOL
    ):
        gaps.append(
            "band start %g Hz not covered; first recorded point at %g Hz"
            % (start, sweep[0]["frequency_hz"])
        )
    if sweep[-1]["frequency_hz"] < stop and not math.isclose(
        sweep[-1]["frequency_hz"], stop, rel_tol=1e-12, abs_tol=DB_TOL
    ):
        gaps.append(
            "band stop %g Hz not covered; last recorded point at %g Hz"
            % (stop, sweep[-1]["frequency_hz"])
        )
    for index in range(1, len(sweep)):
        lower = sweep[index - 1]["frequency_hz"]
        upper = sweep[index]["frequency_hz"]
        step = upper / lower
        if step > ratio and not math.isclose(step, ratio, rel_tol=1e-12, abs_tol=DB_TOL):
            gaps.append(
                "step %g Hz -> %g Hz is a ratio of %.3f, above the declared %.3f"
                % (lower, upper, step, ratio)
            )
    return gaps


def attribute_reading(measured_dbuv_m, ambient_dbuv_m):
    """Attribute a later graded reading against the recorded ambient floor."""
    measured = _number({"v": measured_dbuv_m}, "v", "measured_dbuv_m")
    ambient = _number({"v": ambient_dbuv_m}, "v", "ambient_dbuv_m")
    rise = measured - ambient
    if rise < -DB_TOL:
        raise ValueError(
            "measured level %g dB is below the recorded ambient %g dB; the "
            "baseline and the graded run are inconsistent" % (measured, ambient)
        )
    if at_least(rise, UNIT_DOMINANCE_DB):
        return "unit-dominated"
    if rise <= AMBIENT_LIMITED_DB:
        return "ambient-limited"
    return "indeterminate"


def assess_ambient_radiated_level(
    config,
    points,
    band_start_hz,
    band_stop_hz,
    required_headroom_db=DEFAULT_REQUIRED_HEADROOM_DB,
    max_step_ratio=1.5,
    reference_bandwidth_hz=None,
):
    """Full clause 5.2.2.3 ambient radiated baseline assessment."""
    configuration = validate_ambient_configuration(config, reference_bandwidth_hz)
    sweep = validate_sweep(points)
    graded = []
    counts = dict((category, 0) for category in CATEGORIES)
    for point in sweep:
        category = categorize_point(point, required_headroom_db)
        counts[category] += 1
        graded.append(
            {
                "frequency_hz": point["frequency_hz"],
                "ambient_dbuv_m": point["ambient_dbuv_m"],
                "limit_dbuv_m": point["limit_dbuv_m"],
                "headroom_db": point_headroom_db(point),
                "category": category,
            }
        )
    worst = min(graded, key=lambda g: g["headroom_db"])
    gaps = check_band_coverage(sweep, band_start_hz, band_stop_hz, max_step_ratio)
    peaks = identify_narrowband_ambient(sweep)

    findings = []
    for entry in graded:
        if entry["category"] == CATEGORY_EXCEEDANCE:
            findings.append(
                "ambient exceedance at %g Hz: %.1f dB headroom"
                % (entry["frequency_hz"], entry["headroom_db"])
            )
    findings.extend("coverage gap: %s" % gap for gap in gaps)

    limitations = [
        "marginal headroom %.1f dB at %g Hz"
        % (entry["headroom_db"], entry["frequency_hz"])
        for entry in graded
        if entry["category"] == CATEGORY_MARGINAL
    ]
    limitations.extend(
        "narrowband ambient signal at %g Hz (%.1f dB prominence) must be documented"
        % (peak["frequency_hz"], peak["prominence_db"])
        for peak in peaks
    )

    return {
        "configuration": configuration,
        "points": graded,
        "counts": counts,
        "worst_case": worst,
        "coverage_gaps": gaps,
        "narrowband_ambient": peaks,
        "findings": findings,
        "limitations": limitations,
        "verdict": "usable-baseline" if not findings else "baseline-rejected",
    }
