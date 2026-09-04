"""fir_filter_design_logic: windowed-sinc linear-phase FIR lowpass design.

Pure Python stdlib, fully deterministic (no RNG anywhere). Implements
the ideal lowpass impulse response, window weighting (rectangular,
Hann, Hamming, Blackman), DC-normalized coefficient design, the real
magnitude response of the symmetric tap set, the group delay, direct
convolution filtering, and a design self-check.

Design family boundary: this leaf is the finite-impulse-response
(windowed-sinc) side of the numerics filter pair. It designs
symmetric, linear-phase taps only, with no feedback path: the all-zero
transfer function of the taps is unconditionally bounded, so no check
table of any kind is needed. The feedback-form frequency-selective
design family with its analog-prototype mapping lives in the numerics
partner leaf digital-filter-design and is intentionally absent here.

Run the contract test:

    python3 scripts/test_fir_filter_design.py
"""

import math

PI = math.pi
WINDOWS = ("rectangular", "hann", "hamming", "blackman")


def _require_num_taps(num_taps):
    """Reject num_taps that are not positive integers (ValueError)."""
    if not isinstance(num_taps, int) or num_taps < 1:
        raise ValueError("num_taps must be a positive integer, got %r" % (num_taps,))


def _require_window(window):
    """Reject a window name that is not in WINDOWS (ValueError)."""
    if window not in WINDOWS:
        raise ValueError(
            "unknown window %r, choose from %s" % (window, ", ".join(WINDOWS))
        )


def _require_response_inputs(coefficients, frequency_hz, sample_rate_hz):
    """Shared physical-input checks for the frequency-domain probes."""
    if not coefficients:
        raise ValueError("coefficients must not be empty")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if frequency_hz < 0:
        raise ValueError("frequency_hz must be non-negative")
    if frequency_hz > sample_rate_hz / 2.0:
        raise ValueError("frequency_hz must not exceed the Nyquist frequency fs/2")


def window_coefficients(window, num_taps):
    """Window weights w[n] for n = 0..num_taps-1.

    rectangular: w[n] = 1.0; hann: w[n] = 0.5 - 0.5*cos(2*pi*n/(N-1));
    hamming: w[n] = 0.54 - 0.46*cos(2*pi*n/(N-1)); blackman:
    w[n] = 0.42 - 0.5*cos(2*pi*n/(N-1)) + 0.08*cos(4*pi*n/(N-1)).
    """
    _require_window(window)
    _require_num_taps(num_taps)
    if num_taps == 1:
        # Degenerate single-tap window: every symmetric window equals
        # 1.0 at its center tap, the limit of the defining formulas.
        return [1.0]
    if window == "rectangular":
        return [1.0] * num_taps
    denom = num_taps - 1
    if window == "hann":
        return [0.5 - 0.5 * math.cos(2.0 * PI * n / denom) for n in range(num_taps)]
    if window == "hamming":
        return [0.54 - 0.46 * math.cos(2.0 * PI * n / denom) for n in range(num_taps)]
    # blackman
    return [
        0.42 - 0.5 * math.cos(2.0 * PI * n / denom)
        + 0.08 * math.cos(4.0 * PI * n / denom)
        for n in range(num_taps)
    ]


def ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps):
    """Ideal lowpass impulse response h[n] truncated to num_taps taps.

    h[n] = sin(2*pi*fc/fs * (n - (N-1)/2)) / (pi * (n - (N-1)/2)) with
    the center tap (n = (N-1)/2) set to the limit value 2*fc/fs.
    """
    if cutoff_hz <= 0:
        raise ValueError("cutoff_hz must be positive")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if cutoff_hz >= sample_rate_hz / 2.0:
        raise ValueError("cutoff_hz must be below the Nyquist frequency fs/2")
    _require_num_taps(num_taps)
    mid = (num_taps - 1) / 2.0
    omega_c = 2.0 * PI * cutoff_hz / sample_rate_hz  # radians per sample
    taps = []
    for n in range(num_taps):
        if n == mid:
            taps.append(omega_c / PI)  # limit of sin(x)/x: 2*fc/fs
        else:
            taps.append(math.sin(omega_c * (n - mid)) / (PI * (n - mid)))
    return taps


