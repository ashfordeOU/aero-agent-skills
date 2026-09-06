#!/usr/bin/env python3
"""Rayleigh flow of a perfect gas in a constant-area frictionless duct.

Pure stdlib (math only), closed form throughout. Models steady heat
addition or rejection q in J/kg in a constant-area frictionless duct of
air at gamma 1.4 and R 287.0: the five Rayleigh-line station ratios
T/T*, p/p*, rho/rho*, T0/T0* and p0/p0* against the thermal-choking
sonic state (the star state of the same-mass-flow duct), the maximum
heat addition that thermally chokes the duct on either inlet branch,
the exit Mach number after a prescribed heat addition recovered from
the quadratic-in-M^2 total-temperature balance, the full downstream
static and stagnation state, and the second-law entropy rise of the
heat addition.

Module constants: GAMMA = 1.4, R = 287.0 and CP = GAMMA * R /
(GAMMA - 1) = 1004.5 J/(kg K), derived from gamma and R so the entropy
identity ds = cp*ln(T2/T1) - R*ln(p2/p1) and the heat balance
q = cp*(T0_2 - T0_1) close consistently. Non-physical inputs raise
ValueError. No RNG anywhere, so identical inputs return identical bits.

Worked anchors (air, T1 = 300 K, p1 = 101325 Pa, q = q_max/2 =
70628.90625 J/kg): subsonic inlet M1 = 0.5 exits at M2 = 0.625879453912
with ds = 214.987084722 J/(kg K) and p02/p01 = 0.957052789099;
supersonic inlet M1 = 2.0 exits at M2 = 1.54998945381 with
ds = 200.481131945 J/(kg K). The thermal-choking heat addition is
q_max = 141257.8125 J/kg for both inlets (the M to 1/M duality).
"""

import math

# Module constants: air as the perfect gas, spec values. CP is derived
# from GAMMA and R so the entropy and heat-balance identities close.
GAMMA = 1.4
R = 287.0
CP = GAMMA * R / (GAMMA - 1.0)  # 1004.5 J/(kg K)

_REL_TOL = 1e-12  # relative tolerance for branch-limit boundary checks


def _f(mach, gamma):
    """Return f = 1 + gamma*M^2, the common station-ratio denominator."""
    return 1.0 + gamma * mach * mach


def _t_over_tstar(mach, gamma):
    """Return the static temperature ratio T/T* at a Mach number."""
    f = _f(mach, gamma)
    return mach * mach * (1.0 + gamma) ** 2 / (f * f)


def _p_over_pstar(mach, gamma):
    """Return the static pressure ratio p/p* at a Mach number."""
    return (1.0 + gamma) / _f(mach, gamma)


def _rho_over_rhostar(mach, gamma):
    """Return the density ratio rho/rho* at a Mach number.

    Equals (p/p*)/(T/T*) exactly, so the three static ratios close.
    """
    f = _f(mach, gamma)
    return f / (mach * mach * (1.0 + gamma))


def _t0_over_t0star(mach, gamma):
    """Return the stagnation temperature ratio T0/T0* at a Mach number.

    T0/T0* = (T/T*) * (1 + (gamma-1)M^2/2) * 2/(gamma+1).
    """
    inner = (1.0 + 0.5 * (gamma - 1.0) * mach * mach) * 2.0 / (gamma + 1.0)
    return _t_over_tstar(mach, gamma) * inner


def _p0_over_p0star(mach, gamma):
    """Return the stagnation pressure ratio p0/p0* at a Mach number.

    p0/p0* = (p/p*) * ((1 + (gamma-1)M^2/2) * 2/(gamma+1)) ** (gamma/(gamma-1)).
    """
    inner = (1.0 + 0.5 * (gamma - 1.0) * mach * mach) * 2.0 / (gamma + 1.0)
    return _p_over_pstar(mach, gamma) * inner ** (gamma / (gamma - 1.0))


def rayleigh_ratios(mach, gamma=GAMMA):
    """Return the five Rayleigh-line station ratios at a Mach number.

    dict with keys t_over_tstar, p_over_pstar, rho_over_rhostar,
    t0_over_t0star and p0_over_p0star, all equal to 1.0 at mach 1.0
    (the thermal-choking sonic state of the same-mass-flow duct).
    Raises ValueError when mach is not positive.
    """
    if mach <= 0.0:
        raise ValueError("mach must be > 0.0 (no stationary or negative Mach number)")
    return {
        "t_over_tstar": _t_over_tstar(mach, gamma),
        "p_over_pstar": _p_over_pstar(mach, gamma),
        "rho_over_rhostar": _rho_over_rhostar(mach, gamma),
        "t0_over_t0star": _t0_over_t0star(mach, gamma),
        "p0_over_p0star": _p0_over_p0star(mach, gamma),
    }


