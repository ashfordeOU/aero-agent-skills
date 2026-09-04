"""Rank-based (nonparametric) hypothesis tests for location (pure stdlib).

Implements the distribution-free location tests that remain valid when
the normality assumption of the parametric sibling fails:

- Wilcoxon rank-sum test (Mann-Whitney U) for two independent samples.
- Wilcoxon signed-rank test for paired data.
- Sign test for paired data.

Each test returns the exact rank sums (average ranks for ties), the
normal-approximation z statistic with the 0.5 continuity correction
toward zero, the two-sided p-value from the standard normal CDF via
math.erf, and the reject/accept verdict at a chosen alpha. Everything is
deterministic and offline; no external statistics package is used.

Conventions (stated):
- U = R1 - n1 (n1 + 1) / 2 with sample 1 as the x sample, matching the
  worked example; the equivalent other orientation is n1 n2 +
  n1 (n1 + 1) / 2 - R1.
- Signed-rank W = (sum of ranks of positive differences) minus (sum of
  ranks of negative differences).
- Continuity correction shifts the statistic 0.5 toward zero before
  dividing by the standard error.
"""

import math

# Module constants.
ALPHA = 0.05
CC = 0.5

TEST_RANK_SUM = "rank-sum"
TEST_SIGNED_RANK = "signed-rank"
TEST_SIGN = "sign"


def _normal_cdf(z):
    """Standard normal CDF Phi(z) = 0.5 (1 + erf(z / sqrt(2)))."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _two_sided_p(z):
    """Two-sided p-value 2 * (1 - Phi(|z|)), clipped to at most 1.0."""
    return min(2.0 * (1.0 - _normal_cdf(abs(z))), 1.0)


def _check_alpha(alpha):
    """Reject significance levels outside the open interval (0, 1)."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie in (0, 1)")


def _rank_values(values):
    """Average ranks of values; tied values share the mean of their positions."""
    ordered = sorted(values)
    n = len(ordered)
    avg_rank = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1] == ordered[i]:
            j += 1
        avg_rank[ordered[i]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return [avg_rank[v] for v in values]


def _correct_toward_zero(diff):
    """Apply the 0.5 continuity correction toward zero."""
    if diff > 0.0:
        return diff - CC
    if diff < 0.0:
        return diff + CC
    return 0.0


def wilcoxon_rank_sum(x, y, alpha=ALPHA):
    """Wilcoxon rank-sum (Mann-Whitney U) test on two independent samples.

    Returns {n1, n2, r1, u, mu_u, sd_u, z, p_value, reject}. Ties get
    average ranks; z uses the continuity correction toward zero.
    """
    if len(x) < 2 or len(y) < 2:
        raise ValueError("each sample needs at least 2 observations")
    _check_alpha(alpha)
    n1 = len(x)
    n2 = len(y)
    ranks = _rank_values(list(x) + list(y))
    r1 = float(sum(ranks[:n1]))
    u = r1 - n1 * (n1 + 1) / 2.0
    mu_u = n1 * n2 / 2.0
    sd_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    z = _correct_toward_zero(u - mu_u) / sd_u
    p_value = _two_sided_p(z)
    return {
        "n1": n1,
        "n2": n2,
        "r1": r1,
        "u": u,
        "mu_u": mu_u,
        "sd_u": sd_u,
        "z": z,
        "p_value": p_value,
        "reject": p_value <= alpha,
    }


def wilcoxon_signed_rank(x, y, alpha=ALPHA):
    """Wilcoxon signed-rank test on paired samples.

    Returns {n, w, sd_w, z, p_value, reject}. Zero differences are
    dropped; ties in absolute difference get average ranks. W is the
    sum of signed ranks (positive minus negative).
    """
    if len(x) != len(y):
        raise ValueError("paired samples must have equal length")
    _check_alpha(alpha)
    diffs = [float(a) - float(b) for a, b in zip(x, y) if a != b]
    if len(diffs) < 2:
        raise ValueError("need at least 2 nonzero paired differences")
    n = len(diffs)
    ranks = _rank_values([abs(d) for d in diffs])
    w = float(sum(r if d > 0.0 else -r for d, r in zip(diffs, ranks)))
    sd_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 6.0)
    z = _correct_toward_zero(w) / sd_w
    p_value = _two_sided_p(z)
    return {
        "n": n,
        "w": w,
        "sd_w": sd_w,
        "z": z,
        "p_value": p_value,
        "reject": p_value <= alpha,
    }


def sign_test(x, y, alpha=ALPHA):
    """Sign test on paired samples (binomial normal approximation).

    Returns {n_pos, n_neg, n, z, p_value, reject}. Only the signs of
    nonzero differences count; z uses the continuity correction toward
    zero on (n_pos - n / 2) with standard error sqrt(n / 4).
    """
    if len(x) != len(y):
        raise ValueError("paired samples must have equal length")
    _check_alpha(alpha)
    n_pos = sum(1 for a, b in zip(x, y) if a > b)
    n_neg = sum(1 for a, b in zip(x, y) if a < b)
    n = n_pos + n_neg
    if n == 0:
        raise ValueError("need at least one nonzero paired difference")
    sd = math.sqrt(n / 4.0)
    z = _correct_toward_zero(n_pos - n / 2.0) / sd
    p_value = _two_sided_p(z)
    return {
        "n_pos": n_pos,
        "n_neg": n_neg,
        "n": n,
        "z": z,
        "p_value": p_value,
        "reject": p_value <= alpha,
    }


def rank_test_summary(test, x, y, alpha=ALPHA):
    """Dispatch to one of the three rank tests by name.

    test is "rank-sum", "signed-rank" or "sign"; the chosen test's dict
    is returned. Unknown test names raise ValueError.
    """
    if test == TEST_RANK_SUM:
        return wilcoxon_rank_sum(x, y, alpha)
    if test == TEST_SIGNED_RANK:
        return wilcoxon_signed_rank(x, y, alpha)
    if test == TEST_SIGN:
        return sign_test(x, y, alpha)
    raise ValueError("unknown rank test %r: use 'rank-sum', 'signed-rank' or 'sign'" % test)
