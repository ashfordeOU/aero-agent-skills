"""Power spectral density estimation logic (Welch averaged periodogram).

Estimates the one-sided power spectral density (units^2/Hz) of a
stochastic sampled signal by Welch's method: the record is split into
overlapping Hann-windowed segments, each segment periodogram is
density-scaled, and the segment periodograms are averaged. The windowed
segments are transformed with the leaf's own iterative radix-2
Cooley-Tukey fast Fourier transform (pure stdlib: math only;
random is never used here). NACA Report 824 is the pack's public-domain
numerics anchor (standards-map.yaml); the methodology is generic
signal-processing summary.

Conventions: sampling frequency fs (Hz), segment length M samples (a
power of two for the radix-2 transform), overlap fraction in [0, 1)
(default 0.5). One-sided density scaling per bin of a real segment:

  P[k]  = 2 |X[k]|^2 / (fs * sum(w^2))   interior bins k = 1..M/2 - 1
  P[0]  =     |X[0]|^2 / (fs * sum(w^2)) (DC bin is not doubled)
  P[M/2]=     |X[M/2]|^2 / (fs * sum(w^2)) (Nyquist bin is not doubled)

with X the radix-2 transform of the windowed segment and w the Hann
window w[n] = 0.5 - 0.5 cos(2 pi n / M). The frequency axis is
freqs[k] = k * fs / M for k = 0..M/2, so df = fs / M.

Equivalent noise bandwidth ENBW = fs * sum(w^2) / (sum(w))^2; total
power = sum_k P[k] * df equals the signal variance for a zero-mean
signal (an energy-conservation identity, implemented as
psd_total_power).

Worked anchors for fs = 1024 Hz, M = 256, Hann window, 50% overlap on
an 8192-sample record (63 segments exactly, (8192 - 256) / 128 + 1):
  hann_window sum 128.0 (M/2), sum of squares 96.0 (3M/8)
  ENBW = 1024 * 96 / 128^2 = 6.0 Hz
  60 Hz sine (bin 15), amplitude A = 1: peak density 0.083333333 =
    A^2 / (2 ENBW), integrated power 0.500000000 = A^2 / 2
  amplitude A = 0.5: peak density 0.020833333 (one quarter)

Every public function validates its input and raises ValueError with a
clear message on non-physical input: a segment length that is not a
power of two, fs <= 0, overlap outside [0, 1), an x record shorter
than the segment length, an empty or zero-sum window, and df <= 0.
All functions are deterministic and offline.
"""

import math


def _is_power_of_two(n):
    """True when n is a positive power of two."""
    return n > 0 and (n & (n - 1)) == 0


def _as_float_list(seq, what="sequence"):
    """Coerce a sequence of numbers to a list of floats (not empty)."""
    try:
        items = list(seq)
    except TypeError:
        raise TypeError("%s must be a sequence of numbers" % what) from None
    if len(items) == 0:
        raise ValueError("%s must not be empty" % what)
    out = []
    for v in items:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TypeError(
                "%s entries must be real numbers, got %r" % (what, v)
            )
        out.append(float(v))
    return out


def _check_fs(fs):
    """Return fs as a float after rejecting non-positive values."""
    if isinstance(fs, bool) or not isinstance(fs, (int, float)):
        raise TypeError("fs must be a number, got %r" % (fs,))
    fs = float(fs)
    if fs <= 0.0:
        raise ValueError("fs must be positive, got %r" % (fs,))
    return fs


def hann_window(m):
    """Hann window weights w[n] = 0.5 - 0.5 cos(2 pi n / m).

    Returns a list of m weights. For even m the weights sum to m/2
    (128.0 for m = 256) and the sum of squares to 3m/8 (96.0 for
    m = 256) up to cosine rounding. Raises ValueError when m < 1 and
    TypeError when m is not an integer.
    """
    if isinstance(m, bool) or not isinstance(m, int):
        raise TypeError("m must be an integer, got %r" % (m,))
    if m < 1:
        raise ValueError("m must be >= 1, got %d" % m)
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * n / m) for n in range(m)]


def _fft(x):
    """Radix-2 Cooley-Tukey transform of a sequence (internal helper).

    X[k] = sum_n x[n] * exp(-2 pi i k n / N) with no scaling, computed
    by an iterative bit-reversal radix-2 decomposition. The length N
    must be a power of two (ValueError otherwise); entries may be real
    or complex. Deterministic and identical in value to the transform
    definition for power-of-two lengths.
    """
    try:
        items = list(x)
    except TypeError:
        raise TypeError("input must be a sequence of numbers") from None
    if len(items) == 0:
        raise ValueError("input must not be empty")
    n = len(items)
    if not _is_power_of_two(n):
        raise ValueError("radix-2 transform needs a power-of-two length, got N=%d" % n)
    arr = []
    for v in items:
        if isinstance(v, bool) or not isinstance(v, (int, float, complex)):
            raise TypeError("entries must be numbers, got %r" % (v,))
        arr.append(complex(v))
    # Bit-reversal permutation.
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            arr[i], arr[j] = arr[j], arr[i]
    # Butterflies with twiddle factors exp(-2 pi i k / length).
    length = 2
    while length <= n:
        angle = -2.0 * math.pi / length
        wlen = complex(math.cos(angle), math.sin(angle))
        half = length // 2
        for base in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(half):
                u = arr[base + k]
                v = arr[base + k + half] * w
                arr[base + k] = u + v
                arr[base + k + half] = u - v
                w = w * wlen
        length <<= 1
    return arr


