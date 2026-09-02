"""Table interpolation math for aerospace data tables.

Deterministic, offline, stdlib-only helpers for interpolating between
the tabulated points of a data table (aerodynamic polars, atmosphere
tables, calibration curves): single-segment linear interpolation,
piecewise linear interpolation over a whole table, the natural cubic
spline through the data points with its second-derivative coefficients,
and boundary-aware evaluation with optional extrapolation beyond the
table ends. Tables must be strictly increasing in x and well formed;
out-of-range reads raise ValueError unless extrapolation is requested.

Contract exercised by scripts/test_interpolation.py.
"""

import bisect
import math


def validate_table(xs, ys):
    """Raise ValueError unless xs and ys form a usable table.

    The table must hold at least 2 points, xs and ys must have the same
    length, every value must be finite, and xs must be strictly
    increasing. Returns None; raises ValueError describing the defect.
    """
    if len(xs) < 2:
        raise ValueError("table needs at least 2 points, got %d" % (len(xs),))
    if len(xs) != len(ys):
        raise ValueError(
            "xs and ys lengths differ: %d vs %d" % (len(xs), len(ys))
        )
    for i, v in enumerate(xs):
        if not math.isfinite(v):
            raise ValueError("xs[%d] is not finite: %r" % (i, v))
    for i, v in enumerate(ys):
        if not math.isfinite(v):
            raise ValueError("ys[%d] is not finite: %r" % (i, v))
    for i in range(1, len(xs)):
        if xs[i] <= xs[i - 1]:
            raise ValueError(
                "xs must be strictly increasing, xs[%d]=%r <= xs[%d]=%r"
                % (i, xs[i], i - 1, xs[i - 1])
            )


def find_segment(xs, x):
    """Return the index i with xs[i] <= x <= xs[i + 1].

    Binary search over the strictly increasing abscissas. Raises
    ValueError when x lies outside the table range; callers that want
    extrapolation handle the boundary cases themselves.
    """
    if x < xs[0] or x > xs[-1]:
        raise ValueError(
            "x=%r outside table range [%r, %r]" % (x, xs[0], xs[-1])
        )
    i = bisect.bisect_right(xs, x) - 1
    if i >= len(xs) - 1:
        i = len(xs) - 2
    return i


def linear_interpolate(x, x0, y0, x1, y1):
    """Return y at x on the straight segment (x0, y0) to (x1, y1).

    y = y0 + (y1 - y0) * (x - x0) / (x1 - x0). The formula also
    extrapolates when x lies outside [x0, x1]. Raises ValueError when
    x0 equals x1, which would divide by zero.
    """
    if x1 == x0:
        raise ValueError("segment endpoints share x=%r; cannot interpolate" % (x0,))
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def interpolate_linear(xs, ys, x, extrapolate=False):
    """Return the piecewise linear interpolation of the table at x.

    Finds the bracketing segment with find_segment and interpolates on
    it. When x lies outside the table and extrapolate is True, the end
    segment slope is extended; otherwise ValueError is raised.
    """
    validate_table(xs, ys)
    if x < xs[0]:
        if not extrapolate:
            raise ValueError(
                "x=%r below table start %r; pass extrapolate=True to extend"
                % (x, xs[0])
            )
        return linear_interpolate(x, xs[0], ys[0], xs[1], ys[1])
    if x > xs[-1]:
        if not extrapolate:
            raise ValueError(
                "x=%r above table end %r; pass extrapolate=True to extend"
                % (x, xs[-1])
            )
        return linear_interpolate(x, xs[-2], ys[-2], xs[-1], ys[-1])
    i = find_segment(xs, x)
    return linear_interpolate(x, xs[i], ys[i], xs[i + 1], ys[i + 1])


def natural_cubic_spline_coefficients(xs, ys):
    """Return the second derivatives m for the natural cubic spline.

    The natural spline is piecewise cubic, twice differentiable at the
    knots, and has zero second derivative at both ends. The interior
    second derivatives solve a tridiagonal system, solved here with the
    Thomas algorithm. With two points the spline degenerates to the
    straight segment and m is [0.0, 0.0]. Raises ValueError for a
    malformed table.
    """
    validate_table(xs, ys)
    n = len(xs)
    if n == 2:
        return [0.0, 0.0]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    u = n - 2  # interior unknowns m[1] .. m[n - 2]
    b = [2.0 * (h[r] + h[r + 1]) for r in range(u)]
    a = [h[r] for r in range(u)]
    c = [h[r + 1] for r in range(u)]
    d = [
        6.0 * ((ys[r + 2] - ys[r + 1]) / h[r + 1] - (ys[r + 1] - ys[r]) / h[r])
        for r in range(u)
    ]
    # Thomas algorithm: forward elimination.
    cp = [0.0] * u
    dp = [0.0] * u
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for r in range(1, u):
        denom = b[r] - a[r] * cp[r - 1]
        cp[r] = c[r] / denom
        dp[r] = (d[r] - a[r] * dp[r - 1]) / denom
    # Back substitution.
    xm = [0.0] * u
    xm[u - 1] = dp[u - 1]
    for r in range(u - 2, -1, -1):
        xm[r] = dp[r] - cp[r] * xm[r + 1]
    return [0.0] + xm + [0.0]


def cubic_spline_evaluate(xs, ys, coefficients, x, extrapolate=False):
    """Return the spline value at x for the given second derivatives.

    Evaluates the cubic segment that brackets x. When x lies outside
    the table and extrapolate is True, the end-segment polynomial is
    continued; otherwise ValueError is raised. The coefficients list
    must match the table length and normally comes from
    natural_cubic_spline_coefficients.
    """
    validate_table(xs, ys)
    if len(coefficients) != len(xs):
        raise ValueError(
            "coefficients length %d != table length %d"
            % (len(coefficients), len(xs))
        )
    if x < xs[0]:
        if not extrapolate:
            raise ValueError(
                "x=%r below table start %r; pass extrapolate=True to extend"
                % (x, xs[0])
            )
        i = 0
    elif x > xs[-1]:
        if not extrapolate:
            raise ValueError(
                "x=%r above table end %r; pass extrapolate=True to extend"
                % (x, xs[-1])
            )
        i = len(xs) - 2
    else:
        i = find_segment(xs, x)
    x0, x1 = xs[i], xs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    m0, m1 = coefficients[i], coefficients[i + 1]
    h = x1 - x0
    t = (x1 - x) / h
    s = (x - x0) / h
    return (
        m0 * t * t * t * h * h / 6.0
        + m1 * s * s * s * h * h / 6.0
        + (y0 - m0 * h * h / 6.0) * t
        + (y1 - m1 * h * h / 6.0) * s
    )


def interpolate_cubic(xs, ys, x, extrapolate=False):
    """Return the natural cubic spline interpolation of the table at x.

    Convenience wrapper: builds the coefficients with
    natural_cubic_spline_coefficients and evaluates with
    cubic_spline_evaluate, so a one-call interpolation needs no
    coefficient bookkeeping.
    """
    m = natural_cubic_spline_coefficients(xs, ys)
    return cubic_spline_evaluate(xs, ys, m, x, extrapolate=extrapolate)
