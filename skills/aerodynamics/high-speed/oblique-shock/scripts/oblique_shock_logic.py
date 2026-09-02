#!/usr/bin/env python3
"""Oblique shock relations for compressible flow (stdlib only).

A supersonic flow turned into itself (compression corner, wedge) forms
an attached oblique shock inclined at the wave angle beta to the
upstream flow. Only the Mach number component normal to the shock
M1n = M1 * sin(beta) changes across it; the tangential component
passes through unchanged. The normal shock relations applied to M1n
give the downstream ratios, and the downstream Mach number follows
from M2 = M2n / sin(beta - theta), where theta is the flow deflection
angle.

The theta-beta-M relation ties the three together:

  tan(theta) = 2 * cot(beta) * (M1^2 * sin^2(beta) - 1)
               / (M1^2 * (gamma + cos(2*beta)) + 2)

For a given M1 and theta below the maximum deflection theta_max there
are two wave angles: the weak solution (small beta, downstream flow
usually still supersonic, the physically realized branch) and the
strong solution (large beta, downstream subsonic). Above theta_max no
attached oblique shock exists and the shock detaches. theta = 0 gives
beta = mu = asin(1/M1) (Mach wave, isentropic limit) on the weak
branch and beta = 90 deg (normal shock) on the strong branch; the two
branches merge at theta_max, the apex of the shock polar.

All inputs are unitless: M1 > 1, beta in degrees with asin(1/M1) < beta
<= 90, theta in degrees with 0 <= theta <= theta_max, gamma > 1
(default 1.4 for air). Violations raise ValueError.

Textbook anchor at M1 = 2.0, theta = 10 deg, gamma = 1.4 (Anderson,
Modern Compressible Flow, Example 4.2): weak solution beta = 39.31 deg,
M2 = 1.64, p2/p1 = 1.707; strong solution beta = 83.70 deg, M2 = 0.604,
p2/p1 = 4.444. At theta = 0 the strong branch collapses onto the normal
shock (beta = 90 deg, p2/p1 = 4.5, M2 = 0.5773503 at M1 = 2) and the
weak branch onto the Mach wave (beta = mu, p2/p1 = 1).
"""

import math


def _validate(M1, gamma):
    """Reject nonphysical inputs: M1 must be supersonic, gamma > 1."""
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 (specific heat ratio)")
    if M1 <= 1.0:
        raise ValueError("M1 must be > 1 (upstream flow must be supersonic)")


# mu = degrees(asin(1/M1)) is not bit-identical across libm
# implementations (observed: macOS vs Linux glibc can differ by ~1e-14
# deg), so a strict beta_deg <= mu boundary check is platform-dependent
# right at beta_deg == mu. This tolerance is two orders of magnitude
# above that noise floor and two orders below the 1e-9 offset the
# invalid-input tests probe with, so it absorbs the platform noise
# without loosening the actual validation.
_MU_TOL_DEG = 1e-10


def _validate_beta(M1, beta_deg, gamma=1.4):
    """Reject wave angles outside (mu, 90 deg]: below the Mach angle no
    shock exists, above 90 deg the relation is meaningless."""
    _validate(M1, gamma)
    mu = math.degrees(math.asin(1.0 / M1))
    if beta_deg <= mu - _MU_TOL_DEG:
        raise ValueError(
            "beta must be > mu = %g deg (Mach angle); below it there is no shock" % mu
        )
    if beta_deg > 90.0:
        raise ValueError("beta must be <= 90 deg (normal shock limit)")


def mach_angle(M1):
    """Mach wave angle mu = asin(1/M1) in degrees (unitless input).

    The limiting wave angle of the weak branch as the deflection goes
    to zero. M1 > 1 required.
    """
    if M1 <= 1.0:
        raise ValueError("M1 must be > 1 (Mach angle is undefined at or below Mach 1)")
    return math.degrees(math.asin(1.0 / M1))


def theta_beta_m(M1, beta_deg, gamma=1.4):
    """Flow deflection angle theta in degrees (unitless inputs).

    The theta-beta-M relation: the deflection of a supersonic flow
    across an oblique shock at wave angle beta. theta = 0 at both the
    Mach angle mu (weak limit) and 90 deg (normal shock); a single
    interior maximum theta_max separates the weak and strong branches.
    """
    _validate_beta(M1, beta_deg, gamma)
    b = math.radians(beta_deg)
    m1s = M1 * M1
    num = 2.0 * (1.0 / math.tan(b)) * (m1s * math.sin(b) * math.sin(b) - 1.0)
    den = m1s * (gamma + math.cos(2.0 * b)) + 2.0
    return math.degrees(math.atan(num / den))


