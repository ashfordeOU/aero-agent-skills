"""Maximum-work pressure ratio selection for the air-standard gas turbine cycle.

Pure stdlib (math only), deterministic, closed form. The module supports
the SKILL.md workflow of the propulsion/gas-turbine-cycle/
brayton-optimum-pressure-ratio leaf:

1. Fix the cycle temperature limits T1, T3 and the component efficiencies
   eta_c, eta_t (temperature and efficiency validation).
2. Select the ideal max-work pressure ratio with
   ideal_optimum_pressure_ratio: x_opt = sqrt(tau), tau = T3/T1, giving
   r_opt = tau**(GAMMA/(2*(GAMMA-1))).
3. Select the lossy max-work pressure ratio with optimum_pressure_ratio:
   x_opt = sqrt(tau*eta_c*eta_t), returning r_opt = x_opt**(1/KAPPA); at
   eta_c = eta_t = 1.0 this degenerates exactly to the ideal closed form.
4. Cross-check the zero-work limiting ratio with
   zero_work_pressure_ratio: the factored work form
   w = cp*T1*(x-1)*(A-x)/(x*eta_c) has roots x = 1 and x = A =
   tau*eta_c*eta_t, so r_zero = r_opt**2 exactly.
5. Evaluate the net specific work at the optimum with
   net_specific_work and confirm the peak against log-symmetric
   neighbours of the ratio.
6. Verify the maximum by the derivative sign change of d(w)/dx across
   x_opt.
7. Issue the efficiency-versus-work verdict with design_verdict: the
   ideal efficiency rises monotonically with the ratio (no finite
   maximizer) while the lossy-cycle efficiency peaks at r_eta_max above
   r_opt and returns to zero at r_zero.
8. Close out with the deterministic contract test.

Air-standard gamma = 1.4 only; the temperature dependence of specific
heat is out of scope. Every selected max-work ratio is a pure ratio and
independent of CP; CP appears only to quote the specific work in J/kg.
"""

import math

GAMMA = 1.4  # air-standard specific heat ratio, fixed
KAPPA = (GAMMA - 1.0) / GAMMA  # 2/7, about 0.285714, the pressure exponent
CP = 1005.0  # J/(kg K), air specific heat at constant pressure
ETA_VERDICT_LOW_R = 1.01  # ideal-efficiency monotone arm, near-unity sample
ETA_VERDICT_HIGH_R = 1.0e6  # ideal-efficiency monotone arm, high sample


def _check_temperature_limits(t1, t3):
    """Raise ValueError unless 0 < T1 < T3 (Kelvin, cycle limits)."""
    if t1 <= 0.0:
        raise ValueError("t1 must be positive (K), got %r" % (t1,))
    if t3 <= t1:
        raise ValueError("t3 must exceed t1 (K), got t3=%r t1=%r" % (t3, t1))


def _check_eta(eta_c, eta_t):
    """Raise ValueError unless both efficiencies lie in (0, 1]."""
    for name, eta in (("eta_c", eta_c), ("eta_t", eta_t)):
        if not (0.0 < eta <= 1.0):
            raise ValueError(
                "%s must lie in (0, 1], got %r" % (name, eta))


def _check_ratio(r):
    """Raise ValueError unless the pressure ratio exceeds 1 (sibling
    convention: ratios of 1 or below are non-physical for the cycle)."""
    if r <= 1.0:
        raise ValueError("pressure ratio r must exceed 1, got %r" % (r,))


def ideal_optimum_pressure_ratio(t1, t3):
    """Max-work pressure ratio of the ideal (lossless) cycle.

    From d(w)/dx = 0 with w/(cp*T1) = tau*(1 - 1/x) - (x - 1): x_opt =
    sqrt(tau), so r_opt = tau**(GAMMA/(2*(GAMMA-1))). ValueError if
    t1 <= 0 or t3 <= t1.
    """
    _check_temperature_limits(t1, t3)
    tau = t3 / t1
    return tau ** (GAMMA / (2.0 * (GAMMA - 1.0)))


def optimum_pressure_ratio(t1, t3, eta_c, eta_t):
    """Max-work pressure ratio of the real cycle with component
    efficiencies eta_c (compressor) and eta_t (turbine).

    x_opt = sqrt(tau*eta_c*eta_t), returned as r_opt = x_opt**(1/KAPPA).
    Component losses pull x_opt below sqrt(tau), so r_opt falls below the
    ideal value. Degenerates exactly to ideal_optimum_pressure_ratio at
    eta_c = eta_t = 1.0. ValueError if t1 <= 0, t3 <= t1, or an
    efficiency outside (0, 1].
    """
    _check_temperature_limits(t1, t3)
    _check_eta(eta_c, eta_t)
    tau = t3 / t1
    x_opt = math.sqrt(tau * eta_c * eta_t)
    return x_opt ** (1.0 / KAPPA)


def zero_work_pressure_ratio(t1, t3, eta_c, eta_t):
    """Zero-net-work limiting pressure ratio of the real cycle.

    The factored work form w = cp*T1*(x - 1)*(A - x)/(x*eta_c) with
    A = tau*eta_c*eta_t has roots x = 1 (no compression) and x = A, so
    x_zero = tau*eta_c*eta_t = x_opt**2 and r_zero = r_opt**2 exactly
    (r = x**(1/KAPPA) is a power). Ratios above r_zero would consume
    more compressor work than the turbine delivers. ValueError set as
    optimum_pressure_ratio.
    """
    _check_temperature_limits(t1, t3)
    _check_eta(eta_c, eta_t)
    tau = t3 / t1
    x_zero = tau * eta_c * eta_t
    return x_zero ** (1.0 / KAPPA)


