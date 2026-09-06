"""Deterministic delivered-thrust loss bookkeeping for a rocket nozzle.

Pure stdlib, math only, closed form. Computes the nozzle-side share of
the delivered-thrust loss chain of an attached-flow nozzle: the conical
divergence factor lambda = (1 + cos(alpha))/2 for a half-angle alpha,
the equivalent 80-percent-length Rao-class bell contour efficiency, the
turbulent flat-plate boundary-layer displacement-thickness growth over
the divergent length, and the combined delivered thrust and delivered
Isp. The ideal attached-flow exit state (ve, pe, Ae, mdot at the
geometry) is an input from the nozzle-design leaf, never re-derived
here; off-design overexpansion past the separation limit is the domain
of rocket-nozzle-flow-separation, not this chain.
"""

import math

G0 = 9.80665  # m/s^2, standard gravity (sibling rocket convention)
ETA_BELL_DEFAULT = 0.98  # documented typical contour efficiency of the
                         # equivalent 80-percent-length Rao-class bell
ALPHA_REF_DEG = 15.0     # comparison conical half-angle for the bell ratio
TURB_COEFF = 0.37  # turbulent flat-plate growth coefficient (1/7-power law)
DELTA_STAR_OVER_DELTA = 1.0 / 8.0    # 1/7-power profile shape ratio
THETA_OVER_DELTA = 7.0 / 72.0        # so theta = (7/9) * delta_star exactly


def conical_divergence_factor(alpha_deg):
    """Axial divergence factor lambda = (1 + cos(alpha)) / 2 of a cone.

    Fraction of the ideal axial momentum thrust delivered by a conical
    divergent section of half-angle alpha: the velocity vectors leave
    the wall at angle alpha to the axis, so only the cosine-projected
    component contributes to axial thrust. lambda(0 deg) tends to 1,
    lambda(60 deg) = 0.75 exactly, lambda(15 deg) = 0.982963.
    """
    if alpha_deg <= 0.0 or alpha_deg >= 90.0:
        raise ValueError("alpha_deg must be in (0, 90)")
    return (1.0 + math.cos(math.radians(alpha_deg))) / 2.0


def bell_contour_efficiency(eta_bell=ETA_BELL_DEFAULT):
    """Validated bell/parabolic-contour contour efficiency parameter.

    Documented typical 0.98 for a Rao-class parabolic contour at about
    80 percent of the equivalent 15-degree conical length; allowed as a
    parameter in (0, 1]. Acts on the momentum term exactly where the
    conical divergence factor would act.
    """
    if not 0.0 < eta_bell <= 1.0:
        raise ValueError("eta_bell must be in (0, 1]")
    return eta_bell


def bell_relative_to_conical(eta_bell=ETA_BELL_DEFAULT,
                             alpha_deg=ALPHA_REF_DEG):
    """Contour-only efficiency of the bell relative to the cone it replaces.

    eta_bell / lambda(alpha_deg): 0.996986 at the defaults (0.98 contour
    against the 15-degree cone), exactly 1.0 when eta_bell equals
    lambda(15 deg). The delivered comparison additionally carries the
    shorter bell wall's smaller boundary-layer growth.
    """
    return bell_contour_efficiency(eta_bell) / conical_divergence_factor(alpha_deg)


def turbulent_displacement_thickness(length_m, vel_ms, rho_kgm3, mu_pas):
    """Exit displacement thickness of the turbulent wall layer, in meters.

    Flat-plate growth over the divergent length L with edge conditions
    at the exit: Re_L = rho * vel * L / mu, delta = 0.37 * L *
    Re_L**(-0.2), then delta_star = delta / 8 for the 1/7-power velocity
    profile. The throat boundary layer is neglected.
    """
    for value, name in ((length_m, "length_m"), (vel_ms, "vel_ms"),
                        (rho_kgm3, "rho_kgm3"), (mu_pas, "mu_pas")):
        if value <= 0.0:
            raise ValueError("%s must be positive" % name)
    re_l = rho_kgm3 * vel_ms * length_m / mu_pas
    delta = TURB_COEFF * length_m * re_l ** (-0.2)
    return DELTA_STAR_OVER_DELTA * delta


def boundary_layer_loss_fraction(delta_star_m, r_exit_m):
    """Fractional loss of the momentum term to the exit boundary layer.

    1-D mass-flux correction: the wall layer removes the momentum flux
    rho * ve * theta through the annulus of momentum thickness theta
    over the exit perimeter, theta = (7/9) * delta_star for the
    1/7-power profile, so the fractional momentum loss is 2 * theta /
    r_exit = (14/9) * delta_star / r_exit to first order in
    delta_star / r_exit (thin layer).
    """
    if delta_star_m <= 0.0 or r_exit_m <= 0.0:
        raise ValueError("delta_star_m and r_exit_m must be positive")
    if delta_star_m >= r_exit_m:
        raise ValueError("delta_star_m must be below r_exit_m")
    return (14.0 / 9.0) * delta_star_m / r_exit_m


def effective_exit_area_ratio(area_ratio, delta_star_m, r_exit_m):
    """Displaced-core exit area ratio eps_eff = eps * (1 - d*/r)**2.

    The displacement thickness shrinks the inviscid core cross-section
    at the exit plane (internal flow): A_eff = pi * (r_exit -
    delta_star)**2, throat boundary layer neglected. The plus-sign
    displaced-wall form of external-flow displacement is NOT used.
    """
    if area_ratio <= 1.0:
        raise ValueError("area_ratio must exceed 1")
    if delta_star_m <= 0.0 or r_exit_m <= 0.0:
        raise ValueError("delta_star_m and r_exit_m must be positive")
    if delta_star_m >= r_exit_m:
        raise ValueError("delta_star_m must be below r_exit_m")
    return area_ratio * (1.0 - delta_star_m / r_exit_m) ** 2


def delivered_thrust(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2,
                     shape_factor, bl_loss_fraction):
    """Delivered thrust: shape*(1 - xi)*mdot*ve + (pe - pa)*Ae, in N.

    The divergence/contour shape factor and the boundary-layer momentum
    loss act on the momentum term only; the pressure term acts over the
    full geometric exit area and is unchanged by the thin wall layer.
    At shape_factor 1 and bl_loss_fraction 0 the chain reproduces the
    ideal thrust of the same state exactly (the no-loss identity).
    """
    if mdot_kgs <= 0.0 or ve_ms <= 0.0 or ae_m2 <= 0.0:
        raise ValueError("mdot_kgs, ve_ms and ae_m2 must be positive")
    if not 0.0 < shape_factor <= 1.0:
        raise ValueError("shape_factor must be in (0, 1]")
    if not 0.0 <= bl_loss_fraction < 1.0:
        raise ValueError("bl_loss_fraction must be in [0, 1)")
    momentum = shape_factor * (1.0 - bl_loss_fraction) * mdot_kgs * ve_ms
    return momentum + (pe_pa - pa_pa) * ae_m2


def delivered_isp(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2,
                  shape_factor, bl_loss_fraction, g0=G0):
    """Delivered specific impulse = delivered_thrust / (mdot * g0), in s."""
    if g0 <= 0.0:
        raise ValueError("g0 must be positive")
    return delivered_thrust(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2,
                            shape_factor, bl_loss_fraction) / (mdot_kgs * g0)
