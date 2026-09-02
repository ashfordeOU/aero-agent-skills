#!/usr/bin/env python3
"""Thermal stress analysis of constrained aerospace structures (paraphrase, not copy).

Common-knowledge summary of thermal stress in statically constrained
structures (Bruhn, Niu, Timoshenko; standards-map.yaml far-25 gated
false, reference-only): a member whose free thermal expansion is fully
blocked develops the axial thermal stress

    sigma = E * alpha * dT

where E is the Young's modulus, alpha the coefficient of thermal
expansion and dT the temperature change; the free thermal strain is

    eps = alpha * dT

A negative dT (cooling) reverses the sign of the stress; an
unrestrained member carries no thermal stress at all.

A bonded bimetallic strip of two layers with different coefficients
bends under a temperature change. The layers share the interface
strain, so an equal and opposite axial force per unit width P and a
common curvature kappa develop from the compatibility and moment
equilibrium

    kappa = (alpha2 - alpha1) * dT /
            ( (t1 + t2)/2 + 2*(E1*I1 + E2*I2)/(t1 + t2)
              * (1/(E1*t1) + 1/(E2*t2)) )
    P     = 2 * kappa * (E1*I1 + E2*I2) / (t1 + t2)

with I_i = width * t_i^3 / 12. For equal thicknesses and equal moduli
this reduces to kappa = 1.5 * (alpha2 - alpha1) * dT / (t1 + t2) and
a layer stress of magnitude E * (alpha2 - alpha1) * dT / 8.

A plate constrained against in-plane expansion (a long skin panel
held between stiffeners) develops the compression E * alpha * dT
under a temperature rise and buckles when that stress reaches the
plate critical stress, so the critical temperature rise is

    dT_cr = k * pi^2 / (12 * (1 - nu^2) * alpha) * (t / b)^2

with k the plate buckling coefficient (4.0 for a simply supported
long plate, 6.97 for a clamped long plate). Only the Python standard
library is used.

Worked anchors (verified by running this module): E = 70 GPa,
alpha = 23e-6 1/K and dT = 100 K give sigma = 161 MPa and a free
strain of 2300 microstrain; a bimetallic strip of steel (alpha =
11e-6 1/K) and aluminum (alpha = 23e-6 1/K), each 1 mm thick with
E = 70 GPa, at dT = 100 K bends to kappa = 0.9 1/m with a layer
stress of 10.5 MPa; doubling the aluminum modulus to 140 GPa gives
kappa = 0.8727 1/m and a layer stress of 15.27 MPa; a 2 mm aluminum
skin on 150 mm stiffener pitch with E = 70 GPa, alpha = 23e-6 1/K and
nu = 0.33 has a critical temperature rise of 28.54 K.

Units: SI throughout. E in Pa, alpha in 1/K, dT in K, t and b in m,
stresses in Pa, curvature in 1/m, force per unit width in N/m. One
unit convention, no mixing.
"""

import math

_PI2 = math.pi * math.pi


