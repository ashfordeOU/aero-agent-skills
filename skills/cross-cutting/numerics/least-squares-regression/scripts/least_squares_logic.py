#!/usr/bin/env python3
"""Ordinary least squares linear regression logic (stdlib only).

Fits the model y = a + b*x to paired (x, y) measurements by
minimizing the sum of squared residuals. Paraphrase of the standard
numerical methodology; NACA Report 824 is the pack's public-domain
anchor (standards-map.yaml); least squares regression is generic
numerical methodology, not RTCA or SAE content.

Conventions: n paired samples (x_i, y_i), n >= 3 so the residual
standard deviation has at least one degree of freedom. Means
xbar = sum(x)/n and ybar = sum(y)/n; Sxx = sum((x-xbar)**2) and
Sxy = sum((x-xbar)*(y-ybar)). The least squares slope is
b = Sxy / Sxx and the intercept is a = ybar - b*xbar. Residuals
r_i = y_i - (a + b*x_i) give SSE = sum(r_i**2); the residual
standard deviation is s = sqrt(SSE / (n - 2)) with n - 2 degrees of
freedom (one each for the estimated slope and intercept). The total
sum of squares SST = sum((y-ybar)**2) gives the coefficient of
determination r**2 = 1 - SSE / SST, dimensionless in [0, 1].

Units: a and s inherit the units of y, b is y per unit of x;
r**2 is dimensionless.
"""

import math


def _require_paired(xs, ys):
    """Raise ValueError unless xs and ys are equal-length, n >= 3."""
    if len(xs) != len(ys):
        raise ValueError(
            "xs and ys must have equal length: got %d and %d"
            % (len(xs), len(ys))
        )
    if len(xs) < 3:
        raise ValueError(
            "need at least 3 points for a residual estimate: got %d"
            % (len(xs),)
        )


def linear_fit(xs, ys):
    """Slope b and intercept a of the least squares line y = a + b*x.

    b = Sxy / Sxx with Sxx = sum((x-xbar)**2) and
    Sxy = sum((x-xbar)*(y-ybar)); a = ybar - b*xbar. Raises ValueError
    when fewer than 3 points, lengths differ, or Sxx == 0 (zero
    variance in x makes the slope undefined).
    """
    _require_paired(xs, ys)
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("zero variance in x: slope undefined")
    sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = ybar - b * xbar
    return b, a


def residual_std(xs, ys, a, b):
    """Residual standard deviation s = sqrt(SSE / (n - 2)).

    SSE = sum((y - (a + b*x))**2); the denominator n - 2 is the
    degrees of freedom of the two-parameter fit. Raises ValueError
    when fewer than 3 points or lengths differ.
    """
    _require_paired(xs, ys)
    n = len(xs)
    sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    return math.sqrt(sse / (n - 2))


def r_squared(xs, ys, a, b):
    """Coefficient of determination r**2 = 1 - SSE / SST.

    SST = sum((y - ybar)**2). Raises ValueError when fewer than 3
    points, lengths differ, or SST == 0 (constant response: the
    coefficient is undefined).
    """
    _require_paired(xs, ys)
    ybar = sum(ys) / len(ys)
    sst = sum((y - ybar) ** 2 for y in ys)
    if sst == 0.0:
        raise ValueError("zero total sum of squares: r squared undefined")
    sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    return 1.0 - sse / sst


def predict(x, a, b):
    """Predicted response y = a + b*x at input x."""
    return a + b * x


def fit_report(xs, ys):
    """One-shot fit: dict with slope, intercept, residual_std,
    r_squared, and n (all computed internally).
    """
    b, a = linear_fit(xs, ys)
    return {
        "slope": b,
        "intercept": a,
        "residual_std": residual_std(xs, ys, a, b),
        "r_squared": r_squared(xs, ys, a, b),
        "n": len(xs),
    }
