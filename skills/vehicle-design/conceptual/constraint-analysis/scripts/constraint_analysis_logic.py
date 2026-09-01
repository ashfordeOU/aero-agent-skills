#!/usr/bin/env python3
"""Aircraft constraint analysis logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): conceptual design constraint analysis draws a matching chart
of required thrust to weight T/W against wing loading W/S, one curve
per constraint. The stall constraint sets a maximum wing loading W/S =
0.5 * rho * CLmax * VS^2; the takeoff distance constraint requires
T/W = 1.21 * (W/S) / (rho * g * CLmax * s_TO); the climb gradient
constraint requires T/W = 1/LD + gamma (the excess thrust fraction
(T - D)/W equals the climb gradient at small angles); the cruise
constraint requires T/W = 0.5 * rho * V^2 * CD0 / (W/S) + k * (W/S) /
(0.5 * rho * V^2); the maneuvering constraint in a level turn at load
factor n requires T/W = 0.5 * rho * V^2 * CD0 / (W/S) + k * n^2 *
(W/S) / (0.5 * rho * V^2). At a given wing loading the feasible region
lower bound is the maximum of the required T/W values over the active
constraints; the boundary of the feasible design region is the set of
those lower bounds across the wing loading sweep.

Units are SI throughout: W/S in N/m^2, T/W unitless, speeds in m/s,
air density rho in kg/m^3 (default 1.225 kg/m^3, sea-level ISA),
distances in m, flight path angle in rad, load factor unitless, g =
9.80665 m/s^2. Invalid inputs raise ValueError throughout.
"""

G = 9.80665  # standard gravity, m/s^2 (SI)
RHO_SL = 1.225  # sea-level ISA air density, kg/m^3 (default)


def stall_constraint(VS, CLmax, rho=RHO_SL):
    """Maximum wing loading allowed by the stall speed (N/m^2).

    W/S = 0.5 * rho * CLmax * VS^2 follows from lift equal to weight
    at the stall speed VS (m/s), maximum lift coefficient CLmax, and
    air density rho (kg/m^3).

    Raises ValueError if VS, CLmax, or rho is not positive.
    """
    if VS <= 0:
        raise ValueError("stall speed VS must be positive, got %r" % (VS,))
    if CLmax <= 0:
        raise ValueError("CLmax must be positive, got %r" % (CLmax,))
    if rho <= 0:
        raise ValueError("air density rho must be positive, got %r" % (rho,))
    return 0.5 * rho * CLmax * VS * VS


def takeoff_constraint(W_S, rho, CLmax, s_TO):
    """Required thrust to weight from the takeoff distance (unitless).

    T/W = 1.21 * (W/S) / (rho * g * CLmax * s_TO), with W/S in N/m^2,
    rho in kg/m^3, g = 9.80665 m/s^2, CLmax the maximum lift
    coefficient in the takeoff configuration, and s_TO the takeoff
    distance in m. The 1.21 factor folds in the takeoff speed ratio
    and the ground-roll approximation.

    Raises ValueError if any input is not positive.
    """
    if W_S <= 0:
        raise ValueError("wing loading W/S must be positive, got %r" % (W_S,))
    if rho <= 0:
        raise ValueError("air density rho must be positive, got %r" % (rho,))
    if CLmax <= 0:
        raise ValueError("CLmax must be positive, got %r" % (CLmax,))
    if s_TO <= 0:
        raise ValueError("takeoff distance s_TO must be positive, got %r" % (s_TO,))
    return 1.21 * W_S / (rho * G * CLmax * s_TO)


