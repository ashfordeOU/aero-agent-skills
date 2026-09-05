"""Exact binomial test of an observed count against a hypothesized proportion.

Pure stdlib implementation (math.comb, math.erfc) of the exact binomial
tail test for attribute-data significance claims: the single-outcome mass
P(X = k), the cumulative lower tail P(X <= k), the exact test verdict dict
with the doubling convention for the two-sided p-value and an optional
mid-p correction, the normal approximation with the continuity correction
as a large-sample cross-check, and the small-count recommendation that
gates when the exact tail must be used instead of the approximation.

Conventions (documented in the SKILL.md workflow):
- The observed direction is "less" when k sits at or below the null mean
  n*p0 and "greater" otherwise; the one-sided p-value is the lower tail in
  the first case and the upper tail in the second.
- The two-sided p-value doubles the observed-direction one-sided mass and
  caps the result at 1 (the documented doubling convention shared with the
  nonparametric two-sided family). At or above a one-sided mass of one half
  the cap makes the two-sided p-value exactly 1.
- The mid-p correction subtracts the probability of the observed count,
  P(X = k), from the doubled two-sided p-value, and half of it from a
  one-sided p-value, relaxing the conservative doubling.
- The continuity correction moves the count half a step toward the null
  mean before the z transform.
"""

import math

__all__ = [
    "binomial_probability",
    "binomial_cdf",
    "binomial_exact_test",
    "binomial_normal_approximation",
    "small_count_recommendation",
]


def _as_count(value, name):
    """Return value as an int count, rejecting booleans and non-integral numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a whole-number count, got %r" % (name, value))
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("%s must be a whole-number count, got %r" % (name, value))
    return int(value)


def _as_probability(p, name="p"):
    """Return p as a float, rejecting values at or outside the open unit interval."""
    if isinstance(p, bool) or not isinstance(p, (int, float)):
        raise ValueError("%s must be a proportion in (0, 1), got %r" % (name, p))
    p = float(p)
    if p <= 0.0 or p >= 1.0:
        raise ValueError("%s must lie strictly inside (0, 1), got %r" % (name, p))
    return p


def _require_trials(n):
    """Validate n as an integer trial count of at least 1."""
    n = _as_count(n, "n")
    if n < 1:
        raise ValueError("n must be at least 1, got %r" % (n,))
    return n


def _require_count(k, n):
    """Validate k as an integer count inside [0, n] for n trials."""
    k = _as_count(k, "k")
    if k < 0 or k > n:
        raise ValueError("k must be an integer in [0, n], got %r with n %r" % (k, n))
    return k


def binomial_probability(k, n, p):
    """Probability of exactly k successes in n Bernoulli trials with success probability p.

    C(n, k) * p**k * (1 - p)**(n - k) via math.comb. Raises ValueError for a
    non-integer or out-of-range k, n below 1, or p at or outside (0, 1).
    """
    n = _require_trials(n)
    k = _require_count(k, n)
    p = _as_probability(p)
    return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))


def binomial_cdf(k, n, p):
    """Lower tail P(X <= k): the sum of the exact binomial probabilities over j = 0..k.

    Returns exactly 1.0 when k equals n. Raises ValueError for a non-integer or
    out-of-range k, n below 1, or p at or outside (0, 1).
    """
    n = _require_trials(n)
    k = _require_count(k, n)
    p = _as_probability(p)
    if k == n:
        return 1.0
    total = 0.0
    for j in range(k + 1):
        total += math.comb(n, j) * (p ** j) * ((1.0 - p) ** (n - j))
    return total


def binomial_exact_test(k, n, p0, alternative="two-sided", midp=False):
    """Exact binomial test of the observed count k against the null proportion p0.

    Returns a dict with the exact keys p_lower_tail (P(X <= k)), p_upper_tail
    (P(X >= k)), p_value, direction and midp_applied. With alternative
    "less" the p-value is the lower tail and with "greater" the upper tail;
    with "two-sided" the p-value doubles the observed-direction one-sided
    mass and caps at 1. With midp True the two-sided p-value drops the
    probability of the observed count and each one-sided p-value drops half
    of it. Raises ValueError for a non-integer or out-of-range k, p0 at or
    outside (0, 1), or an unknown alternative.
    """
    n = _require_trials(n)
    k = _require_count(k, n)
    p0 = _as_probability(p0, "p0")
    if alternative not in ("two-sided", "less", "greater"):
        raise ValueError(
            "alternative must be 'two-sided', 'less' or 'greater', got %r"
            % (alternative,)
        )
    p_lower_tail = binomial_cdf(k, n, p0)
    if k == 0:
        p_upper_tail = 1.0
    else:
        p_upper_tail = 1.0 - binomial_cdf(k - 1, n, p0)
    direction = "less" if k <= n * p0 else "greater"
    p_obs = binomial_probability(k, n, p0)
    if alternative == "two-sided":
        one_sided = p_lower_tail if direction == "less" else p_upper_tail
        p_value = min(2.0 * one_sided, 1.0)
        if midp:
            p_value = max(p_value - p_obs, 0.0)
    elif alternative == "less":
        p_value = p_lower_tail
        if midp:
            p_value = max(p_value - 0.5 * p_obs, 0.0)
    else:
        p_value = p_upper_tail
        if midp:
            p_value = max(p_value - 0.5 * p_obs, 0.0)
    return {
        "p_lower_tail": p_lower_tail,
        "p_upper_tail": p_upper_tail,
        "p_value": p_value,
        "direction": direction,
        "midp_applied": bool(midp),
    }


def _normal_cdf(x):
    """Standard normal CDF Phi(x) from math.erfc, pure stdlib."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def binomial_normal_approximation(k, n, p0):
    """Large-sample cross-check: z with the continuity correction toward the null mean.

    Returns a dict with the exact keys z and p_value, where
    z = (k_c - n*p0) / sqrt(n*p0*(1 - p0)) with k_c the observed count moved
    half a step toward the null mean, and p_value the two-sided normal tail
    2 * Phi(-abs(z)). Raises ValueError for a non-integer or out-of-range k,
    n below 1, or p0 at or outside (0, 1).
    """
    n = _require_trials(n)
    k = _require_count(k, n)
    p0 = _as_probability(p0, "p0")
    mean = n * p0
    sd = math.sqrt(n * p0 * (1.0 - p0))
    if k < mean:
        corrected = k + 0.5
    elif k > mean:
        corrected = k - 0.5
    else:
        corrected = float(k)
    z = (corrected - mean) / sd
    p_value = 2.0 * _normal_cdf(-abs(z))
    return {"z": z, "p_value": p_value}


def small_count_recommendation(n, p0):
    """Recommend the exact test when the minimum expected count under the null is small.

    Returns a dict with the exact keys min_expected = n * min(p0, 1 - p0)
    and verdict: "exact-test-recommended" when min_expected falls below 5,
    else "normal-approximation-adequate". Raises ValueError for n below 1 or
    p0 at or outside (0, 1).
    """
    n = _require_trials(n)
    p0 = _as_probability(p0, "p0")
    min_expected = n * min(p0, 1.0 - p0)
    if min_expected < 5.0:
        verdict = "exact-test-recommended"
    else:
        verdict = "normal-approximation-adequate"
    return {"min_expected": min_expected, "verdict": verdict}
