#!/usr/bin/env python3
"""Flatness of an unmounted bare solar cell across its full face.

Anchor: ECSS-E-ST-20-08C clause 7.5.19. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell is a thin brittle wafer that has to sit down flat on a
substrate and stay in contact with it. The question the clause asks is
how far the free, unmounted cell surface departs from a plane, measured
over the whole face rather than over whichever part of it the fixture
made convenient to probe. Three things have to happen before a height
grid becomes a flatness number:

    coverage   a grid that samples the middle of the cell has measured
               the middle of the cell. Full-area flatness needs span in
               both directions and points in every quadrant, otherwise
               the deviation reported is a lower bound on the real one
    datum      a cell sitting at a slight angle in the fixture reads as
               a sloped surface and is perfectly flat. Tilt belongs to
               the setup, not to the cell, so a least-squares reference
               plane is fitted and removed before any deviation is read
    shape      peak-to-valley alone does not say whether the wafer is
               domed, dished or buckled, and those three behave very
               differently once the cell is bonded down

The governing limit is the tighter of a declared absolute allowance and
a share of the cell diagonal, so a larger cell does not silently inherit
a limit written for a small one.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ABSOLUTE_ALLOWANCE = "absolute-allowance"
DIAGONAL_SHARE_ALLOWANCE = "diagonal-share-allowance"

CONVEX = "convex"
CONCAVE = "concave"
IRREGULAR = "irregular"

FLATNESS_NOT_ESTABLISHED = "bare-cell-flatness-not-established"
CELL_WITHIN_FLATNESS_LIMIT = "bare-cell-within-flatness-limit"
CELL_REFERRED_FOR_REVIEW = "bare-cell-flatness-referred-for-review"
CELL_EXCEEDS_FLATNESS_LIMIT = "bare-cell-exceeds-flatness-limit"

DEFAULT_FLATNESS_CRITERIA = {
    # the two ways the allowance can be stated; the tighter one governs
    "max_flatness_deviation_mm": 0.120,
    "flatness_fraction_of_diagonal": 0.0012,
    # a deviation past the limit but inside this factor is referred
    "flatness_review_factor": 1.5,
    # an accepted cell using at least this share of the limit is advised on
    "marginal_band_fraction": 0.90,
    # what "across its full area" demands of the measurement grid
    "min_grid_points": 9,
    "min_span_fraction": 0.80,
    "require_all_quadrants": True,
    # residual asymmetry below this share of peak-to-valley is not a shape
    "bow_signature_fraction": 0.25,
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


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Several limits here are a product of a criteria share and a measured
    dimension, so a reading sitting exactly on a limit can evaluate a few
    units in the last place above it. The limit is never widened; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_flatness_criteria(criteria):
    """Check a flatness criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "criteria max_flatness_deviation_mm", criteria.get("max_flatness_deviation_mm")
    )
    for key in ("flatness_fraction_of_diagonal", "min_span_fraction",
                "marginal_band_fraction", "bow_signature_fraction"):
        share = _require_positive("criteria %s" % key, criteria.get(key))
        if share > 1.0:
            raise ValueError(
                "criteria %s is a share and cannot exceed one, got %r" % (key, share)
            )
    factor = _require_positive(
        "criteria flatness_review_factor", criteria.get("flatness_review_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "criteria flatness_review_factor must be at least one; a review "
            "band cannot be tighter than the accept band, got %r" % (factor,)
        )
    _require_count("criteria min_grid_points", criteria.get("min_grid_points"), 3)
    if not isinstance(criteria.get("require_all_quadrants"), bool):
        raise ValueError("criteria require_all_quadrants must be true or false")
    return criteria


def validate_cell_outline(outline):
    """Check the unmounted cell outline the limit is derived from."""
    if not isinstance(outline, dict):
        raise ValueError("outline must be a mapping, got %r" % (outline,))
    length = _require_positive("length_mm", outline.get("length_mm"))
    width = _require_positive("width_mm", outline.get("width_mm"))
    thickness = _require_positive("thickness_um", outline.get("thickness_um"))
    return {
        "length_mm": length,
        "width_mm": width,
        "thickness_um": thickness,
        "diagonal_mm": math.hypot(length, width),
        "face_area_mm2": length * width,
    }


def validate_height_grid(points, outline):
    """Read back the measured height grid, refusing what cannot be used."""
    resolved = validate_cell_outline(outline)
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("the height grid must be a non-empty list of readings")
    seen = set()
    readings = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("grid reading %d must be a mapping, got %r" % (index, point))
        x = _require_number("grid reading %d x_mm" % index, point.get("x_mm"))
        y = _require_number("grid reading %d y_mm" % index, point.get("y_mm"))
        z = _require_number("grid reading %d height_um" % index, point.get("height_um"))
        if x < 0.0 or not _at_most(x, resolved["length_mm"]):
            raise ValueError(
                "grid reading %d sits at x=%.3f mm, off a %.3f mm cell"
                % (index, x, resolved["length_mm"])
            )
        if y < 0.0 or not _at_most(y, resolved["width_mm"]):
            raise ValueError(
                "grid reading %d sits at y=%.3f mm, off a %.3f mm cell"
                % (index, y, resolved["width_mm"])
            )
        station = (round(x, 6), round(y, 6))
        if station in seen:
            raise ValueError(
                "grid reading %d repeats station (%.3f, %.3f); two heights at "
                "one station cannot both be the surface" % (index, x, y)
            )
        seen.add(station)
        readings.append({"x_mm": x, "y_mm": y, "height_um": z})
    return readings


def grid_coverage(points, outline, criteria=DEFAULT_FLATNESS_CRITERIA):
    """Decide whether the grid actually spans the full face of the cell."""
    validate_flatness_criteria(criteria)
    resolved = validate_cell_outline(outline)
    readings = validate_height_grid(points, outline)
    xs = [reading["x_mm"] for reading in readings]
    ys = [reading["y_mm"] for reading in readings]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    span_x_fraction = span_x / resolved["length_mm"]
    span_y_fraction = span_y / resolved["width_mm"]
    mid_x = resolved["length_mm"] / 2.0
    mid_y = resolved["width_mm"] / 2.0
    quadrants = set()
    for reading in readings:
        quadrants.add(
            (reading["x_mm"] >= mid_x, reading["y_mm"] >= mid_y)
        )
    gaps = []
    floor = criteria["min_span_fraction"]
    if len(readings) < criteria["min_grid_points"]:
        gaps.append(
            "%d readings is short of the %d a full-area grid needs"
            % (len(readings), criteria["min_grid_points"])
        )
    if not _at_most(floor, span_x_fraction):
        gaps.append(
            "the grid spans %.3f of the cell length, short of the %.3f a "
            "full-area grid needs" % (span_x_fraction, floor)
        )
    if not _at_most(floor, span_y_fraction):
        gaps.append(
            "the grid spans %.3f of the cell width, short of the %.3f a "
            "full-area grid needs" % (span_y_fraction, floor)
        )
    if criteria["require_all_quadrants"] and len(quadrants) < 4:
        gaps.append(
            "readings fall in %d of the four quadrants; an unsampled quadrant "
            "cannot be reported as flat" % (len(quadrants),)
        )
    return {
        "reading_count": len(readings),
        "span_x_mm": span_x,
        "span_y_mm": span_y,
        "span_x_fraction": span_x_fraction,
        "span_y_fraction": span_y_fraction,
        "quadrants_sampled": len(quadrants),
        "full_area": not gaps,
        "gaps": gaps,
    }


def _solve_three(matrix, rhs):
    """Gaussian elimination with partial pivoting on a 3x3 system."""
    rows = [list(matrix[i]) + [rhs[i]] for i in range(3)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda r: abs(rows[r][column]))
        if abs(rows[pivot][column]) <= 1e-12:
            raise ValueError(
                "the height grid is degenerate: its stations are collinear, so "
                "no reference plane is determined by them"
            )
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for target in range(column + 1, 3):
            factor = rows[target][column] / rows[column][column]
            for c in range(column, 4):
                rows[target][c] -= factor * rows[column][c]
    solution = [0.0, 0.0, 0.0]
    for index in (2, 1, 0):
        total = rows[index][3]
        for c in range(index + 1, 3):
            total -= rows[index][c] * solution[c]
        solution[index] = total / rows[index][index]
    return solution


def fit_reference_plane(points, outline):
    """Least-squares reference plane through the measured stations.

    Fixture tilt is a property of the setup, not of the cell, so the datum
    is the plane the readings themselves define rather than the bench.
    """
    readings = validate_height_grid(points, outline)
    if len(readings) < 3:
        raise ValueError(
            "a reference plane needs at least three readings, got %d" % (len(readings),)
        )
    sxx = sxy = sx = syy = sy = n = 0.0
    sxz = syz = sz = 0.0
    for reading in readings:
        x = reading["x_mm"]
        y = reading["y_mm"]
        z = reading["height_um"]
        sxx += x * x
        sxy += x * y
        sx += x
        syy += y * y
        sy += y
        n += 1.0
        sxz += x * z
        syz += y * z
        sz += z
    slope_x, slope_y, offset = _solve_three(
        [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, n]], [sxz, syz, sz]
    )
    residuals = [
        reading["height_um"] - (slope_x * reading["x_mm"] + slope_y * reading["y_mm"] + offset)
        for reading in readings
    ]
    return {
        "slope_x_um_per_mm": slope_x,
        "slope_y_um_per_mm": slope_y,
        "offset_um": offset,
        "residuals_um": residuals,
        "stations": readings,
    }