def design_lowpass(cutoff_hz, sample_rate_hz, num_taps, window="hamming"):
    """Windowed-sinc lowpass design, DC-normalized.

    b[n] = h[n] * w[n] divided by the sum of the weighted taps, so the
    DC gain (the sum of b) is exactly 1.0. num_taps must be odd so the
    taps are symmetric about an integer center tap.
    """
    _require_num_taps(num_taps)
    if num_taps % 2 == 0:
        raise ValueError("num_taps must be odd for an integer-centered symmetric tap set")
    if cutoff_hz <= 0:
        raise ValueError("cutoff_hz must be positive")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if cutoff_hz >= sample_rate_hz / 2.0:
        raise ValueError("cutoff_hz must be below the Nyquist frequency fs/2")
    _require_window(window)
    ideal = ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps)
    weights = window_coefficients(window, num_taps)
    weighted = [h * w for h, w in zip(ideal, weights)]
    gain = sum(weighted)
    coefficients = [b / gain for b in weighted]
    return {
        "coefficients": coefficients,
        "num_taps": num_taps,
        "cutoff_hz": cutoff_hz,
        "sample_rate_hz": sample_rate_hz,
        "window": window,
        "group_delay_samples": (num_taps - 1) / 2.0,
        "dc_gain": sum(coefficients),
    }


def gain_at(coefficients, frequency_hz, sample_rate_hz):
    """Linear magnitude |H(f)| of the symmetric tap set.

    H(f) = sum_n b[n] * cos(2*pi*f/fs * (n - (N-1)/2)): the real
    response of the symmetric taps, the linear phase term dropped for
    the magnitude.
    """
    _require_response_inputs(coefficients, frequency_hz, sample_rate_hz)
    n_taps = len(coefficients)
    mid = (n_taps - 1) / 2.0
    omega = 2.0 * PI * frequency_hz / sample_rate_hz
    total = 0.0
    for k, b in enumerate(coefficients):
        total += b * math.cos(omega * (k - mid))
    return abs(total)


def magnitude_response_db(coefficients, frequency_hz, sample_rate_hz):
    """Magnitude response in dB: 20*log10(|H(f)|) at frequency_hz."""
    magnitude = gain_at(coefficients, frequency_hz, sample_rate_hz)
    if magnitude <= 0.0:
        return -math.inf
    return 20.0 * math.log10(magnitude)


def group_delay_samples(num_taps):
    """Group delay of a symmetric tap set: (num_taps - 1) / 2 samples."""
    _require_num_taps(num_taps)
    return (num_taps - 1) / 2.0


def filter_signal(coefficients, signal):
    """Direct-form convolution filter, output length equals input.

    y[n] = sum_k b[k] * x[n-k] with x treated as zero outside its
    range (zero-padded boundaries); the causal output starts at the
    first input sample.
    """
    if not coefficients:
        raise ValueError("coefficients must not be empty")
    if not signal:
        raise ValueError("signal must not be empty")
    n_taps = len(coefficients)
    n_samples = len(signal)
    out = []
    for n in range(n_samples):
        acc = 0.0
        for k in range(n_taps):
            idx = n - k
            if 0 <= idx < n_samples:
                acc += coefficients[k] * signal[idx]
        out.append(acc)
    return out


def design_check(coefficients, cutoff_hz, sample_rate_hz):
    """Design self-check for a windowed-sinc lowpass.

    Probes the DC gain at 0 Hz, the gain at the cutoff (about 0.5,
    the -6 dB point of the windowed-sinc design) and the gain at
    2*cutoff as the stopband probe. Returns dc_gain,
    cutoff_gain_db, stopband_gain_db, stopband_attenuation_db (the DC
    level minus the stopband level). The 2*cutoff probe must stay at
    or below the Nyquist frequency, so cutoff_hz must not exceed
    fs/4 here (recorded assumption).
    """
    if not coefficients:
        raise ValueError("coefficients must not be empty")
    if cutoff_hz <= 0:
        raise ValueError("cutoff_hz must be positive")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if 2.0 * cutoff_hz > sample_rate_hz / 2.0:
        raise ValueError(
            "cutoff_hz must not exceed fs/4 so the 2*cutoff stopband probe "
            "stays at or below the Nyquist frequency"
        )
    dc = gain_at(coefficients, 0.0, sample_rate_hz)
    cutoff_db = magnitude_response_db(coefficients, cutoff_hz, sample_rate_hz)
    stop_db = magnitude_response_db(coefficients, 2.0 * cutoff_hz, sample_rate_hz)
    dc_db = 20.0 * math.log10(dc) if dc > 0.0 else -math.inf
    attenuation = dc_db - stop_db if stop_db != -math.inf else math.inf
    return {
        "dc_gain": dc,
        "cutoff_gain_db": cutoff_db,
        "stopband_gain_db": stop_db,
        "stopband_attenuation_db": attenuation,
    }
