"""Poisson confidence interval logic (pure stdlib).

Implements exact (Garwood) and normal-approximation confidence intervals
for a Poisson rate from a total event count k over an exposure T. The
exact bounds come from chi-square quantiles chi2(df, q) evaluated
entirely in-leaf: the regularized lower incomplete gamma function is
computed by a series below the crossover and a Lentz continued fraction
above it, and the quantile inverts that CDF by bisection to 1e-9. The
normal bounds use the in-leaf Acklam normal quantile with one Halley
refinement.

Conventions: k events (defects, failures) over exposure T (cycles,
hours, inspection units), confidence level cl in (0, 1) (default
0.95), alpha = 1 - cl. Exact Garwood bounds per the chi-square
relation are lower = chi2(2k, alpha / 2) / (2T) and
upper = chi2(2k + 2, 1 - alpha / 2) / (2T); a zero count forces the
lower bound to 0 because the df = 0 quantile is degenerate. Normal
approximation bounds are (k +/- z * sqrt(k)) / T with
z = normal_quantile((1 + cl) / 2). All functions are deterministic
and depend only on math.
"""

import math

# Lanczos approximation coefficients for log-gamma (g = 7, standard set).
_LANCZOS_G = 7
_LANCZOS_C = [
    0.99999999999980993,
    676.5203681218851,
    -1259.1392167224028,
    771.32342877765313,
    -176.61502916214059,
    12.507343278686905,
    -0.13857109526572012,
    9.9843695780195716e-6,
    1.5056327351493116e-7,
]

# Series and continued-fraction control parameters.
_GAMMA_EPS = 1e-13
_GAMMA_FPMIN = 1e-300
_GAMMA_ITMAX = 10000
_QUANTILE_TOL = 1e-9
_QUANTILE_MAX_ITER = 500

# Acklam rational approximation coefficients for the normal quantile.
_A = [
    -3.969683028665376e1,
    2.209460984245205e2,
    -2.759285104469687e2,
    1.38357751867269e2,
    -3.066479806614716e1,
    2.506628277459239,
]
_B = [
    -5.447609879822406e1,
    1.615858368580409e2,
    -1.556989798598866e2,
    6.680131188771972e1,
    -1.328068155288572e1,
]
_C = [
    -7.784894002430293e-3,
    -3.223964580411365e-1,
    -2.400758277161838,
    -2.549732539343734,
    4.374664141464968,
    2.938163982698783,
]
_D = [
    7.784695709041462e-3,
    3.224671290700398e-1,
    2.445134137142996,
    3.754408661907416,
]

_PLOW = 0.02425
_PHIGH = 1.0 - _PLOW


def _gammaln(x):
    """Natural log of the gamma function via Lanczos (x > 0)."""
    if x <= 0.0:
        raise ValueError("gamma argument must be positive")
    x -= 1.0
    series = _LANCZOS_C[0]
    for i in range(1, _LANCZOS_G + 2):
        series += _LANCZOS_C[i] / (x + i)
    t = x + _LANCZOS_G + 0.5
    return 0.5 * math.log(2.0 * math.pi) + (x + 0.5) * math.log(t) - t + math.log(series)


def _series_p(a, x):
    """Regularized lower incomplete gamma P(a, x) by series (x < a + 1)."""
    ap = a
    total = 1.0 / a
    term = total
    for _ in range(_GAMMA_ITMAX):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _GAMMA_EPS:
            break
    return total * math.exp(-x + a * math.log(x) - _gammaln(a))


def _cf_q(a, x):
    """Regularized upper incomplete gamma Q(a, x) by Lentz CF (x >= a + 1)."""
    b = x + 1.0 - a
    c = 1.0 / _GAMMA_FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, _GAMMA_ITMAX):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _GAMMA_FPMIN:
            d = _GAMMA_FPMIN
        c = b + an / c
        if abs(c) < _GAMMA_FPMIN:
            c = _GAMMA_FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _GAMMA_EPS:
            break
    return math.exp(-x + a * math.log(x) - _gammaln(a)) * h


def _reg_lower_incomplete_gamma(a, x):
    """Regularized lower incomplete gamma P(a, x), series or CF branch."""
    if a <= 0.0:
        raise ValueError("gamma shape must be positive")
    if x < 0.0:
        raise ValueError("gamma argument must be non-negative")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _series_p(a, x)
    return 1.0 - _cf_q(a, x)


