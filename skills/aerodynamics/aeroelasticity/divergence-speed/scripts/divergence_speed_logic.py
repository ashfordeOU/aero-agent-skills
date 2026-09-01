#!/usr/bin/env python3
"""Static aeroelastic divergence logic (typical section paraphrase).

Common-knowledge summary (public-domain textbook content, e.g.
Bisplinghoff/Ashley/Halfman and Hodges/Pierce; standards-map.yaml
naca-tr-824: public domain): a lifting surface whose aerodynamic center
lies ahead of the shear center sees a destabilizing torsional moment
from the lift. The moment grows with dynamic pressure, and at the
divergence dynamic pressure it overcomes the torsional stiffness so the
twist, hence the lift, grows without bound. For the typical section:

    q_div = k_theta / (S * c * C_Lalpha * e)

with k_theta the torsional stiffness about the shear center axis
(N m per rad; for a beam model this is the product G * K_theta of the
shear modulus G and the torsion constant K_theta), S the reference
area (m^2), c the chord (m), C_Lalpha the lift curve slope per radian,
and e the offset ratio, the aerodynamic-center-to-shear-center distance
divided by the chord, positive when the aerodynamic center lies ahead
of the shear center. The divergence speed follows from the dynamic
pressure at the flight density, V_div = sqrt(2 * q_div / rho), with the
ISA sea level density 1.225 kg/m^3 as the default. The divergence
margin is m = V_div / V_design, and common design practice keeps m at
or above 1.15; a margin below the threshold flags divergence risk.
When e <= 0 the aerodynamic center is at or aft of the shear center,
the torsion is restoring, and no divergence exists: the divergence
formulas are out of domain.
"""

import math

ISA_SEA_LEVEL_DENSITY = 1.225  # kg/m^3, ISA standard atmosphere at sea level
MIN_DIVERGENCE_MARGIN = 1.15  # common design practice threshold (rule of thumb)


def _require_positive(name, value):
    if not (isinstance(value, (int, float)) and value > 0.0):
        raise ValueError("%s must be positive, got %r" % (name, value))


def divergence_dynamic_pressure(k_theta, area, chord, cl_alpha, offset_ratio):
    """Divergence dynamic pressure q_div in Pa.

    q_div = k_theta / (S * c * C_Lalpha * e). k_theta in N m per rad
    (torsional stiffness, the G * K_theta product for a beam model),
    area S in m^2, chord c in m, cl_alpha per radian, offset_ratio e
    dimensionless. Raises when e <= 0: an aerodynamic center at or aft
    of the shear center has no divergence mechanism.
    """
    _require_positive("torsional stiffness k_theta", k_theta)
    _require_positive("reference area S", area)
    _require_positive("chord c", chord)
    _require_positive("lift curve slope C_Lalpha", cl_alpha)
    if not (isinstance(offset_ratio, (int, float)) and offset_ratio > 0.0):
        raise ValueError(
            "offset ratio e must be positive (aerodynamic center ahead of the "
            "shear center); e <= 0 means no divergence mechanism, got %r"
            % (offset_ratio,)
        )
    return k_theta / (area * chord * cl_alpha * offset_ratio)


def divergence_speed(q_div, rho=ISA_SEA_LEVEL_DENSITY):
    """Divergence speed in m/s from the divergence dynamic pressure.

    V_div = sqrt(2 * q_div / rho). Default density is the ISA sea level
    value 1.225 kg/m^3; pass the flight density for altitude cases.
    """
    _require_positive("divergence dynamic pressure q_div", q_div)
    _require_positive("air density rho", rho)
    return math.sqrt(2.0 * q_div / rho)


def divergence_margin(v_div, v_design):
    """Divergence margin ratio m = V_div / V_design."""
    _require_positive("divergence speed V_div", v_div)
    _require_positive("design dive speed V_design", v_design)
    return v_div / v_design


def assess_divergence_margin(v_div, v_design, min_margin=MIN_DIVERGENCE_MARGIN):
    """Assess the divergence margin against the required minimum.

    Returns (margin, acceptable). A margin at or above min_margin (the
    design practice default 1.15) is acceptable; below it the lifting
    surface is flagged at divergence risk and needs more torsional
    stiffness. min_margin must be at least 1.0.
    """
    margin = divergence_margin(v_div, v_design)
    if not (min_margin >= 1.0):
        raise ValueError(
            "required margin must be at least 1.0, got %r" % (min_margin,)
        )
    return (margin, margin >= min_margin)


def stiffness_for_margin(v_design, area, chord, cl_alpha, offset_ratio,
                         margin=MIN_DIVERGENCE_MARGIN,
                         rho=ISA_SEA_LEVEL_DENSITY):
    """Torsional stiffness k_theta needed for a target divergence margin.

    Sizes k_theta so that V_div reaches margin * V_design: the required
    dynamic pressure is q = 0.5 * rho * (margin * V_design)^2 and
    k_theta = q * S * c * C_Lalpha * e. The margin requirement must be
    at least 1.0.
    """
    if not (margin >= 1.0):
        raise ValueError(
            "required margin must be at least 1.0, got %r" % (margin,)
        )
    _require_positive("design dive speed V_design", v_design)
    _require_positive("reference area S", area)
    _require_positive("chord c", chord)
    _require_positive("lift curve slope C_Lalpha", cl_alpha)
    _require_positive("air density rho", rho)
    if not (isinstance(offset_ratio, (int, float)) and offset_ratio > 0.0):
        raise ValueError(
            "offset ratio e must be positive (aerodynamic center ahead of the "
            "shear center); e <= 0 means no divergence mechanism, got %r"
            % (offset_ratio,)
        )
    q_target = 0.5 * rho * (margin * v_design) ** 2
    return q_target * area * chord * cl_alpha * offset_ratio
