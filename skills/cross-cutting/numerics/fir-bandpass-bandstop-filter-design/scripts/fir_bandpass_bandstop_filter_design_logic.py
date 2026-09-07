"""Linear-phase FIR highpass, bandpass and bandstop filter design by the
windowed-sinc method (spectral inversion and cosine frequency translation
of a lowpass prototype).

Every tap is computed from closed-form sine, cosine and window algebra,
none looked up, no iteration and no search: deterministic, offline, pure
Python stdlib (math only). All taps are real floats, symmetric about the
integer center M = (num_taps - 1)/2, so the filter is linear phase with
constant group delay (num_taps - 1)/2 samples and its transfer function
is all-zero: unconditionally stable, no feedback path. The methodology is
the standard published windowed-sinc FIR design summary (Oppenheim and
Schafer, Discrete-Time Signal Processing, Section 8.4, with the highpass
prototype from spectral inversion of the lowpass response and the
bandpass/bandstop prototypes from cosine modulation or frequency
translation; identical closed forms in Proakis and Manolakis, Chapter 10,
and Hamming, Digital Filters). NACA TR-824 is referenced only, per
standards-map.yaml, as the numerics-convention anchor.

Defining relations (wc = 2*pi*fc_proto/fs, m = (num_taps - 1)/2):
- Window weights w[n], denominator num_taps - 1: rectangular all 1.0;
  hann 0.5 - 0.5*cos(2*pi*n/(num_taps - 1)); hamming
  0.54 - 0.46*cos(2*pi*n/(num_taps - 1)); blackman
  0.42 - 0.5*cos(2*pi*n/(num_taps - 1)) + 0.08*cos(4*pi*n/(num_taps - 1)).
- Ideal lowpass prototype h_lp[n] = sin(wc*(n - m))/(pi*(n - m)) for
  n != m, center limit h_lp[m] = wc/pi = 2*fc_proto/fs.
- Windowed prototype p[n] = w[n]*h_lp[n] (NOT DC-normalized).
- Highpass by spectral inversion: b_raw[n] = w[n]*delta[n - m] - p[n].
- Bandpass by cosine frequency translation:
  b_raw[n] = 2*p[n]*cos(w0*(n - m)), w0 = 2*pi*center_hz/fs.
- Bandstop by spectral inversion of the translated bandpass:
  b_raw[n] = w[n]*delta[n - m] - 2*p[n]*cos(w0*(n - m)).
- Unity passband gain normalization: b[n] = b_raw[n]/G with G the
  passband reference cosine sum (Nyquist for the highpass, center for the
  bandpass, DC for the bandstop).
- Magnitude response H(f) = sum_n b[n]*cos(2*pi*f/fs*(n - m)).

Cosine sums accumulate row by row in index order (no generator-sum float
reassociation) so the module is deterministic and bitwise reproducible.

Design inputs must satisfy 0 < fc < fs/2 for the highpass and
0 < low_cutoff_hz < high_cutoff_hz < fs/2 for the band types, with odd
num_taps >= 1; nonphysical inputs raise ValueError.
"""

import math

# The windowed-sinc band-edge geometry is the gain-0.5 midpoint of the
# prototype transition, the FIR lowpass sibling convention: the prototype
# response at its own cutoff is exactly |H| = 0.5, so the requested edges
# of these FIR filters sit on -6.020599913279624 dB (20*log10(0.5))
# within window ripple and image leakage. The -3.010299956639813 dB level
# is the Butterworth prototype convention of the IIR siblings and is
# reached strictly INSIDE the passband of these FIR filters, never at the
# requested edges.
BAND_EDGE_TARGET_DB = 20.0 * math.log10(0.5)
WINDOW_NAMES = ("rectangular", "hann", "hamming", "blackman")
FILTER_TYPES = ("highpass", "bandpass", "bandstop")


def _require_window(window):
    """Reject an unknown window name with ValueError."""
    if window not in WINDOW_NAMES:
        raise ValueError(
            "window must be one of rectangular, hann, hamming, blackman"
        )


def _require_num_taps(num_taps):
    """Reject num_taps below 1 or even (odd taps keep the center index
    M = (num_taps - 1)/2 an integer so the taps stay symmetric)."""
    if not isinstance(num_taps, int):
        if float(num_taps) != int(num_taps):
            raise ValueError("num_taps must be a whole number")
        num_taps = int(num_taps)
    if num_taps < 1:
        raise ValueError("num_taps must be >= 1")
    if num_taps % 2 == 0:
        raise ValueError("num_taps must be odd for a symmetric tap set")


