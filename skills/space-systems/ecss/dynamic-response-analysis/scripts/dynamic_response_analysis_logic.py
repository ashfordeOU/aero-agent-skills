"""
Dynamic response analysis logic per ECSS-E-ST-32C, clause 4.6.2.5.

Implements:
  - Dynamic amplification factor (DAF) for swept-sine response of a SDOF oscillator
  - Miles' equation for broadband random-vibration RMS and 3-sigma acceleration
  - Shock response spectrum (SRS) approximation for a half-sine pulse
  - Load-type categorization and per-event summary

stdlib only. Offline. Deterministic.
"""

import math

__all__ = [
    "AnalysisInputError",
    "dynamic_amplification_factor",
    "sine_peak_response",
    "miles_rms_acceleration",
    "miles_3sigma_acceleration",
    "srs_half_sine_peak",
    "categorize_load",
    "analysis_summary",
]

VALID_LOAD_TYPES = frozenset({"sine", "random", "shock", "transient"})


class AnalysisInputError(ValueError):
    """Raised when a caller supplies an out-of-range or unrecognized input."""


def _check_positive(value, name):
    if not (value > 0):
        raise AnalysisInputError(f"{name} must be strictly positive; got {value!r}")


def _check_damping(zeta):
    if not (0 < zeta < 1):
        raise AnalysisInputError(
            f"Damping ratio must be in the open interval (0, 1); got {zeta!r}"
        )


def dynamic_amplification_factor(fn_hz, f_hz, damping_ratio):
    """
    Return the dynamic amplification factor (DAF) for a single-DOF oscillator.

    DAF = 1 / sqrt[(1 - r^2)^2 + (2*zeta*r)^2]
    where r = f_hz / fn_hz (tuning ratio).

    At resonance (r = 1): DAF = 1 / (2 * damping_ratio).
    At f_hz = 0 (static):  DAF = 1.0.

    Parameters
    ----------
    fn_hz : float
        Natural frequency of the oscillator (Hz). Must be > 0.
    f_hz : float
        Excitation frequency (Hz). Must be >= 0.
    damping_ratio : float
        Critical damping ratio zeta. Must be in (0, 1).

    Returns
    -------
    float
        DAF (dimensionless, >= 0).
    """
    _check_positive(fn_hz, "fn_hz")
    if f_hz < 0:
        raise AnalysisInputError(f"f_hz must be non-negative; got {f_hz!r}")
    _check_damping(damping_ratio)

    r = f_hz / fn_hz
    denominator = math.sqrt((1.0 - r * r) ** 2 + (2.0 * damping_ratio * r) ** 2)
    if denominator == 0.0:
        raise AnalysisInputError(
            "DAF denominator is zero (exact undamped resonance with zero damping)"
        )
    return 1.0 / denominator


def sine_peak_response(static_response, fn_hz, f_hz, damping_ratio):
    """
    Return the peak dynamic response for a sine-excited SDOF oscillator.

    peak_response = static_response * DAF(fn_hz, f_hz, damping_ratio)

    Parameters
    ----------
    static_response : float
        Equivalent static response (any unit, e.g. N, m, g). Must be >= 0.
    fn_hz : float
        Natural frequency (Hz). Must be > 0.
    f_hz : float
        Excitation frequency (Hz). Must be >= 0.
    damping_ratio : float
        Critical damping ratio. Must be in (0, 1).

    Returns
    -------
    float
        Peak dynamic response in the same unit as static_response.
    """
    if static_response < 0:
        raise AnalysisInputError(
            f"static_response must be non-negative; got {static_response!r}"
        )
    daf = dynamic_amplification_factor(fn_hz, f_hz, damping_ratio)
    return static_response * daf


def miles_rms_acceleration(fn_hz, damping_ratio, psd_g2_per_hz):
    """
    Compute the RMS acceleration response via Miles' equation.

    RMS = sqrt(pi/2 * fn * Q * W)
    where Q = 1 / (2 * damping_ratio) and W is the input PSD at fn (g^2/Hz).

    Assumes a flat (white-noise) input PSD evaluated at the natural frequency.

    Parameters
    ----------
    fn_hz : float
        Natural frequency (Hz). Must be > 0.
    damping_ratio : float
        Critical damping ratio. Must be in (0, 1).
    psd_g2_per_hz : float
        Input power spectral density at fn (g^2/Hz). Must be > 0.

    Returns
    -------
    float
        RMS acceleration (g).
    """
    _check_positive(fn_hz, "fn_hz")
    _check_damping(damping_ratio)
    _check_positive(psd_g2_per_hz, "psd_g2_per_hz")

    quality_factor = 1.0 / (2.0 * damping_ratio)
    return math.sqrt((math.pi / 2.0) * fn_hz * quality_factor * psd_g2_per_hz)


def miles_3sigma_acceleration(fn_hz, damping_ratio, psd_g2_per_hz):
    """
    Return the 3-sigma (design-limit) acceleration = 3 * RMS.

    See miles_rms_acceleration for parameter descriptions.

    Returns
    -------
    float
        3-sigma acceleration (g).
    """
    return 3.0 * miles_rms_acceleration(fn_hz, damping_ratio, psd_g2_per_hz)


