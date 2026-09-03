"""Laminar-turbulent transition location by Thwaites integral plus Michel criterion.

Pure stdlib implementation for the aerodynamics/boundary-layer/
boundary-layer-transition leaf. Given the edge-velocity distribution
Ue(x) along a two-dimensional body, this module:

- grows the laminar boundary layer with the Thwaites integral relation
  to obtain the momentum thickness theta at each station,
- forms the local Reynolds numbers Re_x = Ue x / nu and
  Re_theta = Ue theta / nu,
- evaluates the Michel transition criterion
  Re_theta,tr = A (1 + B / Re_x) Re_x**P with A = 1.174, B = 22400,
  P = 0.46 at each station,
- locates the first station where Re_theta reaches the threshold and
  linearly interpolates the transition location between the bracketing
  stations.

The Thwaites relation is an integral method: no PDE solver is used, and
the inputs are a two-dimensional clean-surface edge-velocity history
only. The flat_plate_transition helper is a closed-form verification
check for the constant-edge-velocity case.
"""

import math

MICHEL_A = 1.174
MICHEL_B = 22400.0
MICHEL_P = 0.46
THWAITES_C = 0.45
SQRT_THWAITES_C = math.sqrt(THWAITES_C)


def _check_stations(xs, ues):
    """Validate a station grid: xs and ues equal-length positive data.

    Raises ValueError for fewer than two stations, unequal lengths, any
    x below zero, any x not strictly increasing, or any non-positive
    edge velocity.
    """
    if len(xs) < 2:
        raise ValueError("at least two stations are required")
    if len(xs) != len(ues):
        raise ValueError("xs and ues must have equal length")
    if any(x < 0 for x in xs):
        raise ValueError("x stations must be non-negative")
    for prev, cur in zip(xs, xs[1:]):
        if cur <= prev:
            raise ValueError("x stations must be strictly increasing")
    if any(ue <= 0 for ue in ues):
        raise ValueError("edge velocity ue must be positive at every station")


def momentum_thickness_profile(xs, ues, nu):
    """Thwaites integral momentum thickness at each station.

    theta(x)^2 = 0.45 nu / Ue(x)^6 * integral_0^x Ue(xi)^5 d(xi) with
    the integral evaluated cumulatively by the trapezoid rule over the
    supplied stations. The leading-edge segment from 0 to xs[0] keeps
    Ue at its first-station value, which makes the constant-edge-
    velocity flat plate exact. Raises ValueError on a malformed grid,
    non-positive edge velocity, or nu <= 0.
    """
    _check_stations(xs, ues)
    if nu <= 0:
        raise ValueError("kinematic viscosity nu must be positive")
    integrand = [ue ** 5 for ue in ues]
    integral = [0.0] * len(xs)
    integral[0] = integrand[0] * xs[0]
    for i in range(1, len(xs)):
        integral[i] = integral[i - 1] + 0.5 * (integrand[i - 1] + integrand[i]) * (xs[i] - xs[i - 1])
    theta_list = []
    for i in range(len(xs)):
        theta_list.append(math.sqrt(THWAITES_C * nu * integral[i] / ues[i] ** 6))
    return theta_list


def re_theta_profile(xs, ues, theta_list, nu):
    """Momentum-thickness Reynolds number Re_theta = Ue theta / nu."""
    if len(xs) != len(ues) or len(xs) != len(theta_list):
        raise ValueError("xs, ues and theta_list must have equal length")
    if nu <= 0:
        raise ValueError("kinematic viscosity nu must be positive")
    return [ues[i] * theta_list[i] / nu for i in range(len(xs))]


def michel_threshold(re_x):
    """Michel criterion value A (1 + B / Re_x) Re_x**P at Re_x.

    Raises ValueError for re_x <= 0.
    """
    if re_x <= 0:
        raise ValueError("re_x must be positive")
    return MICHEL_A * (1.0 + MICHEL_B / re_x) * re_x ** MICHEL_P


def michel_criterion(re_x, re_theta):
    """True when transition onset is reached: re_theta >= threshold.

    Raises ValueError for re_x <= 0 or re_theta < 0.
    """
    if re_x <= 0:
        raise ValueError("re_x must be positive")
    if re_theta < 0:
        raise ValueError("re_theta must be non-negative")
    return re_theta >= michel_threshold(re_x)


def _interp_crossing(x0, m0, x1, m1):
    """Linear-interpolate x at margin = 0 between stations (x0, m0), (x1, m1)."""
    if m1 == m0:
        return x0
    return x0 - m0 * (x1 - x0) / (m1 - m0)


def transition_location(xs, ues, nu):
    """Full Thwaites plus Michel transition sweep along the body.

    Returns a dict with theta_list, re_theta_list, criterion_margin_list
    (re_theta minus the Michel threshold at each station),
    x_transition (first station where the margin is non-negative, or
    None when the criterion is never crossed), transition_index (its
    index, or None) and interp_x_transition (linear interpolation of x
    at margin zero between the bracketing stations, xs[0] when the very
    first station already satisfies the criterion, None when there is
    no crossing). ValueErrors propagate from the helpers.
    """
    theta_list = momentum_thickness_profile(xs, ues, nu)
    re_theta_list = re_theta_profile(xs, ues, theta_list, nu)
    margin_list = []
    for i in range(len(xs)):
        re_x = ues[i] * xs[i] / nu
        margin_list.append(re_theta_list[i] - michel_threshold(re_x))
    transition_index = None
    for i, margin in enumerate(margin_list):
        if margin >= 0.0:
            transition_index = i
            break
    if transition_index is None:
        return {
            "theta_list": theta_list,
            "re_theta_list": re_theta_list,
            "criterion_margin_list": margin_list,
            "x_transition": None,
            "transition_index": None,
            "interp_x_transition": None,
        }
    if transition_index >= 1:
        interp_x = _interp_crossing(
            xs[transition_index - 1],
            margin_list[transition_index - 1],
            xs[transition_index],
            margin_list[transition_index],
        )
    else:
        interp_x = xs[0]
    return {
        "theta_list": theta_list,
        "re_theta_list": re_theta_list,
        "criterion_margin_list": margin_list,
        "x_transition": xs[transition_index],
        "transition_index": transition_index,
        "interp_x_transition": interp_x,
    }


def flat_plate_transition(nu, ue, x_max):
    """Flat-plate natural-transition check (closed form, verification helper).

    With a constant edge velocity the Thwaites relation closes to
    Re_theta = sqrt(0.45) sqrt(Re_x) = 0.6708 sqrt(Re_x). The Michel
    threshold is scanned over x from 1e-3 to x_max in 500 uniform
    steps; the first x where Re_theta reaches the threshold is
    returned, or None when no crossing exists. Raises ValueError for
    nu <= 0, ue <= 0 or x_max <= 0.
    """
    if nu <= 0:
        raise ValueError("kinematic viscosity nu must be positive")
    if ue <= 0:
        raise ValueError("edge velocity ue must be positive")
    if x_max <= 0:
        raise ValueError("x_max must be positive")
    lo = 1e-3
    steps = 500
    dx = (x_max - lo) / steps
    for i in range(steps + 1):
        x = lo + i * dx
        re_x = ue * x / nu
        re_theta = SQRT_THWAITES_C * math.sqrt(re_x)
        if re_theta >= michel_threshold(re_x):
            return x
    return None
