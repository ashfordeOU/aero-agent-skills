"""Electrothermal thruster (resistojet, arcjet) performance analysis.

Pure stdlib module for spacecraft electric propulsion. Converts input
electrical power into propellant enthalpy (useful heating power), sizes
the propellant mass flow from the heating power and temperature rise,
expands the heated propellant ideally to vacuum, and reports thrust,
exhaust velocity, specific impulse, thrust efficiency and the
thrust-to-power ratio for a single resistojet or arcjet operating point.

Ideal-model assumptions (documented in SKILL.md): vacuum nozzle with
p_e = 0 so the pressure thrust term vanishes, frozen-flow and
finite-area-ratio losses folded into eta_nozzle. Electrostatic
thrusters are out of scope (gridded-ion-thruster and hall-thruster own
ion acceleration claims).
"""

import math

# Standard gravity, m/s^2.
G0 = 9.80665

# Propellant thermophysical values at 300 K, reference-only per the leaf
# spec: cp in J/(kg K), gamma the specific-heat ratio.
PROPELLANTS = {
    "NH3": {"cp": 2090.0, "gamma": 1.31},
    "N2": {"cp": 1040.0, "gamma": 1.40},
    "H2": {"cp": 14300.0, "gamma": 1.41},
    "He": {"cp": 5190.0, "gamma": 1.67},
}

# Typical published specific-impulse bands, s. The leaf reports whether
# an operating point lies in its family band; it does not enforce them.
RESISTOJET_ISP_BAND = (200.0, 350.0)
ARCJET_ISP_BAND = (400.0, 700.0)

# Default family parameters.
DEFAULT_ETA_HEAT = 0.85  # resistojet family heating efficiency.
ARCJET_ETA_HEAT = 0.7  # arcjet family heating efficiency.
DEFAULT_ETA_NOZZLE = 0.9
DEFAULT_GAMMA = 1.3  # working-gas family fallback.
DEFAULT_ETA_HEAT_FAMILY = {"resistojet": DEFAULT_ETA_HEAT, "arcjet": ARCJET_ETA_HEAT}


def propellant_properties(name):
    """Return (cp, gamma) for a propellant name, ValueError if unknown.

    cp is the 300 K specific heat in J/(kg K); gamma the specific-heat
    ratio. Values are reference-only, used to support the trade.
    """
    try:
        entry = PROPELLANTS[name]
    except KeyError:
        raise ValueError(
            "unknown propellant {0!r}; choose from {1}".format(
                name, ", ".join(sorted(PROPELLANTS))
            )
        ) from None
    return entry["cp"], entry["gamma"]


def useful_heating_power(eta_heat, p_elec):
    """Return the useful heating power P_heat = eta_heat * P_elec (W)."""
    if not math.isfinite(eta_heat) or not math.isfinite(p_elec):
        raise ValueError("eta_heat and p_elec must be finite")
    if not 0.0 < eta_heat <= 1.0:
        raise ValueError("eta_heat must lie in (0, 1]")
    if p_elec <= 0.0:
        raise ValueError("p_elec must be positive")
    return eta_heat * p_elec


def mass_flow_from_heating(p_heat, cp, t0, t_in):
    """Return mass flow mdot = P_heat / (cp * (T_0 - T_in)) in kg/s.

    Assumes all useful heating power goes into raising propellant
    enthalpy from the plenum temperature T_in to the chamber
    temperature T_0.
    """
    if not math.isfinite(p_heat) or not math.isfinite(cp):
        raise ValueError("p_heat and cp must be finite")
    if not math.isfinite(t0) or not math.isfinite(t_in):
        raise ValueError("t0 and t_in must be finite")
    if p_heat < 0.0:
        raise ValueError("p_heat must be non-negative")
    if cp <= 0.0:
        raise ValueError("cp must be positive")
    if t_in <= 0.0:
        raise ValueError("t_in must be positive")
    if t0 <= t_in:
        raise ValueError("t0 must exceed t_in")
    return p_heat / (cp * (t0 - t_in))


def exhaust_velocity_ideal(cp, eta_nozzle, t0):
    """Return the ideal vacuum exhaust velocity sqrt(2*cp*eta_nozzle*T_0).

    Vacuum form: with p_e = 0 the pressure ratio term
    (1 - (p_e/p_0)^((gamma-1)/gamma)) collapses to one, so gamma does
    not enter. Frozen-flow and finite-area-ratio losses are folded
    into eta_nozzle.
    """
    if not math.isfinite(cp) or not math.isfinite(eta_nozzle):
        raise ValueError("cp and eta_nozzle must be finite")
    if not math.isfinite(t0):
        raise ValueError("t0 must be finite")
    if cp <= 0.0:
        raise ValueError("cp must be positive")
    if not 0.0 < eta_nozzle <= 1.0:
        raise ValueError("eta_nozzle must lie in (0, 1]")
    if t0 <= 0.0:
        raise ValueError("t0 must be positive")
    return math.sqrt(2.0 * cp * eta_nozzle * t0)


def thrust_from_mass_flow(mdot, v_e):
    """Return thrust F = mdot * v_e (N), fully expanded vacuum nozzle.

    The pressure term (p_e - p_a) * A_e vanishes in vacuum with p_e = 0.
    """
    if not math.isfinite(mdot) or not math.isfinite(v_e):
        raise ValueError("mdot and v_e must be finite")
    if mdot < 0.0:
        raise ValueError("mdot must be non-negative")
    if v_e < 0.0:
        raise ValueError("v_e must be non-negative")
    return mdot * v_e


