"""Probability distribution fitting and characterization (stdlib only).

Fit the normal, lognormal, exponential, and Weibull distributions to a
univariate sample, evaluate their pdf, cdf, quantile, reliability, and
hazard functions, and score goodness of fit with the chi-square and
Kolmogorov-Smirnov statistics. Deterministic: no random sampling, no
external libraries. NACA TR-824 frames the statistical methods context;
all relations below are standard engineering methodology, summary-only.

Domain gates: lifetime distributions (lognormal, exponential, weibull)
are defined on strictly positive x; the normal distribution is defined
on the whole real line.
"""

import math

# Weibull MLE bisection bracket and tolerance on the shape parameter.
WEIBULL_K_MIN = 0.05
WEIBULL_K_MAX = 10.0
WEIBULL_TOL = 1e-8

# Chi-square goodness of fit: merge bins whose expected count falls
# below this floor (expected count per cell after merging).
MIN_EXP = 1.0

# Kolmogorov-Smirnov 5% critical values, large-sample approximation
# D_crit = KS_CRIT_COEF / sqrt(n) (asymptotic, documented as such).
KS_CRIT_COEF = 1.358

# Chi-square 5% critical values keyed by degrees of freedom after
# bin merging (df in the reachable 6 to 10 range).
CRIT_CHI2 = {6: 12.59, 7: 14.07, 8: 15.51, 9: 16.92, 10: 18.31}

# Acklam rational approximation coefficients for the standard normal
# quantile (published set, relative error near 1e-9 over the whole
# probability range).
ACKLAM_A = (
    -3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
    1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00,
)
ACKLAM_B = (
    -5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
    6.680131188771972e01, -1.328068155288572e01,
)
ACKLAM_C = (
    -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
    -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00,
)
ACKLAM_D = (
    7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
    3.754408661907416e00,
)
ACKLAM_PLOW = 0.02425
ACKLAM_PHIGH = 0.97575

_DIST_NAMES = ("normal", "lognormal", "exponential", "weibull")
_POSITIVE_DISTS = ("lognormal", "exponential", "weibull")


def _validate_dist(dist):
    """Raise ValueError when the distribution name is unknown."""
    if dist not in _DIST_NAMES:
        raise ValueError(
            "unknown distribution %r, expected one of %s"
            % (dist, ", ".join(_DIST_NAMES))
        )


def _as_float_list(data):
    """Coerce to floats and reject empty or non-finite input."""
    if data is None or len(data) == 0:
        raise ValueError("data must not be empty")
    floats = []
    for value in data:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("data values must be numeric") from None
        if not math.isfinite(number):
            raise ValueError("data values must be finite")
        floats.append(number)
    return floats


def _require_pos_data(floats, dist):
    """Reject non-positive values for lifetime distributions."""
    for value in floats:
        if value <= 0.0:
            raise ValueError("%s fit requires strictly positive data" % dist)


def _require_positive(value, name, dist):
    """Reject non-positive evaluation points for lifetime distributions."""
    if value <= 0.0:
        raise ValueError(
            "%s must be positive for the %s distribution" % (name, dist)
        )


def _fit_normal(floats):
    """Normal parameters: mean and sample standard deviation (ddof 1)."""
    n = len(floats)
    mu = sum(floats) / n
    variance = sum((value - mu) ** 2 for value in floats) / (n - 1)
    sigma = math.sqrt(variance)
    if sigma <= 0.0:
        raise ValueError(
            "sigma must be positive, constant data has zero sample "
            "standard deviation"
        )
    return {"mu": mu, "sigma": sigma}


def _fit_lognormal(floats):
    """Lognormal parameters from mean and std of the log data."""
    logs = [math.log(value) for value in floats]
    n = len(logs)
    mu_ln = sum(logs) / n
    variance = sum((value - mu_ln) ** 2 for value in logs) / (n - 1)
    sigma_ln = math.sqrt(variance)
    if sigma_ln <= 0.0:
        raise ValueError(
            "sigma_ln must be positive, identical data has zero log "
            "standard deviation"
        )
    return {"mu_ln": mu_ln, "sigma_ln": sigma_ln}


