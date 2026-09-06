"""Main rotor sizing for a single-main-rotor rotorcraft (weight-borne hover).

Pure stdlib, deterministic, closed form. This leaf sizes the MAIN rotor
from the takeoff weight and the design ceilings in the momentum-theory
weight-borne hover reference, thrust T = m * g0: the disk area and radius
from the weight against the chosen main-rotor-disk-loading ceiling
(A = T / DL_max, R = sqrt(A / PI)), the hover thrust coefficient CT at
the rotor tip speed, the rotor solidity closure from the ct-over-sigma
design point (sigma = CT / (CT/sigma)_design), the total blade area and
the constant blade chord from the blade count on rectangular blades, and
the rotor tip Mach at the tip speed.

Sizing only: no rotor power, no inflow solve, no figure of merit, no
blade-element sections, no compressibility corrections beyond the tip
Mach check, no structural or dynamics content, no RNG. The geometry
consuming rotorcraft performance leaves (hover power, forward flight,
turn, climb, autorotation, ground effect) all consume a given rotor;
this leaf produces the geometry they consume. All quantities SI (N, m,
m2, Pa, m/s). All functions raise ValueError on non-physical inputs.
"""

import math

G0 = 9.80665
PI = math.pi
RHO_SL = 1.225
A0_SL = 340.3


def disk_area_and_radius(thrust, disk_loading_max):
    """Disk area A = thrust / disk_loading_max (m2) and radius
    R = sqrt(A / PI) (m), the disk sized exactly at the ceiling.

    ValueError if thrust <= 0 or disk_loading_max <= 0.
    """
    if thrust <= 0:
        raise ValueError("thrust must be > 0")
    if disk_loading_max <= 0:
        raise ValueError("disk_loading_max must be > 0")
    area = thrust / disk_loading_max
    radius = math.sqrt(area / PI)
    return area, radius


def hover_thrust_coefficient(thrust, rho, radius, tip_speed):
    """Hover thrust coefficient CT = thrust / (rho * area * tip_speed**2),
    with area = PI * radius**2 computed inside; dimensionless.

    tip_speed is the rotor tip speed Vtip = Omega * R in m/s. At the
    sized disk (thrust over area equals the ceiling) the identity
    CT = disk_loading_max / (rho * tip_speed**2) holds, so CT is
    independent of the rotor size. ValueError if thrust <= 0, rho <= 0,
    radius <= 0 or tip_speed <= 0.
    """
    if thrust <= 0:
        raise ValueError("thrust must be > 0")
    if rho <= 0:
        raise ValueError("rho must be > 0")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    if tip_speed <= 0:
        raise ValueError("tip_speed must be > 0")
    area = PI * radius ** 2
    return thrust / (rho * area * tip_speed ** 2)


def solidity_closure(thrust_coefficient, ct_over_sigma_design):
    """Rotor solidity sigma = thrust_coefficient / ct_over_sigma_design,
    dimensionless, the solidity the hover design point implies; the
    closure round trip sigma * ct_over_sigma_design equals the input CT.

    ValueError if thrust_coefficient <= 0 or ct_over_sigma_design <= 0.
    """
    if thrust_coefficient <= 0:
        raise ValueError("thrust_coefficient must be > 0")
    if ct_over_sigma_design <= 0:
        raise ValueError("ct_over_sigma_design must be > 0")
    return thrust_coefficient / ct_over_sigma_design


def blade_area_chord(solidity, area, blade_count, radius):
    """Total blade area A_b = solidity * area (m2) and the constant blade
    chord c = A_b / (blade_count * radius) (m) on rectangular blades.

    ValueError if solidity <= 0, area <= 0, radius <= 0, blade_count < 1
    or blade_count is not a positive integer.
    """
    if solidity <= 0:
        raise ValueError("solidity must be > 0")
    if area <= 0:
        raise ValueError("area must be > 0")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    if blade_count < 1 or not float(blade_count).is_integer():
        raise ValueError("blade_count must be a positive integer")
    blade_area = solidity * area
    chord = blade_area / (blade_count * radius)
    return blade_area, chord


def tip_mach(tip_speed, speed_of_sound):
    """Rotor tip Mach number M_tip = tip_speed / speed_of_sound,
    dimensionless.

    ValueError if tip_speed < 0 or speed_of_sound <= 0.
    """
    if tip_speed < 0:
        raise ValueError("tip_speed must be >= 0")
    if speed_of_sound <= 0:
        raise ValueError("speed_of_sound must be > 0")
    return tip_speed / speed_of_sound
