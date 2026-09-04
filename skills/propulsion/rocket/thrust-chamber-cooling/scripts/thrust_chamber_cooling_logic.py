"""Thrust chamber cooling logic for liquid rocket engines.

Pure stdlib, SI units throughout. Implements the thermal design of a
liquid rocket thrust chamber and nozzle wall: throat-area and mass-flow
anchor, the hot-gas side Bartz convective coefficient at the throat,
the coolant-side coefficient from the channel flow (Dittus-Boelter),
the series wall resistance network giving the heat flux and the hot and
cold wall temperatures, the coolant mass flux required to hold a copper
wall temperature limit, and the film-cooling handoff verdict when plain
regenerative flow cannot hold the limit.

The throat is the reference station (At/A = 1 in the Bartz
correlation). Recovery temperature uses r = Pr^(1/3) with the M = 1
static temperature relation: T_t = T_c / (1 + (gamma - 1) / 2) and
T_aw = T_t (1 + r (gamma - 1) / 2).
"""

import math

G0 = 9.80665  # standard gravity, m/s^2

# Dittus-Boelter heating correlation (fluid heated, Pr^0.4) constant.
_DITTUS_CONSTANT = 0.023
# Bartz SI correlation constant.
_BARTZ_CONSTANT = 0.026


def throat_area(diameter_m):
    """Throat cross section area A_t = pi d^2 / 4 from the throat diameter.

    Returns the area in m^2. Raises ValueError for a non-positive diameter.
    """
    if diameter_m <= 0:
        raise ValueError("throat diameter must be positive")
    return math.pi * diameter_m ** 2 / 4.0


def chamber_mass_flow(chamber_pressure_pa, throat_area_m2, cstar_m_s):
    """Propellant mass flow from the chamber pressure, throat area and c-star.

    mdot = Pc * At / c*. Raises ValueError on non-positive inputs.
    """
    if chamber_pressure_pa <= 0:
        raise ValueError("chamber pressure must be positive")
    if throat_area_m2 <= 0:
        raise ValueError("throat area must be positive")
    if cstar_m_s <= 0:
        raise ValueError("c-star must be positive")
    return chamber_pressure_pa * throat_area_m2 / cstar_m_s


def adiabatic_wall_temperature(chamber_temp_k, gamma, prandtl=0.72):
    """Recovery temperature at the throat for M = 1 hot gas flow.

    T_t = T_c / (1 + (gamma - 1) / 2) and
    T_aw = T_t (1 + Pr^(1/3) (gamma - 1) / 2).

    Returns {throat_static_temp_k, recovery_temp_k}. Raises ValueError
    for non-positive chamber temperature or Prandtl, or gamma <= 1.
    """
    if chamber_temp_k <= 0:
        raise ValueError("chamber temperature must be positive")
    if gamma <= 1:
        raise ValueError("specific heat ratio must be above 1")
    if prandtl <= 0:
        raise ValueError("Prandtl number must be positive")
    half_gamma_minus_one = (gamma - 1.0) / 2.0
    throat_static_temp_k = chamber_temp_k / (1.0 + half_gamma_minus_one)
    recovery_factor = prandtl ** (1.0 / 3.0)
    recovery_temp_k = throat_static_temp_k * (
        1.0 + recovery_factor * half_gamma_minus_one
    )
    return {
        "throat_static_temp_k": throat_static_temp_k,
        "recovery_temp_k": recovery_temp_k,
    }


def bartz_hot_gas_coefficient(
    chamber_pressure_pa,
    cstar_m_s,
    throat_diameter_m,
    mu_gas,
    cp_gas,
    prandtl_gas,
    sigma=1.0,
):
    """Hot gas convective coefficient at the throat, Bartz correlation (SI).

    h_g = 0.026 (mu^0.2 cp / Pr^0.6) (Pc / c*)^0.8 / Dt^0.2 * sigma
    with the throat station factor At/A = 1.

    Returns h_g in W/(m^2 K). Raises ValueError on non-positive inputs
    or sigma <= 0.
    """
    if chamber_pressure_pa <= 0:
        raise ValueError("chamber pressure must be positive")
    if cstar_m_s <= 0:
        raise ValueError("c-star must be positive")
    if throat_diameter_m <= 0:
        raise ValueError("throat diameter must be positive")
    if mu_gas <= 0:
        raise ValueError("gas viscosity must be positive")
    if cp_gas <= 0:
        raise ValueError("gas specific heat must be positive")
    if prandtl_gas <= 0:
        raise ValueError("gas Prandtl number must be positive")
    if sigma <= 0:
        raise ValueError("Bartz correction sigma must be positive")
    property_term = mu_gas ** 0.2 * cp_gas / prandtl_gas ** 0.6
    pressure_term = (chamber_pressure_pa / cstar_m_s) ** 0.8
    diameter_term = throat_diameter_m ** 0.2
    return (
        _BARTZ_CONSTANT * property_term * pressure_term / diameter_term * sigma
    )