def heat_addition_maximum(t_static, mach, gamma=GAMMA, cp=CP):
    """Return the heat addition q_max in J/kg that thermally chokes the duct.

    q_max = cp*T1*(1 - M^2)^2 / (2*(gamma+1)*M^2), the closed form of
    cp*(T0* - T0_1) valid on both branches. Zero at mach 1.0 and
    symmetric under mach to 1/mach at equal static temperature.
    Raises ValueError for non-positive t_static or mach.
    """
    if t_static <= 0.0:
        raise ValueError("t_static must be > 0.0 (kelvin)")
    if mach <= 0.0:
        raise ValueError("mach must be > 0.0 (no stationary or negative Mach number)")
    return cp * t_static * (1.0 - mach * mach) ** 2 / (2.0 * (gamma + 1.0) * mach * mach)


def _exit_mach_root(g2, gamma):
    """Solve g(M2) = g2, g = T0/T0*, on the branch the inlet dictates.

    The balance is a quadratic in x = M2^2,
    (gamma^2 - 1 - g2*gamma^2)*x^2 + (2*(1+gamma) - 2*g2*gamma)*x -
    g2 = 0. Returns (x_sub, x_sup), the subsonic and supersonic branch
    roots in x, from the numerically stable quadratic form; the
    caller picks by the inlet Mach number.
    """
    a = (gamma * gamma - 1.0) - g2 * gamma * gamma
    b = 2.0 * (1.0 + gamma) - 2.0 * g2 * gamma
    c = -g2
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        # Tiny negative noise only appears within 1e-9 of the double root.
        disc = 0.0
    sqrt_disc = math.sqrt(disc)
    # Stable form: roots of a*x^2 + b*x + c = 0 are q/a and c/q with
    # q = -0.5*(b + sign(b)*sqrt(disc)); b is always positive here.
    q = -0.5 * (b + sqrt_disc)
    x_sup = q / a if a != 0.0 else float("inf")
    x_sub = c / q
    return x_sub, x_sup


def exit_mach(t_static, mach, q, gamma=GAMMA, cp=CP):
    """Return the exit Mach number after heat addition q in J/kg.

    Positive q heats, negative q rejects. q at or above q_max*(1-1e-12)
    returns 1.0 (thermally choked); q strictly above q_max raises
    ValueError naming the thermal choking limit. Subsonic inlet: the
    exit lies in (0, 1], q down to just above -cp*T0_1 is accepted and
    q at or below -cp*T0_1 raises. Supersonic inlet: the exit lies in
    [1, inf), rejection that drops the balance g2 at or below the
    branch floor (gamma^2-1)/gamma^2 raises ValueError naming the
    branch limit. mach 1.0 with nonzero q raises (already choked).
    Raises ValueError for non-positive t_static or mach.
    """
    if t_static <= 0.0:
        raise ValueError("t_static must be > 0.0 (kelvin)")
    if mach <= 0.0:
        raise ValueError("mach must be > 0.0 (no stationary or negative Mach number)")
    if abs(mach - 1.0) <= _REL_TOL:
        if q == 0.0:
            return 1.0
        raise ValueError("inlet duct is already thermally choked at mach 1.0")
    q_max = heat_addition_maximum(t_static, mach, gamma, cp)
    if q > q_max:
        raise ValueError(
            "heat addition q exceeds the thermal choking limit q_max = %.12g J/kg" % q_max
        )
    if q >= q_max * (1.0 - _REL_TOL):
        return 1.0
    t0_1 = t_static * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    g1 = _t0_over_t0star(mach, gamma)
    g2 = g1 * (1.0 + q / (cp * t0_1))
    if mach < 1.0:
        if g2 <= _REL_TOL:
            raise ValueError(
                "heat rejection at or below -cp*T0_1 leaves no steady "
                "subsonic Rayleigh state (the exit Mach tends to 0)"
            )
        x_sub, _x_sup = _exit_mach_root(g2, gamma)
        return math.sqrt(x_sub)
    floor = (gamma * gamma - 1.0) / (gamma * gamma)
    if g2 <= floor * (1.0 + _REL_TOL):
        raise ValueError(
            "heat rejection past the supersonic branch limit g2 = "
            "%.12g leaves no steady Rayleigh state (the exit Mach "
            "tends to infinity)" % floor
        )
    _x_sub, x_sup = _exit_mach_root(g2, gamma)
    return math.sqrt(x_sup)


