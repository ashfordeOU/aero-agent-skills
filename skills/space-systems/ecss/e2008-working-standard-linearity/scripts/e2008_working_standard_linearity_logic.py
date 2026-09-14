#!/usr/bin/env python3
"""Linearity of a secondary working standard.

Anchor: ECSS-E-ST-20-08C clause 10.2.2.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not write a linearity method of its own. It sends the
work to the photovoltaic measurement standard it references, so the
device record has to name the referenced method it was measured by: a
sweep with no declared method is a set of numbers, not a linearity
assessment, and cannot be dispositioned.

What the referenced methods have in common is the quantity they produce.
A working standard is used to read an irradiance from a current, so the
property under test is whether the current per unit irradiance is the
same number everywhere on the range the device is used across. That
number is the responsivity, and it is what the assessment works in:

    responsivity = short-circuit current / irradiance

A perfectly linear device gives one responsivity at every point. A real
one is anchored at the reference irradiance, where its calibration value
lives, and every other point is expressed as a fractional deviation from
that anchor. The deviation, not the current, is the measurement.

Two things are checked alongside the deviation band.

The straight-line fit. Fitting current against irradiance by least
squares separates the slope from the intercept. A device with a dark
current or a leakage path reports a current at zero irradiance, and that
offset is a fixed error that grows in relative terms as the light goes
down; it shows up as a rising deviation at the bottom of the range,
which the intercept then names as an offset rather than as a curvature.

The range the points actually span. A device certified only near one sun
says nothing about the low-irradiance end it is later used at, so the
lowest and highest points and the ratio between them are checked against
the range the assessment is supposed to cover.

A sweep in which the current falls as the irradiance rises is reported
separately, because that is not a linearity figure, it is a measurement
that went wrong.

Dispositions are linearity-within-band, refer-for-review and
linearity-out-of-band.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_BAND = "linearity-within-band"
REFER = "refer-for-review"
OUT_OF_BAND = "linearity-out-of-band"
POINT_DISPOSITIONS = (WITHIN_BAND, REFER, OUT_OF_BAND)

_SEVERITY_ORDER = {WITHIN_BAND: 0, REFER: 1, OUT_OF_BAND: 2}

DEVICE_LINEAR = "working-standard-linear"
DEVICE_REFERRED = "working-standard-referred"
DEVICE_NON_LINEAR = "working-standard-non-linear"

_VERDICT_BY_SEVERITY = {
    WITHIN_BAND: DEVICE_LINEAR,
    REFER: DEVICE_REFERRED,
    OUT_OF_BAND: DEVICE_NON_LINEAR,
}

DEFAULT_LINEARITY_CRITERIA = {
    # a sweep needs enough points to show a shape rather than two ends
    "min_points": 6,
    # where the device's calibration value lives
    "reference_irradiance_w_m2": 1000.0,
    # how close to it a point has to sit to anchor the responsivity
    "reference_band_fraction": 0.05,
    # the range the assessment has to cover
    "required_low_irradiance_w_m2": 200.0,
    "required_high_irradiance_w_m2": 1100.0,
    "min_range_ratio": 4.0,
    # how far one point's responsivity may sit from the anchor
    "max_responsivity_deviation_fraction": 0.0050,
    "deviation_review_factor": 2.0,
    # a current reported at zero irradiance, against the reference current
    "max_offset_fraction": 0.0020,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_finite(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_finite(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every figure compared here is a ratio of measured quantities, so a
    point that should sit exactly on a limit can evaluate a few units in
    the last place above it. The limit is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = WITHIN_BAND
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_linearity_criteria(criteria):
    """Check a linearity criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    points = _require_count("criteria min_points", criteria.get("min_points"), minimum=1)
    if points < 3:
        raise ValueError(
            "a straight line through two points is not evidence of linearity; "
            "min_points must be at least three, got %d" % points
        )
    for key in (
        "reference_irradiance_w_m2",
        "required_low_irradiance_w_m2",
        "required_high_irradiance_w_m2",
        "min_range_ratio",
    ):
        _require_positive("criteria %s" % key, criteria.get(key))
    for key in (
        "reference_band_fraction",
        "max_responsivity_deviation_fraction",
        "max_offset_fraction",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction >= 1.0:
            raise ValueError(
                "criteria %s is a share of a measured quantity and a whole "
                "unit of it is not a tolerance, got %r" % (key, fraction)
            )
    factor = _require_positive(
        "criteria deviation_review_factor", criteria.get("deviation_review_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "criteria deviation_review_factor must be at least one; a review "
            "band cannot be tighter than the accept band, got %r" % (factor,)
        )
    if criteria["min_range_ratio"] < 1.0:
        raise ValueError(
            "a range ratio below one means the top of the range is under the "
            "bottom of it, got %r" % (criteria["min_range_ratio"],)
        )
    if not _at_most(
        criteria["required_low_irradiance_w_m2"],
        criteria["required_high_irradiance_w_m2"],
    ):
        raise ValueError(
            "the required low irradiance sits above the required high one: "
            "%r against %r"
            % (
                criteria["required_low_irradiance_w_m2"],
                criteria["required_high_irradiance_w_m2"],
            )
        )
    return criteria


def responsivity_a_per_w_m2(current_a, irradiance_w_m2):
    """Current per unit irradiance: the quantity linearity is judged in."""
    current = _require_positive("short_circuit_current_a", current_a)
    irradiance = _require_positive("irradiance_w_m2", irradiance_w_m2)
    return current / irradiance


def validate_linearity_points(points, criteria=DEFAULT_LINEARITY_CRITERIA):
    """Check a sweep and return it in irradiance order with responsivities."""
    validate_linearity_criteria(criteria)
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a list, got %r" % (points,))
    if len(points) < criteria["min_points"]:
        raise ValueError(
            "a sweep of %d points cannot carry the assessment; at least %d are "
            "needed" % (len(points), criteria["min_points"])
        )
    resolved = []
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("each point must be a mapping, got %r" % (point,))
        irradiance = _require_positive(
            "irradiance_w_m2", point.get("irradiance_w_m2")
        )
        current = _require_positive(
            "short_circuit_current_a", point.get("short_circuit_current_a")
        )
        resolved.append(
            {
                "irradiance_w_m2": irradiance,
                "short_circuit_current_a": current,
                "responsivity_a_per_w_m2": responsivity_a_per_w_m2(
                    current, irradiance
                ),
            }
        )
    resolved.sort(key=lambda entry: entry["irradiance_w_m2"])
    for earlier, later in zip(resolved, resolved[1:]):
        if math.isclose(
            earlier["irradiance_w_m2"],
            later["irradiance_w_m2"],
            rel_tol=_REL_TOL,
            abs_tol=_ABS_TOL,
        ):
            raise ValueError(
                "two points share the irradiance %.4f W/m2; a repeat reading "
                "is not a second point on the sweep"
                % (earlier["irradiance_w_m2"],)
            )
    return resolved


def reference_responsivity(points, criteria=DEFAULT_LINEARITY_CRITERIA):
    """Anchor responsivity, taken from the points at the reference level.

    The anchor is where the device's calibration value lives, so every
    deviation is reported relative to the condition the device is
    actually certified at rather than to the average of the sweep.
    """
    resolved = validate_linearity_points(points, criteria)
    reference = criteria["reference_irradiance_w_m2"]
    band = criteria["reference_band_fraction"]
    low = reference * (1.0 - band)
    high = reference * (1.0 + band)
    inside = [
        entry
        for entry in resolved
        if _at_most(low, entry["irradiance_w_m2"])
        and _at_most(entry["irradiance_w_m2"], high)
    ]
    if not inside:
        raise ValueError(
            "no point sits within %.1f%% of the %.1f W/m2 reference level, so "
            "the sweep has nothing to anchor the responsivity on"
            % (band * 100.0, reference)
        )
    return sum(entry["responsivity_a_per_w_m2"] for entry in inside) / float(
        len(inside)
    )


def least_squares_line(points):
    """Slope and intercept of a straight line through (x, y) points."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("a line needs at least two points, got %r" % (points,))
    xs = [_require_finite("x", x) for x, _ in points]
    ys = [_require_finite("y", y) for _, y in points]
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0.0:
        raise ValueError("every point shares the same x value, so no line is defined")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, mean_y - slope * mean_x


def deviation_profile(points, criteria=DEFAULT_LINEARITY_CRITERIA):
    """Fractional departure of each point's responsivity from the anchor."""
    resolved = validate_linearity_points(points, criteria)
    anchor = reference_responsivity(points, criteria)
    limit = criteria["max_responsivity_deviation_fraction"]
    review_limit = limit * criteria["deviation_review_factor"]
    profile = []
    for entry in resolved:
        deviation = entry["responsivity_a_per_w_m2"] / anchor - 1.0
        magnitude = abs(deviation)
        if _at_most(magnitude, limit):
            disposition = WITHIN_BAND
        elif _at_most(magnitude, review_limit):
            disposition = REFER
        else:
            disposition = OUT_OF_BAND
        profile.append(
            {
                "irradiance_w_m2": entry["irradiance_w_m2"],
                "short_circuit_current_a": entry["short_circuit_current_a"],
                "responsivity_a_per_w_m2": entry["responsivity_a_per_w_m2"],
                "deviation_fraction": deviation,
                "deviation_magnitude": magnitude,
                "disposition": disposition,
            }
        )
    return profile


def range_coverage(points, criteria=DEFAULT_LINEARITY_CRITERIA):
    """What the sweep actually spans against what it is meant to cover."""
    resolved = validate_linearity_points(points, criteria)
    lowest = resolved[0]["irradiance_w_m2"]
    highest = resolved[-1]["irradiance_w_m2"]
    gaps = []
    if not _at_most(lowest, criteria["required_low_irradiance_w_m2"]):
        gaps.append(
            "the sweep starts at %.1f W/m2 and says nothing about the %.1f "
            "W/m2 end the device is used at"
            % (lowest, criteria["required_low_irradiance_w_m2"])
        )
    if not _at_most(criteria["required_high_irradiance_w_m2"], highest):
        gaps.append(
            "the sweep stops at %.1f W/m2, short of the %.1f W/m2 it has to "
            "cover" % (highest, criteria["required_high_irradiance_w_m2"])
        )
    ratio = highest / lowest
    if not _at_most(criteria["min_range_ratio"], ratio):
        gaps.append(
            "the sweep spans a ratio of %.3f, under the %.3f the assessment "
            "needs to see a shape" % (ratio, criteria["min_range_ratio"])
        )
    return {
        "lowest_irradiance_w_m2": lowest,
        "highest_irradiance_w_m2": highest,
        "range_ratio": ratio,
        "covers_required_range": not gaps,
        "gaps": gaps,
    }


def monotonicity_findings(points, criteria=DEFAULT_LINEARITY_CRITERIA):
    """Steps where the current fell although the irradiance rose."""
    resolved = validate_linearity_points(points, criteria)
    findings = []
    for earlier, later in zip(resolved, resolved[1:]):
        if later["short_circuit_current_a"] < earlier["short_circuit_current_a"]:
            findings.append(
                "current fell from %.6f A to %.6f A while irradiance rose from "
                "%.1f to %.1f W/m2; that is not a linearity figure, it is a "
                "reading that went wrong"
                % (
                    earlier["short_circuit_current_a"],
                    later["short_circuit_current_a"],
                    earlier["irradiance_w_m2"],
                    later["irradiance_w_m2"],
                )
            )
    return findings


def assess_working_standard_linearity(device, criteria=DEFAULT_LINEARITY_CRITERIA):
    """Clause 10.2.2.3.3 linearity assessment of one working standard."""
    validate_linearity_criteria(criteria)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    device_id = _require_identifier("device_id", device.get("device_id"))
    method_reference = _require_identifier(
        "method_reference", device.get("method_reference")
    )
    points = device.get("points")
    resolved = validate_linearity_points(points, criteria)
    anchor = reference_responsivity(points, criteria)
    profile = deviation_profile(points, criteria)
    coverage = range_coverage(points, criteria)

    findings = []
    verdict = _worst([entry["disposition"] for entry in profile])
    worst_point = max(profile, key=lambda entry: entry["deviation_magnitude"])
    if worst_point["disposition"] != WITHIN_BAND:
        findings.append(
            "responsivity at %.1f W/m2 sits %.5f from the reference anchor, "
            "past the %.5f allowance"
            % (
                worst_point["irradiance_w_m2"],
                worst_point["deviation_magnitude"],
                criteria["max_responsivity_deviation_fraction"],
            )
        )

    slope, intercept = least_squares_line(
        [
            (entry["irradiance_w_m2"], entry["short_circuit_current_a"])
            for entry in resolved
        ]
    )
    reference_current = anchor * criteria["reference_irradiance_w_m2"]
    offset_fraction = abs(intercept) / reference_current
    if not _at_most(offset_fraction, criteria["max_offset_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "the fit reports %.6f A at zero irradiance, %.5f of the reference "
            "current, past the %.5f allowance; a fixed offset is a dark or "
            "leakage current, not a curvature, and it grows in relative terms "
            "as the light goes down"
            % (intercept, offset_fraction, criteria["max_offset_fraction"])
        )

    for gap in coverage["gaps"]:
        verdict = _worst((verdict, REFER))
        findings.append(gap)

    for finding in monotonicity_findings(points, criteria):
        verdict = _worst((verdict, REFER))
        findings.append(finding)

    return {
        "device_id": device_id,
        "method_reference": method_reference,
        "point_count": len(resolved),
        "reference_responsivity_a_per_w_m2": anchor,
        "reference_current_a": reference_current,
        "fitted_slope_a_per_w_m2": slope,
        "fitted_intercept_a": intercept,
        "offset_fraction": offset_fraction,
        "profile": profile,
        "worst_deviation_fraction": worst_point["deviation_fraction"],
        "worst_deviation_magnitude": worst_point["deviation_magnitude"],
        "worst_deviation_irradiance_w_m2": worst_point["irradiance_w_m2"],
        "coverage": coverage,
        "out_of_band_irradiances_w_m2": [
            entry["irradiance_w_m2"]
            for entry in profile
            if entry["disposition"] != WITHIN_BAND
        ],
        "verdict": _VERDICT_BY_SEVERITY[verdict],
        "disposition": verdict,
        "findings": findings,
    }