def periodogram(x_segment, fs, window):
    """One-sided power spectral density of a single segment.

    Returns (freqs, P) with freqs[k] = k * fs / M for k = 0..M/2 and
    P[k] the density-scaled value: interior bins carry the factor 2
    (both spectral sides fold into the one-sided axis) while the DC
    bin (k = 0) and the Nyquist bin (k = M/2) are not doubled. The
    segment length M must equal len(window) and be a power of two
    (radix-2 transform); fs must be positive. Raises ValueError on
    any violation and TypeError on non-numeric entries.
    """
    x = _as_float_list(x_segment, "x_segment")
    m = len(x)
    if not _is_power_of_two(m):
        raise ValueError(
            "segment length must be a power of two, got %d" % m
        )
    fs = _check_fs(fs)
    w = _as_float_list(window, "window")
    if len(w) != m:
        raise ValueError(
            "window length %d must equal the segment length %d" % (len(w), m)
        )
    win_sq = sum(ww * ww for ww in w)
    if win_sq <= 0.0:
        raise ValueError("window must not be identically zero")
    windowed = [x[n] * w[n] for n in range(m)]
    xf = _fft(windowed)
    half = m // 2
    denom = fs * win_sq
    psd = []
    for k in range(half + 1):
        mag_sq = xf[k].real * xf[k].real + xf[k].imag * xf[k].imag
        if k == 0 or k == half:
            psd.append(mag_sq / denom)
        else:
            psd.append(2.0 * mag_sq / denom)
    freqs = [k * fs / m for k in range(half + 1)]
    return freqs, psd


def welch_psd(x, fs, seg_len, overlap=0.5):
    """Welch averaged periodogram PSD estimate of a stochastic record.

    Splits x into segments of seg_len samples whose starts slide by
    hop = seg_len * (1 - overlap) samples (default 50% overlap), forms
    the Hann window of length seg_len, and returns the mean of the
    segment periodograms as (freqs, PSD). Raises ValueError when
    seg_len is not a power of two (and at least 2), fs <= 0, overlap
    lies outside [0, 1), or x is shorter than seg_len.
    """
    data = _as_float_list(x, "x")
    if isinstance(seg_len, bool) or not isinstance(seg_len, int):
        raise TypeError("seg_len must be an integer, got %r" % (seg_len,))
    if seg_len < 2 or not _is_power_of_two(seg_len):
        raise ValueError(
            "seg_len must be a power of two >= 2, got %d" % seg_len
        )
    fs = _check_fs(fs)
    if isinstance(overlap, bool) or not isinstance(overlap, (int, float)):
        raise TypeError("overlap must be a number, got %r" % (overlap,))
    overlap = float(overlap)
    if overlap < 0.0 or overlap >= 1.0:
        raise ValueError(
            "overlap must lie in [0, 1), got %r" % (overlap,)
        )
    if len(data) < seg_len:
        raise ValueError(
            "x has %d samples, shorter than seg_len=%d" % (len(data), seg_len)
        )
    window = hann_window(seg_len)
    hop = int(seg_len * (1.0 - overlap))
    if hop < 1:
        hop = 1
    n_seg = 1 + (len(data) - seg_len) // hop
    first_f, first_p = periodogram(data[0:seg_len], fs, window)
    freqs = first_f
    acc = [0.0] * len(first_p)
    for i in range(n_seg):
        start = i * hop
        seg = data[start:start + seg_len]
        _, p = periodogram(seg, fs, window)
        for k, pk in enumerate(p):
            acc[k] += pk
    psd = [v / n_seg for v in acc]
    return freqs, psd


def equivalent_noise_bw(window, fs):
    """Equivalent noise bandwidth ENBW = fs * sum(w^2) / (sum(w))^2.

    The bandwidth in Hz of an ideal rectangular filter that passes the
    same white-noise power as the window. For the Hann window of
    length 256 at fs = 1024 Hz: ENBW = 1024 * 96 / 128^2 = 6.0 Hz.
    Raises ValueError when fs <= 0 or the window weights have no
    positive sum.
    """
    w = _as_float_list(window, "window")
    fs = _check_fs(fs)
    s = sum(w)
    s2 = sum(v * v for v in w)
    if s <= 0.0:
        raise ValueError("window weights must have a positive sum")
    return fs * s2 / (s * s)


def psd_total_power(psd, df):
    """Total power of a one-sided density array: sum_k P[k] * df.

    With the density scaling used here this equals the variance of a
    zero-mean signal, the integrated-power identity behind noise and
    random-vibration level checks. Raises ValueError when df <= 0.
    """
    p = _as_float_list(psd, "psd")
    if isinstance(df, bool) or not isinstance(df, (int, float)):
        raise TypeError("df must be a number, got %r" % (df,))
    df = float(df)
    if df <= 0.0:
        raise ValueError("df must be positive, got %r" % (df,))
    return sum(p) * df


def psd_summary(x, fs, seg_len, overlap=0.5):
    """Convenience summary of a Welch PSD estimate.

    Returns a dict with exactly the keys: freqs, psd, enbw_hz,
    df_hz, total_power, peak_density, peak_freq_hz. Validates the
    same inputs as welch_psd and raises the same ValueErrors.
    """
    freqs, psd = welch_psd(x, fs, seg_len, overlap=overlap)
    df = fs / seg_len
    enbw = equivalent_noise_bw(hann_window(seg_len), fs)
    total_power = psd_total_power(psd, df)
    peak_idx = 0
    for k in range(1, len(psd)):
        if psd[k] > psd[peak_idx]:
            peak_idx = k
    return {
        "freqs": freqs,
        "psd": psd,
        "enbw_hz": enbw,
        "df_hz": df,
        "total_power": total_power,
        "peak_density": psd[peak_idx],
        "peak_freq_hz": freqs[peak_idx],
    }
