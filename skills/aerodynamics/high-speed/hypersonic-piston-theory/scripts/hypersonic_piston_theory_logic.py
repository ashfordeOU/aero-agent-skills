#!/usr/bin/env python3
"""Lighthill piston-theory surface pressure for small-perturbation hypersonic surfaces.

Evaluates the piston-theory surface-pressure problem of the Lighthill
1953 piston analogy in the Ashley-Zartarian hypersonic
small-perturbation class: the pressure ratio across a moving surface
element follows the closed form p/p_inf = (1 + ((gamma - 1)/2) *
(v/a_inf))^(2 gamma/(gamma - 1)) from the local piston velocity ratio
v/a_inf, positive for a compression (shock-side) motion and negative
for an expansion, collapsing to vacuum p/p_inf = 0 at the expansion
cutoff v/a_inf = -2/(gamma - 1). The linearized limit p/p_inf = 1 +
gamma * (v/a_inf) is the small-piston-velocity first-order law; on a
steady surface inclined theta to the freestream the piston velocity
ratio is the freestream normal component M * sin(theta), giving the
per-side surface-pressure coefficient Cp = 2/(gamma M^2) * (p/p_inf -
1) with the linearized hypersonic limit Cp = 2 * sin(theta)/M. An
unsteady surface whose normal wall motion adds to the geometric piston
velocity carries the instantaneous pressure ratio and coefficient at
any phase of its motion. Pure stdlib, math only, no RNG; all angles in
degrees, gamma defaults to 1.4 (air). This leaf is the unsteady
complement to the steady blunt-body impact theory of the hypersonic-flow
leaf: same hypersonic surface-pressure physics, built from the local
piston velocity rather than from steady impact integrals.

Pinned anchors at gamma 1.4 (verified by the contract test): the
piston law table p/p_inf = 1.948717100000 at v/a = 0.5 and
0.478296900000 at -0.5, the expansion cutoff exactly zero at
v/a = -5.0, surface A (M = 6, theta = 5 deg) compression p/p_inf =
2.006315343379 against expansion 0.461491957246, surface B (M = 8,
theta = 10 deg) 5.563247915155 against 0.102434506727, and the
unsteady swing 0.253904031159 of the steady ratio for a wall velocity
amplitude 0.10.
"""

import math

GAMMA = 1.4  # air default; gamma is a parameter of every function
D2R = 0.017453292519943295  # degrees to radians

SIDES = ("compression", "expansion")
DIRECTIONS = (1, -1)  # +1 wall motion into the gas, -1 retreat


def _check_gamma(gamma):
    """Reject gamma at or below 1 (no real exponent law below it)."""
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be > 1")


def _check_mach_theta(mach, theta_deg):
    """Reject a non-supersonic Mach or an inclination outside [0, 90) deg."""
    if mach <= 1.0:
        raise ValueError("Mach number must be supersonic (M > 1)")
    if not 0.0 <= theta_deg < 90.0:
        raise ValueError("inclination theta must lie in [0, 90) degrees")


def piston_pressure_ratio(v_a, gamma=GAMMA):
    """Piston-theory pressure ratio p/p_inf from the piston velocity ratio.

    Closed form (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma - 1)):
    equal to 1.0 at v_a = 0, above 1 on the compression side, between 1
    and 0 on the expansion side, and exactly 0.0 when the base vanishes
    at the expansion cutoff v_a = -2/(gamma - 1). ValueError when gamma
    <= 1 or the piston velocity ratio sits below the cutoff (the flow is
    fully expanded and the law has no real value).
    """
    _check_gamma(gamma)
    base = 1.0 + 0.5 * (gamma - 1.0) * v_a
    if base < 0.0:
        raise ValueError(
            "piston velocity ratio below the expansion cutoff "
            "-2/(gamma - 1); the flow is fully expanded"
        )
    if base == 0.0:
        return 0.0
    return base ** (2.0 * gamma / (gamma - 1.0))


def linear_pressure_ratio(v_a, gamma=GAMMA):
    """Linearized piston-theory pressure ratio p_lin/p_inf = 1 + gamma*v_a.

    First-order expansion of the piston law, the regime of small
    M*sin(theta). ValueError when gamma <= 1.
    """
    _check_gamma(gamma)
    return 1.0 + gamma * v_a


def piston_velocity_ratio(mach, theta_deg):
    """Piston velocity ratio v/a_inf = M * sin(theta) of a steady surface.

    The freestream normal component U*sin(theta) divided by a_inf = U/M,
    positive for a compression-side inclination. ValueError when mach
    <= 1 or theta lies outside [0, 90) degrees.
    """
    _check_mach_theta(mach, theta_deg)
    return mach * math.sin(theta_deg * D2R)


def _side_ratio(mach, theta_deg, side, gamma):
    """Piston velocity ratio of one side, +M*sin(theta) or -M*sin(theta)."""
    base = piston_velocity_ratio(mach, theta_deg)
    if side == "compression":
        return piston_pressure_ratio(base, gamma)
    if side == "expansion":
        return piston_pressure_ratio(-base, gamma)
    raise ValueError("side must be 'compression' or 'expansion'")


def surface_pressure_ratio(mach, theta_deg, side, gamma=GAMMA):
    """Piston pressure ratio on the compression or the expansion side.

    Compression carries v/a_inf = +M*sin(theta), expansion
    v/a_inf = -M*sin(theta), each through the pinned closed form.
    ValueError as piston_velocity_ratio plus gamma <= 1 and a side other
    than the two names.
    """
    return _side_ratio(mach, theta_deg, side, gamma)


def surface_pressure_coefficient(mach, theta_deg, side, gamma=GAMMA):
    """Surface-pressure coefficient Cp = 2/(gamma M^2) * (p/p_inf - 1).

    Evaluated per side with the side's own piston pressure ratio. Same
    ValueError set as surface_pressure_ratio.
    """
    p_ratio = _side_ratio(mach, theta_deg, side, gamma)
    return 2.0 / (gamma * mach * mach) * (p_ratio - 1.0)


def linear_cp(mach, theta_deg):
    """Linearized hypersonic surface-pressure coefficient 2 * sin(theta)/M.

    Follows from the linearized pressure ratio through the Cp relation;
    gamma cancels, so the coefficient is exactly gamma-independent.
    ValueError as piston_velocity_ratio.
    """
    _check_mach_theta(mach, theta_deg)
    return 2.0 * math.sin(theta_deg * D2R) / mach


def unsteady_piston_ratio(mach, theta_deg, wall_v_a, direction):
    """Instantaneous piston velocity ratio of a moving surface.

    The steady geometric term M*sin(theta) plus direction * abs(wall_v_a):
    direction +1 for wall motion into the gas (compression), -1 for
    retreat. ValueError as piston_velocity_ratio plus a direction other
    than +1 or -1.
    """
    geometric = piston_velocity_ratio(mach, theta_deg)
    if direction not in DIRECTIONS:
        raise ValueError("direction must be +1 (into the gas) or -1 (retreat)")
    return geometric + direction * abs(wall_v_a)


def unsteady_pressure_ratio(mach, theta_deg, wall_v_a, direction, gamma=GAMMA):
    """Instantaneous piston pressure ratio of the moving surface.

    piston_pressure_ratio of the composed unsteady piston velocity
    ratio, no time integration, no RNG. ValueError set of
    unsteady_piston_ratio plus gamma <= 1 and the expansion-cutoff guard.
    """
    _check_gamma(gamma)
    composed = unsteady_piston_ratio(mach, theta_deg, wall_v_a, direction)
    return piston_pressure_ratio(composed, gamma)