def _require_design_inputs(ftype, sample_rate_hz, low_cutoff_hz,
                           high_cutoff_hz):
    """Per-type physical range checks shared by the design functions."""
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be > 0")
    if ftype == "highpass":
        if high_cutoff_hz is not None:
            raise ValueError("high_cutoff_hz must be None for highpass")
        if low_cutoff_hz <= 0:
            raise ValueError("cutoff_hz must be > 0")
        if low_cutoff_hz >= sample_rate_hz / 2.0:
            raise ValueError("cutoff_hz must be < fs/2")
    else:
        if high_cutoff_hz is None:
            raise ValueError("high_cutoff_hz is required for band types")
        if low_cutoff_hz <= 0:
            raise ValueError("low_cutoff_hz must be > 0")
        if low_cutoff_hz >= high_cutoff_hz:
            raise ValueError("low_cutoff_hz must be < high_cutoff_hz")
        if high_cutoff_hz >= sample_rate_hz / 2.0:
            raise ValueError("high_cutoff_hz must be < fs/2")


def window_coefficients(window, num_taps):
    """Return the window weight list w[n], n = 0..num_taps - 1, with the
    cosine denominator num_taps - 1 (rectangular, hann, hamming or
    blackman). Every window is symmetric about m = (num_taps - 1)/2 and
    evaluates to exactly 1.0 at the center tap (cos(pi) = -1), so
    windowed taps stay symmetric. num_taps = 1 returns [1.0].
    ValueError if num_taps < 1 or the window name is unknown."""
    _require_window(window)
    if not isinstance(num_taps, int):
        if float(num_taps) != int(num_taps):
            raise ValueError("num_taps must be a whole number")
        num_taps = int(num_taps)
    if num_taps < 1:
        raise ValueError("num_taps must be >= 1")
    if num_taps == 1:
        return [1.0]
    denom = float(num_taps - 1)
    out = []
    for n in range(num_taps):
        t = 2.0 * math.pi * float(n) / denom
        if window == "rectangular":
            out.append(1.0)
        elif window == "hann":
            out.append(0.5 - 0.5 * math.cos(t))
        elif window == "hamming":
            out.append(0.54 - 0.46 * math.cos(t))
        else:  # blackman
            out.append(0.42 - 0.5 * math.cos(t) + 0.08 * math.cos(2.0 * t))
    return out


def ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps):
    """Return the ideal lowpass impulse response
    h_lp[n] = sin(wc*(n - M))/(pi*(n - M)) with the center limit
    h_lp[M] = wc/pi = 2*fc/fs at n = M (odd num_taps only reaches the
    center index). ValueError if fs <= 0, cutoff_hz <= 0,
    cutoff_hz >= fs/2, or num_taps < 1."""
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be > 0")
    if cutoff_hz <= 0:
        raise ValueError("cutoff_hz must be > 0")
    if cutoff_hz >= sample_rate_hz / 2.0:
        raise ValueError("cutoff_hz must be < fs/2")
    if not isinstance(num_taps, int):
        if float(num_taps) != int(num_taps):
            raise ValueError("num_taps must be a whole number")
        num_taps = int(num_taps)
    if num_taps < 1:
        raise ValueError("num_taps must be >= 1")
    m = float(num_taps - 1) / 2.0
    wc = 2.0 * math.pi * float(cutoff_hz) / float(sample_rate_hz)
    out = []
    for n in range(num_taps):
        d = float(n) - m
        if d == 0.0:
            out.append(wc / math.pi)
        else:
            out.append(math.sin(wc * d) / (math.pi * d))
    return out


def _windowed_prototype(cutoff_hz, sample_rate_hz, num_taps, window):
    """Return (p, m): the windowed lowpass prototype list
    p[n] = w[n]*h_lp[n] (the raw translation material, NOT DC-normalized;
    its DC gain is only approximately 1, which limits the null depths of
    the spectral-inversion constructions) and the integer center index
    m = (num_taps - 1)/2."""
    w = window_coefficients(window, num_taps)
    lp = ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps)
    p = []
    for n in range(num_taps):
        p.append(w[n] * lp[n])
    m = float(num_taps - 1) / 2.0
    return p, m


def _cos_sum_response(taps, m, freq_hz, sample_rate_hz):
    """Return the real cosine sum sum_n taps[n]*cos(2*pi*f/fs*(n - m)),
    accumulated row by row in index order (deterministic; the linear
    phase term is dropped because the taps are symmetric about m)."""
    total = 0.0
    omega = 2.0 * math.pi * float(freq_hz) / float(sample_rate_hz)
    for n in range(len(taps)):
        total += taps[n] * math.cos(omega * (float(n) - m))
    return total


