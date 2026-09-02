#!/usr/bin/env python3
"""Boundary-layer theory logic (flat plate, laminar and turbulent).

Classical physics results, public-domain knowledge. The Blasius (1908)
similarity solution for a laminar flat-plate boundary layer at station
x with local Reynolds number Re_x = U * x / nu gives:

  delta  = 5.0 * x / sqrt(Re_x)     (99-percent thickness)
  delta* = 1.7208 * x / sqrt(Re_x)  (displacement thickness)
  theta  = 0.664 * x / sqrt(Re_x)   (momentum thickness)
  Cf     = 0.664 / sqrt(Re_x)       (local skin friction)
  Cf_bar = 1.328 / sqrt(Re_x)       (average, one side)

The turbulent 1/7 power-law profile (valid to Re_x ~ 1e7) gives:

  delta  = 0.37 * x / Re_x^(1/5)
  delta* = delta / 8
  theta  = 7 * delta / 72
  Cf     = 0.0592 / Re_x^(1/5)
  Cf_bar = 0.074 / Re_x^(1/5)

and the fully turbulent log-law correlation

  Cf = 0.455 / (log10 Re_x)^2.58

extends friction estimates to higher Reynolds numbers. Displacement
thickness delta* is the mass deficit of the layer, momentum thickness
theta the momentum deficit; their ratio is the shape factor H =
delta* / theta (2.5916 laminar, 9 / 7 turbulent). Transition on a
smooth flat plate with low free-stream turbulence is near Re_x = 5e5.
"""

import math

DEFAULT_TRANSITION_RE = 5e5


def _check_x(x):
    if not (x > 0.0):
        raise ValueError("station x must be positive, got %r" % (x,))


def _check_re(re_x):
    if not (re_x > 0.0):
        raise ValueError("Reynolds number must be positive, got %r" % (re_x,))


def _check_positive(value, name):
    if not (value > 0.0):
        raise ValueError("%s must be positive, got %r" % (name, value))


def reynolds_number(rho, v, l, mu):
    """Local Reynolds number Re_x = rho * V * L / mu."""
    _check_positive(rho, "density rho")
    _check_positive(v, "speed v")
    _check_positive(l, "length l")
    _check_positive(mu, "dynamic viscosity mu")
    return rho * v * l / mu


def kinematic_viscosity(mu, rho):
    """Kinematic viscosity nu = mu / rho."""
    _check_positive(mu, "dynamic viscosity mu")
    _check_positive(rho, "density rho")
    return mu / rho


def classify_regime(re_x, re_tr=DEFAULT_TRANSITION_RE):
    """Return 'laminar' below the transition Reynolds number, else 'turbulent'."""
    _check_re(re_x)
    _check_positive(re_tr, "transition Reynolds number re_tr")
    return "laminar" if re_x < re_tr else "turbulent"


def blasius_thickness(x, re_x):
    """Laminar 99-percent boundary-layer thickness delta."""
    _check_x(x)
    _check_re(re_x)
    return 5.0 * x / math.sqrt(re_x)


def blasius_displacement_thickness(x, re_x):
    """Laminar displacement thickness delta*."""
    _check_x(x)
    _check_re(re_x)
    return 1.7208 * x / math.sqrt(re_x)


def blasius_momentum_thickness(x, re_x):
    """Laminar momentum thickness theta."""
    _check_x(x)
    _check_re(re_x)
    return 0.664 * x / math.sqrt(re_x)


def blasius_skin_friction(re_x):
    """Laminar local skin-friction coefficient Cf = 0.664 / sqrt(Re_x)."""
    _check_re(re_x)
    return 0.664 / math.sqrt(re_x)


def blasius_average_skin_friction(re_x):
    """Laminar average skin friction over one side: 1.328 / sqrt(Re_x)."""
    _check_re(re_x)
    return 1.328 / math.sqrt(re_x)


def turb_power_thickness(x, re_x):
    """Turbulent 99-percent boundary-layer thickness (1/7 power law)."""
    _check_x(x)
    _check_re(re_x)
    return 0.37 * x / re_x ** 0.2


def turb_power_displacement_thickness(x, re_x):
    """Turbulent displacement thickness delta* = delta / 8."""
    _check_x(x)
    _check_re(re_x)
    return turb_power_thickness(x, re_x) / 8.0


def turb_power_momentum_thickness(x, re_x):
    """Turbulent momentum thickness theta = 7 * delta / 72."""
    _check_x(x)
    _check_re(re_x)
    return 7.0 * turb_power_thickness(x, re_x) / 72.0


def turb_power_skin_friction(re_x):
    """Turbulent local skin friction (1/7 power law): 0.0592 / Re_x^(1/5)."""
    _check_re(re_x)
    return 0.0592 / re_x ** 0.2


def turb_power_average_skin_friction(re_x):
    """Turbulent average skin friction over one side: 0.074 / Re_x^(1/5)."""
    _check_re(re_x)
    return 0.074 / re_x ** 0.2


def cf_turbulent_log_law(re_x):
    """Fully turbulent log-law skin friction: 0.455 / (log10 Re_x)^2.58.

    Valid for Re_x above about 1e7; requires Re_x > 1 so log10 is positive.
    """
    _check_re(re_x)
    if re_x <= 1.0:
        raise ValueError("log-law skin friction needs Re_x > 1, got %r" % (re_x,))
    return 0.455 / math.log10(re_x) ** 2.58


def shape_factor(delta_star, theta):
    """Shape factor H = delta* / theta (2.5916 laminar, 9/7 turbulent)."""
    if not (theta > 0.0):
        raise ValueError("momentum thickness theta must be positive, got %r" % (theta,))
    if not (delta_star > 0.0):
        raise ValueError("displacement thickness must be positive, got %r" % (delta_star,))
    return delta_star / theta


def flat_plate_thicknesses(x, re_x, re_tr=DEFAULT_TRANSITION_RE):
    """One-call summary for a flat-plate station.

    Returns a dict with regime, delta, delta_star, theta, shape_factor,
    cf_local, cf_average. Uses the Blasius solution for laminar flow and
    the 1/7 power law for turbulent flow.
    """
    regime = classify_regime(re_x, re_tr)
    if regime == "laminar":
        delta = blasius_thickness(x, re_x)
        dstar = blasius_displacement_thickness(x, re_x)
        theta = blasius_momentum_thickness(x, re_x)
        cf_local = blasius_skin_friction(re_x)
        cf_avg = blasius_average_skin_friction(re_x)
    else:
        delta = turb_power_thickness(x, re_x)
        dstar = turb_power_displacement_thickness(x, re_x)
        theta = turb_power_momentum_thickness(x, re_x)
        cf_local = turb_power_skin_friction(re_x)
        cf_avg = turb_power_average_skin_friction(re_x)
    return {
        "regime": regime,
        "delta": delta,
        "delta_star": dstar,
        "theta": theta,
        "shape_factor": shape_factor(dstar, theta),
        "cf_local": cf_local,
        "cf_average": cf_avg,
    }
