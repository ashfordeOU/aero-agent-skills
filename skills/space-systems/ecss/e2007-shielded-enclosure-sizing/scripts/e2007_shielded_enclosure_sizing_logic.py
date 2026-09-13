#!/usr/bin/env python3
"""Shielded-enclosure sizing check, ECSS-E-ST-20-07C clause 5.2.2.2 (anchor).

Paraphrased procedure, no verbatim standard text. The clause requires the
EMC facility to be dimensionally adequate for the declared equipment layout
and for the measurement-antenna placement the emission and susceptibility
runs need. This module turns that into a deterministic geometry check:

  internal envelope -> usable envelope (absorber removed)
  layout + antenna   -> per-axis requirement
  requirement vs usable -> signed margin, governing axis, verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Dimensional tolerance, metres. Layout requirements are a sum of several
# float lengths, so an exactly-fitting layout can land a few units in the
# last place short of the usable dimension. The tolerance absorbs that
# representation error only; it never relaxes a clearance.
DIM_TOL_M = 1e-9

# Calibrated antenna standoffs recognized for radiated runs, metres.
CALIBRATED_STANDOFFS_M = (1.0, 3.0, 10.0)

# Physical depth of the antenna body behind its reference point, metres,
# and the half-aperture used for the vertical scan-ceiling check.
ANTENNA_GEOMETRY_M = {
    "biconical": {"depth": 0.55, "half_aperture": 0.70},
    "log-periodic": {"depth": 0.75, "half_aperture": 0.40},
    "double-ridged-horn": {"depth": 0.45, "half_aperture": 0.20},
    "loop": {"depth": 0.20, "half_aperture": 0.30},
    "rod-monopole": {"depth": 0.15, "half_aperture": 0.55},
}

# Minimum separation that must remain between the back of the antenna and
# the absorber tips behind it, metres.
ANTENNA_TIP_CLEARANCE_M = 0.30

AXES = ("measurement", "lateral", "vertical")


def _number(record, key, where):
    """Return record[key] as float, raising ValueError on absence or type."""
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be > 0, got %g" % (where, key, value))
    return value


def _non_negative(record, key, where):
    value = _number(record, key, where)
    if value < 0.0:
        raise ValueError("%s: field %r must be >= 0, got %g" % (where, key, value))
    return value


def fits(available_m, required_m, tol_m=DIM_TOL_M):
    """True when available clears required, absorbing float representation.

    A difference smaller than the dimensional tolerance is a fit: the
    requirement is a sum of float lengths and an exactly-fitting layout must
    not be failed by the last bit of the mantissa.
    """
    if available_m >= required_m:
        return True
    return math.isclose(available_m, required_m, rel_tol=0.0, abs_tol=tol_m)


def validate_enclosure(enclosure):
    """Validate a shielded-enclosure record and return a normalized copy.

    Required: internal_length_m, internal_width_m, internal_height_m,
    wall_absorber_depth_m. Optional: ceiling_absorber_depth_m,
    floor_absorber_depth_m (default 0.0 = unlined floor, e.g. a ground
    plane), quiet_zone_diameter_m (default 0.0 = not declared).
    """
    where = "enclosure"
    if not isinstance(enclosure, dict):
        raise ValueError("%s: record must be a mapping" % where)
    out = {
        "internal_length_m": _positive(enclosure, "internal_length_m", where),
        "internal_width_m": _positive(enclosure, "internal_width_m", where),
        "internal_height_m": _positive(enclosure, "internal_height_m", where),
        "wall_absorber_depth_m": _non_negative(enclosure, "wall_absorber_depth_m", where),
    }
    ceiling = enclosure.get("ceiling_absorber_depth_m", out["wall_absorber_depth_m"])
    floor = enclosure.get("floor_absorber_depth_m", 0.0)
    out["ceiling_absorber_depth_m"] = _non_negative(
        {"v": ceiling}, "v", "%s.ceiling_absorber_depth_m" % where
    )
    out["floor_absorber_depth_m"] = _non_negative(
        {"v": floor}, "v", "%s.floor_absorber_depth_m" % where
    )
    quiet = enclosure.get("quiet_zone_diameter_m", 0.0)
    out["quiet_zone_diameter_m"] = _non_negative(
        {"v": quiet}, "v", "%s.quiet_zone_diameter_m" % where
    )

    wall_pair = 2.0 * out["wall_absorber_depth_m"]
    for key in ("internal_length_m", "internal_width_m"):
        if wall_pair >= out[key]:
            raise ValueError(
                "%s: absorber on both walls (%g m) consumes the whole %s (%g m)"
                % (where, wall_pair, key, out[key])
            )
    vertical_pair = out["ceiling_absorber_depth_m"] + out["floor_absorber_depth_m"]
    if vertical_pair >= out["internal_height_m"]:
        raise ValueError(
            "%s: ceiling plus floor absorber (%g m) consumes the whole height (%g m)"
            % (where, vertical_pair, out["internal_height_m"])
        )
    return out


def usable_envelope(enclosure):
    """Reduce a validated internal envelope to the usable envelope."""
    record = validate_enclosure(enclosure)
    wall_pair = 2.0 * record["wall_absorber_depth_m"]
    return {
        "measurement_m": record["internal_length_m"] - wall_pair,
        "lateral_m": record["internal_width_m"] - wall_pair,
        "vertical_m": record["internal_height_m"]
        - record["ceiling_absorber_depth_m"]
        - record["floor_absorber_depth_m"],
        "quiet_zone_diameter_m": record["quiet_zone_diameter_m"],
    }


def antenna_geometry(antenna_type):
    """Return the depth / half-aperture pair for a recognized antenna type."""
    if not isinstance(antenna_type, str):
        raise ValueError("antenna_type must be a string, got %r" % (antenna_type,))
    key = antenna_type.strip().lower()
    if key not in ANTENNA_GEOMETRY_M:
        raise ValueError(
            "unrecognized antenna_type %r; recognized: %s"
            % (antenna_type, ", ".join(sorted(ANTENNA_GEOMETRY_M)))
        )
    return dict(ANTENNA_GEOMETRY_M[key])


def validate_layout(layout):
    """Validate the bench layout record and return a normalized copy.

    Required: unit_depth_m, unit_width_m, unit_height_m, bench_height_m,
    edge_clearance_m. Optional: support_rack_width_m (default 0.0),
    support_rack_separation_m (default 0.0), ceiling_headroom_m
    (default 0.5), antenna_scan_top_m (default 0.0 = no scan declared).
    """
    where = "layout"
    if not isinstance(layout, dict):
        raise ValueError("%s: record must be a mapping" % where)
    out = {
        "unit_depth_m": _positive(layout, "unit_depth_m", where),
        "unit_width_m": _positive(layout, "unit_width_m", where),
        "unit_height_m": _positive(layout, "unit_height_m", where),
        "bench_height_m": _positive(layout, "bench_height_m", where),
        "edge_clearance_m": _non_negative(layout, "edge_clearance_m", where),
    }
    for key, default in (
        ("support_rack_width_m", 0.0),
        ("support_rack_separation_m", 0.0),
        ("ceiling_headroom_m", 0.5),
        ("antenna_scan_top_m", 0.0),
    ):
        out[key] = _non_negative(
            {"v": layout.get(key, default)}, "v", "%s.%s" % (where, key)
        )
    if out["support_rack_width_m"] == 0.0 and out["support_rack_separation_m"] > 0.0:
        raise ValueError(
            "%s: support_rack_separation_m declared without support_rack_width_m"
            % where
        )
    return out


def validate_standoff(standoff_m):
    """Validate the antenna standoff against the calibrated separations."""
    value = _positive({"v": standoff_m}, "v", "standoff_m")
    for allowed in CALIBRATED_STANDOFFS_M:
        if math.isclose(value, allowed, rel_tol=0.0, abs_tol=DIM_TOL_M):
            return allowed
    raise ValueError(
        "standoff_m %g is not a calibrated separation; allowed: %s"
        % (value, ", ".join("%g" % s for s in CALIBRATED_STANDOFFS_M))
    )


def bench_footprint(layout):
    """Return the bench footprint (depth, width) built from the unit and
    its edge-clearance, plus the footprint diagonal used by the quiet-zone
    check."""
    record = validate_layout(layout)
    depth = record["unit_depth_m"] + 2.0 * record["edge_clearance_m"]
    width = record["unit_width_m"] + 2.0 * record["edge_clearance_m"]
    return {
        "depth_m": depth,
        "width_m": width,
        "diagonal_m": math.hypot(depth, width),
    }


def required_measurement_axis(layout, antenna_type, standoff_m):
    """Length required along the measurement axis, metres.

    unit depth on the bench + antenna standoff + antenna body depth +
    antenna-to-absorber-tip clearance.
    """
    footprint = bench_footprint(layout)
    geometry = antenna_geometry(antenna_type)
    standoff = validate_standoff(standoff_m)
    return (
        footprint["depth_m"]
        + standoff
        + geometry["depth"]
        + ANTENNA_TIP_CLEARANCE_M
    )


def required_lateral_axis(layout):
    """Width required across the lateral axis, metres."""
    record = validate_layout(layout)
    footprint = bench_footprint(layout)
    width = footprint["width_m"]
    if record["support_rack_width_m"] > 0.0:
        width += record["support_rack_separation_m"] + record["support_rack_width_m"]
    return width


def required_vertical_axis(layout, antenna_type):
    """Height required on the vertical axis, metres.

    The governing term is the larger of the bench stack (bench height +
    unit height + ceiling headroom) and the antenna scan ceiling (top scan
    position + antenna half-aperture + ceiling headroom).
    """
    record = validate_layout(layout)
    geometry = antenna_geometry(antenna_type)
    bench_stack = (
        record["bench_height_m"] + record["unit_height_m"] + record["ceiling_headroom_m"]
    )
    scan_ceiling = 0.0
    if record["antenna_scan_top_m"] > 0.0:
        scan_ceiling = (
            record["antenna_scan_top_m"]
            + geometry["half_aperture"]
            + record["ceiling_headroom_m"]
        )
    return max(bench_stack, scan_ceiling)


def axis_result(axis, required_m, available_m):
    """Build the per-axis result record."""
    if axis not in AXES:
        raise ValueError("unrecognized axis %r; recognized: %s" % (axis, ", ".join(AXES)))
    ok = fits(available_m, required_m)
    return {
        "axis": axis,
        "required_m": required_m,
        "available_m": available_m,
        "margin_m": available_m - required_m,
        "adequate": ok,
    }


def assess_shielded_enclosure_sizing(enclosure, layout, antenna_type, standoff_m):
    """Full clause 5.2.2.2 facility-adequacy assessment.

    Returns a report: per-axis results, the governing (smallest-margin)
    axis, the quiet-zone check, a findings list and an overall verdict.
    """
    usable = usable_envelope(enclosure)
    footprint = bench_footprint(layout)
    results = [
        axis_result(
            "measurement",
            required_measurement_axis(layout, antenna_type, standoff_m),
            usable["measurement_m"],
        ),
        axis_result("lateral", required_lateral_axis(layout), usable["lateral_m"]),
        axis_result(
            "vertical",
            required_vertical_axis(layout, antenna_type),
            usable["vertical_m"],
        ),
    ]
    findings = []
    for result in results:
        if not result["adequate"]:
            findings.append(
                "%s axis short by %.3f m (needs %.3f m, usable %.3f m)"
                % (
                    result["axis"],
                    result["required_m"] - result["available_m"],
                    result["required_m"],
                    result["available_m"],
                )
            )

    quiet_declared = usable["quiet_zone_diameter_m"] > 0.0
    quiet_ok = True
    if quiet_declared:
        quiet_ok = fits(usable["quiet_zone_diameter_m"], footprint["diagonal_m"])
        if not quiet_ok:
            findings.append(
                "bench footprint diagonal %.3f m exceeds the declared "
                "quiet-zone diameter %.3f m"
                % (footprint["diagonal_m"], usable["quiet_zone_diameter_m"])
            )
    else:
        findings.append("quiet-zone diameter not declared for this enclosure")

    governing = min(results, key=lambda r: r["margin_m"])
    return {
        "usable_envelope_m": {
            "measurement": usable["measurement_m"],
            "lateral": usable["lateral_m"],
            "vertical": usable["vertical_m"],
        },
        "bench_footprint": footprint,
        "axes": results,
        "governing_axis": governing["axis"],
        "governing_margin_m": governing["margin_m"],
        "quiet_zone_declared": quiet_declared,
        "quiet_zone_adequate": quiet_ok and quiet_declared,
        "findings": findings,
        "verdict": "adequate" if not findings else "inadequate",
    }