def _fit_exponential(floats):
    """Exponential rate as the reciprocal of the sample mean."""
    rate = 1.0 / (sum(floats) / len(floats))
    return {"rate": rate}


def _weibull_mle_shape(logs):
    """MLE Weibull shape by bisection of the fixed-point equation.

    The MLE shape k solves 1/k = mean(x^k ln x) / mean(x^k) - mean(ln x).
    The left side falls and the ratio rises with k, so the residual is
    monotone decreasing and the bisection bracket holds when the root
    lies inside [WEIBULL_K_MIN, WEIBULL_K_MAX].
    """
    n = len(logs)
    mean_ln = sum(logs) / n

    def residual(k):
        powers = [math.exp(k * log) for log in logs]
        total = sum(powers)
        weighted = sum(power * log for power, log in zip(powers, logs))
        return 1.0 / k - weighted / total + mean_ln

    low_res = residual(WEIBULL_K_MIN)
    high_res = residual(WEIBULL_K_MAX)
    if low_res < 0.0:
        raise ValueError(
            "weibull MLE shape below the bisection bracket lower bound"
        )
    if high_res > 0.0:
        raise ValueError(
            "weibull MLE shape above the bisection bracket upper bound"
        )
    low, high = WEIBULL_K_MIN, WEIBULL_K_MAX
    while high - low > WEIBULL_TOL:
        mid = 0.5 * (low + high)
        if residual(mid) > 0.0:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def _fit_weibull(floats):
    """Weibull MLE parameters: shape by bisection, scale from the mean."""
    logs = [math.log(value) for value in floats]
    shape = _weibull_mle_shape(logs)
    mean_power = sum(math.exp(shape * log) for log in logs) / len(logs)
    scale = math.exp(math.log(mean_power) / shape)
    return {"shape": shape, "scale": scale}


def fit_distribution(data, dist):
    """Fit the named distribution to a sample and return the params dict.

    Param keys: normal {mu, sigma}, lognormal {mu_ln, sigma_ln},
    exponential {rate}, weibull {shape, scale}. At least three finite
    data points are required; lifetime distributions reject non-positive
    values; zero sample standard deviation raises ValueError.
    """
    _validate_dist(dist)
    floats = _as_float_list(data)
    if len(floats) < 3:
        raise ValueError("at least 3 data points are required to fit")
    if dist in _POSITIVE_DISTS:
        _require_pos_data(floats, dist)
    if dist == "normal":
        return _fit_normal(floats)
    if dist == "lognormal":
        return _fit_lognormal(floats)
    if dist == "exponential":
        return _fit_exponential(floats)
    return _fit_weibull(floats)


def _normal_pdf(x, mu, sigma):
    """Normal density at x."""
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))


