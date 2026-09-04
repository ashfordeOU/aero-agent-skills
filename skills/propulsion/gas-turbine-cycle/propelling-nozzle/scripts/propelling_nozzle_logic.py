"""Propelling nozzle sizing logic for an air-breathing gas turbine.

Pure stdlib, deterministic, offline. Implements the convergent nozzle
model of the propelling-nozzle leaf (propulsion/gas-turbine-cycle):

- regime decision: nozzle pressure ratio (NPR = P0 / Pa) against the
  critical ratio ((gamma+1)/2)^(gamma/(gamma-1)); choked when NPR is at
  or above the critical value,
- throat sizing from the design mass flow under the choked flow
  relation for a convergent nozzle,
- choked exit state at the throat (Mach 1): Te = T0 * 2/(gamma+1),
  Ve = sqrt(gamma R Te), Pe = P0 * (2/(gamma+1))^(gamma/(gamma-1)),
- gross thrust Fg = mdot * Ve + (Pe - Pa) * At,
- unchoked off-design exit state (subsonic Mach from the isentropic
  relation) and the actual mass flow the same throat passes.

All inputs SI: p in Pa, T in K, mdot in kg/s, area in m2, velocity in
m/s. Non-physical inputs raise ValueError.
"""

import math

# Module constants (air-breathing nozzle products convention, matching
# the afterburner-cycle anchor).
GAMMA = 1.33
R_GAS = 287.0
P_AMB_DEFAULT = 101325.0

# Choked flow factor (2/(gamma+1))^((gamma+1)/(2*(gamma-1))).
_CHOKED_FACTOR = (2.0 / (GAMMA + 1.0)) ** (
    (GAMMA + 1.0) / (2.0 * (GAMMA - 1.0))
)

# Critical ratio ((gamma+1)/2)^(gamma/(gamma-1)): minimum NPR for the
# convergent nozzle to choke.
CRITICAL_RATIO = ((GAMMA + 1.0) / 2.0) ** (GAMMA / (GAMMA - 1.0))


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %s" % (name, value))


def nozzle_regime(p0_pa, p_amb_pa):
    """Return the nozzle regime dict for total pressure p0_pa at ambient.

    dict keys: npr, critical_ratio, choked. Choked when npr >= the
    critical ratio. Raises ValueError for p0 <= 0, p_amb <= 0 or a
    nozzle pressure ratio npr <= 1 (no expansion possible).
    """
    _check_positive(p0_pa, "p0_pa")
    _check_positive(p_amb_pa, "p_amb_pa")
    npr = p0_pa / p_amb_pa
    if npr <= 1.0:
        raise ValueError(
            "nozzle pressure ratio must exceed 1 to expand, got %s" % npr
        )
    return {
        "npr": npr,
        "critical_ratio": CRITICAL_RATIO,
        "choked": npr >= CRITICAL_RATIO,
    }


def throat_area(mdot_kg_s, p0_pa, t0_k):
    """Return the choked throat area m2 passing mdot at total state (p0, t0).

    At = mdot * sqrt(T0) / (P0 * sqrt(gamma/R) * (2/(gamma+1))^((gamma+1)/
    (2*(gamma-1)))). Raises ValueError for mdot <= 0, p0 <= 0, t0 <= 0.
    """
    _check_positive(mdot_kg_s, "mdot_kg_s")
    _check_positive(p0_pa, "p0_pa")
    _check_positive(t0_k, "t0_k")
    return (
        mdot_kg_s
        * math.sqrt(t0_k)
        / (p0_pa * math.sqrt(GAMMA / R_GAS) * _CHOKED_FACTOR)
    )


def choked_exit_state(p0_pa, t0_k):
    """Return the choked exit state dict at the throat of a convergent nozzle.

    dict keys: t_exit_k, v_exit_m_s, p_exit_pa, mach. Exit is sonic
    (mach = 1.0). Raises ValueError for p0 <= 0 or t0 <= 0.
    """
    _check_positive(p0_pa, "p0_pa")
    _check_positive(t0_k, "t0_k")
    t_exit = t0_k * 2.0 / (GAMMA + 1.0)
    p_exit = p0_pa * (2.0 / (GAMMA + 1.0)) ** (GAMMA / (GAMMA - 1.0))
    v_exit = math.sqrt(GAMMA * R_GAS * t_exit)
    return {
        "t_exit_k": t_exit,
        "v_exit_m_s": v_exit,
        "p_exit_pa": p_exit,
        "mach": 1.0,
    }


def gross_thrust(mdot_kg_s, v_exit_m_s, p_exit_pa, p_amb_pa, area_m2):
    """Return gross thrust N = mdot*Ve + (Pe - Pa)*A.

    The pressure term (Pe - Pa)*A is the nozzle pressure thrust; it
    vanishes when the exit is fully expanded (Pe == Pa). Raises
    ValueError for mdot <= 0, v_exit < 0, area <= 0, p_exit <= 0 or
    p_amb <= 0.
    """
    _check_positive(mdot_kg_s, "mdot_kg_s")
    if v_exit_m_s < 0:
        raise ValueError("v_exit_m_s must not be negative, got %s" % v_exit_m_s)
    _check_positive(area_m2, "area_m2")
    _check_positive(p_exit_pa, "p_exit_pa")
    _check_positive(p_amb_pa, "p_amb_pa")
    return mdot_kg_s * v_exit_m_s + (p_exit_pa - p_amb_pa) * area_m2


