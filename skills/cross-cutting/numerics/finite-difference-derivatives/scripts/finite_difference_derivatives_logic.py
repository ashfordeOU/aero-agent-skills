"""Finite difference derivative logic (forward, backward, central).

Paraphrase of the standard finite difference method for numerical
differentiation. NACA Report 824 is the pack's public-domain anchor
(standards-map.yaml); finite difference stencils are generic numerical
methodology, not RTCA or SAE content.

Conventions: forward_difference uses (f(x + h) - f(x)) / h, the
one-sided stencil with error O(h); backward_difference uses
(f(x) - f(x - h)) / h, also O(h); central_difference uses
(f(x + h) - f(x - h)) / (2 h), the centered stencil with error O(h^2);
second_central_difference uses (f(x + h) - 2 f(x) + f(x - h)) / h^2,
the centered three point stencil for the second derivative with error
O(h^2). tabulated_derivative differentiates evenly spaced tabulated
data: the centered stencil at interior points and the one-sided
stencils at the first and last points; the spacing must be uniform
within a relative tolerance of 1e-9.

All stencil functions raise ValueError when the step h is not strictly
positive. tabulated_derivative raises ValueError when the arrays have
different lengths, when fewer than two points are given, or when the
tabulated spacing is not uniform.
"""


def forward_difference(f, x, h):
    """First derivative with the forward stencil (error O(h))."""
    if h <= 0.0:
        raise ValueError("step h must be > 0: got h=%r" % (h,))
    return (f(x + h) - f(x)) / h


def backward_difference(f, x, h):
    """First derivative with the backward stencil (error O(h))."""
    if h <= 0.0:
        raise ValueError("step h must be > 0: got h=%r" % (h,))
    return (f(x) - f(x - h)) / h


def central_difference(f, x, h):
    """First derivative with the centered stencil (error O(h^2))."""
    if h <= 0.0:
        raise ValueError("step h must be > 0: got h=%r" % (h,))
    return (f(x + h) - f(x - h)) / (2.0 * h)


def second_central_difference(f, x, h):
    """Second derivative with the centered three point stencil."""

    if h <= 0.0:
        raise ValueError("step h must be > 0: got h=%r" % (h,))
    return (f(x + h) - 2.0 * f(x) + f(x - h)) / (h * h)


def _check_spacing(xs, tol=1e-9):
    dx = xs[1] - xs[0]
    if dx <= 0.0:
        raise ValueError("tabulated x values must be strictly increasing")
    for i in range(2, len(xs)):
        step = xs[i] - xs[i - 1]
        if abs(step - dx) > tol * max(1.0, abs(dx)):
            raise ValueError(
                "tabulated x values must be evenly spaced: got step %r at index %d"
                % (step, i)
            )
    return dx


def tabulated_derivative(xs, ys):
    """First derivatives of evenly spaced tabulated data (xs, ys).

    Returns a list of derivative estimates aligned with the input
    points: the centered stencil at interior points, the forward
    stencil at the first point, and the backward stencil at the last
    point. Raises ValueError on length mismatch, fewer than two
    points, or non-uniform spacing.
    """
    if len(xs) != len(ys):
        raise ValueError(
            "xs and ys must have equal length: got %d and %d" % (len(xs), len(ys))
        )
    if len(xs) < 2:
        raise ValueError("tabulated data needs at least 2 points")
    dx = _check_spacing(xs)
    out = []
    n = len(xs)
    for i in range(n):
        if i == 0:
            out.append((ys[1] - ys[0]) / dx)
        elif i == n - 1:
            out.append((ys[n - 1] - ys[n - 2]) / dx)
        else:
            out.append((ys[i + 1] - ys[i - 1]) / (2.0 * dx))
    return out
