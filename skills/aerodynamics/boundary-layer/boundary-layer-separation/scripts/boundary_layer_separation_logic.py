"""Laminar and turbulent boundary-layer separation prediction.

Pure stdlib implementation for the aerodynamics/boundary-layer/
boundary-layer-separation leaf. Given the edge-velocity distribution
U(x) along a two-dimensional body, this module:

- grows the laminar layer with the Thwaites integral relation to obtain
  the momentum thickness theta at each station (theta^2 = 0.45 * nu /
  U^6 * integral_0^x U^5 dx, integrated by the trapezoid rule),
- forms the Thwaites pressure-gradient parameter
  lambda = theta^2 / nu * dU/dx at each station,
- flags the first station where lambda drops to THWAITES_LAMBDA_SEP
  (-0.09), the classical laminar separation criterion,

and, given the pressure-coefficient recovery C_p(x) on the same body:

- evaluates the Stratford-style separation parameter
  S = C_p * sqrt((x / C_p) * dC_p/dx) on the recovery side
  (stations with C_p > 0 and dC_p/dx > 0), using one-sided interval
  differences attributed to the right end of each interval,
- flags the first station where S reaches STRATFORD_SEP (0.35) and
  reports the margin 0.35 - max S on the recovery side before the
  crossing (positive margin means the flow has headroom up to the
  crossing point).

Conventions (recorded in the SKILL body):

- The Thwaites traverse starts with theta = 0 at the first station with
  U > 0 (sharp-leading-edge start); head stations with U = 0 (a true
  stagnation point) are skipped, which removes the U^6 singularity.
- Trailing stations where U returns to zero carry lambda = -inf: the
  edge flow has stopped, so separation certainly occurred upstream.
- S is evaluated with the difference over the interval ending at each
  station, which reproduces the verified worked-example anchor
  S = 0.3505 at station 8 of the C_p = 0.4 x^2 recovery.

No PDE solver, no external packages, no randomness: every output is a
deterministic function of the station lists.
"""

import math

THWAITES_LAMBDA_SEP = -0.09
STRATFORD_SEP = 0.35
THWAITES_C = 0.45


def _validate_stations(xs, ys, ylabel):
    """Raise ValueError when the station lists are non-physical.

    Checks: non-empty lists, matching lengths, strictly increasing
    x stations (a traverse must march forward along the body).
    """
    if not xs or not ys:
        raise ValueError("station lists must be non-empty")
    if len(xs) != len(ys):
        raise ValueError(
            "station and %s lists must have the same length" % ylabel
        )
    for i in range(1, len(xs)):
        if xs[i] <= xs[i - 1]:
            raise ValueError("x stations must be strictly increasing")


def thwaites_lambda(xs, us, nu):
    """Return the Thwaites lambda parameter at every station.

    xs, us: edge-velocity stations (m, m/s). nu: kinematic viscosity
    (m2/s). Raises ValueError for empty or mismatched lists,
    non-increasing x, nu <= 0, any negative velocity, or a velocity
    field that never becomes positive.
    """
    _validate_stations(xs, us, "velocity")
    if nu <= 0:
        raise ValueError("kinematic viscosity nu must be positive")
    for u in us:
        if u < 0.0:
            raise ValueError("edge velocity must be non-negative")

    n = len(xs)
    start = 0
    while start < n and us[start] <= 0.0:
        start += 1
    if start == n:
        raise ValueError("edge velocity must be positive at some station")

    # Trapezoid integral of U^5 dx from the first positive station on.
    integral = [0.0] * n
    for i in range(start + 1, n):
        dx = xs[i] - xs[i - 1]
        integral[i] = integral[i - 1] + 0.5 * (us[i] ** 5 + us[i - 1] ** 5) * dx

    lam = [0.0] * n
    for i in range(n):
        if us[i] == 0.0 and i > start:
            # Edge flow stopped downstream of the start: separated long ago.
            lam[i] = float("-inf")
            continue
        if us[i] > 0.0:
            theta2 = THWAITES_C * nu * integral[i] / (us[i] ** 6)
        else:
            theta2 = 0.0  # stagnation head stations: theta = 0
        dudx = _velocity_derivative(xs, us, i)
        lam[i] = theta2 / nu * dudx
    return lam


def _velocity_derivative(xs, us, i):
    """Central difference for dU/dx, forward at station 0 and backward
    at the last station."""
    n = len(xs)
    if n == 1:
        return 0.0
    if i == 0:
        return (us[1] - us[0]) / (xs[1] - xs[0])
    if i == n - 1:
        return (us[i] - us[i - 1]) / (xs[i] - xs[i - 1])
    return (us[i + 1] - us[i - 1]) / (xs[i + 1] - xs[i - 1])


def laminar_separation_station(xs, us, nu):
    """Return (index, x) of the first station with lambda <= -0.09.

    Returns None when lambda stays above the criterion for the whole
    run. Validates its inputs exactly like thwaites_lambda.
    """
    lam = thwaites_lambda(xs, us, nu)
    for i, value in enumerate(lam):
        if value <= THWAITES_LAMBDA_SEP:
            return (i, xs[i])
    return None


def stratford_parameter(xs, cps):
    """Return the Stratford S parameter at every recovery station.

    S is defined only on the recovery side: stations with C_p > 0 and
    a positive pressure slope. Other stations carry None in the result
    list. The slope uses the interval ending at each station (backward
    at i >= 1, forward at station 0), attributed to its right end.
    """
    _validate_stations(xs, cps, "pressure-coefficient")
    n = len(xs)
    s_vals = [None] * n
    for i in range(n):
        if cps[i] <= 0.0:
            continue
        if n == 1:
            continue
        if i == 0:
            slope = (cps[1] - cps[0]) / (xs[1] - xs[0])
        else:
            slope = (cps[i] - cps[i - 1]) / (xs[i] - xs[i - 1])
        if slope <= 0.0:
            continue
        s_vals[i] = cps[i] * math.sqrt((xs[i] / cps[i]) * slope)
    return s_vals


def stratford_separation_station(xs, cps):
    """Return (index, x) of the first recovery station with S >= 0.35.

    Returns None when the criterion is never met. Validates its inputs
    exactly like stratford_parameter.
    """
    s_vals = stratford_parameter(xs, cps)
    for i, value in enumerate(s_vals):
        if value is not None and value >= STRATFORD_SEP:
            return (i, xs[i])
    return None


def separation_margin(xs, cps):
    """Return 0.35 - max S on the recovery side before the crossing.

    With a crossing at station i the maximum is taken over recovery
    stations before i (headroom up to the separation point, hence
    positive). With no crossing the maximum is taken over the whole
    recovery. With no recovery stations at all the margin is the full
    STRATFORD_SEP. A positive margin means the flow keeps headroom.
    """
    s_vals = stratford_parameter(xs, cps)
    crossing = None
    for i, value in enumerate(s_vals):
        if value is not None and value >= STRATFORD_SEP:
            crossing = i
            break
    candidates = []
    for i, value in enumerate(s_vals):
        if value is None:
            continue
        if crossing is not None and i >= crossing:
            break
        candidates.append(value)
    if not candidates:
        return float(STRATFORD_SEP)
    return float(STRATFORD_SEP) - max(candidates)
