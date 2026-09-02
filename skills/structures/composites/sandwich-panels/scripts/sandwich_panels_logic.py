#!/usr/bin/env python3
"""Sandwich panel design logic (aerospace structures, common knowledge).

A sandwich panel is two thin, stiff face sheets separated by a
lightweight core (honeycomb or foam). The faces carry the bending
moment as a tension-compression couple, the core carries the
transverse shear, and the large face separation gives a high bending
stiffness per unit weight. The functions below implement the standard
engineering approximations: face-couple bending stiffness, face
stress from a moment, core shear stress from a shear load, face
wrinkling stress, core shear and face margins, and the deflection of
a simply supported sandwich beam including the core shear
contribution. These are generic mechanics (common knowledge,
summary-not-copy per standards-map.yaml); no text is reproduced from
any standard.

All functions are deterministic, offline, stdlib only.
"""

import math


def face_distance(core_thickness, t_face):
    """Distance d between the face sheet centroids: d = c + t."""
    if core_thickness <= 0.0:
        raise ValueError("core thickness must be > 0, got %r" % (core_thickness,))
    if t_face <= 0.0:
        raise ValueError("face thickness must be > 0, got %r" % (t_face,))
    return core_thickness + t_face


def total_thickness(core_thickness, t_face):
    """Overall sandwich thickness h = c + 2t."""
    face_distance(core_thickness, t_face)  # shared input validation
    return core_thickness + 2.0 * t_face


def bending_stiffness(ef, t_face, core_thickness, nu=0.0):
    """Equivalent bending stiffness D per unit width (N*m).

    D = Ef*t*d**2/(2*(1-nu**2)) + Ef*t**3/(6*(1-nu**2)), d = c + t.
    The first term is the face-couple (dominant when t << d); the
    second is the face bending about its own centroid. nu = 0 gives
    the beam-style D = Ef*t*d**2/2 + Ef*t**3/6.
    """
    if ef <= 0.0:
        raise ValueError("face modulus must be > 0, got %r" % (ef,))
    if not (0.0 <= nu < 1.0):
        raise ValueError("poisson ratio must be in [0, 1), got %r" % (nu,))
    d = face_distance(core_thickness, t_face)
    denom = 1.0 - nu * nu
    couple = ef * t_face * d * d / (2.0 * denom)
    intrinsic = ef * t_face ** 3 / (6.0 * denom)
    return couple + intrinsic


def face_stress(moment, t_face, core_thickness):
    """Signed face stresses (Pa) from a bending moment per unit width.

    sigma_top = -M/(d*t) (compression for positive sagging M),
    sigma_bottom = +M/(d*t). Returns (sigma_top, sigma_bottom).
    """
    d = face_distance(core_thickness, t_face)
    magnitude = moment / (d * t_face)
    return (-magnitude, magnitude)


def core_shear_stress(shear_load, core_thickness, t_face, width=1.0):
    """Core shear stress tau = V/(b*d) (Pa); the core carries nearly
    all of the transverse shear. b defaults to unit width."""
    d = face_distance(core_thickness, t_face)
    if width <= 0.0:
        raise ValueError("width must be > 0, got %r" % (width,))
    return shear_load / (width * d)


def wrinkling_stress(ef, ec, gc):
    """Face wrinkling stress sigma_wr = 0.5*(Ef*Ec*Gc)**(1/3) (Pa).

    Local buckling of a face sheet into the core; the formula is the
    standard symmetric-wrinkling approximation used in honeycomb and
    foam core design. Higher core modulus or shear modulus raises the
    wrinkling stress.
    """
    if ef <= 0.0 or ec <= 0.0 or gc <= 0.0:
        raise ValueError("face/core moduli must all be > 0, got %r, %r, %r" % (ef, ec, gc))
    return 0.5 * (ef * ec * gc) ** (1.0 / 3.0)


