#!/usr/bin/env python3
"""Window aperture sizing logic for a pressurized cabin (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25: gated false): a
pressurized-cabin passenger window is sized as a flat circular pane
clamped at its edge under a uniform pressure differential. The design
differential follows from the ISA pressures at the cabin and flight
altitudes with the certification pressure factor applied (the ultimate
pressure check applies 1.33 times the normal operating differential
pressure, a paraphrase of the FAR 25.365 cabin pressure rule). The
clamped-edge plate bending stress comes from the Roark flat-circular-
plate closed form sigma_max = (3/4) * p * (r/t)^2, independent of the
Poisson ratio, with the maximum at the clamped edge. The required pane
thickness inverts that relation, the margin compares the computed
stress with a designer-supplied allowable, and the pane weight rolls
up the pane volume over the window count.

Units are SI throughout: pressures in Pa, lengths in m, stress in Pa,
density in kg/m^3. Invalid inputs raise ValueError throughout.
"""

import math

# ISA atmosphere constants (standard pressure formula, troposphere plus
# isothermal stratosphere).
P0_PA = 101325.0
T0_K = 288.15
LAPSE_K_PER_M = 0.0065
TROPOPAUSE_M = 11000.0
TROPOPAUSE_TEMP_K = 216.65
G0_M_S2 = 9.80665
R_GAS = 287.05
# g0 / (R * L) evaluated with the module constants; evaluates to
# 5.25593236 (5.25588 is the rounded textbook form). Using the exact
# evaluation reproduces the spec worked example to the last digit.
TROPOSPHERIC_EXPONENT = G0_M_S2 / (R_GAS * LAPSE_K_PER_M)
ALTITUDE_LIMIT_M = 20000.0

# Clamped circular plate under uniform pressure (Roark flat-circular-
# plate case, clamped edge): sigma_max = (3/4) * p * (r/t)^2.
CLAMPED_PLATE_STRESS_COEF = 0.75

# Certification pressure factor: the ultimate check applies 1.33 times
# the normal operating differential pressure (FAR 25.365 paraphrase).
CERT_PRESSURE_FACTOR = 1.33


def isa_pressure_pa(altitude_m):
    """ISA atmospheric pressure (Pa) at a geopotential altitude (m).

    Troposphere (0 to 11000 m): P(h) = P0 * (1 - L*h/T0)^e with e the
    tropospheric exponent. Isothermal stratosphere (11000 to 20000 m):
    P(h) = P_tropo * exp(-g0*(h - 11000)/(R*T_tropo)) with P_tropo the
    pressure at the tropopause and T_tropo = 216.65 K.

    Raises ValueError if altitude_m is outside 0 to 20000 m.
    """
    if altitude_m < 0.0:
        raise ValueError("altitude_m must be non-negative, got %r" % (altitude_m,))
    if altitude_m > ALTITUDE_LIMIT_M:
        raise ValueError("altitude_m above 20000 m is out of range, got %r" % (altitude_m,))
    if altitude_m <= TROPOPAUSE_M:
        ratio = 1.0 - LAPSE_K_PER_M * altitude_m / T0_K
        return P0_PA * ratio ** TROPOSPHERIC_EXPONENT
    p_tropo = P0_PA * (1.0 - LAPSE_K_PER_M * TROPOPAUSE_M / T0_K) ** TROPOSPHERIC_EXPONENT
    exponent = -G0_M_S2 * (altitude_m - TROPOPAUSE_M) / (R_GAS * TROPOPAUSE_TEMP_K)
    return p_tropo * math.exp(exponent)


def design_pressure_differential(
    cabin_altitude_m, flight_altitude_m, certification_factor=CERT_PRESSURE_FACTOR
):
    """Design cabin pressure differential (dict of Pa values).

    Returns {"cabin_pressure_pa", "ambient_pressure_pa",
    "limit_differential_pa", "design_differential_pa"}: the ISA cabin
    and ambient pressures at the two altitudes, their difference as the
    limit differential, and the limit times the certification pressure
    factor as the design differential.

    Raises ValueError if the flight altitude does not exceed the cabin
    altitude or the certification factor is not positive.
    """
    if flight_altitude_m <= cabin_altitude_m:
        raise ValueError(
            "flight_altitude_m must exceed cabin_altitude_m, got %r and %r"
            % (flight_altitude_m, cabin_altitude_m)
        )
    if certification_factor <= 0.0:
        raise ValueError(
            "certification_factor must be positive, got %r" % (certification_factor,)
        )
    cabin_pressure_pa = isa_pressure_pa(cabin_altitude_m)
    ambient_pressure_pa = isa_pressure_pa(flight_altitude_m)
    limit_differential_pa = cabin_pressure_pa - ambient_pressure_pa
    return {
        "cabin_pressure_pa": cabin_pressure_pa,
        "ambient_pressure_pa": ambient_pressure_pa,
        "limit_differential_pa": limit_differential_pa,
        "design_differential_pa": limit_differential_pa * certification_factor,
    }


