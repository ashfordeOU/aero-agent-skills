#!/usr/bin/env python3
"""Hall effect thruster (HET) design and performance analysis.

Pure Python 3, stdlib only, SI units throughout. Implements the standard
HET performance model used in electric propulsion analysis (Goebel and
Katz style decomposition):

  - thrust from beam current, mass flow and exhaust velocity:
      T = m_dot * v_e,  v_e = sqrt(2*e*V_b/m_i) * eta_m * eta_d
  - specific impulse: I_sp = v_e / g0
  - thrust-to-power ratio: T/P = 2*eta_T / (g0 * I_sp)
  - total efficiency decomposition:
      eta_T = eta_m * eta_v * eta_c * eta_d  (mass, voltage, current
      utilization, divergence efficiency)
  - anode vs total efficiency (auxiliary power split)
  - discharge power: P_d = V_d * I_d
  - xenon vs krypton propellant comparison (atomic mass, ionization
    energy, ideal exhaust velocity)
  - rocket-equation propellant mass for a delta-v mission

All functions validate their inputs and raise ValueError on physically
invalid values (non-positive power, voltage, current, mass, efficiency
outside (0, 1]).
"""

import math

# Fundamental constants, SI.
E_CHARGE = 1.602176634e-19   # elementary charge, C
G0 = 9.80665                 # standard gravity, m/s^2
AMU = 1.66053906660e-27      # unified atomic mass unit, kg

# Deterministic propellant property table (standard reference values).
# atomic_mass_u: relative atomic mass in u; ionization_eV: first
# ionization energy in electron volts (Xe 12.13 eV, Kr 14.00 eV).
PROPELLANTS = {
    "xenon": {"atomic_mass_u": 131.293, "ionization_eV": 12.1298},
    "krypton": {"atomic_mass_u": 83.798, "ionization_eV": 13.9996},
}


def _require_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_non_negative(value, name):
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def _require_eta(value, name):
    if not (0.0 < value <= 1.0):
        raise ValueError("%s must be in (0, 1], got %r" % (name, value))


def ion_mass_from_u(atomic_mass_u):
    """Convert relative atomic mass in u to kilograms."""
    _require_positive(atomic_mass_u, "atomic_mass_u")
    return atomic_mass_u * AMU


def ideal_exhaust_velocity(beam_voltage, ion_mass):
    """Ideal exhaust velocity of a singly charged ion, sqrt(2*e*V_b/m_i).

    beam_voltage: acceleration potential seen by the ions, V (the beam
    voltage V_b, which is the discharge voltage times the voltage
    utilization eta_v in the standard model).
    ion_mass: ion mass in kg (use ion_mass_from_u for u values).
    """
    _require_positive(beam_voltage, "beam_voltage")
    _require_positive(ion_mass, "ion_mass")
    return math.sqrt(2.0 * E_CHARGE * beam_voltage / ion_mass)


def exhaust_velocity(beam_voltage, ion_mass, eta_mass, eta_divergence):
    """Effective exhaust velocity with mass and divergence utilization.

    v_e = sqrt(2*e*V_b/m_i) * eta_m * eta_d. The mass utilization
    accounts for neutral (un-ionized) propellant leaving without
    acceleration; the divergence efficiency cos^2(theta) for a mean beam
    half-angle theta accounts for off-axis ion velocity components.
    """
    _require_eta(eta_mass, "eta_mass")
    _require_eta(eta_divergence, "eta_divergence")
    return ideal_exhaust_velocity(beam_voltage, ion_mass) * eta_mass * eta_divergence


def thrust_from_mass_flow(mass_flow, exhaust_velocity):
    """Thrust from total propellant mass flow and exhaust velocity, T = m_dot * v_e."""
    _require_positive(mass_flow, "mass_flow")
    _require_positive(exhaust_velocity, "exhaust_velocity")
    return mass_flow * exhaust_velocity


