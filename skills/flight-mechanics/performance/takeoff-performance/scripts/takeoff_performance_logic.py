#!/usr/bin/env python3
"""Takeoff performance logic (paraphrase, common flight-mechanics
methodology).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25 and CS-25 require transport aeroplanes to
demonstrate takeoff performance, and the standard field-length
estimate derives the takeoff ground roll from the weight, wing area,
thrust, air density, and maximum lift coefficient. The stall speed
comes from the wing loading (weight per wing area) and the maximum
lift coefficient; the lift-off speed is the stall speed scaled by a
factor of 1.2 for transport operation, and the ground roll distance is
the standard estimate with rolling friction subtracted from the net
thrust. All inputs are SI: weight and thrust in newtons, wing area in
square metres, density in kg/m^3, speeds in m/s, g0 = 9.80665 m/s^2.
"""

import math


def stall_speed(wing_loading_n_m2, rho_kg_m3, cl_max):
    """Stall speed from wing loading, air density, and Cl_max (m/s).

    V_s = sqrt(2 * W/S / (rho * Cl_max)). Raises ValueError when any
    input is non-positive.
    """
    if wing_loading_n_m2 <= 0:
        raise ValueError("wing loading must be > 0, got %r" % (wing_loading_n_m2,))
    if rho_kg_m3 <= 0:
        raise ValueError("density must be > 0, got %r" % (rho_kg_m3,))
    if cl_max <= 0:
        raise ValueError("cl_max must be > 0, got %r" % (cl_max,))
    return math.sqrt(2.0 * wing_loading_n_m2 / (rho_kg_m3 * cl_max))


def stall_speed_from_weight(weight_n, wing_area_m2, rho_kg_m3, cl_max):
    """Stall speed from weight, wing area, density, and Cl_max (m/s).

    V_s = sqrt(2 * W / (rho * S * Cl_max)). Raises ValueError when any
    input is non-positive.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be > 0, got %r" % (wing_area_m2,))
    if rho_kg_m3 <= 0:
        raise ValueError("density must be > 0, got %r" % (rho_kg_m3,))
    if cl_max <= 0:
        raise ValueError("cl_max must be > 0, got %r" % (cl_max,))
    return math.sqrt(2.0 * weight_n / (rho_kg_m3 * wing_area_m2 * cl_max))


def liftoff_speed(vs_ms, factor=1.2):
    """Lift-off speed from the stall speed and the liftoff factor (m/s).

    V_LOF = factor * V_s, with the transport convention factor 1.2.
    Raises ValueError when vs_ms is non-positive or the factor is below
    1.0 (no certification credit below the stall).
    """
    if vs_ms <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (vs_ms,))
    if factor < 1.0:
        raise ValueError("liftoff factor must be >= 1.0, got %r" % (factor,))
    return factor * vs_ms


def ground_roll_distance(weight_n, wing_area_m2, thrust_n, rho_kg_m3,
                         cl_max, mu=0.03, g0=9.80665):
    """Takeoff ground roll distance (m).

    S_g = 1.44 * W^2 / (g0 * rho * S * Cl_max * (T - mu * W)), the
    standard estimate with rolling friction mu acting against the
    thrust. Raises ValueError when any input is non-positive, mu is
    outside [0, 1), or the thrust does not exceed the rolling friction
    drag (mu * W) so the aircraft cannot accelerate.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be > 0, got %r" % (wing_area_m2,))
    if thrust_n <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust_n,))
    if rho_kg_m3 <= 0:
        raise ValueError("density must be > 0, got %r" % (rho_kg_m3,))
    if cl_max <= 0:
        raise ValueError("cl_max must be > 0, got %r" % (cl_max,))
    if not (0.0 <= mu < 1.0):
        raise ValueError("rolling friction mu must be in [0, 1), got %r" % (mu,))
    if thrust_n <= mu * weight_n:
        raise ValueError(
            "thrust %r must exceed rolling friction %r" % (thrust_n, mu * weight_n)
        )
    return (1.44 * weight_n ** 2 /
            (g0 * rho_kg_m3 * wing_area_m2 * cl_max *
             (thrust_n - mu * weight_n)))
