"""Hydraulic linear actuator sizing logic (pure stdlib, deterministic).

Sizes a linear hydraulic actuator for an aircraft control or utility
load: required piston area and bore from the load and system pressure
with the pressure-margin factor and mechanical efficiency, annulus
(rod-side) area for the retract direction, rod diameter from Euler
column buckling over the extended rod length with the design factor,
nearest preferred bore and rod diameters at or above the requirements,
rod stress, buckling margin and an actuator mass estimate.

All inputs are SI (N, Pa, m, kg) unless a function signature states
mm. Non-physical inputs raise ValueError. Module constants document the
design assumptions (pressure margin 1.10, mechanical efficiency 0.90,
buckling factor of safety 2.0, pinned ends K = 1.0, steel rod modulus
205 GPa and density 7850 kg/m3, rod yield 1100 MPa, compact preferred
bore and rod lists).
"""

import math

# Design margins and model constants (documented, per leaf spec).
PRESSURE_MARGIN = 1.10
MECHANICAL_EFFICIENCY = 0.90
BUCKLING_FACTOR_OF_SAFETY = 2.0
END_FIXITY_K = 1.0  # pinned ends
MODULUS_ROD = 205e9  # Pa, steel rod
ROD_DENSITY = 7850.0  # kg/m3
STEEL_YIELD = 1100e6  # Pa, rod material yield
PREFERRED_BORES_MM = (25.0, 32.0, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0)
PREFERRED_RODS_MM = (12.0, 16.0, 20.0, 25.0, 32.0, 40.0, 50.0, 63.0)


def piston_area(load_N, pressure_Pa):
    """Required piston area m2 = load * margin / (pressure * efficiency).

    The pressure-margin factor covers dynamic and seal effects on the
    required load; the mechanical efficiency divides the pressure side
    because the actuator converts hydraulic power to mechanical work
    imperfectly.
    """
    if load_N <= 0:
        raise ValueError("load must be positive")
    if pressure_Pa <= 0:
        raise ValueError("pressure must be positive")
    return load_N * PRESSURE_MARGIN / (pressure_Pa * MECHANICAL_EFFICIENCY)


def bore_diameter(area_m2):
    """Bore diameter m from a piston area: sqrt(4 * A / pi)."""
    if area_m2 <= 0:
        raise ValueError("piston area must be positive")
    return math.sqrt(4.0 * area_m2 / math.pi)


def annulus_area(bore_m, rod_m):
    """Rod-side annulus area m2 = pi/4 * (bore^2 - rod^2).

    The annulus is the piston area that remains available to the
    retract direction after the rod occupies the center.
    """
    if bore_m <= 0:
        raise ValueError("bore diameter must be positive")
    if rod_m <= 0:
        raise ValueError("rod diameter must be positive")
    if rod_m >= bore_m:
        raise ValueError("rod diameter must be smaller than the bore")
    return math.pi / 4.0 * (bore_m ** 2 - rod_m ** 2)


def retract_capability(annulus_area_m2, pressure_Pa):
    """Retract-direction force N from the annulus area and pressure.

    The pressure margin is removed here (the margin load is divided
    back out) so the capability is compared directly with the required
    load.
    """
    if annulus_area_m2 <= 0:
        raise ValueError("annulus area must be positive")
    if pressure_Pa <= 0:
        raise ValueError("pressure must be positive")
    return annulus_area_m2 * pressure_Pa * MECHANICAL_EFFICIENCY / PRESSURE_MARGIN


def rod_buckling_diameter(load_N, rod_length_m):
    """Minimum rod diameter m for Euler buckling over the extended length.

    Required second moment I = load * FOS * (K * length)^2 / (pi^2 * E)
    and D = (64 * I / pi)^0.25 for a solid circular rod. The rod is
    loaded in compression when it pushes, so it is checked as a column
    at full extension.
    """
    if load_N <= 0:
        raise ValueError("load must be positive")
    if rod_length_m <= 0:
        raise ValueError("rod length must be positive")
    inertia = (
        load_N
        * BUCKLING_FACTOR_OF_SAFETY
        * (END_FIXITY_K * rod_length_m) ** 2
        / (math.pi ** 2 * MODULUS_ROD)
    )
    return (64.0 * inertia / math.pi) ** 0.25