def thrust_from_beam_current(beam_current, beam_voltage, ion_mass,
                             divergence_efficiency=1.0):
    """Thrust from the beam (ion) current alone.

    T = I_b * sqrt(2*m_i*V_b/e) * eta_d. Carries only the divergence
    loss; mass and voltage utilization enter through the beam current
    and beam voltage definitions themselves.
    """
    _require_positive(beam_current, "beam_current")
    _require_eta(divergence_efficiency, "divergence_efficiency")
    return beam_current * math.sqrt(2.0 * ion_mass * beam_voltage / E_CHARGE) \
        * divergence_efficiency


def isp_from_exhaust_velocity(exhaust_velocity):
    """Specific impulse from exhaust velocity, I_sp = v_e / g0."""
    _require_positive(exhaust_velocity, "exhaust_velocity")
    return exhaust_velocity / G0


def mass_flow_from_thrust(thrust, isp):
    """Total propellant mass flow for a thrust and specific impulse.

    m_dot = T / (g0 * I_sp).
    """
    _require_positive(thrust, "thrust")
    _require_positive(isp, "isp")
    return thrust / (G0 * isp)


def thrust_from_power(power, eta_total, isp):
    """Thrust from input power, total efficiency and specific impulse.

    T = 2 * eta_T * P / (g0 * I_sp). Raises ValueError for non-positive
    power (the contract gate) or out-of-range efficiency.
    """
    _require_positive(power, "power")
    _require_eta(eta_total, "eta_total")
    _require_positive(isp, "isp")
    return 2.0 * eta_total * power / (G0 * isp)


def thrust_to_power(thrust, power):
    """Thrust-to-power ratio, T/P in N/W."""
    _require_positive(thrust, "thrust")
    _require_positive(power, "power")
    return thrust / power


def hall_thruster_efficiency(eta_mass, eta_voltage, eta_current,
                             eta_divergence):
    """Total efficiency decomposition.

    eta_T = eta_m * eta_v * eta_c * eta_d where
      eta_m: mass utilization, ion mass flow / total mass flow
      eta_v: voltage utilization, beam voltage / discharge voltage
      eta_c: current utilization, beam current / discharge current
      eta_d: divergence efficiency, cos^2(theta)
    """
    _require_eta(eta_mass, "eta_mass")
    _require_eta(eta_voltage, "eta_voltage")
    _require_eta(eta_current, "eta_current")
    _require_eta(eta_divergence, "eta_divergence")
    return eta_mass * eta_voltage * eta_current * eta_divergence


def beam_current(thrust, beam_voltage, ion_mass, divergence_efficiency=1.0):
    """Beam (ion) current required for a thrust at a given beam voltage.

    I_b = T / (eta_d * sqrt(2*m_i*V_b/e)).
    """
    _require_positive(thrust, "thrust")
    _require_eta(divergence_efficiency, "divergence_efficiency")
    return thrust / (divergence_efficiency
                     * math.sqrt(2.0 * ion_mass * beam_voltage / E_CHARGE))


def beam_current_from_mass_flow(mass_flow, eta_mass, ion_mass):
    """Beam current from ionized mass flow: I_b = e * eta_m * m_dot / m_i.

    Singly charged ions assumed.
    """
    _require_positive(mass_flow, "mass_flow")
    _require_eta(eta_mass, "eta_mass")
    return E_CHARGE * eta_mass * mass_flow / ion_mass


def discharge_power(discharge_voltage, discharge_current):
    """Discharge power, P_d = V_d * I_d."""
    _require_positive(discharge_voltage, "discharge_voltage")
    _require_positive(discharge_current, "discharge_current")
    return discharge_voltage * discharge_current


def discharge_current_from_beam(beam_current, current_utilization):
    """Discharge current from beam current and current utilization, I_d = I_b / eta_c."""
    _require_positive(beam_current, "beam_current")
    _require_eta(current_utilization, "current_utilization")
    return beam_current / current_utilization


