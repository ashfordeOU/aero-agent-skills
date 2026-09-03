"""Propellant tank sizing for a spacecraft propulsion bus.

Pure stdlib sizing model: converts a propellant mass budget into the
liquid volume, adds the ullage volume for the required ullage fraction,
computes the spherical tank volume and radius, sizes the membrane wall
thickness from the burst pressure and the material allowable, estimates
the tank shell mass, sizes the pressurant gas mass for the regulated or
blowdown pressurization scheme, and reports the blowdown pressure range
and a tank-mass-fraction verdict.

All inputs and outputs are SI (kg, m3, m, Pa, K). Deterministic and
offline. Reference: standard spacecraft tank sizing methodology in the
ECSS space engineering context (cited reference-only, not reproduced).
"""

import math

# Module constants (documented typical values; all are program inputs
# through the function arguments).
G0 = 9.80665  # standard gravity, m/s2 (reserved for impulse bookkeeping)
DEFAULT_ULLAGE_FRACTION = 0.06  # ullage as fraction of TOTAL tank volume
DEFAULT_BOSS_FACTOR = 1.10  # shell mass increase for bosses and welds
GAS_CONSTANT_HE = 2077.0  # helium gas constant, J/(kg K)

PRESSURIZATION_MODES = ("regulated", "blowdown")

# Tank mass fraction sanity budget (typical spacecraft bus allowance).
TANK_MASS_FRACTION_LIMIT = 0.20


def propellant_volume_m3(mass_kg, density_kg_m3):
    """Return the liquid propellant volume V_p = m / rho."""
    if mass_kg <= 0.0:
        raise ValueError("propellant mass must be > 0")
    if density_kg_m3 <= 0.0:
        raise ValueError("propellant density must be > 0")
    return mass_kg / density_kg_m3


def ullage_volume_m3(prop_vol_m3, ullage_fraction):
    """Return the ullage volume for a fraction of the TOTAL volume.

    ullage fraction u means V_ullage = V_p * u / (1 - u), since the
    propellant occupies (1 - u) of the total tank volume.
    """
    if prop_vol_m3 <= 0.0:
        raise ValueError("propellant volume must be > 0")
    if not 0.0 < ullage_fraction < 1.0:
        raise ValueError("ullage fraction must be in (0, 1)")
    return prop_vol_m3 * ullage_fraction / (1.0 - ullage_fraction)


def tank_volume_m3(prop_vol_m3, ullage_fraction):
    """Return the total tank volume V_t = V_p / (1 - u)."""
    if prop_vol_m3 <= 0.0:
        raise ValueError("propellant volume must be > 0")
    if not 0.0 < ullage_fraction < 1.0:
        raise ValueError("ullage fraction must be in (0, 1)")
    return prop_vol_m3 / (1.0 - ullage_fraction)


def sphere_radius_m(volume_m3):
    """Return the radius of a sphere of the given volume."""
    if volume_m3 <= 0.0:
        raise ValueError("volume must be > 0")
    return (3.0 * volume_m3 / (4.0 * math.pi)) ** (1.0 / 3.0)


def burst_pressure_pa(meop_pa, burst_factor):
    """Return the burst (proof design) pressure = factor * MEOP."""
    if meop_pa <= 0.0:
        raise ValueError("MEOP must be > 0")
    if burst_factor <= 1.0:
        raise ValueError("burst factor must be > 1")
    return burst_factor * meop_pa


def wall_thickness_m(burst_pa, radius_m, material_ultimate_pa):
    """Return the thin-walled sphere membrane thickness t = p*r/(2*sigma)."""
    if burst_pa <= 0.0:
        raise ValueError("burst pressure must be > 0")
    if radius_m <= 0.0:
        raise ValueError("radius must be > 0")
    if material_ultimate_pa <= 0.0:
        raise ValueError("material ultimate must be > 0")
    return burst_pa * radius_m / (2.0 * material_ultimate_pa)


def shell_mass_kg(radius_m, thickness_m, material_density_kg_m3, boss_factor):
    """Return the tank shell mass 4*pi*r^2*t*rho*boss_factor."""
    if radius_m <= 0.0:
        raise ValueError("radius must be > 0")
    if thickness_m <= 0.0:
        raise ValueError("thickness must be > 0")
    if material_density_kg_m3 <= 0.0:
        raise ValueError("material density must be > 0")
    if boss_factor <= 0.0:
        raise ValueError("boss factor must be > 0")
    surface = 4.0 * math.pi * radius_m * radius_m
    return surface * thickness_m * material_density_kg_m3 * boss_factor


def pressurant_mass_kg(pressure_pa, ullage_vol_m3, temperature_K, gas_constant):
    """Return the pressurant gas mass from the ideal gas law m = P*V/(R*T).

    The pressure is the operating pressure of the scheme: MEOP for a
    regulated system, the initial (MEOP) pressure for a blowdown system.
    """
    if pressure_pa <= 0.0:
        raise ValueError("pressure must be > 0")
    if ullage_vol_m3 < 0.0:
        raise ValueError("ullage volume must be >= 0")
    if temperature_K <= 0.0:
        raise ValueError("pressurant temperature must be > 0")
    if gas_constant <= 0.0:
        raise ValueError("gas constant must be > 0")
    return pressure_pa * ullage_vol_m3 / (gas_constant * temperature_K)


