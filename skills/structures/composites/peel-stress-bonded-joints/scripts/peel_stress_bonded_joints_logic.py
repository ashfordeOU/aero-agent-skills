"""Peel stress at the overlap end of a single-lap bonded joint.

Pure stdlib logic for the AeroSkills leaf
skills/structures/composites/peel-stress-bonded-joints. Classical
Goland-Reissner (1944) single-lap analysis with identical adherends,
per unit width: the bending moment factor k from the load, adherend
geometry and elastic modulus, the edge moment at the overlap end, the
adhesive Winkler-foundation beam response that resolves the maximum
peel stress at the overlap end, the exponential peel-decay parameter
and the peel margin against an allowable peel strength.

SI units throughout: load per unit width P_pw in N/m, thicknesses in
m, elastic moduli in Pa, peel stress in Pa. All functions raise
ValueError on non-physical inputs.

The elastic in-plane shear transfer along the overlap is out of scope
here; the sibling leaf structures/composites/adhesive-bonded-joints
owns that bondline shear analysis.
"""

import math

SQRT2 = math.sqrt(2.0)


def _check_positive(value, name):
    if value <= 0.0:
        raise ValueError("%s must be positive" % name)


def _check_poisson(poisson_ratio):
    if not (-1.0 < poisson_ratio < 0.5):
        raise ValueError("poisson ratio must lie in (-1, 0.5)")


def bending_moment_factor(load_per_unit_width, adherend_thickness,
                          adherend_modulus, poisson_ratio,
                          overlap_half_length):
    """Return the Goland-Reissner bending moment factor k in (0, 1].

    u^2 = (3 (1 - nu^2) / 2) * P_pw / (E t^3), then
    k = cosh(u c) / (cosh(u c) + 2 sqrt(2) sinh(u c)). k tends to 1 as
    the load or the overlap half length c tends to zero (no-bending
    limit) and falls toward the classical long-overlap floor near
    0.261.
    """
    if load_per_unit_width < 0.0:
        raise ValueError("load per unit width must not be negative")
    _check_positive(adherend_thickness, "adherend thickness")
    _check_positive(adherend_modulus, "adherend modulus")
    _check_poisson(poisson_ratio)
    _check_positive(overlap_half_length, "overlap half length")
    u_squared = (3.0 * (1.0 - poisson_ratio * poisson_ratio) / 2.0) \
        * load_per_unit_width / (adherend_modulus * adherend_thickness ** 3)
    arg = math.sqrt(u_squared) * overlap_half_length
    cosh_arg = math.cosh(arg)
    sinh_arg = math.sinh(arg)
    return cosh_arg / (cosh_arg + 2.0 * SQRT2 * sinh_arg)


def peel_decay_coefficient(adhesive_modulus, adhesive_thickness,
                           adherend_modulus, adherend_thickness):
    """Return the classical exponential peel-decay parameter beta in 1/m.

    beta = sqrt(6 E_a / (t_a E t)), the decay rate of the peel stress
    away from the overlap end in the simplified peel models.
    """
    _check_positive(adhesive_modulus, "adhesive modulus")
    _check_positive(adhesive_thickness, "adhesive thickness")
    _check_positive(adherend_modulus, "adherend modulus")
    _check_positive(adherend_thickness, "adherend thickness")
    return math.sqrt(6.0 * adhesive_modulus
                     / (adhesive_thickness * adherend_modulus
                        * adherend_thickness))


def peel_stress_at_overlap_end(load_per_unit_width, adherend_thickness,
                               adherend_modulus, poisson_ratio,
                               adhesive_modulus, adhesive_thickness,
                               moment_factor):
    """Return the peel response dict at the overlap end.

    D = E t^3 / (12 (1 - nu^2)), M0 = k P_pw t / 2,
    lambda^4 = 3 (1 - nu^2) E_a / (E t^3 t_a),
    w0 = M0 / (2 lambda^2 D), sigma_peel = (E_a / t_a) w0.
    Returns {"peel_stress": sigma_peel, "edge_moment": M0,
    "lambda": lam} with the moment factor k passed in as
    moment_factor.
    """
    if load_per_unit_width < 0.0:
        raise ValueError("load per unit width must not be negative")
    _check_positive(adherend_thickness, "adherend thickness")
    _check_positive(adherend_modulus, "adherend modulus")
    _check_poisson(poisson_ratio)
    _check_positive(adhesive_modulus, "adhesive modulus")
    _check_positive(adhesive_thickness, "adhesive thickness")
    flexural_rigidity = adherend_modulus * adherend_thickness ** 3 \
        / (12.0 * (1.0 - poisson_ratio * poisson_ratio))
    lam = (3.0 * (1.0 - poisson_ratio * poisson_ratio) * adhesive_modulus
           / (adherend_modulus * adherend_thickness ** 3
              * adhesive_thickness)) ** 0.25
    edge_moment = moment_factor * load_per_unit_width * adherend_thickness / 2.0
    end_deflection = edge_moment / (2.0 * lam * lam * flexural_rigidity)
    peel_stress = (adhesive_modulus / adhesive_thickness) * end_deflection
    return {"peel_stress": peel_stress,
            "edge_moment": edge_moment,
            "lambda": lam}


def peel_margin(peel_stress, peel_strength_allowable):
    """Return the peel margin allowable / peel stress.

    A margin below one means the computed peel stress exceeds the
    peel strength allowable and the joint fails the peel-critical
    check.
    """
    _check_positive(peel_stress, "peel stress")
    _check_positive(peel_strength_allowable, "peel strength allowable")
    return peel_strength_allowable / peel_stress
