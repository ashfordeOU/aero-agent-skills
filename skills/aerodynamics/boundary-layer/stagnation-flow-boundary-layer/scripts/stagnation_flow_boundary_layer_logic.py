#!/usr/bin/env python3
"""Stagnation-flow boundary-layer logic (Hiemenz 2-D and Homann axisymmetric).

Classical exact-similarity results, public-domain engineering knowledge
(summary of the standard tabulations in Schlichting and White). At a
low-speed stagnation point or leading edge the inviscid surface speed
rises linearly with arc length s from the attachment line, u_e = a * s,
with the potential-flow stagnation velocity gradient a:

  a = 2.0 * u_inf / R   (circular cylinder or 2-D leading edge, Hiemenz)
  a = 1.5 * u_inf / R   (sphere or axisymmetric nose, Homann)

The Hiemenz and Homann similarity layers have constant thickness along
the attachment region (they do not grow in the streamwise direction), so
the 99-percent laminar boundary-layer thickness is

  delta = 2.4 * sqrt(nu / a)

with no streamwise station input. The wall shear follows from the exact
closed form tau_w = mu * u_inf * sqrt(a / nu) * fpp with mu = rho * nu
and fpp the classical similarity wall-shear constant (1.2326 for the
2-D Hiemenz layer, 1.3119 for the axisymmetric Homann layer), and the
local skin-friction coefficient is Cf = tau_w / (0.5 * rho * u_inf^2).
The full similarity ODEs f''' + f f'' + 1 - f'^2 = 0 (Hiemenz) and
2 f''' + 2 f f'' + 1 - f'^2 = 0 (Homann) are NOT integrated here; only
their classical constants enter, so the module is deterministic and
closed-form. Heat transfer is out of scope: this is the low-speed
laminar momentum boundary layer only.
"""

import math

# Classical Hiemenz (2-D) similarity wall-shear constant, f''(0).
FPP_2D = 1.2326
# Classical Homann (axisymmetric) similarity wall-shear constant, f''(0).
FPP_AXISYM = 1.3119
# Classical Hiemenz 99-percent boundary-layer thickness coefficient.
BL_DELTA_COEF = 2.4
# Potential-flow surface-speed gradient coefficient, circular cylinder.
CYLINDER_GRADIENT_COEF = 2.0
# Potential-flow surface-speed gradient coefficient, sphere.
SPHERE_GRADIENT_COEF = 1.5

# Accepted flow-type strings for the 2-D (Hiemenz) regime.
_TWO_D_FLOW_TYPES = ("cylinder", "2d", "two-dimensional")
# Accepted flow-type strings for the axisymmetric (Homann) regime.
_AXISYMMETRIC_FLOW_TYPES = ("sphere", "axisymmetric", "axi")


def _regime(flow_type):
    """Return the similarity regime key for a flow type, ValueError otherwise.

    Accepts the 2-D synonyms cylinder/2d/two-dimensional and the
    axisymmetric synonyms sphere/axisymmetric/axi, case-insensitive.
    """
    if not isinstance(flow_type, str):
        raise ValueError(
            "flow_type must be a string, got %r" % (flow_type,))
    key = flow_type.strip().lower()
    if key in _TWO_D_FLOW_TYPES:
        return "hiemenz-2d"
    if key in _AXISYMMETRIC_FLOW_TYPES:
        return "homann-axisymmetric"
    raise ValueError(
        "flow_type %r not recognized; use cylinder/2d/two-dimensional "
        "(Hiemenz) or sphere/axisymmetric/axi (Homann)" % (flow_type,))


def _check_positive(value, name):
    if not (value > 0.0):
        raise ValueError("%s must be positive, got %r" % (name, value))