def _chi_square_cdf(x, df):
    """CDF of the chi-square law at x >= 0: P(df / 2, x / 2)."""
    if x < 0.0:
        raise ValueError("chi-square argument must be non-negative")
    return _reg_lower_incomplete_gamma(df / 2.0, x / 2.0)


def _as_count(value):
    """Coerce count to a non-negative integer or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("count must be an integer")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("count must be an integer")
    if value < 0:
        raise ValueError("count must be non-negative")
    return int(value)


def _as_exposure(value):
    """Coerce exposure to a positive float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("exposure must be a positive number")
    value = float(value)
    if value <= 0.0:
        raise ValueError("exposure must be positive")
    return value


def _as_level(value):
    """Coerce confidence level to (0, 1) or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence level must be a number")
    value = float(value)
    if not (0.0 < value < 1.0):
        raise ValueError("confidence level must lie strictly inside (0, 1)")
    return value


def _as_df(value):
    """Coerce degrees of freedom to a positive integer or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("df must be a positive integer")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("df must be a positive integer")
    if value < 1:
        raise ValueError("df must be a positive integer")
    return int(value)


def chi_square_quantile(df, q):
    """q quantile of the chi-square law with df degrees of freedom.

    Inverts the documented chi-square CDF (the regularized lower
    incomplete gamma survival function P(df / 2, x / 2)) by bisection on
    an expanding bracket to tolerance 1e-9. Deterministic, pure stdlib.
    """
    df = _as_df(df)
    if not (0.0 < q < 1.0):
        raise ValueError("q must lie strictly inside (0, 1)")
    lo = 0.0
    hi = max(float(df), 1.0)
    while _chi_square_cdf(hi, df) < q:
        hi *= 2.0
    for _ in range(_QUANTILE_MAX_ITER):
        mid = 0.5 * (lo + hi)
        if hi - lo < _QUANTILE_TOL:
            break
        if _chi_square_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _acklam_tail(q):
    """Acklam tail-region rational for the normal quantile."""
    return (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
        (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
    )


def normal_quantile(p):
    """Inverse standard normal CDF at p in (0, 1) (Acklam, refined).

    Deterministic in-leaf quantile: 1.959964 for p = 0.975, the 95%
    two-sided z value used by the normal-approximation interval.
    """
    if not (0.0 < p < 1.0):
        raise ValueError("p must lie strictly inside (0, 1)")
    if p == 0.5:
        return 0.0
    if p < _PLOW:
        q = math.sqrt(-2.0 * math.log(p))
        x = _acklam_tail(q)
    elif p <= _PHIGH:
        q = p - 0.5
        r = q * q
        num = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q
        den = (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
        x = num / den
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -_acklam_tail(q)
    # One Halley refinement against the normal CDF via math.erfc.
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


def poisson_rate(count, exposure):
    """Rate estimate lambda_hat = k / T for k events over exposure T."""
    k = _as_count(count)
    t = _as_exposure(exposure)
    return k / t


def poisson_confidence_interval(count, exposure, confidence_level=0.95):
    """Exact Garwood Poisson rate interval from the chi-square relation.

    Returns {"rate", "lower", "upper", "method"} with method
    "exact-poisson": lower = chi2(2k, alpha / 2) / (2T) and
    upper = chi2(2k + 2, 1 - alpha / 2) / (2T). A zero count gives a
    lower bound of 0.0 because the df = 0 quantile is degenerate.
    """
    k = _as_count(count)
    t = _as_exposure(exposure)
    cl = _as_level(confidence_level)
    alpha = 1.0 - cl
    if k == 0:
        lower = 0.0
    else:
        lower = chi_square_quantile(2 * k, alpha / 2.0) / (2.0 * t)
    upper = chi_square_quantile(2 * k + 2, 1.0 - alpha / 2.0) / (2.0 * t)
    return {"rate": k / t, "lower": lower, "upper": upper, "method": "exact-poisson"}


def normal_approximation_interval(count, exposure, confidence_level=0.95):
    """Normal-approximation Poisson rate interval (k +/- z sqrt(k)) / T.

    Returns {"rate", "lower", "upper", "method"} with method
    "normal-approximation". A zero count forces the lower bound to 0.0
    (the Wald form collapses to the point estimate at the edge).
    """
    k = _as_count(count)
    t = _as_exposure(exposure)
    cl = _as_level(confidence_level)
    z = normal_quantile(0.5 * (1.0 + cl))
    rate = k / t
    half_width = z * math.sqrt(k) / t
    lower = max(0.0, rate - half_width)
    return {"rate": rate, "lower": lower, "upper": rate + half_width, "method": "normal-approximation"}
