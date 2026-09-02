#!/usr/bin/env python3
"""Dynamic stability flight test logic: excitation, identification,
and handling qualities verdicts (paraphrase, common flight test
methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: public
domain / free-download regulation context): the dynamic stability
flight test excites each mode with a control input (elevator doublet
for the short period, elevator pulse for the phugoid, rudder pulse for
the Dutch roll, aileron step for roll subsidence, rudder step for the
spiral), records the response time history, and identifies the mode
from the decaying oscillation: log decrement delta = (1/n) ln(A0/An),
damping ratio zeta = delta / sqrt(delta^2 + 4 pi^2), damped frequency
w_d = 2 pi / T_d, undamped natural frequency w_n = w_d / sqrt(1 -
zeta^2), time to half amplitude t_half = ln(2) / (zeta w_n). The
certification requirement (paraphrased) is that short period and Dutch
roll oscillations be damped and the phugoid not be divergent; the
band values used here are typical flight test practice and the cited
standards take precedence.

Pure stdlib (math only), deterministic, offline.
"""

import math

TWO_PI = 2.0 * math.pi
LN2 = math.log(2.0)

EXCITATION_TECHNIQUES = {
    "short-period": {
        "control": "elevator",
        "technique": "elevator doublet (push-pull-push) or pulse",
        "amplitude": "small, 1 to 2 degrees",
        "notes": "excite the pitch short period without engaging the phugoid; "
                 "release and record the decaying oscillation",
    },
    "phugoid": {
        "control": "elevator",
        "technique": "elevator pulse or push-pull step",
        "amplitude": "small speed change, 5 to 10 knots",
        "notes": "hold a small pitch disturbance, then hands-off; the phugoid "
                 "period is long, record 2 to 3 full cycles",
    },
    "dutch-roll": {
        "control": "rudder",
        "technique": "rudder pulse or rudder doublet",
        "amplitude": "1 to 2 degrees rudder",
        "notes": "wings level, excite yaw; record the coupled roll-yaw "
                 "oscillation until it damps",
    },
    "roll-subsidence": {
        "control": "aileron",
        "technique": "aileron step input",
        "amplitude": "small step, one third to one half aileron",
        "notes": "step, hold, release; the roll mode is aperiodic, estimate "
                 "the time constant from the exponential decay",
    },
    "spiral": {
        "control": "rudder",
        "technique": "rudder step, hold a small bank angle",
        "amplitude": "small step",
        "notes": "establish a small bank angle, release controls; observe "
                 "convergence or divergence over 20 to 30 seconds",
    },
}

VERDICT_BANDS = {
    "short-period": (
        (2.0, 2.0, "acceptable", "aperiodic, heavily damped, no oscillation"),
        (0.3, 2.0, "acceptable", "well damped"),
        (0.08, 0.3, "marginal", "lightly damped, review the band"),
        (None, 0.08, "inadequate", "poorly damped"),
    ),
    "phugoid": (
        (0.04, 2.0, "acceptable", "positively damped"),
        (0.0, 0.04, "marginal", "near neutral, review the band"),
        (None, 0.0, "inadequate", "neutral or divergent"),
    ),
    "dutch-roll": (
        (0.08, 2.0, "acceptable", "positively damped"),
        (0.02, 0.08, "marginal", "lightly damped, review the band"),
        (None, 0.02, "inadequate", "near neutral or divergent"),
    ),
    "roll-subsidence": (
        (1.0, 2.0, "acceptable", "aperiodic convergence as expected"),
        (None, 1.0, "marginal", "oscillatory roll mode, investigate"),
    ),
    "spiral": (
        (0.0, 2.0, "acceptable", "convergent"),
        (None, 0.0, "inadequate", "divergent, time to double applies"),
    ),
}


