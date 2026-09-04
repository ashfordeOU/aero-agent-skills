"""Overlapping Allan deviation analysis for gyroscope rate noise (pure stdlib).

Characterizes the noise of a gyroscope rate sample series for ADCS sensor
selection: computes the overlapping Allan deviation AD(tau) over a
correlation-time grid, fits the log-log noise slope, categorizes the noise
process from the slope band, and scales the tau = 1 s deviation into the
angle random walk coefficient in deg/sqrt(h). Input-deterministic: the
module draws no randomness; fixtures live in the contract test with a
seeded RNG.

Conventions: rate samples in rad/s, equally spaced tau0_s seconds apart.
The overlapping Allan deviation at cluster time tau = m * tau0_s is

    AD(tau) = sqrt( 1 / (2 * (N - 2m)) * sum_{k=0}^{N-2m-1}
                    ( mean(samples[k+m : k+2m]) - mean(samples[k : k+m]) )^2 )

computed with cumulative sums for numerical stability on long series.
"""

import math

# Module constants (the fixture seed is used only by the contract test).
RNG_SEED = 20260904  # seeded fixture RNG for the contract test only
DEG_PER_RAD = 57.2958  # radians to degrees
SECONDS_PER_HOUR = 3600.0
MIN_SAMPLES = 3


def _cumulative_sums(rate_samples):
    """Return S with S[i] = sum(rate_samples[:i]); S[0] = 0.0."""
    sums = [0.0] * (len(rate_samples) + 1)
    acc = 0.0
    for i, value in enumerate(rate_samples):
        acc += value
        sums[i + 1] = acc
    return sums


def _cluster_length(tau, tau0_s, n_samples):
    """Resolve tau into the integer cluster length m = tau / tau0_s.

    Raises ValueError when tau is below tau0_s, is not a whole multiple
    of tau0_s, or needs a cluster longer than the sample supports
    (m > (N - 1) / 2 leaves no valid overlapping pair).
    """
    m_float = tau / tau0_s
    m = int(round(m_float))
    if m < 1 or abs(m_float - m) > 1e-9 * max(1.0, abs(m_float)):
        raise ValueError(
            "cluster time tau must be a whole multiple of tau0_s, "
            "got tau=%r with tau0_s=%r" % (tau, tau0_s)
        )
    if m > (n_samples - 1) / 2.0:
        raise ValueError(
            "cluster time tau=%r needs m=%d longer than the sample "
            "allows (m must be <= (N - 1) / 2 with N=%d)"
            % (tau, m, n_samples)
        )
    return m


def allan_deviation(rate_samples, tau0_s, taus):
    """Overlapping Allan deviation AD(tau) in rad/s for each tau.

    rate_samples: sequence of rate samples in rad/s (len >= 3).
    tau0_s: sample period in seconds (> 0).
    taus: iterable of cluster times in seconds, each an integer multiple
        of tau0_s and at most (N - 1) / 2 * tau0_s.

    Returns the AD values in rad/s in the same order as taus. Raises
    ValueError on fewer than 3 samples, non-positive tau0_s, a tau below
    tau0_s, a tau that is not a whole multiple of tau0_s, or a tau whose
    cluster exceeds half the sample.
    """
    n_samples = len(rate_samples)
    if n_samples < MIN_SAMPLES:
        raise ValueError("at least %d rate samples are required" % MIN_SAMPLES)
    if tau0_s <= 0:
        raise ValueError("tau0_s must be positive, got %r" % tau0_s)

    sums = _cumulative_sums(rate_samples)
    ads = []
    for tau in taus:
        if tau < tau0_s:
            raise ValueError(
                "cluster time tau=%r is below the sample period tau0_s=%r"
                % (tau, tau0_s)
            )
        m = _cluster_length(tau, tau0_s, n_samples)
        two_m = 2 * m
        limit = n_samples - two_m
        inv_m = 1.0 / m
        acc = 0.0
        # Overlapping pairs k .. k+m-1 and k+m .. k+2m-1.
        for k in range(limit):
            diff = (sums[k + two_m] - 2.0 * sums[k + m] + sums[k]) * inv_m
            acc += diff * diff
        ads.append(math.sqrt(acc / (2.0 * limit)))
    return ads


