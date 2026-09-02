#!/usr/bin/env python3
"""Structural coupling test (SCT) logic for flight test (paraphrase, common
knowledge).

Structural coupling is the closed-loop coupling of the flight control
system with the airframe structural modes. The flight test measures the
frequency response of the control loop over the band that brackets the
structural modes and derives the stability margins from the measured
amplitude and phase response:

- gain margin: the negative of the amplitude (in dB) at the frequency
  where the phase response crosses -180 degrees;
- phase margin: 180 degrees plus the phase (in degrees) at the
  frequency where the amplitude response crosses 0 dB (unity gain);
- margin verdict: PASS when the measured margins meet the typical 6 dB
  gain margin and 45 degree phase margin criteria of the flutter and
  coupling guidance (standards-map.yaml: far-25 / cs-25 reference-only).

Frequencies in Hz, amplitudes in dB, phases in degrees. Stdlib only.
"""

import math


def _as_float(value, name):
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(f):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return f


def gain_margin(db_at_phase_crossing):
    """Gain margin in dB from the amplitude response at the phase crossing.

    The amplitude (in dB) at the frequency where the phase crosses
    -180 degrees is the gain still available before the loop goes
    unstable; a negative amplitude gives a negative margin, which
    fails the criterion.

    Raises ValueError when the input is not a finite number.
    """
    db = _as_float(db_at_phase_crossing, "amplitude at phase crossing")
    return -db


def phase_margin(phase_deg_at_gain_crossing):
    """Phase margin in degrees from the phase at the gain crossing.

    The phase (in degrees) at the frequency where the amplitude crosses
    0 dB (unity gain) is measured against -180 degrees; the margin is
    the distance from that phase to -180 degrees.

    Raises ValueError when the input is not a finite number.
    """
    phase = _as_float(phase_deg_at_gain_crossing, "phase at gain crossing")
    return 180.0 + phase


def margin_verdict(gain_db, phase_deg, gain_limit_db=6.0, phase_limit_deg=45.0):
    """PASS/FAIL verdict against the margin criteria.

    PASS when gain_db >= gain_limit_db and phase_deg >= phase_limit_deg.
    Returns a dict with the verdict and the margins:
      {"verdict": "PASS"|"FAIL", "gain_margin_db": float,
       "phase_margin_deg": float, "gain_limit_db": float,
       "phase_limit_deg": float}

    Raises ValueError when any input is not a finite number or a limit
    is not positive.
    """
    gm = _as_float(gain_db, "gain margin")
    pm = _as_float(phase_deg, "phase margin")
    gl = _as_float(gain_limit_db, "gain limit")
    pl = _as_float(phase_limit_deg, "phase limit")
    if gl <= 0 or pl <= 0:
        raise ValueError("margin limits must be positive, got %r" % ((gl, pl),))
    verdict = "PASS" if gm >= gl and pm >= pl else "FAIL"
    return {
        "verdict": verdict,
        "gain_margin_db": gm,
        "phase_margin_deg": pm,
        "gain_limit_db": gl,
        "phase_limit_deg": pl,
    }


def _check_response(freqs, values, name):
    if len(freqs) != len(values):
        raise ValueError(
            "%s: frequency and value lists must match in length, "
            "got %d and %d" % (name, len(freqs), len(values))
        )
    if len(freqs) < 2:
        raise ValueError(
            "%s: at least two points required, got %d" % (name, len(freqs))
        )
    for f in freqs:
        if f <= 0:
            raise ValueError(
                "%s: frequencies must be positive, got %r" % (name, freqs)
            )
    for i in range(1, len(freqs)):
        if freqs[i] <= freqs[i - 1]:
            raise ValueError(
                "%s: frequencies must be strictly increasing, got %r" % (name, freqs)
            )
    vals = [_as_float(v, name + " value") for v in values]
    return [float(f) for f in freqs], vals


