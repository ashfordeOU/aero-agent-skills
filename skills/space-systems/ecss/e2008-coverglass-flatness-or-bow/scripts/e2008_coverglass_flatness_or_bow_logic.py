#!/usr/bin/env python3
"""Maximum deflection of a coverglass resting on an optically flat reference.

Anchor: ECSS-E-ST-20-08C clause 8.7.8. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The measurement is deliberately simple: lay the coverglass on a
reference flat, leave it alone, and record how far the glass departs
from that surface. Everything that makes the figure defensible sits
around that simplicity rather than in it.

The article is an unclamped thin plate, so the moment it is held down
the deflection being measured is the fixture's and not the glass's. The
reference has to be flat by a margin against the thing it is measuring,
and the probe or the fringe count has to resolve the departure by a
margin too, or the reported number is mostly instrument. And the grid
has to reach the corners: a bow is largest at the rim, so a grid that
samples the middle of a coverglass returns a small number about a real
article.

Two shapes hide behind one figure. A bow is a single-sign departure --
the glass is dished or domed, and every point sits on the same side of
the best-fit reference plane. Waviness alternates. Both can produce the
same peak-to-valley, and they behave differently under bonding, so the
reduction separates them rather than reporting only the maximum.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# A recorded deflection has to stand this far above what the probe can
# resolve before it is a measurement rather than an instrument reading.
MIN_RESOLUTION_RATIO = 10.0

# The reference flat's own departure has to be this much smaller than the
# article's before it can serve as the datum.
MIN_REFERENCE_FLAT_RATIO = 4.0

# Fewest grid points a departure map can be reduced from.
MIN_GRID_POINTS = 9

# Share of the article span the grid's bounding box has to reach on both
# axes, since the bow is largest at the rim.
MIN_SPAN_COVERAGE = 0.8

# Steps under this share of the residual peak-to-valley are noise and take
# no part in the shape decision.
SHAPE_NOISE_SHARE = 0.1

# Residual spread under this is arithmetic rounding rather than a shape.
SHAPE_ABSOLUTE_NOISE_UM = 1e-9

SHAPE_BOW = "single-sign-bow"
SHAPE_WAVINESS = "mixed-sign-waviness"
SHAPE_WITHIN_NOISE = "departure-within-noise"

FLATNESS_ACCEPTED = "coverglass-flatness-accepted"
FLATNESS_NOT_ACCEPTED = "coverglass-flatness-not-accepted"

REQUIRED_EVIDENCE = (
    "deflection_limit_um",
    "grid_points",
    "instrument_resolution_um",
    "reference_flatness_um",
    "specimen_span_mm",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Heights arrive in micrometres, spans in millimetres, and a fringe
    count turns into a height through a wavelength, so a value that
    should land on a limit can miss it by a few units in the last place.
    The limit is never relaxed; only the comparison tolerates the
    representation error, which is why no caller uses a bare >= on a
    derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def fringe_deflection_um(fringe_count, wavelength_nm):
    """Gap height an interference fringe count over the reference flat means.

    In reflected light each whole fringe is half a wavelength of gap, so
    a count is a height once the illumination wavelength is stated.
    """
    count = _require_non_negative("fringe_count", fringe_count)
    wavelength = _require_positive("wavelength_nm", wavelength_nm)
    return count * wavelength / 2000.0


def normalized_points(grid_points):
    """Validate a departure map and return it as plain (x, y, z) triples."""
    if not isinstance(grid_points, (list, tuple)) or not grid_points:
        raise ValueError(
            "grid_points must be a non-empty sequence, got %r" % (grid_points,)
        )
    cleaned = []
    for index, point in enumerate(grid_points):
        if isinstance(point, dict):
            x = point.get("x_mm")
            y = point.get("y_mm")
            z = point.get("height_um")
        elif isinstance(point, (list, tuple)) and len(point) == 3:
            x, y, z = point
        else:
            raise ValueError(
                "grid point %d must be a mapping or an (x, y, z) triple, got %r"
                % (index, point)
            )
        cleaned.append(
            (
                _require_number("grid point %d x_mm" % index, x),
                _require_number("grid point %d y_mm" % index, y),
                _require_non_negative("grid point %d height_um" % index, z),
            )
        )
    return tuple(cleaned)


def grid_span_mm(points):
    """Extent of the measured grid on each axis."""
    cleaned = normalized_points(points)
    xs = [point[0] for point in cleaned]
    ys = [point[1] for point in cleaned]
    return (max(xs) - min(xs), max(ys) - min(ys))


def grid_reaches_the_rim(points, specimen_span_mm):
    """Whether the grid's bounding box reaches far enough across the article."""
    span = _require_positive("specimen_span_mm", specimen_span_mm)
    x_span, y_span = grid_span_mm(points)
    return _at_least(x_span / span, MIN_SPAN_COVERAGE) and _at_least(
        y_span / span, MIN_SPAN_COVERAGE
    )