def select_preferred(value_m, preferred_mm):
    """Nearest preferred diameter mm at or above value_m.

    Compares the value in millimetres against the preferred list and
    returns the first preferred size that covers it, so the selection
    never under-sizes the requirement.
    """
    if value_m <= 0:
        raise ValueError("value must be positive")
    value_mm = value_m * 1000.0
    for preferred in preferred_mm:
        if preferred >= value_mm:
            return float(preferred)
    raise ValueError("required diameter exceeds the largest preferred size")


def _rod_stress(load_N, rod_diameter_m):
    """Compressive rod stress Pa = load / (pi/4 * rod_diameter^2)."""
    return load_N / (math.pi / 4.0 * rod_diameter_m ** 2)


def _critical_buckling_load(rod_diameter_m, rod_length_m):
    """Euler critical load N for the actual rod diameter at full extension."""
    inertia = math.pi / 64.0 * rod_diameter_m ** 4
    return (
        math.pi ** 2
        * MODULUS_ROD
        * inertia
        / (END_FIXITY_K * rod_length_m) ** 2
    )


def actuator_mass(bore_m, rod_m, stroke_m):
    """Actuator mass estimate kg from bore, rod and stroke.

    Rod volume pi/4 * rod^2 * stroke plus the barrel annulus volume
    pi/4 * (bore^2 - rod^2) * stroke at a 0.6 fill factor (barrel
    wall, seals, gland and fittings allowance), times the rod steel
    density.
    """
    if bore_m <= 0:
        raise ValueError("bore diameter must be positive")
    if rod_m <= 0:
        raise ValueError("rod diameter must be positive")
    if stroke_m <= 0:
        raise ValueError("stroke must be positive")
    if rod_m >= bore_m:
        raise ValueError("rod diameter must be smaller than the bore")
    rod_volume = math.pi / 4.0 * rod_m ** 2 * stroke_m
    barrel_volume = math.pi / 4.0 * (bore_m ** 2 - rod_m ** 2) * stroke_m
    return (rod_volume + 0.6 * barrel_volume) * ROD_DENSITY


def actuator_review(load_N, pressure_Pa, rod_length_m, stroke_m):
    """Full actuator sizing review dict for a required load.

    Returns {piston_area, bore_mm, annulus_area, rod_buckling_mm,
    bore_pref_mm, rod_pref_mm, retract_capability_N, rod_stress_Pa,
    buckling_margin, mass_kg, verdict}. Areas are m2, diameters in mm
    (preferred values are the nearest at-or-above selections), rod
    stress and buckling margin use the preferred rod diameter, and the
    mass uses the preferred bore and rod at the given stroke. Verdict
    is "pass" when the retract capability meets the load and the rod
    stress stays within the steel yield, else "fail".
    """
    if stroke_m <= 0:
        raise ValueError("stroke must be positive")
    area = piston_area(load_N, pressure_Pa)
    bore_req = bore_diameter(area)
    bore_pref_mm = select_preferred(bore_req, PREFERRED_BORES_MM)
    buckling_req = rod_buckling_diameter(load_N, rod_length_m)
    rod_pref_mm = select_preferred(buckling_req, PREFERRED_RODS_MM)
    bore_pref_m = bore_pref_mm / 1000.0
    rod_pref_m = rod_pref_mm / 1000.0
    annulus = annulus_area(bore_pref_m, rod_pref_m)
    retract = retract_capability(annulus, pressure_Pa)
    stress = _rod_stress(load_N, rod_pref_m)
    margin = _critical_buckling_load(rod_pref_m, rod_length_m) / load_N
    mass = actuator_mass(bore_pref_m, rod_pref_m, stroke_m)
    verdict = "pass" if (retract >= load_N and stress <= STEEL_YIELD) else "fail"
    return {
        "piston_area": area,
        "bore_mm": bore_req * 1000.0,
        "annulus_area": annulus,
        "rod_buckling_mm": buckling_req * 1000.0,
        "bore_pref_mm": bore_pref_mm,
        "rod_pref_mm": rod_pref_mm,
        "retract_capability_N": retract,
        "rod_stress_Pa": stress,
        "buckling_margin": margin,
        "mass_kg": mass,
        "verdict": verdict,
    }
