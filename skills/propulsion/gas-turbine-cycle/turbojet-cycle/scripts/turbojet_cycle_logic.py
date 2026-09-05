"""Ideal single-stream turbojet core cycle at flight Mach number (pure stdlib).

Station sequence: 0 freestream, 3 compressor exit, 4 combustor exit (turbine
inlet), 5 turbine exit, 9 nozzle exit.  The ideal cycle uses the module gas
constants gamma = 1.4, cp_c = 1005 J/(kg K) on the cold side, cp_g =
1150 J/(kg K) on the hot side and R = 287 J/(kg K); every function accepts
keyword overrides.  All inputs and outputs are SI: K, kg/(kg air), N/(kg/s),
kg/(N s), m/s.  Deterministic, offline, no third-party imports.

The cycle closes through the compressor-turbine work balance: the turbine
exit total temperature follows from matching the turbine shaft work to the
compressor work, which is the canonical compressor-turbine matching step of
a core-engine cycle assessment.  The nozzle expands the remaining total
pressure to ambient and the net specific thrust is the exit velocity minus
the flight velocity, so ram drag appears explicitly at Mach number.
"""

import math

GAMMA = 1.4        # ratio of specific heats (cold and hot side)
CP_C = 1005.0      # cold-side specific heat at constant pressure, J/(kg K)
CP_G = 1150.0      # hot-side specific heat at constant pressure, J/(kg K)
R = 287.0          # gas constant for air, J/(kg K)
LHV = 43.0e6       # fuel lower heating value, J/kg (Jet A class)
ETA_B = 0.99       # combustor efficiency default


def _check_finite(*values):
    """Reject NaN and infinite inputs with ValueError."""
    for v in values:
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("inputs must be finite numbers")


def _check_positive_temperature(t):
    if t <= 0.0:
        raise ValueError("temperatures must be positive (K)")


def freestream_stagnation_temperature(t0, mach, gamma=GAMMA):
    """Freestream total temperature from the flight Mach number:
    Tt0 = t0 * (1 + (gamma - 1) / 2 * mach^2)."""
    _check_finite(t0, mach, gamma)
    _check_positive_temperature(t0)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    return t0 * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)


def compressor_exit_temperature(t0, mach, pr, gamma=GAMMA):
    """Compressor exit total temperature T03 = Tt0 * pr^((gamma-1)/gamma)."""
    _check_finite(t0, mach, pr, gamma)
    _check_positive_temperature(t0)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    if pr <= 1.0:
        raise ValueError("pressure ratio must exceed 1")
    tt0 = freestream_stagnation_temperature(t0, mach, gamma)
    return tt0 * pr ** ((gamma - 1.0) / gamma)


def fuel_air_ratio(t03, t04, eta_b=ETA_B, lhv=LHV, cp_c=CP_C):
    """Fuel-to-air ratio from the combustor energy balance:
    f = cp_c * (t04 - t03) / (eta_b * lhv)."""
    _check_finite(t03, t04, eta_b, lhv, cp_c)
    _check_positive_temperature(t03)
    _check_positive_temperature(t04)
    if t04 <= t03:
        raise ValueError("turbine inlet temperature must exceed the compressor exit temperature")
    if not (0.0 < eta_b <= 1.0):
        raise ValueError("combustor efficiency must lie in (0, 1]")
    if lhv <= 0.0:
        raise ValueError("lower heating value must be positive")
    return cp_c * (t04 - t03) / (eta_b * lhv)


def turbine_exit_temperature(t03, t04, t0, mach, cp_c=CP_C, cp_g=CP_G, gamma=GAMMA):
    """Turbine exit total temperature from the compressor-turbine work
    balance: Tt5 = t04 - (cp_c / cp_g) * (t03 - Tt0)."""
    _check_finite(t03, t04, t0, mach, cp_c, cp_g, gamma)
    _check_positive_temperature(t03)
    _check_positive_temperature(t04)
    _check_positive_temperature(t0)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    tt0 = freestream_stagnation_temperature(t0, mach, gamma)
    if t03 < tt0:
        raise ValueError("compressor exit temperature below the stagnation value is non-physical")
    return t04 - (cp_c / cp_g) * (t03 - tt0)


