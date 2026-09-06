"""Fanno-flow duct solver: steady adiabatic constant-area duct with wall friction.

Pure-stdlib module for the Fanno problem of a perfect gas: the Fanno-line
integral fL*/D (the friction parameter that chokes the duct from a Mach
number), the friction-duct choking length L*, the downstream Mach number
recovered by deterministic bisection on the inlet branch, the friction
factor required to choke a duct of given length and diameter, and the
total-pressure and static ratios to the sonic reference state of the same
duct. Duct flow here is adiabatic (no heat addition, T0 constant) and
friction is the Fanning factor f = tau_w / (rho u^2 / 2); callers with
Darcy-factor tables must divide f_D by 4 first. D is the hydraulic
diameter. Deterministic, no RNG, math only.
"""

import math

GAMMA = 1.4  # air default; gamma is a parameter of every function
BISECT_TOL = 1e-12  # absolute Mach tolerance of the deterministic bisection
MAX_ITER = 200  # iteration cap, no RNG: identical inputs give identical bits


def _check_gamma(gamma):
    """Reject non-physical specific-heat ratios (gamma must exceed 1)."""
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 for a perfect gas")


def _check_mach(mach):
    """Reject non-physical Mach numbers (must be strictly positive)."""
    if mach <= 0.0:
        raise ValueError("mach must be > 0")


def fanno_function(mach, gamma=GAMMA):
    """Fanno-line integral phi(M) = fL*/D by the closed form.

    phi = (1 - M^2)/(gamma M^2) + ((gamma + 1)/(2 gamma))
          ln((gamma + 1) M^2 / (2 + (gamma - 1) M^2))

    phi has its only zero and minimum at M = 1, falls from infinity at
    M -> 0 to 0 at M = 1, then rises to the plateau
    ((gamma + 1)/(2 gamma)) ln((gamma + 1)/(gamma - 1)) - 1/gamma.
    """
    _check_mach(mach)
    _check_gamma(gamma)
    m2 = mach * mach
    term1 = (1.0 - m2) / (gamma * m2)
    arg = (gamma + 1.0) * m2 / (2.0 + (gamma - 1.0) * m2)
    term2 = ((gamma + 1.0) / (2.0 * gamma)) * math.log(arg)
    return term1 + term2


def choke_length(mach, friction_factor, diameter, gamma=GAMMA):
    """Choking length L* = D/f * phi(M), the duct run to exactly M = 1.

    Returns 0.0 at mach = 1 (the duct is already choked at the inlet).
    """
    _check_mach(mach)
    _check_gamma(gamma)
    if friction_factor <= 0.0:
        raise ValueError("friction_factor must be > 0 (Fanning factor)")
    if diameter <= 0.0:
        raise ValueError("diameter must be > 0 (hydraulic diameter)")
    return diameter / friction_factor * fanno_function(mach, gamma)


def _residual(mach, target, gamma):
    """Residual phi(mach) - target; monotone on each branch, root unique."""
    return fanno_function(mach, gamma) - target


def downstream_mach(mach_in, fld, gamma=GAMMA):
    """Mach number after a duct segment of friction parameter fld = fL/D.

    Solves phi(M2) = phi(M1) - fld by deterministic bisection on the inlet
    branch: subsonic inlet M1 in (0, 1) brackets [M1, 1 - 1e-12] (friction
    accelerates the flow toward M = 1), supersonic inlet M1 > 1 brackets
    [1 + 1e-12, M1] (friction decelerates it toward M = 1). At fld = 0 the
    root sits on the bracket edge and the bisection returns M1.
    """
    _check_mach(mach_in)
    _check_gamma(gamma)
    if mach_in == 1.0:
        raise ValueError("a sonic inlet is already choked; no duct inversion")
    if fld < 0.0:
        raise ValueError("fld must be >= 0 (friction parameter fL/D)")
    phi1 = fanno_function(mach_in, gamma)
    if fld >= phi1:
        raise ValueError(
            "fld at or above the choke value fL*/D(M1): the duct chokes "
            "at or before the exit; use choke_length or friction_to_choke "
            "for the exactly choked duct"
        )
    target = phi1 - fld
    if mach_in < 1.0:
        lo, hi = mach_in, 1.0 - 1e-12
    else:
        lo, hi = 1.0 + 1e-12, mach_in
    for _ in range(MAX_ITER):
        mid = 0.5 * (lo + hi)
        if hi - lo <= BISECT_TOL:
            return mid
        if _residual(mid, target, gamma) * _residual(lo, target, gamma) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def friction_to_choke(mach, duct_length, diameter, gamma=GAMMA):
    """Fanning factor f_req = D/L * phi(M) that chokes the given duct."""
    _check_mach(mach)
    _check_gamma(gamma)
    if duct_length <= 0.0:
        raise ValueError("duct_length must be > 0")
    if diameter <= 0.0:
        raise ValueError("diameter must be > 0 (hydraulic diameter)")
    return diameter / duct_length * fanno_function(mach, gamma)


def total_pressure_ratio(mach, gamma=GAMMA):
    """Total-pressure ratio to the sonic reference, p0/p0*.

    p0/p0* = (1/M) (2 (1 + (gamma - 1) M^2 / 2)/(gamma + 1))
                  ^((gamma + 1)/(2 (gamma - 1)))
    equals 1 at M = 1 and grows on both branches away from it.
    """
    _check_mach(mach)
    _check_gamma(gamma)
    m2 = mach * mach
    base = (2.0 + (gamma - 1.0) * m2) / (gamma + 1.0)
    expo = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    return (1.0 / mach) * base ** expo


def static_ratios(mach, gamma=GAMMA):
    """Static ratios to the sonic reference of the same duct.

    Returns a dict with keys T_Tstar, p_pstar, rho_rhostar from the pinned
    closed forms; all are 1.0 at M = 1 and mutually consistent with
    p/p* = (rho/rho*)(T/T*) and T0/T0* = 1 (adiabatic duct).
    """
    _check_mach(mach)
    _check_gamma(gamma)
    m2 = mach * mach
    denom = 2.0 + (gamma - 1.0) * m2
    t_ratio = (gamma + 1.0) / denom
    p_ratio = (1.0 / mach) * math.sqrt((gamma + 1.0) / denom)
    rho_ratio = (1.0 / mach) * math.sqrt(denom / (gamma + 1.0))
    return {
        "T_Tstar": t_ratio,
        "p_pstar": p_ratio,
        "rho_rhostar": rho_ratio,
    }


def duct_state(mach_in, fld, gamma=GAMMA):
    """Station-to-station state across a duct segment of parameter fL/D.

    Returns a dict with keys mach_out, p02_over_p01, p2_over_p1,
    T2_over_T1, rho2_over_rho1. One duct, one sonic reference: p02/p01 is
    the quotient of p0/p0* at the two stations (below 1 on both branches,
    the friction total-pressure loss) and each static ratio is the quotient
    of the starred static ratios. Identical ValueError set as
    downstream_mach.
    """
    m2 = downstream_mach(mach_in, fld, gamma)
    tpr_in = total_pressure_ratio(mach_in, gamma)
    tpr_out = total_pressure_ratio(m2, gamma)
    s_in = static_ratios(mach_in, gamma)
    s_out = static_ratios(m2, gamma)
    return {
        "mach_out": m2,
        "p02_over_p01": tpr_out / tpr_in,
        "p2_over_p1": s_out["p_pstar"] / s_in["p_pstar"],
        "T2_over_T1": s_out["T_Tstar"] / s_in["T_Tstar"],
        "rho2_over_rho1": s_out["rho_rhostar"] / s_in["rho_rhostar"],
    }