def specific_impulse(v_e):
    """Return specific impulse Isp = v_e / g0 (s)."""
    if not math.isfinite(v_e):
        raise ValueError("v_e must be finite")
    if v_e < 0.0:
        raise ValueError("v_e must be non-negative")
    return v_e / G0


def thrust_efficiency(f, mdot, p_elec):
    """Return thrust efficiency eta_t = F^2 / (2 * mdot * P_elec).

    Jet power over input power. In the ideal model eta_t equals
    eta_heat * eta_nozzle; the function returns the ratio from the
    computed point so the identity can be checked.
    """
    if not math.isfinite(f) or not math.isfinite(mdot):
        raise ValueError("f and mdot must be finite")
    if not math.isfinite(p_elec):
        raise ValueError("p_elec must be finite")
    if f < 0.0:
        raise ValueError("f must be non-negative")
    if mdot <= 0.0:
        raise ValueError("mdot must be positive")
    if p_elec <= 0.0:
        raise ValueError("p_elec must be positive")
    return (f * f) / (2.0 * mdot * p_elec)


def thrust_to_power(f, p_elec):
    """Return thrust-to-power ratio F / P_elec (N/W).

    Report mN/kW by scaling the return value by 1e6 in callers.
    """
    if not math.isfinite(f) or not math.isfinite(p_elec):
        raise ValueError("f and p_elec must be finite")
    if f < 0.0:
        raise ValueError("f must be non-negative")
    if p_elec <= 0.0:
        raise ValueError("p_elec must be positive")
    return f / p_elec


def operating_band_verdict(isp, thruster_family):
    """Return a string verdict on whether isp lies in the family band.

    Band lookup is by family name ('resistojet' or 'arcjet'); unknown
    families raise ValueError. Bands are typical published ranges and
    are reported, not enforced.
    """
    if not math.isfinite(isp):
        raise ValueError("isp must be finite")
    if isp < 0.0:
        raise ValueError("isp must be non-negative")
    if thruster_family == "resistojet":
        lo, hi = RESISTOJET_ISP_BAND
    elif thruster_family == "arcjet":
        lo, hi = ARCJET_ISP_BAND
    else:
        raise ValueError(
            "unknown thruster family {0!r}; choose resistojet or arcjet".format(
                thruster_family
            )
        )
    if lo <= isp <= hi:
        return "inside the typical {0} band ({1:.0f}-{2:.0f} s)".format(
            thruster_family, lo, hi
        )
    return "outside the typical {0} band ({1:.0f}-{2:.0f} s)".format(
        thruster_family, lo, hi
    )


def electrothermal_performance(
    p_elec,
    t0,
    t_in,
    propellant,
    eta_heat=None,
    eta_nozzle=DEFAULT_ETA_NOZZLE,
    family="resistojet",
):
    """Return the electrothermal operating point as a summary dict.

    Heats the propellant with eta_heat * p_elec of useful power, sizes
    the mass flow from the chamber temperature rise, expands ideally to
    vacuum and reports thrust, exhaust velocity, specific impulse,
    thrust efficiency and thrust-to-power (mN/kW). family defaults the
    heating efficiency and picks the typical Isp band for the verdict.
    """
    if not isinstance(propellant, str):
        raise ValueError("propellant must be a string name")
    cp, _gamma = propellant_properties(propellant)
    if family not in DEFAULT_ETA_HEAT_FAMILY:
        raise ValueError(
            "unknown thruster family {0!r}; choose resistojet or arcjet".format(
                family
            )
        )
    if eta_heat is None:
        eta_heat = DEFAULT_ETA_HEAT_FAMILY[family]
    p_heat = useful_heating_power(eta_heat, p_elec)
    mdot = mass_flow_from_heating(p_heat, cp, t0, t_in)
    v_e = exhaust_velocity_ideal(cp, eta_nozzle, t0)
    f = thrust_from_mass_flow(mdot, v_e)
    isp = specific_impulse(v_e)
    eta_t = thrust_efficiency(f, mdot, p_elec)
    return {
        "family": family,
        "propellant": propellant,
        "cp": cp,
        "eta_heat": eta_heat,
        "eta_nozzle": eta_nozzle,
        "p_elec": p_elec,
        "p_heat": p_heat,
        "t0": t0,
        "t_in": t_in,
        "mass_flow": mdot,
        "exhaust_velocity": v_e,
        "thrust": f,
        "specific_impulse": isp,
        "thrust_efficiency": eta_t,
        "thrust_to_power": f / p_elec,
        "thrust_to_power_mn_kw": f / p_elec * 1e6,
        "band_verdict": operating_band_verdict(isp, family),
    }


if __name__ == "__main__":
    # Sanity block: resistojet worked example from the leaf spec.
    _r = electrothermal_performance(
        1000.0, 1200.0, 300.0, "NH3", family="resistojet"
    )
    print("resistojet NH3 1 kW:", _r["mass_flow"], _r["exhaust_velocity"],
          _r["thrust"], _r["specific_impulse"], _r["band_verdict"])
