"""Thermal buckling of restrained aerospace structure (pure stdlib).

Computes the elastic buckling stress of a flat plate under uniform
compression, the in-plane compressive stress built up by a constrained
temperature rise under uniaxial or biaxial restraint, the critical
temperature rise that drives a skin panel to its buckling stress, and
the critical temperature rise of an Euler column between rigid
supports. The plate and column buckle because a restrained temperature
rise builds the compressive load, not because an external load is
applied. Linear elastic buckling only: post-buckling and
large-deflection behavior are out of scope.

SI units throughout: E in Pa, alpha in 1/K, thickness/width/lengths in
m, stresses in Pa, temperature rise in K.

Methodology is standard engineering (FAR 25 referenced, not
reproduced); no material constants are hard-coded, every input is an
explicit argument.
"""

import math

# Physically admissible Poisson ratio range for an isotropic solid:
# stability of the plate rigidity requires 1 - nu**2 > 0 (nu inside
# (-1, 1)); solids require nu < 0.5 (the incompressible limit).
_POISSON_MIN = -1.0
_POISSON_MAX = 0.5


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _check_poisson(poisson):
    _require(_POISSON_MIN < poisson < _POISSON_MAX,
             "poisson must be inside (-1, 0.5)")


def plate_buckling_stress(elastic_modulus, poisson, thickness, width,
                          k_coefficient=4.0):
    """Elastic buckling stress of a flat plate under uniform compression.

    sigma_cr = k_coefficient * pi**2 * D / (width**2 * thickness) with
    the flexural rigidity D = E * thickness**3 / (12 * (1 - nu**2)).
    k_coefficient = 4.0 is the simply supported long-plate value.
    """
    _require(elastic_modulus > 0, "elastic_modulus must be positive")
    _require(thickness > 0, "thickness must be positive")
    _require(width > 0, "width must be positive")
    _require(k_coefficient > 0, "k_coefficient must be positive")
    _check_poisson(poisson)
    rigidity = (elastic_modulus * thickness**3
                / (12.0 * (1.0 - poisson**2)))
    return (k_coefficient * math.pi**2 * rigidity
            / (width**2 * thickness))


def thermal_stress_uniaxial(elastic_modulus, alpha, temp_rise):
    """In-plane compressive stress of a uniaxially restrained member.

    sigma = E * alpha * dT: the temperature rise dT wants free strain
    alpha * dT and full restraint converts it into stress. Positive dT
    means compression in the restrained direction.
    """
    _require(elastic_modulus > 0, "elastic_modulus must be positive")
    _require(alpha >= 0, "alpha must be non-negative")
    _require(temp_rise >= 0, "temp_rise must be non-negative")
    return elastic_modulus * alpha * temp_rise


def thermal_stress_biaxial(elastic_modulus, poisson, alpha, temp_rise):
    """In-plane compressive stress of a biaxially restrained plate.

    sigma = E * alpha * dT / (1 - nu): restraint in both in-plane
    directions adds the transverse reaction, so the stress is higher
    than the uniaxial value by the factor 1 / (1 - nu).
    """
    _require(elastic_modulus > 0, "elastic_modulus must be positive")
    _require(alpha >= 0, "alpha must be non-negative")
    _require(temp_rise >= 0, "temp_rise must be non-negative")
    _check_poisson(poisson)
    return elastic_modulus * alpha * temp_rise / (1.0 - poisson)


def critical_temp_plate(elastic_modulus, poisson, alpha, thickness,
                        width, k_coefficient=4.0, restraint="uniaxial"):
    """Temperature rise that drives a restrained plate to buckling.

    Set the thermal stress equal to the plate buckling stress and solve
    for dT: dT = sigma_cr / (E * alpha) for uniaxial restraint and
    dT = sigma_cr * (1 - nu) / (E * alpha) for biaxial restraint. An
    alpha of zero can never buckle the plate, so it is rejected.
    """
    _require(restraint in ("uniaxial", "biaxial"),
             'restraint must be "uniaxial" or "biaxial"')
    _require(alpha > 0,
             "alpha must be positive for a critical temperature rise")
    sigma_cr = plate_buckling_stress(elastic_modulus, poisson, thickness,
                                     width, k_coefficient)
    if restraint == "uniaxial":
        return sigma_cr / (elastic_modulus * alpha)
    return sigma_cr * (1.0 - poisson) / (elastic_modulus * alpha)


def column_critical_temp(elastic_modulus, alpha, effective_length,
                         radius_of_gyration):
    """Temperature rise that buckles an Euler column between rigid supports.

    The axial thermal load is P = alpha * E * A * dT and the Euler
    buckling load is P_cr = pi**2 * E * I / L_eff**2 with I = A * r**2,
    so the area cancels and dT_cr = pi**2 * r**2 / (alpha * L_eff**2).
    The modulus cancels too but is still validated as an input.
    """
    _require(elastic_modulus > 0, "elastic_modulus must be positive")
    _require(alpha > 0, "alpha must be positive")
    _require(effective_length > 0, "effective_length must be positive")
    _require(radius_of_gyration > 0,
             "radius_of_gyration must be positive")
    return (math.pi**2 * radius_of_gyration**2
            / (alpha * effective_length**2))


def thermal_buckling_assessment(elastic_modulus, poisson, alpha,
                                thickness, width, temp_rise,
                                k_coefficient=4.0,
                                restraint="uniaxial"):
    """Full thermal-stability check of a hot restrained panel.

    Returns a dict with buckling_stress_Pa, thermal_stress_Pa,
    critical_temp_rise_K and margin = buckling_stress / thermal_stress
    - 1. A positive margin means the panel is safe at this temperature
    rise. The margin is undefined at zero temperature rise, so
    temp_rise must be positive here.
    """
    _require(temp_rise > 0,
             "temp_rise must be positive for a buckling margin")
    sigma_cr = plate_buckling_stress(elastic_modulus, poisson, thickness,
                                     width, k_coefficient)
    dT_cr = critical_temp_plate(elastic_modulus, poisson, alpha,
                                thickness, width, k_coefficient,
                                restraint)
    if restraint == "uniaxial":
        sigma_thermal = thermal_stress_uniaxial(elastic_modulus, alpha,
                                                temp_rise)
    else:
        sigma_thermal = thermal_stress_biaxial(elastic_modulus, poisson,
                                               alpha, temp_rise)
    return {
        "buckling_stress_Pa": sigma_cr,
        "thermal_stress_Pa": sigma_thermal,
        "critical_temp_rise_K": dT_cr,
        "margin": sigma_cr / sigma_thermal - 1.0,
    }
