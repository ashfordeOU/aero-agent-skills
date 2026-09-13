#!/usr/bin/env python3
"""Coupon dimensions, stay-out zones and standoff features at inspection.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Part of the visual inspection of a photovoltaic assembly coupon is not
about defects at all. It asks three geometric questions:

    dimensions      is the coupon the size the drawing says, inside the
                    plus and minus tolerance written against each
                    dimension
    stay-out zones  do the keep-out areas -- harness routing corridors,
                    hold-down footprints, edge margins reserved for the
                    substrate bond -- stay empty of every placed feature
    standoffs       are the standoff features at their called-out height,
                    and does each footprint sit where it is allowed to

The arithmetic is plain rectangle geometry, which is exactly why it is
worth doing mechanically: an intrusion of a fraction of a millimetre is
invisible to an inspector holding a drawing, and a stay-out zone that a
feature only just touches is the one that moves under thermal cycling.

Rectangles are axis-aligned and carry the lower-left corner with a width
and a height, in millimetres, in the coupon frame.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIMENSION_WITHIN = "dimension-within-tolerance"
DIMENSION_ABOVE = "dimension-above-upper-limit"
DIMENSION_BELOW = "dimension-below-lower-limit"

ZONE_CLEAR = "stay-out-zone-clear"
ZONE_CLEARANCE_SHORT = "stay-out-zone-clearance-short"
ZONE_INTRUDED = "stay-out-zone-intruded"

GEOMETRY_ACCEPTED = "coupon-geometry-accepted"
GEOMETRY_REJECTED = "coupon-geometry-rejected"

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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _close(a, b):
    return math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A clearance is a difference of coordinates that were themselves built
    by addition, so a feature placed exactly on a minimum clearance can
    land a few units in the last place below it. The minimum is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= limit or _close(value, limit)


def check_dimension(name, nominal_mm, plus_tolerance_mm, minus_tolerance_mm, measured_mm):
    """Place one measured coupon dimension inside its drawing tolerance band."""
    label = _require_text("dimension name", name)
    nominal = _require_positive("%s nominal_mm" % label, nominal_mm)
    plus = _require_non_negative("%s plus_tolerance_mm" % label, plus_tolerance_mm)
    minus = _require_non_negative("%s minus_tolerance_mm" % label, minus_tolerance_mm)
    if plus + minus <= 0.0:
        raise ValueError("%s has no tolerance band on either side" % label)
    measured = _require_positive("%s measured_mm" % label, measured_mm)
    upper = nominal + plus
    lower = nominal - minus
    if lower <= 0.0:
        raise ValueError(
            "%s lower limit %g mm is not a physical dimension" % (label, lower)
        )
    deviation = measured - nominal
    if deviation > 0.0 and not _close(measured, nominal):
        utilisation = math.inf if plus == 0.0 else deviation / plus
    elif deviation < 0.0 and not _close(measured, nominal):
        utilisation = math.inf if minus == 0.0 else -deviation / minus
    else:
        utilisation = 0.0
    if measured > upper and not _close(measured, upper):
        verdict = DIMENSION_ABOVE
    elif measured < lower and not _close(measured, lower):
        verdict = DIMENSION_BELOW
    else:
        verdict = DIMENSION_WITHIN
    return {
        "name": label,
        "nominal_mm": nominal,
        "upper_limit_mm": upper,
        "lower_limit_mm": lower,
        "measured_mm": measured,
        "deviation_mm": deviation,
        "utilisation": utilisation,
        "within_tolerance": verdict == DIMENSION_WITHIN,
        "verdict": verdict,
    }


def check_coupon_dimensions(spec, measured):
    """Check every called-out coupon dimension against its measurement."""
    if not isinstance(spec, dict) or not spec:
        raise ValueError("spec must be a non-empty mapping of dimension names")
    if not isinstance(measured, dict) or not measured:
        raise ValueError("measured must be a non-empty mapping of dimension names")
    extra = sorted(set(measured) - set(spec))
    if extra:
        raise ValueError(
            "measured dimensions with no drawing entry: %s" % ", ".join(extra)
        )
    results = []
    for name in sorted(spec):
        entry = spec[name]
        if not isinstance(entry, dict):
            raise ValueError("spec entry %s must be a mapping" % name)
        if name not in measured:
            raise ValueError("dimension %s was called out but never measured" % name)
        results.append(
            check_dimension(
                name,
                entry.get("nominal_mm"),
                entry.get("plus_tolerance_mm"),
                entry.get("minus_tolerance_mm"),
                measured[name],
            )
        )
    out_of_tolerance = [r for r in results if not r["within_tolerance"]]
    governing = sorted(results, key=lambda r: (-r["utilisation"], r["name"]))[0]["name"]
    findings = [
        "%s measured %.3f mm against %.3f/%.3f mm limits"
        % (r["name"], r["measured_mm"], r["lower_limit_mm"], r["upper_limit_mm"])
        for r in out_of_tolerance
    ]
    return {
        "results": results,
        "out_of_tolerance": [r["name"] for r in out_of_tolerance],
        "governing_dimension": governing,
        "within_tolerance": not out_of_tolerance,
        "findings": findings,
    }


def _rect_bounds(label, rect):
    if not isinstance(rect, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, rect))
    x0 = _require_number("%s x_mm" % label, rect.get("x_mm"))
    y0 = _require_number("%s y_mm" % label, rect.get("y_mm"))
    width = _require_positive("%s width_mm" % label, rect.get("width_mm"))
    height = _require_positive("%s height_mm" % label, rect.get("height_mm"))
    return x0, y0, x0 + width, y0 + height


def rectangle_overlap_area_mm2(first, second):
    """Area the two axis-aligned rectangles share, zero when they do not."""
    ax0, ay0, ax1, ay1 = _rect_bounds("first rectangle", first)
    bx0, by0, bx1, by1 = _rect_bounds("second rectangle", second)
    dx = min(ax1, bx1) - max(ax0, bx0)
    dy = min(ay1, by1) - max(ay0, by0)
    if dx <= 0.0 or dy <= 0.0:
        return 0.0
    return dx * dy


def rectangle_clearance_mm(first, second):
    """Shortest distance between two rectangles; zero when they touch."""
    ax0, ay0, ax1, ay1 = _rect_bounds("first rectangle", first)
    bx0, by0, bx1, by1 = _rect_bounds("second rectangle", second)
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def intrusion_depth_mm(feature, zone):
    """How far the feature would have to move to leave the stay-out zone."""
    fx0, fy0, fx1, fy1 = _rect_bounds("feature", feature)
    zx0, zy0, zx1, zy1 = _rect_bounds("zone", zone)
    dx = min(fx1, zx1) - max(fx0, zx0)
    dy = min(fy1, zy1) - max(fy0, zy0)
    if dx <= 0.0 or dy <= 0.0:
        return 0.0
    return min(fx1 - zx0, zx1 - fx0, fy1 - zy0, zy1 - fy0)


def edge_margin_zones(coupon_width_mm, coupon_height_mm, margin_mm):
    """Build the four border stay-out bands a reserved edge margin creates."""
    width = _require_positive("coupon_width_mm", coupon_width_mm)
    height = _require_positive("coupon_height_mm", coupon_height_mm)
    margin = _require_positive("margin_mm", margin_mm)
    if 2.0 * margin >= width or 2.0 * margin >= height:
        raise ValueError(
            "an edge margin of %g mm leaves no usable area on a %g by %g mm coupon"
            % (margin, width, height)
        )
    return [
        {"id": "edge-margin-left", "x_mm": 0.0, "y_mm": 0.0,
         "width_mm": margin, "height_mm": height},
        {"id": "edge-margin-right", "x_mm": width - margin, "y_mm": 0.0,
         "width_mm": margin, "height_mm": height},
        {"id": "edge-margin-bottom", "x_mm": margin, "y_mm": 0.0,
         "width_mm": width - 2.0 * margin, "height_mm": margin},
        {"id": "edge-margin-top", "x_mm": margin, "y_mm": height - margin,
         "width_mm": width - 2.0 * margin, "height_mm": margin},
    ]


def check_stay_out_zones(zones, features, minimum_clearance_mm=0.0):
    """Test every placed feature against every keep-out area on the coupon."""
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("zones must be a non-empty sequence")
    if not isinstance(features, (list, tuple)):
        raise ValueError("features must be a sequence")
    minimum = _require_non_negative("minimum_clearance_mm", minimum_clearance_mm)
    zone_ids = set()
    for zone in zones:
        zone_id = _require_text("zone id", zone.get("id") if isinstance(zone, dict) else None)
        if zone_id in zone_ids:
            raise ValueError("duplicate stay-out zone id %r" % (zone_id,))
        zone_ids.add(zone_id)
        _rect_bounds("zone %s" % zone_id, zone)
    pairs = []
    findings = []
    for feature in features:
        feature_id = _require_text(
            "feature id", feature.get("id") if isinstance(feature, dict) else None
        )
        _rect_bounds("feature %s" % feature_id, feature)
        for zone in zones:
            overlap = rectangle_overlap_area_mm2(feature, zone)
            depth = intrusion_depth_mm(feature, zone)
            clearance = rectangle_clearance_mm(feature, zone)
            if overlap > 0.0:
                verdict = ZONE_INTRUDED
                findings.append(
                    "%s intrudes %.3f mm into %s over %.4f mm2"
                    % (feature_id, depth, zone["id"], overlap)
                )
            elif not _at_least(clearance, minimum):
                verdict = ZONE_CLEARANCE_SHORT
                findings.append(
                    "%s clears %s by %.3f mm against a %.3f mm minimum"
                    % (feature_id, zone["id"], clearance, minimum)
                )
            else:
                verdict = ZONE_CLEAR
            pairs.append(
                {
                    "feature": feature_id,
                    "zone": zone["id"],
                    "overlap_area_mm2": overlap,
                    "intrusion_depth_mm": depth,
                    "clearance_mm": clearance,
                    "verdict": verdict,
                }
            )
    breaches = [p for p in pairs if p["verdict"] != ZONE_CLEAR]
    return {
        "pairs": pairs,
        "breaches": breaches,
        "clear": not breaches,
        "findings": findings,
    }


def check_standoff_features(standoffs, height_spec, zones=None, minimum_clearance_mm=0.0):
    """Check each standoff height and keep its footprint out of the zones."""
    if not isinstance(standoffs, (list, tuple)) or not standoffs:
        raise ValueError("standoffs must be a non-empty sequence")
    if not isinstance(height_spec, dict):
        raise ValueError("height_spec must be a mapping")
    results = []
    findings = []
    footprints = []
    seen = set()
    for standoff in standoffs:
        if not isinstance(standoff, dict):
            raise ValueError("standoff must be a mapping, got %r" % (standoff,))
        standoff_id = _require_text("standoff id", standoff.get("id"))
        if standoff_id in seen:
            raise ValueError("duplicate standoff id %r" % (standoff_id,))
        seen.add(standoff_id)
        height = check_dimension(
            "%s height" % standoff_id,
            height_spec.get("nominal_mm"),
            height_spec.get("plus_tolerance_mm"),
            height_spec.get("minus_tolerance_mm"),
            standoff.get("height_mm"),
        )
        footprint = standoff.get("footprint")
        _rect_bounds("standoff %s footprint" % standoff_id, footprint)
        footprints.append(dict(footprint, id=standoff_id))
        if not height["within_tolerance"]:
            findings.append(
                "%s stands %.3f mm against %.3f/%.3f mm limits"
                % (
                    standoff_id,
                    height["measured_mm"],
                    height["lower_limit_mm"],
                    height["upper_limit_mm"],
                )
            )
        results.append({"id": standoff_id, "height": height})
    zone_report = None
    if zones:
        zone_report = check_stay_out_zones(zones, footprints, minimum_clearance_mm)
        findings.extend(zone_report["findings"])
    return {
        "results": results,
        "zone_report": zone_report,
        "heights_within_tolerance": all(
            r["height"]["within_tolerance"] for r in results
        ),
        "findings": findings,
    }


def inspect_coupon_geometry(case):
    """Full clause 5.5.3.2.4 dimensional and keep-out check of one coupon."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    dimensions = check_coupon_dimensions(
        case.get("dimension_spec"), case.get("measured_dimensions")
    )
    zones = list(case.get("stay_out_zones") or [])
    margin = case.get("edge_margin_mm")
    if margin is not None:
        zones.extend(
            edge_margin_zones(
                case["measured_dimensions"].get(case.get("width_dimension", "width")),
                case["measured_dimensions"].get(case.get("height_dimension", "height")),
                margin,
            )
        )
    minimum = case.get("minimum_clearance_mm", 0.0)
    if zones:
        zone_report = check_stay_out_zones(zones, case.get("features") or [], minimum)
    else:
        if case.get("features"):
            raise ValueError(
                "features were placed but the case declares no stay-out zone to "
                "check them against"
            )
        zone_report = {"pairs": [], "breaches": [], "clear": True, "findings": []}
    standoff_report = None
    findings = list(dimensions["findings"]) + list(zone_report["findings"])
    if case.get("standoffs"):
        standoff_report = check_standoff_features(
            case["standoffs"], case.get("standoff_height_spec") or {}, zones, minimum
        )
        findings.extend(standoff_report["findings"])
    accepted = (
        dimensions["within_tolerance"]
        and zone_report["clear"]
        and (
            standoff_report is None
            or (
                standoff_report["heights_within_tolerance"]
                and (
                    standoff_report["zone_report"] is None
                    or standoff_report["zone_report"]["clear"]
                )
            )
        )
    )
    return {
        "dimensions": dimensions,
        "zone_report": zone_report,
        "standoff_report": standoff_report,
        "verdict": GEOMETRY_ACCEPTED if accepted else GEOMETRY_REJECTED,
        "findings": findings,
    }