def maximum_deflection_um(points):
    """Largest gap between the glass and the reference flat it rests on."""
    cleaned = normalized_points(points)
    return max(point[2] for point in cleaned)


def peak_to_valley_um(points):
    """Spread between the highest and the lowest measured gap."""
    cleaned = normalized_points(points)
    heights = [point[2] for point in cleaned]
    return max(heights) - min(heights)


def best_fit_plane(points):
    """Least-squares plane z = a x + b y + c through the departure map.

    Removing this plane takes out the tilt of the article on the datum,
    which is a setup artefact, and leaves the shape of the glass itself.
    """
    cleaned = normalized_points(points)
    if len(cleaned) < 3:
        raise ValueError(
            "a plane needs at least three grid points, got %d" % len(cleaned)
        )
    n = float(len(cleaned))
    sxx = sxy = sx = syy = sy = sxz = syz = sz = 0.0
    for x, y, z in cleaned:
        sxx += x * x
        sxy += x * y
        sx += x
        syy += y * y
        sy += y
        sxz += x * z
        syz += y * z
        sz += z
    det = (
        sxx * (syy * n - sy * sy)
        - sxy * (sxy * n - sy * sx)
        + sx * (sxy * sy - syy * sx)
    )
    scale = max(abs(sxx), abs(syy), abs(sxy), abs(sx), abs(sy), n, 1.0)
    if abs(det) <= 1e-12 * scale ** 3:
        raise ValueError(
            "the grid points are collinear, so no plane is determined by them"
        )
    det_a = (
        sxz * (syy * n - sy * sy)
        - sxy * (syz * n - sy * sz)
        + sx * (syz * sy - syy * sz)
    )
    det_b = (
        sxx * (syz * n - sz * sy)
        - sxz * (sxy * n - sy * sx)
        + sx * (sxy * sz - syz * sx)
    )
    det_c = (
        sxx * (syy * sz - syz * sy)
        - sxy * (sxy * sz - syz * sx)
        + sxz * (sxy * sy - syy * sx)
    )
    return (det_a / det, det_b / det, det_c / det)


def plane_residuals_um(points, plane=None):
    """Departure of each grid point from the best-fit plane."""
    cleaned = normalized_points(points)
    a, b, c = best_fit_plane(cleaned) if plane is None else plane
    return tuple(z - (a * x + b * y + c) for x, y, z in cleaned)


def departure_shape(grid_points):
    """Whether the departure is a bow or alternating waviness.

    Removing the best-fit plane puts a dished or domed article on both
    sides of zero, so the sign of a residual says nothing on its own.
    What separates the two shapes is the radial profile: a bow rises or
    falls once as the radius grows out from the grid centroid, while
    waviness turns back on itself. Steps smaller than a share of the
    residual spread are noise and are stepped over rather than counted.
    """
    cleaned = normalized_points(grid_points)
    if len(cleaned) < 3:
        raise ValueError(
            "a departure shape needs at least three grid points, got %d"
            % len(cleaned)
        )
    residuals = plane_residuals_um(cleaned)
    spread = max(residuals) - min(residuals)
    if spread <= SHAPE_ABSOLUTE_NOISE_UM:
        return SHAPE_WITHIN_NOISE
    floor = SHAPE_NOISE_SHARE * spread
    centre_x = sum(point[0] for point in cleaned) / len(cleaned)
    centre_y = sum(point[1] for point in cleaned) / len(cleaned)
    profile = sorted(
        (math.hypot(point[0] - centre_x, point[1] - centre_y), residual)
        for point, residual in zip(cleaned, residuals)
    )
    direction = 0
    turns = 0
    for (_, lower), (_, upper) in zip(profile, profile[1:]):
        step = upper - lower
        if abs(step) <= floor:
            continue
        sign = 1 if step > 0.0 else -1
        if direction != 0 and sign != direction:
            turns += 1
        direction = sign
    if direction == 0:
        return SHAPE_WITHIN_NOISE
    return SHAPE_BOW if turns == 0 else SHAPE_WAVINESS


