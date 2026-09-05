"""Bootstrap air cycle machine (ACM) cooling pack thermodynamics.

Pure stdlib, math only. Perfect-gas dry air with constant cp. Stations:
1 = pack-inlet bleed, 2 = compressor exit, 3 = heat-exchanger exit
(constant pressure, p3 = p2), 4 = cooling turbine exit at cabin pressure
p4 = p_cabin. Two-wheel bootstrap only: the turbine drives the
compressor on one shaft, so W_t must cover W_c for the pack to close.

Bleed assumption: p1 and T1 are the conditions at the pack inlet after
upstream bleed conditioning (the precooler context of the bleed-air
system sizing sibling). A production bootstrap pack places a primary ram
heat exchanger ahead of the pack compressor, so the pack-inlet
temperature is already the precooled value and this module never
re-derives it from the raw engine bleed temperature.

All functions raise ValueError on non-physical inputs.
"""

import math

GAMMA = 1.4
CP_AIR = 1005.0  # J/(kg K), constant-pressure specific heat of dry air
EXP = (GAMMA - 1.0) / GAMMA
REL_TOL = 1e-9  # turbine pressure-ratio consistency tolerance
BALANCE_TOL_W = 1.0  # shaft equality band, W


def compressor_exit(bleed_p1, bleed_t1, pr_c, eta_c):
    """Compressor exit state from the pack-inlet bleed condition.

    T2 = T1 * (1 + (pr_c^EXP - 1) / eta_c), p2 = p1 * pr_c.

    Args:
        bleed_p1: pack-inlet bleed pressure, Pa.
        bleed_t1: pack-inlet bleed temperature, K.
        pr_c: compressor pressure ratio (>= 1).
        eta_c: compressor isentropic efficiency in (0, 1).

    Returns:
        dict with keys "t2" and "p2" (K and Pa).

    Raises:
        ValueError: on non-positive bleed state, pr_c <= 1.0 or
            eta_c outside (0, 1).
    """
    if bleed_p1 <= 0:
        raise ValueError("bleed_p1 must be positive")
    if bleed_t1 <= 0:
        raise ValueError("bleed_t1 must be positive")
    if pr_c <= 1.0:
        raise ValueError("pr_c must be above 1.0")
    if not 0.0 < eta_c < 1.0:
        raise ValueError("eta_c must be in (0, 1)")
    t2 = bleed_t1 * (1.0 + (pr_c ** EXP - 1.0) / eta_c)
    p2 = bleed_p1 * pr_c
    return {"t2": t2, "p2": p2}


def heat_exchanger_exit(t_hot_in, effectiveness, t_sink):
    """Ram-air heat exchanger exit temperature, NTU-style effectiveness.

    T3 = t_hot_in - effectiveness * (t_hot_in - t_sink). Convention
    pinned: the effectiveness form, not a fixed temperature drop.

    Args:
        t_hot_in: hot-side inlet temperature (compressor discharge), K.
        effectiveness: exchanger effectiveness in (0, 1].
        t_sink: ram-air sink temperature, K.

    Returns:
        T3 in K.

    Raises:
        ValueError: on non-positive temperatures, effectiveness outside
            (0, 1] or t_hot_in <= t_sink (a cooling exchanger needs a
            hot inlet above the sink).
    """
    if t_hot_in <= 0:
        raise ValueError("t_hot_in must be positive")
    if t_sink <= 0:
        raise ValueError("t_sink must be positive")
    if not 0.0 < effectiveness <= 1.0:
        raise ValueError("effectiveness must be in (0, 1]")
    if t_hot_in <= t_sink:
        raise ValueError("t_hot_in must be above t_sink for cooling")
    return t_hot_in - effectiveness * (t_hot_in - t_sink)


