"""Kruskal-Wallis test logic: distribution-free comparison of k >= 3 groups.

Pure stdlib, deterministic, offline. Self-contained: the chi-square
survival function is built here from the regularized lower incomplete
gamma (series and continued-fraction pair), so this module never imports
sibling numerics leaves. Standard engineering method per the wave-39
engineering spec: merge all observations, assign average ranks for ties,
compute H = (12 / (N (N + 1))) sum(R_i^2 / n_i) - 3 (N + 1), divide by
the ties correction denominator C = 1 - sum((t^3 - t) / (N^3 - N)), and
evaluate the p-value as the chi-square survival with k - 1 degrees of
freedom.

Functions:
    rank_data(values)             average ranks for ties
    kruskal_wallis_h(groups)      uncorrected H statistic
    ties_correction(groups)       ties denominator C (1.0 when no ties)
    kruskal_wallis_p_value(h, k)  chi-square survival P(chi2_(k-1) > h)
    kruskal_wallis_test(groups, alpha)   full report dict
"""

import math

# Convergence tolerances for the incomplete-gamma pair (no magic numbers
# in the statistics: these are numerical-analysis constants only).
_GAMMA_EPS = 1e-14
_GAMMA_ITMAX = 1000
_FPMIN = 1e-300


def _check_finite(value):
    """Raise ValueError unless value is a real finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("observations must be real numbers")
    if not math.isfinite(value):
        raise ValueError("observations must be finite (no nan or inf)")


def rank_data(values):
    """Return the average ranks (midranks) of each observation.

    Equal observations share the arithmetic mean of the integer rank
    positions they occupy in the merged sample; distinct observations
    receive consecutive ranks starting at 1. Values must be finite.
    """
    vals = list(values)
    if not vals:
        return []
    for v in vals:
        _check_finite(v)
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    n = len(vals)
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        average_rank = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = average_rank
        i = j + 1
    return ranks


def _validate_groups(groups):
    """Check the k >= 3, n_i >= 2, finite-value preconditions."""
    if not isinstance(groups, (list, tuple)) or len(groups) == 0:
        raise ValueError("groups must be a non-empty list of samples")
    if len(groups) < 3:
        raise ValueError("kruskal-wallis-test requires at least 3 groups")
    for group in groups:
        if not isinstance(group, (list, tuple)) or len(group) < 2:
            raise ValueError("every group needs at least 2 observations")
        for v in group:
            _check_finite(v)


def kruskal_wallis_h(groups):
    """Compute the uncorrected H statistic on average ranks.

    H = (12 / (N (N + 1))) sum_i(R_i^2 / n_i) - 3 (N + 1), with R_i the
    sum of the average ranks of group i over the merged sample of N
    observations. All-identical data gives H = 0.0 exactly.
    """
    _validate_groups(groups)
    sizes = [len(g) for g in groups]
    total = sum(sizes)
    merged = [v for g in groups for v in g]
    ranks = rank_data(merged)
    rank_sums = []
    offset = 0
    for size in sizes:
        rank_sums.append(sum(ranks[offset:offset + size]))
        offset += size
    h = (12.0 / (total * (total + 1.0))
         * sum(r * r / size for r, size in zip(rank_sums, sizes))
         - 3.0 * (total + 1.0))
    return h


def ties_correction(groups):
    """Return the ties denominator C = 1 - sum((t^3 - t) / (N^3 - N)).

    The sum runs over tie runs of size t in the merged sample of N
    observations; C = 1.0 when there are no ties (t = 1 runs contribute
    zero). The corrected statistic is H / C. C is 0.0 only when every
    observation is equal, where H is 0 and the corrected statistic stays
    0.
    """
    _validate_groups(groups)
    merged = [v for g in groups for v in g]
    total = len(merged)
    if total < 2:
        return 1.0
    ordered = sorted(merged)
    tie_sum = 0.0
    i = 0
    while i < total:
        j = i
        while j + 1 < total and ordered[j + 1] == ordered[i]:
            j += 1
        size = j - i + 1
        if size > 1:
            tie_sum += size ** 3 - size
        i = j + 1
    if tie_sum == 0.0:
        return 1.0
    return 1.0 - tie_sum / (total ** 3 - total)


def _regularized_lower_gamma(shape, x):
    """Regularized lower incomplete gamma P(shape, x) by series.

    Converges quickly for x < shape + 1; the upper-tail branch below
    handles larger x with the continued fraction.
    """
    if x == 0.0:
        return 0.0
    term = 1.0 / shape
    total = term
    ap = shape
    for _ in range(_GAMMA_ITMAX):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _GAMMA_EPS:
            break
    return total * math.exp(-x + shape * math.log(x) - math.lgamma(shape))


def _regularized_upper_gamma(shape, x):
    """Regularized upper incomplete gamma Q(shape, x) = 1 - P(shape, x).

    Modified Lentz continued-fraction evaluation, accurate for large x.
    """
    b = x + 1.0 - shape
    c = 1.0 / _FPMIN
    d = 1.0 / b
    fraction = d
    for i in range(1, _GAMMA_ITMAX):
        an = -i * (i - shape)
        b += 2.0
        d = an * d + b
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = b + an / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) < _GAMMA_EPS:
            break
    return math.exp(-x + shape * math.log(x) - math.lgamma(shape)) * fraction


def _chi_square_survival(x, degrees_of_freedom):
    """Survival P(chi2_df > x) = Q(df / 2, x / 2)."""
    if x <= 0.0:
        return 1.0
    shape = degrees_of_freedom / 2.0
    y = x / 2.0
    if y < shape + 1.0:
        return 1.0 - _regularized_lower_gamma(shape, y)
    return _regularized_upper_gamma(shape, y)


def kruskal_wallis_p_value(h_corrected, group_count):
    """p-value P(chi2_(k-1) > h_corrected) for k >= 3 groups."""
    _check_finite(h_corrected)
    if h_corrected < 0.0:
        raise ValueError("h_corrected must be non-negative")
    if not isinstance(group_count, int) or isinstance(group_count, bool):
        raise ValueError("group_count must be an integer")
    if group_count < 3:
        raise ValueError("group_count must be at least 3")
    return _chi_square_survival(h_corrected, group_count - 1)


def kruskal_wallis_test(groups, alpha=0.05):
    """Full Kruskal-Wallis report dict for groups at significance alpha.

    Keys: h (uncorrected), h_corrected (ties-corrected H / C), df,
    p_value, verdict ("reject" or "fail to reject"), group_rank_sums
    (per-group sums of average ranks, in input order).
    """
    _check_finite(alpha)
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie in the open interval (0, 1)")
    h = kruskal_wallis_h(groups)
    sizes = [len(g) for g in groups]
    total = sum(sizes)
    ranks = rank_data([v for g in groups for v in g])
    group_rank_sums = []
    offset = 0
    for size in sizes:
        group_rank_sums.append(sum(ranks[offset:offset + size]))
        offset += size
    correction = ties_correction(groups)
    if correction == 0.0:
        h_corrected = 0.0
    else:
        h_corrected = h / correction
    degrees_of_freedom = len(groups) - 1
    p_value = kruskal_wallis_p_value(h_corrected, len(groups))
    verdict = "reject" if p_value <= alpha else "fail to reject"
    return {
        "h": h,
        "h_corrected": h_corrected,
        "df": degrees_of_freedom,
        "p_value": p_value,
        "verdict": verdict,
        "group_rank_sums": group_rank_sums,
    }
