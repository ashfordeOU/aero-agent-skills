"""In-flight mechanical vibration survey reduction (order domain).

Pure-stdlib reduction of measured accelerometer time histories into
per-rev (N/rev) order amplitudes, windowed total RMS survey levels and
pass or needs-trim verdicts, for rotorcraft main-rotor track-and-balance
surveys, airframe vibration limit checks and fixed-wing vibration or
buzz surveys.

Conventions implemented here:
- The survey segment is an integer-revolution window of N samples with
  N = round(m_revs * sample_rate_hz / rotor_hz); round to the nearest
  integer sample count. For synthetic work choose parameters that make
  N exact (the worked example uses N = 12 * 1000 / 5 = 2400).
- order_amplitude uses the first N samples of the record; a record
  shorter than one full window raises ValueError.
- The synchronous DFT bin for order p is p * m_revs, so a p-per-rev
  component falls exactly on one DFT bin of the m-rev window.
- windowed_rms slides with hop equal to the window; a trailing partial
  window is dropped.
- Vibration verdict margin = (limit - level) / limit, pass when the
  margin is >= 0. The 1P trim verdict applies the same margin to the
  1P component against the trim limit, needs_trim when margin < 0.
"""

import math


def _require_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %s" % (name, value))


def order_amplitude(samples, sample_rate_hz, rotor_hz, order, m_revs):
    """Synchronous order DFT amplitude A_p = (2/N)|sum x_k exp(-j 2 pi
    (p m) k / N)| over the first N samples of the integer-revolution
    window, N = round(m_revs * sample_rate_hz / rotor_hz).

    Returns the single-sided amplitude in the units of the samples (g
    for accelerometer records). ValueErrors on empty samples and on
    non-positive sample rate, rotor frequency, order below 1 or
    m_revs below 1.
    """
    if not samples:
        raise ValueError("samples must not be empty")
    _require_positive(sample_rate_hz, "sample_rate_hz")
    _require_positive(rotor_hz, "rotor_hz")
    _require_positive(order, "order")
    _require_positive(m_revs, "m_revs")
    if order < 1:
        raise ValueError("order must be >= 1, got %s" % (order,))
    if m_revs < 1:
        raise ValueError("m_revs must be >= 1, got %s" % (m_revs,))
    n_window = int(round(m_revs * sample_rate_hz / rotor_hz))
    if n_window < 1:
        raise ValueError("window sample count rounds below 1 sample")
    if len(samples) < n_window:
        raise ValueError(
            "record has %d samples, shorter than one %d-sample "
            "integer-rev window" % (len(samples), n_window))
    bin_index = order * m_revs
    phase_step = 2.0 * math.pi * bin_index / n_window
    re_sum = 0.0
    im_sum = 0.0
    for k, x_k in enumerate(samples[:n_window]):
        angle = phase_step * k
        re_sum += x_k * math.cos(angle)
        im_sum -= x_k * math.sin(angle)
    return 2.0 * math.hypot(re_sum, im_sum) / n_window


def total_rms(samples):
    """Total RMS of the record: sqrt(mean(x^2)). ValueError on empty."""
    if not samples:
        raise ValueError("samples must not be empty")
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def windowed_rms(samples, sample_rate_hz, window_s):
    """List of RMS levels per window; the window slides with hop equal
    to the window length and a trailing partial window is dropped.
    ValueError on empty samples and non-positive rate or window.
    """
    if not samples:
        raise ValueError("samples must not be empty")
    _require_positive(sample_rate_hz, "sample_rate_hz")
    _require_positive(window_s, "window_s")
    n_window = int(round(window_s * sample_rate_hz))
    if n_window < 1:
        raise ValueError("window sample count rounds below 1 sample")
    levels = []
    start = 0
    while start + n_window <= len(samples):
        window = samples[start:start + n_window]
        mean_sq = sum(x * x for x in window) / n_window
        levels.append(math.sqrt(mean_sq))
        start += n_window
    return levels


def rss_of_orders(order_amps):
    """Root-sum-square combination of the order amplitudes:
    sqrt(sum_p A_p^2 / 2); equals the full-record RMS over integer
    revolutions for a pure multi-order signal. ValueError on empty
    dict.
    """
    if not order_amps:
        raise ValueError("order_amps must not be empty")
    return math.sqrt(sum(amp * amp for amp in order_amps.values()) / 2.0)


def vibration_verdict(level_g, limit_g):
    """Verdict for one survey point: margin = (limit - level) / limit,
    pass when margin >= 0. Returns dict {margin, pass}. ValueError on
    a non-positive limit or a negative level.
    """
    if limit_g <= 0:
        raise ValueError("limit_g must be positive, got %s" % (limit_g,))
    if level_g < 0:
        raise ValueError("level_g must be >= 0, got %s" % (level_g,))
    margin = (limit_g - level_g) / limit_g
    return {"margin": margin, "pass": margin >= 0.0}


def trim_verdict(amp_1p_g, limit_1p_g):
    """1P trim verdict: margin on the 1P component against the trim
    limit, needs_trim when the amplitude exceeds the limit (margin
    below zero). Returns dict {margin, needs_trim}. ValueError on a
    non-positive trim limit or a negative amplitude.
    """
    if limit_1p_g <= 0:
        raise ValueError("limit_1p_g must be positive, got %s" % (limit_1p_g,))
    if amp_1p_g < 0:
        raise ValueError("amp_1p_g must be >= 0, got %s" % (amp_1p_g,))
    margin = (limit_1p_g - amp_1p_g) / limit_1p_g
    return {"margin": margin, "needs_trim": margin < 0.0}


def vibration_survey_summary(samples, sample_rate_hz, rotor_hz, orders,
                             m_revs, vibration_limit_g, trim_limit_g):
    """Reduce one survey point to its order-domain summary.

    Returns dict with exactly these keys:
    - order_amplitudes_g: {order: A_p} for each requested order,
    - total_rms_g: windowed total RMS over the integer-rev window,
    - rss_of_orders_g: root-sum-square of the order amplitudes,
    - vibration_verdict: {margin, pass} against vibration_limit_g,
    - trim_verdict: {margin, needs_trim} against trim_limit_g.

    orders must be a non-empty iterable of integers >= 1 and must
    include order 1, the 1P component the trim verdict gates.
    """
    if not samples:
        raise ValueError("samples must not be empty")
    order_list = list(orders)
    if not order_list:
        raise ValueError("orders must not be empty")
    if any(order < 1 for order in order_list):
        raise ValueError("each order must be >= 1")
    if 1 not in order_list:
        raise ValueError("orders must include order 1 for the 1P trim verdict")
    _require_positive(sample_rate_hz, "sample_rate_hz")
    _require_positive(rotor_hz, "rotor_hz")
    _require_positive(m_revs, "m_revs")
    _require_positive(vibration_limit_g, "vibration_limit_g")
    _require_positive(trim_limit_g, "trim_limit_g")
    amps = {
        order: order_amplitude(samples, sample_rate_hz, rotor_hz, order,
                               m_revs)
        for order in order_list
    }
    n_window = int(round(m_revs * sample_rate_hz / rotor_hz))
    total = total_rms(samples[:n_window])
    rss = rss_of_orders(amps)
    return {
        "order_amplitudes_g": amps,
        "total_rms_g": total,
        "rss_of_orders_g": rss,
        "vibration_verdict": vibration_verdict(total, vibration_limit_g),
        "trim_verdict": trim_verdict(amps[1], trim_limit_g),
    }
