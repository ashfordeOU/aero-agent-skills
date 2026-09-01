"""Fast Fourier transform logic (discrete Fourier transform and radix-2 FFT).

Paraphrase of the classical numerical method: the DFT definition and
the Cooley-Tukey radix-2 decomposition are generic mathematics (the
textbook anchors are Abramowitz and Stegun and standard signal
processing texts), not RTCA or SAE content. NACA Report 824 is the
pack's public-domain anchor (standards-map.yaml).

Conventions: forward transforms use exp(-2*pi*i*k*n/N) with no
scaling; the inverse uses exp(+2*pi*i*k*n/N) scaled by 1/N. dft is the
O(N^2) definition and works for any length N; fft is the radix-2
Cooley-Tukey decomposition and requires N to be a power of two;
ifft is the inverse radix-2 transform, also power-of-two only.

Worked anchors (exact for small N):
  dft([1, 2, 3, 4]) = [10, -2+2j, -2, -2-2j]
  fft([1, 0, 0, 0]) = [1, 1, 1, 1]          (impulse gives all ones)
  ifft([1, 1, 1, 1]) = [1, 0, 0, 0]
  ifft(dft([1, 2, 3, 4])) = [1, 2, 3, 4]    (round trip)
  magnitude_spectrum of sin(pi*n/2), N=8: peak 4.0 at bins 2 and 6,
    phase -pi/2 at bin 2 and +pi/2 at bin 6 (a sine at bin k peaks
    at bin k, and its mirror N-k, with magnitude N/2)
  parseval_ratio([1, 2, 3, 4]) = 1.0 (sum |x|^2 = (1/N) sum |X|^2)

All functions are deterministic and stdlib-only (math, cmath). Every
public function validates its input and raises ValueError with a clear
message: empty input, non-numeric entries, and (for the radix-2 paths)
a length that is not a power of two.
"""

import cmath
import math


def _as_complex_list(seq):
    """Coerce a sequence of numbers to a list of complex values."""
    try:
        items = list(seq)
    except TypeError:
        raise TypeError("input must be a sequence of numbers") from None
    if len(items) == 0:
        raise ValueError("input sequence must not be empty")
    out = []
    for v in items:
        if not isinstance(v, (int, float, complex)):
            raise TypeError("input entries must be real or complex numbers, got %r" % (v,))
        out.append(complex(v))
    return out


def _is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def dft(x):
    """Discrete Fourier transform by definition, O(N^2), any length N.

    X[k] = sum_{n=0}^{N-1} x[n] * exp(-2*pi*i*k*n/N).

    Worked anchor: dft([1, 2, 3, 4]) = [10, -2+2j, -2, -2-2j].
    Raises ValueError on an empty input and TypeError on non-numeric
    entries.
    """
    x = _as_complex_list(x)
    n = len(x)
    out = []
    for k in range(n):
        s = 0j
        for i, xi in enumerate(x):
            s += xi * cmath.exp(-2j * math.pi * k * i / n)
        out.append(s)
    return out


def fft(x):
    """Radix-2 Cooley-Tukey fast Fourier transform (N must be a power of two).

    Splits the sequence into even and odd indexed samples, transforms
    each half recursively, and combines with the twiddle factors
    exp(-2*pi*i*k/N). Identical to dft for power-of-two lengths.

    Worked anchors: fft([1, 0, 0, 0]) = [1, 1, 1, 1] (all ones);
    fft([1, 2, 3, 4]) = [10, -2+2j, -2, -2-2j].
    Raises ValueError when N is empty or not a power of two.
    """
    x = _as_complex_list(x)
    n = len(x)
    if not _is_power_of_two(n):
        raise ValueError(
            "fft requires a power-of-two length, got N=%d" % n
        )
    if n == 1:
        return x
    even = fft(x[0::2])
    odd = fft(x[1::2])
    half = n // 2
    out = [0j] * n
    for k in range(half):
        t = odd[k] * cmath.exp(-2j * math.pi * k / n)
        out[k] = even[k] + t
        out[k + half] = even[k] - t
    return out


def ifft(X):
    """Inverse radix-2 FFT (N must be a power of two).

    x[n] = (1/N) sum_{k=0}^{N-1} X[k] * exp(+2*pi*i*k*n/N), computed
    as conjugate(fft(conjugate(X))) / N.

    Worked anchors: ifft([1, 1, 1, 1]) = [1, 0, 0, 0];
    ifft([10, -2+2j, -2, -2-2j]) = [1, 2, 3, 4].
    Raises ValueError when N is empty or not a power of two.
    """
    X = _as_complex_list(X)
    n = len(X)
    if not _is_power_of_two(n):
        raise ValueError(
            "ifft requires a power-of-two length, got N=%d" % n
        )
    conj = [z.conjugate() for z in X]
    y = fft(conj)
    return [z.conjugate() / n for z in y]


def _transform(x):
    """Spectrum path: fft for power-of-two lengths, else dft.

    This is the deterministic dispatcher behind magnitude_spectrum,
    phase_spectrum, and power_spectrum: any length N is accepted, and
    the radix-2 fast path is used whenever it applies.
    """
    x = _as_complex_list(x)
    if len(x) > 1 and _is_power_of_two(len(x)):
        return fft(x)
    return dft(x)


def magnitude_spectrum(x):
    """Magnitude |X[k]| of the spectrum, one entry per bin.

    A pure sine at bin k0 with N samples peaks at bins k0 and N-k0
    with magnitude N/2: for x[n] = sin(pi*n/2) with N=8 the peak is
    4.0 at bins 2 and 6, and near zero elsewhere. Raises ValueError
    on an empty input.
    """
    return [abs(z) for z in _transform(x)]


def phase_spectrum(x):
    """Phase arg(X[k]) in radians on (-pi, pi], one entry per bin.

    A sine at bin k0 gives phase -pi/2 at bin k0 and +pi/2 at bin
    N-k0; a cosine at bin k0 gives phase 0 at bin k0. Raises
    ValueError on an empty input.
    """
    return [cmath.phase(z) for z in _transform(x)]


def power_spectrum(x):
    """Power |X[k]|^2 of the spectrum, one entry per bin.

    Summed over all bins and divided by N this equals the time-domain
    energy (Parseval). Raises ValueError on an empty input.
    """
    return [abs(z) * abs(z) for z in _transform(x)]


def parseval_ratio(x):
    """Ratio of time-domain energy to frequency-domain energy.

    Returns sum |x[n]|^2 / ((1/N) sum |X[k]|^2), which is exactly 1.0
    for any input under the DFT/FFT convention used here. The ratio is
    the energy check for a spectrum: a value far from 1 indicates a
    bug, never a property of a correct transform.

    Worked anchor: parseval_ratio([1, 2, 3, 4]) = 1.0 (30 / 30).
    Raises ValueError on an empty input.
    """
    x = _as_complex_list(x)
    n = len(x)
    time_energy = sum(abs(v) * abs(v) for v in x)
    freq_energy = sum(power_spectrum(x)) / n
    if freq_energy == 0.0:
        return 1.0  # all-zero signal: both energies are zero
    return time_energy / freq_energy
