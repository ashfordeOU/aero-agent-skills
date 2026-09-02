#!/usr/bin/env python3
"""Supersonic ramjet inlet logic: diffuser pressure recovery and the
Kantrowitz starting criterion (paraphrase, common propulsion methodology).

Common-knowledge summary (standards-map.yaml, far-33: public domain
regulation context): a supersonic ramjet inlet decelerates the captured
flow in the diffuser. The total pressure recovery is the ratio of the
diffuser exit total pressure to the freestream total pressure. Ideal
(isentropic) deceleration recovers 1.0. A pitot-type inlet at a
supersonic flight Mach number carries a normal shock at the cowl lip,
and the recovery is the normal shock total pressure ratio at the flight
Mach M:

p02/p01 = [((gamma + 1) M^2) / ((gamma - 1) M^2 + 2)]^(gamma/(gamma-1))
          * [(gamma + 1) / (2 gamma M^2 - (gamma - 1))]^(1/(gamma-1))

with 0.7209 at M = 2 and 0.3283 at M = 3 for gamma = 1.4. The Kantrowitz
starting criterion says the inlet with contraction ratio CR (capture
area over throat area) swallows the lip shock and starts only when the
quasi-steady choked-throat mass flow behind the shock passes the
captured flow: CR <= CR_K(M) with

CR_K(M) = (1/M) * (p02/p01)_ns(M)
          * (1 + (gamma - 1)/2 M^2)^((gamma+1)/(2(gamma-1)))
          * ((gamma + 1)/2)^(-(gamma+1)/(2(gamma-1)))

which rises from 1.0 at M = 1 toward about 1.666 (gamma = 1.4) as M
grows; a contraction above that can never start at any Mach number.
Units: pressures in Pa, Mach number and all ratios dimensionless.
"""

import math

DEFAULT_GAMMA = 1.4
MAX_BISECTION_MACH = 1.0e6
BISECTION_ITERATIONS = 200


def _check_gamma(gamma):
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))


def normal_shock_total_pressure_ratio(mach, gamma=DEFAULT_GAMMA):
    """Total pressure ratio p02/p01 across a normal shock at Mach.

    Valid for supersonic Mach only: raises ValueError below M = 1 and
    for gamma <= 1. Returns 1.0 at exactly M = 1 (Mach wave).
    """
    _check_gamma(gamma)
    if mach < 1.0:
        raise ValueError("Mach number must be >= 1 for a normal shock, got %r" % (mach,))
    m2 = mach * mach
    f1 = ((gamma + 1.0) * m2) / ((gamma - 1.0) * m2 + 2.0)
    f2 = (gamma + 1.0) / (2.0 * gamma * m2 - (gamma - 1.0))
    return f1 ** (gamma / (gamma - 1.0)) * f2 ** (1.0 / (gamma - 1.0))


def isentropic_pressure_recovery():
    """Ideal diffuser total pressure recovery: 1.0, no losses.

    The reference ceiling for the isentropic deceleration of the
    captured flow; unreachable at a supersonic Mach number.
    """
    return 1.0


def pressure_recovery(mach, shock_model="normal", gamma=DEFAULT_GAMMA):
    """Diffuser total pressure recovery at the flight Mach number.

    shock_model "normal" uses the normal shock at the cowl lip (the
    pitot-type inlet recovery at supersonic Mach); "isentropic" uses
    the ideal lossless value 1.0. Raises ValueError for an unknown
    model, a non-positive Mach, or a subsonic Mach on the normal
    branch.
    """
    if shock_model not in ("normal", "isentropic"):
        raise ValueError(
            "shock model must be 'normal' or 'isentropic', got %r" % (shock_model,)
        )
    if mach <= 0.0:
        raise ValueError("Mach number must be > 0, got %r" % (mach,))
    if shock_model == "isentropic":
        return isentropic_pressure_recovery()
    return normal_shock_total_pressure_ratio(mach, gamma)


def exit_total_pressure(freestream_total_pressure_pa, mach,
                        shock_model="normal", gamma=DEFAULT_GAMMA):
    """Diffuser exit total pressure pt2 = pi_d * pt0 in Pa."""
    if freestream_total_pressure_pa <= 0.0:
        raise ValueError(
            "freestream total pressure must be > 0 Pa, got %r"
            % (freestream_total_pressure_pa,)
        )
    recovery = pressure_recovery(mach, shock_model, gamma)
    return freestream_total_pressure_pa * recovery