def _normal_cdf(x, mu, sigma):
    """Normal cdf at x through the error function."""
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def _normal_quantile_standard(p):
    """Acklam rational approximation of the standard normal quantile."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    if p < ACKLAM_PLOW:
        q = math.sqrt(-2.0 * math.log(p))
        num = (((((ACKLAM_C[0] * q + ACKLAM_C[1]) * q + ACKLAM_C[2]) * q
                 + ACKLAM_C[3]) * q + ACKLAM_C[4]) * q + ACKLAM_C[5])
        den = ((((ACKLAM_D[0] * q + ACKLAM_D[1]) * q + ACKLAM_D[2]) * q
                + ACKLAM_D[3]) * q + 1.0)
        return num / den
    if p <= ACKLAM_PHIGH:
        q = p - 0.5
        r = q * q
        num = (((((ACKLAM_A[0] * r + ACKLAM_A[1]) * r + ACKLAM_A[2]) * r
                 + ACKLAM_A[3]) * r + ACKLAM_A[4]) * r + ACKLAM_A[5]) * q
        den = (((((ACKLAM_B[0] * r + ACKLAM_B[1]) * r + ACKLAM_B[2]) * r
                 + ACKLAM_B[3]) * r + ACKLAM_B[4]) * r + 1.0)
        return num / den
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    num = (((((ACKLAM_C[0] * q + ACKLAM_C[1]) * q + ACKLAM_C[2]) * q
             + ACKLAM_C[3]) * q + ACKLAM_C[4]) * q + ACKLAM_C[5])
    den = ((((ACKLAM_D[0] * q + ACKLAM_D[1]) * q + ACKLAM_D[2]) * q
            + ACKLAM_D[3]) * q + 1.0)
    return -num / den


def _lognormal_pdf(x, mu_ln, sigma_ln):
    """Lognormal density at x for the log-space parameters."""
    log_x = math.log(x)
    z = (log_x - mu_ln) / sigma_ln
    return math.exp(-0.5 * z * z) / (
        x * sigma_ln * math.sqrt(2.0 * math.pi)
    )


def _exponential_pdf(x, rate):
    """Exponential density at x."""
    return rate * math.exp(-rate * x)


def _weibull_pdf(x, shape, scale):
    """Weibull density at x."""
    ratio = x / scale
    return (shape / scale) * (ratio ** (shape - 1.0)) * math.exp(
        -(ratio ** shape)
    )


def pdf(x, dist, params):
    """Probability density at x for the fitted distribution."""
    _validate_dist(dist)
    if dist == "normal":
        return _normal_pdf(x, params["mu"], params["sigma"])
    _require_positive(x, "x", dist)
    if dist == "lognormal":
        return _lognormal_pdf(x, params["mu_ln"], params["sigma_ln"])
    if dist == "exponential":
        return _exponential_pdf(x, params["rate"])
    return _weibull_pdf(x, params["shape"], params["scale"])


def cdf(x, dist, params):
    """Cumulative distribution function at x."""
    _validate_dist(dist)
    if dist == "normal":
        return _normal_cdf(x, params["mu"], params["sigma"])
    _require_positive(x, "x", dist)
    if dist == "lognormal":
        return _normal_cdf(math.log(x), params["mu_ln"], params["sigma_ln"])
    if dist == "exponential":
        return 1.0 - math.exp(-params["rate"] * x)
    ratio = x / params["scale"]
    return 1.0 - math.exp(-(ratio ** params["shape"]))


def quantile(p, dist, params):
    """Quantile at probability p, the inverse of the cdf.

    Probabilities outside [0, 1] raise ValueError; p = 0 maps to the
    lower support bound and p = 1 to positive infinity.
    """
    _validate_dist(dist)
    if p < 0.0 or p > 1.0:
        raise ValueError("probability p must lie in [0, 1]")
    if dist == "normal":
        z = _normal_quantile_standard(p)
        return params["mu"] + params["sigma"] * z
    if dist == "lognormal":
        z = _normal_quantile_standard(p)
        return math.exp(params["mu_ln"] + params["sigma_ln"] * z)
    if p >= 1.0:
        return math.inf
    if dist == "exponential":
        return -math.log(1.0 - p) / params["rate"]
    return params["scale"] * ((-math.log(1.0 - p)) ** (1.0 / params["shape"]))


def reliability(t, dist, params):
    """Reliability R(t) = 1 - cdf(t), survival past time t."""
    _validate_dist(dist)
    if dist in _POSITIVE_DISTS:
        _require_positive(t, "t", dist)
    if dist == "normal":
        return 1.0 - _normal_cdf(t, params["mu"], params["sigma"])
    if dist == "lognormal":
        return 1.0 - _normal_cdf(
            math.log(t), params["mu_ln"], params["sigma_ln"]
        )
    if dist == "exponential":
        return math.exp(-params["rate"] * t)
    ratio = t / params["scale"]
    return math.exp(-(ratio ** params["shape"]))


def hazard(t, dist, params):
    """Hazard function h(t), the instantaneous failure rate at t."""
    _validate_dist(dist)
    if dist in _POSITIVE_DISTS:
        _require_positive(t, "t", dist)
    if dist == "exponential":
        return params["rate"]
    if dist == "weibull":
        ratio = t / params["scale"]
        return (params["shape"] / params["scale"]) * (
            ratio ** (params["shape"] - 1.0)
        )
    density = pdf(t, dist, params)
    survival = reliability(t, dist, params)
    if survival <= 0.0:
        return math.inf
    return density / survival


def _merge_low_expected(observed, expected):
    """Merge adjacent cells until every expected count reaches MIN_EXP."""
    obs = list(observed)
    exp = list(expected)
    while len(obs) > 1:
        low_index = None
        for index, count in enumerate(exp):
            if count < MIN_EXP:
                low_index = index
                break
        if low_index is None:
            break
        if low_index == len(obs) - 1:
            target = low_index - 1
        else:
            target = low_index + 1
        obs[target] += obs[low_index]
        exp[target] += exp[low_index]
        del obs[low_index]
        del exp[low_index]
    return obs, exp


def chi2_gof(data, dist, params, bins=8):
    """Chi-square goodness of fit over fixed-width bins.

    Returns (statistic, df, verdict) with the verdict PASS when the
    statistic is at most the 5% critical value for the post-merge
    degrees of freedom; degrees of freedom outside the module critical
    table raise ValueError.
    """
    _validate_dist(dist)
    floats = _as_float_list(data)
    if len(floats) < 3:
        raise ValueError("at least 3 data points are required")
    if dist in _POSITIVE_DISTS:
        _require_pos_data(floats, dist)
    low = min(floats)
    high = max(floats)
    if high - low <= 0.0:
        raise ValueError("zero data range, chi-square bins undefined")
    width = (high - low) / bins
    observed = [0] * bins
    for value in floats:
        index = int((value - low) / width)
        if index >= bins:
            index = bins - 1
        observed[index] += 1
    expected = []
    for index in range(bins):
        edge_low = low + index * width
        edge_high = low + (index + 1) * width
        prob = cdf(edge_high, dist, params) - cdf(edge_low, dist, params)
        expected.append(len(floats) * prob)
    merged_obs, merged_exp = _merge_low_expected(observed, expected)
    df = len(merged_obs) - 1
    if df not in CRIT_CHI2:
        raise ValueError(
            "degrees of freedom %d outside the chi-square critical table"
            % df
        )
    stat = sum(
        (obs - exp_count) ** 2 / exp_count
        for obs, exp_count in zip(merged_obs, merged_exp)
    )
    verdict = "PASS" if stat <= CRIT_CHI2[df] else "FAIL"
    return stat, df, verdict


def ks_gof(data, dist, params):
    """Kolmogorov-Smirnov goodness of fit against the fitted cdf.

    Returns (D, verdict) with D the largest absolute gap between the
    empirical and the fitted cdf over the sorted sample and the verdict
    PASS when D is at most KS_CRIT_COEF / sqrt(n), the large-sample 5%
    approximation.
    """
    _validate_dist(dist)
    floats = _as_float_list(data)
    if len(floats) < 3:
        raise ValueError("at least 3 data points are required")
    if dist in _POSITIVE_DISTS:
        _require_pos_data(floats, dist)
    n = len(floats)
    sorted_data = sorted(floats)
    d_stat = 0.0
    for index, value in enumerate(sorted_data, start=1):
        fitted = cdf(value, dist, params)
        d_stat = max(d_stat, abs(index / n - fitted),
                     abs((index - 1) / n - fitted))
    critical = KS_CRIT_COEF / math.sqrt(n)
    verdict = "PASS" if d_stat <= critical else "FAIL"
    return d_stat, verdict


def summarize(data, dist, target):
    """Fit and characterize: params, gof verdicts, percentiles, reliability.

    Returns {params, n, chi2_stat, chi2_verdict, ks_D, ks_verdict, q05,
    q50, q95, reliability_at_target} for the fitted distribution at the
    target time.
    """
    _validate_dist(dist)
    floats = _as_float_list(data)
    if len(floats) < 3:
        raise ValueError("at least 3 data points are required")
    if dist in _POSITIVE_DISTS:
        _require_pos_data(floats, dist)
    params = fit_distribution(floats, dist)
    chi2_stat, _df, chi2_verdict = chi2_gof(floats, dist, params)
    ks_d, ks_verdict = ks_gof(floats, dist, params)
    return {
        "params": params,
        "n": len(floats),
        "chi2_stat": chi2_stat,
        "chi2_verdict": chi2_verdict,
        "ks_D": ks_d,
        "ks_verdict": ks_verdict,
        "q05": quantile(0.05, dist, params),
        "q50": quantile(0.50, dist, params),
        "q95": quantile(0.95, dist, params),
        "reliability_at_target": reliability(target, dist, params),
    }
