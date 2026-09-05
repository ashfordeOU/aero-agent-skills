#!/usr/bin/env python3
"""Intercooled gas turbine (Brayton) cycle logic, air-standard analysis.

Common-knowledge thermodynamics (paraphrase; standards-map.yaml far-33 is
the aircraft engine certification context and does not prescribe cycle
analysis methods). An intercooled cycle splits the total pressure ratio
pi_total into two compression stages, pi_1 * pi_2 = pi_total, with an
intercooler between them that cools the stage-1 discharge toward the
ambient temperature with effectiveness eps_ic. The equal-work pressure
split pi_1 = pi_2 = sqrt(pi_total) is the documented optimum for a fixed
total ratio when intercooling returns the air to the ambient temperature.

Conventions: SI units, temperatures in kelvin, works as specific work in
J/kg (the worked example tables divide by 1000 to quote kJ/kg), pressure
ratios and efficiencies dimensionless, effectiveness in [0, 1]. Perfect
gas with constant module constants GAMMA = 1.4 and CP = 1005.0 J/(kg K).

Model notes:
- stage_exit_temperature returns the real (actual) discharge temperature
  with the stage isentropic efficiency applied once.
- Stage work is the actual enthalpy rise CP * (T_exit - T_in), which
  equals CP * T_in * (pi**((GAMMA-1)/GAMMA) - 1) / eta_c, the spec's
  isentropic-work-over-efficiency closed form. No second efficiency
  division is applied.
- With eps_ic = 0 the two-stage chain recomputes the stage-2 efficiency
  on the real (hotter) stage-1 discharge, so its total work exceeds the
  single-stage value by a small margin that vanishes as eta_c -> 1; the
  contract test treats the two as approximately equal per the spec.
"""

GAMMA = 1.4
CP = 1005.0

_PI_MIN = 1.0
_EPS_MIN = 0.0
_EPS_MAX = 1.0


def _validate_temperature(t_k, name="temperature"):
    """Inlet temperatures must be positive (kelvin)."""
    if t_k <= 0:
        raise ValueError("%s must be > 0 K, got %r" % (name, t_k))


def _validate_pressure_ratio(pi, name="pressure ratio"):
    """Pressure ratios must exceed 1 (dimensionless)."""
    if pi <= _PI_MIN:
        raise ValueError("%s must be > 1, got %r" % (name, pi))


def _validate_efficiency(eta, name="efficiency"):
    """Efficiencies must lie in the open interval (0, 1]."""
    if eta <= 0.0 or eta > 1.0:
        raise ValueError("%s must be in (0, 1], got %r" % (name, eta))


def _validate_effectiveness(eps):
    """Intercooler effectiveness must lie in [0, 1]."""
    if eps < _EPS_MIN or eps > _EPS_MAX:
        raise ValueError(
            "intercooler effectiveness must be in [0, 1], got %r" % (eps,)
        )


def stage_exit_temperature(t_in, pi_stage, eta_c):
    """Real compressor discharge temperature after one stage (kelvin).

    T_exit = T_in * (1 + (pi_stage**((GAMMA-1)/GAMMA) - 1) / eta_c).
    t_in in kelvin (> 0), pi_stage dimensionless (> 1), eta_c in (0, 1].
    """
    _validate_temperature(t_in, "stage inlet temperature")
    _validate_pressure_ratio(pi_stage, "stage pressure ratio")
    _validate_efficiency(eta_c, "stage isentropic efficiency")
    exponent = (GAMMA - 1.0) / GAMMA
    return t_in * (1.0 + (pi_stage ** exponent - 1.0) / eta_c)


def intercooler_exit_temperature(t_in_hot, t_coolant, eps_ic):
    """Intercooler discharge temperature from its effectiveness (kelvin).

    T_exit = T_in_hot - eps_ic * (T_in_hot - T_coolant). eps_ic = 0
    returns the hot inlet unchanged; eps_ic = 1 returns the coolant
    temperature. eps_ic in [0, 1]; t_coolant must be below t_in_hot for
    cooling to occur.
    """
    _validate_temperature(t_in_hot, "intercooler hot inlet temperature")
    _validate_temperature(t_coolant, "coolant temperature")
    _validate_effectiveness(eps_ic)
    if t_coolant >= t_in_hot:
        raise ValueError(
            "coolant temperature must be below the hot inlet for cooling, "
            "got hot=%r coolant=%r" % (t_in_hot, t_coolant)
        )
    return t_in_hot - eps_ic * (t_in_hot - t_coolant)


def optimum_intercooler_pressure_ratio(pi_total):
    """Optimum intercooler pressure ratio for a fixed total ratio.

    Equal stage split sqrt(pi_total) minimizes the total compressor work
    when the intercooler returns the air to the ambient temperature.
    pi_total dimensionless (> 1).
    """
    _validate_pressure_ratio(pi_total, "total pressure ratio")
    return pi_total ** 0.5