def deflection_limit(M1, gamma=1.4):
    """Maximum attached-shock deflection theta_max in degrees.

    The apex of the shock polar: the largest flow deflection for which
    an attached oblique shock exists at M1. Above it the shock
    detaches. Grows with M1 toward about 45.6 deg (gamma = 1.4) as
    M1 goes to infinity.
    """
    _validate(M1, gamma)
    mu = math.degrees(math.asin(1.0 / M1))
    lo = mu + 1e-9
    hi = 90.0
    for _ in range(200):
        m1 = (2.0 * lo + hi) / 3.0
        m2 = (lo + 2.0 * hi) / 3.0
        if theta_beta_m(M1, m1, gamma) < theta_beta_m(M1, m2, gamma):
            lo = m1
        else:
            hi = m2
    mid = 0.5 * (lo + hi)
    return theta_beta_m(M1, mid, gamma)


def _normal_ratios(m1n, gamma):
    """Ratios across the shock from the normal Mach component."""
    p = 1.0 + 2.0 * gamma / (gamma + 1.0) * (m1n * m1n - 1.0)
    r = (gamma + 1.0) * m1n * m1n / (2.0 + (gamma - 1.0) * m1n * m1n)
    t = p / r
    p0 = p ** (1.0 / (1.0 - gamma)) * r ** (gamma / (gamma - 1.0))
    m2n = math.sqrt(
        (1.0 + (gamma - 1.0) / 2.0 * m1n * m1n)
        / (gamma * m1n * m1n - (gamma - 1.0) / 2.0)
    )
    return m2n, p, r, t, p0


def shock_angles(M1, theta_deg, gamma=1.4):
    """Weak and strong wave angles (beta_weak, beta_strong) in degrees.

    Both solutions of the theta-beta-M relation for a deflection
    theta_deg in [0, theta_max]. The weak branch (smaller beta) is the
    physically realized one in most attached-shock flows; the strong
    branch (larger beta) makes the downstream flow subsonic. theta = 0
    returns (mu, 90). A deflection above theta_max raises ValueError
    (detached shock: no attached oblique shock exists).
    """
    _validate(M1, gamma)
    if theta_deg < 0.0:
        raise ValueError("theta must be >= 0 (a negative deflection is an expansion)")
    tmax = deflection_limit(M1, gamma)
    if theta_deg > tmax:
        raise ValueError(
            "theta = %g deg exceeds theta_max = %g deg at M1 = %g: "
            "the shock detaches (no attached oblique shock)"
            % (theta_deg, tmax, M1)
        )
    mu = math.degrees(math.asin(1.0 / M1))

    def _target(beta):
        return theta_beta_m(M1, beta, gamma) - theta_deg

    # Weak root on (mu, beta_at_tmax]; strong root on [beta_at_tmax, 90).
    lo = mu + 1e-9
    hi = 90.0
    for _ in range(200):
        m1 = (2.0 * lo + hi) / 3.0
        m2 = (lo + 2.0 * hi) / 3.0
        if theta_beta_m(M1, m1, gamma) < theta_beta_m(M1, m2, gamma):
            lo = m1
        else:
            hi = m2
    bmax = 0.5 * (lo + hi)
    if theta_deg <= 1e-12:
        return mu, 90.0
    lo_w, hi_w = mu + 1e-9, bmax
    for _ in range(200):
        mid = 0.5 * (lo_w + hi_w)
        if _target(mid) < 0.0:
            lo_w = mid
        else:
            hi_w = mid
    beta_weak = 0.5 * (lo_w + hi_w)
    lo_s, hi_s = bmax, 90.0
    for _ in range(200):
        mid = 0.5 * (lo_s + hi_s)
        if _target(mid) > 0.0:
            lo_s = mid
        else:
            hi_s = mid
    beta_strong = 0.5 * (lo_s + hi_s)
    return beta_weak, beta_strong


def shock_properties(M1, theta_deg, gamma=1.4, strong=False):
    """Downstream state across the oblique shock (unitless).

    Returns the dict {m2, beta_deg, p2_p1, rho2_rho1, t2_t1, p02_p01,
    theta_deg, strong} for the deflection theta_deg: the wave angle on
    the weak branch (strong=False, default) or the strong branch, the
    downstream Mach number from M2 = M2n / sin(beta - theta), and the
    static ratios from the normal shock relations on M1n = M1 *
    sin(beta). p02/p01 < 1: the oblique shock still loses stagnation
    pressure, but far less than the normal shock at the same M1.
    """
    beta_weak, beta_strong = shock_angles(M1, theta_deg, gamma)
    beta = beta_strong if strong else beta_weak
    m1n = M1 * math.sin(math.radians(beta))
    m2n, p, r, t, p0 = _normal_ratios(m1n, gamma)
    m2 = m2n / math.sin(math.radians(beta - theta_deg))
    return {
        "m2": m2,
        "beta_deg": beta,
        "p2_p1": p,
        "rho2_rho1": r,
        "t2_t1": t,
        "p02_p01": p0,
        "theta_deg": theta_deg,
        "strong": bool(strong),
    }
