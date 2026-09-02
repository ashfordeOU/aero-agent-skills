#!/usr/bin/env python3
"""Aileron reversal logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context, cs-25 mirrors it): FAR-25.629 requires the
airplane to be free from control reversal within the design envelope.
The classical simplified aeroelastic estimate (NACA TR-799 lineage)
relates the reversal dynamic pressure to the wing torsional stiffness
about the elastic axis: q_rev = k_t / (C_l_alpha * eta * S * c * e),
with k_t in N m / rad, C_l_alpha the lift curve slope per radian, eta
the aileron effectiveness factor (0 < eta <= 1), S the wing area in
m^2, c the mean chord in m, and e the elastic axis to aerodynamic
center offset in m. The reversal true airspeed is
V_rev = sqrt(2 q_rev / rho) with rho the air density in kg/m^3. The
aileron effectiveness fraction at a flight dynamic pressure is
1 - q / q_rev: unity at zero speed, zero at the reversal point, and
negative beyond it (control reversal). Units: dynamic pressure in Pa,
stiffness in N m / rad, angles in radians.
"""


def reversal_dynamic_pressure(k_t, cl_alpha, eta, s, c, e):
    """Reversal dynamic pressure q_rev = k_t / (C_l_alpha * eta * S * c * e).

    k_t is the wing torsional stiffness about the elastic axis in
    N m / rad, cl_alpha the lift curve slope per radian, eta the
    dimensionless aileron effectiveness factor, s the wing area in
    m^2, c the mean chord in m, and e the elastic axis to aerodynamic
    center offset in m (positive when the aerodynamic center lies aft
    of the elastic axis). Returns the reversal dynamic pressure in Pa.
    Raises ValueError on non-positive stiffness, lift slope, area,
    chord, or offset, and on an effectiveness factor outside (0, 1].
    """
    if k_t <= 0:
        raise ValueError("torsional stiffness must be > 0 N m / rad, got %r" % (k_t,))
    if cl_alpha <= 0:
        raise ValueError("lift curve slope must be > 0 per radian, got %r" % (cl_alpha,))
    if not (0 < eta <= 1):
        raise ValueError("aileron effectiveness factor must be in (0, 1], got %r" % (eta,))
    if s <= 0:
        raise ValueError("wing area must be > 0 m^2, got %r" % (s,))
    if c <= 0:
        raise ValueError("mean chord must be > 0 m, got %r" % (c,))
    if e <= 0:
        raise ValueError("elastic axis to aerodynamic center offset must be > 0 m, got %r" % (e,))
    return k_t / (cl_alpha * eta * s * c * e)


def reversal_speed(q_rev, rho):
    """Reversal true airspeed V_rev = sqrt(2 q_rev / rho) in m/s.

    q_rev is the reversal dynamic pressure in Pa and rho the air
    density in kg/m^3. Raises ValueError on non-positive inputs.
    """
    if q_rev <= 0:
        raise ValueError("dynamic pressure must be > 0 Pa, got %r" % (q_rev,))
    if rho <= 0:
        raise ValueError("air density must be > 0 kg/m^3, got %r" % (rho,))
    return (2.0 * q_rev / rho) ** 0.5


def reversal_speed_from_stiffness(k_t, cl_alpha, eta, s, c, e, rho):
    """Reversal true airspeed from the stiffness inputs and air density.

    Combines reversal_dynamic_pressure and reversal_speed in one step:
    V_rev = sqrt(2 k_t / (C_l_alpha * eta * S * c * e * rho)) in m/s.
    Validates every input through the two underlying functions.
    """
    q_rev = reversal_dynamic_pressure(k_t, cl_alpha, eta, s, c, e)
    return reversal_speed(q_rev, rho)


def aileron_effectiveness(q, q_rev):
    """Aileron effectiveness fraction 1 - q / q_rev at a flight q.

    Unity at zero dynamic pressure, zero at the reversal point, and
    negative beyond it (control reversal). Raises ValueError on a
    negative flight dynamic pressure or a non-positive q_rev.
    """
    if q < 0:
        raise ValueError("flight dynamic pressure must be >= 0 Pa, got %r" % (q,))
    if q_rev <= 0:
        raise ValueError("reversal dynamic pressure must be > 0 Pa, got %r" % (q_rev,))
    return 1.0 - q / q_rev


def is_reversed(q, q_rev):
    """True when the flight dynamic pressure exceeds the reversal value.

    The strict comparison means the boundary q == q_rev (effectiveness
    exactly zero) is not yet reversed. Raises ValueError on a negative
    flight dynamic pressure or a non-positive q_rev.
    """
    if q < 0:
        raise ValueError("flight dynamic pressure must be >= 0 Pa, got %r" % (q,))
    if q_rev <= 0:
        raise ValueError("reversal dynamic pressure must be > 0 Pa, got %r" % (q_rev,))
    return q > q_rev
