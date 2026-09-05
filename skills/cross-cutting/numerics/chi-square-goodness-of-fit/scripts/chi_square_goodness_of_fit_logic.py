"""Chi-square goodness-of-fit logic for the AeroSkills leaf
skills/cross-cutting/numerics/chi-square-goodness-of-fit.

Pure Python stdlib and fully self-contained: the one-tailed p-value is
evaluated from this module's own regularized lower incomplete gamma,
with the series branch for x < a + 1 and the continued-fraction branch
otherwise. No sibling modules are imported.
"""

import math

# Module constants for the incomplete gamma evaluation.
ITMAX = 200        # maximum iterations, gamma series and continued fraction
EPS = 3.0e-12      # relative convergence tolerance for both branches
FPMIN = 1.0e-300   # floor guard for the Lentz continued-fraction recursion

DEFAULT_ALPHA = 0.05  # significance level used when the caller omits alpha


def _validate_counts(observed, expected):
    """Reject malformed category-count inputs before any arithmetic.

    Raises ValueError when the lengths differ, when fewer than two
    categories are given, when any observed count is negative or
    non-finite, or when any expected count is not strictly positive and
    finite.
    """
    if len(observed) != len(expected):
        raise ValueError(
            "observed and expected must have the same number of categories")
    if len(observed) < 2:
        raise ValueError("at least two categories are required")
    for value in observed:
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("observed counts must be finite and non-negative")
    for value in expected:
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("expected counts must be finite and positive")


def chi_square_gof_statistic(observed, expected):
    """Return the chi-square goodness-of-fit statistic.

    statistic = sum over the categories of (O_i - E_i)^2 / E_i, with O_i
    the observed count and E_i the expected count of category i. The
    statistic is exactly 0 when every observed count equals its expected
    count. Inputs are validated by _validate_counts.
    """
    _validate_counts(observed, expected)
    statistic = 0.0
    for obs, exp in zip(observed, expected):
        gap = obs - exp
        statistic += (gap * gap) / exp
    return statistic


def _gamma_series(a, x):
    """Regularized lower incomplete gamma P(a, x) by the power series.

    Convergent for x < a + 1; returns P = x^a e^-x / Gamma(a) times the
    series sum over rising a. This is the standard series evaluation of
    the lower tail.
    """
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(ITMAX):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * EPS:
            break
    factor = math.exp(-x + a * math.log(x) - math.lgamma(a))
    return total * factor


def _gamma_continued_fraction(a, x):
    """Complement Q(a, x) = 1 - P(a, x) by the Lentz continued fraction.

    Convergent for x >= a + 1; evaluates the upper-tail value directly so
    that very small survival probabilities keep their precision instead of
    being lost in a 1 - P subtraction.
    """
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, ITMAX):
        an = -float(i) * (float(i) - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    factor = math.exp(-x + a * math.log(x) - math.lgamma(a))
    return factor * h


def regularized_lower_incomplete_gamma(a, x):
    """Return the regularized lower incomplete gamma P(a, x).

    Uses the power-series branch when x < a + 1 and the complement
    continued-fraction branch otherwise, so both the lower and the upper
    tail keep full precision across the whole domain. P(1, 1) equals
    1 - e^-1 and P(0.5, x) equals erf(sqrt(x)) as closed-form anchors.
    """
    if a <= 0.0 or not math.isfinite(a):
        raise ValueError("shape a must be finite and positive")
    if x < 0.0 or not math.isfinite(x):
        raise ValueError("argument x must be finite and non-negative")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gamma_series(a, x)
    return 1.0 - _gamma_continued_fraction(a, x)


def goodness_of_fit_p_value(statistic, degrees_freedom):
    """Return the one-tailed chi-square survival probability.

    p = P(chi2_df > statistic) = 1 - P(df/2, statistic/2), evaluated with
    the series branch when x = statistic/2 lies below a + 1 = df/2 + 1 and
    with the continued-fraction complement otherwise. A zero statistic
    gives p = 1.0 exactly.
    """
    if not math.isfinite(statistic) or statistic < 0.0:
        raise ValueError("statistic must be finite and non-negative")
    if not math.isfinite(degrees_freedom) or degrees_freedom < 1.0:
        raise ValueError("degrees of freedom must be finite and at least 1")
    if statistic == 0.0:
        return 1.0
    a = degrees_freedom / 2.0
    x = statistic / 2.0
    if x >= a + 1.0:
        return _gamma_continued_fraction(a, x)
    return 1.0 - _gamma_series(a, x)


def merge_small_expected_categories(observed, expected):
    """Fold categories whose expected count is below 1 into a neighbor.

    Each deficient category is merged with the next category, or with the
    previous category when it is the final one, summing both the observed
    and the expected counts. Merging repeats until every expected count is
    at least 1; fewer than two surviving categories raises ValueError.
    """
    _validate_counts(observed, expected)
    merged_obs = list(observed)
    merged_exp = list(expected)
    while len(merged_obs) > 1:
        deficient = None
        for index, exp in enumerate(merged_exp):
            if exp < 1.0:
                deficient = index
                break
        if deficient is None:
            break
        if deficient == len(merged_obs) - 1:
            partner = deficient - 1
        else:
            partner = deficient + 1
        low = min(deficient, partner)
        high = max(deficient, partner)
        merged_obs[low] = merged_obs[low] + merged_obs[high]
        merged_exp[low] = merged_exp[low] + merged_exp[high]
        del merged_obs[high]
        del merged_exp[high]
    if len(merged_obs) < 2:
        raise ValueError(
            "fewer than two categories remain after merging small expected counts")
    return merged_obs, merged_exp


def chi_square_goodness_of_fit(observed, expected, alpha=DEFAULT_ALPHA,
                               estimated_parameters=0,
                               merge_small_expected=False):
    """Run the full goodness-of-fit test and return the fit report.

    Report dict keys: statistic, df, p_value and verdict, with df = k - 1
    - estimated_parameters for k categories after any merging, and verdict
    reject when p_value is at or below alpha, fail-to-reject otherwise.
    """
    if not math.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie strictly between 0 and 1")
    if estimated_parameters < 0:
        raise ValueError("estimated_parameters must be non-negative")
    counts_observed = observed
    counts_expected = expected
    if merge_small_expected:
        (counts_observed,
         counts_expected) = merge_small_expected_categories(observed, expected)
    statistic = chi_square_gof_statistic(counts_observed, counts_expected)
    df = len(counts_expected) - 1 - estimated_parameters
    if df < 1:
        raise ValueError(
            "degrees of freedom below 1 after subtracting estimated parameters")
    p_value = goodness_of_fit_p_value(statistic, df)
    verdict = "reject" if p_value <= alpha else "fail-to-reject"
    return {"statistic": statistic, "df": df, "p_value": p_value,
            "verdict": verdict}