def _unchoked_mach(p0_pa, p_amb_pa):
    """Return the subsonic exit Mach number from the isentropic relation.

    NPR = (1 + (gamma-1)/2 Me^2)^(gamma/(gamma-1)). Raises ValueError
    when the regime is choked (NPR >= critical ratio) or non-physical.
    """
    regime = nozzle_regime(p0_pa, p_amb_pa)
    if regime["choked"]:
        raise ValueError(
            "unchoked relation invalid at choked regime npr=%s" % regime["npr"]
        )
    mach = math.sqrt(
        2.0
        / (GAMMA - 1.0)
        * (regime["npr"] ** ((GAMMA - 1.0) / GAMMA) - 1.0)
    )
    return mach


def unchoked_exit_state(p0_pa, p_amb_pa, t0_k):
    """Return the unchoked off-design exit state dict.

    dict keys: mach, t_exit_k, v_exit_m_s with
    Te = T0/(1 + (gamma-1)/2 Me^2) and Ve = Me*sqrt(gamma R Te). Raises
    ValueError for non-physical inputs or a choked NPR.
    """
    _check_positive(t0_k, "t0_k")
    mach = _unchoked_mach(p0_pa, p_amb_pa)
    t_exit = t0_k / (1.0 + (GAMMA - 1.0) / 2.0 * mach * mach)
    v_exit = mach * math.sqrt(GAMMA * R_GAS * t_exit)
    return {"mach": mach, "t_exit_k": t_exit, "v_exit_m_s": v_exit}


def unchoked_mass_flow(area_m2, p0_pa, t0_k, p_amb_pa):
    """Return the actual kg/s an unchoked throat of area_m2 passes.

    mdot = P0*At/sqrt(T0) * sqrt(gamma/R) * Me * (1+(gamma-1)/2 Me^2)^
    (-(gamma+1)/(2(gamma-1))) with Me from the unchoked relation. Raises
    ValueError for area <= 0, non-physical totals or a choked regime.
    """
    _check_positive(area_m2, "area_m2")
    _check_positive(p0_pa, "p0_pa")
    _check_positive(t0_k, "t0_k")
    _check_positive(p_amb_pa, "p_amb_pa")
    mach = _unchoked_mach(p0_pa, p_amb_pa)
    ratio = 1.0 + (GAMMA - 1.0) / 2.0 * mach * mach
    return (
        p0_pa
        * area_m2
        / math.sqrt(t0_k)
        * math.sqrt(GAMMA / R_GAS)
        * mach
        * ratio ** (-(GAMMA + 1.0) / (2.0 * (GAMMA - 1.0)))
    )


def nozzle_sizing(mdot_design_kg_s, p0_design_pa, t0_k, p_amb_pa):
    """Size the convergent nozzle at a choked design point.

    Returns dict {regime, throat_area_m2, exit_state, gross_thrust_n,
    expansion_verdict} with expansion_verdict FULLY_EXPANDED when
    p_exit <= p_amb + 1e-6 else PRESSURE_TERM_ACTIVE. Raises ValueError
    for non-physical inputs or an unchoked design point (the choked
    sizing relation only applies there).
    """
    _check_positive(mdot_design_kg_s, "mdot_design_kg_s")
    _check_positive(p0_design_pa, "p0_design_pa")
    _check_positive(t0_k, "t0_k")
    _check_positive(p_amb_pa, "p_amb_pa")
    regime = nozzle_regime(p0_design_pa, p_amb_pa)
    if not regime["choked"]:
        raise ValueError(
            "nozzle sizing requires a choked design point, got npr=%s"
            % regime["npr"]
        )
    area = throat_area(mdot_design_kg_s, p0_design_pa, t0_k)
    exit_state = choked_exit_state(p0_design_pa, t0_k)
    thrust = gross_thrust(
        mdot_design_kg_s,
        exit_state["v_exit_m_s"],
        exit_state["p_exit_pa"],
        p_amb_pa,
        area,
    )
    verdict = (
        "FULLY_EXPANDED"
        if exit_state["p_exit_pa"] <= p_amb_pa + 1e-6
        else "PRESSURE_TERM_ACTIVE"
    )
    return {
        "regime": regime,
        "throat_area_m2": area,
        "exit_state": exit_state,
        "gross_thrust_n": thrust,
        "expansion_verdict": verdict,
    }


def off_design_nozzle(area_m2, p0_pa, t0_k, p_amb_pa):
    """Evaluate an unchoked off-design point on a fixed throat.

    Returns dict {regime, mach, v_exit_m_s, actual_mass_flow_kg_s}.
    Raises ValueError for area <= 0 or when the point is choked (use
    the choked relation instead).
    """
    _check_positive(area_m2, "area_m2")
    _check_positive(p0_pa, "p0_pa")
    _check_positive(t0_k, "t0_k")
    _check_positive(p_amb_pa, "p_amb_pa")
    regime = nozzle_regime(p0_pa, p_amb_pa)
    if regime["choked"]:
        raise ValueError(
            "off_design_nozzle requires an unchoked point, got npr=%s"
            % regime["npr"]
        )
    exit_state = unchoked_exit_state(p0_pa, p_amb_pa, t0_k)
    flow = unchoked_mass_flow(area_m2, p0_pa, t0_k, p_amb_pa)
    return {
        "regime": regime,
        "mach": exit_state["mach"],
        "v_exit_m_s": exit_state["v_exit_m_s"],
        "actual_mass_flow_kg_s": flow,
    }
