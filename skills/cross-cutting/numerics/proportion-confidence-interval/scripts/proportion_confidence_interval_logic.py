"""Proportion confidence interval logic (pure stdlib).

Implements confidence intervals for a binomial proportion from attribute
data: the Wilson score interval, its continuity-corrected variant, the
exact Clopper-Pearson interval (by inverting the regularized incomplete
beta), and the normal-approximation interval for the difference of two
proportions. All functions are deterministic and depend only on math.

Conventions: k successes in n trials, confidence level cl in (0, 1)
(default 0.95), z = normal_quantile((1 + cl) / 2) computed in-leaf.
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

_BISECT_TOL = 1e-10
_BISECT_MAX_ITER = 200


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


def _check_proportion_inputs(k, n, cl):
    """Reject non-physical proportion inputs with ValueError."""
    if n <= 0:
        raise ValueError("n must be positive")
    if k < 0 or k > n:
        raise ValueError("k must lie in [0, n]")
    if not (0.0 < cl < 1.0):
        raise ValueError("cl must lie strictly inside (0, 1)")


def _z_value(cl):
    """Two-sided normal quantile for confidence level cl."""
    return normal_quantile(0.5 * (1.0 + cl))


_PLOW = 0.02425
_PHIGH = 1.0 - _PLOW


def normal_quantile(p):
    """Inverse standard normal CDF at p in (0, 1) (Acklam, refined).

    Deterministic in-leaf quantile: 1.959964 for p = 0.975 (the 95%
    two-sided level used across this leaf). Acklam rational regions for
    the tails and the central band, then one Halley refinement against
    the normal CDF via math.erfc.
    """
    if not (0.0 < p < 1.0):
        raise ValueError("p must lie strictly inside (0, 1)")
    if p == 0.5:
        return 0.0
    if p < _PLOW:
        # Lower tail region.
        q = math.sqrt(-2.0 * math.log(p))
        x = _acklam_tail(q)
    elif p <= _PHIGH:
        # Central band: q = p - 0.5, r = q * q.
        q = p - 0.5
        r = q * q
        num = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4])
               * r + _A[5]) * q
        den = (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
        x = num / den
    else:
        # Upper tail region.
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -_acklam_tail(q)
    # One Halley refinement step: solve Phi(x) = p.
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(0.5 * x * x)
    return x - u / (1.0 + 0.5 * x * u)


def _acklam_tail(q):
    """Acklam tail-region rational approximation in q = sqrt(-2 ln(tail))."""
    num = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4])
           * q + _C[5])
    den = ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    return num / den


def wilson_score_interval(k, n, cl=0.95):
    """Wilson score interval dict {lower, upper, width} for k/n at level cl."""
    _check_proportion_inputs(k, n, cl)
    phat = k / n
    z = _z_value(cl)
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half_width = z * math.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) / denom
    if k == 0:
        lower = 0.0
    else:
        lower = max(0.0, center - half_width)
    if k == n:
        upper = 1.0
    else:
        upper = min(1.0, center + half_width)
    return {"lower": lower, "upper": upper, "width": upper - lower}


def wilson_score_cc_interval(k, n, cl=0.95):
    """Continuity-corrected Wilson interval (Newcombe form).

    Endpoints follow the published convention: k = 0 forces lower = 0 and
    k = n forces upper = 1; results are clamped to [0, 1].
    """
    _check_proportion_inputs(k, n, cl)
    z = _z_value(cl)
    z2 = z * z
    if k == 0:
        lower = 0.0
    else:
        radicand = z2 - 2.0 - 1.0 / n + 4.0 * k * (n - k + 1) / n
        lower = (2.0 * k + z2 - 1.0 - z * math.sqrt(max(0.0, radicand))) / (
            2.0 * (n + z2)
        )
    if k == n:
        upper = 1.0
    else:
        radicand = z2 + 2.0 - 1.0 / n + 4.0 * k * (n - k - 1) / n
        upper = (2.0 * k + z2 + 1.0 + z * math.sqrt(max(0.0, radicand))) / (
            2.0 * (n + z2)
        )
    lower = max(0.0, min(1.0, lower))
    upper = max(0.0, min(1.0, upper))
    return {"lower": lower, "upper": upper, "width": upper - lower}


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta (Lentz method)."""
    max_iter = 200
    eps = 3.0e-14
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1.0e-30:
        d = 1.0e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1.0e-30:
            d = 1.0e-30
        c = 1.0 + aa / c
        if abs(c) < 1.0e-30:
            c = 1.0e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1.0e-30:
            d = 1.0e-30
        c = 1.0 + aa / c
        if abs(c) < 1.0e-30:
            c = 1.0e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def regularized_incomplete_beta(a, b, x):
    """Regularized incomplete beta I_x(a, b) for a, b > 0, x in [0, 1].

    Uses the symmetry transform: below the crossover (a + 1) / (a + b + 2)
    the continued fraction runs as betacf(a, b, x) / a; at or above it the
    result is 1 - bt * betacf(b, a, 1 - x) / b. A naive single-sided
    continued fraction diverges near the upper end and breaks the exact
    Clopper-Pearson inversion, so the transform is mandatory.
    """
    if a <= 0.0 or b <= 0.0:
        raise ValueError("a and b must be positive")
    if not (0.0 <= x <= 1.0):
        raise ValueError("x must lie in [0, 1]")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    ln_bt = (
        _gammaln(a + b)
        - _gammaln(a)
        - _gammaln(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    bt = math.exp(ln_bt)
    crossover = (a + 1.0) / (a + b + 2.0)
    if x < crossover:
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def beta_quantile(a, b, q):
    """Inverse regularized incomplete beta: x with I_x(a, b) = q.

    Bisection on the monotone CDF to absolute tolerance 1e-10.
    """
    if a <= 0.0 or b <= 0.0:
        raise ValueError("a and b must be positive")
    if not (0.0 < q < 1.0):
        raise ValueError("q must lie strictly inside (0, 1)")
    lo, hi = 0.0, 1.0
    for _ in range(_BISECT_MAX_ITER):
        mid = 0.5 * (lo + hi)
        if hi - lo < _BISECT_TOL:
            break
        if regularized_incomplete_beta(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_interval(k, n, cl=0.95):
    """Exact Clopper-Pearson interval dict {lower, upper, width}.

    Lower inverts I_p(k, n - k + 1) = alpha / 2 and upper inverts
    I_p(k + 1, n - k) = 1 - alpha / 2, with the endpoint handling
    k = 0 -> lower 0 and k = n -> upper 1.
    """
    _check_proportion_inputs(k, n, cl)
    alpha = 1.0 - cl
    if k == 0:
        lower = 0.0
    else:
        lower = beta_quantile(k, n - k + 1, alpha / 2.0)
    if k == n:
        upper = 1.0
    else:
        upper = beta_quantile(k + 1, n - k, 1.0 - alpha / 2.0)
    return {"lower": lower, "upper": upper, "width": upper - lower}


def two_proportion_diff_interval(k1, n1, k2, n2, cl=0.95):
    """Normal-approximation interval for p1 - p2 (attribute data).

    diff = phat1 - phat2 with standard error
    sqrt(phat1 * (1 - phat1) / n1 + phat2 * (1 - phat2) / n2); width is the
    margin z * se of the worked example, so lower = diff - width and
    upper = diff + width by construction.
    """
    _check_proportion_inputs(k1, n1, cl)
    _check_proportion_inputs(k2, n2, cl)
    p1 = k1 / n1
    p2 = k2 / n2
    diff = p1 - p2
    se = math.sqrt(p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2)
    width = _z_value(cl) * se
    lower = diff - width
    upper = diff + width
    return {"diff": diff, "lower": lower, "upper": upper, "width": width}