def climb_constraint(LD, gamma_rad):
    """Required thrust to weight from the climb gradient (unitless).

    T/W = 1/LD + gamma_rad: the level-flight drag term plus the
    small-angle climb term, with LD the lift-to-drag ratio and
    gamma_rad the flight path angle in rad. The excess thrust fraction
    (T - D)/W equals the climb gradient, so T/W = D/W + gamma.

    Raises ValueError if LD is not positive or gamma_rad is negative.
    """
    if LD <= 0:
        raise ValueError("lift-to-drag ratio LD must be positive, got %r" % (LD,))
    if gamma_rad < 0:
        raise ValueError(
            "climb gradient gamma_rad must be non-negative, got %r" % (gamma_rad,)
        )
    return 1.0 / LD + gamma_rad


def cruise_constraint(W_S, V, rho, CD0, k):
    """Required thrust to weight at the cruise speed (unitless).

    T/W = 0.5 * rho * V^2 * CD0 / (W/S) + k * (W/S) / (0.5 * rho * V^2):
    the zero-lift drag term plus the lift-induced drag term, with W/S
    in N/m^2, V in m/s, rho in kg/m^3, CD0 the zero-lift drag
    coefficient, and k the induced drag factor k = 1/(pi * e * AR).

    Raises ValueError if any input is not positive.
    """
    if W_S <= 0:
        raise ValueError("wing loading W/S must be positive, got %r" % (W_S,))
    if V <= 0:
        raise ValueError("cruise speed V must be positive, got %r" % (V,))
    if rho <= 0:
        raise ValueError("air density rho must be positive, got %r" % (rho,))
    if CD0 <= 0:
        raise ValueError("zero-lift drag coefficient CD0 must be positive, got %r" % (CD0,))
    if k <= 0:
        raise ValueError("induced drag factor k must be positive, got %r" % (k,))
    q = 0.5 * rho * V * V
    return q * CD0 / W_S + k * W_S / q


def maneuvering_constraint(W_S, V, rho, CD0, k, n):
    """Required thrust to weight in a level turn (unitless).

    T/W = 0.5 * rho * V^2 * CD0 / (W/S) + k * n^2 * (W/S) /
    (0.5 * rho * V^2): the zero-lift drag term plus the lift-induced
    drag term scaled by the load factor squared, with W/S in N/m^2, V
    in m/s, rho in kg/m^3, CD0 the zero-lift drag coefficient, k the
    induced drag factor, and n the load factor. At n = 1 the curve
    reduces to the cruise constraint.

    Raises ValueError if any input is not positive.
    """
    if W_S <= 0:
        raise ValueError("wing loading W/S must be positive, got %r" % (W_S,))
    if V <= 0:
        raise ValueError("turn speed V must be positive, got %r" % (V,))
    if rho <= 0:
        raise ValueError("air density rho must be positive, got %r" % (rho,))
    if CD0 <= 0:
        raise ValueError("zero-lift drag coefficient CD0 must be positive, got %r" % (CD0,))
    if k <= 0:
        raise ValueError("induced drag factor k must be positive, got %r" % (k,))
    if n <= 0:
        raise ValueError("load factor n must be positive, got %r" % (n,))
    q = 0.5 * rho * V * V
    return q * CD0 / W_S + k * n * n * W_S / q


def feasible_region_lower_bounds(ws_values, constraints):
    """Feasible region lower bounds as (W/S, T/W) pairs.

    For each wing loading in ws_values (N/m^2, ascending order), the
    lower bound of the feasible region is the maximum required T/W
    over the active constraint curves; constraints maps constraint
    names to callables T/W = f(W/S) that reuse the constraint
    functions above. Returns a list of (W/S, T/W) pairs sorted by W/S
    that traces the boundary of the feasible design region on the
    matching chart.

    Raises ValueError if ws_values or constraints is empty or if any
    wing loading is not positive.
    """
    if not ws_values:
        raise ValueError("ws_values must not be empty")
    if not constraints:
        raise ValueError("constraints must not be empty")
    if any(ws <= 0 for ws in ws_values):
        raise ValueError("every wing loading W/S must be positive")
    bounds = []
    for ws in sorted(ws_values):
        required = [f(ws) for f in constraints.values()]
        bounds.append((ws, max(required)))
    return bounds
