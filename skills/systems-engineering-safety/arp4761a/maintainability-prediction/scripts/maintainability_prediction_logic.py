"""Maintainability prediction rollup logic for ARP4761A LRU fleets.

Pure stdlib, deterministic. Rolls line-replaceable-unit (LRU) failure
rates and repair-task times into the system maintainability prediction:
the failure-rate-weighted MTTR, the lognormal repair-time model on the
failure-rate-weighted median t50, the t50 and t95 repair-time
percentiles, the PASS/FAIL verdict against the maximum-repair-time
requirement, and an optional per-LRU expected-downtime rollup.

Units: repair times and MTTR are in SECONDS; failure rates are per
hour. Items are lists of (lambda_i, mttr_s_i) tuples, lambda_i the
per-hour failure rate and mttr_s_i the LRU mean or median repair time
in seconds. The lognormal sigma is an engineering input chosen from
fleet data or the documented default, never estimated by this module.
This is the repair-side derivation the arp4761a/markov-analysis leaf
never performs: that leaf takes the repair rate mu (per hour) as a
given input, while pairing this rollup with its two-state model gives
mu = 1/MTTR and the steady-state unavailability lambda/(lambda + mu)
only in the small-product limit lambda * MTTR_h << 1.

Functions (all ValueError on non-physical inputs, all deterministic):
failure_rate_weighted_mttr, failure_rate_weighted_median,
normal_quantile (Acklam inverse normal CDF), lognormal_percentile,
maintainability_verdict, lru_downtime_rollup.
"""

import math

# Documented 2 h maximum-repair-time requirement, applied to the t95
# repair-time percentile.
MAX_REPAIR_TIME_LIMIT_S = 7200.0

# Typical lognormal log-space spread for avionics and mechanical LRU
# repair times when fleet data is absent.
REPAIR_TIME_SIGMA_DEFAULT = 0.5

SECONDS_PER_HOUR = 3600.0

# Acklam inverse normal CDF coefficients, published coefficient sets.
# Central region polynomial (a1..a6, b1..b5) valid between the tail
# split probability P_LOW and its mirror.
ACKLAM_A = (
    -3.969683028665376e+01,
    2.209460984245205e+02,
    -2.759285104469687e+02,
    1.383577518672690e+02,
    -3.066479806614716e+01,
    2.506628277459239e+00,
)
ACKLAM_B = (
    -5.447609879822406e+01,
    1.615858368580409e+02,
    -1.556989798598866e+02,
    6.680131188771972e+01,
    -1.328068155288572e+01,
)
# Tail region rational approximation (c1..c6, d1..d4).
ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e+00,
    -2.549732539343734e+00,
    4.374664141464968e+00,
    2.938163982698783e+00,
)
ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e+00,
    3.754408661907416e+00,
)
P_LOW = 0.02425


def _validate_items(items):
    """Return (total_rate, weighted numerator helpers) after checks.

    Raise ValueError on an empty items list, on any lambda_i <= 0, on
    any mttr_s_i <= 0, and on a total rate of 0. Every item is a
    (lambda_i, mttr_s_i) pair of positive floats.
    """
    if items is None or len(items) == 0:
        raise ValueError("items must contain at least one LRU")
    total_rate = 0.0
    for item in items:
        try:
            lam, mttr_s = item
        except (TypeError, ValueError):
            raise ValueError("each item must be a (lambda, mttr_s) pair")
        if lam <= 0.0:
            raise ValueError("failure rate lambda must be positive")
        if mttr_s <= 0.0:
            raise ValueError("repair time mttr_s must be positive")
        total_rate += lam
    if total_rate == 0.0:
        raise ValueError("total failure rate must be positive")
    return total_rate


def failure_rate_weighted_mttr(items):
    """Return the failure-rate-weighted MTTR in seconds.

    Step 1 of the SKILL.md workflow, the lambda-weighted rollup of the
    per-LRU mean repair times: sum(lambda_i * mttr_s_i) /
    sum(lambda_i). With equal failure rates this collapses to the
    plain arithmetic mean of the repair times.
    """
    total_rate = _validate_items(items)
    numerator = 0.0
    for lam, mttr_s in items:
        numerator += lam * mttr_s
    return numerator / total_rate


def failure_rate_weighted_median(items):
    """Return the failure-rate-weighted median repair time t50 in seconds.

    Step 2 of the SKILL.md workflow, the lambda-weighted geometric mean
    of the per-LRU median repair times: exp(sum(lambda_i * ln(mttr_s_i))
    / sum(lambda_i)). This t50 is the median parameter of the system
    lognormal repair-time model. With equal failure rates it collapses
    to the plain geometric mean of the repair times.
    """
    total_rate = _validate_items(items)
    log_numerator = 0.0
    for lam, mttr_s in items:
        log_numerator += lam * math.log(mttr_s)
    return math.exp(log_numerator / total_rate)