def turbine_exit(p3, t3, pr_t, eta_t, p_cabin):
    """Cooling turbine exit state at cabin discharge pressure.

    pr_t = p3 / p4 is the design expansion ratio and p4 = p_cabin. The
    pack discharges at cabin pressure, so p3 / pr_t is validated against
    p_cabin at REL_TOL and a mismatch raises ValueError.
    T4 = T3 * (1 - eta_t * (1 - (p4 / p3)^EXP)).

    Args:
        p3: turbine inlet pressure (heat-exchanger exit), Pa.
        t3: turbine inlet temperature (heat-exchanger exit), K.
        pr_t: design expansion ratio (>= 1).
        eta_t: turbine isentropic efficiency in (0, 1).
        p_cabin: cabin design pressure, Pa.

    Returns:
        dict with keys "t4", "p4" and "pr_t" (K, Pa and ratio).

    Raises:
        ValueError: on non-positive pressures or temperatures, pr_t <=
            1.0, eta_t outside (0, 1) or a p3 / pr_t versus p_cabin
            mismatch beyond REL_TOL.
    """
    if p3 <= 0:
        raise ValueError("p3 must be positive")
    if t3 <= 0:
        raise ValueError("t3 must be positive")
    if p_cabin <= 0:
        raise ValueError("p_cabin must be positive")
    if pr_t <= 1.0:
        raise ValueError("pr_t must be above 1.0")
    if not 0.0 < eta_t < 1.0:
        raise ValueError("eta_t must be in (0, 1)")
    implied_p4 = p3 / pr_t
    if abs(implied_p4 - p_cabin) / p_cabin > REL_TOL:
        raise ValueError(
            "p3 / pr_t does not match p_cabin within REL_TOL"
        )
    p4 = p_cabin
    t4 = t3 * (1.0 - eta_t * (1.0 - (p4 / p3) ** EXP))
    return {"t4": t4, "p4": p4, "pr_t": pr_t}


def compressor_power(m_dot, t1, t2):
    """Compressor shaft power W_c = m_dot * CP_AIR * (T2 - T1)."""
    if m_dot <= 0:
        raise ValueError("m_dot must be positive")
    if t2 < t1:
        raise ValueError("t2 must be at least t1 for compression")
    return m_dot * CP_AIR * (t2 - t1)


def turbine_power(m_dot, t3, t4):
    """Turbine shaft power W_t = m_dot * CP_AIR * (T3 - T4)."""
    if m_dot <= 0:
        raise ValueError("m_dot must be positive")
    if t4 > t3:
        raise ValueError("t4 must be at most t3 for expansion")
    return m_dot * CP_AIR * (t3 - t4)


def shaft_balance(w_compressor, w_turbine):
    """Two-wheel ACM shaft balance verdict.

    Balanced is True when w_turbine + BALANCE_TOL_W >= w_compressor; the
    tolerance absorbs float noise, anything beyond 1 W is a real
    deficit. deficit_w = max(w_compressor - w_turbine, 0.0),
    power_ratio = w_turbine / w_compressor.

    Args:
        w_compressor: compressor shaft power demand, W.
        w_turbine: turbine shaft power delivered, W.

    Returns:
        dict with keys "balanced", "w_compressor", "w_turbine",
        "deficit_w" and "power_ratio".

    Raises:
        ValueError: on w_compressor <= 0 or w_turbine < 0.
    """
    if w_compressor <= 0:
        raise ValueError("w_compressor must be positive")
    if w_turbine < 0:
        raise ValueError("w_turbine must be non-negative")
    balanced = w_turbine + BALANCE_TOL_W >= w_compressor
    deficit_w = max(w_compressor - w_turbine, 0.0)
    power_ratio = w_turbine / w_compressor
    return {
        "balanced": balanced,
        "w_compressor": w_compressor,
        "w_turbine": w_turbine,
        "deficit_w": deficit_w,
        "power_ratio": power_ratio,
    }


def t3_required_for_balance(t1, t2, eta_t, p3, p_cabin):
    """Turbine inlet temperature that makes W_t = W_c.

    Closure is set by the turbine inlet temperature T3 after the heat
    exchanger: the compressor delta-T (T2 - T1) must equal the turbine
    delta-T eta_t * (1 - (p4 / p3)^EXP) * T3, so
    T3 = (T2 - T1) / (eta_t * (1 - (p_cabin / p3)^EXP)).

    Args:
        t1: compressor inlet temperature, K.
        t2: compressor exit temperature, K.
        eta_t: turbine isentropic efficiency in (0, 1).
        p3: turbine inlet pressure, Pa.
        p_cabin: cabin pressure, Pa.

    Returns:
        required T3 in K.

    Raises:
        ValueError: on t1 <= 0, t2 <= t1, p3 <= p_cabin or eta_t
            outside (0, 1).
    """
    if t1 <= 0:
        raise ValueError("t1 must be positive")
    if t2 <= t1:
        raise ValueError("t2 must be above t1")
    if p3 <= p_cabin:
        raise ValueError("p3 must be above p_cabin")
    if not 0.0 < eta_t < 1.0:
        raise ValueError("eta_t must be in (0, 1)")
    denom = eta_t * (1.0 - (p_cabin / p3) ** EXP)
    return (t2 - t1) / denom