def entropy_rise(t1, p1, t2, p2, gamma=GAMMA, r=R, cp=CP):
    """Return the entropy rise ds in J/(kg K) between two gas states.

    ds = cp*ln(T2/T1) - r*ln(p2/p1) from the second law for a perfect
    gas. Raises ValueError when any argument is not positive.
    """
    if t1 <= 0.0 or p1 <= 0.0 or t2 <= 0.0 or p2 <= 0.0:
        raise ValueError("t1, p1, t2 and p2 must all be > 0.0 (SI units)")
    return cp * math.log(t2 / t1) - r * math.log(p2 / p1)


def rayleigh_curve_offset(mach, gamma=GAMMA):
    """Return the Rayleigh T-s curve offset (s - s*)/cp at a Mach number.

    (s - s*)/cp = ln(T/T*) - ((gamma-1)/gamma)*ln(p/p*), strictly
    negative away from mach 1.0 with maximum 0.0 at mach 1.0, the
    entropy maximum of the Rayleigh line. Raises ValueError when mach
    is not positive.
    """
    if mach <= 0.0:
        raise ValueError("mach must be > 0.0 (no stationary or negative Mach number)")
    ratios = rayleigh_ratios(mach, gamma)
    return math.log(ratios["t_over_tstar"]) - (
        (gamma - 1.0) / gamma
    ) * math.log(ratios["p_over_pstar"])


def heat_addition(t_static, p_static, mach, q, gamma=GAMMA, r=R, cp=CP):
    """Return the downstream station after heat addition q in J/kg.

    Full dict: m2, t2, p2, rho2, t02, p02 (absolute SI values), the
    ratios t2_over_t1, p2_over_p1, rho2_over_rho1, t02_over_t01 (=
    1 + q/(cp*T0_1)), p02_over_p01, ds (J/(kg K)), ds_over_cp, and
    choked (True when m2 is 1.0). The star state is shared by both
    stations of the same-mass-flow duct, so every state ratio is the
    ratio of the two station Rayleigh ratios, T0* stays fixed, and the
    entropy rise follows from the second law. Raises ValueError as
    exit_mach, and for non-positive p_static.
    """
    if p_static <= 0.0:
        raise ValueError("p_static must be > 0.0 (pascal)")
    m2 = exit_mach(t_static, mach, q, gamma, cp)
    t0_1 = t_static * (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    p0_1 = p_static * (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (
        gamma / (gamma - 1.0)
    )
    rho_1 = p_static / (r * t_static)
    r1 = rayleigh_ratios(mach, gamma)
    r2 = rayleigh_ratios(m2, gamma)
    t2_over_t1 = r2["t_over_tstar"] / r1["t_over_tstar"]
    p2_over_p1 = r2["p_over_pstar"] / r1["p_over_pstar"]
    rho2_over_rho1 = r2["rho_over_rhostar"] / r1["rho_over_rhostar"]
    t2 = t_static * t2_over_t1
    p2 = p_static * p2_over_p1
    rho2 = rho_1 * rho2_over_rho1
    t02 = t0_1 + q / cp
    t02_over_t01 = t02 / t0_1
    p02_over_p01 = r2["p0_over_p0star"] / r1["p0_over_p0star"]
    p02 = p0_1 * p02_over_p01
    ds = entropy_rise(t_static, p_static, t2, p2, gamma, r, cp)
    return {
        "m2": m2,
        "t2": t2,
        "p2": p2,
        "rho2": rho2,
        "t02": t02,
        "p02": p02,
        "t2_over_t1": t2_over_t1,
        "p2_over_p1": p2_over_p1,
        "rho2_over_rho1": rho2_over_rho1,
        "t02_over_t01": t02_over_t01,
        "p02_over_p01": p02_over_p01,
        "ds": ds,
        "ds_over_cp": ds / cp,
        "choked": m2 == 1.0,
    }
