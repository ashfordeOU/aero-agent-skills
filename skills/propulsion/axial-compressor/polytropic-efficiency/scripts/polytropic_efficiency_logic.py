"""Polytropic efficiency conversions for compressor and turbine sizing.

Pure stdlib, closed form, air-standard gamma = 1.4 only.  The polytropic
(stage-count-independent) efficiency eta_p sits in the denominator of the
compressor exponent because the actual temperature rise exceeds the
isentropic rise at every small stage: t02/t01 = pr**(KAPPA/eta_p).  The
turbine relation mirrors it with the temperature ratio inverted,
t04/t03 = pr**(-KAPPA*eta_p), because the actual temperature drop falls
short of the isentropic drop.

All functions raise ValueError on non-physical inputs: pressure ratios
must exceed 1, efficiencies must lie in (0, 1], and the state
temperatures must describe a real compression (t02 > t01) or a real
expansion (t04 < t03).
"""

import math

# Air-standard ratio of specific heats (fixed for this leaf).
GAMMA = 1.4
# Isentropic exponent (GAMMA - 1) / GAMMA = 2/7, about 0.285714.
KAPPA = (GAMMA - 1.0) / GAMMA


def _check_pr(pr):
    """Raise ValueError unless the pressure ratio is physical (pr > 1)."""
    if pr <= 1.0:
        raise ValueError(
            "pressure ratio must exceed 1 for a compression or expansion, "
            "got {0!r}".format(pr)
        )


def _check_eta(eta):
    """Raise ValueError unless the efficiency lies in (0, 1]."""
    if not (0.0 < eta <= 1.0):
        raise ValueError(
            "efficiency must lie in (0, 1], got {0!r}".format(eta)
        )


def _check_stage_prs(stage_prs):
    """Raise ValueError unless the stage ratio list is non-empty and valid."""
    if not stage_prs:
        raise ValueError("stage_prs must not be empty")
    for pr in stage_prs:
        _check_pr(pr)


def compressor_polytropic_from_states(t01, t02, pr):
    """Resolve the compressor polytropic efficiency from total states.

    eta_p = KAPPA * ln(pr) / ln(t02/t01), the closed form resolved from
    the defining relation t02/t01 = pr**(KAPPA/eta_p).  Both state
    temperatures are required.  Raises ValueError for non-positive
    temperatures, t02 <= t01 (no compression) or pr <= 1.
    """
    if t01 <= 0.0 or t02 <= 0.0:
        raise ValueError(
            "total temperatures must be positive, got t01={0!r}, t02={1!r}"
            .format(t01, t02)
        )
    if t02 <= t01:
        raise ValueError(
            "t02 must exceed t01 for a compression, got t01={0!r}, t02={1!r}"
            .format(t01, t02)
        )
    _check_pr(pr)
    return KAPPA * math.log(pr) / math.log(t02 / t01)


def compressor_isentropic_from_polytropic(eta_p, pr):
    """Convert a compressor polytropic efficiency to the isentropic one.

    eta_s = (pr**KAPPA - 1) / (pr**(KAPPA/eta_p) - 1) from
    eta_s = (t02s - t01) / (t02 - t01) with the polytropic and isentropic
    temperature ratios.  Raises ValueError if eta_p lies outside (0, 1]
    or pr <= 1.
    """
    _check_eta(eta_p)
    _check_pr(pr)
    return (pr ** KAPPA - 1.0) / (pr ** (KAPPA / eta_p) - 1.0)


def compressor_polytropic_from_isentropic(eta_s, pr):
    """Convert a compressor isentropic efficiency to the polytropic one.

    eta_p = KAPPA * ln(pr) / ln(1 + (pr**KAPPA - 1)/eta_s), the exact
    inverse of compressor_isentropic_from_polytropic at fixed pr.  Raises
    ValueError if eta_s lies outside (0, 1] or pr <= 1.
    """
    _check_eta(eta_s)
    _check_pr(pr)
    return KAPPA * math.log(pr) / math.log(
        1.0 + (pr ** KAPPA - 1.0) / eta_s
    )


def turbine_polytropic_from_states(t03, t04, pr):
    """Resolve the turbine polytropic efficiency from total states.

    eta_p = ln(t03/t04) / (KAPPA * ln(pr)), resolved from the defining
    relation t04/t03 = pr**(-KAPPA*eta_p) with pr = p03/p04 the
    expansion ratio.  Raises ValueError for non-positive temperatures,
    t04 >= t03 (no expansion) or pr <= 1.
    """
    if t03 <= 0.0 or t04 <= 0.0:
        raise ValueError(
            "total temperatures must be positive, got t03={0!r}, t04={1!r}"
            .format(t03, t04)
        )
    if t04 >= t03:
        raise ValueError(
            "t04 must be below t03 for an expansion, got t03={0!r}, t04={1!r}"
            .format(t03, t04)
        )
    _check_pr(pr)
    return math.log(t03 / t04) / (KAPPA * math.log(pr))


def turbine_isentropic_from_polytropic(eta_p, pr):
    """Convert a turbine polytropic efficiency to the isentropic one.

    eta_s = (1 - pr**(-KAPPA*eta_p)) / (1 - pr**(-KAPPA)) from
    eta_s = (t03 - t04) / (t03 - t04s).  Raises ValueError if eta_p lies
    outside (0, 1] or pr <= 1.
    """
    _check_eta(eta_p)
    _check_pr(pr)
    return (1.0 - pr ** (-KAPPA * eta_p)) / (1.0 - pr ** (-KAPPA))


def turbine_polytropic_from_isentropic(eta_s, pr):
    """Convert a turbine isentropic efficiency to the polytropic one.

    eta_p = ln(1 - eta_s*(1 - pr**(-KAPPA))) / (-KAPPA * ln(pr)), the
    exact inverse of turbine_isentropic_from_polytropic at fixed pr.
    Numerator and denominator are both negative for pr > 1 and eta_s in
    (0, 1].  Raises ValueError if eta_s lies outside (0, 1] or pr <= 1.
    """
    _check_eta(eta_s)
    _check_pr(pr)
    return math.log(1.0 - eta_s * (1.0 - pr ** (-KAPPA))) / (
        -KAPPA * math.log(pr)
    )


def reheat_factor_check(stage_prs, overall_pr):
    """Cross-check stage ratios against the overall ratio on the log scale.

    R = sum(ln(pr_i) for pr_i in stage_prs) / ln(overall_pr), the
    log-sum consistency ratio on the pressure-ratio side.  Because the
    polytropic stage terms are additive on the log scale, R equals 1
    exactly when the product of the stage ratios equals the overall
    ratio (equal-stage identity); R below or above 1 flags stage data
    inconsistent with the quoted overall ratio.  This is NOT the
    work-based reheat factor RF = W_actual / W_ideal_sum of the
    multi-stage-compressor leaf, which inflates with the stage count and
    is not computed here.  Raises ValueError if stage_prs is empty, any
    stage ratio is <= 1, or overall_pr <= 1.
    """
    _check_stage_prs(stage_prs)
    _check_pr(overall_pr)
    log_sum = sum(math.log(pr) for pr in stage_prs)
    return log_sum / math.log(overall_pr)