def hx_effectiveness_for_balance(t2, t_sink, t3_required):
    """Heat exchanger effectiveness that lands T3 on the balance value.

    eff = (T2 - T3_req) / (T2 - t_sink).

    Args:
        t2: compressor exit temperature (exchanger hot inlet), K.
        t_sink: ram-air sink temperature, K.
        t3_required: turbine inlet temperature needed for closure, K.

    Returns:
        effectiveness in (0, 1].

    Raises:
        ValueError: on t2 <= t_sink or an infeasible required
            temperature for a cooling exchanger (t3_required <= t_sink
            or t3_required > t2): no heat exchanger can close the pack.
    """
    if t2 <= t_sink:
        raise ValueError("t2 must be above t_sink")
    if t3_required <= t_sink:
        raise ValueError(
            "t3_required is below the sink; no exchanger can close the pack"
        )
    if t3_required > t2:
        raise ValueError(
            "t3_required exceeds the exchanger hot inlet; no exchanger "
            "can close the pack"
        )
    return (t2 - t3_required) / (t2 - t_sink)


def cooling_capacity(m_dot, t_turbine_out, t_cabin_supply_target):
    """Delivered cooling power Q = m_dot * CP_AIR * (T_target - T4).

    Signed W: positive when the turbine exit arrives below the cabin
    design temperature (cooling capability), zero or negative when the
    supply is not cold enough.

    Raises:
        ValueError: on m_dot <= 0 or either temperature <= 0.
    """
    if m_dot <= 0:
        raise ValueError("m_dot must be positive")
    if t_turbine_out <= 0:
        raise ValueError("t_turbine_out must be positive")
    if t_cabin_supply_target <= 0:
        raise ValueError("t_cabin_supply_target must be positive")
    return m_dot * CP_AIR * (t_cabin_supply_target - t_turbine_out)


def required_bleed_flow(q_load, t4_effective, target_t):
    """Bleed flow that carries the load at the actual turbine exit.

    m_dot_req = q_load / (CP_AIR * (T_target - T4)).

    Raises:
        ValueError: on q_load <= 0 (a cooling demand must be positive)
            or t4_effective >= target_t (the air cannot cool; raising
            the flow never helps).
    """
    if q_load <= 0:
        raise ValueError("q_load must be positive")
    if t4_effective >= target_t:
        raise ValueError("turbine exit is not below the target; no cooling")
    return q_load / (CP_AIR * (target_t - t4_effective))


def _chain_case_a():
    """Nominal design-point chain (unprecooled bleed), for determinism."""
    c = compressor_exit(240000.0, 460.0, 3.0, 0.78)
    t3 = heat_exchanger_exit(c["t2"], 0.8, 320.0)
    t = turbine_exit(c["p2"], t3, c["p2"] / 101325.0, 0.85, 101325.0)
    wc = compressor_power(0.9, 460.0, c["t2"])
    wt = turbine_power(0.9, t3, t["t4"])
    return shaft_balance(wc, wt)


def _chain_case_b():
    """Precooled pack-inlet chain (balanced), for determinism."""
    c = compressor_exit(240000.0, 340.0, 3.0, 0.78)
    t3r = t3_required_for_balance(340.0, c["t2"], 0.85, c["p2"], 101325.0)
    eff = hx_effectiveness_for_balance(c["t2"], 320.0, t3r)
    t3 = heat_exchanger_exit(c["t2"], eff, 320.0)
    t = turbine_exit(c["p2"], t3, c["p2"] / 101325.0, 0.85, 101325.0)
    wc = compressor_power(0.9, 340.0, c["t2"])
    wt = turbine_power(0.9, t3, t["t4"])
    return shaft_balance(wc, wt), c, t3, t, eff, t3r