def plane_tilt_um(plane, outline):
    """Height the fitted datum itself runs across the cell diagonal."""
    resolved = validate_cell_outline(outline)
    gradient = math.hypot(plane["slope_x_um_per_mm"], plane["slope_y_um_per_mm"])
    return gradient * resolved["diagonal_mm"]


def residual_profile(plane):
    """Peak-to-valley, one-sided extremes and RMS of the plane residuals."""
    residuals = plane["residuals_um"]
    if not residuals:
        raise ValueError("the plane carries no residuals to profile")
    highest = max(residuals)
    lowest = min(residuals)
    mean_square = sum(value * value for value in residuals) / float(len(residuals))
    return {
        "peak_to_valley_um": highest - lowest,
        "max_above_um": highest,
        "max_below_um": lowest,
        "rms_um": math.sqrt(mean_square),
    }


def bow_direction(plane, outline, criteria=DEFAULT_FLATNESS_CRITERIA):
    """Name the shape the residuals describe, not only their size.

    A domed cell and a dished cell can share a peak-to-valley figure and
    behave very differently once the cell is bonded down, so the centre of
    the face is compared against its perimeter rather than only measured.
    """
    validate_flatness_criteria(criteria)
    resolved = validate_cell_outline(outline)
    stations = plane["stations"]
    residuals = plane["residuals_um"]
    profile = residual_profile(plane)
    mid_x = resolved["length_mm"] / 2.0
    mid_y = resolved["width_mm"] / 2.0
    half_diagonal = math.hypot(mid_x, mid_y)
    inner = []
    outer = []
    for station, residual in zip(stations, residuals):
        radius = math.hypot(station["x_mm"] - mid_x, station["y_mm"] - mid_y)
        if _at_most(radius, half_diagonal / 2.0):
            inner.append(residual)
        else:
            outer.append(residual)
    if not inner or not outer:
        return {
            "shape": IRREGULAR,
            "centre_minus_edge_um": 0.0,
            "inner_station_count": len(inner),
            "outer_station_count": len(outer),
        }
    difference = (sum(inner) / float(len(inner))) - (sum(outer) / float(len(outer)))
    signature = profile["peak_to_valley_um"] * criteria["bow_signature_fraction"]
    if _at_most(abs(difference), signature):
        shape = IRREGULAR
    elif difference > 0.0:
        shape = CONVEX
    else:
        shape = CONCAVE
    return {
        "shape": shape,
        "centre_minus_edge_um": difference,
        "inner_station_count": len(inner),
        "outer_station_count": len(outer),
    }