def coolant_side_coefficient(mass_flux, hydraulic_diameter_m, mu_c, cp_c, k_c):
    """Coolant side coefficient from the channel flow, Dittus-Boelter.

    Re = G Dh / mu; Pr = cp mu / k; Nu = 0.023 Re^0.8 Pr^0.4;
    h = Nu k / Dh.

    Returns {h_c, reynolds, nusselt, prandtl}. Raises ValueError on
    non-positive inputs.
    """
    if mass_flux <= 0:
        raise ValueError("coolant mass flux must be positive")
    if hydraulic_diameter_m <= 0:
        raise ValueError("hydraulic diameter must be positive")
    if mu_c <= 0:
        raise ValueError("coolant viscosity must be positive")
    if cp_c <= 0:
        raise ValueError("coolant specific heat must be positive")
    if k_c <= 0:
        raise ValueError("coolant conductivity must be positive")
    reynolds = mass_flux * hydraulic_diameter_m / mu_c
    prandtl = cp_c * mu_c / k_c
    nusselt = (
        _DITTUS_CONSTANT * reynolds ** 0.8 * prandtl ** 0.4
    )
    h_c = nusselt * k_c / hydraulic_diameter_m
    return {
        "h_c": h_c,
        "reynolds": reynolds,
        "nusselt": nusselt,
        "prandtl": prandtl,
    }


def wall_heat_flux(
    hot_coeff,
    cold_coeff,
    wall_thickness_m,
    wall_conductivity,
    recovery_temp_k,
    coolant_temp_k,
):
    """Series wall resistance network heat flux and wall temperatures.

    R = 1/h_g + t_w/k_w + 1/h_c; q = (T_aw - T_cool)/R;
    T_wg = T_aw - q/h_g; T_wc = T_cool + q/h_c; dT = q t_w/k_w.

    Returns {heat_flux_wm2, hot_wall_temp_k, cold_wall_temp_k,
    wall_delta_temp_k}. Raises ValueError on non-positive inputs.
    """
    if hot_coeff <= 0:
        raise ValueError("hot gas coefficient must be positive")
    if cold_coeff <= 0:
        raise ValueError("coolant coefficient must be positive")
    if wall_thickness_m <= 0:
        raise ValueError("wall thickness must be positive")
    if wall_conductivity <= 0:
        raise ValueError("wall conductivity must be positive")
    if recovery_temp_k <= 0:
        raise ValueError("recovery temperature must be positive")
    if coolant_temp_k <= 0:
        raise ValueError("coolant temperature must be positive")
    resistance = (
        1.0 / hot_coeff
        + wall_thickness_m / wall_conductivity
        + 1.0 / cold_coeff
    )
    heat_flux_wm2 = (recovery_temp_k - coolant_temp_k) / resistance
    hot_wall_temp_k = recovery_temp_k - heat_flux_wm2 / hot_coeff
    cold_wall_temp_k = coolant_temp_k + heat_flux_wm2 / cold_coeff
    wall_delta_temp_k = heat_flux_wm2 * wall_thickness_m / wall_conductivity
    return {
        "heat_flux_wm2": heat_flux_wm2,
        "hot_wall_temp_k": hot_wall_temp_k,
        "cold_wall_temp_k": cold_wall_temp_k,
        "wall_delta_temp_k": wall_delta_temp_k,
    }


def coolant_mass_flux_for_wall_limit(
    hot_coeff,
    wall_thickness_m,
    wall_conductivity,
    recovery_temp_k,
    coolant_temp_k,
    wall_limit_k,
    coolant_props,
):
    """Coolant mass flux that holds the hot wall at the temperature limit.

    q_lim = h_g (T_aw - T_lim); R_lim = (T_aw - T_cool) / q_lim; the
    required coolant coefficient follows from the series network and the
    Dittus-Boelter correlation is inverted for the mass flux:
    Re = (h_req Dh / (0.023 Pr^0.4 k))^(1/0.8); G = Re mu / Dh.

    coolant_props must be the dict {hydraulic_diameter_m, mu_c, cp_c,
    k_c}. Returns {required_h_c, required_reynolds, required_mass_flux}.
    Raises ValueError on non-physical inputs, including a wall limit at
    or above the recovery temperature and a limit below what infinite
    coolant convection could hold (required coefficient non-positive).
    """
    if hot_coeff <= 0:
        raise ValueError("hot gas coefficient must be positive")
    if wall_thickness_m <= 0:
        raise ValueError("wall thickness must be positive")
    if wall_conductivity <= 0:
        raise ValueError("wall conductivity must be positive")
    if recovery_temp_k <= 0:
        raise ValueError("recovery temperature must be positive")
    if coolant_temp_k <= 0:
        raise ValueError("coolant temperature must be positive")
    if wall_limit_k <= 0:
        raise ValueError("wall temperature limit must be positive")
    if wall_limit_k >= recovery_temp_k:
        raise ValueError("wall limit must be below the recovery temperature")
    hydraulic_diameter_m = coolant_props["hydraulic_diameter_m"]
    mu_c = coolant_props["mu_c"]
    cp_c = coolant_props["cp_c"]
    k_c = coolant_props["k_c"]
    if hydraulic_diameter_m <= 0:
        raise ValueError("hydraulic diameter must be positive")
    if mu_c <= 0:
        raise ValueError("coolant viscosity must be positive")
    if cp_c <= 0:
        raise ValueError("coolant specific heat must be positive")
    if k_c <= 0:
        raise ValueError("coolant conductivity must be positive")
    q_lim = hot_coeff * (recovery_temp_k - wall_limit_k)
    resistance_lim = (recovery_temp_k - coolant_temp_k) / q_lim
    conduction_resistance = (
        1.0 / hot_coeff + wall_thickness_m / wall_conductivity
    )
    required_h_c = 1.0 / (resistance_lim - conduction_resistance)
    if required_h_c <= 0:
        raise ValueError(
            "wall limit is below what infinite coolant convection could hold"
        )
    prandtl = cp_c * mu_c / k_c
    required_reynolds = (
        required_h_c
        * hydraulic_diameter_m
        / (_DITTUS_CONSTANT * prandtl ** 0.4 * k_c)
    ) ** (1.0 / 0.8)
    required_mass_flux = required_reynolds * mu_c / hydraulic_diameter_m
    return {
        "required_h_c": required_h_c,
        "required_reynolds": required_reynolds,
        "required_mass_flux": required_mass_flux,
    }


