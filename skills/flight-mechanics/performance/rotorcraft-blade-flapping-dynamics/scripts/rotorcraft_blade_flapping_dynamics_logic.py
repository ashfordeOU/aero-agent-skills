"""Rotorcraft blade flapping dynamics: Lock number, hover coning, flap frequency ratio.

Pure stdlib, deterministic, no RNG. SI units throughout. Implements the
standard articulated-rotor blade flap model (Johnson Helicopter Theory
ch.4, Leishman Principles of Helicopter Aerodynamics ch.4): the blade
Lock number, the steady hover coning angle from the flap-moment balance,
and the rotating flap natural frequency ratio for a flap hinge offset.

This is the first blade-dynamics leaf in the rotorcraft subdomain: it
covers flap dynamics only, not rotor power, inflow, or ground resonance.
"""

import math

# Module constants
RHO_SL = 1.225        # kg/m3, sea-level standard air density
A_LIFT_DEFAULT = 5.73  # 1/rad, typical section lift-curve slope (published rotor Lock numbers fall in the 5-12 band)
PI = math.pi


def blade_flap_inertia_uniform(blade_mass_kg, radius_m):
    """Moment of inertia I_beta of a uniform blade about the flap hinge at the rotation axis.

    I_beta = blade_mass_kg * radius_m**2 / 3. Raises ValueError on
    non-positive mass or radius.
    """
    if blade_mass_kg <= 0:
        raise ValueError("blade_mass_kg must be positive")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    return blade_mass_kg * radius_m ** 2 / 3.0


def lock_number(rho, lift_slope, chord_m, radius_m, flap_inertia):
    """Blade Lock number gamma = rho * lift_slope * chord_m * radius_m**4 / flap_inertia.

    The Lock number is the ratio of aerodynamic flap moment to
    centrifugal restoring moment. Raises ValueError on any non-positive
    input.
    """
    if rho <= 0:
        raise ValueError("rho must be positive")
    if lift_slope <= 0:
        raise ValueError("lift_slope must be positive")
    if chord_m <= 0:
        raise ValueError("chord_m must be positive")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    if flap_inertia <= 0:
        raise ValueError("flap_inertia must be positive")
    return rho * lift_slope * chord_m * radius_m ** 4 / flap_inertia


def hover_coning_angle(gamma, theta0_rad, inflow_ratio):
    """Steady hover coning angle a0 = 0.5 * gamma * (theta0_rad / 4 - inflow_ratio / 3) rad.

    From the steady flap-moment balance for an untwisted centrally
    hinged blade with uniform inflow: the aerodynamic flap moment
    0.5 * rho * a * c * Omega**2 * R**4 * (theta0/4 - lambda/3) equals
    the centrifugal restoring moment I_beta * Omega**2 * a0, which
    solves to a0 = (gamma / 2) * (theta0/4 - lambda/3). Raises
    ValueError if gamma <= 0, theta0_rad < 0, or inflow_ratio < 0.
    """
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    if theta0_rad < 0:
        raise ValueError("theta0_rad must be non-negative")
    if inflow_ratio < 0:
        raise ValueError("inflow_ratio must be non-negative")
    return 0.5 * gamma * (theta0_rad / 4.0 - inflow_ratio / 3.0)


def flap_frequency_ratio(hinge_offset_fraction):
    """Rotating flap natural frequency ratio nu = sqrt(1 + 1.5 * e / (1 - e)).

    e = hinge_offset_fraction in [0, 1). Exact uniform-mass rotating
    flap frequency ratio about an offset hinge, algebraically identical
    to nu**2 = (1 - 3*e/2 + e**3/2) / (1 - e)**3. At e = 0 the central
    hinge limit is exactly 1.0 (1/rev). Raises ValueError if e < 0 or
    e >= 1.
    """
    if hinge_offset_fraction < 0:
        raise ValueError("hinge_offset_fraction must be non-negative")
    if hinge_offset_fraction >= 1:
        raise ValueError("hinge_offset_fraction must be below 1")
    return math.sqrt(1.0 + 1.5 * hinge_offset_fraction / (1.0 - hinge_offset_fraction))


def blade_flapping_summary(blade_mass_kg, radius_m, chord_m, theta0_rad,
                           inflow_ratio, hinge_offset_fraction,
                           lift_slope=A_LIFT_DEFAULT, rho=RHO_SL):
    """One-call blade flapping assessment dict for a uniform untwisted blade.

    Returns {lock_number, flap_inertia_kg_m2, coning_angle_rad,
    coning_angle_deg, flap_frequency_ratio, flap_frequency_per_rev}.
    ValueErrors propagate from the underlying checks. The flap frequency
    per revolution equals the frequency ratio nu: the flapping natural
    frequency scales with rotor speed, so nu is already expressed in
    units of rotor revolutions and no rotor speed input is needed.
    """
    inertia = blade_flap_inertia_uniform(blade_mass_kg, radius_m)
    gamma = lock_number(rho, lift_slope, chord_m, radius_m, inertia)
    a0_rad = hover_coning_angle(gamma, theta0_rad, inflow_ratio)
    nu = flap_frequency_ratio(hinge_offset_fraction)
    return {
        "lock_number": gamma,
        "flap_inertia_kg_m2": inertia,
        "coning_angle_rad": a0_rad,
        "coning_angle_deg": a0_rad * 180.0 / PI,
        "flap_frequency_ratio": nu,
        "flap_frequency_per_rev": nu,
    }
