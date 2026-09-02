#!/usr/bin/env python3
"""Ideal ramjet cycle performance logic (paraphrase, common methodology).

Common-knowledge summary (standards-map.yaml, far-33: public domain
regulation context): a ramjet has no rotating machinery. Compression
comes from the ram effect of the flight speed, heat is added in the
combustor, and the flow expands through the nozzle. For the ideal
cycle (isentropic inlet, constant-pressure heat addition, fully
expanded nozzle, perfect gas with constant cp and gamma) the thrust
per unit captured air flow closes in one line:

  F / m_dot_a = a0 * M0 * (sqrt(tau_lambda) - 1)

where a0 is the ambient speed of sound, M0 the flight Mach number,
and tau_lambda = Tt4 / Tt0 the total temperature ratio across the
combustor. The exit jet speed for full expansion is v9 = v0 *
sqrt(tau_lambda), so the specific thrust is the jet minus flight
momentum per unit air flow. Fuel flow follows from the energy
balance: f = cp * (Tt4 - Tt0) / (eta_b * LHV), which is inverted
here as tau_lambda = 1 + eta_b * f * LHV / (cp * Tt0).

Units: static temperature in K, speeds in m/s, mass flow in kg/s,
thrust in N, specific thrust in N/(kg/s) (equivalently m/s), LHV in
J/kg, cp in J/(kg K), fuel air ratio and efficiencies dimensionless,
specific impulse in seconds.
"""

import math

GAMMA_AIR = 1.4
R_AIR = 287.0  # J/(kg K), dry air gas constant
G0 = 9.80665  # m/s^2, standard gravity


def speed_of_sound(t_static_k, gamma=GAMMA_AIR, r_gas=R_AIR):
    """Ambient speed of sound a0 = sqrt(gamma * R * T) in m/s."""
    if t_static_k <= 0:
        raise ValueError("static temperature must be > 0 K, got %r" % (t_static_k,))
    if gamma <= 1:
        raise ValueError("ratio of specific heats must be > 1, got %r" % (gamma,))
    if r_gas <= 0:
        raise ValueError("gas constant must be > 0, got %r" % (r_gas,))
    return math.sqrt(gamma * r_gas * t_static_k)


def stagnation_temperature(t_static_k, mach, gamma=GAMMA_AIR):
    """Flight total temperature Tt0 = T0 * (1 + (gamma-1)/2 * M0^2)."""
    if t_static_k <= 0:
        raise ValueError("static temperature must be > 0 K, got %r" % (t_static_k,))
    if mach < 0:
        raise ValueError("Mach number must be >= 0, got %r" % (mach,))
    if gamma <= 1:
        raise ValueError("ratio of specific heats must be > 1, got %r" % (gamma,))
    return t_static_k * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)


def total_temperature_ratio(
    fuel_air_ratio,
    lhv_j_per_kg,
    cp_j_per_kg_k,
    t_static_k,
    mach,
    combustor_efficiency=1.0,
    gamma=GAMMA_AIR,
):
    """Combustor total temperature ratio tau_lambda = Tt4 / Tt0.

    From the heat balance tau_lambda = 1 + eta_b * f * LHV /
    (cp * Tt0), with Tt0 the flight stagnation temperature.
    """
    if fuel_air_ratio < 0:
        raise ValueError(
            "fuel air ratio must be >= 0, got %r" % (fuel_air_ratio,)
        )
    if lhv_j_per_kg <= 0:
        raise ValueError(
            "lower heating value must be > 0 J/kg, got %r" % (lhv_j_per_kg,)
        )
    if cp_j_per_kg_k <= 0:
        raise ValueError(
            "specific heat must be > 0 J/(kg K), got %r" % (cp_j_per_kg_k,)
        )
    if not (0.0 < combustor_efficiency <= 1.0):
        raise ValueError(
            "combustor efficiency must be in (0, 1], got %r"
            % (combustor_efficiency,)
        )
    tt0 = stagnation_temperature(t_static_k, mach, gamma)
    return 1.0 + (
        combustor_efficiency * fuel_air_ratio * lhv_j_per_kg
        / (cp_j_per_kg_k * tt0)
    )


