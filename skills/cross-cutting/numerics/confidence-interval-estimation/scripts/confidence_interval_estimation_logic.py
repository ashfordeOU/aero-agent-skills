"""Parametric confidence interval estimation, pure stdlib.

Estimates exact small-sample confidence intervals for sample statistics:
the Student t interval for a mean, the pooled or Welch-Satterthwaite
interval for a difference of means, and the chi-square interval for a
variance and standard deviation. Quantile machinery is implemented
in-leaf: the two-sided t quantile comes from bisection on the
regularized incomplete beta relation for the t distribution, and the
chi-square quantile comes from bisection on the lower incomplete gamma
relation P(df/2, x/2). No numpy/scipy, no network, no RNG.

Conventions: level is the two-sided confidence level (0.95 for 95%);
alpha = 1 - level; sample variance uses the n-1 denominator.

Functions:
    t_ppf_two_sided(level, df)
    chi2_ppf(p, df)
    confidence_interval_mean(x, level=0.95)
    confidence_interval_mean_difference(a, b, level=0.95, equal_var=True)
    confidence_interval_variance(x, level=0.95)
    interval_summary(lower, upper, level=0.95, digits=4)
"""

import math

# Module constants for the special-function machinery.
CF_MAX_ITER = 200          # continued fraction iteration cap
CF_EPS = 3e-12             # continued fraction convergence criterion
FPMIN = 1e-300             # underflow floor for Lentz division guards
BISECTION_TOL = 1e-9       # absolute bisection target tolerance
BISECTION_MAX_ITER = 300   # bisection iteration cap
_BETA_A = 0.5              # second beta parameter of the t CDF identity


def _check_level(level):
    """Raise ValueError unless level is a two-sided confidence in (0, 1)."""
    if not isinstance(level, (int, float)):
        raise ValueError("level must be a number in (0, 1)")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must lie in (0, 1), got %r" % (level,))


def _check_df(df):
    """Raise ValueError unless df is a finite value of at least 1."""
    if not isinstance(df, (int, float)):
        raise ValueError("df must be a number")
    df = float(df)
    if df < 1.0 or math.isnan(df) or math.isinf(df):
        raise ValueError("df must be >= 1, got %r" % (df,))


def _check_bounds(lower, upper):
    """Raise ValueError unless the interval bounds are ordered numbers."""
    for bound in (lower, upper):
        if not isinstance(bound, (int, float)):
            raise ValueError("interval bounds must be numbers")
    if float(lower) > float(upper):
        raise ValueError("lower bound exceeds upper bound")


# ---------------------------------------------------------------------------
# Regularized incomplete beta (the t CDF layer, in-leaf).
# ---------------------------------------------------------------------------