def nozzle_exit_temperature(t0, mach, pr, t04, t05=None, cp_c=CP_C, cp_g=CP_G,
                            gamma=GAMMA):
    """Nozzle exit static temperature T9 = Tt5 * (p0/pt5)^((gamma-1)/gamma)
    with the nozzle total pressure ratio
    pt5/p0 = (1 + (gamma-1)/2*mach^2)^(gamma/(gamma-1)) * pr *
             (Tt5/Tt4)^(gamma/(gamma-1)).
    t05 defaults to the turbine exit state from the step 5 work balance."""
    _check_finite(t0, mach, pr, t04, cp_c, cp_g, gamma)
    _check_positive_temperature(t0)
    _check_positive_temperature(t04)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    if pr <= 1.0:
        raise ValueError("pressure ratio must exceed 1")
    if t05 is None:
        t03 = compressor_exit_temperature(t0, mach, pr, gamma)
        t05 = turbine_exit_temperature(t03, t04, t0, mach, cp_c, cp_g, gamma)
    _check_finite(t05)
    _check_positive_temperature(t05)
    ram = (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (gamma / (gamma - 1.0))
    pt5_over_p0 = ram * pr * (t05 / t04) ** (gamma / (gamma - 1.0))
    if pt5_over_p0 <= 1.0:
        raise ValueError("nozzle total pressure ratio at or below one: state does not expand to ambient")
    return t05 * (1.0 / pt5_over_p0) ** ((gamma - 1.0) / gamma)


def exit_velocity(t05, t9, cp_g=CP_G):
    """Nozzle exit velocity from the thermal expansion across the nozzle:
    v9 = sqrt(2 * cp_g * (Tt5 - T9))."""
    _check_finite(t05, t9, cp_g)
    _check_positive_temperature(t05)
    _check_positive_temperature(t9)
    if t9 >= t05:
        raise ValueError("nozzle exit static temperature must stay below the total temperature")
    return math.sqrt(2.0 * cp_g * (t05 - t9))


def net_specific_thrust(t0, mach, t05, t9, cp_g=CP_G, gamma=GAMMA, r=R):
    """Net specific thrust F/mdot = v9 - v0 with the flight velocity
    v0 = mach * sqrt(gamma * R * t0)."""
    _check_finite(t0, mach, t05, t9, cp_g, gamma, r)
    _check_positive_temperature(t0)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    v9 = exit_velocity(t05, t9, cp_g)
    v0 = mach * math.sqrt(gamma * r * t0)
    return v9 - v0


def turbojet_tsfc(f, f_over_mdot):
    """Turbojet thrust specific fuel consumption TSFC = f / (F/mdot) in
    kg/(N s)."""
    _check_finite(f, f_over_mdot)
    if f < 0.0:
        raise ValueError("fuel-to-air ratio must be non-negative")
    if f_over_mdot <= 0.0:
        raise ValueError("specific thrust must be positive")
    return f / f_over_mdot


def propulsive_efficiency(v0, v9):
    """Propulsive efficiency eta_p = 2 * v0 / (v0 + v9)."""
    _check_finite(v0, v9)
    if v0 < 0.0 or v9 <= 0.0:
        raise ValueError("velocities must be non-negative with a positive exit velocity")
    return 2.0 * v0 / (v0 + v9)


def cycle_report(t0, mach, pr, t04, eta_b=ETA_B, lhv=LHV, cp_c=CP_C,
                 cp_g=CP_G, gamma=GAMMA, r=R):
    """Full cycle report dict with keys tt0, t03, fuel_air, t05, t9, v9,
    specific_thrust, tsfc and propulsive_efficiency."""
    _check_finite(t0, mach, pr, t04, eta_b, lhv, cp_c, cp_g, gamma, r)
    _check_positive_temperature(t0)
    _check_positive_temperature(t04)
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    if pr <= 1.0:
        raise ValueError("pressure ratio must exceed 1")
    if not (0.0 < eta_b <= 1.0):
        raise ValueError("combustor efficiency must lie in (0, 1]")
    if lhv <= 0.0:
        raise ValueError("lower heating value must be positive")
    tt0 = freestream_stagnation_temperature(t0, mach, gamma)
    t03 = compressor_exit_temperature(t0, mach, pr, gamma)
    if t04 <= t03:
        raise ValueError("turbine inlet temperature must exceed the compressor exit temperature")
    f = fuel_air_ratio(t03, t04, eta_b, lhv, cp_c)
    t05 = turbine_exit_temperature(t03, t04, t0, mach, cp_c, cp_g, gamma)
    t9 = nozzle_exit_temperature(t0, mach, pr, t04, t05, cp_c, cp_g, gamma)
    v9 = exit_velocity(t05, t9, cp_g)
    v0 = mach * math.sqrt(gamma * r * t0)
    specific_thrust = v9 - v0
    tsfc = turbojet_tsfc(f, specific_thrust)
    eta_p = propulsive_efficiency(v0, v9)
    return {
        "tt0": tt0,
        "t03": t03,
        "fuel_air": f,
        "t05": t05,
        "t9": t9,
        "v9": v9,
        "specific_thrust": specific_thrust,
        "tsfc": tsfc,
        "propulsive_efficiency": eta_p,
    }


if __name__ == "__main__":
    rep = cycle_report(288.15, 0.9, 18.0, 1600.0)
    for key, value in rep.items():
        print("%-20s %.6g" % (key, value))
