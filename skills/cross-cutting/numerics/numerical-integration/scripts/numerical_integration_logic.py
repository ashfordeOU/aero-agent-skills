#!/usr/bin/env python3
"""Composite quadrature for definite integrals (stdlib only, offline).

Implements the composite trapezoid rule, the composite Simpson rule
(which requires an even number of subintervals), Gauss-Legendre
quadrature with a fixed set of node counts (n = 2..5, exact for
polynomials of degree <= 2n-1), and a Richardson extrapolation based
error estimate for the trapezoid rule. All functions raise ValueError
on invalid inputs and are deterministic.
"""

# Gauss-Legendre nodes and weights on [-1, 1] (standard tables,
# Abramowitz and Stegun 25.4). n-point quadrature is exact for
# polynomials of degree <= 2n - 1.
_GAUSS_LEGENDRE = {
    2: [
        (-0.5773502691896257, 1.0),
        (0.5773502691896257, 1.0),
    ],
    3: [
        (-0.7745966692414834, 0.5555555555555556),
        (0.0, 0.8888888888888888),
        (0.7745966692414834, 0.5555555555555556),
    ],
    4: [
        (-0.8611363115940526, 0.3478548451374538),
        (-0.3399810435848563, 0.6521451548625461),
        (0.3399810435848563, 0.6521451548625461),
        (0.8611363115940526, 0.3478548451374538),
    ],
    5: [
        (-0.9061798459386640, 0.2369268850561891),
        (-0.5384693101056831, 0.4786286704993665),
        (0.0, 0.5688888888888889),
        (0.5384693101056831, 0.4786286704993665),
        (0.9061798459386640, 0.2369268850561891),
    ],
}


def trapezoid(f, a, b, n):
    """Composite trapezoid rule over n subintervals of [a, b].

    I = (b - a) / (2 n) * (f(a) + f(b) + 2 * sum_{i=1}^{n-1} f(a + i h)),
    with h = (b - a) / n. Returns the integral estimate. Raises
    ValueError when n < 1.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += 2.0 * f(a + i * h)
    return h * total / 2.0


def simpson(f, a, b, n):
    """Composite Simpson rule over n subintervals of [a, b], n even.

    I = (b - a) / (3 n) * (f(a) + f(b) + 4 * sum_odd + 2 * sum_even),
    where sum_odd sums f at interior nodes 1, 3, ..., n-1 and sum_even
    sums f at interior nodes 2, 4, ..., n-2. Exact for polynomials of
    degree <= 3. Raises ValueError when n is odd or n < 2.
    """
    if not isinstance(n, int) or n < 2 or n % 2 != 0:
        raise ValueError("n must be an even integer >= 2")
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4.0 if i % 2 == 1 else 2.0) * f(a + i * h)
    return h * total / 3.0


def gauss_legendre(f, a, b, n):
    """n-point Gauss-Legendre quadrature on [a, b], n in {2, 3, 4, 5}.

    I = (b - a) / 2 * sum_i w_i f((b - a) / 2 * x_i + (a + b) / 2),
    where (x_i, w_i) are the fixed nodes and weights on [-1, 1]. The
    n-point rule is exact for polynomials of degree <= 2n - 1, so a
    small node count beats a large composite rule on smooth
    integrands. Raises ValueError when n is not one of the supported
    node counts or when the node table is absent.
    """
    if not isinstance(n, int) or n not in _GAUSS_LEGENDRE:
        raise ValueError("n must be one of 2, 3, 4, 5 (fixed Gauss-Legendre node counts)")
    half = (b - a) / 2.0
    mid = (a + b) / 2.0
    total = 0.0
    for x, w in _GAUSS_LEGENDRE[n]:
        total += w * f(half * x + mid)
    return half * total


def error_estimate_trapezoid(f, a, b, n):
    """Richardson error estimate for the composite trapezoid rule.

    The trapezoid error scales with h**2, so combining the n and 2 n
    estimates gives, to leading order, error(2n) = (I_2n - I_n) / 3.
    Returns the absolute value of that estimate. Raises ValueError
    when n < 1.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    i_n = trapezoid(f, a, b, n)
    i_2n = trapezoid(f, a, b, 2 * n)
    return abs(i_2n - i_n) / 3.0