def stagnation_velocity_gradient(flow_type, u_inf, radius):
    """Potential-flow stagnation velocity gradient a = du_e / ds (1/s).

    a = 2.0 * u_inf / radius for a circular cylinder or 2-D leading edge
    (from the inviscid surface speed u_e = 2 u_inf sin(s / R)) and
    a = 1.5 * u_inf / radius for a sphere or axisymmetric nose (from
    u_e = 1.5 u_inf sin(s / R)).
    """
    _regime(flow_type)
    _check_positive(u_inf, "freestream speed u_inf")
    _check_positive(radius, "body radius")
    if _regime(flow_type) == "hiemenz-2d":
        return CYLINDER_GRADIENT_COEF * u_inf / radius
    return SPHERE_GRADIENT_COEF * u_inf / radius


def boundary_layer_thickness(nu, a):
    """99-percent laminar boundary-layer thickness delta (m) of the layer.

    delta = BL_DELTA_COEF * sqrt(nu / a), constant along the attachment
    region because the Hiemenz and Homann similarity layers do not grow
    in the streamwise direction. The 2-D coefficient 2.4 is returned for
    both regimes; the axisymmetric layer at equal a is somewhat thinner
    in the standard tabulations, so the module value is a conservative
    documented approximation for the Homann case.
    """
    _check_positive(nu, "kinematic viscosity nu")
    _check_positive(a, "stagnation velocity gradient a")
    return BL_DELTA_COEF * math.sqrt(nu / a)


def wall_shear_stress(rho, nu, a, u_inf, flow_type):
    """Wall shear tau_w (Pa) at the attachment-line station.

    tau_w = mu * u_inf * sqrt(a / nu) * fpp with mu = rho * nu and fpp =
    FPP_2D (Hiemenz 2-D) or FPP_AXISYM (Homann axisymmetric); the closed
    form equals the algebraic identity rho * u_inf * sqrt(a * nu) * fpp.
    The station is where the inviscid edge velocity reaches u_inf
    (u_e = a * s = u_inf); tau_w scales linearly with u_e in the
    similarity layer, so other near-stagnation stations scale with
    u_e / u_inf.
    """
    _check_positive(rho, "density rho")
    _check_positive(nu, "kinematic viscosity nu")
    _check_positive(a, "stagnation velocity gradient a")
    _check_positive(u_inf, "freestream speed u_inf")
    fpp = FPP_2D if _regime(flow_type) == "hiemenz-2d" else FPP_AXISYM
    mu = rho * nu
    return mu * u_inf * math.sqrt(a / nu) * fpp


def skin_friction_coefficient(rho, u_inf, tau_w):
    """Local skin-friction coefficient Cf = 2 tau_w / (rho u_inf^2).

    Based on the freestream dynamic pressure 0.5 * rho * u_inf^2.
    """
    _check_positive(rho, "density rho")
    _check_positive(u_inf, "freestream speed u_inf")
    if not (tau_w >= 0.0):
        raise ValueError("wall shear tau_w must be non-negative, got %r"
                         % (tau_w,))
    return 2.0 * tau_w / (rho * u_inf * u_inf)


def swept_stagnation_gradient(u_inf, radius, sweep_deg):
    """Chordwise stagnation velocity gradient a (1/s) of a swept edge.

    a = 2.0 * u_inf * cos(sweep_deg) / radius for an infinite yawed
    cylinder or swept leading edge of radius radius at sweep angle
    sweep_deg. The swept (infinite yawed) stagnation line obeys the 2-D
    Hiemenz solution in the crossflow plane (independence-principle
    paraphrase, standard engineering methodology), with the chordwise
    pressure gradient driven by the velocity component normal to the
    leading edge u_n = u_inf * cos(sweep), so the 2-D Hiemenz constants
    apply in that plane. sweep_deg = 0 reproduces the unswept cylinder
    gradient 2 u_inf / radius.
    """
    _check_positive(u_inf, "freestream speed u_inf")
    _check_positive(radius, "body radius")
    if abs(sweep_deg) > 90.0:
        raise ValueError(
            "sweep angle magnitude must be at most 90 degrees, got %r"
            % (sweep_deg,))
    return (CYLINDER_GRADIENT_COEF * u_inf
            * math.cos(math.radians(sweep_deg)) / radius)
