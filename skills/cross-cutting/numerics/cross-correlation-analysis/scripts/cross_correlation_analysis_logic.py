"""Cross-correlation and autocorrelation analysis of sampled signal sequences.

Convention: rxy[k] = sum over n of x[n] * y[n - k], computed for every
integer lag k in [-(Ny - 1), Nx - 1] where Nx = len(x) and Ny = len(y);
terms whose index falls outside a sequence contribute zero (zero
padding).  A positive peak lag means x leads y, so when y is x delayed
by d samples the peak appears at lag -d.  Positive delay_samples in the
delay_estimate result means y is delayed relative to x.

Modes for cross_correlation and autocorrelation:
  raw      return the plain sums
  biased   divide every value by Nx = len(x)
  unbiased divide every value by the number of overlapping samples at
           that lag

normalized_cross_correlation divides every raw value by
sqrt(rxx0 * ryy0) with rxx0 = sum x[n]**2 and ryy0 = sum y[n]**2, so
each coefficient lies in [-1, 1] and a perfect match reaches 1.0.
delay_estimate returns the peak lag, the raw and normalized peak
values, and delay_samples = -peak_lag.  All helpers are pure Python
stdlib, deterministic, offline.

Raises ValueError on empty inputs, non-numeric or non-finite entries,
unknown modes, mismatched lags/values lengths, and zero-energy
normalization.
"""

import math

_MODES = ("raw", "biased", "unbiased")


def _as_floats(seq, name):
    """Return seq as a list of floats, raising ValueError when invalid."""
    if seq is None or len(seq) == 0:
        raise ValueError("%s must be a non-empty sequence" % name)
    out = []
    for entry in seq:
        try:
            value = float(entry)
        except (TypeError, ValueError):
            raise ValueError(
                "%s entries must be numeric, got %r" % (name, entry)
            ) from None
        if not math.isfinite(value):
            raise ValueError(
                "%s entries must be finite, got %r" % (name, entry)
            )
        out.append(value)
    return out


def _lag_range(nx, ny):
    """Return the lag list [-(Ny-1), Nx-1] inclusive as Python range args."""
    return range(-(ny - 1), nx)


def _overlap_count(nx, ny, k):
    """Number of n in [0, Nx-1] with n - k inside [0, Ny-1]."""
    low = max(0, k)
    high = min(nx - 1, ny - 1 + k)
    if high < low:
        return 0
    return high - low + 1


def cross_correlation(x, y, mode="raw"):
    """Cross-correlation rxy[k] = sum x[n]*y[n-k] for k in [-(Ny-1), Nx-1].

    Returns (lags, values): lags is an ascending list of ints and values
    holds one float per lag.  mode selects raw, biased (divide by Nx) or
    unbiased (divide by the per-lag overlap count).
    """
    xs = _as_floats(x, "x")
    ys = _as_floats(y, "y")
    if mode not in _MODES:
        raise ValueError("unknown mode %r; expected one of %s" % (mode, _MODES))
    nx = len(xs)
    ny = len(ys)
    lags = list(_lag_range(nx, ny))
    values = []
    for k in lags:
        total = 0.0
        for n in range(nx):
            m = n - k
            if 0 <= m < ny:
                total += xs[n] * ys[m]
        if mode == "biased":
            total = total / nx
        elif mode == "unbiased":
            total = total / _overlap_count(nx, ny, k)
        values.append(total)
    return lags, values


def _energies(xs, ys):
    """Zero-lag energies rxx0 = sum x[n]**2 and ryy0 = sum y[n]**2."""
    rxx0 = sum(v * v for v in xs)
    ryy0 = sum(v * v for v in ys)
    return rxx0, ryy0


def normalized_cross_correlation(x, y):
    """Normalized cross-correlation, coefficient per lag in [-1, 1].

    Each raw value is divided by sqrt(rxx0 * ryy0); raises ValueError
    when either zero-lag energy is zero.
    """
    xs = _as_floats(x, "x")
    ys = _as_floats(y, "y")
    rxx0, ryy0 = _energies(xs, ys)
    if rxx0 == 0.0 or ryy0 == 0.0:
        raise ValueError(
            "normalization needs nonzero energy, got rxx0=%g ryy0=%g"
            % (rxx0, ryy0)
        )
    denom = math.sqrt(rxx0 * ryy0)
    lags, raw = cross_correlation(xs, ys, "raw")
    return lags, [value / denom for value in raw]


def autocorrelation(x, mode="raw"):
    """Autocorrelation rxx[k] = sum x[n]*x[n-k] for k in [-(Nx-1), Nx-1].

    Returns (lags, values) with the same mode semantics as
    cross_correlation.  The sequence is even: value at lag k equals the
    value at lag -k.
    """
    return cross_correlation(x, x, mode)


def peak_lag(lags, values):
    """Lag of the maximum absolute value; ties favor the smaller |lag|.

    Returns an int.  Raises ValueError on empty or length-mismatched
    lists.
    """
    if lags is None or values is None or len(lags) == 0 or len(values) == 0:
        raise ValueError("lags and values must be non-empty lists")
    if len(lags) != len(values):
        raise ValueError(
            "lags and values must have equal length, got %d and %d"
            % (len(lags), len(values))
        )
    best = 0
    for i in range(1, len(lags)):
        av = abs(values[i])
        bv = abs(values[best])
        if av > bv or (av == bv and abs(lags[i]) < abs(lags[best])):
            best = i
    return int(lags[best])


def delay_estimate(x, y):
    """Time-delay estimate between x and y from the peak of the correlation.

    Returns dict(peak_lag, peak_value, normalized_peak, delay_samples)
    with delay_samples = -peak_lag; a positive delay_samples means y is
    delayed relative to x.
    """
    xs = _as_floats(x, "x")
    ys = _as_floats(y, "y")
    lags, raw = cross_correlation(xs, ys, "raw")
    k = peak_lag(lags, raw)
    idx = lags.index(k)
    _, coeffs = normalized_cross_correlation(xs, ys)
    return {
        "peak_lag": k,
        "peak_value": raw[idx],
        "normalized_peak": coeffs[idx],
        "delay_samples": -k,
    }


def zero_lag_coefficient(x, y):
    """Normalized correlation coefficient at lag 0: rxy[0]/sqrt(rxx0*ryy0).

    Raises ValueError when either zero-lag energy is zero.
    """
    xs = _as_floats(x, "x")
    ys = _as_floats(y, "y")
    rxx0, ryy0 = _energies(xs, ys)
    if rxx0 == 0.0 or ryy0 == 0.0:
        raise ValueError(
            "normalization needs nonzero energy, got rxx0=%g ryy0=%g"
            % (rxx0, ryy0)
        )
    denom = math.sqrt(rxx0 * ryy0)
    rxy0 = 0.0
    for n in range(len(xs)):
        if n < len(ys):
            rxy0 += xs[n] * ys[n]
    return rxy0 / denom