def core_shear_margin(tau_allow, shear_load, core_thickness, t_face, width=1.0):
    """Core shear failure check: (tau_applied, margin = tau_allow/|tau|).

    margin >= 1.0 means the core shear stress is acceptable. Zero shear
    load returns margin = inf.
    """
    tau = core_shear_stress(shear_load, core_thickness, t_face, width)
    if tau_allow <= 0.0:
        raise ValueError("allowable core shear stress must be > 0, got %r" % (tau_allow,))
    if tau == 0.0:
        return (0.0, float("inf"))
    return (tau, tau_allow / abs(tau))


def face_stress_margin(sigma_allow, moment, t_face, core_thickness):
    """Face failure check: (|sigma|_max, margin = sigma_allow/|sigma|_max).

    Uses the larger of the two face stress magnitudes. Zero moment
    returns margin = inf.
    """
    top, bottom = face_stress(moment, t_face, core_thickness)
    if sigma_allow <= 0.0:
        raise ValueError("allowable face stress must be > 0, got %r" % (sigma_allow,))
    applied = max(abs(top), abs(bottom))
    if applied == 0.0:
        return (0.0, float("inf"))
    return (applied, sigma_allow / applied)


def sandwich_beam_deflection(q, length, d_stiffness, gc, core_thickness, t_face):
    """Simply supported sandwich beam, uniform load q per unit width.

    Bending term delta_b = 5*q*L**4/(384*D); core shear term
    delta_s = q*L**2/(8*Gc*d). Returns (delta_b, delta_s, delta_total).
    The shear term dominates for soft (foam) cores; the bending term
    dominates for stiff honeycomb cores.
    """
    if q < 0.0:
        raise ValueError("load q must be >= 0, got %r" % (q,))
    if length <= 0.0:
        raise ValueError("length must be > 0, got %r" % (length,))
    if d_stiffness <= 0.0:
        raise ValueError("bending stiffness must be > 0, got %r" % (d_stiffness,))
    if gc <= 0.0:
        raise ValueError("core shear modulus must be > 0, got %r" % (gc,))
    d = face_distance(core_thickness, t_face)
    delta_b = 5.0 * q * length ** 4 / (384.0 * d_stiffness)
    delta_s = q * length * length / (8.0 * gc * d)
    return (delta_b, delta_s, delta_b + delta_s)


def select_core(honeycomb_gc, honeycomb_rho, foam_gc, foam_rho,
                weight_priority=1.0, impact_priority=0.0, cost_priority=0.0):
    """Deterministic honeycomb vs foam core selection heuristic.

    Honeycomb advantage: specific shear stiffness Gc/rho, typically
    3-10x foam at equal weight. Foam advantages: impact tolerance,
    moisture immunity, and formability to curved tooling (lower cost
    on contoured parts). Scores are normalized to the better specific
    shear stiffness, so each priority is in [0, 1]-ish units.

    Returns ("honeycomb"|"foam", honeycomb_score, foam_score).
    """
    if honeycomb_gc <= 0.0 or foam_gc <= 0.0:
        raise ValueError("core shear moduli must be > 0, got %r, %r" % (honeycomb_gc, foam_gc))
    if honeycomb_rho <= 0.0 or foam_rho <= 0.0:
        raise ValueError("core densities must be > 0, got %r, %r" % (honeycomb_rho, foam_rho))
    if weight_priority < 0.0 or impact_priority < 0.0 or cost_priority < 0.0:
        raise ValueError("priorities must be >= 0")
    hc_specific = honeycomb_gc / honeycomb_rho
    foam_specific = foam_gc / foam_rho
    best_specific = max(hc_specific, foam_specific)
    hc_score = weight_priority * (hc_specific / best_specific)
    foam_score = (weight_priority * (foam_specific / best_specific)
                  + impact_priority + cost_priority)
    winner = "honeycomb" if hc_score >= foam_score else "foam"
    return (winner, hc_score, foam_score)


def _cbrt(x):
    """Cube root helper used by tests to cross-check wrinkling_stress."""
    return x ** (1.0 / 3.0)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