def _translate_invert(ftype, low_cutoff_hz, high_cutoff_hz,
                      sample_rate_hz, num_taps, window):
    """Return (raw_taps, m, w0_or_none): the RAW (unnormalized) tap set
    for the requested ftype built by the defining relation, the center
    index m, and the band center w0 for the band types (None for the
    highpass). Implemented constructions: highpass spectral inversion
    w[n]*delta[n - m] - p[n]; bandpass cosine frequency translation
    2*p[n]*cos(w0*(n - m)); bandstop spectral inversion of the translated
    bandpass w[n]*delta[n - m] - 2*p[n]*cos(w0*(n - m)). Because the
    constructions are per-sample additions and scalings they commute with
    the window: raw bandstop plus raw bandpass equals the windowed unit
    sample w[n]*delta[n - m] elementwise (the complement identity)."""
    if ftype not in FILTER_TYPES:
        raise ValueError(
            "ftype must be one of highpass, bandpass, bandstop"
        )
    _require_design_inputs(ftype, sample_rate_hz, low_cutoff_hz,
                           high_cutoff_hz)
    _require_num_taps(num_taps)
    _require_window(window)
    m = float(num_taps - 1) / 2.0
    w = window_coefficients(window, num_taps)
    if ftype == "highpass":
        (p, _) = _windowed_prototype(low_cutoff_hz, sample_rate_hz,
                                     num_taps, window)
        raw = []
        for n in range(num_taps):
            if float(n) == m:
                raw.append(w[n] - p[n])
            else:
                raw.append(-p[n])
        return raw, m, None
    fc_proto = (high_cutoff_hz - low_cutoff_hz) / 2.0
    center_hz = (low_cutoff_hz + high_cutoff_hz) / 2.0
    w0 = 2.0 * math.pi * float(center_hz) / float(sample_rate_hz)
    (p, _) = _windowed_prototype(fc_proto, sample_rate_hz, num_taps,
                                 window)
    raw = []
    for n in range(num_taps):
        arg = w0 * (float(n) - m)
        if ftype == "bandpass":
            raw.append(2.0 * p[n] * math.cos(arg))
        else:  # bandstop
            if float(n) == m:
                raw.append(w[n] - 2.0 * p[n] * math.cos(arg))
            else:
                raw.append(-2.0 * p[n] * math.cos(arg))
    return raw, m, w0


def _normalize(raw, m, reference_db):
    """Return (b, g): raw taps divided by the passband scale
    g = |cosine sum of the raw taps at the passband reference|, so the
    passband gain of the normalized taps is exactly 1 to float
    precision."""
    g = abs(_cos_sum_response(raw, m, reference_db[0], reference_db[1]))
    b = []
    for n in range(len(raw)):
        b.append(raw[n] / g)
    return b, g


def design_highpass(cutoff_hz, sample_rate_hz, num_taps, window):
    """Design a linear-phase FIR highpass by spectral inversion of the
    windowed-sinc lowpass prototype, normalized to unity Nyquist gain.
    Returns the dict {coefficients, num_taps, cutoff_hz, sample_rate_hz,
    window, group_delay_samples, nyquist_gain}. ValueError if fs <= 0,
    cutoff_hz <= 0, cutoff_hz >= fs/2, num_taps < 1 or even, or unknown
    window."""
    _require_design_inputs("highpass", sample_rate_hz, cutoff_hz, None)
    _require_num_taps(num_taps)
    _require_window(window)
    (raw, m, _) = _translate_invert("highpass", cutoff_hz, None,
                                    sample_rate_hz, num_taps, window)
    (b, _g) = _normalize(raw, m, (sample_rate_hz / 2.0, sample_rate_hz))
    return {
        "coefficients": b,
        "num_taps": num_taps,
        "cutoff_hz": float(cutoff_hz),
        "sample_rate_hz": float(sample_rate_hz),
        "window": window,
        "group_delay_samples": group_delay_samples(num_taps),
        "nyquist_gain": gain_at(b, sample_rate_hz / 2.0, sample_rate_hz),
    }


