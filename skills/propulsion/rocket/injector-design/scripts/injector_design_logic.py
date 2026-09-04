"""Rocket engine injector element design logic (Aero Agent Skills propulsion).

Pure functions, stdlib only. Real engineering math for the injection
elements that meter propellant into the chamber: orifice discharge
flow from a discharge coefficient and pressure drop, injection
velocity from the Bernoulli head, the momentum flux ratio of impinging
unlike-doublet elements, per-propellant orifice counts for a chamber
mass flow at a given mixture ratio, and the per-element flow balance
for the element layout. Invalid inputs raise ValueError.

Units: diameter in m, pressure drop in Pa, density in kg/m^3, velocity
in m/s, mass flow in kg/s, mixture ratio dimensionless.

Conventions: a round orifice has area A = pi * d^2 / 4 and jet velocity
v = Cd * sqrt(2 * dP / rho), so the discharge flow
m_dot = rho * A * v reduces to the standard discharge law
m_dot = Cd * A * sqrt(2 * rho * dP). An unlike-doublet element carries
one fuel orifice and two oxidizer orifices whose jets impinge; the
momentum flux ratio is J = (rho_o * v_o^2) / (rho_f * v_f^2) per pair.
"""

import math

PI = math.pi  # circle constant


def orifice_area(diameter_m):
    """Cross-section area A = pi * d^2 / 4 of a round orifice in m^2."""
    if diameter_m <= 0:
        raise ValueError("diameter_m must be positive")
    return PI * diameter_m * diameter_m / 4.0


def injection_velocity(discharge_coefficient, pressure_drop_pa, density):
    """Injection velocity v = Cd * sqrt(2 * dP / rho) in m/s.

    The discharge coefficient is applied to the Bernoulli head; the
    result is the mean jet velocity at the orifice exit plane.
    """
    if discharge_coefficient <= 0:
        raise ValueError("discharge_coefficient must be positive")
    if pressure_drop_pa <= 0:
        raise ValueError("pressure_drop_pa must be positive")
    if density <= 0:
        raise ValueError("density must be positive")
    return discharge_coefficient * math.sqrt(2.0 * pressure_drop_pa / density)


def orifice_mass_flow(discharge_coefficient, pressure_drop_pa, density,
                      diameter_m):
    """Discharge of one orifice as dict with keys area_m2, velocity_m_s,
    mass_flow_kgs.

    mass_flow_kgs = density * area * velocity with the velocity already
    carrying the discharge coefficient, which is the standard discharge
    law Cd * A * sqrt(2 * rho * dP).
    """
    area_m2 = orifice_area(diameter_m)
    velocity_m_s = injection_velocity(discharge_coefficient, pressure_drop_pa,
                                      density)
    mass_flow_kgs = density * area_m2 * velocity_m_s
    return {"area_m2": area_m2, "velocity_m_s": velocity_m_s,
            "mass_flow_kgs": mass_flow_kgs}


def momentum_flux_ratio(oxidizer_density, oxidizer_velocity, fuel_density,
                        fuel_velocity):
    """Momentum flux ratio J = (rho_o * v_o^2) / (rho_f * v_f^2).

    For an impinging unlike doublet, near-unity momentum flux gives a
    well-mixed atomized sheet; large excursions leave one jet dominant
    and the spray one-sided.
    """
    if oxidizer_density <= 0 or fuel_density <= 0:
        raise ValueError("densities must be positive")
    if oxidizer_velocity <= 0 or fuel_velocity <= 0:
        raise ValueError("velocities must be positive")
    oxidizer_momentum = oxidizer_density * oxidizer_velocity * oxidizer_velocity
    fuel_momentum = fuel_density * fuel_velocity * fuel_velocity
    return oxidizer_momentum / fuel_momentum


def orifice_count(total_mass_flow_kgs, per_orifice_mass_flow_kgs):
    """Number of orifices needed: ceil(total / per_orifice).

    Orifice counts are integers, so a fractional requirement rounds up
    to the next whole orifice; an exactly integral requirement is not
    bumped.
    """
    if per_orifice_mass_flow_kgs <= 0:
        raise ValueError("per_orifice_mass_flow_kgs must be positive")
    if total_mass_flow_kgs < 0:
        raise ValueError("total_mass_flow_kgs must be non-negative")
    return int(math.ceil(total_mass_flow_kgs / per_orifice_mass_flow_kgs))


def element_mass_flow(fuel_orifices_per_element, oxidizer_orifices_per_element,
                      fuel_per_orifice_kgs, oxidizer_per_orifice_kgs):
    """Mass flow carried by one element layout as dict with keys fuel_kgs,
    oxidizer_kgs, total_kgs.

    The element layout fixes how many fuel and oxidizer orifices share
    one element; the element flow is the sum over those orifices.
    """
    if fuel_orifices_per_element < 1 or oxidizer_orifices_per_element < 1:
        raise ValueError("orifice counts per element must be at least 1")
    if fuel_per_orifice_kgs <= 0 or oxidizer_per_orifice_kgs <= 0:
        raise ValueError("per-orifice mass flows must be positive")
    fuel_kgs = fuel_orifices_per_element * fuel_per_orifice_kgs
    oxidizer_kgs = oxidizer_orifices_per_element * oxidizer_per_orifice_kgs
    return {"fuel_kgs": fuel_kgs, "oxidizer_kgs": oxidizer_kgs,
            "total_kgs": fuel_kgs + oxidizer_kgs}