def normal_quantile(p):
    """Return z_p, the p-th quantile of the standard normal CDF.

    Step 3 of the SKILL.md workflow, Acklam's inverse normal CDF with
    the published coefficient sets: the central polynomial between the
    tail split at P_LOW = 0.02425 and its mirror, the tail rational
    form outside it, and the single refinement step
    x = x - u / (1 + x * u / 2) with u = e * sqrt(2 pi) * exp(x^2 / 2)
    and e = 0.5 * erfc(-x / sqrt(2)) - p computed with stdlib
    math.erfc. normal_quantile(0.5) is 0.0 exactly and
    normal_quantile(0.95) is 1.6448536269514726 on IEEE-754 doubles.
    """
    if not (0.0 < p < 1.0):
        raise ValueError("probability p must lie strictly inside (0, 1)")
    if p < P_LOW:
        # Lower tail: negative z, rational approximation in sqrt(-2 ln p).
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((ACKLAM_C[0] * q + ACKLAM_C[1]) * q + ACKLAM_C[2]) * q
               + ACKLAM_C[3]) * q + ACKLAM_C[4]) * q + ACKLAM_C[5]) / (
            ((((ACKLAM_D[0] * q + ACKLAM_D[1]) * q + ACKLAM_D[2]) * q
              + ACKLAM_D[3]) * q + 1.0))
    elif p > 1.0 - P_LOW:
        # Upper tail: positive z by symmetry.
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -((((((ACKLAM_C[0] * q + ACKLAM_C[1]) * q + ACKLAM_C[2]) * q
                 + ACKLAM_C[3]) * q + ACKLAM_C[4]) * q + ACKLAM_C[5]) / (
            ((((ACKLAM_D[0] * q + ACKLAM_D[1]) * q + ACKLAM_D[2]) * q
              + ACKLAM_D[3]) * q + 1.0)))
    else:
        # Central region: odd polynomial in (p - 0.5).
        q = p - 0.5
        r = q * q
        x = ((((((ACKLAM_A[0] * r + ACKLAM_A[1]) * r + ACKLAM_A[2]) * r
                 + ACKLAM_A[3]) * r + ACKLAM_A[4]) * r + ACKLAM_A[5])
             * q) / ((((((ACKLAM_B[0] * r + ACKLAM_B[1]) * r + ACKLAM_B[2])
                        * r + ACKLAM_B[3]) * r + ACKLAM_B[4]) * r + 1.0))
    # Single refinement step for the full 1e-15 accuracy claim.
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    x = x - u / (1.0 + x * u / 2.0)
    return x


def lognormal_percentile(mttr_median, sigma, p):
    """Return the p-th percentile of the lognormal repair-time model.

    Step 4 of the SKILL.md workflow, t_p = mttr_median *
    exp(sigma * normal_quantile(p)): t50 equals mttr_median exactly at
    p = 0.5 (z = 0, identity) and t95 = mttr_median * exp(sigma *
    z_0.95) carries the maximum-repair-time check. sigma = 0 collapses
    every percentile onto the median.
    """
    if mttr_median <= 0.0:
        raise ValueError("median repair time mttr_median must be positive")
    if sigma < 0.0:
        raise ValueError("lognormal sigma must be non-negative")
    return mttr_median * math.exp(sigma * normal_quantile(p))


def maintainability_verdict(t95, requirement_limit=MAX_REPAIR_TIME_LIMIT_S):
    """Return the verdict dict for predicted t95 against the limit.

    Step 5 of the SKILL.md workflow, the maximum-repair-time verdict:
    PASS when t95 <= requirement_limit (inclusive at the boundary),
    else FAIL, with margin_s = requirement_limit - t95 (non-negative
    on PASS, the negative shortfall on FAIL). Keys are exactly
    verdict, t95_s, limit_s and margin_s.
    """
    if t95 <= 0.0:
        raise ValueError("predicted t95 repair time must be positive")
    if requirement_limit <= 0.0:
        raise ValueError("requirement limit must be positive")
    if t95 <= requirement_limit:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    return {
        "verdict": verdict,
        "t95_s": t95,
        "limit_s": requirement_limit,
        "margin_s": requirement_limit - t95,
    }


def lru_downtime_rollup(items, exposure_hours):
    """Return the per-LRU expected-downtime rollup over the exposure.

    Step 6 of the SKILL.md workflow: per-LRU expected downtime D_i =
    lambda_i * exposure_hours * (mttr_s_i / SECONDS_PER_HOUR) hours,
    total_downtime_hours the sum over LRUs, and
    expected_unavailability = total_downtime_hours / exposure_hours.
    This is the small-unavailability approximation: it reproduces the
    markov-analysis steady-state unavailability lambda/(lambda + mu)
    with mu = 1/MTTR_h only in the limit lambda * MTTR_h << 1; the
    exact two-state value is the markov-analysis function's job.
    """
    if exposure_hours <= 0.0:
        raise ValueError("exposure hours must be positive")
    total_rate = _validate_items(items)
    per_lru = []
    total_downtime = 0.0
    for lam, mttr_s in items:
        downtime = lam * exposure_hours * (mttr_s / SECONDS_PER_HOUR)
        per_lru.append(downtime)
        total_downtime += downtime
    return {
        "per_lru_downtime_hours": per_lru,
        "total_downtime_hours": total_downtime,
        "expected_unavailability": total_downtime / exposure_hours,
    }
