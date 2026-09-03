"""Rocket turbopump pump-level sizing logic (pure stdlib).

Sizes the centrifugal pump inside a liquid rocket engine turbopump from
the discharge pressure rise, propellant flow, shaft speed and suction
conditions: head, dimensionless specific speed, impeller tip speed and
diameter from the design head coefficient, pump power at the given
efficiency, available net positive suction head, suction specific speed,
and the cavitation verdict against the suction specific speed limit.

Boundary: the feed cycle and cycle-level pump discharge pressure and
power balance belong to propulsion/rocket/rocket-engine-cycle; this
module sizes the pump once discharge pressure rise and flow are fixed.

SI units throughout. Deterministic, offline, stdlib only.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
PSI_DESIGN = 0.55  # design head coefficient, centrifugal pump impeller
S_CRIT = 3.0  # dimensionless suction specific speed limit for the verdict


def omega_from_rpm(rpm):
    """Convert shaft speed in rpm to angular speed in rad/s."""
    if rpm <= 0:
        raise ValueError("rpm must be positive")
    return 2.0 * math.pi * rpm / 60.0


def head_rise_m(pressure_rise, density):
    """Pump head rise H = pressure_rise / (density * G0), in meters."""
    if pressure_rise <= 0:
        raise ValueError("pressure_rise must be positive")
    if density <= 0:
        raise ValueError("density must be positive")
    return pressure_rise / (density * G0)


def specific_speed(omega, volume_flow, head_m):
    """Dimensionless specific speed N_s = omega*sqrt(Q)/(G0*H)**0.75."""
    if omega <= 0:
        raise ValueError("omega must be positive")
    if volume_flow <= 0:
        raise ValueError("volume_flow must be positive")
    if head_m <= 0:
        raise ValueError("head_m must be positive")
    return omega * math.sqrt(volume_flow) / (G0 * head_m) ** 0.75


def impeller_tip_speed(head_m, psi=PSI_DESIGN):
    """Impeller tip speed u2 = sqrt(G0 * head_m / psi), in m/s."""
    if head_m <= 0:
        raise ValueError("head_m must be positive")
    if psi <= 0:
        raise ValueError("psi must be positive")
    return math.sqrt(G0 * head_m / psi)


def impeller_diameter(tip_speed, omega):
    """Impeller diameter D = 2 * tip_speed / omega, in meters."""
    if tip_speed <= 0:
        raise ValueError("tip_speed must be positive")
    if omega <= 0:
        raise ValueError("omega must be positive")
    return 2.0 * tip_speed / omega


def pump_power(volume_flow, pressure_rise, efficiency):
    """Pump hydraulic input power P = Q * pressure_rise / efficiency, in W."""
    if volume_flow <= 0:
        raise ValueError("volume_flow must be positive")
    if pressure_rise <= 0:
        raise ValueError("pressure_rise must be positive")
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("efficiency must be in (0, 1]")
    return volume_flow * pressure_rise / efficiency


def npsh_available(inlet_pressure, vapor_pressure, density):
    """Available NPSH = (p_inlet - p_vapor) / (density * G0), in meters."""
    if inlet_pressure <= vapor_pressure:
        raise ValueError("inlet_pressure must exceed vapor_pressure")
    if density <= 0:
        raise ValueError("density must be positive")
    return (inlet_pressure - vapor_pressure) / (density * G0)


def suction_specific_speed(omega, volume_flow, npsh_m):
    """Dimensionless suction specific speed S = omega*sqrt(Q)/(G0*NPSH)**0.75."""
    if omega <= 0:
        raise ValueError("omega must be positive")
    if volume_flow <= 0:
        raise ValueError("volume_flow must be positive")
    if npsh_m <= 0:
        raise ValueError("npsh_m must be positive")
    return omega * math.sqrt(volume_flow) / (G0 * npsh_m) ** 0.75


def cavitation_verdict(suction_specific_speed_value, s_crit=S_CRIT):
    """Verdict string: acceptable at or above s_crit, else cavitation-risk."""
    if s_crit <= 0:
        raise ValueError("s_crit must be positive")
    if suction_specific_speed_value >= s_crit:
        return "acceptable"
    return "cavitation-risk"


def size_pump(rpm, volume_flow, pressure_rise, density, efficiency,
              inlet_pressure, vapor_pressure):
    """Chain the pump sizing functions into one result dict.

    Returns omega, head_m, specific_speed, tip_speed_ms, diameter_m,
    power_W, npsh_m, suction_specific_speed, verdict. ValueErrors from
    the individual functions propagate.
    """
    omega = omega_from_rpm(rpm)
    head_m = head_rise_m(pressure_rise, density)
    ns = specific_speed(omega, volume_flow, head_m)
    tip_speed_ms = impeller_tip_speed(head_m)
    diameter_m = impeller_diameter(tip_speed_ms, omega)
    power_w = pump_power(volume_flow, pressure_rise, efficiency)
    npsh_m = npsh_available(inlet_pressure, vapor_pressure, density)
    s = suction_specific_speed(omega, volume_flow, npsh_m)
    verdict = cavitation_verdict(s)
    return {
        "omega": omega,
        "head_m": head_m,
        "specific_speed": ns,
        "tip_speed_ms": tip_speed_ms,
        "diameter_m": diameter_m,
        "power_W": power_w,
        "npsh_m": npsh_m,
        "suction_specific_speed": s,
        "verdict": verdict,
    }
