"""ARP4761A failure-rate estimation and reliability demonstration.

Pure stdlib functions (no numpy/scipy) for estimating and demonstrating
aircraft system failure rates from test or service data:

- point estimate of the failure rate from failures and test hours
- exact Poisson (chi-square) upper confidence bound on the failure rate
- zero-failure demonstration rule: demonstrated rate = -ln(alpha)/T
- test-time planning to demonstrate a target rate at a confidence
- MTBF point estimate and lower confidence bound
- Poisson acceptance probability for a demonstration test plan
- maximum confidence demonstrated by a zero-failure test

All invalid inputs raise ValueError. All math is deterministic, offline.

Worked references (standard chi-square quantiles, Abramowitz and Stegun
table 26.7 / NIST): chi2(0.80, 2) = 3.21888, chi2(0.95, 2) = 5.99146,
chi2(0.95, 4) = 9.48773, chi2(0.95, 6) = 12.59159,
chi2(0.90, 12) = 18.54935, chi2(0.95, 20) = 31.41043.
"""

import math

_FPMIN = 1e-300


# ---------------------------------------------------------------------------
# Regularized incomplete gamma helpers (Numerical Recipes gser/gcf style,
# standard public-domain numerical algorithms, reimplemented here).
# ---------------------------------------------------------------------------

def _gammp_series(a, x):
    """Regularized lower incomplete gamma P(a, x) via the power series."""
    ap = a
    total = 1.0 / a
    term = total
    for _ in range(500):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * 1e-16:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gammq_cf(a, x):
    """Regularized upper incomplete gamma Q(a, x) via the Lentz continued
    fraction; accurate when x >= a + 1."""
    b = x + 1.0 - a
    c = 1.0 / _FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = b + an / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def _gammq(a, x):
    """Regularized upper incomplete gamma Q(a, x) = Gamma(a,x)/Gamma(a)."""
    if x < a + 1.0:
        return 1.0 - _gammp_series(a, x)
    return _gammq_cf(a, x)


def _chi2_cdf(value, a):
    """CDF of the chi-square distribution at value, with shape a = df / 2."""
    return 1.0 - _gammq(a, value / 2.0)


def chi2_ppf(p, df):
    """Quantile of the chi-square distribution: P(chi2 <= x) = p.

    Inverted by bisection on the exact CDF; deterministic and offline.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("chi2_ppf: p must be in (0, 1), got %r" % (p,))
    if df <= 0:
        raise ValueError("chi2_ppf: degrees of freedom must be positive, got %r" % (df,))
    a = df / 2.0
    lo = 1e-12
    hi = 1.0
    while _chi2_cdf(hi, a) < p:
        hi *= 2.0
        if hi > 1e12:
            raise ValueError("chi2_ppf: quantile bracket failed to converge")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _chi2_cdf(mid, a) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-9 * max(1.0, abs(mid)):
            break
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Failure-rate estimation and demonstration
# ---------------------------------------------------------------------------

def point_estimate_failure_rate(failures, test_hours):
    """Point estimate of the failure rate: lambda_hat = n / T, per hour."""
    if failures < 0:
        raise ValueError("failures must be non-negative, got %r" % (failures,))
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    return failures / test_hours


def mtbf_estimate(failures, test_hours):
    """Point estimate of the mean time between failures: MTBF = T / n.

    Requires at least one failure; use mtbf_lower_bound or
    zero_failure_demonstrated_rate for the zero-failure case.
    """
    if failures <= 0:
        raise ValueError(
            "mtbf_estimate: need at least one failure for a point MTBF, "
            "got %r; use the zero-failure confidence bound instead" % (failures,)
        )
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    return test_hours / failures


def poisson_rate_upper_bound(failures, test_hours, confidence):
    """Exact (1 - alpha) upper confidence bound on the failure rate.

    lambda_upper = chi2(confidence, 2n + 2) / (2 T). For n = 0 this
    reduces to the zero-failure rule -ln(1 - confidence) / T.
    """
    if failures < 0:
        raise ValueError("failures must be non-negative, got %r" % (failures,))
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1), got %r" % (confidence,))
    df = 2 * failures + 2
    return chi2_ppf(confidence, df) / (2.0 * test_hours)


def zero_failure_demonstrated_rate(test_hours, confidence):
    """Failure rate demonstrated by a zero-failure test: -ln(alpha) / T.

    Worked: 1,000,000 h with zero failures demonstrates 1.60944e-6 per
    hour at 80 percent confidence; 2.30259e-6 at 90 percent.
    """
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1), got %r" % (confidence,))
    return -math.log(1.0 - confidence) / test_hours


def test_time_to_demonstrate(target_rate, confidence, allowed_failures=0):
    """Test hours required to demonstrate a target rate at a confidence.

    T = chi2(confidence, 2n + 2) / (2 * target_rate), with n the allowed
    number of failures in the demonstration. Worked: a 1e-6 per hour rate
    at 80 percent confidence with zero allowed failures needs
    3.21888 / 2e-6 = 1.60944e6 test hours.
    """
    if target_rate <= 0:
        raise ValueError("target_rate must be positive, got %r" % (target_rate,))
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1), got %r" % (confidence,))
    if allowed_failures < 0:
        raise ValueError(
            "allowed_failures must be non-negative, got %r" % (allowed_failures,)
        )
    df = 2 * allowed_failures + 2
    return chi2_ppf(confidence, df) / (2.0 * target_rate)


def mtbf_lower_bound(failures, test_hours, confidence):
    """Lower (1 - alpha) confidence bound on the MTBF: 2 T / chi2(1 - alpha)."""
    if failures < 0:
        raise ValueError("failures must be non-negative, got %r" % (failures,))
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1), got %r" % (confidence,))
    df = 2 * failures + 2
    return 2.0 * test_hours / chi2_ppf(confidence, df)


def poisson_cdf(rate, test_hours, k):
    """P(X <= k) for X Poisson with mean rate * test_hours.

    Acceptance probability of a demonstration plan: if the true rate is
    `rate`, the probability that a test of `test_hours` records at most k
    failures and therefore passes. Worked: rate 1e-6 per hour over
    1,000,000 h gives mean 1.0, so P(0 failures) = 0.3679 and
    P(<= 1 failure) = 0.7358.
    """
    if rate < 0:
        raise ValueError("rate must be non-negative, got %r" % (rate,))
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    if k < 0:
        raise ValueError("k must be non-negative, got %r" % (k,))
    mu = rate * test_hours
    return _gammq(k + 1, mu)


def confidence_from_zero_failure_test(test_hours, target_rate):
    """Maximum confidence demonstrated by a zero-failure test of T hours
    against a target rate: C = 1 - exp(-target_rate * T).

    Worked: 1.60944e6 h at a 1e-6 per hour target demonstrates 80 percent
    confidence (1 - exp(-1.60944) = 0.8000).
    """
    if test_hours <= 0:
        raise ValueError("test_hours must be positive, got %r" % (test_hours,))
    if target_rate <= 0:
        raise ValueError("target_rate must be positive, got %r" % (target_rate,))
    return 1.0 - math.exp(-target_rate * test_hours)
