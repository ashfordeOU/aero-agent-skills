"""Statistical power analysis logic (pure stdlib).

Implements minimum-sample-size planning and achieved-power evaluation for
planned comparisons: the two-sample pooled z-based comparison, the
one-sample mean comparison and the one-sample proportion comparison, plus
the achieved power of the two-sample design at a rounded per-group sample
size. All functions are deterministic and depend only on math.

Conventions: significance level alpha in (0, 1) (default 0.05, two-sided),
target power in (0, 1) (default 0.8, so the type II error rate is 0.2),
effect size delta > 0 for a mean shift or a proportion gap, population
standard deviation sigma > 0. The required sample size is rounded up to
whole groups with math.ceil. The achieved power is evaluated with the
standard normal survival function 1 - Phi.
"""

import math

# Acklam rational approximation coefficients for the standard normal
# quantile (published set, same as the sibling proportion-confidence-
# interval leaf uses in-leaf).
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

_SQRT2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _acklam_tail(t):
    """Acklam tail rational approximation at t = sqrt(-2 ln(p)) or
    sqrt(-2 ln(1 - p)); returns the signed tail value num / den."""
    num = (((((_C[0] * t + _C[1]) * t + _C[2]) * t + _C[3]) * t + _C[4]) * t + _C[5])
    den = ((((_D[0] * t + _D[1]) * t + _D[2]) * t + _D[3]) * t + 1.0)
    return num / den


