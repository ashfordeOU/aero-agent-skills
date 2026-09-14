#!/usr/bin/env python3
"""Spatial uniformity of the irradiance a simulator lays over its test plane.

Anchor: ECSS-E-ST-20-08C clause 10.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks one question: over the area nominated as the test plane,
and while the measurement is actually being taken, how evenly is the
irradiance spread? Four consequences follow, and each is a way a
simulator qualification goes wrong.

The area is nominated, not assumed. A beam is uniform over some region
and not over a larger one, so the figure only means something once the
plane it was taken over is declared and the sample points are shown to
sit inside it. A map that covers the comfortable middle of the plane and
stops short of the corners has measured a smaller simulator than the one
the article will be illuminated by.

The figure is an extreme-to-extreme figure, not a scatter about the
mean. The cell that sees the coldest corner is the cell that limits a
series string, and a standard deviation over a hundred points can look
healthy while two of them are eight per cent apart. Non-uniformity is
therefore taken as the spread between the brightest and dimmest readings
normalised by their sum.

Sampling is part of the result. A grid of four points cannot find a
gradient that lives between them, so a point count and a plane coverage
are validated before any uniformity figure is quoted, and a map that
fails either closes the assessment rather than passing it.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TEST_PLANE_NOT_DECLARED = "test-plane-not-declared"
PLANE_SAMPLING_INSUFFICIENT = "test-plane-sampling-insufficient"
UNIFORMITY_OUT_OF_LIMIT = "irradiance-uniformity-out-of-limit"
UNIFORMITY_WITHIN_LIMIT = "irradiance-uniformity-within-limit"

OUTSIDE_DECLARED_BANDS = "outside-declared-bands"

DEFAULT_UNIFORMITY_POLICY = {
    "max_non_uniformity_percent": 2.0,
    "min_sample_points": 9,
    "min_coverage_fraction": 0.8,
    "uniformity_bands_percent": (2.0, 5.0, 10.0),
    "marginal_band_percent": 0.2,
}

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


def validate_uniformity_policy(policy):
    """Check the uniformity policy is complete and sensible before it is used."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    limit = _require_positive(
        "max_non_uniformity_percent", policy.get("max_non_uniformity_percent")
    )
    if limit >= 100.0:
        raise ValueError(
            "max_non_uniformity_percent %g admits a plane lit at one corner "
            "and dark at the other; that is not a uniformity limit" % limit
        )
    points = policy.get("min_sample_points")
    if not isinstance(points, int) or isinstance(points, bool) or points < 4:
        raise ValueError(
            "min_sample_points must be an integer of at least four, got %r"
            % (points,)
        )
    coverage = _require_positive(
        "min_coverage_fraction", policy.get("min_coverage_fraction")
    )
    if coverage > 1.0:
        raise ValueError(
            "min_coverage_fraction %g asks the map to cover more than the "
            "plane it was nominated over" % coverage
        )
    bands = policy.get("uniformity_bands_percent")
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("uniformity_bands_percent must be a non-empty sequence")
    previous = 0.0
    for index, band in enumerate(bands):
        edge = _require_positive("uniformity_bands_percent[%d]" % index, band)
        if not edge > previous:
            raise ValueError(
                "uniformity bands must widen in order; %g follows %g"
                % (edge, previous)
            )
        previous = edge
    _require_non_negative(
        "marginal_band_percent", policy.get("marginal_band_percent")
    )
    return policy


def validate_test_plane(plane):
    """Read the area nominated as the test plane."""
    if not isinstance(plane, dict):
        raise ValueError("plane must be a mapping, got %r" % (plane,))
    designation = _require_label("designation", plane.get("designation"))
    width = _require_positive("width_mm", plane.get("width_mm"))
    height = _require_positive("height_mm", plane.get("height_mm"))
    return {
        "designation": designation,
        "width_mm": width,
        "height_mm": height,
        "area_mm2": width * height,
    }


