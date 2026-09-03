"""Wheel brake energy sizing for aircraft (vehicle-design/sizing/brake-energy-sizing).

Pure stdlib. Sizes the wheel brake heat sink from the kinetic energy the
brakes must absorb: rejected-takeoff (RTO) energy at the decision speed,
landing-stop energy at the touchdown speed, per-brake division over the
braked wheels, required heat-sink mass from the allowable temperature
rise and the heat-sink specific heat, actual temperature rise of the
selected heat sink, and the braking distance at the design deceleration.

All functions raise ValueError on non-physical inputs (non-positive
masses, speeds, wheel counts, specific heats, temperature rises, or
decelerations, and reverse-thrust credits outside 0..1). SI units
throughout; the deceleration input is a fraction of standard gravity.

The carbon specific heat, the reverse-thrust credit and the design
deceleration are documented typical values used as defaults; they are
program inputs in practice.
"""

G0 = 9.80665
"""Standard gravity, m/s^2."""

CP_CARBON = 1200.0
"""Typical specific heat of a carbon brake heat sink, J/(kg K)."""

REVERSE_THRUST_CREDIT_DEFAULT = 0.0
"""Default fraction of RTO energy removed by reverse thrust (conservative 0)."""


def rto_energy_J(mtow_kg, v1_m_s):
    """Rejected-takeoff kinetic energy E = 0.5 * mtow * v1^2 at V1, in J."""
    if mtow_kg <= 0:
        raise ValueError("mtow_kg must be positive")
    if v1_m_s <= 0:
        raise ValueError("v1_m_s must be positive")
    return 0.5 * mtow_kg * v1_m_s * v1_m_s


def landing_energy_J(mlw_kg, touchdown_speed_m_s):
    """Landing-stop kinetic energy E = 0.5 * mlw * v_td^2, in J."""
    if mlw_kg <= 0:
        raise ValueError("mlw_kg must be positive")
    if touchdown_speed_m_s <= 0:
        raise ValueError("touchdown_speed_m_s must be positive")
    return 0.5 * mlw_kg * touchdown_speed_m_s * touchdown_speed_m_s


def per_brake_energy_J(total_energy_J, n_braked_wheels, reverse_credit=REVERSE_THRUST_CREDIT_DEFAULT):
    """Energy each braked wheel must absorb after the reverse-thrust credit.

    per brake = total * (1 - reverse_credit) / n_braked_wheels.
    """
    if total_energy_J <= 0:
        raise ValueError("total_energy_J must be positive")
    if not isinstance(n_braked_wheels, int) or n_braked_wheels <= 0:
        raise ValueError("n_braked_wheels must be a positive integer")
    if reverse_credit < 0.0 or reverse_credit > 1.0:
        raise ValueError("reverse_credit must be within 0..1")
    return total_energy_J * (1.0 - reverse_credit) / n_braked_wheels


def required_heat_sink_mass_kg(energy_per_brake_J, cp, delta_t_K):
    """Heat-sink mass per brake for a given temperature rise: E / (cp * delta_t)."""
    if energy_per_brake_J <= 0:
        raise ValueError("energy_per_brake_J must be positive")
    if cp <= 0:
        raise ValueError("cp must be positive")
    if delta_t_K <= 0:
        raise ValueError("delta_t_K must be positive")
    return energy_per_brake_J / (cp * delta_t_K)


def temperature_rise_K(energy_per_brake_J, mass_kg, cp):
    """Adiabatic heat-sink temperature rise: E / (mass * cp), in K."""
    if energy_per_brake_J <= 0:
        raise ValueError("energy_per_brake_J must be positive")
    if mass_kg <= 0:
        raise ValueError("mass_kg must be positive")
    if cp <= 0:
        raise ValueError("cp must be positive")
    return energy_per_brake_J / (mass_kg * cp)


