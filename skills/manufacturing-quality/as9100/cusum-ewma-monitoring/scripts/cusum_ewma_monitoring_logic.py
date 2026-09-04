"""Tabular CUSUM and EWMA control chart statistics for small-shift monitoring.

Pure Python stdlib implementation of the sequential monitoring statistics
used to detect small sustained mean shifts in a production process:

- Tabular CUSUM on the standardized deviations z_i = (x_i - mu0) / sigma:
  S+_i = max(0, z_i - k + S+_{i-1}), S-_i = max(0, -z_i - k + S-_{i-1}),
  starting from S+_0 = S-_0 = 0; a signal fires when S+_i > h or
  S-_i > h (slack k, decision interval h, defaults 0.5 and 5.0).
- EWMA recursion e_i = lam * x_i + (1 - lam) * e_{i-1} seeded at mu0 with
  time varying sigma limits sigma_e_i = sigma * sqrt(lam / (2 - lam) *
  (1 - (1 - lam)^(2 i))), UCL_i = mu0 + L * sigma_e_i and
  LCL_i = mu0 - L * sigma_e_i (defaults lam 0.2, L 3.0).

Observations are assumed independent normal around the in-control mean mu0
with known or in-control-estimated sigma. All functions are deterministic
(no RNG) and offline; first signal indices are 1-based sample numbers.
"""

from math import sqrt

DEFAULT_K = 0.5    # CUSUM slack k in sigma units
DEFAULT_H = 5.0    # CUSUM decision interval h in sigma units
DEFAULT_LAM = 0.2  # EWMA smoothing weight
DEFAULT_L = 3.0    # EWMA limit width in sigma units


def _check_observations(xs, sigma):
    """Reject empty observation sequences and non-positive sigma."""
    if xs is None or len(xs) == 0:
        raise ValueError("xs must contain at least one observation")
    if sigma <= 0:
        raise ValueError("sigma must be positive")


def cusum_statistics(xs, mu0, sigma, k=DEFAULT_K, h=DEFAULT_H):
    """Tabular CUSUM path over xs.

    Returns a dict with sp_plus and sp_minus lists (one entry per
    observation) and first_signal_index, the 1-based sample number of the
    first observation for which S+ > h or S- > h, or None when the whole
    sequence stays in control.
    """
    _check_observations(xs, sigma)
    if k <= 0:
        raise ValueError("k must be positive")
    if h <= 0:
        raise ValueError("h must be positive")
    sp_plus = []
    sp_minus = []
    first_signal_index = None
    s_plus = 0.0
    s_minus = 0.0
    for index, x in enumerate(xs):
        z = (x - mu0) / sigma
        s_plus = max(0.0, z - k + s_plus)
        s_minus = max(0.0, -z - k + s_minus)
        sp_plus.append(s_plus)
        sp_minus.append(s_minus)
        if first_signal_index is None and (s_plus > h or s_minus > h):
            first_signal_index = index + 1
    return {
        "sp_plus": sp_plus,
        "sp_minus": sp_minus,
        "first_signal_index": first_signal_index,
    }


def ewma_statistics(xs, mu0, sigma, lam=DEFAULT_LAM, L=DEFAULT_L):
    """EWMA recursion path with time varying limits over xs.

    Returns a dict with ewma_series, ucl and lcl lists (one entry per
    observation) and first_signal_index, the 1-based sample number of the
    first observation for which e_i falls outside UCL_i/LCL_i, or None
    when the whole sequence stays in control.
    """
    _check_observations(xs, sigma)
    if lam <= 0 or lam > 1:
        raise ValueError("lam must be in (0, 1]")
    if L <= 0:
        raise ValueError("L must be positive")
    ewma_series = []
    ucl = []
    lcl = []
    first_signal_index = None
    e = mu0
    decay = 1.0 - lam
    variance_scale = lam / (2.0 - lam)
    for index, x in enumerate(xs):
        e = lam * x + decay * e
        sigma_e = sigma * sqrt(variance_scale * (1.0 - decay ** (2 * (index + 1))))
        upper = mu0 + L * sigma_e
        lower = mu0 - L * sigma_e
        ewma_series.append(e)
        ucl.append(upper)
        lcl.append(lower)
        if first_signal_index is None and (e > upper or e < lower):
            first_signal_index = index + 1
    return {
        "ewma_series": ewma_series,
        "ucl": ucl,
        "lcl": lcl,
        "first_signal_index": first_signal_index,
    }


def monitoring_verdict(cusum_signal_index, ewma_signal_index, n):
    """Combine CUSUM and EWMA signal results into a monitoring verdict.

    Takes the (possibly None) first signal indices of the two charts and
    the number of monitored observations n. Returns a dict with
    cusum_signaled, ewma_signaled, any_signal and first_signal_index,
    the earlier of the two chart signals as a 1-based sample number, or
    None when neither chart fired.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    cusum_signaled = cusum_signal_index is not None
    ewma_signaled = ewma_signal_index is not None
    fired = []
    if cusum_signaled:
        fired.append(cusum_signal_index)
    if ewma_signaled:
        fired.append(ewma_signal_index)
    return {
        "cusum_signaled": cusum_signaled,
        "ewma_signaled": ewma_signaled,
        "any_signal": cusum_signaled or ewma_signaled,
        "first_signal_index": min(fired) if fired else None,
    }


def small_shift_monitoring_report(xs, mu0, sigma, k=DEFAULT_K, h=DEFAULT_H,
                                  lam=DEFAULT_LAM, L=DEFAULT_L):
    """Combine both charts and the verdict into one small-shift report.

    Returns a dict with cusum (cusum_statistics output), ewma
    (ewma_statistics output) and verdict (monitoring_verdict output),
    validating every input through the underlying functions.
    """
    cusum = cusum_statistics(xs, mu0, sigma, k, h)
    ewma = ewma_statistics(xs, mu0, sigma, lam, L)
    verdict = monitoring_verdict(
        cusum["first_signal_index"], ewma["first_signal_index"], len(xs)
    )
    return {"cusum": cusum, "ewma": ewma, "verdict": verdict}