def _check_positive(value, name):
    """Return float(value) after checking it is a positive finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return value


def _check_poisson(nu):
    """Validate the Poisson ratio: a finite number in [0, 0.5)."""
    if isinstance(nu, bool) or not isinstance(nu, (int, float)):
        raise ValueError("nu must be a number, got %r" % (nu,))
    nu = float(nu)
    if not math.isfinite(nu):
        raise ValueError("nu must be finite, got %r" % (nu,))
    if nu < 0.0 or nu >= 0.5:
        raise ValueError("nu must be in [0, 0.5), got %r" % (nu,))
    return nu


def _check_dT(dT):
    """Validate the temperature change: a finite number of any sign."""
    if isinstance(dT, bool) or not isinstance(dT, (int, float)):
        raise ValueError("dT must be a number, got %r" % (dT,))
    dT = float(dT)
    if not math.isfinite(dT):
        raise ValueError("dT must be finite, got %r" % (dT,))
    return dT


def free_thermal_strain(alpha, dT):
    """Free thermal strain eps = alpha * dT of an unrestrained member.

    Worked anchor: alpha = 23e-6 1/K and dT = 100 K give
    eps = 2.3e-3 (2300 microstrain).

    Raises ValueError for a non-positive alpha or a non-finite dT.
    """
    a = _check_positive(alpha, "alpha")
    d = _check_dT(dT)
    return a * d


def constrained_thermal_stress(E, alpha, dT):
    """Thermal stress sigma = E * alpha * dT of a fully constrained member.

    The free expansion is blocked in the load direction. A positive dT
    (heating) gives compression, a negative dT (cooling) tension.

    Worked anchor: E = 70 GPa, alpha = 23e-6 1/K and dT = 100 K give
    sigma = 161 MPa; dT = 0 gives 0.

    Raises ValueError for non-positive E or alpha or a non-finite dT.
    """
    e = _check_positive(E, "E")
    a = _check_positive(alpha, "alpha")
    d = _check_dT(dT)
    return e * a * d


def thermal_stress_check(E, alpha, dT, allowable_stress):
    """Complete thermal stress margin check of a constrained member.

    Returns a dict with the thermal stress, the free thermal strain,
    the margin of safety allowable / |sigma| - 1 (infinite at dT = 0)
    and the acceptable verdict. The margin uses the magnitude of the
    stress because the allowable is a magnitude and the sign only
    tells tension from compression.

    Worked anchor: E = 70 GPa, alpha = 23e-6 1/K, dT = 100 K and an
    allowable of 250 MPa give sigma = 161 MPa, margin = 0.553 and
    acceptable = True.

    Raises ValueError for non-positive E, alpha or allowable_stress or
    a non-finite dT.
    """
    e = _check_positive(E, "E")
    a = _check_positive(alpha, "alpha")
    d = _check_dT(dT)
    allow = _check_positive(allowable_stress, "allowable_stress")
    sigma = e * a * d
    eps = a * d
    if abs(sigma) == 0.0:
        margin = float("inf")
        acceptable = True
    else:
        margin = allow / abs(sigma) - 1.0
        acceptable = abs(sigma) <= allow
    return {
        "thermal_stress": sigma,
        "thermal_strain": eps,
        "margin_of_safety": margin,
        "acceptable": acceptable,
    }


def bimetallic_strip(E1, E2, alpha1, alpha2, t1, t2, dT, width=1.0):
    """Bimetallic strip thermal stress balance for two bonded layers.

    Solves the interface strain compatibility and the moment
    equilibrium of the two layers per unit width. Returns a dict with
    the curvature kappa (1/m), the interface force per unit width P
    (N/m) and the two layer stresses sigma_1 and sigma_2 (Pa). The
    layer with the higher coefficient is compressed and sits on the
    concave side.

    Worked anchors: steel (alpha 11e-6 1/K) on aluminum (alpha
    23e-6 1/K), each 1 mm thick with E = 70 GPa, at dT = 100 K and
    width 1 m give kappa = 0.9 1/m, P = 10500 N/m and layer stresses
    of 10.5 MPa and -10.5 MPa. With the aluminum modulus raised to
    140 GPa, kappa = 0.8727 1/m and the layer stresses are 15.27 MPa.

    Raises ValueError for non-positive moduli, coefficients,
    thicknesses or width, or a non-finite dT.
    """
    e1 = _check_positive(E1, "E1")
    e2 = _check_positive(E2, "E2")
    a1 = _check_positive(alpha1, "alpha1")
    a2 = _check_positive(alpha2, "alpha2")
    th1 = _check_positive(t1, "t1")
    th2 = _check_positive(t2, "t2")
    w = _check_positive(width, "width")
    d = _check_dT(dT)
    i1 = w * th1 ** 3 / 12.0
    i2 = w * th2 ** 3 / 12.0
    total = th1 + th2
    denom = (
        total / 2.0
        + 2.0 * (e1 * i1 + e2 * i2) / total
        * (1.0 / (e1 * th1 * w) + 1.0 / (e2 * th2 * w))
    )
    kappa = (a2 - a1) * d / denom
    force = 2.0 * kappa * (e1 * i1 + e2 * i2) / total
    return {
        "curvature": kappa,
        "force_per_width": force,
        "sigma_1": force / (th1 * w),
        "sigma_2": -force / (th2 * w),
    }


def thermal_buckling_critical_dT(E, alpha, nu, t, b, coefficient=4.0):
    """Critical temperature rise of a plate constrained against in-plane expansion.

    dT_cr = k * pi^2 / (12 * (1 - nu^2) * alpha) * (t / b)^2, derived
    by setting the thermal compression E * alpha * dT equal to the
    plate critical stress. k is the plate buckling coefficient: 4.0
    for a simply supported long plate, 6.97 for a clamped long plate.
    The restraint model is the long panel held in one direction; a
    fully biaxial restraint lowers the critical temperature rise by
    the factor (1 - nu).

    Worked anchor: E = 70 GPa, alpha = 23e-6 1/K, nu = 0.33, t = 2 mm,
    b = 150 mm and k = 4.0 give dT_cr = 28.54 K; doubling t to 3 mm
    gives 64.21 K; k = 6.97 gives 49.72 K.

    Raises ValueError for non-positive E, alpha, t, b or coefficient,
    or an invalid Poisson ratio.
    """
    e = _check_positive(E, "E")
    a = _check_positive(alpha, "alpha")
    n = _check_poisson(nu)
    th = _check_positive(t, "t")
    width = _check_positive(b, "b")
    k = _check_positive(coefficient, "coefficient")
    sigma_cr = k * _PI2 * e / (12.0 * (1.0 - n * n)) * (th / width) ** 2
    return sigma_cr / (e * a)


def thermal_buckling_check(E, alpha, nu, t, b, applied_dT, coefficient=4.0):
    """Complete thermal buckling check of a constrained plate.

    Returns a dict with the critical temperature rise, the margin of
    safety dT_cr / applied_dT - 1 and the stable verdict. The applied
    temperature rise must be positive (heating): cooling a
    constrained plate produces tension, not buckling.

    Worked anchor: E = 70 GPa, alpha = 23e-6 1/K, nu = 0.33, t = 2 mm,
    b = 150 mm, k = 4.0 and applied_dT = 20 K give dT_cr = 28.54 K,
    margin = 0.427 and stable = True; applied_dT = 40 K gives margin
    = -0.287 and stable = False.

    Raises ValueError for non-positive E, alpha, t, b, coefficient or
    applied_dT, or an invalid Poisson ratio.
    """
    e = _check_positive(E, "E")
    a = _check_positive(alpha, "alpha")
    n = _check_poisson(nu)
    th = _check_positive(t, "t")
    width = _check_positive(b, "b")
    k = _check_positive(coefficient, "coefficient")
    applied = _check_positive(applied_dT, "applied_dT")
    sigma_cr = k * _PI2 * e / (12.0 * (1.0 - n * n)) * (th / width) ** 2
    dT_cr = sigma_cr / (e * a)
    return {
        "critical_dT": dT_cr,
        "margin_of_safety": dT_cr / applied - 1.0,
        "stable": applied < dT_cr,
    }