def governing_flatness_limit_um(outline, criteria=DEFAULT_FLATNESS_CRITERIA):
    """The tighter of the absolute allowance and the diagonal share."""
    validate_flatness_criteria(criteria)
    resolved = validate_cell_outline(outline)
    absolute_um = criteria["max_flatness_deviation_mm"] * 1000.0
    derived_um = criteria["flatness_fraction_of_diagonal"] * resolved["diagonal_mm"] * 1000.0
    if _at_most(absolute_um, derived_um):
        return {"limit_um": absolute_um, "source": ABSOLUTE_ALLOWANCE,
                "absolute_um": absolute_um, "diagonal_share_um": derived_um}
    return {"limit_um": derived_um, "source": DIAGONAL_SHARE_ALLOWANCE,
            "absolute_um": absolute_um, "diagonal_share_um": derived_um}


def assess_bare_cell_flatness(case, criteria=DEFAULT_FLATNESS_CRITERIA):
    """Clause 7.5.19 flatness verdict for one unmounted bare cell."""
    validate_flatness_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    cell_id = case.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each case needs a non-empty cell_id")
    outline = case.get("outline")
    points = case.get("height_grid")
    if points is None:
        raise ValueError("a flatness case needs a height_grid of readings")
    resolved = validate_cell_outline(outline)
    coverage = grid_coverage(points, outline, criteria)

    method = case.get("measurement_method")
    findings = list(coverage["gaps"])
    if not isinstance(method, str) or not method.strip():
        findings.append(
            "no measurement method recorded; a flatness figure nobody can tie "
            "to a method is not a verdict against this clause"
        )
    if findings:
        return {
            "cell_id": cell_id,
            "verdict": FLATNESS_NOT_ESTABLISHED,
            "coverage": coverage,
            "findings": findings,
            "advisories": [],
        }

    plane = fit_reference_plane(points, outline)
    profile = residual_profile(plane)
    shape = bow_direction(plane, outline, criteria)
    limit = governing_flatness_limit_um(outline, criteria)
    tilt = plane_tilt_um(plane, outline)

    deviation = profile["peak_to_valley_um"]
    review_limit = limit["limit_um"] * criteria["flatness_review_factor"]
    advisories = []
    if _at_most(deviation, limit["limit_um"]):
        verdict = CELL_WITHIN_FLATNESS_LIMIT
        if not _at_most(
            deviation, limit["limit_um"] * criteria["marginal_band_fraction"]
        ):
            advisories.append(
                "%s is inside the limit at %.2f um of %.2f um, with little left "
                "for handling and bonding" % (cell_id, deviation, limit["limit_um"])
            )
    elif _at_most(deviation, review_limit):
        verdict = CELL_REFERRED_FOR_REVIEW
        findings.append(
            "%s departs %.2f um from its reference plane, past the %.2f um "
            "allowance" % (cell_id, deviation, limit["limit_um"])
        )
    else:
        verdict = CELL_EXCEEDS_FLATNESS_LIMIT
        findings.append(
            "%s departs %.2f um from its reference plane, past the %.2f um "
            "review limit" % (cell_id, deviation, review_limit)
        )

    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "coverage": coverage,
        "measurement_method": method.strip(),
        "diagonal_mm": resolved["diagonal_mm"],
        "peak_to_valley_um": deviation,
        "max_above_um": profile["max_above_um"],
        "max_below_um": profile["max_below_um"],
        "rms_um": profile["rms_um"],
        "shape": shape["shape"],
        "centre_minus_edge_um": shape["centre_minus_edge_um"],
        "fixture_tilt_um_across_diagonal": tilt,
        "flatness_limit_um": limit["limit_um"],
        "limit_source": limit["source"],
        "margin_um": limit["limit_um"] - deviation,
        "limit_used_fraction": deviation / limit["limit_um"],
        "findings": findings,
        "advisories": advisories,
    }