def film_cooling_handoff(hot_wall_temp_k, wall_limit_k):
    """Verdict on handing off to film cooling.

    True when the plain-regenerative hot wall temperature exceeds the
    wall limit, so plain regenerative flow cannot hold the limit and
    film cooling is required. Raises ValueError on non-positive inputs.
    """
    if hot_wall_temp_k <= 0:
        raise ValueError("hot wall temperature must be positive")
    if wall_limit_k <= 0:
        raise ValueError("wall temperature limit must be positive")
    return hot_wall_temp_k > wall_limit_k


def chamber_cooling_summary(
    chamber_pressure_pa,
    cstar_m_s,
    chamber_temp_k,
    gamma,
    throat_diameter_m,
    prandtl_gas,
    mu_gas,
    cp_gas,
    coolant_mass_flux,
    hydraulic_diameter_m,
    mu_c,
    cp_c,
    k_c,
    wall_thickness_m,
    wall_conductivity,
    coolant_temp_k,
    wall_limit_k,
    sigma=1.0,
):
    """One-call cooling design summary for the worked LOX/RP-1 chamber.

    Chains throat_area, chamber_mass_flow, adiabatic_wall_temperature,
    bartz_hot_gas_coefficient, coolant_side_coefficient,
    wall_heat_flux, film_cooling_handoff and
    coolant_mass_flux_for_wall_limit. Returns a flat dict with keys:
    throat_area_m2, chamber_mass_flow_kg_s, throat_static_temp_k,
    recovery_temp_k, h_g, h_c, reynolds, nusselt, prandtl,
    heat_flux_wm2, hot_wall_temp_k, cold_wall_temp_k,
    wall_delta_temp_k, film_cooling_handoff, required_h_c,
    required_reynolds, required_mass_flux.
    """
    at = throat_area(throat_diameter_m)
    mdot = chamber_mass_flow(chamber_pressure_pa, at, cstar_m_s)
    aw = adiabatic_wall_temperature(chamber_temp_k, gamma, prandtl_gas)
    h_g = bartz_hot_gas_coefficient(
        chamber_pressure_pa,
        cstar_m_s,
        throat_diameter_m,
        mu_gas,
        cp_gas,
        prandtl_gas,
        sigma,
    )
    coolant = coolant_side_coefficient(
        coolant_mass_flux, hydraulic_diameter_m, mu_c, cp_c, k_c
    )
    wall = wall_heat_flux(
        h_g,
        coolant["h_c"],
        wall_thickness_m,
        wall_conductivity,
        aw["recovery_temp_k"],
        coolant_temp_k,
    )
    handoff = film_cooling_handoff(wall["hot_wall_temp_k"], wall_limit_k)
    required = coolant_mass_flux_for_wall_limit(
        h_g,
        wall_thickness_m,
        wall_conductivity,
        aw["recovery_temp_k"],
        coolant_temp_k,
        wall_limit_k,
        {
            "hydraulic_diameter_m": hydraulic_diameter_m,
            "mu_c": mu_c,
            "cp_c": cp_c,
            "k_c": k_c,
        },
    )
    return {
        "throat_area_m2": at,
        "chamber_mass_flow_kg_s": mdot,
        "throat_static_temp_k": aw["throat_static_temp_k"],
        "recovery_temp_k": aw["recovery_temp_k"],
        "h_g": h_g,
        "h_c": coolant["h_c"],
        "reynolds": coolant["reynolds"],
        "nusselt": coolant["nusselt"],
        "prandtl": coolant["prandtl"],
        "heat_flux_wm2": wall["heat_flux_wm2"],
        "hot_wall_temp_k": wall["hot_wall_temp_k"],
        "cold_wall_temp_k": wall["cold_wall_temp_k"],
        "wall_delta_temp_k": wall["wall_delta_temp_k"],
        "film_cooling_handoff": handoff,
        "required_h_c": required["required_h_c"],
        "required_reynolds": required["required_reynolds"],
        "required_mass_flux": required["required_mass_flux"],
    }