def anode_efficiency(thrust, mass_flow, discharge_power):
    """Anode efficiency: thrust power over discharge power.

    eta_a = T^2 / (2 * m_dot * P_d). Excludes magnet, cathode keeper,
    heater and other auxiliary power.
    """
    _require_positive(thrust, "thrust")
    _require_positive(mass_flow, "mass_flow")
    _require_positive(discharge_power, "discharge_power")
    return thrust * thrust / (2.0 * mass_flow * discharge_power)


def total_efficiency_from_anode(anode_efficiency, discharge_power,
                                total_power):
    """Total efficiency from anode efficiency and the power split.

    eta_T = eta_a * P_d / P_total, where P_total includes the discharge
    power plus magnet, cathode and heater power. Requires
    total_power >= discharge_power.
    """
    _require_eta(anode_efficiency, "anode_efficiency")
    _require_positive(discharge_power, "discharge_power")
    if total_power < discharge_power:
        raise ValueError("total_power (%r) must be >= discharge_power (%r)"
                         % (total_power, discharge_power))
    if total_power <= 0:
        raise ValueError("total_power must be positive, got %r" % (total_power,))
    return anode_efficiency * discharge_power / total_power


def propellant_mass_for_delta_v(delta_v, dry_mass, isp):
    """Propellant mass for a delta-v mission (rocket equation).

    m_prop = m_dry * (exp(delta_v / (g0 * I_sp)) - 1). dry_mass is the
    final (post-burn) mass; total initial mass is m_dry + m_prop.
    """
    _require_non_negative(delta_v, "delta_v")
    _require_positive(dry_mass, "dry_mass")
    _require_positive(isp, "isp")
    return dry_mass * (math.exp(delta_v / (G0 * isp)) - 1.0)


def xenon_krypton_compare(beam_voltage):
    """Compare xenon and krypton as HET propellants at a beam voltage.

    Returns a dict with atomic mass (u and kg), first ionization energy
    (eV) and ideal exhaust velocity for each propellant, plus the
    krypton/xenon exhaust velocity ratio. Krypton is lighter, so it
    gives a higher ideal exhaust velocity at the same voltage, but its
    higher ionization energy (14.0 vs 12.1 eV) and lower atomic mass
    raise the ionization cost per unit thrust and lower the mass
    utilization in practice.
    """
    _require_positive(beam_voltage, "beam_voltage")
    out = {"beam_voltage": beam_voltage, "propellants": {}}
    for name in ("xenon", "krypton"):
        prop = PROPELLANTS[name]
        mass_kg = ion_mass_from_u(prop["atomic_mass_u"])
        out["propellants"][name] = {
            "atomic_mass_u": prop["atomic_mass_u"],
            "atomic_mass_kg": mass_kg,
            "ionization_eV": prop["ionization_eV"],
            "ideal_exhaust_velocity": ideal_exhaust_velocity(
                beam_voltage, mass_kg),
        }
    kr = out["propellants"]["krypton"]["ideal_exhaust_velocity"]
    xe = out["propellants"]["xenon"]["ideal_exhaust_velocity"]
    out["exhaust_velocity_ratio_kr_over_xe"] = kr / xe
    return out


if __name__ == "__main__":
    # 5 kW class sizing example (matches the contract test).
    power = 5000.0
    eta_total = 0.5
    isp = 1600.0
    thrust = thrust_from_power(power, eta_total, isp)
    mdot = mass_flow_from_thrust(thrust, isp)
    m_prop = propellant_mass_for_delta_v(2000.0, 500.0, isp)
    print("T = %.5f N" % thrust)
    print("m_dot = %.6e kg/s" % mdot)
    print("T/P = %.6e N/W" % thrust_to_power(thrust, power))
    print("m_prop (dv=2000 m/s, m_dry=500 kg) = %.3f kg" % m_prop)
