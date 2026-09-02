#!/usr/bin/env python3
"""First-order ODE solvers (stdlib only, offline).

Implements the explicit Euler method, Heun's method (RK2), and the
classical RK4 method for the initial value problem
dy/dt = f(t, y), y(t0) = y0, plus a max-absolute-error helper that
compares a numerical solution against a closed-form exact solution.
All functions are deterministic, validate their inputs, and raise
ValueError with a clear message on invalid arguments.

Worked anchors (dy/dt = -y, y(0) = 1, exact y(t) = e**(-t)):
- Euler, h = 0.1: y(0.5) = 0.59049 (exact 0.60653, error 1.60e-2).
- Heun (RK2), h = 0.1: y(0.5) = 0.60708 (error 5.5e-4).
- RK4, h = 0.1: y(0.5) = 0.60653 (error 2.7e-7).
Halving h cuts the Euler error by ~2, the Heun error by ~4, and the
RK4 error by ~16: order 1, 2, and 4 respectively.
"""


def _validate(f, t0, y0, h, n):
    """Shared input validation; raises ValueError on invalid arguments."""
    if not callable(f):
        raise ValueError("f must be a callable f(t, y)")
    for name, val in (("t0", t0), ("y0", y0)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be a real number" % name)
    if isinstance(h, bool) or not isinstance(h, (int, float)):
        raise ValueError("h must be a real number")
    if h <= 0:
        raise ValueError("h must be strictly positive")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")


def euler(f, t0, y0, h, n):
    """Explicit Euler: y_{k+1} = y_k + h * f(t_k, y_k).

    First-order accurate (global error O(h)). Returns a list of n + 1
    (t, y) pairs from (t0, y0) to (t0 + n*h, y_n). Worked anchor:
    dy/dt = -y, y(0) = 1, h = 0.1 gives y(0.5) = (0.9)**5 = 0.59049
    against the exact e**(-0.5) = 0.60653. Raises ValueError on
    invalid inputs.
    """
    _validate(f, t0, y0, h, n)
    sol = [(float(t0), float(y0))]
    t, y = float(t0), float(y0)
    for _ in range(n):
        y = y + h * f(t, y)
        t = t + h
        sol.append((t, y))
    return sol


def heun(f, t0, y0, h, n):
    """Heun's method (RK2): predictor y_p = y_k + h * f(t_k, y_k),
    corrector y_{k+1} = y_k + (h/2) * (f(t_k, y_k) + f(t_k + h, y_p)).

    Second-order accurate (global error O(h**2)); the trapezoid
    average of the slopes makes it exact for RHS linear in t.
    Returns a list of n + 1 (t, y) pairs. Worked anchor: dy/dt = -y,
    y(0) = 1, h = 0.1 gives y(0.5) = 0.60708 against the exact
    0.60653. Raises ValueError on invalid inputs.
    """
    _validate(f, t0, y0, h, n)
    sol = [(float(t0), float(y0))]
    t, y = float(t0), float(y0)
    for _ in range(n):
        fp = f(t, y)
        yp = y + h * fp
        y = y + 0.5 * h * (fp + f(t + h, yp))
        t = t + h
        sol.append((t, y))
    return sol


def rk4(f, t0, y0, h, n):
    """Classical RK4: k1 = f(t_k, y_k), k2 = f(t_k + h/2, y_k + h*k1/2),
    k3 = f(t_k + h/2, y_k + h*k2/2), k4 = f(t_k + h, y_k + h*k3),
    y_{k+1} = y_k + (h/6) * (k1 + 2*k2 + 2*k3 + k4).

    Fourth-order accurate (global error O(h**4)); exact for RHS that
    are polynomials in t of degree <= 3. Returns a list of n + 1
    (t, y) pairs. Worked anchor: dy/dt = -y, y(0) = 1, h = 0.1 gives
    y(0.5) = 0.60653 against the exact 0.60653. Raises ValueError on
    invalid inputs.
    """
    _validate(f, t0, y0, h, n)
    sol = [(float(t0), float(y0))]
    t, y = float(t0), float(y0)
    for _ in range(n):
        k1 = f(t, y)
        k2 = f(t + 0.5 * h, y + 0.5 * h * k1)
        k3 = f(t + 0.5 * h, y + 0.5 * h * k2)
        k4 = f(t + h, y + h * k3)
        y = y + h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        t = t + h
        sol.append((t, y))
    return sol


def max_abs_error(sol, exact):
    """Maximum absolute error of a numerical solution against exact.

    exact is a callable exact(t) giving the closed-form solution.
    Returns max over all solution points of abs(y_k - exact(t_k)).
    Raises ValueError when exact is not callable or sol is empty.
    """
    if not callable(exact):
        raise ValueError("exact must be a callable exact(t)")
    if not sol:
        raise ValueError("sol must be a non-empty list of (t, y) pairs")
    err = 0.0
    for t, y in sol:
        err = max(err, abs(y - exact(t)))
    return err
