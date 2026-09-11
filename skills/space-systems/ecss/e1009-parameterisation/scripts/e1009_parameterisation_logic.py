#!/usr/bin/env python3
"""ECSS-E-ST-10-09C §5.4.7 coordinate system parameterisation checks
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
reference-frame specification's parameterisation clause requires that
every coordinate system used in a space-system analysis state its
geometry family (Cartesian, spherical, or cylindrical), a fully
defined origin in the parent frame, an orientation convention (e.g.
ECI, LVLH, body-fixed), and coordinate parameter ranges. Cartesian
systems must use a right-hand axis triad; spherical systems restrict
the radial distance to r ≥ 0, polar angle to [0, π] rad, and azimuth
to [0, 2π) rad; cylindrical systems restrict radial distance to ρ ≥ 0
and azimuth to [0, 2π) rad. This module implements geometry
categorization, origin completeness checking, Cartesian axis-handedness
verification, spherical and cylindrical range validation, orientation-
convention presence checking, and an aggregate parameterisation review.
"""

import math

CS_GEOMETRIES = frozenset({"cartesian", "spherical", "cylindrical"})

_TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Geometry categorization
# ---------------------------------------------------------------------------

def categorize_cs_geometry(geometry):
    """Return the geometry name (one of CS_GEOMETRIES).
    Raises ValueError for an unrecognized geometry type."""
    if geometry not in CS_GEOMETRIES:
        raise ValueError(
            "unrecognized coordinate system geometry %r; expected one of %s"
            % (geometry, sorted(CS_GEOMETRIES))
        )
    return geometry


# ---------------------------------------------------------------------------
# Vector helpers (stdlib only — no numpy)
# ---------------------------------------------------------------------------

def _cross(a, b):
    """3D cross product of sequences a and b."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    """3D dot product of sequences a and b."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _magnitude(v):
    """Euclidean magnitude of a 3-element sequence."""
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


# ---------------------------------------------------------------------------
# Cartesian axis-handedness
# ---------------------------------------------------------------------------

def check_right_hand_rule(x_axis, y_axis, z_axis, tolerance=1e-9):
    """True if x_axis × y_axis is parallel to z_axis within tolerance
    (right-hand convention). Returns False for degenerate (zero-length)
    axes and for left-hand triads."""
    cross_xy = _cross(x_axis, y_axis)
    mag_cross = _magnitude(cross_xy)
    mag_z = _magnitude(z_axis)
    if mag_cross < tolerance or mag_z < tolerance:
        return False
    cross_norm = tuple(c / mag_cross for c in cross_xy)
    z_norm = tuple(c / mag_z for c in z_axis)
    return _dot(cross_norm, z_norm) >= (1.0 - tolerance)


# ---------------------------------------------------------------------------
# Parameter range validation
# ---------------------------------------------------------------------------

def validate_spherical_ranges(r, theta_rad, phi_rad):
    """Return a list of issue strings for out-of-range spherical parameters.
    Valid ranges: r ≥ 0; theta_rad in [0, π]; phi_rad in [0, 2π).
    Raises ValueError for non-numeric inputs."""
    for name, val in (("r", r), ("theta_rad", theta_rad), ("phi_rad", phi_rad)):
        if not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
    issues = []
    if r < 0.0:
        issues.append("r must be >= 0, got %g" % r)
    if not (0.0 <= theta_rad <= math.pi):
        issues.append(
            "theta_rad must be in [0, pi], got %g" % theta_rad
        )
    if not (0.0 <= phi_rad < _TWO_PI):
        issues.append(
            "phi_rad must be in [0, 2*pi), got %g" % phi_rad
        )
    return issues


def validate_cylindrical_ranges(rho, phi_rad, z):
    """Return a list of issue strings for out-of-range cylindrical parameters.
    Valid ranges: rho ≥ 0; phi_rad in [0, 2π). z is unconstrained.
    Raises ValueError for non-numeric inputs."""
    for name, val in (("rho", rho), ("phi_rad", phi_rad), ("z", z)):
        if not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
    issues = []
    if rho < 0.0:
        issues.append("rho must be >= 0, got %g" % rho)
    if not (0.0 <= phi_rad < _TWO_PI):
        issues.append(
            "phi_rad must be in [0, 2*pi), got %g" % phi_rad
        )
    return issues