def validate_sample_point(point):
    """Read one mapped point: where it sat and what it read."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping, got %r" % (point,))
    identifier = _require_label("point id", point.get("id"))
    if not identifier:
        raise ValueError("point id must not be blank")
    x_mm = _require_number("x_mm on %s" % identifier, point.get("x_mm"))
    y_mm = _require_number("y_mm on %s" % identifier, point.get("y_mm"))
    irradiance = _require_positive(
        "irradiance_w_m2 on %s" % identifier, point.get("irradiance_w_m2")
    )
    return {
        "id": identifier,
        "x_mm": x_mm,
        "y_mm": y_mm,
        "irradiance_w_m2": irradiance,
    }


def sample_points(points):
    """Read every mapped point, refusing an empty or self-colliding map."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence of mapped sample points")
    if not points:
        raise ValueError(
            "no point was mapped, so the plane has no uniformity figure at all"
        )
    read = []
    seen = set()
    for point in points:
        checked = validate_sample_point(point)
        if checked["id"] in seen:
            raise ValueError("duplicate point id %r in the map" % checked["id"])
        seen.add(checked["id"])
        read.append(checked)
    return tuple(read)


def point_inside_plane(point, plane):
    """True when a mapped point sits on the nominated plane."""
    checked_plane = validate_test_plane(plane)
    inside_x = _at_least(point["x_mm"], 0.0) and _at_most(
        point["x_mm"], checked_plane["width_mm"]
    )
    inside_y = _at_least(point["y_mm"], 0.0) and _at_most(
        point["y_mm"], checked_plane["height_mm"]
    )
    return inside_x and inside_y


def points_outside_plane(points, plane):
    """Name every mapped point that fell off the nominated plane."""
    checked_plane = validate_test_plane(plane)
    return tuple(
        point["id"]
        for point in points
        if not point_inside_plane(point, checked_plane)
    )


def spatial_non_uniformity_percent(points):
    """Spread between the brightest and dimmest readings, normalised by their sum.

    Deliberately an extreme-to-extreme figure. The dimmest point on the
    plane is what limits a series string, and a scatter about the mean
    hides it behind the well-lit majority.
    """
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence of mapped points")
    values = [
        _require_positive("irradiance_w_m2", point["irradiance_w_m2"])
        for point in points
    ]
    brightest = max(values)
    dimmest = min(values)
    return (brightest - dimmest) / (brightest + dimmest) * 100.0


def mean_irradiance_w_m2(points):
    """Plain average of the mapped readings, reported beside the spread."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence of mapped points")
    return sum(point["irradiance_w_m2"] for point in points) / len(points)


def extreme_points(points):
    """The brightest and the dimmest mapped point, by identifier."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence of mapped points")
    brightest = max(points, key=lambda point: point["irradiance_w_m2"])
    dimmest = min(points, key=lambda point: point["irradiance_w_m2"])
    return brightest["id"], dimmest["id"]


def sampled_coverage_fraction(points, plane):
    """Share of the nominated plane the mapped points actually span.

    Taken as the bounding box the points enclose against the plane area.
    A map bunched in the middle of the plane reports a small fraction and
    is refused, because the corners it never visited are exactly where a
    beam falls away.
    """
    checked_plane = validate_test_plane(plane)
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence of mapped points")
    xs = [point["x_mm"] for point in points]
    ys = [point["y_mm"] for point in points]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    return (span_x * span_y) / checked_plane["area_mm2"]


def uniformity_category(non_uniformity_percent, policy=DEFAULT_UNIFORMITY_POLICY):
    """Group a uniformity figure into the declared bands.

    Returns the one-based band index the figure falls in, or the
    outside-declared-bands marker when it is wider than every band.
    """
    validate_uniformity_policy(policy)
    value = _require_non_negative(
        "non_uniformity_percent", non_uniformity_percent
    )
    for index, edge in enumerate(policy["uniformity_bands_percent"]):
        if _at_most(value, float(edge)):
            return "band-%d" % (index + 1)
    return OUTSIDE_DECLARED_BANDS