def specific_thrust(speed_of_sound_mps, mach, tau_lambda):
    """Ideal ramjet thrust per unit air flow F / m_dot_a in N/(kg/s).

    F / m_dot_a = a0 * M0 * (sqrt(tau_lambda) - 1). Requires
    tau_lambda > 1 (heat added) so the jet outruns the freestream.
    """
    if speed_of_sound_mps <= 0:
        raise ValueError(
            "speed of sound must be > 0 m/s, got %r" % (speed_of_sound_mps,)
        )
    if mach <= 0:
        raise ValueError("Mach number must be > 0, got %r" % (mach,))
    if tau_lambda <= 1.0:
        raise ValueError(
            "total temperature ratio must be > 1, got %r" % (tau_lambda,)
        )
    return speed_of_sound_mps * mach * (math.sqrt(tau_lambda) - 1.0)


def thrust(mass_flow_kgps, speed_of_sound_mps, mach, tau_lambda):
    """Total ramjet thrust F = m_dot_a * (F / m_dot_a) in N."""
    if mass_flow_kgps <= 0:
        raise ValueError(
            "captured mass flow must be > 0 kg/s, got %r" % (mass_flow_kgps,)
        )
    return mass_flow_kgps * specific_thrust(
        speed_of_sound_mps, mach, tau_lambda
    )


def fuel_mass_flow(mass_flow_kgps, fuel_air_ratio):
    """Fuel flow m_dot_f = f * m_dot_a in kg/s."""
    if mass_flow_kgps <= 0:
        raise ValueError(
            "captured mass flow must be > 0 kg/s, got %r" % (mass_flow_kgps,)
        )
    if fuel_air_ratio < 0:
        raise ValueError(
            "fuel air ratio must be >= 0, got %r" % (fuel_air_ratio,)
        )
    return mass_flow_kgps * fuel_air_ratio


def specific_impulse(specific_thrust_n_per_kgps, fuel_air_ratio, g0=G0):
    """Specific impulse Isp = (F / m_dot_a) / (f * g0) in seconds."""
    if specific_thrust_n_per_kgps < 0:
        raise ValueError(
            "specific thrust must be >= 0, got %r" % (specific_thrust_n_per_kgps,)
        )
    if fuel_air_ratio <= 0:
        raise ValueError(
            "fuel air ratio must be > 0, got %r" % (fuel_air_ratio,)
        )
    if g0 <= 0:
        raise ValueError("gravity must be > 0 m/s^2, got %r" % (g0,))
    return specific_thrust_n_per_kgps / (fuel_air_ratio * g0)


def thermal_efficiency(
    specific_thrust_n_per_kgps,
    flight_speed_mps,
    fuel_air_ratio,
    lhv_j_per_kg,
):
    """Ideal ramjet thermal efficiency eta_th = F * v0 / (m_dot_f * LHV).

    Thrust power per unit air flow divided by heat input per unit air
    flow: (F / m_dot_a) * v0 / (f * LHV). Dimensionless.
    """
    if specific_thrust_n_per_kgps < 0:
        raise ValueError(
            "specific thrust must be >= 0, got %r" % (specific_thrust_n_per_kgps,)
        )
    if flight_speed_mps <= 0:
        raise ValueError(
            "flight speed must be > 0 m/s, got %r" % (flight_speed_mps,)
        )
    if fuel_air_ratio <= 0:
        raise ValueError(
            "fuel air ratio must be > 0, got %r" % (fuel_air_ratio,)
        )
    if lhv_j_per_kg <= 0:
        raise ValueError(
            "lower heating value must be > 0 J/kg, got %r" % (lhv_j_per_kg,)
        )
    return (
        specific_thrust_n_per_kgps * flight_speed_mps
        / (fuel_air_ratio * lhv_j_per_kg)
    )
