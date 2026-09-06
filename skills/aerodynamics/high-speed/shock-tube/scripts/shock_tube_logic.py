#!/usr/bin/env python3
"""Classical one-dimensional shock-tube solver (pure stdlib, deterministic).

Given the driver-to-driven diaphragm pressure ratio p4/p1, the driver
sound-speed ratio a4/a1, and the two specific heat ratios gamma1 and
gamma4 (which may differ), recovers the incident-shock Mach number Ms
by deterministic bisection of the implicit shock-tube equation that
matches pressure across the contact surface, then returns the
post-shock state of the driven gas, the contact-surface velocity, the
driver expansion wave ratios and the full four-region state table.

The residual left minus right is strictly increasing in Ms over the
physical interval, so the root is unique. The expansion bracket stays
positive only while (Ms - 1/Ms) < C with C = (gamma1 + 1) a4/a1 /
(gamma4 - 1), which sets the Ms ceiling Ms_lim = (C + sqrt(C^2 + 4))/2.
Deterministic bisection runs on [1 + 1e-12, Ms_lim * (1 - 1e-12)] to
the module tolerance BISECT_TOL with at most MAX_ITER iterations, no
RNG, so identical inputs give identical bits. Region 4 and region 1
gases are initially at rest; the same specific gas constant is assumed
for both gases when building absolute states. Reflected-shock wall
interactions after the first transit are not modeled.

Reference framing: the relations are the standard normal-shock and
unsteady centered-expansion relations summarized in NACA-TR-824; only
names and summary equations are used here, never verbatim tables.
"""

import math

GAMMA_AIR = 1.4
R_AIR = 287.0
BISECT_TOL = 1e-12
MAX_ITER = 200


def normal_shock_ratios(shock_mach, gamma=GAMMA_AIR):
    """Ratios across the incident normal shock at shock_mach, unitless.

    Returns a dict with keys p2_p1, rho2_rho1, T2_T1 using the standard
    normal-shock relations. Raises ValueError if shock_mach <= 1
    (a shock requires a supersonic relative Mach number) or gamma <= 1.
    """
    if shock_mach <= 1.0:
        raise ValueError("shock_mach must be > 1 (supersonic relative to the shock)")
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 (specific heat ratio)")
    m2 = shock_mach * shock_mach
    p2_p1 = 1.0 + 2.0 * gamma * (m2 - 1.0) / (gamma + 1.0)
    rho2_rho1 = (gamma + 1.0) * m2 / (2.0 + (gamma - 1.0) * m2)
    t2_t1 = p2_p1 / rho2_rho1
    return {"p2_p1": p2_p1, "rho2_rho1": rho2_rho1, "T2_T1": t2_t1}


def induced_velocity(shock_mach, a1, gamma=GAMMA_AIR):
    """Lab-frame particle velocity u2 behind the moving shock, m/s.

    u2 = 2 a1 (shock_mach - 1 / shock_mach) / (gamma + 1) for a shock
    moving at shock_mach * a1 into gas at rest. Raises ValueError if
    shock_mach <= 1, a1 <= 0 or gamma <= 1.
    """
    if shock_mach <= 1.0:
        raise ValueError("shock_mach must be > 1 (supersonic relative to the shock)")
    if a1 <= 0.0:
        raise ValueError("a1 must be > 0 (upstream sound speed)")
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 (specific heat ratio)")
    return 2.0 * a1 * (shock_mach - 1.0 / shock_mach) / (gamma + 1.0)