def log_decrement(first_amplitude, last_amplitude, cycles):
    """Log decrement delta = (1/n) ln(A0/An), dimensionless.

    first_amplitude A0 and last_amplitude An are peak amplitudes of the
    same sign taken n = cycles whole cycles apart. Raises ValueError
    when cycles < 1 or when either amplitude is non-positive.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1, got %r" % (cycles,))
    if first_amplitude <= 0:
        raise ValueError(
            "first amplitude must be > 0, got %r" % (first_amplitude,)
        )
    if last_amplitude <= 0:
        raise ValueError(
            "last amplitude must be > 0, got %r" % (last_amplitude,)
        )
    if last_amplitude >= first_amplitude:
        # A growing or equal amplitude means no decay was measured.
        if last_amplitude == first_amplitude:
            raise ValueError("amplitudes equal: no decay measured")
        raise ValueError("last amplitude exceeds first: mode is not decaying")
    return math.log(first_amplitude / last_amplitude) / cycles


def damping_ratio_from_decrement(delta):
    """Damping ratio from the log decrement: zeta = delta / sqrt(delta^2
    + 4 pi^2), dimensionless.

    Exact for a linear second-order mode. For small delta, zeta is
    about delta / (2 pi). Raises ValueError when delta < 0 (a growing
    oscillation is not a damped mode).
    """
    if delta < 0:
        raise ValueError("log decrement must be >= 0, got %r" % (delta,))
    return delta / math.sqrt(delta * delta + TWO_PI * TWO_PI)


def damped_frequency_from_period(period_seconds):
    """Damped natural frequency, rad/s and Hz, from the peak period T_d.

    w_d = 2 pi / T_d. Raises ValueError when the period is non-positive.
    """
    if period_seconds <= 0:
        raise ValueError(
            "peak period must be > 0, got %r" % (period_seconds,)
        )
    rad = TWO_PI / period_seconds
    return {"damped_frequency_rad_s": rad, "damped_frequency_hz": rad / TWO_PI}


def undamped_natural_frequency(damped_frequency_rad_s, damping_ratio):
    """Undamped natural frequency w_n = w_d / sqrt(1 - zeta^2), rad/s.

    Valid for an under-damped mode (zeta < 1). Raises ValueError when
    the damped frequency is non-positive or zeta >= 1.
    """
    if damped_frequency_rad_s <= 0:
        raise ValueError(
            "damped frequency must be > 0, got %r" % (damped_frequency_rad_s,)
        )
    if damping_ratio >= 1.0:
        raise ValueError(
            "damping ratio must be < 1 for an oscillatory mode, got %r"
            % (damping_ratio,)
        )
    return damped_frequency_rad_s / math.sqrt(1.0 - damping_ratio * damping_ratio)


def time_to_half_amplitude(damping_ratio, undamped_frequency_rad_s):
    """Time to half amplitude t_half = ln(2) / (zeta w_n), seconds.

    The damped oscillation envelope e^(-zeta w_n t) reaches half after
    t_half. Raises ValueError when damping_ratio <= 0 or the frequency
    is non-positive.
    """
    if damping_ratio <= 0:
        raise ValueError(
            "damping ratio must be > 0, got %r" % (damping_ratio,)
        )
    if undamped_frequency_rad_s <= 0:
        raise ValueError(
            "undamped frequency must be > 0, got %r" % (undamped_frequency_rad_s,)
        )
    return LN2 / (damping_ratio * undamped_frequency_rad_s)


def time_to_double_amplitude(damping_ratio, undamped_frequency_rad_s):
    """Time to double amplitude t_double = ln(2) / (|zeta| w_n), seconds.

    For a divergent mode (zeta < 0), the envelope grows as
    e^(|zeta| w_n t). Raises ValueError when damping_ratio >= 0 or the
    frequency is non-positive.
    """
    if damping_ratio >= 0:
        raise ValueError(
            "damping ratio must be < 0 for a divergent mode, got %r"
            % (damping_ratio,)
        )
    if undamped_frequency_rad_s <= 0:
        raise ValueError(
            "undamped frequency must be > 0, got %r" % (undamped_frequency_rad_s,)
        )
    return LN2 / (abs(damping_ratio) * undamped_frequency_rad_s)


def cycles_to_half_amplitude(damping_ratio):
    """Cycles to half amplitude N = ln(2) / (2 pi zeta), dimensionless.

    Each cycle of a second-order mode attenuates the envelope by
    e^(-2 pi zeta). Raises ValueError when damping_ratio <= 0.
    """
    if damping_ratio <= 0:
        raise ValueError(
            "damping ratio must be > 0, got %r" % (damping_ratio,)
        )
    return LN2 / (TWO_PI * damping_ratio)


def local_maxima(samples):
    """Indices of strict local maxima in a 1-D sample list.

    sample[i] is a local maximum when it is strictly greater than both
    neighbors (interior points only). Deterministic, stdlib only.
    """
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a list or tuple")
    peaks = []
    for i in range(1, len(samples) - 1):
        if samples[i] > samples[i - 1] and samples[i] > samples[i + 1]:
            peaks.append(i)
    return peaks


def mode_identification(peak_values, peak_times):
    """Identify a mode from the decaying peak sequence, dict of floats.

    peak_values are the same-sign peak amplitudes A0..An in order and
    peak_times their timestamps. Uses n = len(peak_values) - 1 cycles,
    the log decrement, the damping ratio, and the mean peak period.
    Returns decrement, damping_ratio, period_s, damped_frequency_hz,
    damped_frequency_rad_s, undamped_frequency_rad_s (None when
    zeta >= 1), time_to_half_s (None when zeta >= 1), and cycles_used.
    Raises ValueError for fewer than 2 peaks, mismatched lengths,
    non-positive amplitudes, non-ascending times, or no decay.
    """
    if len(peak_values) < 2:
        raise ValueError("need at least 2 peaks, got %d" % len(peak_values))
    if len(peak_times) != len(peak_values):
        raise ValueError(
            "peak_times length %d != peak_values length %d"
            % (len(peak_times), len(peak_values))
        )
    times = list(peak_times)
    if any(t2 <= t1 for t1, t2 in zip(times, times[1:])):
        raise ValueError("peak times must be strictly ascending")
    cycles = len(peak_values) - 1
    delta = log_decrement(peak_values[0], peak_values[-1], cycles)
    zeta = damping_ratio_from_decrement(delta)
    period = (times[-1] - times[0]) / cycles
    damped = damped_frequency_from_period(period)
    undamped = None
    t_half = None
    if zeta < 1.0:
        undamped = undamped_natural_frequency(
            damped["damped_frequency_rad_s"], zeta
        )
        t_half = time_to_half_amplitude(zeta, undamped)
    return {
        "decrement": delta,
        "damping_ratio": zeta,
        "period_s": period,
        "damped_frequency_hz": damped["damped_frequency_hz"],
        "damped_frequency_rad_s": damped["damped_frequency_rad_s"],
        "undamped_frequency_rad_s": undamped,
        "time_to_half_s": t_half,
        "cycles_used": cycles,
    }


def excitation_technique(mode):
    """Recommended excitation for a mode, dict.

    mode is one of short-period, phugoid, dutch-roll, roll-subsidence,
    spiral. Returns the control, technique, amplitude, and notes.
    Raises ValueError for an unknown mode.
    """
    try:
        return dict(EXCITATION_TECHNIQUES[mode])
    except KeyError:
        raise ValueError(
            "unknown mode %r; expected one of %s"
            % (mode, ", ".join(sorted(EXCITATION_TECHNIQUES)))
        )


def handling_qualities_verdict(mode, damping_ratio):
    """Handling qualities verdict for a measured mode damping, dict.

    band/verdict from the typical flight test practice bands in
    VERDICT_BANDS (certification values in the cited standards take
    precedence). Returns mode, damping_ratio, band, verdict, and a
    note. Raises ValueError for an unknown mode.
    """
    if mode not in VERDICT_BANDS:
        raise ValueError(
            "unknown mode %r; expected one of %s"
            % (mode, ", ".join(sorted(VERDICT_BANDS)))
        )
    for low, high, verdict, note in VERDICT_BANDS[mode]:
        if low is None:
            if damping_ratio < high:
                return {
                    "mode": mode,
                    "damping_ratio": damping_ratio,
                    "band": "below %g" % high,
                    "verdict": verdict,
                    "note": note,
                }
        elif high == low:
            if damping_ratio > low:
                return {
                    "mode": mode,
                    "damping_ratio": damping_ratio,
                    "band": "above %g" % low,
                    "verdict": verdict,
                    "note": note,
                }
        elif low <= damping_ratio <= high:
            return {
                "mode": mode,
                "damping_ratio": damping_ratio,
                "band": "%g to %g" % (low, high),
                "verdict": verdict,
                "note": note,
            }
    # Fall through: damping_ratio above the top band of the last entry.
    top_verdict = VERDICT_BANDS[mode][0]
    return {
        "mode": mode,
        "damping_ratio": damping_ratio,
        "band": "above %g" % top_verdict[1],
        "verdict": top_verdict[2],
        "note": top_verdict[3],
    }
