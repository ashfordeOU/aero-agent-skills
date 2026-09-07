"""Cramer-Rao lower bound (CRLB) on unbiased parametric estimators.

Pure stdlib (math only), deterministic, offline. Computes the classical
pre-data variance bound from the Fisher information for the canonical
scalar and vector estimation problems of Kay, Fundamentals of
Statistical Signal Processing: Estimation Theory (1993), chapter 3:

- DC level in white Gaussian noise, x[n] = A + w[n], w ~ N(0, sigma^2).
- Scalar Gaussian mean with known variance.
- Vector Gaussian mean with known covariance (information matrix
  I = n C^-1; CRLB = C/n in the PSD sense).
- Sinusoid phase in white Gaussian noise (Kay example 3.14, small-error
  regime with 0 < f0 < 0.5).
- Poisson rate (discrete pmf).

Every public function validates its inputs and raises ValueError on
non-physical input. No RNG, no numpy, no scipy, no external processes.

Module constants pin the worked scenario of the SKILL body.
"""

import math

# Worked-scenario constants (pin exactly).
N_DC = 100            # samples of the DC level in WGN
SIGMA2_DC = 4.0       # noise variance, sigma = 2.0
SIGMA2_GAUSS = 9.0    # known variance of the scalar Gaussian, single sample
N_VEC = 50            # iid samples of the vector Gaussian
COV_VEC = [[1.0, 0.6], [0.6, 4.0]]  # known 2x2 covariance, det = 3.64
N_PH = 64             # samples of the sinusoid
AMP_PH = 1.0          # sinusoid amplitude
F0_PH = 0.25          # digital frequency in cycles/sample, inside (0, 0.5)
PHI0_PH = 0.0         # true phase
SIGMA2_PH = 0.1       # sinusoid noise variance
N_POI = 25            # iid Poisson observations
LAM_POI = 4.0         # Poisson rate


def _require_n(n):
    """Validate n as a positive integer; raise ValueError otherwise."""
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")


def _require_finite_positive(x, name):
    """Validate x as finite and > 0; raise ValueError otherwise."""
    if not math.isfinite(x) or x <= 0:
        raise ValueError("%s must be finite and > 0" % name)


def _require_finite_nonzero(x, name):
    """Validate x as finite and != 0; raise ValueError otherwise."""
    if not math.isfinite(x) or x == 0:
        raise ValueError("%s must be finite and non-zero" % name)


def _require_f0(f0):
    """Validate f0 inside the open interval (0, 0.5); raise otherwise."""
    if not math.isfinite(f0) or f0 <= 0 or f0 >= 0.5:
        raise ValueError("f0 must be finite and strictly inside (0, 0.5)")


def _check_cov(cov):
    """Validate a 2x2 covariance: finite, symmetric, positive definite.

    Returns (a, b, c, d, det) as floats after validation. Symmetry uses
    the spec tolerance |cov[0][1] - cov[1][0]| <= 1e-12 * max(1, |b|).
    Positive definiteness requires det > 0 for the symmetric 2x2 case.
    """
    try:
        if len(cov) != 2 or len(cov[0]) != 2 or len(cov[1]) != 2:
            raise ValueError("cov must be a 2x2 matrix")
        a, b = float(cov[0][0]), float(cov[0][1])
        c, d = float(cov[1][0]), float(cov[1][1])
    except (TypeError, IndexError):
        raise ValueError("cov must be a 2x2 matrix") from None
    if not all(math.isfinite(x) for x in (a, b, c, d)):
        raise ValueError("cov entries must all be finite")
    if abs(b - c) > 1e-12 * max(1.0, abs(b)):
        raise ValueError("cov must be symmetric")
    det = a * d - b * c
    if det <= 0:
        raise ValueError("cov must be positive definite (det > 0)")
    return a, b, c, d, det


def _inv2x2(cov):
    """Analytic inverse of a validated 2x2 covariance: 1/det [[d, -b], [-c, a]]."""
    a, b, c, d, det = _check_cov(cov)
    return [[d / det, -b / det], [-c / det, a / det]]


def _matmul2x2(A, B):
    """2x2 matrix product A * B (used by the worked-example identity check)."""
    return [
        [A[0][0] * B[0][0] + A[0][1] * B[1][0],
         A[0][0] * B[0][1] + A[0][1] * B[1][1]],
        [A[1][0] * B[0][0] + A[1][1] * B[1][0],
         A[1][0] * B[0][1] + A[1][1] * B[1][1]],
    ]


# --------------------------------------------------------------------------
# DC level in white Gaussian noise
# --------------------------------------------------------------------------

def fisher_info_dc(n, sigma2):
    """Fisher information I(A) = N/sigma^2 of the DC level in WGN."""
    _require_n(n)
    _require_finite_positive(sigma2, "sigma2")
    return n / sigma2


