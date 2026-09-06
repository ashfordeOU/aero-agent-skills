"""GNSS code-carrier (Hatch) pseudorange smoothing, pure stdlib.

First-order Hatch recursion used as a GNSS measurement preprocessor:
the code pseudorange stream is low-pass filtered at a smoothing time
constant tau while precise carrier-phase delta ranges carry the
smoothed range between epochs.  This module implements the recursion,
the exact steady-state noise closed forms, and the code-carrier
ionospheric divergence monitor.

Defining relations (every function derives from these):
- Hatch gain alpha = T / tau in (0, 1), so the recursion pole
  (1 - alpha) lies in (0, 1) and the variance relaxation e-folds in
  about tau/2 seconds.
- Recursion with s_0 = c_0 and, for k >= 1,
  s_k = alpha*c_k + (1-alpha)*(s_(k-1) + (phi_k - phi_(k-1))).
- Steady-state code-only std, exact closed form:
  sigma_code*sqrt(alpha/(2 - alpha)).  The textbook
  sigma_code/sqrt(2*tau/T) equals sigma_code*sqrt(alpha/2), the
  small-alpha limit, with the exact identity
  approx = exact*sqrt((2 - alpha)/2).
- Carrier delta-range term std:
  (1 - alpha)*sigma_carrier/sqrt(alpha*(2 - alpha)); the two noise
  inputs are independent per epoch, so the total smoothed variance is
  the exact sum of the code-term and carrier-term variances.
- Ionospheric divergence: the code is delayed by +I while the carrier
  is advanced by -I, so the code-carrier difference D = code - phi =
  2*I grows at rate dD/dt = 2*dI/dt, and a Hatch filter lagging a
  linear ramp settles at smoothed-minus-code bias -rate*(tau - T).

Conventions: SI units (m, s); deterministic; stdlib math only.  The
methods paraphrase RTCA DO-229 MOPS carrier-smoothing and divergence
concepts in summary form only, never reproducing MOPS text.
"""

import math

# Defaults of the leaf (documented in the SKILL.md workflow).
DEFAULT_TAU = 100.0          # smoothing time constant, s
DEFAULT_T = 1.0              # update interval, s
DEFAULT_SIGMA_CODE = 0.3     # raw code pseudorange noise std, m
DEFAULT_SIGMA_CARRIER = 0.003  # carrier delta-range noise std, m
DEFAULT_WINDOW = 60          # divergence slope-fit window, epochs
DEFAULT_THRESHOLD = 1.0      # divergence alarm threshold, m


def _validate_tau_T(tau, T):
    """Raise ValueError unless 0 < T < tau with both finite."""
    if not math.isfinite(tau) or not math.isfinite(T):
        raise ValueError("tau and T must be finite")
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    if T <= 0.0:
        raise ValueError("T must be positive")
    if T >= tau:
        raise ValueError("T must be below tau so alpha lies in (0, 1)")


def alpha_from_time_constant(tau=DEFAULT_TAU, T=DEFAULT_T):
    """Hatch gain alpha = T/tau in (0, 1), workflow step 1.

    The smoothing configuration is valid only when 0 < T < tau; a
    time constant at or below the update interval means no smoothing.
    """
    _validate_tau_T(tau, T)
    return T / tau


def hatch_update(prev_smoothed, code, carrier_delta_range, alpha):
    """One first-order Hatch recursion step, s_k, workflow step 2.

    Blends the raw code at weight alpha with the previous smoothed
    range carried forward by the carrier delta range at weight
    (1 - alpha).  Raises ValueError on alpha outside (0, 1) or any
    non-finite argument.
    """
    if not math.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie in (0, 1)")
    for name, val in (("prev_smoothed", prev_smoothed), ("code", code),
                      ("carrier_delta_range", carrier_delta_range)):
        if not math.isfinite(val):
            raise ValueError("%s must be finite" % name)
    return alpha * code + (1.0 - alpha) * (prev_smoothed + carrier_delta_range)


def run_hatch_smoother(codes, carrier_phases, tau=DEFAULT_TAU, T=DEFAULT_T):
    """Smoothed range series over the code-carrier stream, step 2.

    The first epoch seeds with the raw code and every later epoch uses
    the phase increment carrier_phases[k] - carrier_phases[k-1] as the
    carrier delta range.  Raises ValueError when the lists differ in
    length, are empty, hold non-finite values, or tau/T fails.
    """
    alpha = alpha_from_time_constant(tau, T)
    if len(codes) != len(carrier_phases):
        raise ValueError("codes and carrier_phases must have equal length")
    if len(codes) < 1:
        raise ValueError("need at least one epoch")
    for k in range(len(codes)):
        if not math.isfinite(codes[k]) or not math.isfinite(carrier_phases[k]):
            raise ValueError("non-finite measurement at epoch %d" % k)
    out = [codes[0]]
    for k in range(1, len(codes)):
        out.append(hatch_update(out[-1], codes[k],
                                carrier_phases[k] - carrier_phases[k - 1],
                                alpha))
    return out