def normal_quantile(q):
    """Standard normal quantile z_q via the Acklam rational approximation.

    Returns the value z with Phi(z) = q for q strictly inside (0, 1).
    Raises ValueError when q lies outside the open unit interval.
    """
    if not (0.0 < q < 1.0):
        raise ValueError("quantile probability must lie strictly between 0 and 1")
    if q == 0.5:
        return 0.0
    low = 0.02425
    high = 1.0 - low
    if q < low:
        x = _acklam_tail(math.sqrt(-2.0 * math.log(q)))
    elif q <= high:
        r = (q - 0.5) * (q - 0.5)
        num = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5])
        num *= (q - 0.5)
        den = (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
        x = num / den
    else:
        x = -_acklam_tail(math.sqrt(-2.0 * math.log(1.0 - q)))
    # One Halley-style refinement step on the error e = Phi(x) - q.
    e = 0.5 * math.erfc(-x / _SQRT2) - q
    u = e * _SQRT_2PI * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


def normal_survival(z):
    """Standard normal survival 1 - Phi(z) = erfc(z / sqrt(2)) / 2."""
    return 0.5 * math.erfc(z / _SQRT2)


def _critical_two_sided(alpha):
    """z_(1-alpha/2), the two-sided critical quantile at level alpha."""
    return normal_quantile(1.0 - alpha / 2.0)


def _validate_levels(alpha, power):
    """Reject significance or power values outside (0, 1) and power at or
    above 1 - alpha, which would demand an infinite sample size."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("significance level alpha must lie strictly between 0 and 1")
    if not (0.0 < power < 1.0):
        raise ValueError("target power must lie strictly between 0 and 1")
    if power >= 1.0 - alpha:
        raise ValueError("target power must stay below 1 - alpha for a finite sample size")


def sample_size_two_sample_pooled(delta, sigma, alpha=0.05, power=0.8):
    """Minimum per-group sample size n for a two-sample pooled comparison.

    n = ceil(2 * sigma^2 * (z_(1-alpha/2) + z_(1-beta))^2 / delta^2),
    with beta = 1 - power and delta the effect size (mean shift). Raises
    ValueError for delta <= 0, sigma <= 0, invalid alpha or power.
    """
    if delta <= 0.0:
        raise ValueError("effect size delta must be positive")
    if sigma <= 0.0:
        raise ValueError("standard deviation sigma must be positive")
    _validate_levels(alpha, power)
    required = 2.0 * sigma * sigma
    required *= (_critical_two_sided(alpha) + _critical_power(power)) ** 2
    required /= delta * delta
    return math.ceil(required)


def _critical_power(power):
    """z_(1-beta) = z_power, the quantile at the target power."""
    return normal_quantile(power)


def sample_size_one_sample(delta, sigma, alpha=0.05, power=0.8):
    """Minimum sample size n for a one-sample mean comparison.

    n = ceil(sigma^2 * (z_(1-alpha/2) + z_(1-beta))^2 / delta^2), exactly
    half the two-sample pooled requirement at identical inputs before the
    ceiling is applied. Raises ValueError for delta <= 0, sigma <= 0,
    invalid alpha or power.
    """
    if delta <= 0.0:
        raise ValueError("effect size delta must be positive")
    if sigma <= 0.0:
        raise ValueError("standard deviation sigma must be positive")
    _validate_levels(alpha, power)
    required = sigma * sigma
    required *= (_critical_two_sided(alpha) + _critical_power(power)) ** 2
    required /= delta * delta
    return math.ceil(required)


def sample_size_one_sample_proportion(p0, p1, alpha=0.05, power=0.8):
    """Minimum sample size n for a one-sample proportion comparison.

    n = ceil((z_(1-alpha/2) * sqrt(p0*(1-p0)) + z_(1-beta) *
    sqrt(p1*(1-p1)))^2 / (p1 - p0)^2), with p0 the hypothesized proportion
    under the null and p1 the proportion under the alternative. Raises
    ValueError when p0 or p1 lies outside (0, 1) or when p1 == p0.
    """
    if not (0.0 < p0 < 1.0):
        raise ValueError("null proportion p0 must lie strictly between 0 and 1")
    if not (0.0 < p1 < 1.0):
        raise ValueError("alternative proportion p1 must lie strictly between 0 and 1")
    if p1 == p0:
        raise ValueError("alternative proportion p1 must differ from the null proportion p0")
    _validate_levels(alpha, power)
    se0 = math.sqrt(p0 * (1.0 - p0))
    se1 = math.sqrt(p1 * (1.0 - p1))
    numerator = _critical_two_sided(alpha) * se0 + _critical_power(power) * se1
    gap = p1 - p0
    required = numerator * numerator / (gap * gap)
    return math.ceil(required)


def achieved_power_two_sample_pooled(n_per_group, delta, sigma, alpha=0.05):
    """Achieved power of a two-sample pooled design at n per group.

    power = 1 - Phi(z_(1-alpha/2) - delta * sqrt(n / (2 * sigma^2))),
    evaluated with the standard normal survival function. Raises ValueError
    for n_per_group < 2, delta <= 0, sigma <= 0 or invalid alpha.
    """
    if n_per_group < 2:
        raise ValueError("per-group sample size must be at least 2")
    if delta <= 0.0:
        raise ValueError("effect size delta must be positive")
    if sigma <= 0.0:
        raise ValueError("standard deviation sigma must be positive")
    if not (0.0 < alpha < 1.0):
        raise ValueError("significance level alpha must lie strictly between 0 and 1")
    zc = _critical_two_sided(alpha)
    shift = delta * math.sqrt(n_per_group / (2.0 * sigma * sigma))
    return normal_survival(zc - shift)


def power_report(delta, sigma, alpha=0.05, power=0.8):
    """Power-planning summary dict for a two-sample pooled comparison.

    Returns the dict with keys n_per_group (the rounded minimum per-group
    sample size), n_total (two groups) and achieved_power (the achieved
    power at the rounded per-group sample size). Raises the same ValueErrors
    as the sizing and achieved-power functions.
    """
    n_per_group = sample_size_two_sample_pooled(delta, sigma, alpha, power)
    achieved = achieved_power_two_sample_pooled(n_per_group, delta, sigma, alpha)
    return {
        "n_per_group": n_per_group,
        "n_total": 2 * n_per_group,
        "achieved_power": achieved,
    }