def crlb_dc(n, sigma2):
    """Cramer-Rao bound var(A_hat) >= sigma^2/N for the DC level in WGN."""
    _require_n(n)
    _require_finite_positive(sigma2, "sigma2")
    return sigma2 / n


def mle_var_dc(n, sigma2):
    """Variance sigma^2/N of the unbiased sample-mean MLE of the DC level."""
    _require_n(n)
    _require_finite_positive(sigma2, "sigma2")
    return sigma2 / n


# --------------------------------------------------------------------------
# Scalar Gaussian mean, known variance
# --------------------------------------------------------------------------

def fisher_info_gauss(n, sigma2):
    """Fisher information I(mu) = n/sigma^2 of the Gaussian mean."""
    _require_n(n)
    _require_finite_positive(sigma2, "sigma2")
    return n / sigma2


def crlb_gauss(n, sigma2):
    """Cramer-Rao bound var(mu_hat) >= sigma^2/n of the Gaussian mean."""
    _require_n(n)
    _require_finite_positive(sigma2, "sigma2")
    return sigma2 / n


# --------------------------------------------------------------------------
# Vector Gaussian mean, known covariance
# --------------------------------------------------------------------------

def info_matrix_gaussian(n, cov):
    """Fisher information matrix I = n C^-1 of the Gaussian mean vector."""
    _require_n(n)
    inv = _inv2x2(cov)
    return [[n * inv[0][0], n * inv[0][1]],
            [n * inv[1][0], n * inv[1][1]]]


def crlb_matrix_gaussian(n, cov):
    """Cramer-Rao covariance bound Cov(mu_hat) >= C/n (matrix sense).

    The inverse of the information matrix is validated (I x CRLB is the
    identity to within 1e-9) but only the bound covariance C/n is
    returned.
    """
    _require_n(n)
    _check_cov(cov)
    info = info_matrix_gaussian(n, cov)
    crlb = [[cov[0][0] / n, cov[0][1] / n],
            [cov[1][0] / n, cov[1][1] / n]]
    ident = _matmul2x2(info, crlb)
    if (abs(ident[0][0] - 1.0) > 1e-9 or abs(ident[1][1] - 1.0) > 1e-9
            or abs(ident[0][1]) > 1e-9 or abs(ident[1][0]) > 1e-9):
        raise ValueError("information x crlb round-trip failed")
    return crlb


# --------------------------------------------------------------------------
# Sinusoid phase in white Gaussian noise
# --------------------------------------------------------------------------

def fisher_info_phase(n, amp, f0, phi0, sigma2):
    """Fisher information I(phi0) = (A^2/sigma^2) sum sin^2(2 pi f0 k + phi0).

    Exact information at the true phase (Kay example 3.14, small-error
    regime, 0 < f0 < 0.5).
    """
    _require_n(n)
    _require_finite_nonzero(amp, "amp")
    _require_f0(f0)
    if not math.isfinite(phi0):
        raise ValueError("phi0 must be finite")
    _require_finite_positive(sigma2, "sigma2")
    total = 0.0
    for k in range(n):
        total += math.sin(2.0 * math.pi * f0 * k + phi0) ** 2
    return (amp * amp / sigma2) * total


def crlb_phase(n, amp, sigma2):
    """Cramer-Rao bound var(phi_hat) >= 2 sigma^2/(N A^2).

    Exact at f0 = 0.25, phi0 = 0 and even N, where the sine-square sum
    is exactly N/2.
    """
    _require_n(n)
    _require_finite_nonzero(amp, "amp")
    _require_finite_positive(sigma2, "sigma2")
    return 2.0 * sigma2 / (n * amp * amp)


# --------------------------------------------------------------------------
# Poisson rate
# --------------------------------------------------------------------------

def fisher_info_poisson(n, lam):
    """Fisher information I(lam) = n/lam of the Poisson rate."""
    _require_n(n)
    _require_finite_positive(lam, "lam")
    return n / lam


def crlb_poisson(n, lam):
    """Cramer-Rao bound var(lam_hat) >= lam/n of the Poisson rate."""
    _require_n(n)
    _require_finite_positive(lam, "lam")
    return lam / n


def mle_var_poisson(n, lam):
    """Variance lam/n of the unbiased sample-mean MLE of the rate."""
    _require_n(n)
    _require_finite_positive(lam, "lam")
    return lam / n


# --------------------------------------------------------------------------
# Estimator efficiency
# --------------------------------------------------------------------------

def efficiency(crlb, estimator_var):
    """Efficiency = crlb / estimator_var in (0, 1]; 1 means bound-achieving."""
    _require_finite_positive(crlb, "crlb")
    _require_finite_positive(estimator_var, "estimator_var")
    return crlb / estimator_var
