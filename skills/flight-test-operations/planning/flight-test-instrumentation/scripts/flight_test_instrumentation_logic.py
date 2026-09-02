#!/usr/bin/env python3
"""Flight test instrumentation design logic (paraphrase, common
measurement methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25
reference-only context): flight test instrumentation must cover the
measurement parameters (air data, accelerations, angular rates,
strain, control positions, engine data) with sensors whose range,
accuracy, and bandwidth fit the signal, and a data acquisition chain
sampled above the Nyquist rate so the recorded signal is a faithful
copy of the measured one. The checks here cover the Nyquist
criterion, the sensor range verdict, the ADC quantization
resolution, the required sample rate, and calibration currency
before the test. Units stay SI (Hz, V, g, N).
"""


def nyquist_ok(sample_rate, max_freq):
    """Check that the sample rate is at least twice the max frequency.

    The Nyquist criterion: a signal of maximum frequency max_freq can
    be reconstructed from samples taken at sample_rate only when
    sample_rate >= 2 * max_freq. Below that rate, aliasing folds high
    frequencies into the passband. Units: Hz.

    Returns True when sample_rate >= 2 * max_freq, else False.

    Raises ValueError on a non-numeric (or bool) input, a
    non-positive sample_rate, or a non-positive max_freq.
    """
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, float)):
        raise ValueError("sample_rate must be numeric, got %r" % (sample_rate,))
    if isinstance(max_freq, bool) or not isinstance(max_freq, (int, float)):
        raise ValueError("max_freq must be numeric, got %r" % (max_freq,))
    if sample_rate <= 0:
        raise ValueError("sample_rate must be > 0, got %r" % (sample_rate,))
    if max_freq <= 0:
        raise ValueError("max_freq must be > 0, got %r" % (max_freq,))
    return sample_rate >= 2 * max_freq


def sensor_range_verdict(measured_value, sensor_range):
    """Verdict for a measured value against a symmetric sensor range.

    A sensor with full-scale range sensor_range (same unit as
    measured_value, SI) measures values in [-sensor_range,
    +sensor_range]. The value is "ok" when |measured_value| <=
    sensor_range, else "over-range". An over-range measurement is
    clipped by the sensor and is not trustworthy.

    Returns "ok" or "over-range".

    Raises ValueError on a non-numeric (or bool) measured_value, a
    non-numeric (or bool) sensor_range, or sensor_range <= 0.
    """
    if isinstance(measured_value, bool) or not isinstance(
        measured_value, (int, float)
    ):
        raise ValueError(
            "measured_value must be numeric, got %r" % (measured_value,)
        )
    if isinstance(sensor_range, bool) or not isinstance(sensor_range, (int, float)):
        raise ValueError("sensor_range must be numeric, got %r" % (sensor_range,))
    if sensor_range <= 0:
        raise ValueError("sensor_range must be > 0, got %r" % (sensor_range,))
    return "ok" if abs(measured_value) <= sensor_range else "over-range"


def quantization_error(bits, range_value):
    """Resolution (1 LSB) of an ideal N-bit ADC over a full-scale range.

    An ideal N-bit converter digitizes the full-scale span range_value
    into 2**bits steps, so the resolution (size of one
    least-significant bit) is range_value / 2**bits. The worst-case
    quantization error is half the resolution. range_value is in the
    ADC input unit (V for voltage channels).

    Returns the resolution as a float.

    Raises ValueError on a non-int (or bool) bits value with bits < 1,
    or a non-numeric (or bool) range_value with range_value <= 0.
    """
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise ValueError("bits must be an int, got %r" % (bits,))
    if bits < 1:
        raise ValueError("bits must be >= 1, got %r" % (bits,))
    if isinstance(range_value, bool) or not isinstance(range_value, (int, float)):
        raise ValueError("range_value must be numeric, got %r" % (range_value,))
    if range_value <= 0:
        raise ValueError("range_value must be > 0, got %r" % (range_value,))
    return range_value / (2 ** bits)


def required_sample_rate(max_freq, margin=2.5):
    """Required sample rate: margin times the Nyquist rate.

    The Nyquist criterion demands sample_rate >= 2 * max_freq; a
    practical acquisition chain samples above that to leave headroom
    for the anti-aliasing filter rolloff. The required rate is
    margin * 2 * max_freq, with a default margin of 2.5 (so 5 times
    the max frequency by default). Units: Hz.

    Returns the required sample rate as a float.

    Raises ValueError on a non-numeric (or bool) max_freq with
    max_freq <= 0, or a non-numeric (or bool) margin with margin <= 0.
    """
    if isinstance(max_freq, bool) or not isinstance(max_freq, (int, float)):
        raise ValueError("max_freq must be numeric, got %r" % (max_freq,))
    if max_freq <= 0:
        raise ValueError("max_freq must be > 0, got %r" % (max_freq,))
    if isinstance(margin, bool) or not isinstance(margin, (int, float)):
        raise ValueError("margin must be numeric, got %r" % (margin,))
    if margin <= 0:
        raise ValueError("margin must be > 0, got %r" % (margin,))
    return margin * 2 * max_freq


def calibration_verdict(calibrated, due):
    """Calibration currency verdict before the test.

    calibrated: True when the instrument was calibrated before the
    test. due: True when recalibration is due (the calibration
    interval has lapsed). A channel is usable only when it is
    calibrated AND recalibration is not due.

    Returns True when the calibration is current, else False.

    Raises ValueError when either input is not a bool.
    """
    for name, val in (("calibrated", calibrated), ("due", due)):
        if not isinstance(val, bool):
            raise ValueError("%s must be a bool, got %r" % (name, val))
    return calibrated and not due