def kantrowitz_contraction_limit(mach, gamma=DEFAULT_GAMMA):
    """Kantrowitz limit contraction ratio CR_K(M), dimensionless.

    The largest contraction ratio the inlet starts at Mach: the
    quasi-steady balance of the captured mass flow against the choked
    throat flow behind a normal shock standing at the lip. Returns
    1.0 at M = 1 and rises toward about 1.666 for gamma = 1.4. Raises
    ValueError for a subsonic Mach or gamma <= 1.
    """
    _check_gamma(gamma)
    if mach < 1.0:
        raise ValueError(
            "Mach number must be >= 1 for the starting criterion, got %r" % (mach,)
        )
    recovery = normal_shock_total_pressure_ratio(mach, gamma)
    factor = (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (
        (gamma + 1.0) / (2.0 * (gamma - 1.0))
    )
    scale = ((gamma + 1.0) / 2.0) ** (-(gamma + 1.0) / (2.0 * (gamma - 1.0)))
    return (1.0 / mach) * recovery * factor * scale


def kantrowitz_max_contraction(gamma=DEFAULT_GAMMA):
    """Asymptotic Kantrowitz limit as the Mach number grows without bound.

    About 1.666 for gamma = 1.4: no inlet with a larger contraction
    ratio can ever start at any Mach number.
    """
    _check_gamma(gamma)
    return kantrowitz_contraction_limit(MAX_BISECTION_MACH, gamma)


def kantrowitz_limit_mach(contraction_ratio, gamma=DEFAULT_GAMMA):
    """Starting limit Mach number for a fixed contraction ratio.

    The M that solves CR_K(M) = contraction_ratio, found by bisection.
    A ratio at or below 1.0 starts from M = 1. Raises ValueError for a
    non-positive ratio, gamma <= 1, or a ratio at or above the
    asymptotic Kantrowitz limit that no Mach number can start.
    """
    _check_gamma(gamma)
    if contraction_ratio <= 0.0:
        raise ValueError(
            "contraction ratio must be > 0, got %r" % (contraction_ratio,)
        )
    if contraction_ratio <= 1.0:
        return 1.0
    limit = kantrowitz_max_contraction(gamma)
    if contraction_ratio >= limit:
        raise ValueError(
            "contraction ratio %r cannot start at any Mach number "
            "(Kantrowitz limit %r for gamma %r)"
            % (contraction_ratio, limit, gamma)
        )
    lo = 1.0
    hi = MAX_BISECTION_MACH
    for _ in range(BISECTION_ITERATIONS):
        mid = 0.5 * (lo + hi)
        if kantrowitz_contraction_limit(mid, gamma) < contraction_ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def inlet_starts(flight_mach, contraction_ratio, gamma=DEFAULT_GAMMA):
    """True when the inlet starts at the flight Mach and contraction.

    The inlet swallows the lip shock when the contraction ratio is at
    or below the Kantrowitz limit CR_K(flight_mach). Raises ValueError
    for a subsonic flight Mach or a non-positive contraction ratio.
    """
    _check_gamma(gamma)
    if flight_mach < 1.0:
        raise ValueError(
            "flight Mach number must be >= 1 for the starting criterion, got %r"
            % (flight_mach,)
        )
    if contraction_ratio <= 0.0:
        raise ValueError(
            "contraction ratio must be > 0, got %r" % (contraction_ratio,)
        )
    return contraction_ratio <= kantrowitz_contraction_limit(flight_mach, gamma)


def freestream_total_pressure(static_pressure_pa, mach, gamma=DEFAULT_GAMMA):
    """Freestream stagnation pressure pt0 = p0 * (1 + 0.2 M^2)^3.5."""
    _check_gamma(gamma)
    if static_pressure_pa <= 0.0:
        raise ValueError("static pressure must be > 0 Pa, got %r" % (static_pressure_pa,))
    if mach < 0.0:
        raise ValueError("Mach number must be >= 0, got %r" % (mach,))
    return static_pressure_pa * (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (
        gamma / (gamma - 1.0)
    )