def injector_layout_summary(chamber_mass_flow_kgs, mixture_ratio_of,
                            fuel_density, oxidizer_density,
                            fuel_pressure_drop_pa, oxidizer_pressure_drop_pa,
                            discharge_coefficient, fuel_orifice_diam,
                            oxidizer_orifice_diam, fuel_orifices_per_element,
                            oxidizer_orifices_per_element):
    """Full injector face summary for a chamber operating point.

    Splits the chamber mass flow at the mixture ratio, sizes one orifice
    of each propellant, computes the doublet momentum flux ratio, the
    per-propellant orifice counts, the element count and the per-element
    flow balance. Returns a dict with keys:

      fuel_mass_flow_kgs, oxidizer_mass_flow_kgs,
      fuel_area_m2, oxidizer_area_m2,
      fuel_injection_velocity_m_s, oxidizer_injection_velocity_m_s,
      fuel_per_orifice_mass_flow_kgs, oxidizer_per_orifice_mass_flow_kgs,
      momentum_flux_ratio, fuel_orifice_count, oxidizer_orifice_count,
      element_count, per_element_fuel_kgs, per_element_oxidizer_kgs,
      per_element_total_kgs

    The element count is the larger of the two propellant-derived
    requirements ceil(orifice_count / orifices_per_element), the binding
    constraint for covering the full chamber flow with whole elements.
    """
    if chamber_mass_flow_kgs <= 0:
        raise ValueError("chamber_mass_flow_kgs must be positive")
    if mixture_ratio_of <= 0:
        raise ValueError("mixture_ratio_of must be positive")
    if discharge_coefficient <= 0:
        raise ValueError("discharge_coefficient must be positive")
    if fuel_orifice_diam <= 0 or oxidizer_orifice_diam <= 0:
        raise ValueError("orifice diameters must be positive")
    if fuel_orifices_per_element < 1 or oxidizer_orifices_per_element < 1:
        raise ValueError("orifice counts per element must be at least 1")

    fuel_mass_flow_kgs = chamber_mass_flow_kgs / (1.0 + mixture_ratio_of)
    oxidizer_mass_flow_kgs = chamber_mass_flow_kgs - fuel_mass_flow_kgs

    fuel_orifice = orifice_mass_flow(discharge_coefficient,
                                     fuel_pressure_drop_pa, fuel_density,
                                     fuel_orifice_diam)
    oxidizer_orifice = orifice_mass_flow(discharge_coefficient,
                                         oxidizer_pressure_drop_pa,
                                         oxidizer_density,
                                         oxidizer_orifice_diam)

    fuel_orifice_count = orifice_count(fuel_mass_flow_kgs,
                                       fuel_orifice["mass_flow_kgs"])
    oxidizer_orifice_count = orifice_count(oxidizer_mass_flow_kgs,
                                           oxidizer_orifice["mass_flow_kgs"])

    fuel_elements = int(math.ceil(fuel_orifice_count / fuel_orifices_per_element))
    oxidizer_elements = int(math.ceil(oxidizer_orifice_count
                                      / oxidizer_orifices_per_element))
    element_count = max(fuel_elements, oxidizer_elements)

    per_element = element_mass_flow(fuel_orifices_per_element,
                                    oxidizer_orifices_per_element,
                                    fuel_orifice["mass_flow_kgs"],
                                    oxidizer_orifice["mass_flow_kgs"])

    momentum = momentum_flux_ratio(oxidizer_density,
                                   oxidizer_orifice["velocity_m_s"],
                                   fuel_density,
                                   fuel_orifice["velocity_m_s"])

    return {
        "fuel_mass_flow_kgs": fuel_mass_flow_kgs,
        "oxidizer_mass_flow_kgs": oxidizer_mass_flow_kgs,
        "fuel_area_m2": fuel_orifice["area_m2"],
        "oxidizer_area_m2": oxidizer_orifice["area_m2"],
        "fuel_injection_velocity_m_s": fuel_orifice["velocity_m_s"],
        "oxidizer_injection_velocity_m_s": oxidizer_orifice["velocity_m_s"],
        "fuel_per_orifice_mass_flow_kgs": fuel_orifice["mass_flow_kgs"],
        "oxidizer_per_orifice_mass_flow_kgs": oxidizer_orifice["mass_flow_kgs"],
        "momentum_flux_ratio": momentum,
        "fuel_orifice_count": fuel_orifice_count,
        "oxidizer_orifice_count": oxidizer_orifice_count,
        "element_count": element_count,
        "per_element_fuel_kgs": per_element["fuel_kgs"],
        "per_element_oxidizer_kgs": per_element["oxidizer_kgs"],
        "per_element_total_kgs": per_element["total_kgs"],
    }