def deflection_per_span(deflection_um, specimen_span_mm):
    """Deflection normalised over the span, in micrometres per millimetre."""
    deflection = _require_non_negative("deflection_um", deflection_um)
    span = _require_positive("specimen_span_mm", specimen_span_mm)
    return deflection / span


def resolution_adequate(deflection_um, instrument_resolution_um):
    """Whether the probe resolves the departure by the required margin."""
    deflection = _require_non_negative("deflection_um", deflection_um)
    resolution = _require_positive("instrument_resolution_um", instrument_resolution_um)
    return _at_least(deflection / resolution, MIN_RESOLUTION_RATIO)


def reference_flat_adequate(deflection_um, reference_flatness_um):
    """Whether the datum is flat enough to serve as the datum."""
    deflection = _require_non_negative("deflection_um", deflection_um)
    reference = _require_positive("reference_flatness_um", reference_flatness_um)
    return _at_least(deflection / reference, MIN_REFERENCE_FLAT_RATIO)


def missing_evidence(case):
    """Required inputs the flatness record has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(name for name in REQUIRED_EVIDENCE if case.get(name) is None)


def assess_flatness(case):
    """Full clause 8.7.8 judgement of one coverglass flatness record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    absent = missing_evidence(case)
    if absent:
        raise ValueError(
            "coverglass flatness record is missing required evidence: %s"
            % ", ".join(absent)
        )

    points = normalized_points(case.get("grid_points"))
    span = _require_positive("specimen_span_mm", case.get("specimen_span_mm"))
    limit = _require_positive("deflection_limit_um", case.get("deflection_limit_um"))
    resolution = _require_positive(
        "instrument_resolution_um", case.get("instrument_resolution_um")
    )
    reference = _require_positive(
        "reference_flatness_um", case.get("reference_flatness_um")
    )

    findings = []

    if case.get("clamped") is True:
        findings.append(
            "the coverglass was held against the reference flat; a clamped thin "
            "plate reports the fixture's deflection rather than its own"
        )

    if len(points) < MIN_GRID_POINTS:
        findings.append(
            "the departure map carries %d points, below the %d a coverglass "
            "surface can be reduced from" % (len(points), MIN_GRID_POINTS)
        )

    if not grid_reaches_the_rim(points, span):
        findings.append(
            "the grid's bounding box does not reach %.0f%% of the article span on "
            "both axes; a bow is largest at the rim and this grid never went there"
            % (MIN_SPAN_COVERAGE * 100.0)
        )

    deflection = maximum_deflection_um(points)
    spread = peak_to_valley_um(points)

    if not resolution_adequate(deflection, resolution):
        findings.append(
            "the %.3f um departure is only %.1f times the %.3f um probe "
            "resolution, below the %.0f the figure needs to be a measurement"
            % (deflection, deflection / resolution, resolution, MIN_RESOLUTION_RATIO)
        )

    if not reference_flat_adequate(deflection, reference):
        findings.append(
            "the reference flat departs %.3f um against an article departure of "
            "%.3f um; the datum is not flat enough to be the datum"
            % (reference, deflection)
        )

    if not _at_most(deflection, limit):
        findings.append(
            "maximum deflection %.3f um exceeds the %.3f um the drawing allows"
            % (deflection, limit)
        )

    if len(points) >= 3:
        residuals = plane_residuals_um(points)
        shape = departure_shape(points)
        residual_peak_to_valley = max(residuals) - min(residuals)
    else:
        shape = SHAPE_WITHIN_NOISE
        residual_peak_to_valley = 0.0

    accepted = not findings
    return {
        "maximum_deflection_um": deflection,
        "peak_to_valley_um": spread,
        "deflection_per_span_um_per_mm": deflection_per_span(deflection, span),
        "departure_shape": shape,
        "residual_peak_to_valley_um": residual_peak_to_valley,
        "grid_point_count": len(points),
        "deflection_limit_um": limit,
        "verdict": FLATNESS_ACCEPTED if accepted else FLATNESS_NOT_ACCEPTED,
        "accepted": accepted,
        "findings": findings,
    }
