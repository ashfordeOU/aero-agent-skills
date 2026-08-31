#!/usr/bin/env python3
"""Flight test data reduction logic (post-flight processing).

Common measurement and data reduction methodology (standards-map.yaml,
far-25/cs-25 reference-only context): recorded flight test channels are
corrected with the calibration slope and intercept of each sensor,
traces from separate recorders are aligned to a common time base, noisy
traces are smoothed with a moving average filter, the corrected
airspeed follows from the impact pressure and the air density, the
independent measurement uncertainty sources combine by root sum square
into the combined uncertainty, and the data quality verdict flags NaN
samples, out-of-range values, and time gaps before the reduced data
feeds the analysis. Units stay SI (m/s, Pa, kg/m^3, s).
"""

import math


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _as_number(x, name):
    if not _is_number(x):
        raise ValueError("%s must be numeric, got %r" % (name, x))
    return float(x)


def _as_number_list(values, name):
    if not isinstance(values, list) or not values:
        raise ValueError("%s must be a non-empty list" % name)
    out = []
    for i, v in enumerate(values):
        if not _is_number(v):
            raise ValueError("%s[%d] must be numeric, got %r" % (name, i, v))
        out.append(float(v))
    return out


def apply_calibration(raw, slope, intercept):
    """Correct a raw channel reading with the calibration line.

    The calibrated value is V_corr = slope * V_raw + intercept, with
    slope the gain and intercept the offset of the channel
    calibration. Units follow the channel (m/s for airspeed channels,
    deg for angles).

    Returns the corrected value as a float.

    Raises ValueError on a non-numeric (or bool) raw, slope, or
    intercept.
    """
    raw_f = _as_number(raw, "raw")
    slope_f = _as_number(slope, "slope")
    intercept_f = _as_number(intercept, "intercept")
    return slope_f * raw_f + intercept_f


def align_time_series(times, offset):
    """Shift a time series by a constant offset.

    The aligned time is t_aligned = t + offset, with offset in s. A
    positive offset shifts the trace later in time; alignment removes
    the start-time skew between recorders.

    Returns the aligned times as a list of floats.

    Raises ValueError on an empty times list, a non-numeric (or bool)
    offset, or a non-numeric (or bool) element in times.
    """
    offset_f = _as_number(offset, "offset")
    t = _as_number_list(times, "times")
    return [ti + offset_f for ti in t]


def moving_average(values, window):
    """Smooth a trace with a moving average over a window of samples.

    The smoothed sample y_k is the mean of the N samples in the window
    starting at k, for k from 0 to n - N, so an n-sample trace gives
    n - N + 1 smoothed samples. Odd windows are centered on the
    samples; even windows lag by half a sample. Units follow the trace.

    Returns the smoothed trace as a list of floats.

    Raises ValueError on an empty values list, a non-numeric (or bool)
    element in values, a non-int (or bool) window, window < 1, or a
    window larger than the trace.
    """
    vals = _as_number_list(values, "values")
    if isinstance(window, bool) or not isinstance(window, int):
        raise ValueError("window must be an int, got %r" % (window,))
    if window < 1:
        raise ValueError("window must be >= 1, got %r" % (window,))
    if window > len(vals):
        raise ValueError(
            "window %d larger than trace of %d samples" % (window, len(vals))
        )
    out = []
    for k in range(len(vals) - window + 1):
        out.append(sum(vals[k : k + window]) / window)
    return out


def corrected_airspeed(impact_pressure, density):
    """Corrected airspeed from the impact pressure and air density.

    The corrected airspeed is V_c = sqrt(2 * q_c / rho), with q_c the
    impact pressure in Pa and rho the air density in kg/m^3. The
    result is in m/s.

    Returns the corrected airspeed as a float.

    Raises ValueError on a non-numeric (or bool) impact_pressure with
    impact_pressure < 0, or a non-numeric (or bool) density with
    density <= 0.
    """
    q = _as_number(impact_pressure, "impact_pressure")
    rho = _as_number(density, "density")
    if q < 0:
        raise ValueError("impact_pressure must be >= 0, got %r" % (q,))
    if rho <= 0:
        raise ValueError("density must be > 0, got %r" % (rho,))
    return math.sqrt(2.0 * q / rho)


def combined_uncertainty(uncertainties):
    """Combine independent standard uncertainties by root sum square.

    The combined standard uncertainty is u_c = sqrt(sum u_i^2), valid
    for independent, uncorrelated contributors. The result is in the
    same unit as the contributors (m/s for airspeed channels).

    Returns the combined uncertainty as a float.

    Raises ValueError on an empty uncertainties list, a non-numeric (or
    bool) contributor, or a negative contributor.
    """
    u = _as_number_list(uncertainties, "uncertainties")
    for i, ui in enumerate(u):
        if ui < 0:
            raise ValueError("uncertainties[%d] must be >= 0, got %r" % (i, ui))
    return math.sqrt(sum(ui * ui for ui in u))


def data_quality_verdict(times, values, valid_min=None, valid_max=None, max_gap=None):
    """Data quality verdict for a reduced trace.

    Flags three issue classes before the analysis: NaN samples in
    values, values outside the valid range [valid_min, valid_max] (only
    when the bound is not None), and time gaps larger than max_gap in s
    between consecutive samples (only when max_gap is not None and the
    trace has more than one sample). Bounds and max_gap may be numeric
    or None; a None bound skips that check.

    Returns a dict with verdict ("ok" or "flagged") and issues, a list
    of {"type", "index", "detail"} dicts ordered by index.

    Raises ValueError on empty or length-mismatched times/values, a
    non-numeric (or bool) element in times or values, a NaN time, a
    non-numeric (or bool) bound, or max_gap <= 0.
    """
    t = _as_number_list(times, "times")
    v = _as_number_list(values, "values")
    if len(t) != len(v):
        raise ValueError(
            "times (%d) and values (%d) must have equal length" % (len(t), len(v))
        )
    for i, ti in enumerate(t):
        if math.isnan(ti):
            raise ValueError("times[%d] is NaN; timestamps must be usable" % i)
    lo = valid_min
    hi = valid_max
    if lo is not None:
        lo = _as_number(lo, "valid_min")
    if hi is not None:
        hi = _as_number(hi, "valid_max")
    gap = max_gap
    if gap is not None:
        gap = _as_number(gap, "max_gap")
        if gap <= 0:
            raise ValueError("max_gap must be > 0, got %r" % (gap,))
    issues = []
    for i, vi in enumerate(v):
        if math.isnan(vi):
            issues.append({"type": "nan", "index": i, "detail": "NaN sample"})
        elif (lo is not None and vi < lo) or (hi is not None and vi > hi):
            issues.append(
                {
                    "type": "out-of-range",
                    "index": i,
                    "detail": "value %.4g outside [%s, %s]"
                    % (vi, "unbounded" if lo is None else lo, "unbounded" if hi is None else hi),
                }
            )
    if gap is not None and len(t) > 1:
        for i in range(1, len(t)):
            d = t[i] - t[i - 1]
            if d > gap:
                issues.append(
                    {
                        "type": "gap",
                        "index": i,
                        "detail": "time gap of %.3f s exceeds %.3f s" % (d, gap),
                    }
                )
    return {"verdict": "ok" if not issues else "flagged", "issues": issues}
