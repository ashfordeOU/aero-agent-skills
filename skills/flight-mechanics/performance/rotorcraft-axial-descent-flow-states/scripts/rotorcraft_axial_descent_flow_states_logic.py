"""Axial descent flow states of a helicopter rotor, windmill-brake momentum theory.

Pure stdlib categorization of the vertical-descent regime of a rotor
from the descent-rate ratio w = Vd / v_h: hover at Vd = 0, the
vortex-ring / turbulent-wake band 0 < w < 2, and the windmill-brake
state w >= 2, the only band on which momentum theory applies. The
module computes the hover induced velocity v_h = sqrt(T / (2 rho A))
from the thrust and disk area, the band limits (0, 2 v_h), the
windmill-brake induced velocity v_i = Vd/2 - sqrt((Vd/2)^2 - v_h^2)
(physical branch, v_i never exceeds v_h), the signed rotor power
P = k T (-Vd + v_i) + P_profile (negative when the rotor absorbs power
from the airstream) and torque Q = P / Omega, and the torque-reversal
condition c = P_profile / (k T) versus v_h that decides whether
momentum theory can close to the zero-shaft-power autorotative
equilibrium on the physical windmill-brake branch.

Conventions (SI): descent_rate Vd in m/s with Vd < 0 a climb that is
rejected, hover induced velocity v_h > 0, thrust T (N), disk area
A = PI * R^2, profile power P_profile (W), induced power factor k,
rotor speed Omega (rad/s). Momentum theory is used ONLY on the
windmill-brake branch Vd >= 2 v_h where it is valid; inside the
vortex-ring band the inflow is empirical (NASA TP-2005-213477,
public-domain context) and no induced velocity or power is computed by
this module. The zero-shaft-power crossing Vd = c + v_h^2 / c exists on
the physical branch only when c >= v_h; when c < v_h the formal
crossing would demand v_i = v_h^2 / c > v_h, impossible on the
windmill-brake branch, so the equilibrium is momentum-unreachable.

All functions return floats or dicts in SI units. Non-physical inputs
raise ValueError. Deterministic: no randomness anywhere.
"""

import math

# Module constants (SI).
RHO_SL = 1.225          # sea-level air density, kg/m^3 (default only)
G = 9.80665             # standard gravitational acceleration, m/s^2
K_INDUCED_DEFAULT = 1.15  # induced power factor for the worked case
PI = math.pi


def _require_positive(name, value):
    """Raise ValueError unless value > 0."""
    if value <= 0:
        raise ValueError("%s must be positive" % name)


def _require_non_negative(name, value):
    """Raise ValueError unless value >= 0."""
    if value < 0:
        raise ValueError("%s must be non-negative" % name)


def _require_descent(name, value):
    """Raise ValueError unless value >= 0 (Vd < 0 is a climb)."""
    if value < 0:
        raise ValueError("%s is negative; climb is not a descent state" % name)


def axial_flow_state(descent_rate, hover_induced_velocity):
    """Categorize the axial flow state from the descent-rate ratio.

    Vd = 0 returns "hover". 0 < Vd < 2 v_h returns
    "vortex-ring-band" (momentum theory invalid). Vd >= 2 v_h returns
    "windmill-brake" (momentum theory applies). Vd < 0 is a climb and
    raises ValueError; v_h <= 0 also raises ValueError.
    """
    _require_positive("hover_induced_velocity", hover_induced_velocity)
    _require_descent("descent_rate", descent_rate)
    if descent_rate == 0.0:
        return "hover"
    if descent_rate < 2.0 * hover_induced_velocity:
        return "vortex-ring-band"
    return "windmill-brake"


def vortex_ring_band_limits(hover_induced_velocity):
    """Descent-rate limits of the vortex-ring band, (0, 2 v_h) in m/s."""
    _require_positive("hover_induced_velocity", hover_induced_velocity)
    return (0.0, 2.0 * hover_induced_velocity)


def windmill_brake_induced_velocity(descent_rate, hover_induced_velocity):
    """Induced velocity on the physical windmill-brake branch.

    v_i = Vd/2 - sqrt((Vd/2)^2 - v_h^2), valid only for Vd >= 2 v_h,
    the boundary identity v_i(2 v_h) = v_h included. The branch keeps
    0 < v_i <= v_h, decreasing like v_h^2 / Vd as Vd grows. ValueError
    for Vd < 2 v_h (vortex-ring band, momentum theory does not apply)
    and for v_h <= 0.
    """
    _require_positive("hover_induced_velocity", hover_induced_velocity)
    _require_descent("descent_rate", descent_rate)
    if descent_rate < 2.0 * hover_induced_velocity:
        raise ValueError(
            "descent_rate below 2 * v_h lies inside the vortex-ring band, "
            "momentum theory does not apply"
        )
    half = descent_rate / 2.0
    return half - math.sqrt(half * half - hover_induced_velocity ** 2)