def sampling_findings(points, plane, policy=DEFAULT_UNIFORMITY_POLICY):
    """Name every way the map is too thin to support a uniformity figure."""
    validate_uniformity_policy(policy)
    checked_plane = validate_test_plane(plane)
    findings = []
    if len(points) < int(policy["min_sample_points"]):
        findings.append(
            "the map holds %d points against the %d the sampling policy asks "
            "for; a gradient living between them cannot be found"
            % (len(points), int(policy["min_sample_points"]))
        )
    stray = points_outside_plane(points, checked_plane)
    if stray:
        findings.append(
            "point %s fell off the nominated plane %s, so the map is not a map "
            "of the area the article is illuminated over"
            % (", ".join(stray), checked_plane["designation"])
        )
    coverage = sampled_coverage_fraction(points, checked_plane)
    if not _at_least(coverage, float(policy["min_coverage_fraction"])):
        findings.append(
            "the mapped points span %.3g per cent of plane %s against the %.3g "
            "per cent the policy asks for; the unvisited edge is where a beam "
            "falls away"
            % (
                coverage * 100.0,
                checked_plane["designation"],
                float(policy["min_coverage_fraction"]) * 100.0,
            )
        )
    return tuple(findings)


def assess_irradiance_uniformity(case, policy=DEFAULT_UNIFORMITY_POLICY):
    """Full clause 10.1.2 uniformity assessment for one mapped test plane."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_uniformity_policy(policy)

    findings = []
    advisories = []
    result = {
        "plane_designation": None,
        "plane_area_mm2": None,
        "sample_count": 0,
        "non_uniformity_percent": None,
        "mean_irradiance_w_m2": None,
        "brightest_point_id": None,
        "dimmest_point_id": None,
        "coverage_fraction": None,
        "uniformity_band": None,
        "findings": findings,
        "advisories": advisories,
    }

    plane = case.get("test_plane")
    if plane is None:
        findings.append(
            "no test plane is nominated, so an irradiance map has no area to "
            "be uniform over and the figure means nothing"
        )
        result["verdict"] = TEST_PLANE_NOT_DECLARED
        return result
    checked_plane = validate_test_plane(plane)
    result["plane_designation"] = checked_plane["designation"]
    result["plane_area_mm2"] = checked_plane["area_mm2"]
    if not checked_plane["designation"]:
        findings.append(
            "the plane carries no designation; an unnamed area cannot be shown "
            "to be the one the measurement was taken over"
        )
        result["verdict"] = TEST_PLANE_NOT_DECLARED
        return result

    points = sample_points(case.get("sample_points"))
    result["sample_count"] = len(points)
    result["coverage_fraction"] = sampled_coverage_fraction(points, checked_plane)

    thin = sampling_findings(points, checked_plane, policy)
    if thin:
        findings.extend(thin)
        result["verdict"] = PLANE_SAMPLING_INSUFFICIENT
        return result

    spread = spatial_non_uniformity_percent(points)
    result["non_uniformity_percent"] = spread
    result["mean_irradiance_w_m2"] = mean_irradiance_w_m2(points)
    brightest, dimmest = extreme_points(points)
    result["brightest_point_id"] = brightest
    result["dimmest_point_id"] = dimmest
    result["uniformity_band"] = uniformity_category(spread, policy)

    limit = float(policy["max_non_uniformity_percent"])
    if not _at_most(spread, limit):
        findings.append(
            "plane %s spreads %.3g per cent between point %s and point %s, "
            "above the %.3g per cent the measurement was quoted at"
            % (checked_plane["designation"], spread, brightest, dimmest, limit)
        )
        result["verdict"] = UNIFORMITY_OUT_OF_LIMIT
        return result

    margin = limit - spread
    if _at_most(margin, float(policy["marginal_band_percent"])):
        advisories.append(
            "plane %s clears the %.3g per cent limit by %.3g percentage "
            "points; lamp ageing will take that back before the next map"
            % (checked_plane["designation"], limit, margin)
        )

    result["verdict"] = UNIFORMITY_WITHIN_LIMIT
    return result