def braking_distance_m(v_m_s, decel_g):
    """Braking distance at speed v with deceleration decel_g * g0: v^2/(2*a)."""
    if v_m_s <= 0:
        raise ValueError("v_m_s must be positive")
    if decel_g <= 0:
        raise ValueError("decel_g must be positive")
    return v_m_s * v_m_s / (2.0 * decel_g * G0)


def analyze(inputs):
    """Run the wheel-brake sizing on an inputs dict, return the result dict.

    Required keys: mtow_kg, v1_m_s, mlw_kg, touchdown_speed_m_s,
    n_braked_wheels, delta_t_allowable_K, heat_sink_mass_available_kg,
    decel_g. Optional keys with defaults: heat_sink_cp (CP_CARBON),
    reverse_credit (REVERSE_THRUST_CREDIT_DEFAULT).

    Returns E_rto_J, E_land_J, per-brake energy for both cases, the
    governing case ("rto" or "landing", the larger per-brake energy),
    required_heat_sink_mass_kg, actual_temperature_rise_K with the
    available mass, delta_t_margin_K, braking_distance_m, and the
    verdict "brake-energy-pass" when the margin is non-negative and the
    required mass fits in the available mass, else "brake-energy-fail".
    """
    required_keys = ("mtow_kg", "v1_m_s", "mlw_kg", "touchdown_speed_m_s",
                     "n_braked_wheels", "delta_t_allowable_K",
                     "heat_sink_mass_available_kg", "decel_g")
    missing = [key for key in required_keys if key not in inputs]
    if missing:
        raise ValueError("analyze missing input(s): " + ", ".join(missing))

    n_braked_wheels = inputs["n_braked_wheels"]
    if not isinstance(n_braked_wheels, int) or n_braked_wheels <= 0:
        raise ValueError("n_braked_wheels must be a positive integer")
    heat_sink_mass_available_kg = inputs["heat_sink_mass_available_kg"]
    if heat_sink_mass_available_kg <= 0:
        raise ValueError("heat_sink_mass_available_kg must be positive")

    cp = inputs.get("heat_sink_cp", CP_CARBON)
    reverse_credit = inputs.get("reverse_credit", REVERSE_THRUST_CREDIT_DEFAULT)
    delta_t_allowable_K = inputs["delta_t_allowable_K"]

    e_rto = rto_energy_J(inputs["mtow_kg"], inputs["v1_m_s"])
    e_land = landing_energy_J(inputs["mlw_kg"], inputs["touchdown_speed_m_s"])
    per_rto = per_brake_energy_J(e_rto, n_braked_wheels, reverse_credit)
    per_land = per_brake_energy_J(e_land, n_braked_wheels, reverse_credit)

    if per_rto >= per_land:
        governing_case = "rto"
        per_brake_governing = per_rto
    else:
        governing_case = "landing"
        per_brake_governing = per_land

    required_mass = required_heat_sink_mass_kg(
        per_brake_governing, cp, delta_t_allowable_K)
    actual_rise = temperature_rise_K(
        per_brake_governing, heat_sink_mass_available_kg, cp)
    delta_t_margin = delta_t_allowable_K - actual_rise
    distance = braking_distance_m(inputs["v1_m_s"], inputs["decel_g"])

    if delta_t_margin >= 0.0 and required_mass <= heat_sink_mass_available_kg:
        verdict = "brake-energy-pass"
    else:
        verdict = "brake-energy-fail"

    return {
        "E_rto_J": e_rto,
        "E_land_J": e_land,
        "per_brake_rto_J": per_rto,
        "per_brake_landing_J": per_land,
        "governing_case": governing_case,
        "per_brake_governing_J": per_brake_governing,
        "required_heat_sink_mass_kg": required_mass,
        "heat_sink_mass_available_kg": heat_sink_mass_available_kg,
        "actual_temperature_rise_K": actual_rise,
        "delta_t_allowable_K": delta_t_allowable_K,
        "delta_t_margin_K": delta_t_margin,
        "braking_distance_m": distance,
        "verdict": verdict,
    }
