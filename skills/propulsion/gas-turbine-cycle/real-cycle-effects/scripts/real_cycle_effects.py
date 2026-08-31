"""Real-cycle effects for the gas turbine (Brayton) cycle.

Component isentropic efficiencies, total-pressure losses, the real
thermal efficiency of the non-ideal cycle, and the actual specific
fuel consumption. Pure stdlib (no numpy/pandas). SI units throughout:

- temperatures in kelvin (K)
- pressure ratio, gamma, efficiencies, loss fractions dimensionless
- lower heating value LHV in J/kg
- SFC in kg/(kN*s), thrust SFC in kg/(kN*s)
"""


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def compressor_exit_temperature(t1, pressure_ratio, gamma, eta_c):
    """Actual compressor exit temperature in kelvin.

    Ideal (isentropic) exit: T2s = T1 * PR**((gamma-1)/gamma).
    Actual with isentropic efficiency eta_c:
        T2 = T1 * (1 + (PR**((gamma-1)/gamma) - 1)/eta_c)
    eta_c = 1 recovers the ideal cycle. 0 < eta_c <= 1 required;
    eta_c > 1 is rejected as non-physical (exit colder than ideal).
    """
    _require(t1 > 0.0, "t1 must be positive (kelvin)")
    _require(pressure_ratio > 1.0, "pressure_ratio must be > 1")
    _require(gamma > 1.0, "gamma must be > 1")
    _require(0.0 < eta_c <= 1.0, "eta_c must be in (0, 1]")
    t2s = t1 * pressure_ratio ** ((gamma - 1.0) / gamma)
    return t1 + (t2s - t1) / eta_c


def turbine_exit_temperature(t3, pressure_ratio, gamma, eta_t):
    """Actual turbine exit temperature in kelvin.

    Ideal (isentropic) exit: T4s = T3 / PR**((gamma-1)/gamma).
    Actual with isentropic efficiency eta_t:
        T4 = T3 - eta_t * (T3 - T4s)
    eta_t = 1 recovers the ideal cycle. 0 < eta_t <= 1 required.
    """
    _require(t3 > 0.0, "t3 must be positive (kelvin)")
    _require(pressure_ratio > 1.0, "pressure_ratio must be > 1")
    _require(gamma > 1.0, "gamma must be > 1")
    _require(0.0 < eta_t <= 1.0, "eta_t must be in (0, 1]")
    t4s = t3 / pressure_ratio ** ((gamma - 1.0) / gamma)
    return t3 - eta_t * (t3 - t4s)


def real_thermal_efficiency(t1, t2, t3, t4):
    """Real cycle thermal efficiency (cp cancels), dimensionless.

    eta_th = (T3 - T4 - T2 + T1)/(T3 - T2)  [net work / heat added]

    T2 and T4 are the ACTUAL (lossy) station temperatures, not the
    isentropic ones. Requires a physically ordered cycle:
    T1 < T2 < T3 and T1 < T4 < T3.
    """
    _require(t1 > 0.0, "t1 must be positive (kelvin)")
    _require(t2 > t1, "t2 must exceed t1 (compression)")
    _require(t3 > t2, "t3 must exceed t2 (heat addition)")
    _require(t4 > t1, "t4 must exceed t1 (expansion to ambient)")
    _require(t4 < t3, "t4 must be below t3 (turbine expansion)")
    return (t3 - t4 - t2 + t1) / (t3 - t2)


def sfc_from_efficiency(thermal_efficiency, lhv_j_per_kg):
    """Cycle-basis specific fuel consumption in kg/(kN*s).

    SFC = 3600/(eta_th * LHV), LHV in J/kg. This is the hourly-scaled
    form of the classic SFC = 3600/(eta * LHV) formula (fuel flow per
    unit net work 1/(eta*LHV) kg/J, scaled by 3600 s/h) expressed on
    the kilonewton-second thrust basis at the reference effective
    velocity V_ref = 3.6 m/s. For a real engine scale linearly with
    the effective jet velocity: see sfc_thrust(eta, LHV, V_eff).
    """
    _require(0.0 < thermal_efficiency <= 1.0,
             "thermal_efficiency must be in (0, 1]")
    _require(lhv_j_per_kg > 0.0, "lhv_j_per_kg must be positive (J/kg)")
    return 3600.0 / (thermal_efficiency * lhv_j_per_kg)