def validate_cartesian_ranges(x, y, z):
    """Return a list of issue strings for non-finite Cartesian coordinates.
    Raises ValueError for non-numeric inputs."""
    for name, val in (("x", x), ("y", y), ("z", z)):
        if not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
    issues = []
    for name, val in (("x", x), ("y", y), ("z", z)):
        if not math.isfinite(val):
            issues.append("%s is not finite: %g" % (name, val))
    return issues


# ---------------------------------------------------------------------------
# Per-coordinate-system violation checks
# ---------------------------------------------------------------------------

def origin_violations(cs_id, origin):
    """Violation list for origin definition.
    origin must be a dict with finite numeric 'x', 'y', 'z' keys.
    Missing, non-numeric, or non-finite components are each flagged."""
    if not isinstance(origin, dict):
        return [{"issue": "origin_not_a_dict", "cs_id": cs_id}]
    findings = []
    for component in ("x", "y", "z"):
        if component not in origin:
            findings.append(
                {"issue": "origin_component_missing", "cs_id": cs_id,
                 "component": component}
            )
        else:
            val = origin[component]
            if not isinstance(val, (int, float)):
                findings.append(
                    {"issue": "origin_component_non_numeric", "cs_id": cs_id,
                     "component": component}
                )
            elif not math.isfinite(val):
                findings.append(
                    {"issue": "origin_component_non_finite", "cs_id": cs_id,
                     "component": component, "value": val}
                )
    return findings


def axis_handedness_violations(cs_id, x_axis, y_axis, z_axis):
    """Violation list for Cartesian axis handedness.
    Returns a finding when the three axes do not form a right-hand triad."""
    if not check_right_hand_rule(x_axis, y_axis, z_axis):
        return [{"issue": "axes_not_right_hand_triad", "cs_id": cs_id}]
    return []


def orientation_convention_violations(cs_id, convention):
    """Violation list for orientation convention documentation.
    A missing or empty convention string is flagged per §5.4.7."""
    if not convention:
        return [{"issue": "orientation_convention_undocumented", "cs_id": cs_id}]
    return []


# ---------------------------------------------------------------------------
# Aggregate review
# ---------------------------------------------------------------------------

def parameterise_review(cs_def):
    """Full §5.4.7 parameterisation review for one coordinate system.

    cs_def fields:
      "cs_id"               : str — identifier
      "geometry"            : str — "cartesian" | "spherical" | "cylindrical"
      "origin"              : dict with numeric x, y, z components
      "orientation_convention": str | None
      For cartesian only:
        "x_axis", "y_axis", "z_axis": each a 3-element list of floats

    Returns {"origin": [...], "axes": [...], "convention": [...]},
    each a violation list. Raises ValueError for an unrecognized geometry."""
    cs_id = cs_def["cs_id"]
    geometry = categorize_cs_geometry(cs_def["geometry"])

    origin_v = origin_violations(cs_id, cs_def.get("origin", {}))
    convention_v = orientation_convention_violations(
        cs_id, cs_def.get("orientation_convention")
    )

    if geometry == "cartesian":
        x_axis = cs_def.get("x_axis", [0.0, 0.0, 0.0])
        y_axis = cs_def.get("y_axis", [0.0, 0.0, 0.0])
        z_axis = cs_def.get("z_axis", [0.0, 0.0, 0.0])
        axes_v = axis_handedness_violations(cs_id, x_axis, y_axis, z_axis)
    else:
        axes_v = []

    return {"origin": origin_v, "axes": axes_v, "convention": convention_v}


def is_parameterisation_valid(review):
    """True when every violation list in the parameterise_review result
    is empty — the coordinate system satisfies §5.4.7 parameterisation
    requirements for this assessment."""
    return all(len(v) == 0 for v in review.values())