def srs_half_sine_peak(fn_hz, pulse_amplitude_g, pulse_duration_s):
    """
    Approximate peak SRS acceleration for a half-sine shock pulse.

    Uses a piecewise approximation based on the dimensionless product
    tau = fn_hz * pulse_duration_s:

    * tau < 0.5  (residual region):  SRS ≈ 2*pi*tau*A
    * 0.5 <= tau < 1.0 (transitional): SRS ≈ 2*A*sin(pi*tau)
    * tau >= 1.0 (primary region):  SRS = min(A*(1 + |sin(pi*tau)|), 2*A)

    Parameters
    ----------
    fn_hz : float
        Natural frequency of the SDOF oscillator (Hz). Must be > 0.
    pulse_amplitude_g : float
        Half-sine pulse peak amplitude (g). Must be > 0.
    pulse_duration_s : float
        Half-sine pulse duration (s). Must be > 0.

    Returns
    -------
    float
        SRS peak absolute acceleration (g).
    """
    _check_positive(fn_hz, "fn_hz")
    _check_positive(pulse_amplitude_g, "pulse_amplitude_g")
    _check_positive(pulse_duration_s, "pulse_duration_s")

    tau = fn_hz * pulse_duration_s

    if tau < 0.5:
        return 2.0 * math.pi * tau * pulse_amplitude_g
    elif tau < 1.0:
        return 2.0 * pulse_amplitude_g * math.sin(math.pi * tau)
    else:
        primary = pulse_amplitude_g * (1.0 + abs(math.sin(math.pi * tau)))
        return min(primary, 2.0 * pulse_amplitude_g)


def categorize_load(load_type_str):
    """
    Categorize a load event string into one of four recognized types:
    'sine', 'random', 'shock', 'transient'.

    Matching is case-insensitive and strips leading/trailing whitespace.
    Raises AnalysisInputError for any unrecognized type.

    Parameters
    ----------
    load_type_str : str
        Raw load type string from the mechanical environment specification.

    Returns
    -------
    str
        Canonical lower-case category string.
    """
    normalized = load_type_str.strip().lower()
    if normalized not in VALID_LOAD_TYPES:
        raise AnalysisInputError(
            f"Unrecognized load type {load_type_str!r}. "
            f"Expected one of: {sorted(VALID_LOAD_TYPES)}"
        )
    return normalized


def analysis_summary(fn_hz, damping_ratio, load_type, **kwargs):
    """
    Run the appropriate dynamic response calculation for a load event.

    Parameters
    ----------
    fn_hz : float
        Natural frequency (Hz). Must be > 0.
    damping_ratio : float
        Critical damping ratio. Must be in (0, 1).
    load_type : str
        Load category: 'sine', 'random', 'shock', or 'transient'.
    **kwargs :
        sine   -> f_exc_hz (float), static_response (float)
        random -> psd_g2_per_hz (float)
        shock  -> pulse_amplitude_g (float), pulse_duration_s (float)
        transient -> (no additional kwargs required)

    Returns
    -------
    dict
        Keys vary by load type:
        sine:      load_type, daf, peak_response, unit
        random:    load_type, rms_g, sigma3_g, unit
        shock:     load_type, tau, srs_g, unit
        transient: load_type, note
    """
    category = categorize_load(load_type)

    if category == "sine":
        f_exc = kwargs.get("f_exc_hz")
        static_resp = kwargs.get("static_response")
        if f_exc is None or static_resp is None:
            raise AnalysisInputError(
                "Sine analysis requires keyword arguments f_exc_hz and static_response"
            )
        daf = dynamic_amplification_factor(fn_hz, f_exc, damping_ratio)
        peak = sine_peak_response(static_resp, fn_hz, f_exc, damping_ratio)
        return {
            "load_type": category,
            "daf": daf,
            "peak_response": peak,
            "unit": "same_as_static_response",
        }

    if category == "random":
        psd = kwargs.get("psd_g2_per_hz")
        if psd is None:
            raise AnalysisInputError(
                "Random analysis requires keyword argument psd_g2_per_hz"
            )
        rms = miles_rms_acceleration(fn_hz, damping_ratio, psd)
        return {
            "load_type": category,
            "rms_g": rms,
            "sigma3_g": 3.0 * rms,
            "unit": "g",
        }

    if category == "shock":
        amp = kwargs.get("pulse_amplitude_g")
        dur = kwargs.get("pulse_duration_s")
        if amp is None or dur is None:
            raise AnalysisInputError(
                "Shock analysis requires keyword arguments pulse_amplitude_g "
                "and pulse_duration_s"
            )
        tau = fn_hz * dur
        srs = srs_half_sine_peak(fn_hz, amp, dur)
        return {
            "load_type": category,
            "tau": tau,
            "srs_g": srs,
            "unit": "g",
        }

    # transient
    return {
        "load_type": category,
        "note": "transient load requires time-domain numerical integration; "
                "Miles equation and DAF do not apply",
    }