def design_bandpass(low_cutoff_hz, high_cutoff_hz, sample_rate_hz,
                    num_taps, window):
    """Design a linear-phase FIR bandpass by cosine frequency translation
    of the windowed-sinc lowpass prototype at the half bandwidth, with
    the prototype cutoff at (high - low)/2 and the translation center at
    w0 = 2*pi*(low + high)/2/fs, normalized to unity gain at the center
    frequency. Returns the dict {coefficients, num_taps, low_cutoff_hz,
    high_cutoff_hz, center_frequency_hz, sample_rate_hz, window,
    group_delay_samples, center_gain}. ValueError if fs <= 0,
    low_cutoff_hz <= 0, low_cutoff_hz >= high_cutoff_hz,
    high_cutoff_hz >= fs/2, num_taps < 1 or even, or unknown window."""
    _require_design_inputs("bandpass", sample_rate_hz, low_cutoff_hz,
                           high_cutoff_hz)
    _require_num_taps(num_taps)
    _require_window(window)
    (raw, m, w0) = _translate_invert("bandpass", low_cutoff_hz,
                                     high_cutoff_hz, sample_rate_hz,
                                     num_taps, window)
    center_hz = (low_cutoff_hz + high_cutoff_hz) / 2.0
    (b, _g) = _normalize(raw, m, (center_hz, sample_rate_hz))
    return {
        "coefficients": b,
        "num_taps": num_taps,
        "low_cutoff_hz": float(low_cutoff_hz),
        "high_cutoff_hz": float(high_cutoff_hz),
        "center_frequency_hz": float(center_hz),
        "sample_rate_hz": float(sample_rate_hz),
        "window": window,
        "group_delay_samples": group_delay_samples(num_taps),
        "center_gain": gain_at(b, center_hz, sample_rate_hz),
    }


def design_bandstop(low_cutoff_hz, high_cutoff_hz, sample_rate_hz,
                    num_taps, window):
    """Design a linear-phase FIR bandstop by spectral inversion of the
    cosine-translated bandpass prototype, normalized to unity DC gain.
    Returns the dict {coefficients, num_taps, low_cutoff_hz,
    high_cutoff_hz, center_frequency_hz, sample_rate_hz, window,
    group_delay_samples, dc_gain}. Same ValueError set as
    design_bandpass. The bandstop is also near-unity at Nyquist and near
    DC away from the notch because the notch complement is not perfect."""
    _require_design_inputs("bandstop", sample_rate_hz, low_cutoff_hz,
                           high_cutoff_hz)
    _require_num_taps(num_taps)
    _require_window(window)
    (raw, m, _w0) = _translate_invert("bandstop", low_cutoff_hz,
                                      high_cutoff_hz, sample_rate_hz,
                                      num_taps, window)
    center_hz = (low_cutoff_hz + high_cutoff_hz) / 2.0
    (b, _g) = _normalize(raw, m, (0.0, sample_rate_hz))
    return {
        "coefficients": b,
        "num_taps": num_taps,
        "low_cutoff_hz": float(low_cutoff_hz),
        "high_cutoff_hz": float(high_cutoff_hz),
        "center_frequency_hz": float(center_hz),
        "sample_rate_hz": float(sample_rate_hz),
        "window": window,
        "group_delay_samples": group_delay_samples(num_taps),
        "dc_gain": gain_at(b, 0.0, sample_rate_hz),
    }


def gain_at(coefficients, freq_hz, sample_rate_hz):
    """Return the linear magnitude |H(freq_hz)| of the real cosine sum of
    the symmetric tap set. Probes 0 Hz and fs/2 are valid. ValueError if
    the coefficient list is empty, fs <= 0, or the probe lies outside
    [0, fs/2]."""
    if not coefficients:
        raise ValueError("coefficients must be non-empty")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be > 0")
    if freq_hz < 0.0 or freq_hz > sample_rate_hz / 2.0:
        raise ValueError("freq_hz must lie in [0, fs/2]")
    m = float(len(coefficients) - 1) / 2.0
    return abs(_cos_sum_response(coefficients, m, freq_hz,
                                 sample_rate_hz))


def magnitude_response_db(coefficients, freq_hz, sample_rate_hz):
    """Return 20*log10(gain_at(...)) in dB. Same ValueError set as
    gain_at."""
    return 20.0 * math.log10(gain_at(coefficients, freq_hz,
                                     sample_rate_hz))


def group_delay_samples(num_taps):
    """Return the constant group delay (num_taps - 1)/2 samples of the
    symmetric tap set. ValueError if num_taps < 1."""
    if not isinstance(num_taps, int):
        if float(num_taps) != int(num_taps):
            raise ValueError("num_taps must be a whole number")
        num_taps = int(num_taps)
    if num_taps < 1:
        raise ValueError("num_taps must be >= 1")
    return float(num_taps - 1) / 2.0


