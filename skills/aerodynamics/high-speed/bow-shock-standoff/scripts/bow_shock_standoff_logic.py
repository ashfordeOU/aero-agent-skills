"""Billig-form bow-shock standoff correlations for blunt noses.

Classical detached bow-shock standoff estimates on the stagnation
streamline ahead of a blunt nose in supersonic and hypersonic flow,
gamma = 1.4. The sphere form applies to an axisymmetric nose and the
circular cylinder form to a two-dimensional leading edge. The
correlations are the standard Billig-form exponentials:

  sphere   Delta / R = 0.143 * exp(3.24 / M^2)
  cylinder Delta / R = 0.386 * exp(4.67 / M^2)

with M the freestream Mach number, R the nose radius and Delta the
standoff distance of the detached shock ahead of the stagnation point.
The forms are documented for freestream Mach above about 1.5; the ratio
grows without bound as M approaches 1, where no detached shock exists.
Pure stdlib, deterministic.
"""

import math

SPHERE_COEF = 0.143
SPHERE_EXP = 3.24
CYL_COEF = 0.386
CYL_EXP = 4.67

VALID_BODIES = ("sphere", "cylinder")
VALIDITY_MACH_FLOOR = 1.5  # documented lower freestream Mach floor


def _check_mach(mach):
    """Reject Mach numbers at or below 1 (no detached bow shock there)."""
    if mach <= 1.0:
        raise ValueError(
            "mach must exceed 1.0 for a detached bow shock; got %s" % mach
        )


def _check_radius(radius):
    """Reject non-positive nose radii."""
    if radius <= 0.0:
        raise ValueError("nose radius must be positive; got %s" % radius)


def _check_body(body):
    """Reject body strings other than 'sphere' and 'cylinder'."""
    if body not in VALID_BODIES:
        raise ValueError(
            "body must be 'sphere' or 'cylinder'; got %r" % body
        )


def standoff_ratio(mach, body="sphere"):
    """Return the standoff ratio Delta / R on the stagnation streamline.

    Billig-form correlation at freestream Mach mach for the given body
    ('sphere' or 'cylinder'). Raises ValueError when mach <= 1 or the
    body string is unknown.
    """
    _check_mach(mach)
    _check_body(body)
    if body == "sphere":
        return SPHERE_COEF * math.exp(SPHERE_EXP / (mach * mach))
    return CYL_COEF * math.exp(CYL_EXP / (mach * mach))


def standoff_distance(mach, radius, body="sphere"):
    """Return the physical standoff distance Delta in meters.

    Delta = (Delta / R) * R, so the distance scales linearly with the
    nose radius. Raises ValueError when mach <= 1, radius <= 0, or the
    body string is unknown.
    """
    _check_mach(mach)
    _check_radius(radius)
    _check_body(body)
    return standoff_ratio(mach, body) * radius


def standoff_report(mach, radius, body="sphere"):
    """Return the standoff summary dict with the trend sanity flags.

    Keys: ratio (Delta / R), distance (Delta in meters),
    sphere_cylinder_order (True when the cylinder ratio exceeds the
    sphere ratio at this Mach), decreasing_with_mach (True when the
    ratio at mach * 1.1 is smaller than the ratio at mach). Raises
    ValueError as documented for standoff_ratio and standoff_distance.
    """
    _check_mach(mach)
    _check_radius(radius)
    _check_body(body)
    ratio = standoff_ratio(mach, body)
    return {
        "ratio": ratio,
        "distance": ratio * radius,
        "sphere_cylinder_order": (
            standoff_ratio(mach, "cylinder") > standoff_ratio(mach, "sphere")
        ),
        "decreasing_with_mach": standoff_ratio(mach * 1.1, body) < ratio,
    }
