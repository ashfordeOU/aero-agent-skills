#!/usr/bin/env python3
"""Reduction of a coverglass transmission-into-air spectrophotometer scan.

Anchor: ECSS-E-ST-20-08C clause 8.7.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The measurement is narrow and the reduction is where campaigns lose it.
A spectrophotometer is pointed through the coverglass and the light that
comes out the far side into air is recorded against wavelength across the
band the project has specified. Four things follow.

The transmission is into air, not into the cell. The far side of the
glass in the instrument is an air interface, so the scan carries the
second Fresnel reflection at the rear face. The same coverglass bonded to
a cell with an index-matched adhesive does not have that interface, and
the two numbers are not interchangeable; the band figure that closes this
clause is the into-air one, and using a bonded-stack figure in its place
is answering a different question.

A scan is only evidence over the wavelengths it actually reaches. A band
figure quoted from a scan that stops short of the specified band is an
extrapolation wearing the band's name, so the coverage check runs before
any integral is taken.

Sampling interval matters as much as coverage. A coverglass with a sharp
cut-on can be sampled so coarsely that the edge falls between two points
and the trapezoid quietly walks straight through it, so the largest gap
between adjacent samples is compared against the specified interval.

The band figure is an integral, not a mean of the recorded points. The
sample points are rarely evenly spaced and the band edges rarely fall on
a sample, so the average is taken as a trapezoidal integral over the band
with interpolated endpoints and divided by the band width. Averaging the
raw ordinates instead lets a densely sampled region carry the figure.

A solar-weighted figure is the same integral with the spectral irradiance
as the weight, and it is the figure that matters for array power. It is
reported when a weighting is supplied and never invented when it is not.

The band, the interval and the required minimum below are declared
policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BASELINE_NOT_REFERENCED = "baseline-calibration-not-referenced"
BAND_NOT_COVERED = "specified-band-not-covered"
SAMPLING_TOO_COARSE = "sampling-interval-too-coarse"
AVERAGE_BELOW_REQUIREMENT = "band-average-below-requirement"
AVERAGE_MEETS_REQUIREMENT = "band-average-meets-requirement"

DEFAULT_SCAN_POLICY = {
    "band_start_nm": 350.0,
    "band_end_nm": 1800.0,
    "max_sample_interval_nm": 10.0,
    "cut_on_transmittance": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-18


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_scan_policy(policy):
    """Check a scan policy names a real band and a usable interval."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    start = _require_positive("band_start_nm", policy.get("band_start_nm"))
    end = _require_positive("band_end_nm", policy.get("band_end_nm"))
    if not end > start:
        raise ValueError(
            "band_end_nm %g must be above band_start_nm %g; a band of zero "
            "width has no average" % (end, start)
        )
    interval = _require_positive(
        "max_sample_interval_nm", policy.get("max_sample_interval_nm")
    )
    if interval > (end - start):
        raise ValueError(
            "max_sample_interval_nm %g is wider than the %g nm band, so no "
            "scan could ever be too coarse" % (interval, end - start)
        )
    threshold = _require_number(
        "cut_on_transmittance", policy.get("cut_on_transmittance")
    )
    if not 0.0 < threshold < 1.0:
        raise ValueError(
            "cut_on_transmittance %g must sit strictly between zero and one"
            % threshold
        )
    return policy


def _point(entry, index):
    if isinstance(entry, dict):
        wavelength = entry.get("wavelength_nm")
        transmittance = entry.get("transmittance")
    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
        wavelength, transmittance = entry
    else:
        raise ValueError(
            "scan point %d must be a (wavelength_nm, transmittance) pair or a "
            "mapping, got %r" % (index, entry)
        )
    wavelength = _require_positive("wavelength_nm at point %d" % index, wavelength)
    transmittance = _require_number("transmittance at point %d" % index, transmittance)
    if transmittance < 0.0 or transmittance > 1.0:
        raise ValueError(
            "transmittance %g at point %d is outside zero to one; a "
            "transmittance is a fraction of the incident beam"
            % (transmittance, index)
        )
    return wavelength, transmittance