def code_noise_std_smoothed(alpha, sigma_code):
    """Exact steady-state code-only std, workflow step 3 closed form.

    sigma_code*sqrt(alpha/(2 - alpha)): the raw code noise, fed at
    weight alpha into the pole-(1-alpha) recursion, relaxes to this
    value in about tau/2 seconds.  Raises ValueError on alpha outside
    (0, 1) or sigma_code non-positive or non-finite.
    """
    if not math.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie in (0, 1)")
    if not math.isfinite(sigma_code) or sigma_code <= 0.0:
        raise ValueError("sigma_code must be positive and finite")
    return sigma_code * math.sqrt(alpha / (2.0 - alpha))


def noise_reduction_verdict(tau=DEFAULT_TAU, T=DEFAULT_T,
                            sigma_code=DEFAULT_SIGMA_CODE,
                            sigma_carrier=DEFAULT_SIGMA_CARRIER):
    """Noise-reduction verdict dict, workflow step 3.

    Keys: alpha, code_only_std (exact closed form), approx_std (the
    sigma_code/sqrt(2*tau/T) textbook limit), carrier_term_std, the
    total_std (variance is the exact sum of the code and carrier
    terms) and improvement_factor = sigma_code/total_std.
    """
    alpha = alpha_from_time_constant(tau, T)
    if not math.isfinite(sigma_code) or sigma_code <= 0.0:
        raise ValueError("sigma_code must be positive and finite")
    if not math.isfinite(sigma_carrier) or sigma_carrier <= 0.0:
        raise ValueError("sigma_carrier must be positive and finite")
    code_only = code_noise_std_smoothed(alpha, sigma_code)
    approx = sigma_code / math.sqrt(2.0 * tau / T)     # textbook limit
    carrier_term = ((1.0 - alpha) / math.sqrt(alpha * (2.0 - alpha))
                    * sigma_carrier)
    total = math.hypot(code_only, carrier_term)
    return {"alpha": alpha, "code_only_std": code_only, "approx_std": approx,
            "carrier_term_std": carrier_term, "total_std": total,
            "improvement_factor": sigma_code / total}


def _ls_slope(values):
    """Least-squares slope of values versus epoch index (closed form)."""
    n = len(values)
    if n < 2:
        raise ValueError("need at least two points for a slope")
    sx = sum(range(n))
    sy = sum(values)
    sxx = sum(k * k for k in range(n))
    sxy = sum(k * v for k, v in enumerate(values))
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def iono_divergence_rate(code_carrier_diffs, tau=DEFAULT_TAU, T=DEFAULT_T,
                         window=DEFAULT_WINDOW):
    """Code-carrier divergence rate dD/dt in m/s, workflow step 4.

    Fits the least-squares slope of the trailing window of the
    code-carrier difference (code minus carrier phase) and divides by
    T to convert per-epoch slope into per-second rate.  The implied
    ionospheric delay rate is half the returned value.  Raises
    ValueError when window is not an int >= 2, window exceeds the
    epoch count, tau/T fails, or any difference is non-finite.
    """
    _validate_tau_T(tau, T)
    if not isinstance(window, int) or window < 2:
        raise ValueError("window must be an int of at least 2")
    if window > len(code_carrier_diffs):
        raise ValueError("window exceeds the available epoch count")
    for val in code_carrier_diffs:
        if not math.isfinite(val):
            raise ValueError("code-carrier differences must be finite")
    return _ls_slope(code_carrier_diffs[-window:]) / T


def smoothed_iono_bias(rate, tau=DEFAULT_TAU, T=DEFAULT_T):
    """Steady-state smoothed-minus-code bias, workflow step 4 (m).

    A Hatch filter lags a linear ionospheric ramp: at divergence rate
    dD/dt the smoothed range settles -rate*(tau - T) below the raw
    code, the classic code-carrier divergence error whose tau >> T
    form is -2*(dI/dt)*tau.  Raises ValueError on a non-finite rate
    or an invalid tau/T pair.
    """
    if not math.isfinite(rate):
        raise ValueError("rate must be finite")
    _validate_tau_T(tau, T)
    return -rate * (tau - T)


def divergence_check(code_carrier_diffs, tau=DEFAULT_TAU, T=DEFAULT_T,
                     window=DEFAULT_WINDOW, threshold=DEFAULT_THRESHOLD):
    """Divergence alarm dict, workflow step 4.

    Keys: rate (m/s), predicted_bias (m, the steady-state smoothed-
    minus-code error the fitted rate implies), threshold (m) and
    alarm = abs(predicted_bias) > threshold.  Raises ValueError when
    threshold is non-positive or non-finite, plus every
    iono_divergence_rate rejection.
    """
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("threshold must be positive and finite")
    rate = iono_divergence_rate(code_carrier_diffs, tau, T, window)
    bias = smoothed_iono_bias(rate, tau, T)
    return {"rate": rate, "predicted_bias": bias, "threshold": threshold,
            "alarm": abs(bias) > threshold}
