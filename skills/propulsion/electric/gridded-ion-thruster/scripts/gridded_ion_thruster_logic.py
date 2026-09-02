#!/usr/bin/env python3
"""Gridded ion thruster (Kaufman type) performance and sizing.

Pure Python 3, stdlib only, SI units throughout. Implements the standard
electrostatic gridded thruster model used in electric propulsion analysis:

  - ion exhaust velocity through the net beam voltage:
      v_i = sqrt(2*e*V_net/m_i)  (singly charged ion)
  - specific impulse: I_sp = v_i / g0
  - Child-Langmuir space-charge-limited planar current density:
      J_CL = (4*eps0/9) * sqrt(2*e/m_i) * V_net^(3/2) / d^2
    where d is the effective screen-to-accelerator gap; grids run below
    this limit at a perveance margin
  - beam current from perveance margin, extraction area and grid
    transparency: I_b = eta_perv * J_CL * A_extract * eta_grid
  - thrust from the beam current:
      T = I_b * sqrt(2*m_i*V_net/e) * eta_d (divergence optional)
  - thrust from power (sizing bridge): T = 2*eta_T*P/(g0*I_sp)
  - beam power P_b = I_b * V_net; total input power
      P_total = P_b / eta_power  (thruster plus PPU losses)
  - rocket-equation propellant mass for a delta-v mission
  - gridded vs hall thruster comparison at equal input power

All functions validate their inputs and raise ValueError on physically
invalid values (non-positive voltage, gap, area, current, power, mass,
and efficiency or perveance margin outside (0, 1]).
"""

import math

# Fundamental constants, SI.
E_CHARGE = 1.602176634e-19   # elementary charge, C
G0 = 9.80665                 # standard gravity, m/s^2
EPS0 = 8.8541878128e-12      # vacuum permittivity, F/m
AMU = 1.66054e-27            # unified atomic mass unit, kg