def filter_signal(coefficients, samples):
    """Filter a sampled signal by direct-form convolution,
    y[n] = sum_k b[k]*x[n - k], the input treated as zero outside its
    range and the output the same length as the input (the first
    (num_taps - 1) output samples carry the filter transient). ValueError
    if the coefficient list or the sample list is empty, or any entry is
    non-finite."""
    if not coefficients:
        raise ValueError("coefficients must be non-empty")
    if not samples:
        raise ValueError("samples must be non-empty")
    for c in coefficients:
        if not math.isfinite(c):
            raise ValueError("coefficients must be finite")
    for s in samples:
        if not math.isfinite(s):
            raise ValueError("samples must be finite")
    nb = len(coefficients)
    ns = len(samples)
    out = []
    for n in range(ns):
        acc = 0.0
        for k in range(nb):
            j = n - k
            if j >= 0:
                acc += coefficients[k] * samples[j]
        out.append(acc)
    return out


def band_edge_checks(coefficients, ftype, sample_rate_hz, low_cutoff_hz,
                     high_cutoff_hz=None):
    """Verify the requested band edges against the FIR midpoint target
    BAND_EDGE_TARGET_DB = -6.020599913279624 dB (20*log10(0.5)): the
    prototype response at its own cutoff is the gain-0.5 midpoint of the
    transition, so the measured edge gains sit on the -6 dB band-edge
    geometry within window ripple and image leakage. Returns the dict
    {low_edge_db, high_edge_db, target_db, low_edge_ok, high_edge_ok,
    passband_ok, extra, verdict}; extra carries the measured passband
    reference gain(s) in dB (a float for highpass/bandpass, a
    (dc_db, nyquist_db) pair for bandstop), and verdict is 'PASS' only
    when low_edge_ok, high_edge_ok and passband_ok all hold. ValueError
    for unknown ftype, fs <= 0, invalid edges, or high_cutoff_hz not None
    with ftype 'highpass'."""
    if ftype not in FILTER_TYPES:
        raise ValueError(
            "ftype must be one of highpass, bandpass, bandstop"
        )
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be > 0")
    if ftype == "highpass":
        if high_cutoff_hz is not None:
            raise ValueError("high_cutoff_hz must be None for highpass")
        if low_cutoff_hz <= 0 or low_cutoff_hz >= sample_rate_hz / 2.0:
            raise ValueError("cutoff_hz must lie in (0, fs/2)")
    else:
        if high_cutoff_hz is None:
            raise ValueError("high_cutoff_hz is required for band types")
        if low_cutoff_hz <= 0:
            raise ValueError("low_cutoff_hz must be > 0")
        if low_cutoff_hz >= high_cutoff_hz:
            raise ValueError("low_cutoff_hz must be < high_cutoff_hz")
        if high_cutoff_hz >= sample_rate_hz / 2.0:
            raise ValueError("high_cutoff_hz must be < fs/2")
    target_db = BAND_EDGE_TARGET_DB
    low_edge_db = magnitude_response_db(coefficients, low_cutoff_hz,
                                        sample_rate_hz)
    low_edge_ok = abs(low_edge_db - target_db) < 0.1
    if ftype == "highpass":
        high_edge_db = None
        high_edge_ok = True
        ref_db = magnitude_response_db(coefficients, sample_rate_hz / 2.0,
                                       sample_rate_hz)
        passband_ok = abs(ref_db) < 0.1
        extra = ref_db
    else:
        high_edge_db = magnitude_response_db(coefficients,
                                             high_cutoff_hz,
                                             sample_rate_hz)
        high_edge_ok = abs(high_edge_db - target_db) < 0.1
        if ftype == "bandpass":
            center_hz = (low_cutoff_hz + high_cutoff_hz) / 2.0
            ref_db = magnitude_response_db(coefficients, center_hz,
                                           sample_rate_hz)
            passband_ok = abs(ref_db) < 0.1
            extra = ref_db
        else:  # bandstop
            dc_db = magnitude_response_db(coefficients, 0.0,
                                          sample_rate_hz)
            nyq_db = magnitude_response_db(coefficients,
                                           sample_rate_hz / 2.0,
                                           sample_rate_hz)
            passband_ok = abs(dc_db) < 0.1 and abs(nyq_db) < 0.1
            extra = (dc_db, nyq_db)
    verdict = "PASS" if (low_edge_ok and high_edge_ok and passband_ok) \
        else "FAIL"
    return {
        "low_edge_db": low_edge_db,
        "high_edge_db": high_edge_db,
        "target_db": target_db,
        "low_edge_ok": low_edge_ok,
        "high_edge_ok": high_edge_ok,
        "passband_ok": passband_ok,
        "extra": extra,
        "verdict": verdict,
    }
