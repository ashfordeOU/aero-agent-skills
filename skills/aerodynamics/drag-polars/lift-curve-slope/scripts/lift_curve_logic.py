#!/usr/bin/env python3
"""Lift curve slope estimation logic (common knowledge, deterministic).

Methods (all documented in the skill's Domain quick reference):
- Thin-airfoil theory: section slope a0 = 2 * pi per radian.
- Lifting-line theory (finite wing, span efficiency e):
  a = a0 / (1 + a0 / (pi * e * AR)), which with a0 = 2 * pi and e = 1
  reduces to a = a0 * AR / (AR + 2).
- Simple sweep theory: a_swept = a * cos(sweep), 0 <= sweep < 90 deg.
- Prandtl-Glauert: a_mach = a / sqrt(1 - M^2), 0 <= M < 0.7.
- Lift coefficient: C_L = a * (alpha - alpha_zero), angles in degrees.

All functions are deterministic, stdlib-only, offline. Invalid inputs
raise ValueError. NACA Report 824 (public domain, standards-map.yaml)
supplies section lift data; the 2 * pi thin-airfoil slope is the
theoretical anchor that measured thin sections approach.
"""

import math

SECTION_SLOPE = 2.0 * math.pi  # thin-airfoil theory, per radian
MAX_MACH = 0.7  # Prandtl-Glauert subsonic validity limit
MAX_SWEEP_DEG = 90.0  # cos(sweep) must stay positive


def airfoil_slope(a0=None):
    """Section (2D) lift curve slope per radian.

    Defaults to 2 * pi from thin-airfoil theory. Raises ValueError
    when a0 is not > 0.
    """
    if a0 is None:
        return SECTION_SLOPE
    if a0 <= 0:
        raise ValueError("section slope a0 must be > 0, got %r" % (a0,))
    return float(a0)


def finite_wing_slope(a0, ar, e=1.0):
    """Finite-wing lift curve slope by lifting-line theory.

    a = a0 / (1 + a0 / (pi * e * AR)). For a0 = 2 * pi and e = 1 this
    is a = a0 * AR / (AR + 2). Raises ValueError when ar <= 0 or e is
    not in (0, 1].
    """
    a0 = airfoil_slope(a0)
    if ar <= 0:
        raise ValueError("aspect ratio must be > 0, got %r" % (ar,))
    if e <= 0 or e > 1:
        raise ValueError("span efficiency e must be in (0, 1], got %r" % (e,))
    return a0 / (1.0 + a0 / (math.pi * e * ar))


def sweep_correction(slope, sweep_deg):
    """Simple sweep theory: a_swept = slope * cos(sweep).

    Documented range 0 <= sweep_deg < 90 where cos(sweep) > 0.
    Raises ValueError outside the range.
    """
    if sweep_deg < 0 or sweep_deg >= MAX_SWEEP_DEG:
        raise ValueError(
            "sweep must be in [0, 90) degrees, got %r" % (sweep_deg,)
        )
    return slope * math.cos(math.radians(sweep_deg))


def mach_correction(slope, mach):
    """Prandtl-Glauert: a_mach = slope / sqrt(1 - M^2).

    Documented range 0 <= mach < 0.7, the subsonic validity of the
    correction. Raises ValueError outside the range.
    """
    if mach < 0 or mach >= MAX_MACH:
        raise ValueError("mach must be in [0, 0.7), got %r" % (mach,))
    return slope / math.sqrt(1.0 - mach * mach)


def wing_lift_curve_slope(ar, a0=None, sweep_deg=0.0, mach=0.0, e=1.0):
    """Combined wing lift curve slope per radian.

    Correction order: section slope (thin airfoil, default 2 * pi),
    finite wing (lifting line), sweep (simple sweep theory), Mach
    (Prandtl-Glauert). Raises ValueError on any invalid input through
    the chained helpers.
    """
    a = finite_wing_slope(a0, ar, e)
    a = sweep_correction(a, sweep_deg)
    a = mach_correction(a, mach)
    return a


def lift_coefficient(a, alpha_deg, alpha_zero_deg=0.0, stall_cl=None):
    """Lift coefficient C_L = a * (alpha - alpha_zero).

    Angles in degrees, slope a per radian. Optional stall guard: when
    stall_cl is given and |C_L| exceeds it, the linear model is
    invalid and ValueError is raised. Raises ValueError when a <= 0.
    """
    if a <= 0:
        raise ValueError("lift curve slope must be > 0, got %r" % (a,))
    cl = a * math.radians(alpha_deg - alpha_zero_deg)
    if stall_cl is not None and abs(cl) > abs(stall_cl):
        raise ValueError(
            "alpha %r deg predicts C_L %.4f beyond stall guard %.4f"
            % (alpha_deg, cl, stall_cl)
        )
    return cl