def compressor_work_total(t_1, pi_total, eps_ic, eta_c):
    """Two-stage compressor with intercooler: stage states and works.

    Returns a dict with keys pi_1, pi_2, T_2a, T_ic_exit, T_2b, w_c1,
    w_c2, w_c_total. pi_1 = pi_2 = sqrt(pi_total); T_2a is the stage-1
    discharge, T_ic_exit the intercooler discharge, T_2b the stage-2
    discharge. Works in J/kg: w_c1 = CP*(T_2a - T_1),
    w_c2 = CP*(T_2b - T_ic_exit).
    """
    _validate_temperature(t_1, "inlet temperature")
    _validate_pressure_ratio(pi_total, "total pressure ratio")
    _validate_effectiveness(eps_ic)
    _validate_efficiency(eta_c, "compressor isentropic efficiency")
    pi_1 = pi_2 = optimum_intercooler_pressure_ratio(pi_total)
    t_2a = stage_exit_temperature(t_1, pi_1, eta_c)
    t_ic_exit = intercooler_exit_temperature(t_2a, t_1, eps_ic)
    t_2b = stage_exit_temperature(t_ic_exit, pi_2, eta_c)
    w_c1 = CP * (t_2a - t_1)
    w_c2 = CP * (t_2b - t_ic_exit)
    return {
        "pi_1": pi_1,
        "pi_2": pi_2,
        "T_2a": t_2a,
        "T_ic_exit": t_ic_exit,
        "T_2b": t_2b,
        "w_c1": w_c1,
        "w_c2": w_c2,
        "w_c_total": w_c1 + w_c2,
    }


def turbine_work(t_3, pi_total, eta_t):
    """Turbine specific work through the full total ratio (J/kg).

    w_t = CP * eta_t * T_3 * (1 - pi_total**(-(GAMMA-1)/GAMMA)).
    t_3 in kelvin (> 0), pi_total dimensionless (> 1), eta_t in (0, 1].
    """
    _validate_temperature(t_3, "turbine inlet temperature")
    _validate_pressure_ratio(pi_total, "total pressure ratio")
    _validate_efficiency(eta_t, "turbine isentropic efficiency")
    exponent = (GAMMA - 1.0) / GAMMA
    return CP * eta_t * t_3 * (1.0 - pi_total ** (-exponent))


def simple_cycle(t_1, t_3, pi_total, eta_c, eta_t):
    """Simple (single compression stage, no intercooler) cycle baseline.

    Returns a dict with keys w_c, w_t, w_net, q_in, eta_th. Works in
    J/kg, eta_th dimensionless. Used only as the comparison baseline.
    """
    _validate_temperature(t_1, "inlet temperature")
    if t_3 <= t_1:
        raise ValueError(
            "turbine inlet temperature must exceed the inlet temperature, "
            "got t_1=%r t_3=%r" % (t_1, t_3)
        )
    _validate_pressure_ratio(pi_total, "total pressure ratio")
    _validate_efficiency(eta_c, "compressor isentropic efficiency")
    _validate_efficiency(eta_t, "turbine isentropic efficiency")
    t_2 = stage_exit_temperature(t_1, pi_total, eta_c)
    w_c = CP * (t_2 - t_1)
    w_t = turbine_work(t_3, pi_total, eta_t)
    q_in = CP * (t_3 - t_2)
    w_net = w_t - w_c
    return {
        "w_c": w_c,
        "w_t": w_t,
        "w_net": w_net,
        "q_in": q_in,
        "eta_th": w_net / q_in,
    }


def intercooled_cycle(t_1, t_3, pi_total, eps_ic, eta_c, eta_t):
    """Full intercooled cycle state and performance summary.

    Returns a dict with keys pi_1, pi_2, T_2a, T_ic_exit, T_2b, w_c1,
    w_c2, w_c_total, w_t, w_net, q_in, eta_th. q_in = CP*(T_3 - T_2b);
    eta_th = w_net / q_in. Works in J/kg, eta_th dimensionless.
    """
    _validate_temperature(t_1, "inlet temperature")
    if t_3 <= t_1:
        raise ValueError(
            "turbine inlet temperature must exceed the inlet temperature, "
            "got t_1=%r t_3=%r" % (t_1, t_3)
        )
    _validate_pressure_ratio(pi_total, "total pressure ratio")
    _validate_effectiveness(eps_ic)
    _validate_efficiency(eta_c, "compressor isentropic efficiency")
    _validate_efficiency(eta_t, "turbine isentropic efficiency")
    comp = compressor_work_total(t_1, pi_total, eps_ic, eta_c)
    w_t = turbine_work(t_3, pi_total, eta_t)
    q_in = CP * (t_3 - comp["T_2b"])
    w_net = w_t - comp["w_c_total"]
    result = dict(comp)
    result["w_t"] = w_t
    result["w_net"] = w_net
    result["q_in"] = q_in
    result["eta_th"] = w_net / q_in
    return result


def cycle_comparison(intercooled, simple):
    """Intercooled over simple cycle comparison summary.

    work_gain_pct = (w_net_i - w_net_s) / w_net_s * 100 (percent);
    eta_delta_pp = (eta_th_i - eta_th_s) * 100 (percentage points).
    """
    work_gain_pct = (
        (intercooled["w_net"] - simple["w_net"]) / simple["w_net"] * 100.0
    )
    eta_delta_pp = (intercooled["eta_th"] - simple["eta_th"]) * 100.0
    return {"work_gain_pct": work_gain_pct, "eta_delta_pp": eta_delta_pp}