def plate_max_stress_clamped_circular(pressure_pa, radius_m, thickness_m):
    """Maximum bending stress (Pa) of a clamped circular plate.

    sigma_max = (3/4) * p * (r/t)^2, the Roark flat-circular-plate
    clamped-edge result under uniform pressure, independent of the
    Poisson ratio. The maximum sits at the clamped edge.

    Raises ValueError if any argument is not positive.
    """
    if pressure_pa <= 0.0:
        raise ValueError("pressure_pa must be positive, got %r" % (pressure_pa,))
    if radius_m <= 0.0:
        raise ValueError("radius_m must be positive, got %r" % (radius_m,))
    if thickness_m <= 0.0:
        raise ValueError("thickness_m must be positive, got %r" % (thickness_m,))
    ratio = radius_m / thickness_m
    return CLAMPED_PLATE_STRESS_COEF * pressure_pa * ratio * ratio


def pane_thickness(pressure_pa, radius_m, allowable_stress_pa):
    """Required pane thickness (m) for a given allowable stress (Pa).

    t = r * sqrt((3/4) * p / sigma_allow), the exact inversion of the
    clamped-edge plate stress relation: a pane of this thickness runs
    the clamped-edge stress exactly at the allowable.

    Raises ValueError if any argument is not positive.
    """
    if pressure_pa <= 0.0:
        raise ValueError("pressure_pa must be positive, got %r" % (pressure_pa,))
    if radius_m <= 0.0:
        raise ValueError("radius_m must be positive, got %r" % (radius_m,))
    if allowable_stress_pa <= 0.0:
        raise ValueError(
            "allowable_stress_pa must be positive, got %r" % (allowable_stress_pa,)
        )
    return radius_m * math.sqrt(
        CLAMPED_PLATE_STRESS_COEF * pressure_pa / allowable_stress_pa
    )


def pane_margin(pressure_pa, radius_m, thickness_m, allowable_stress_pa):
    """Margin of the pane against the allowable stress (float).

    margin = allowable / computed_stress - 1 with the computed stress
    from plate_max_stress_clamped_circular. A negative margin means the
    pane fails at the design differential; zero means it is exactly at
    the allowable.

    Raises ValueError if any argument is not positive.
    """
    if allowable_stress_pa <= 0.0:
        raise ValueError(
            "allowable_stress_pa must be positive, got %r" % (allowable_stress_pa,)
        )
    if thickness_m <= 0.0:
        raise ValueError("thickness_m must be positive, got %r" % (thickness_m,))
    stress = plate_max_stress_clamped_circular(pressure_pa, radius_m, thickness_m)
    return allowable_stress_pa / stress - 1.0


def window_weight(radius_m, thickness_m, material_density_kg_m3, n_windows):
    """Pane weight rollup (dict of kg) over a window count.

    Returns {"per_window_kg", "total_kg"}: per window n * rho * pi *
    r^2 * t and the total over the window count. The weight follows
    from the pane volume only, so no pressure argument is taken.

    Raises ValueError if any argument is not positive or n_windows is
    below 1.
    """
    if radius_m <= 0.0:
        raise ValueError("radius_m must be positive, got %r" % (radius_m,))
    if thickness_m <= 0.0:
        raise ValueError("thickness_m must be positive, got %r" % (thickness_m,))
    if material_density_kg_m3 <= 0.0:
        raise ValueError(
            "material_density_kg_m3 must be positive, got %r"
            % (material_density_kg_m3,)
        )
    if n_windows < 1:
        raise ValueError("n_windows must be at least 1, got %r" % (n_windows,))
    per_window_kg = material_density_kg_m3 * math.pi * radius_m * radius_m * thickness_m
    return {"per_window_kg": per_window_kg, "total_kg": per_window_kg * n_windows}