def expansion_pressure_ratio(u_over_a4, gamma4):
    """Unsteady centered-expansion pressure ratio p3/p4, unitless.

    p3/p4 = (1 - (gamma4 - 1) u_over_a4 / 2) ** (2 gamma4 /
    (gamma4 - 1)). Raises ValueError if gamma4 <= 1 or the bracket
    1 - (gamma4 - 1) u_over_a4 / 2 sits at or below the full-expansion
    limit (bracket <= 1e-14, a float-noise guard around the exact zero
    at u_over_a4 = 2 / (gamma4 - 1); e.g. u_over_a4 = 5.0 at
    gamma4 = 1.4 raises).
    """
    if gamma4 <= 1.0:
        raise ValueError("gamma4 must be > 1 (driver specific heat ratio)")
    bracket = 1.0 - (gamma4 - 1.0) * u_over_a4 / 2.0
    if bracket <= 1e-14:
        raise ValueError("u_over_a4 beyond the full-expansion limit")
    return bracket ** (2.0 * gamma4 / (gamma4 - 1.0))


def shock_tube_residual(shock_mach, p4_p1, a4_a1, gamma1=GAMMA_AIR,
                        gamma4=GAMMA_AIR):
    """Implicit shock-tube residual, p2/p1 minus p3/p4 times p4/p1.

    The left side is the normal-shock pressure ratio at shock_mach; the
    right side is the driver overpressure times the unsteady expansion
    ratio evaluated at the contact velocity u2/a4 =
    2 (shock_mach - 1 / shock_mach) / ((gamma1 + 1) a4_a1). Zero at the
    physical root. ValueErrors as in the component relations.
    """
    if a4_a1 <= 0.0:
        raise ValueError("a4_a1 must be > 0 (driver-to-driven sound speed ratio)")
    left = normal_shock_ratios(shock_mach, gamma1)["p2_p1"]
    u2_over_a4 = 2.0 * (shock_mach - 1.0 / shock_mach) / ((gamma1 + 1.0) * a4_a1)
    right = p4_p1 * expansion_pressure_ratio(u2_over_a4, gamma4)
    return left - right


def incident_shock_mach(p4_p1, a4_a1=1.0, gamma1=GAMMA_AIR, gamma4=GAMMA_AIR):
    """Incident-shock Mach number Ms from the diaphragm pressure state.

    Deterministic bisection of shock_tube_residual on the bracket
    [1 + 1e-12, Ms_lim * (1 - 1e-12)] to BISECT_TOL, at most MAX_ITER
    iterations, returning the final bracket midpoint. Raises ValueError
    if p4_p1 <= 1 (a driver overpressure is required), a4_a1 <= 0,
    gamma1 <= 1, gamma4 <= 1, or no sign change appears on the bracket.
    """
    if p4_p1 <= 1.0:
        raise ValueError("p4_p1 must be > 1 (a driver overpressure is required)")
    if a4_a1 <= 0.0:
        raise ValueError("a4_a1 must be > 0 (driver-to-driven sound speed ratio)")
    if gamma1 <= 1.0:
        raise ValueError("gamma1 must be > 1 (driven gas specific heat ratio)")
    if gamma4 <= 1.0:
        raise ValueError("gamma4 must be > 1 (driver specific heat ratio)")
    c_lim = (gamma1 + 1.0) * a4_a1 / (gamma4 - 1.0)
    ms_lim = (c_lim + math.sqrt(c_lim * c_lim + 4.0)) / 2.0
    lo = 1.0 + 1e-12
    hi = ms_lim * (1.0 - 1e-12)
    if shock_tube_residual(lo, p4_p1, a4_a1, gamma1, gamma4) >= 0.0:
        raise ValueError("no sign change on the physical bracket (root below it)")
    if shock_tube_residual(hi, p4_p1, a4_a1, gamma1, gamma4) <= 0.0:
        raise ValueError("no sign change on the physical bracket (root above it)")
    for _ in range(MAX_ITER):
        mid = 0.5 * (lo + hi)
        if shock_tube_residual(mid, p4_p1, a4_a1, gamma1, gamma4) < 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= BISECT_TOL:
            break
    return 0.5 * (lo + hi)