def net_specific_work(t1, t3, r, eta_c, eta_t, cp=CP):
    """Real-cycle net specific work in J/kg at pressure ratio r.

    w = cp*(eta_t*t3*(1 - 1/x) - t1*(x - 1)/eta_c) with x = r**KAPPA, the
    turbine work minus the compressor work. Pass eta_c = eta_t = 1.0 for
    the ideal-cycle value. ValueError if r <= 1, t1 <= 0, t3 <= t1, or an
    efficiency outside (0, 1].
    """
    _check_ratio(r)
    _check_temperature_limits(t1, t3)
    _check_eta(eta_c, eta_t)
    x = r ** KAPPA
    return cp * (eta_t * t3 * (1.0 - 1.0 / x) - t1 * (x - 1.0) / eta_c)


def ideal_cycle_efficiency(r):
    """Ideal-cycle thermal efficiency eta = 1 - 1/(r**KAPPA).

    Strictly increasing in the pressure ratio, so it has no finite
    maximizer; used only for the monotonicity arm of the verdict.
    ValueError if r <= 1.
    """
    _check_ratio(r)
    return 1.0 - 1.0 / (r ** KAPPA)


def cycle_efficiency(t1, t3, r, eta_c, eta_t, cp=CP):
    """Real-cycle thermal efficiency eta_th = w/q_in at pressure ratio r.

    q_in = cp*(t3 - t2) with t2 = t1*(1 + (x - 1)/eta_c) the compressor
    exit temperature; w is the net specific work of the same cycle. The
    efficiency equals zero at r = 1 and at the zero-work ratio r_zero,
    and peaks at the closed-form quadratic root r_eta_max strictly above
    r_opt. ValueError set as net_specific_work.
    """
    _check_ratio(r)
    _check_temperature_limits(t1, t3)
    _check_eta(eta_c, eta_t)
    x = r ** KAPPA
    t2 = t1 * (1.0 + (x - 1.0) / eta_c)
    q_in = cp * (t3 - t2)
    w = net_specific_work(t1, t3, r, eta_c, eta_t, cp)
    return w / q_in


def _real_efficiency_optimum_x(t1, t3, eta_c, eta_t):
    """Smaller closed-form quadratic root x_eta_max of d(eta_th)/dx = 0.

    With eta_th(x) = (x - 1)*(a - b*x)/(x*(c - b*x)), a = eta_t*T3,
    b = T1/eta_c, c = T3 - T1 + b, the stationary condition is
    b*(b - c + a)*x**2 - 2*a*b*x + a*c = 0; the smaller root sits between
    x_opt and x_zero, the larger root is unphysical (beyond the q_in = 0
    pole at x = c/b). Internal helper of design_verdict.
    """
    a = eta_t * t3
    b = t1 / eta_c
    c = t3 - t1 + b
    aq = b * (b - c + a)
    bq = -2.0 * a * b
    cq = a * c
    disc = bq * bq - 4.0 * aq * cq
    return (-bq - math.sqrt(disc)) / (2.0 * aq)


def design_verdict(t1, t3, eta_c, eta_t):
    """Efficiency-versus-work verdict comparing the max-efficiency and
    max-work pressure ratios, all closed form.

    Returns a dict with the ideal-cycle monotone arm (eta_ideal_low at a
    near-unity ratio, eta_ideal_at_r_opt_ideal at the ideal max-work
    ratio, eta_ideal_high_r at a very high ratio: no finite efficiency
    maximizer) and the lossy-cycle arm (eta_real_at_r_opt at the
    max-work ratio, the quadratic-root optimum x_eta_max_real and its
    ratio r_eta_max_real, eta_real_at_eta_max at that optimum, and
    eta_real_at_r_zero, zero at the zero-work ratio). ValueError set as
    optimum_pressure_ratio. Intended for the lossy cycle (eta < 1); at
    eta_c = eta_t = 1.0 the zero-work ratio coincides with the q_in = 0
    pole, so eta_real_at_r_zero is not defined there.
    """
    _check_temperature_limits(t1, t3)
    _check_eta(eta_c, eta_t)
    r_opt_ideal = ideal_optimum_pressure_ratio(t1, t3)
    eta_ideal_at_r_opt_ideal = ideal_cycle_efficiency(r_opt_ideal)
    eta_ideal_low = ideal_cycle_efficiency(ETA_VERDICT_LOW_R)
    eta_ideal_high_r = ideal_cycle_efficiency(ETA_VERDICT_HIGH_R)
    r_opt = optimum_pressure_ratio(t1, t3, eta_c, eta_t)
    eta_real_at_r_opt = cycle_efficiency(t1, t3, r_opt, eta_c, eta_t)
    x_eta_max_real = _real_efficiency_optimum_x(t1, t3, eta_c, eta_t)
    r_eta_max_real = x_eta_max_real ** (1.0 / KAPPA)
    eta_real_at_eta_max = cycle_efficiency(
        t1, t3, r_eta_max_real, eta_c, eta_t)
    r_zero = zero_work_pressure_ratio(t1, t3, eta_c, eta_t)
    eta_real_at_r_zero = cycle_efficiency(t1, t3, r_zero, eta_c, eta_t)
    return {
        "eta_ideal_at_r_opt_ideal": eta_ideal_at_r_opt_ideal,
        "eta_ideal_low": eta_ideal_low,
        "eta_ideal_high_r": eta_ideal_high_r,
        "eta_real_at_r_opt": eta_real_at_r_opt,
        "x_eta_max_real": x_eta_max_real,
        "r_eta_max_real": r_eta_max_real,
        "eta_real_at_eta_max": eta_real_at_eta_max,
        "eta_real_at_r_zero": eta_real_at_r_zero,
    }
