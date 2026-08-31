#!/usr/bin/env python3
"""Stall speed determination logic (paraphrase, common flight-test
methodology).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25/CS-25 stall speed practice uses the
reference stall speed Vs1g derived from the wing loading and the
maximum lift coefficient, weight-corrected with the square root of
the weight ratio, and compared to the current speed as a stall
margin.
"""

import math


def vs1g(wing_loading_n_m2, rho_kg_m3, cl_max):
    """Reference stall speed Vs1g in m/s.

    Vs1g = sqrt(2 * (W/S) / (rho * CLmax)), where W/S is the wing
    loading in N/m^2, rho the air density in kg/m^3, and CLmax the
    maximum lift coefficient. Raises ValueError on non-positive wing
    loading, air density, or lift coefficient.
    """
    if wing_loading_n_m2 <= 0:
        raise ValueError("wing loading must be > 0, got %r" % (wing_loading_n_m2,))
    if rho_kg_m3 <= 0:
        raise ValueError("air density must be > 0, got %r" % (rho_kg_m3,))
    if cl_max <= 0:
        raise ValueError("maximum lift coefficient must be > 0, got %r" % (cl_max,))
    return math.sqrt(2.0 * wing_loading_n_m2 / (rho_kg_m3 * cl_max))


def weight_corrected_stall_speed(vs_ref, w_ref, w_new):
    """Stall speed corrected for a weight change, in m/s.

    V_new = vs_ref * sqrt(w_new / w_ref); stall speed scales with the
    square root of the weight ratio. Raises ValueError on a
    non-positive reference stall speed or either weight.
    """
    if vs_ref <= 0:
        raise ValueError("reference stall speed must be > 0, got %r" % (vs_ref,))
    if w_ref <= 0:
        raise ValueError("reference weight must be > 0, got %r" % (w_ref,))
    if w_new <= 0:
        raise ValueError("new weight must be > 0, got %r" % (w_new,))
    return vs_ref * math.sqrt(w_new / float(w_ref))


def stall_margin(vs, v_current):
    """Stall margin: (v_current - vs) / vs.

    A negative margin is allowed and meaningful: it means the current
    speed is below the reference stall speed. Raises ValueError on a
    non-positive stall speed or a negative current speed.
    """
    if vs <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (vs,))
    if v_current < 0:
        raise ValueError("current speed must be >= 0, got %r" % (v_current,))
    return (v_current - vs) / vs