def blowdown_pressure_range(meop_pa, blowdown_ratio):
    """Return the blowdown pressure range dict for a given ratio.

    The system starts at MEOP and falls to MEOP/ratio as the gas
    expands into the propellant volume.
    """
    if meop_pa <= 0.0:
        raise ValueError("MEOP must be > 0")
    if blowdown_ratio <= 1.0:
        raise ValueError("blowdown ratio must be > 1")
    return {
        "p_initial_pa": meop_pa,
        "p_final_pa": meop_pa / blowdown_ratio,
    }


def analyze(inputs):
    """Run the full tank sizing on an inputs dict and return the result.

    Required keys: propellant_mass_kg, propellant_density_kg_m3,
    pressurization ("regulated" or "blowdown"), meop_pa,
    material_ultimate_pa. Optional keys with documented typical
    defaults: ullage_fraction, burst_factor, material_density_kg_m3,
    boss_factor, pressurant_temperature_K, gas_constant, blowdown_ratio
    (required when pressurization is "blowdown").

    Returns the propellant volume, ullage volume, tank volume, sphere
    radius, burst pressure, wall thickness, shell mass, tank mass
    fraction, pressurant mass, the blowdown pressure range for blowdown
    systems, and the verdict "tank-sizing-pass" when the tank mass
    fraction stays within the typical 0.20 budget else
    "tank-sizing-fail".
    """
    mass_kg = inputs["propellant_mass_kg"]
    density_kg_m3 = inputs["propellant_density_kg_m3"]
    pressurization = inputs["pressurization"]
    meop_pa = inputs["meop_pa"]
    material_ultimate_pa = inputs["material_ultimate_pa"]

    if mass_kg <= 0.0:
        raise ValueError("propellant mass must be > 0")
    if density_kg_m3 <= 0.0:
        raise ValueError("propellant density must be > 0")
    if meop_pa <= 0.0:
        raise ValueError("MEOP must be > 0")
    if material_ultimate_pa <= 0.0:
        raise ValueError("material ultimate must be > 0")
    if pressurization not in PRESSURIZATION_MODES:
        raise ValueError(
            "pressurization must be 'regulated' or 'blowdown'"
        )
    if pressurization == "blowdown" and inputs.get("blowdown_ratio") is None:
        raise ValueError("blowdown requires a blowdown ratio")
    if inputs.get("pressurant_temperature_K", 293.0) <= 0.0:
        raise ValueError("pressurant temperature must be > 0")

    ullage_fraction = inputs.get("ullage_fraction", DEFAULT_ULLAGE_FRACTION)
    burst_factor = inputs.get("burst_factor", 2.0)
    material_density = inputs.get("material_density_kg_m3", 4430.0)
    boss_factor = inputs.get("boss_factor", DEFAULT_BOSS_FACTOR)
    temperature_K = inputs.get("pressurant_temperature_K", 293.0)
    gas_constant = inputs.get("gas_constant", GAS_CONSTANT_HE)
    blowdown_ratio = inputs.get("blowdown_ratio")

    prop_vol = propellant_volume_m3(mass_kg, density_kg_m3)
    ullage_vol = ullage_volume_m3(prop_vol, ullage_fraction)
    tank_vol = tank_volume_m3(prop_vol, ullage_fraction)
    radius = sphere_radius_m(tank_vol)
    burst = burst_pressure_pa(meop_pa, burst_factor)
    thickness = wall_thickness_m(burst, radius, material_ultimate_pa)
    shell = shell_mass_kg(radius, thickness, material_density, boss_factor)
    mass_fraction = shell / mass_kg
    pressurant = pressurant_mass_kg(
        meop_pa, ullage_vol, temperature_K, gas_constant
    )

    result = {
        "propellant_volume_m3": prop_vol,
        "ullage_volume_m3": ullage_vol,
        "tank_volume_m3": tank_vol,
        "radius_m": radius,
        "burst_pressure_pa": burst,
        "wall_thickness_m": thickness,
        "shell_mass_kg": shell,
        "tank_mass_fraction": mass_fraction,
        "pressurant_mass_kg": pressurant,
        "verdict": (
            "tank-sizing-pass"
            if mass_fraction <= TANK_MASS_FRACTION_LIMIT
            else "tank-sizing-fail"
        ),
    }
    if pressurization == "blowdown":
        result["blowdown_pressure_range"] = blowdown_pressure_range(
            meop_pa, blowdown_ratio
        )
    return result


def worked_example():
    """Return the hydrazine monopropellant sizing result (spec anchor)."""
    return analyze(
        {
            "propellant_mass_kg": 100.0,
            "propellant_density_kg_m3": 1008.0,
            "ullage_fraction": 0.06,
            "pressurization": "regulated",
            "meop_pa": 2.0e6,
            "burst_factor": 2.0,
            "material_ultimate_pa": 900.0e6,
            "material_density_kg_m3": 4430.0,
            "boss_factor": 1.10,
            "pressurant_temperature_K": 293.0,
            "gas_constant": GAS_CONSTANT_HE,
        }
    )


if __name__ == "__main__":
    result = worked_example()
    for key, value in sorted(result.items()):
        print(key, value)