# Deterministic propellant property table (standard reference values).
# atomic_mass_u: relative atomic mass in u (Xe 131.293, Kr 83.798).
PROPELLANTS = {
    "xenon": {"atomic_mass_u": 131.293},
    "krypton": {"atomic_mass_u": 83.798},
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


def xenon_ion_mass():
    """Xenon ion mass in kg (131.293 u), the default gridded propellant."""
    return ion_mass_from_u(PROPELLANTS["xenon"]["atomic_mass_u"])


def exhaust_velocity(net_voltage, ion_mass):
    """Ion exhaust velocity through the net beam voltage.

    v_i = sqrt(2*e*V_net/m_i), the velocity of a singly charged ion
    accelerated through the full screen-to-accelerator net voltage
    V_net. This is the ideal axial velocity before any divergence loss.
    """
    _require_positive(net_voltage, "net_voltage")
    _require_positive(ion_mass, "ion_mass")
    return math.sqrt(2.0 * E_CHARGE * net_voltage / ion_mass)


def isp_from_net_voltage(net_voltage, ion_mass):
    """Specific impulse of the ion beam, I_sp = v_i / g0."""
    return exhaust_velocity(net_voltage, ion_mass) / G0


def child_langmuir_density(net_voltage, gap, ion_mass):
    """Child-Langmuir space-charge-limited planar current density.

    J_CL = (4*eps0/9) * sqrt(2*e/m_i) * V_net^(3/2) / d^2 in A/m^2, with
    d the effective acceleration gap (screen-to-accelerator spacing, m).
    The extracted beam density cannot exceed this limit for a given
    voltage and gap; real ion optics run below it.
    """
    _require_positive(net_voltage, "net_voltage")
    _require_positive(gap, "gap")
    _require_positive(ion_mass, "ion_mass")
    factor = 4.0 * EPS0 / 9.0
    return (factor * math.sqrt(2.0 * E_CHARGE / ion_mass)
            * net_voltage ** 1.5 / (gap * gap))


def beam_current_from_perveance(net_voltage, gap, extract_area,
                                grid_transparency, perveance_margin,
                                ion_mass):
    """Beam current the ion optics can deliver at a perveance margin.

    I_b = eta_perv * J_CL * A_extract * eta_grid, where eta_perv is the
    perveance margin (typical 0.4 to 0.8, grids are run below the
    space-charge limit) and eta_grid the grid transparency (fraction of
    the extraction plane actually open to beamlets).
    """
    _require_positive(net_voltage, "net_voltage")
    _require_positive(gap, "gap")
    _require_positive(extract_area, "extract_area")
    _require_eta(grid_transparency, "grid_transparency")
    _require_eta(perveance_margin, "perveance_margin")
    _require_positive(ion_mass, "ion_mass")
    j_cl = child_langmuir_density(net_voltage, gap, ion_mass)
    return perveance_margin * j_cl * extract_area * grid_transparency


def thrust_from_beam_current(beam_current, net_voltage, ion_mass,
                             divergence_efficiency=1.0):
    """Thrust from the beam (ion) current alone.

    T = I_b * sqrt(2*m_i*V_net/e) * eta_d. Valid for singly charged,
    axial ions; divergence_efficiency is cos of the mean beam half-angle
    (about 0.98 to 0.995 in practice).
    """
    _require_positive(beam_current, "beam_current")
    _require_positive(net_voltage, "net_voltage")
    _require_positive(ion_mass, "ion_mass")
    _require_eta(divergence_efficiency, "divergence_efficiency")
    return beam_current * math.sqrt(2.0 * ion_mass * net_voltage / E_CHARGE) \
        * divergence_efficiency


def beam_power(beam_current, net_voltage):
    """Beam power, P_b = I_b * V_net."""
    _require_positive(beam_current, "beam_current")
    _require_positive(net_voltage, "net_voltage")
    return beam_current * net_voltage


def total_power(beam_power_value, eta_power):
    """Total input power from beam power and the power chain efficiency.

    P_total = P_b / eta_power. eta_power covers the discharge chamber
    (ionization cost) and the power processing unit losses, so it sits
    below the total efficiency eta_T used in the sizing bridge.
    """
    _require_positive(beam_power_value, "beam_power_value")
    _require_eta(eta_power, "eta_power")
    return beam_power_value / eta_power


def thrust_from_power(power, eta_total, isp):
    """Thrust from input power, total efficiency and specific impulse.

    T = 2 * eta_T * P / (g0 * I_sp). The sizing bridge between power,
    efficiency and impulse. Raises ValueError for non-positive power
    (the contract gate) or out-of-range efficiency.
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


def mass_flow_from_thrust(thrust, isp):
    """Total propellant mass flow for a thrust and specific impulse.

    m_dot = T / (g0 * I_sp).
    """
    _require_positive(thrust, "thrust")
    _require_positive(isp, "isp")
    return thrust / (G0 * isp)


def propellant_mass_for_delta_v(delta_v, dry_mass, isp):
    """Propellant mass for a delta-v mission (rocket equation).

    m_prop = m_dry * (exp(delta_v / (g0 * I_sp)) - 1). dry_mass is the
    final (post-burn) mass; total initial mass is m_dry + m_prop.
    """
    _require_non_negative(delta_v, "delta_v")
    _require_positive(dry_mass, "dry_mass")
    _require_positive(isp, "isp")
    return dry_mass * (math.exp(delta_v / (G0 * isp)) - 1.0)


def gridded_vs_hall_compare(power, gridded_isp, hall_isp,
                            gridded_efficiency, hall_efficiency):
    """Compare a gridded ion thruster with a hall thruster at equal power.

    Both are run through the sizing bridge T = 2*eta_T*P/(g0*I_sp).
    Gridded ion optics run at high net voltage (I_sp roughly 3000 to
    4500 s, total efficiency 0.6 to 0.7); the hall thruster runs at low
    discharge voltage (I_sp roughly 1500 to 2000 s, total efficiency
    0.45 to 0.6). At equal power the gridded thruster therefore delivers
    less thrust per kilowatt but a much higher specific impulse and a
    far lower propellant mass flow. Thrust density is not returned as a
    number: gridded extraction is space-charge limited by the Child-
    Langmuir density across the accelerator grid, which keeps the
    thrust density lower than the crossed-field hall discharge.
    """
    _require_positive(power, "power")
    _require_positive(gridded_isp, "gridded_isp")
    _require_positive(hall_isp, "hall_isp")
    _require_eta(gridded_efficiency, "gridded_efficiency")
    _require_eta(hall_efficiency, "hall_efficiency")

    def _side(isp, eta):
        t = thrust_from_power(power, eta, isp)
        return {
            "thrust": t,
            "thrust_to_power": thrust_to_power(t, power),
            "isp": isp,
            "mass_flow": mass_flow_from_thrust(t, isp),
        }

    gridded = _side(gridded_isp, gridded_efficiency)
    hall = _side(hall_isp, hall_efficiency)
    return {
        "power": power,
        "gridded": gridded,
        "hall": hall,
        "thrust_ratio_gridded_over_hall":
            gridded["thrust"] / hall["thrust"],
        "isp_ratio_gridded_over_hall":
            gridded["isp"] / hall["isp"],
        "mass_flow_ratio_gridded_over_hall":
            gridded["mass_flow"] / hall["mass_flow"],
    }


if __name__ == "__main__":
    # Worked example: 1100 V xenon gridded thruster (matches the
    # contract test and the SKILL.md worked example).
    m_xe = xenon_ion_mass()
    v_net = 1100.0
    gap = 0.8e-3
    a_extract = 0.028
    eta_grid = 0.68
    eta_perv = 0.6
    eta_d = 0.985
    eta_t = 0.65

    v_i = exhaust_velocity(v_net, m_xe)
    isp = isp_from_net_voltage(v_net, m_xe)
    j_cl = child_langmuir_density(v_net, gap, m_xe)
    i_b = beam_current_from_perveance(v_net, gap, a_extract, eta_grid,
                                      eta_perv, m_xe)
    t = thrust_from_beam_current(i_b, v_net, m_xe, eta_d)
    p_b = beam_power(i_b, v_net)
    p_total = total_power(p_b, 0.66)
    t_bridge = thrust_from_power(p_total, eta_t, isp)
    m_prop = propellant_mass_for_delta_v(2000.0, 1000.0, isp)
    print("m_i = %.6e kg" % m_xe)
    print("v_i = %.4f m/s" % v_i)
    print("I_sp = %.4f s" % isp)
    print("J_CL = %.4f A/m^2" % j_cl)
    print("I_b = %.6f A" % i_b)
    print("T (beam, eta_d=0.985) = %.6f N" % t)
    print("P_b = %.4f W" % p_b)
    print("P_total = %.4f W" % p_total)
    print("T/P_total = %.6e N/W (%.2f mN/kW)" %
          (t / p_total, t / p_total * 1e6))
    print("T bridge at eta_T=0.65 = %.6f N" % t_bridge)
    print("m_prop (dv=2000 m/s, m_dry=1000 kg) = %.4f kg" % m_prop)
    cmp_ = gridded_vs_hall_compare(5000.0, 4100.0, 1600.0, 0.65, 0.5)
    print("gridded/hall T ratio = %.4f, Isp ratio = %.4f, mdot ratio = %.5f"
          % (cmp_["thrust_ratio_gridded_over_hall"],
             cmp_["isp_ratio_gridded_over_hall"],
             cmp_["mass_flow_ratio_gridded_over_hall"]))