def shock_tube_state(p4_p1, a4_a1=1.0, gamma1=GAMMA_AIR, gamma4=GAMMA_AIR,
                     p1=101325.0, t1=288.15, r_gas=R_AIR):
    """Full four-region state table of the shock-tube run.

    Returns a dict with keys exactly: Ms, p2_p1, rho2_rho1, T2_T1, u2,
    p2, T2, rho2, a2, M2_lab, a1, rho1, p1, p3_p4, T3_T4, rho3_rho4,
    p3, T3, rho3, a3, M3_lab, u3, p4, T4, rho4, a4, fan_head_speed,
    fan_tail_speed, residual. Region-2 absolute state comes from the
    shock ratios and induced_velocity; driver-side absolute states
    assume the same specific gas constant for both gases, so
    T4 = t1 a4_a1^2 gamma1 / gamma4. Region 3 sits between the contact
    surface and the fan tail with u3 = u2 and its pressure p3 computed
    from the expansion side p3_p4 * p4 (equal to p2 at the root to the
    bisection tolerance). fan_head_speed = a4 (leftward into the
    quiescent driver gas), fan_tail_speed = u3 - a3 (lab frame,
    right-positive). Raises ValueError if p1 <= 0, t1 <= 0, r_gas <= 0,
    plus all component ValueErrors.
    """
    if p1 <= 0.0:
        raise ValueError("p1 must be > 0 (driven gas static pressure)")
    if t1 <= 0.0:
        raise ValueError("t1 must be > 0 (driven gas static temperature)")
    if r_gas <= 0.0:
        raise ValueError("r_gas must be > 0 (specific gas constant)")
    ms = incident_shock_mach(p4_p1, a4_a1, gamma1, gamma4)
    ratios = normal_shock_ratios(ms, gamma1)
    a1 = math.sqrt(gamma1 * r_gas * t1)
    rho1 = p1 / (r_gas * t1)
    u2 = induced_velocity(ms, a1, gamma1)
    p2 = ratios["p2_p1"] * p1
    t2 = ratios["T2_T1"] * t1
    rho2 = ratios["rho2_rho1"] * rho1
    a2 = math.sqrt(gamma1 * r_gas * t2)
    m2_lab = u2 / a2
    t4 = t1 * a4_a1 * a4_a1 * gamma1 / gamma4
    a4 = math.sqrt(gamma4 * r_gas * t4)
    p4 = p4_p1 * p1
    rho4 = p4 / (r_gas * t4)
    u3 = u2
    p3_p4 = expansion_pressure_ratio(u3 / a4, gamma4)
    t3_t4 = (1.0 - (gamma4 - 1.0) * u3 / (2.0 * a4)) ** 2
    rho3_rho4 = p3_p4 / t3_t4
    p3 = p3_p4 * p4
    t3 = t3_t4 * t4
    rho3 = rho3_rho4 * rho4
    a3 = math.sqrt(gamma4 * r_gas * t3)
    m3_lab = u3 / a3
    fan_head_speed = a4
    fan_tail_speed = u3 - a3
    residual = shock_tube_residual(ms, p4_p1, a4_a1, gamma1, gamma4)
    return {
        "Ms": ms,
        "p2_p1": ratios["p2_p1"],
        "rho2_rho1": ratios["rho2_rho1"],
        "T2_T1": ratios["T2_T1"],
        "u2": u2,
        "p2": p2,
        "T2": t2,
        "rho2": rho2,
        "a2": a2,
        "M2_lab": m2_lab,
        "a1": a1,
        "rho1": rho1,
        "p1": p1,
        "p3_p4": p3_p4,
        "T3_T4": t3_t4,
        "rho3_rho4": rho3_rho4,
        "p3": p3,
        "T3": t3,
        "rho3": rho3,
        "a3": a3,
        "M3_lab": m3_lab,
        "u3": u3,
        "p4": p4,
        "T4": t4,
        "rho4": rho4,
        "a4": a4,
        "fan_head_speed": fan_head_speed,
        "fan_tail_speed": fan_tail_speed,
        "residual": residual,
    }
