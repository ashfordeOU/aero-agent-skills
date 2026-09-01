#!/usr/bin/env python3
"""Stick fixed pitch trim analysis logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the trim lift coefficient in level flight is
CL_trim = 2W / (rho V^2 S). The pitching moment model is Cm = Cm0 +
Cm_alpha * alpha + Cm_delta_e * de and the trimmed condition closes
the moment at zero. With the simplified lift curve CL = CL_alpha *
alpha, the angle of attack at trim is alpha_trim = CL_trim /
CL_alpha and the elevator deflection to trim is de_trim = -(Cm0 +
Cm_alpha * alpha_trim) / Cm_delta_e. The trim speed for a given
trim lift coefficient is V_trim = sqrt(2W / (rho S CL_trim)). Units:
weight in newtons, density in kg/m^3, speed in m/s, wing area in
m^2, angles in radians.
"""

import math


def trim_lift_coefficient(weight_n, rho, v, s):
    """Trim lift coefficient in level flight: 2W / (rho V^2 S).

    Raises ValueError on non-positive inputs.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    if rho <= 0:
        raise ValueError("density must be > 0 kg/m^3, got %r" % (rho,))
    if v <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v,))
    if s <= 0:
        raise ValueError("wing area must be > 0 m^2, got %r" % (s,))
    return 2.0 * weight_n / (rho * v * v * s)


def elevator_deflection_to_trim(cm0, cm_alpha, cl_alpha, cl_trim, cm_delta_e):
    """Elevator deflection in radians required to trim the moment.

    Uses the simplified lift curve CL = CL_alpha * alpha, so
    alpha_trim = CL_trim / CL_alpha and Cm = 0 gives de_trim =
    -(Cm0 + Cm_alpha * alpha_trim) / Cm_delta_e. Raises ValueError
    on non-positive lift slope or zero elevator effectiveness.
    """
    if cl_alpha <= 0:
        raise ValueError("lift slope must be > 0, got %r" % (cl_alpha,))
    if cm_delta_e == 0:
        raise ValueError("elevator effectiveness must be non-zero, got %r" % (cm_delta_e,))
    alpha_trim = cl_trim / cl_alpha
    return -(cm0 + cm_alpha * alpha_trim) / cm_delta_e


def trim_speed(weight_n, rho, s, cl_trim):
    """Trim speed in m/s for a given trim lift coefficient.

    Raises ValueError on non-positive weight, density, wing area,
    or trim lift coefficient.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    if rho <= 0:
        raise ValueError("density must be > 0 kg/m^3, got %r" % (rho,))
    if s <= 0:
        raise ValueError("wing area must be > 0 m^2, got %r" % (s,))
    if cl_trim <= 0:
        raise ValueError("trim lift coefficient must be > 0, got %r" % (cl_trim,))
    return math.sqrt(2.0 * weight_n / (rho * s * cl_trim))


def is_trimmed(cm_total, tol=1e-6):
    """Trimmed verdict: True when the total pitching moment is
    within the tolerance of zero."""
    return abs(cm_total) <= tol