def validate_scan(points):
    """Check a spectrophotometer scan is orderly and physically readable."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("scan must be a sequence of points")
    if len(points) < 2:
        raise ValueError(
            "a scan of %d point(s) spans no wavelength interval and cannot be "
            "integrated" % len(points)
        )
    reduced = []
    previous = None
    for index, entry in enumerate(points, start=1):
        wavelength, transmittance = _point(entry, index)
        if previous is not None and not wavelength > previous:
            raise ValueError(
                "scan wavelengths must strictly ascend; point %d at %g nm does "
                "not follow %g nm" % (index, wavelength, previous)
            )
        previous = wavelength
        reduced.append((wavelength, transmittance))
    return tuple(reduced)


def scan_span_nm(points):
    """The first and last wavelength the scan actually reaches."""
    reduced = validate_scan(points)
    return reduced[0][0], reduced[-1][0]


def covers_band(points, band_start_nm, band_end_nm):
    """True when the scan reaches both edges of the specified band."""
    start = _require_positive("band_start_nm", band_start_nm)
    end = _require_positive("band_end_nm", band_end_nm)
    if not end > start:
        raise ValueError("band_end_nm must be above band_start_nm")
    first, last = scan_span_nm(points)
    return _at_most(first, start) and _at_least(last, end)


def max_sample_interval_nm(points):
    """The widest gap between adjacent samples in the scan."""
    reduced = validate_scan(points)
    return max(
        reduced[i + 1][0] - reduced[i][0] for i in range(len(reduced) - 1)
    )


def interpolate_transmittance(points, wavelength_nm):
    """Transmittance at one wavelength, linear between the bracketing samples."""
    reduced = validate_scan(points)
    target = _require_positive("wavelength_nm", wavelength_nm)
    first, last = reduced[0][0], reduced[-1][0]
    if target < first or target > last:
        raise ValueError(
            "%g nm lies outside the %g to %g nm scan; the scan is evidence "
            "only where it was taken" % (target, first, last)
        )
    for index in range(len(reduced) - 1):
        low_w, low_t = reduced[index]
        high_w, high_t = reduced[index + 1]
        if low_w <= target <= high_w:
            width = high_w - low_w
            if width == 0.0:
                return low_t
            return low_t + (high_t - low_t) * (target - low_w) / width
    return reduced[-1][1]


def _band_nodes(points, band_start_nm, band_end_nm, extra=()):
    reduced = validate_scan(points)
    nodes = {band_start_nm, band_end_nm}
    for wavelength, _transmittance in reduced:
        if band_start_nm < wavelength < band_end_nm:
            nodes.add(wavelength)
    for wavelength in extra:
        if band_start_nm < wavelength < band_end_nm:
            nodes.add(wavelength)
    return sorted(nodes)


def band_average_transmittance(points, band_start_nm, band_end_nm):
    """Trapezoidal band average, with the band edges interpolated onto the scan."""
    start = _require_positive("band_start_nm", band_start_nm)
    end = _require_positive("band_end_nm", band_end_nm)
    if not end > start:
        raise ValueError("band_end_nm must be above band_start_nm")
    if not covers_band(points, start, end):
        first, last = scan_span_nm(points)
        raise ValueError(
            "the scan spans %g to %g nm and cannot produce a %g to %g nm band "
            "average; the missing wavelengths would be extrapolation"
            % (first, last, start, end)
        )
    nodes = _band_nodes(points, start, end)
    integral = 0.0
    for index in range(len(nodes) - 1):
        low, high = nodes[index], nodes[index + 1]
        low_t = interpolate_transmittance(points, low)
        high_t = interpolate_transmittance(points, high)
        integral += 0.5 * (low_t + high_t) * (high - low)
    return integral / (end - start)


def validate_weighting(weights):
    """Check a spectral irradiance weighting is orderly and non-negative."""
    if not isinstance(weights, (list, tuple)):
        raise ValueError("weighting must be a sequence of points")
    if len(weights) < 2:
        raise ValueError(
            "a weighting of %d point(s) spans no wavelength interval"
            % len(weights)
        )
    reduced = []
    previous = None
    total = 0.0
    for index, entry in enumerate(weights, start=1):
        if isinstance(entry, dict):
            wavelength = entry.get("wavelength_nm")
            value = entry.get("spectral_irradiance")
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            wavelength, value = entry
        else:
            raise ValueError(
                "weighting point %d must be a (wavelength_nm, "
                "spectral_irradiance) pair or a mapping, got %r" % (index, entry)
            )
        wavelength = _require_positive(
            "weighting wavelength_nm at point %d" % index, wavelength
        )
        value = _require_number(
            "spectral_irradiance at point %d" % index, value
        )
        if value < 0.0:
            raise ValueError(
                "spectral_irradiance %g at point %d is negative" % (value, index)
            )
        if previous is not None and not wavelength > previous:
            raise ValueError(
                "weighting wavelengths must strictly ascend; point %d at %g nm "
                "does not follow %g nm" % (index, wavelength, previous)
            )
        previous = wavelength
        total += value
        reduced.append((wavelength, value))
    if total <= 0.0:
        raise ValueError(
            "the weighting is zero everywhere, so it selects no part of the band"
        )
    return tuple(reduced)


def _interpolate_weight(weights, wavelength_nm):
    reduced = validate_weighting(weights)
    first, last = reduced[0][0], reduced[-1][0]
    if wavelength_nm < first or wavelength_nm > last:
        raise ValueError(
            "%g nm lies outside the %g to %g nm weighting" % (wavelength_nm, first, last)
        )
    for index in range(len(reduced) - 1):
        low_w, low_v = reduced[index]
        high_w, high_v = reduced[index + 1]
        if low_w <= wavelength_nm <= high_w:
            width = high_w - low_w
            if width == 0.0:
                return low_v
            return low_v + (high_v - low_v) * (wavelength_nm - low_w) / width
    return reduced[-1][1]


def weighted_band_average_transmittance(
    points, weights, band_start_nm, band_end_nm
):
    """Irradiance-weighted band average: the figure that carries array power."""
    start = _require_positive("band_start_nm", band_start_nm)
    end = _require_positive("band_end_nm", band_end_nm)
    if not end > start:
        raise ValueError("band_end_nm must be above band_start_nm")
    if not covers_band(points, start, end):
        raise ValueError(
            "the scan does not cover the %g to %g nm band" % (start, end)
        )
    weight_points = validate_weighting(weights)
    first, last = weight_points[0][0], weight_points[-1][0]
    if not (_at_most(first, start) and _at_least(last, end)):
        raise ValueError(
            "the weighting spans %g to %g nm and does not cover the %g to %g nm "
            "band" % (first, last, start, end)
        )
    nodes = _band_nodes(
        points, start, end, extra=[w for w, _v in weight_points]
    )
    numerator = 0.0
    denominator = 0.0
    for index in range(len(nodes) - 1):
        low, high = nodes[index], nodes[index + 1]
        width = high - low
        low_t = interpolate_transmittance(points, low)
        high_t = interpolate_transmittance(points, high)
        low_w = _interpolate_weight(weights, low)
        high_w = _interpolate_weight(weights, high)
        numerator += 0.5 * (low_t * low_w + high_t * high_w) * width
        denominator += 0.5 * (low_w + high_w) * width
    if denominator <= 0.0:
        raise ValueError(
            "the weighting integrates to zero across the band, so no weighted "
            "average exists"
        )
    return numerator / denominator


def cut_on_wavelength_nm(points, threshold):
    """Wavelength where transmission first rises through the threshold."""
    reduced = validate_scan(points)
    level = _require_number("threshold", threshold)
    if not 0.0 < level < 1.0:
        raise ValueError(
            "threshold %g must sit strictly between zero and one" % level
        )
    if _at_least(reduced[0][1], level):
        raise ValueError(
            "the scan already reads %g at its first point, so the cut-on lies "
            "below %g nm and was not measured" % (reduced[0][1], reduced[0][0])
        )
    for index in range(len(reduced) - 1):
        low_w, low_t = reduced[index]
        high_w, high_t = reduced[index + 1]
        if low_t < level and _at_least(high_t, level):
            span = high_t - low_t
            if span == 0.0:
                return high_w
            return low_w + (high_w - low_w) * (level - low_t) / span
    return None


def meets_requirement(average, required_minimum):
    """True when the band average reaches the requirement; a tie is admissible."""
    value = _require_number("average", average)
    minimum = _require_number("required_minimum", required_minimum)
    if not 0.0 <= value <= 1.0:
        raise ValueError("average %g is outside zero to one" % value)
    if not 0.0 < minimum <= 1.0:
        raise ValueError(
            "required_minimum %g must sit above zero and at or below one"
            % minimum
        )
    return _at_least(value, minimum)


def assess_transmission_into_air(case, policy=DEFAULT_SCAN_POLICY):
    """Full clause 8.7.2 reduction and verdict for one coverglass scan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_scan_policy(policy)

    start = float(policy["band_start_nm"])
    end = float(policy["band_end_nm"])
    findings = []
    advisories = []
    result = {
        "band_start_nm": start,
        "band_end_nm": end,
        "baseline_reference": None,
        "scan_first_nm": None,
        "scan_last_nm": None,
        "sample_count": None,
        "max_sample_interval_nm": None,
        "band_average_transmittance": None,
        "weighted_band_average_transmittance": None,
        "cut_on_wavelength_nm": None,
        "required_minimum": None,
        "margin": None,
        "findings": findings,
        "advisories": advisories,
    }

    points = validate_scan(case.get("scan"))
    result["sample_count"] = len(points)
    result["scan_first_nm"] = points[0][0]
    result["scan_last_nm"] = points[-1][0]
    result["max_sample_interval_nm"] = max_sample_interval_nm(points)

    baseline = case.get("baseline_reference")
    reference = _require_label("baseline_reference", baseline or "")
    result["baseline_reference"] = reference or None
    if not reference:
        findings.append(
            "the scan carries no baseline calibration reference; an "
            "uncalibrated spectrophotometer trace is not a transmission "
            "measurement of the coverglass"
        )
        result["verdict"] = BASELINE_NOT_REFERENCED
        return result

    if not covers_band(points, start, end):
        findings.append(
            "the scan spans %g to %g nm and the specified band is %g to %g nm; "
            "a band average taken from it would be extrapolation"
            % (points[0][0], points[-1][0], start, end)
        )
        result["verdict"] = BAND_NOT_COVERED
        return result

    interval_limit = float(policy["max_sample_interval_nm"])
    if not _at_most(result["max_sample_interval_nm"], interval_limit):
        findings.append(
            "the widest sample gap is %g nm against a specified %g nm "
            "interval; a cut-on edge can fall between two points and the "
            "trapezoid walks straight through it"
            % (result["max_sample_interval_nm"], interval_limit)
        )
        result["verdict"] = SAMPLING_TOO_COARSE
        return result

    average = band_average_transmittance(points, start, end)
    result["band_average_transmittance"] = average

    weights = case.get("spectral_irradiance_weighting")
    if weights is not None:
        result["weighted_band_average_transmittance"] = (
            weighted_band_average_transmittance(points, weights, start, end)
        )

    try:
        result["cut_on_wavelength_nm"] = cut_on_wavelength_nm(
            points, float(policy["cut_on_transmittance"])
        )
    except ValueError:
        advisories.append(
            "the scan already transmits above the cut-on threshold at its "
            "first point, so the cut-on edge lies below the scanned band and "
            "is not evidenced here"
        )

    required = case.get("required_minimum_transmittance")
    if required is None:
        advisories.append(
            "no minimum transmission is declared for this coverglass, so the "
            "band average is reported without a verdict against a requirement"
        )
        result["verdict"] = AVERAGE_MEETS_REQUIREMENT
        return result

    minimum = _require_number("required_minimum_transmittance", required)
    result["required_minimum"] = minimum
    result["margin"] = average - minimum
    if meets_requirement(average, minimum):
        result["verdict"] = AVERAGE_MEETS_REQUIREMENT
        return result

    findings.append(
        "the %g to %g nm into-air band average is %.4f against a required "
        "minimum of %.4f, short by %.4f"
        % (start, end, average, minimum, minimum - average)
    )
    result["verdict"] = AVERAGE_BELOW_REQUIREMENT
    return result