def sfc_thrust(thermal_efficiency, lhv_j_per_kg, v_eff_m_per_s):
    """Thrust-specific fuel consumption in kg/(kN*s).

    SFC_T = 1000 * V_eff / (eta_th * LHV), with the effective jet
    velocity V_eff in m/s (typical 500 to 700 m/s for a turbojet at
    cruise). Derived from mf/T = V_eff/(eta_th*LHV) in kg/(N*s),
    converted to the kilonewton basis (divide by 1000).
    """
    _require(0.0 < thermal_efficiency <= 1.0,
             "thermal_efficiency must be in (0, 1]")
    _require(lhv_j_per_kg > 0.0, "lhv_j_per_kg must be positive (J/kg)")
    _require(v_eff_m_per_s > 0.0, "v_eff_m_per_s must be positive (m/s)")
    return 1000.0 * v_eff_m_per_s / (thermal_efficiency * lhv_j_per_kg)


def pressure_loss_penalty(pressure_ratio, combustor_loss_frac):
    """Effective pressure ratio after the combustor total-pressure loss.

    PR_eff = PR * (1 - combustor_loss_frac). The fractional loss is
    dimensionless (typical 0.02 to 0.06); it lowers the pressure ratio
    seen by the turbine and therefore raises T4s and T4.
    """
    _require(pressure_ratio > 1.0, "pressure_ratio must be > 1")
    _require(0.0 <= combustor_loss_frac < 1.0,
             "combustor_loss_frac must be in [0, 1)")
    return pressure_ratio * (1.0 - combustor_loss_frac)


def cycle_efficiency_with_losses(t1, t3, pressure_ratio, gamma, eta_c,
                                 eta_t, combustor_loss_frac=0.0):
    """Real cycle efficiency including the combustor total-pressure loss.

    The compressor sees the full pressure ratio; the turbine sees the
    reduced PR_eff = PR * (1 - combustor_loss_frac).
    """
    pr_eff = pressure_loss_penalty(pressure_ratio, combustor_loss_frac)
    t2 = compressor_exit_temperature(t1, pressure_ratio, gamma, eta_c)
    t4 = turbine_exit_temperature(t3, pr_eff, gamma, eta_t)
    return real_thermal_efficiency(t1, t2, t3, t4)


def efficiency_sensitivity(t1=288.15, t3=1500.0, pressure_ratio=20.0,
                           gamma=1.4, eta_c=0.85, eta_t=0.88,
                           combustor_loss_frac=0.0, step=1e-3):
    """Numeric sensitivities d(eta_th)/d(eta_c) and d(eta_th)/d(eta_t).

    Central differences around the reference point. Returns a dict with
    the derivative of the real thermal efficiency with respect to the
    compressor efficiency, the turbine efficiency, and the combustor
    loss fraction, plus the base efficiency. Both component-efficiency
    derivatives are positive (losses always hurt); the loss derivative
    is negative.
    """
    _require(0.0 < step < 0.1, "step must be small and positive")

    def eta_at(ec, et, loss):
        return cycle_efficiency_with_losses(
            t1, t3, pressure_ratio, gamma, ec, et, loss)

    base = eta_at(eta_c, eta_t, combustor_loss_frac)
    d_eta_c = (eta_at(eta_c + step, eta_t, combustor_loss_frac)
               - eta_at(eta_c - step, eta_t, combustor_loss_frac)) / (2.0 * step)
    d_eta_t = (eta_at(eta_c, eta_t + step, combustor_loss_frac)
               - eta_at(eta_c, eta_t - step, combustor_loss_frac)) / (2.0 * step)
    d_eta_loss = (eta_at(eta_c, eta_t, combustor_loss_frac + step)
                  - eta_at(eta_c, eta_t, combustor_loss_frac)) / step
    return {
        "eta_base": base,
        "d_eta_d_eta_c": d_eta_c,
        "d_eta_d_eta_t": d_eta_t,
        "d_eta_d_loss": d_eta_loss,
    }
