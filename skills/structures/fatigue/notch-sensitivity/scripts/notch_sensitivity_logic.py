#!/usr/bin/env python3
"""Notch sensitivity and fatigue notch factor math (stdlib only).

Computes the stress concentration factor Kt for hole geometry, the
fatigue notch factor Kf by the Peterson and Neuber methods from the
notch root radius and material constants, the notch sensitivity
q = (Kf - 1) / (Kt - 1), and the effective stress amplitude that
enters the endurance check of a notched aerospace part.

Conventions: all lengths share one unit (mm is the common choice for
the material constants); all stresses share one unit. Kt is the
elastic stress concentration factor of the geometric feature, always
>= 1. Kf is the fatigue notch factor, between 1 and Kt for a positive
notch sensitivity. q ranges from 0 (no fatigue reduction, Kf = 1) to
1 (full sensitivity, Kf = Kt).

Methods:
  elliptical hole in infinite plate: Kt = 1 + 2a/b with a the semi
  axis perpendicular to the load and b the semi axis parallel to it
  (a = b for a circular hole gives Kt = 3).
  circular hole in finite width plate: Kt = 3 - 3.14(d/w) +
  3.667(d/w)^2 - 1.527(d/w)^3, a curve fit of the Howland solution
  valid for d/w <= 0.5, with d the hole diameter and w the plate
  width.
  Peterson: Kf = 1 + (Kt - 1) / (1 + a / rho), with a the Peterson
  material constant and rho the notch root radius.
  Neuber: Kf = 1 + (Kt - 1) / (1 + sqrt(a' / rho)), with a' the
  Neuber material constant and rho the notch root radius.

Generic mechanical engineering methodology; FAR-25 / CS-25 are cited
reference-only in the skill, nothing here quotes either regulation.

Contract exercised by scripts/test_notch_sensitivity.py.
"""

import math

PETERSON_REFERENCE_STRENGTH = 2070.0  # MPa, steel strength at which a = 0.0254 mm
PETERSON_REFERENCE_CONSTANT = 0.0254  # mm


def _require_positive(value, label):
    """Raise ValueError unless the value is strictly positive."""
    if not value > 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))


def kt_elliptical_hole(a, b):
    """Return the stress concentration factor Kt for an elliptical hole
    in an infinite plate under uniaxial tension.

    Kt = 1 + 2a/b with a the semi axis perpendicular to the load and b
    the semi axis parallel to the load. A circular hole (a = b) gives
    the classical Kt = 3.

    Raises ValueError for a non-positive a or b.
    """
    _require_positive(a, "semi axis a")
    _require_positive(b, "semi axis b")
    return 1.0 + 2.0 * a / b


def kt_circular_hole_finite_width(d, w):
    """Return the stress concentration factor Kt for a circular hole of
    diameter d in a plate of width w under uniaxial tension.

    Kt = 3 - 3.14(d/w) + 3.667(d/w)^2 - 1.527(d/w)^3, a curve fit of
    the Howland solution valid for d/w <= 0.5. As d/w tends to zero
    the factor tends to the infinite plate value of 3.

    Raises ValueError for a non-positive d, a non-positive w, or d >= w.
    """
    _require_positive(d, "hole diameter d")
    _require_positive(w, "plate width w")
    if d >= w:
        raise ValueError("hole diameter d must be < plate width w, got d=%r w=%r" % (d, w))
    x = d / w
    return 3.0 - 3.14 * x + 3.667 * x * x - 1.527 * x * x * x


def peterson_material_constant(sut_mpa):
    """Return the Peterson material constant a in mm from the ultimate
    tensile strength Sut in MPa.

    a = 0.0254 * (2070 / Sut)^1.8, the steel correlation: at Sut = 2070
    MPa the constant is 0.0254 mm (0.001 inch), and it grows as the
    strength falls. Stronger material, smaller a, sharper notch that
    still carries full fatigue sensitivity.

    Raises ValueError for a non-positive Sut.
    """
    _require_positive(sut_mpa, "ultimate tensile strength Sut")
    return PETERSON_REFERENCE_CONSTANT * (
        (PETERSON_REFERENCE_STRENGTH / sut_mpa) ** 1.8
    )


def peterson_fatigue_notch_factor(kt, rho, a):
    """Return the fatigue notch factor Kf by the Peterson method.

    Kf = 1 + (Kt - 1) / (1 + a / rho), with a the Peterson material
    constant and rho the notch root radius in the same length unit.
    A blunt notch (large rho) drives Kf toward Kt; a sharp notch
    (small rho) drives Kf toward 1 because only a thin surface layer
    carries the peak stress.

    Raises ValueError for kt < 1, a non-positive rho, or a non-positive a.
    """
    if kt < 1.0:
        raise ValueError("Kt must be >= 1, got %r" % (kt,))
    _require_positive(rho, "notch root radius rho")
    _require_positive(a, "Peterson material constant a")
    return 1.0 + (kt - 1.0) / (1.0 + a / rho)


def neuber_fatigue_notch_factor(kt, rho, a_prime):
    """Return the fatigue notch factor Kf by the Neuber method.

    Kf = 1 + (Kt - 1) / (1 + sqrt(a' / rho)), with a' the Neuber
    material constant and rho the notch root radius in the same length
    unit. The square root makes the sensitivity fall more slowly with
    root radius than the Peterson form; a' near 0.25 mm is typical for
    steel (sqrt(a') near 0.5 mm^0.5).

    Raises ValueError for kt < 1, a non-positive rho, or a non-positive
    a_prime.
    """
    if kt < 1.0:
        raise ValueError("Kt must be >= 1, got %r" % (kt,))
    _require_positive(rho, "notch root radius rho")
    _require_positive(a_prime, "Neuber material constant a'")
    return 1.0 + (kt - 1.0) / (1.0 + math.sqrt(a_prime / rho))


def notch_sensitivity(kt, kf):
    """Return the notch sensitivity q = (Kf - 1) / (Kt - 1).

    q ranges from 0 (Kf = 1, no fatigue reduction) to 1 (Kf = Kt, full
    sensitivity). The value quantifies how much of the elastic
    concentration actually affects fatigue strength.

    Raises ValueError for kt <= 1 or a kf outside [1, kt].
    """
    if kt <= 1.0:
        raise ValueError("Kt must be > 1 for a sensitivity, got %r" % (kt,))
    if not 1.0 <= kf <= kt:
        raise ValueError("Kf must lie in [1, Kt], got kf=%r kt=%r" % (kf, kt))
    return (kf - 1.0) / (kt - 1.0)


def effective_stress_amplitude(kf, sigma_nominal):
    """Return the effective stress amplitude Kf * sigma_nominal that the
    endurance check must use for the notched part.

    The nominal amplitude at the section is amplified by the fatigue
    notch factor before comparison with the endurance limit.

    Raises ValueError for a non-positive sigma_nominal or kf < 1.
    """
    if kf < 1.0:
        raise ValueError("Kf must be >= 1, got %r" % (kf,))
    _require_positive(sigma_nominal, "nominal stress amplitude")
    return kf * sigma_nominal


def max_stress_at_notch(kt, sigma_nominal):
    """Return the elastic peak stress Kt * sigma_nominal at the notch
    root. This is the local stress the elastic stress concentration
    produces; the fatigue check instead uses Kf * sigma_nominal.

    Raises ValueError for kt < 1 or a non-positive sigma_nominal.
    """
    if kt < 1.0:
        raise ValueError("Kt must be >= 1, got %r" % (kt,))
    _require_positive(sigma_nominal, "nominal stress")
    return kt * sigma_nominal