def noise_slope(log_taus, log_ads):
    """Least-squares slope of log(AD) against log(tau).

    log_taus: log of the cluster times; log_ads: log of the Allan
    deviations. Returns the fitted slope. Raises ValueError on empty or
    mismatched lists, fewer than two points, or zero variance in the
    log-tau grid (degenerate fit).
    """
    if not log_taus or not log_ads:
        raise ValueError("noise_slope needs non-empty log lists")
    if len(log_taus) != len(log_ads):
        raise ValueError("log_taus and log_ads must have equal length")
    if len(log_taus) < 2:
        raise ValueError("noise_slope needs at least two points")
    n = len(log_taus)
    mean_x = sum(log_taus) / n
    mean_y = sum(log_ads) / n
    cov = 0.0
    var_x = 0.0
    for x, y in zip(log_taus, log_ads):
        dx = x - mean_x
        cov += dx * (y - mean_y)
        var_x += dx * dx
    if var_x == 0.0:
        raise ValueError("log-tau grid has zero variance, slope undefined")
    return cov / var_x


def classify_noise(slope):
    """Categorize the noise process from the log-log Allan slope band.

    Deterministic band classification: slope <= -0.85 quantization-noise,
    slope in [-0.75, -0.25] angle-random-walk, slope in [0.25, 0.75]
    rate-random-walk, |slope| < 0.15 bias-instability, else mixed.
    """
    if slope <= -0.85:
        return "quantization-noise"
    if -0.75 <= slope <= -0.25:
        return "angle-random-walk"
    if 0.25 <= slope <= 0.75:
        return "rate-random-walk"
    if abs(slope) < 0.15:
        return "bias-instability"
    return "mixed"


def angle_random_walk(ad_at_tau1, tau0_s=1.0):
    """Angle random walk coefficient in deg/sqrt(h).

    ARW = ad_at_tau1 * 57.2958 * sqrt(3600 * tau0_s). For a rate sample
    series at period tau0_s the coefficient N in deg/sqrt(h) is
    sigma_rate * sqrt(tau0_s) * 57.2958 * sqrt(3600); with tau0_s = 1 s
    and AD(tau = 1 s) = sigma_rate this is ad_at_tau1 * 3437.748.
    Raises ValueError on non-positive ad_at_tau1 or tau0_s.
    """
    if ad_at_tau1 <= 0:
        raise ValueError("ad_at_tau1 must be positive, got %r" % ad_at_tau1)
    if tau0_s <= 0:
        raise ValueError("tau0_s must be positive, got %r" % tau0_s)
    return ad_at_tau1 * DEG_PER_RAD * math.sqrt(SECONDS_PER_HOUR * tau0_s)


def gyro_noise_summary(rate_samples, tau0_s, taus):
    """One-call gyro noise characterization over the given tau grid.

    Returns a dict with exactly the keys taus, allan_deviations,
    fitted_slope, noise_class, arw_deg_per_sqrt_h, ad_at_1s. The
    tau = 1 s deviation is computed directly (ValueError when a 1 s
    cluster is not representable on this sample period) and feeds the
    angle random walk coefficient.
    """
    ads = allan_deviation(rate_samples, tau0_s, taus)
    tau_list = list(taus)
    slope = noise_slope(
        [math.log(t) for t in tau_list], [math.log(a) for a in ads]
    )
    ad_at_1s = allan_deviation(rate_samples, tau0_s, [1.0])[0]
    return {
        "taus": tau_list,
        "allan_deviations": ads,
        "fitted_slope": slope,
        "noise_class": classify_noise(slope),
        "arw_deg_per_sqrt_h": angle_random_walk(ad_at_1s, tau0_s),
        "ad_at_1s": ad_at_1s,
    }
