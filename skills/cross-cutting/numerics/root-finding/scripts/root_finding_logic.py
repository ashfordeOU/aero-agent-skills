#!/usr/bin/env python3
"""Numerical root-finding methods (stdlib only, offline).

Implements the bisection method, Newton-Raphson, the secant method,
and fixed-point iteration for a nonlinear scalar equation f(x) = 0,
plus a fixed-point helper. All functions are deterministic, validate
their inputs, and raise ValueError with a clear message on invalid
arguments:

- bisection raises when the bracket [a, b] does not straddle zero
  (f(a) and f(b) share a sign) and when the interval does not shrink
  to the tolerance within max_iter iterations.
- newton_raphson raises when the derivative is zero at a step (the
  update x - f/df is undefined) and when the iteration does not
  converge within max_iter iterations.
- secant raises when the secant slope f(x_k) - f(x_{k-1}) is zero
  (the step is undefined) and when the iteration does not converge
  within max_iter iterations.
- fixed_point_iteration raises when the iteration does not converge
  within max_iter iterations.

Worked anchors (f(x) = x**2 - 2, root sqrt(2) = 1.4142135623730951):
- Bisection on [1, 2]: each step halves the interval, so after k
  steps the error is at most 2**(-k).
- Newton-Raphson from x0 = 1.5: quadratic convergence, three steps
  reach machine precision (1.41421356237).
- Secant from x0 = 1, x1 = 2: superlinear convergence (order about
  1.618), a handful of steps reach machine precision.
Aerospace anchor: the isentropic area-Mach relation
A/A* = (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M**2)) **
((gamma+1)/(2*(gamma-1))) for gamma = 1.4 is inverted by any of the
methods; A/A* = 1.2 has a subsonic root near M = 0.552 and a
supersonic root near M = 1.534.
"""

import math


def _validate_scalar(name, val):
    """Raise ValueError unless val is a real number (bool rejected)."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError("%s must be a real number" % name)


def _validate_tol(tol):
    if isinstance(tol, bool) or not isinstance(tol, (int, float)):
        raise ValueError("tol must be a real number")
    if tol <= 0:
        raise ValueError("tol must be strictly positive")


def _validate_max_iter(max_iter):
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter must be a positive integer")


def bisection(f, a, b, tol=1e-10, max_iter=100):
    """Root of f(x) = 0 on [a, b] by the bisection method.

    Requires f(a) and f(b) to straddle zero (f(a) * f(b) < 0), so a
    sign change is bracketed; each step evaluates the midpoint
    c = (a + b) / 2 and halves the interval. Returns the midpoint
    once the interval half-width is below tol (step tolerance) or
    f(c) is exactly zero. Linear convergence: one binary digit per
    step. Raises ValueError when the bracket does not straddle zero
    or when the interval does not reach tol within max_iter steps.
    """
    if not callable(f):
        raise ValueError("f must be a callable f(x)")
    _validate_scalar("a", a)
    _validate_scalar("b", b)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    a, b = float(a), float(b)
    if a > b:
        a, b = b, a
    fa = f(a)
    fb = f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise ValueError(
            "bracket [a, b] does not straddle zero: f(a) and f(b) have the same sign"
        )
    for _ in range(max_iter):
        c = 0.5 * (a + b)
        fc = f(c)
        if fc == 0.0:
            return c
        if 0.5 * (b - a) < tol:
            return c
        if fa * fc < 0.0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    raise ValueError(
        "bisection did not converge to tolerance %g within %d iterations"
        % (tol, max_iter)
    )


def newton_raphson(f, df, x0, tol=1e-10, max_iter=100):
    """Root of f(x) = 0 by Newton-Raphson from the initial guess x0.

    Iterates x_{k+1} = x_k - f(x_k) / df(x_k). Quadratic convergence
    for a simple root when the guess is close enough; requires the
    derivative df. Convergence is declared on the function tolerance
    abs(f(x)) < tol. Raises ValueError when the derivative is zero at
    a step (the update is undefined), when the derivative is not
    finite (ill-conditioned function), or when the iteration does not
    converge within max_iter iterations.
    """
    if not callable(f) or not callable(df):
        raise ValueError("f and df must be callables")
    _validate_scalar("x0", x0)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    x = float(x0)
    for _ in range(max_iter):
        fx = f(x)
        if abs(fx) < tol:
            return x
        dfx = df(x)
        if dfx == 0.0:
            raise ValueError(
                "derivative is zero at x = %g; Newton-Raphson step is undefined" % x
            )
        if not math.isfinite(dfx):
            raise ValueError(
                "derivative is not finite at x = %g; the function is ill-conditioned" % x
            )
        x = x - fx / dfx
        if not math.isfinite(x):
            raise ValueError(
                "Newton-Raphson produced a non-finite iterate; the iteration diverged"
            )
    raise ValueError(
        "newton-raphson did not converge within %d iterations" % max_iter
    )


def secant(f, x0, x1, tol=1e-10, max_iter=100):
    """Root of f(x) = 0 by the secant method from two initial guesses.

    Iterates x_{k+1} = x_k - f(x_k) * (x_k - x_{k-1}) /
    (f(x_k) - f(x_{k-1})), approximating the derivative by the secant
    slope, so no analytic derivative is needed. Superlinear
    convergence (order about 1.618) for a simple root. Convergence is
    declared on the function tolerance abs(f(x)) < tol. Raises
    ValueError when the secant slope is zero (the step is undefined)
    or when the iteration does not converge within max_iter
    iterations.
    """
    if not callable(f):
        raise ValueError("f must be a callable f(x)")
    _validate_scalar("x0", x0)
    _validate_scalar("x1", x1)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    x_prev, x_cur = float(x0), float(x1)
    f_prev = f(x_prev)
    f_cur = f(x_cur)
    if abs(f_prev) < tol:
        return x_prev
    if abs(f_cur) < tol:
        return x_cur
    for _ in range(max_iter):
        if abs(f_cur) < tol:
            return x_cur
        if f_cur == f_prev:
            raise ValueError(
                "secant step is undefined: f(x0) equals f(x1), the secant slope is zero"
            )
        x_next = x_cur - f_cur * (x_cur - x_prev) / (f_cur - f_prev)
        if not math.isfinite(x_next):
            raise ValueError(
                "secant produced a non-finite iterate; the iteration diverged"
            )
        x_prev, f_prev = x_cur, f_cur
        x_cur, f_cur = x_next, f(x_next)
    raise ValueError(
        "secant method did not converge within %d iterations" % max_iter
    )


def fixed_point_iteration(g, x0, tol=1e-10, max_iter=100):
    """Fixed point of g(x) = x by the iteration x_{k+1} = g(x_k).

    Converges when g is a contraction near the fixed point, in
    practice when abs(g'(x*)) < 1 at the fixed point x*. Convergence
    is declared on the step tolerance abs(x_{k+1} - x_k) < tol.
    Raises ValueError when the iteration produces a non-finite
    iterate or does not converge within max_iter iterations.
    """
    if not callable(g):
        raise ValueError("g must be a callable g(x)")
    _validate_scalar("x0", x0)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    x = float(x0)
    for _ in range(max_iter):
        x_next = g(x)
        if not math.isfinite(x_next):
            raise ValueError(
                "fixed-point iteration produced a non-finite iterate; the iteration diverged"
            )
        if abs(x_next - x) < tol:
            return x_next
        x = x_next
    raise ValueError(
        "fixed-point iteration did not converge within %d iterations" % max_iter
    )