def _betacf(a, b, x):
    """Lentz continued fraction for the incomplete beta ratio."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, CF_MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < CF_EPS:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta I_x(a, b) on [0, 1]."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_cdf(t, df):
    """CDF of Student t at t >= 0 via I_x(df/2, 1/2), x = df/(df + t^2)."""
    x = df / (df + t * t)
    return 1.0 - 0.5 * _betai(df / 2.0, _BETA_A, x)


# ---------------------------------------------------------------------------
# Regularized lower incomplete gamma (the chi2 CDF layer, in-leaf).
# ---------------------------------------------------------------------------

def _gammp(a, x):
    """Regularized lower incomplete gamma P(a, x) for a > 0, x >= 0."""
    if x <= 0.0:
        return 0.0
    if x < a + 1.0:
        # Series representation.
        ap = a
        summ = 1.0 / a
        delta = summ
        for _ in range(CF_MAX_ITER):
            ap += 1.0
            delta *= x / ap
            summ += delta
            if abs(delta) < abs(summ) * CF_EPS:
                break
        return summ * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # Continued fraction representation of the complementary function.
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, CF_MAX_ITER + 1):
        an = -i * (i - a)
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
        if abs(delta - 1.0) < CF_EPS:
            break
    return 1.0 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def _chi2_cdf(x, df):
    """CDF of the chi-square distribution at x >= 0: P(df/2, x/2)."""
    return _gammp(df / 2.0, x / 2.0)


def _bisect_invert(cdf, target, df, lo, hi):
    """Bisect cdf(x) = target on [lo, hi] to BISECTION_TOL, return x."""
    flo = cdf(lo, df)
    for _ in range(BISECTION_MAX_ITER):
        mid = 0.5 * (lo + hi)
        if hi - lo <= BISECTION_TOL:
            return mid
        fmid = cdf(mid, df)
        if (fmid - target) * (flo - target) <= 0.0:
            hi = mid
        else:
            lo = mid
            flo = fmid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Public quantile machinery.
# ---------------------------------------------------------------------------

def t_ppf_two_sided(level, df):
    """Two-sided t quantile t_{1-alpha/2, df} for alpha = 1 - level.

    The two-sided quantile q satisfies P(|T| <= q) = level, so the CDF
    target is p = 1 - alpha/2 = (1 + level)/2 and the value is found by
    bisection on the incomplete-beta identity of the t CDF.
    """
    _check_level(level)
    _check_df(df)
    target = 0.5 * (1.0 + float(level))  # p = 1 - alpha/2, in (0.5, 1)
    hi = 1.0
    while _t_cdf(hi, df) < target and hi < 1e12:
        hi *= 2.0
    return _bisect_invert(_t_cdf, target, float(df), 0.0, hi)


def chi2_ppf(p, df):
    """Chi-square quantile: x with P(df/2, x/2) = p, via bisection."""
    if not isinstance(p, (int, float)):
        raise ValueError("p must be a number in [0, 1]")
    p = float(p)
    if p < 0.0 or p > 1.0:
        raise ValueError("p must lie in [0, 1], got %r" % (p,))
    _check_df(df)
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return math.inf
    hi = 1.0
    while _chi2_cdf(hi, df) < p and hi < 1e12:
        hi *= 2.0
    return _bisect_invert(_chi2_cdf, p, float(df), 0.0, hi)


# ---------------------------------------------------------------------------
# Interval builders.
# ---------------------------------------------------------------------------

def _sample_stats(x, name="sample"):
    """Mean, n-1 sample standard deviation and length of a numeric sample."""
    if not isinstance(x, (list, tuple)) or len(x) == 0:
        raise ValueError("%s must be a non-empty sequence" % name)
    if len(x) < 2:
        raise ValueError("%s needs at least 2 observations for an interval"
                         % name)
    n = len(x)
    mean = sum(float(v) for v in x) / n
    var = sum((float(v) - mean) ** 2 for v in x) / (n - 1)
    return mean, math.sqrt(var), n


def confidence_interval_mean(x, level=0.95):
    """t interval for the mean: xbar +/- t_{1-alpha/2, n-1} * s / sqrt(n).

    Returns {mean, se, df, t_quantile, lower, upper}. A degenerate
    constant sample (s = 0) yields the point interval [xbar, xbar].
    """
    _check_level(level)
    mean, s, n = _sample_stats(x)
    df = n - 1
    t_quantile = t_ppf_two_sided(level, df)
    se = s / math.sqrt(n)
    half = t_quantile * se
    return {"mean": mean, "se": se, "df": float(df),
            "t_quantile": t_quantile,
            "lower": mean - half, "upper": mean + half}


def _welch_df(s1, n1, s2, n2):
    """Welch-Satterthwaite degrees of freedom for unequal variances."""
    v1 = s1 * s1 / n1
    v2 = s2 * s2 / n2
    if v1 + v2 == 0.0:
        return 1.0  # degenerate: both samples constant, interval has zero width
    return (v1 + v2) ** 2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1))


def confidence_interval_mean_difference(a, b, level=0.95, equal_var=True):
    """Interval for the difference of means (m1 - m2) +/- t * se.

    equal_var=True uses the pooled standard error with df = n1 + n2 - 2;
    equal_var=False uses the Welch standard error with the
    Welch-Satterthwaite df. Returns {mean_diff, se, df, t_quantile,
    lower, upper}.
    """
    _check_level(level)
    mean_a, s_a, n_a = _sample_stats(a, "a")
    mean_b, s_b, n_b = _sample_stats(b, "b")
    if equal_var:
        sp2 = ((n_a - 1) * s_a * s_a + (n_b - 1) * s_b * s_b) / (n_a + n_b - 2)
        sp = math.sqrt(sp2)
        se = sp * math.sqrt(1.0 / n_a + 1.0 / n_b)
        df = float(n_a + n_b - 2)
    else:
        se = math.sqrt(s_a * s_a / n_a + s_b * s_b / n_b)
        df = _welch_df(s_a, n_a, s_b, n_b)
    t_quantile = t_ppf_two_sided(level, df)
    mean_diff = mean_a - mean_b
    half = t_quantile * se
    return {"mean_diff": mean_diff, "se": se, "df": df,
            "t_quantile": t_quantile,
            "lower": mean_diff - half, "upper": mean_diff + half}


def confidence_interval_variance(x, level=0.95):
    """Chi-square interval for the variance and standard deviation.

    Bounds: [(n-1)s^2 / chi2_{1-alpha/2, n-1},
    (n-1)s^2 / chi2_{alpha/2, n-1}]; sigma bounds are the square roots.
    Returns {variance, df, chi2_lower, chi2_upper, lower, upper,
    sigma_lower, sigma_upper}.
    """
    _check_level(level)
    mean, s, n = _sample_stats(x)
    df = n - 1
    variance = s * s
    alpha = 1.0 - float(level)
    chi2_lower = chi2_ppf(alpha / 2.0, df)
    chi2_upper = chi2_ppf(1.0 - alpha / 2.0, df)
    lower = df * variance / chi2_upper
    upper = df * variance / chi2_lower
    return {"variance": variance, "df": float(df),
            "chi2_lower": chi2_lower, "chi2_upper": chi2_upper,
            "lower": lower, "upper": upper,
            "sigma_lower": math.sqrt(lower), "sigma_upper": math.sqrt(upper)}


def interval_summary(lower, upper=None, level=0.95, digits=4):
    """Compact summary dict for a requested interval.

    Accepts two bound numbers, or a single builder result dict whose
    'lower' and 'upper' keys hold the primary bound pair. For
    confidence_interval_variance the primary pair is the variance
    interval; pass sigma_lower and sigma_upper explicitly for the sigma
    interval. Returns {level, lower, upper, width, summary}.
    """
    if isinstance(lower, dict):
        if upper is not None:
            raise ValueError("pass either a builder dict or bound numbers, "
                             "not both")
        upper = lower["upper"]
        lower = lower["lower"]
    if upper is None:
        raise ValueError("upper bound is required")
    _check_level(level)
    _check_bounds(lower, upper)
    if not isinstance(digits, int) or digits < 0:
        raise ValueError("digits must be a non-negative integer")
    low = round(float(lower), digits)
    high = round(float(upper), digits)
    return {"level": float(level), "lower": low, "upper": high,
            "width": round(high - low, digits),
            "summary": "%g%% CI [%s, %s]" % (
                float(level) * 100.0, low, high)}


if __name__ == "__main__":  # pragma: no cover
    a = [267, 261, 263, 258, 262]
    b = [273, 271, 268, 275, 270]
    print("t(0.975,4) =", t_ppf_two_sided(0.95, 4))
    print("t(0.975,8) =", t_ppf_two_sided(0.95, 8))
    print("chi2(0.025,4) =", chi2_ppf(0.025, 4))
    print("chi2(0.975,4) =", chi2_ppf(0.975, 4))
    print("mean CI a:", confidence_interval_mean(a))
    print("pooled diff CI:", confidence_interval_mean_difference(a, b))
    print("welch diff CI:", confidence_interval_mean_difference(a, b,
                                                                equal_var=False))
    print("variance CI:", confidence_interval_variance(a))