def interpolate_response(freqs, values, target_freq):
    """Linear interpolation of a response (dB or degrees) at target_freq.

    Raises ValueError when the response lists are malformed or the
    target frequency sits outside the measured band.
    """
    f, v = _check_response(freqs, values, "interpolate_response")
    t = _as_float(target_freq, "target frequency")
    if t < f[0] or t > f[-1]:
        raise ValueError(
            "interpolate_response: target %r outside band [%r, %r]"
            % (t, f[0], f[-1])
        )
    i = 0
    while i + 1 < len(f) and f[i + 1] < t:
        i += 1
    frac = (t - f[i]) / (f[i + 1] - f[i])
    return v[i] + frac * (v[i + 1] - v[i])


def _crossing_frequency(freqs, values, target, name):
    f, v = _check_response(freqs, values, name)
    t = _as_float(target, name + " target")
    for i in range(len(f) - 1):
        a, b = v[i], v[i + 1]
        if (a - t) * (b - t) <= 0 and a != b:
            frac = (t - a) / (b - a)
            return f[i] + frac * (f[i + 1] - f[i])
    return None


def phase_crossing_frequency(freqs, phase_deg, target_phase=-180.0):
    """Frequency where the phase response crosses target_phase.

    Returns the linearly interpolated frequency of the first crossing,
    or None when the phase never crosses the target in the measured
    band. Raises ValueError on malformed input.
    """
    return _crossing_frequency(freqs, phase_deg, target_phase, "phase_crossing_frequency")


def gain_crossing_frequency(freqs, mag_db, target_db=0.0):
    """Frequency where the amplitude response crosses target_db (0 dB).

    Returns the first interpolated crossing frequency, or None when the
    amplitude never crosses the target in the measured band. Raises
    ValueError on malformed input.
    """
    return _crossing_frequency(freqs, mag_db, target_db, "gain_crossing_frequency")


def gain_margin_from_response(freqs, mag_db, phase_deg):
    """Gain margin in dB from the measured amplitude and phase response.

    Finds the phase crossing of -180 degrees, interpolates the amplitude
    there, and returns the gain margin. Returns None when the phase never
    crosses -180 degrees in the measured band. Raises ValueError on
    malformed input.
    """
    f_cross = phase_crossing_frequency(freqs, phase_deg, -180.0)
    if f_cross is None:
        return None
    amp = interpolate_response(freqs, mag_db, f_cross)
    return gain_margin(amp)


def phase_margin_from_response(freqs, mag_db, phase_deg):
    """Phase margin in degrees from the measured amplitude and phase response.

    Finds the gain crossing of 0 dB, interpolates the phase there, and
    returns the phase margin. Returns None when the amplitude never
    crosses 0 dB in the measured band. Raises ValueError on malformed
    input.
    """
    f_cross = gain_crossing_frequency(freqs, mag_db, 0.0)
    if f_cross is None:
        return None
    ph = interpolate_response(freqs, phase_deg, f_cross)
    return phase_margin(ph)


def excitation_frequencies(f_min, f_max, points_per_decade=10.0):
    """Log-spaced excitation frequencies for the swept sine or chirp sweep.

    Returns n = int(round(points_per_decade * log10(f_max / f_min))) + 1
    frequencies from f_min to f_max inclusive, geometrically spaced so
    the band is covered evenly per decade.

    Raises ValueError when f_min <= 0, f_max <= f_min, or
    points_per_decade <= 0.
    """
    lo = _as_float(f_min, "minimum frequency")
    hi = _as_float(f_max, "maximum frequency")
    ppd = _as_float(points_per_decade, "points per decade")
    if lo <= 0:
        raise ValueError("minimum frequency must be > 0, got %r" % (lo,))
    if hi <= lo:
        raise ValueError(
            "maximum frequency must be > minimum, got %r" % ((lo, hi),)
        )
    if ppd <= 0:
        raise ValueError("points per decade must be > 0, got %r" % (ppd,))
    decades = math.log10(hi / lo)
    n = int(round(ppd * decades)) + 1
    if n < 2:
        n = 2
    ratio = hi / lo
    return [lo * ratio ** (i / (n - 1)) for i in range(n)]
