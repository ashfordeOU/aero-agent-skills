#!/usr/bin/env python3
"""Single axial turbine stage velocity-triangle logic.

Convention (Dixon): flow angles are measured from the axial direction,
all angles in RADIANS. A turbine stage extracts work from the flow, so
the absolute flow angle falls across the rotor (alpha1 > alpha2 gives
positive specific work output). tan(beta) = u/ca - tan(alpha) relates
the relative flow angles beta to the absolute angles alpha at the same
axial station.

Quantities (SI units throughout):
- blade speed u in m/s
- axial velocity ca in m/s
- absolute flow angles alpha1 (rotor inlet), alpha2 (rotor outlet) in rad
- relative flow angles beta1 (rotor inlet), beta2 (rotor outlet) in rad
- specific work w = u*ca*(tan(alpha1) - tan(alpha2)) in J/kg, positive
  when the rotor turns the flow toward the axial direction (turbine)
- flow coefficient phi = ca/u, dimensionless
- stage loading psi = w/u^2, dimensionless (turbines run near 1-3)
- degree of reaction r = 1 - ca/(2*u)*(tan(alpha1) + tan(alpha2)),
  dimensionless; r = 0 is an impulse stage, r = 0.5 is a symmetric
  50% reaction stage
- row enthalpy loss coefficients zeta_n (nozzle/stator row) and
  zeta_r (rotor row), dimensionless, applied to the row-exit kinetic
  energy: nozzle loss = zeta_n*c1^2/2, rotor loss = zeta_r*w2^2/2
- total-to-total efficiency eta_tt = w/(w + nozzle_loss + rotor_loss)
- total-to-static efficiency eta_ts = w/(w + nozzle_loss + rotor_loss
  + c3^2/2), with the stage exit absolute angle alpha3 (axial exit
  alpha3 = 0 loses the full exit kinetic energy)

FAR-33 is referenced, not reproduced; the velocity-triangle relations
are common turbomachinery methodology summarized per standards-map.yaml.

Functions raise ValueError on non-physical inputs (u <= 0, ca <= 0,
zeta < 0) instead of returning nonsense or dividing by zero.
"""

import math


def specific_work(u, ca, alpha1, alpha2):
    """Specific work output w = u*ca*(tan(alpha1) - tan(alpha2)) in J/kg.

    Positive when the rotor turns the flow toward the axial direction
    (alpha1 > alpha2), which is the turbine (work-extracting) case.
    """
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    return u * ca * (math.tan(alpha1) - math.tan(alpha2))


def flow_coefficient(ca, u):
    """Flow coefficient phi = ca/u, dimensionless."""
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    return ca / u


def stage_loading(u, ca, alpha1, alpha2):
    """Stage loading psi = w/u^2, dimensionless.

    Turbine stages run at psi near 1 to 3, well above the compressor
    range, because the flow turns through larger angles.
    """
    return specific_work(u, ca, alpha1, alpha2) / (u * u)


def degree_of_reaction(ca, u, alpha1, alpha2):
    """Degree of reaction r = 1 - ca/(2*u)*(tan(alpha1) + tan(alpha2)).

    Dimensionless; r = 0 for an impulse stage (the whole enthalpy drop
    in the nozzle row) and r = 0.5 for a symmetric 50% reaction stage
    (equal enthalpy drops across the rotor and stator rows).
    """
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    return 1.0 - ca / (2.0 * u) * (math.tan(alpha1) + math.tan(alpha2))


def relative_angle(u, ca, alpha):
    """Relative flow angle beta = atan(u/ca - tan(alpha)) in rad.

    Same station relation as the compressor stage: tan(beta) = u/ca
    minus tan(alpha), with angles from the axial direction.
    """
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    return math.atan(u / ca - math.tan(alpha))


def blade_row_loss(ca, angle, zeta):
    """Row enthalpy loss zeta * (ca/cos(angle))^2 / 2 in J/kg.

    Pass the absolute flow angle alpha1 for the nozzle/stator row exit
    kinetic energy and the relative flow angle beta2 for the rotor row
    exit kinetic energy. zeta is the row enthalpy loss coefficient,
    dimensionless and non-negative.
    """
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    if zeta < 0:
        raise ValueError("zeta must be >= 0, got %r" % (zeta,))
    return zeta * (ca / math.cos(angle)) ** 2 / 2.0


def total_to_total_efficiency(u, ca, alpha1, alpha2, beta2, zeta_n=0.05,
                              zeta_r=0.05):
    """Total-to-total efficiency eta_tt = w/(w + nozzle_loss + rotor_loss).

    Dimensionless. The nozzle loss uses the rotor inlet absolute angle
    alpha1 and the rotor loss uses the rotor outlet relative angle beta2,
    both in rad. zeta_n and zeta_r default to 0.05 each.
    """
    w = specific_work(u, ca, alpha1, alpha2)
    loss_n = blade_row_loss(ca, alpha1, zeta_n)
    loss_r = blade_row_loss(ca, beta2, zeta_r)
    return w / (w + loss_n + loss_r)


def total_to_static_efficiency(u, ca, alpha1, alpha2, beta2, alpha3=0.0,
                               zeta_n=0.05, zeta_r=0.05):
    """Total-to-static efficiency eta_ts = w/(w + losses + c3^2/2).

    Dimensionless. Adds the stage exit kinetic energy c3^2/2 with the
    exit absolute angle alpha3 in rad (default 0, axial exit, so the
    full ca^2/2 is lost).
    """
    w = specific_work(u, ca, alpha1, alpha2)
    loss_n = blade_row_loss(ca, alpha1, zeta_n)
    loss_r = blade_row_loss(ca, beta2, zeta_r)
    c3_sq_half = (ca / math.cos(alpha3)) ** 2 / 2.0
    return w / (w + loss_n + loss_r + c3_sq_half)


def stage_properties(u, ca, alpha1, alpha2, zeta_n=0.05, zeta_r=0.05):
    """Full velocity-triangle turbine stage assessment as a dict.

    Computes beta2 = relative_angle(u, ca, alpha2) internally. Returns
    specific_work (J/kg), phi and psi and reaction and eta_tt
    (dimensionless), and the nozzle_loss and rotor_loss (J/kg).
    """
    w = specific_work(u, ca, alpha1, alpha2)
    beta2 = relative_angle(u, ca, alpha2)
    loss_n = blade_row_loss(ca, alpha1, zeta_n)
    loss_r = blade_row_loss(ca, beta2, zeta_r)
    return {
        "specific_work": w,
        "phi": flow_coefficient(ca, u),
        "psi": stage_loading(u, ca, alpha1, alpha2),
        "reaction": degree_of_reaction(ca, u, alpha1, alpha2),
        "eta_tt": w / (w + loss_n + loss_r),
        "nozzle_loss": loss_n,
        "rotor_loss": loss_r,
    }