def rotor_descent_power(thrust_N, descent_rate, induced_velocity,
                        profile_power_W, k=K_INDUCED_DEFAULT):
    """Signed rotor shaft power in descent.

    P = k T (-Vd + v_i) + P_profile. The sign convention makes P
    negative when the rotor absorbs power from the airstream (the
    windmill-brake working state) and positive when the shaft must
    drive the rotor. ValueErrors on non-positive thrust, induced power
    factor, negative profile power, negative induced velocity and
    negative descent rate (climb).
    """
    _require_positive("thrust_N", thrust_N)
    _require_positive("k", k)
    _require_non_negative("profile_power_W", profile_power_W)
    _require_non_negative("induced_velocity", induced_velocity)
    _require_descent("descent_rate", descent_rate)
    return k * thrust_N * (-descent_rate + induced_velocity) + profile_power_W


def rotor_descent_torque(power_W, rotor_speed_rad_s):
    """Signed rotor torque in descent, Q = P / Omega.

    Sign follows the power: negative torque opposes the engine drive
    while the rotor absorbs power from the airstream. ValueError on
    Omega <= 0.
    """
    _require_positive("rotor_speed_rad_s", rotor_speed_rad_s)
    return power_W / rotor_speed_rad_s


def torque_reversal_condition(profile_power_W, thrust_N, k, v_h):
    """Zero-shaft-power reachability on the momentum windmill-brake branch.

    c = P_profile / (k T). The zero-power condition P = 0 demands
    Vd - v_i = c, which with the momentum quadratic v_i^2 - Vd v_i +
    v_h^2 = 0 gives v_i = v_h^2 / c and Vd = c + v_h^2 / c. That root
    sits on the physical branch only when v_i <= v_h, i.e. c >= v_h
    (then Vd >= 2 v_h by AM-GM); when c < v_h the required v_i would
    exceed v_h and the equilibrium is momentum-unreachable, living in
    the empirical vortex-ring / turbulent-wake regime.

    Returns dict {c, v_h, c_less_than_vh, verdict, momentum_root_Vd}
    with momentum_root_Vd None when unreachable.
    """
    _require_non_negative("profile_power_W", profile_power_W)
    _require_positive("thrust_N", thrust_N)
    _require_positive("k", k)
    _require_positive("v_h", v_h)
    c = profile_power_W / (k * thrust_N)
    c_less_than_vh = c < v_h
    if c_less_than_vh:
        verdict = ("momentum-unreachable: the autorotative equilibrium lies "
                   "in the empirical vortex-ring/turbulent-wake regime")
        root = None
    else:
        root = c + v_h * v_h / c
        verdict = ("momentum-reachable: zero-shaft-power root at "
                   "Vd = c + v_h^2 / c on the windmill-brake branch")
    return {
        "c": c,
        "v_h": v_h,
        "c_less_than_vh": c_less_than_vh,
        "verdict": verdict,
        "momentum_root_Vd": root,
    }


def descent_summary(thrust_N, rotor_radius, profile_power_W, descent_rate,
                    rho=RHO_SL, k=K_INDUCED_DEFAULT, rotor_speed_rad_s=None):
    """Bundle the axial-descent categorization for one operating point.

    Computes v_h = sqrt(T / (2 rho A)) with A = PI * R^2, the flow
    state and band limits, and on the windmill-brake branch only the
    induced velocity, signed power and torque. Inside the vortex-ring
    band and at hover the momentum fields are None because momentum
    theory does not apply there. torque_Nm is None when
    rotor_speed_rad_s is omitted (pass Omega to get torque). The
    momentum_root_reachable flag is the rotor-level torque-reversal
    verdict: whether the zero-shaft-power autorotative equilibrium is
    reachable on the physical windmill-brake branch.

    Returns dict with exactly the keys flow_state, v_h, band_limits,
    induced_velocity, power_W, torque_Nm, momentum_root_reachable.
    """
    _require_positive("thrust_N", thrust_N)
    _require_positive("rotor_radius", rotor_radius)
    _require_positive("rho", rho)
    _require_positive("k", k)
    _require_non_negative("profile_power_W", profile_power_W)
    _require_descent("descent_rate", descent_rate)
    if rotor_speed_rad_s is not None:
        _require_positive("rotor_speed_rad_s", rotor_speed_rad_s)

    area = PI * rotor_radius ** 2
    v_h = math.sqrt(thrust_N / (2.0 * rho * area))
    state = axial_flow_state(descent_rate, v_h)
    band = vortex_ring_band_limits(v_h)
    reachable = not torque_reversal_condition(
        profile_power_W, thrust_N, k, v_h)["c_less_than_vh"]

    if state == "windmill-brake":
        v_i = windmill_brake_induced_velocity(descent_rate, v_h)
        power = rotor_descent_power(thrust_N, descent_rate, v_i,
                                    profile_power_W, k)
        torque = None
        if rotor_speed_rad_s is not None:
            torque = rotor_descent_torque(power, rotor_speed_rad_s)
    else:
        v_i = None
        power = None
        torque = None

    return {
        "flow_state": state,
        "v_h": v_h,
        "band_limits": band,
        "induced_velocity": v_i,
        "power_W": power,
        "torque_Nm": torque,
        "momentum_root_reachable": reachable,
    }
