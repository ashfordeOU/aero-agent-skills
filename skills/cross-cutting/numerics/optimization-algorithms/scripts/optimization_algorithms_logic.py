#!/usr/bin/env python3
"""Numerical optimization algorithms for unconstrained minimization
(stdlib only, offline).

Implements four deterministic minimizers: golden-section search for a
1D bounded minimum, gradient descent with an Armijo backtracking line
search for multivariate problems, the Nelder-Mead simplex method for
derivative-free multivariate minimization, and Newton's method applied
to the derivative for smooth 1D problems. All functions validate their
inputs and raise ValueError with a clear message on invalid arguments:

- golden_section_minimize raises when the bracket is empty (a == b),
  when the triple (f(a), f(mid), f(b)) is not unimodal with the
  minimum strictly inside the bracket, and when the interval does not
  shrink to tol within max_iter iterations.
- gradient_descent raises on a non-positive learning rate, a failed
  Armijo line search, and non-convergence to the gradient tolerance
  within max_iter iterations.
- nelder_mead raises when the objective is not finite at a simplex
  vertex and when the simplex does not collapse to tol within max_iter
  iterations. The seed argument is accepted for interface
  compatibility; the method is fully deterministic and uses no
  randomness, so the seed is ignored.
- newton_1d_minimize raises when the second derivative is zero at a
  step (the update is undefined), when an iterate or derivative is
  not finite, and when the iteration does not converge within
  max_iter iterations.

Worked anchors (verified by scripts/test_optimization_algorithms.py):
- golden_section_minimize on f(x) = (x - 3)**2 + 2 over [0, 10]
  returns x = 3.0 (within 1e-4) and f = 2.0 in 34 interval updates.
- gradient_descent on f(x, y) = x**2 + 2*y**2 from (1, 1) with a
  backtracking line search converges to (0, 0) with f below 1e-12.
- nelder_mead on f(x) = (x - 2)**2 + 1 from x0 = 0.0 converges to
  x = 2.0; on the Rosenbrock function it converges near (1, 1).
- newton_1d_minimize on f(x) = (x - 3)**2 + 2 from x0 = 10.0 lands on
  x = 3.0 in one step (the Newton update is exact for a quadratic).

Conventions: golden_section_minimize and newton_1d_minimize are
scalar (x is a float). gradient_descent and nelder_mead accept either
a scalar x0 for 1D problems (f receives a float) or a sequence of
coordinates for multivariate problems (f receives a tuple; grad
returns a sequence of the same length).
"""

import math

# Golden-section ratio and coefficients (module constants, no magic
# numbers inline).
PHI = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio, interval shrink per step
ARMIJO_C1 = 1e-4                     # sufficient-decrease constant
BACKTRACK_FACTOR = 0.5               # learning-rate halving factor
BACKTRACK_MAX = 60                   # max halvings in one line search
NM_RHO = 1.0                         # Nelder-Mead reflection coefficient
NM_CHI = 2.0                         # Nelder-Mead expansion coefficient
NM_GAMMA = 0.5                       # Nelder-Mead contraction coefficient
NM_SIGMA = 0.5                       # Nelder-Mead shrink coefficient
SIMPLEX_H = 0.05                     # relative initial-simplex perturbation
SIMPLEX_H_ZERO = 2.5e-4              # absolute perturbation at a zero coordinate


def _validate_callable(fn, name):
    """Raise ValueError unless fn is callable."""
    if not callable(fn):
        raise ValueError("%s must be a callable" % name)


def _validate_real(name, val):
    """Raise ValueError unless val is a finite real number (bool rejected)."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError("%s must be a real number" % name)
    if not math.isfinite(float(val)):
        raise ValueError("%s must be finite" % name)


def _validate_tol(tol):
    if isinstance(tol, bool) or not isinstance(tol, (int, float)):
        raise ValueError("tol must be a real number")
    if not math.isfinite(float(tol)):
        raise ValueError("tol must be finite")
    if tol <= 0:
        raise ValueError("tol must be strictly positive")


def _validate_max_iter(max_iter):
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter must be a positive integer")


def _validate_finite(name, val):
    """Raise ValueError unless val is a finite number."""
    if not math.isfinite(val):
        raise ValueError("%s must be finite, got %r" % (name, val))


def _point_from(x0):
    """Normalize x0 to (is_scalar, [coords]).

    A scalar x0 selects 1D mode, where objective callables receive a
    float. A list or tuple of finite reals selects vector mode, where
    objective callables receive a tuple of coordinates.
    """
    if isinstance(x0, bool):
        raise ValueError("x0 must be a real number or a sequence of real numbers")
    if isinstance(x0, (int, float)):
        _validate_real("x0", x0)
        return True, [float(x0)]
    if isinstance(x0, (list, tuple)):
        if len(x0) == 0:
            raise ValueError("x0 must not be empty")
        coords = []
        for val in x0:
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError("x0 entries must be real numbers")
            _validate_real("x0 entry", val)
            coords.append(float(val))
        return False, coords
    raise ValueError("x0 must be a real number or a sequence of real numbers")


def golden_section_minimize(f, a, b, tol=1e-6, max_iter=200):
    """Minimum of a 1D unimodal function on [a, b] by golden-section search.

    Uses the golden ratio PHI = (1 + sqrt(5)) / 2: with c = b - (b-a)/PHI
    and d = a + (b-a)/PHI inside the bracket, each step evaluates f(c)
    and f(d) and discards the interval end adjacent to the larger
    value, shrinking the bracket by the factor 1/PHI per step. The
    bracket must be unimodal with the minimum strictly inside: the
    midpoint m = (a + b) / 2 must satisfy f(m) < f(a) and f(m) < f(b);
    otherwise the search is not bracketing and ValueError is raised.
    Convergence is declared on the step tolerance (b - a) < tol, and
    the returned x is the bracket midpoint. Returns
    (x_min, f_min, iterations). Raises ValueError for an empty or
    non-unimodal bracket, non-finite endpoints, tol <= 0, and
    non-convergence within max_iter iterations.
    """
    _validate_callable(f, "f")
    _validate_real("a", a)
    _validate_real("b", b)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    a, b = float(a), float(b)
    if a > b:
        a, b = b, a
    if a == b:
        raise ValueError("empty bracket: a and b must differ")
    mid = 0.5 * (a + b)
    fa = f(a)
    fm = f(mid)
    fb = f(b)
    _validate_finite("f(a)", fa)
    _validate_finite("f(mid)", fm)
    _validate_finite("f(b)", fb)
    if not (fm < fa and fm < fb):
        raise ValueError(
            "bracket [a, b] is not unimodal: need f(mid) < f(a) and "
            "f(mid) < f(b), with the minimum strictly inside the bracket"
        )
    c = b - (b - a) / PHI
    d = a + (b - a) / PHI
    iterations = 0
    while b - a > tol and iterations < max_iter:
        fc = f(c)
        fd = f(d)
        _validate_finite("f(c)", fc)
        _validate_finite("f(d)", fd)
        if fc < fd:
            b = d
            d = c
            c = b - (b - a) / PHI
        else:
            a = c
            c = d
            d = a + (b - a) / PHI
        iterations += 1
    if b - a >= tol:
        raise ValueError(
            "golden-section search did not reach tolerance %g within %d iterations"
            % (tol, max_iter)
        )
    x_min = 0.5 * (a + b)
    return x_min, f(x_min), iterations


def gradient_descent(f, grad, x0, lr, tol=1e-6, max_iter=10000):
    """Multivariate steepest descent with an Armijo backtracking step.

    Iterates x_{k+1} = x_k - lr_k * grad(x_k) with the descent
    direction the negative gradient. Each step starts from the given
    learning rate lr and backtracks, halving lr_k, until the Armijo
    sufficient-decrease condition f(x - lr_k * g) <= f(x) -
    C1 * lr_k * ||g||**2 holds with C1 = 1e-4. Convergence is declared
    on the gradient tolerance ||grad(x)|| < tol. Returns
    (x_min, f_min, iterations) where x_min is a float in 1D mode (x0
    scalar) and a tuple of coordinates in vector mode (x0 a sequence).
    Raises ValueError for a non-positive learning rate, a failed line
    search, a non-finite objective, and non-convergence within
    max_iter iterations.
    """
    _validate_callable(f, "f")
    _validate_callable(grad, "grad")
    _validate_real("lr", lr)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    lr = float(lr)
    if lr <= 0:
        raise ValueError("lr must be strictly positive")
    scalar, x_start = _point_from(x0)
    n = len(x_start)

    def evaluate(xlist):
        val = f(xlist[0]) if scalar else f(tuple(xlist))
        _validate_finite("objective value", val)
        return val

    def evaluate_grad(xlist):
        g = grad(xlist[0]) if scalar else grad(tuple(xlist))
        if scalar:
            if isinstance(g, bool) or not isinstance(g, (int, float)):
                if isinstance(g, (list, tuple)) and len(g) == 1:
                    g = g[0]
                else:
                    raise ValueError(
                        "grad must return a single number in 1D mode, got %r" % (g,)
                    )
            g = [float(g)]
        else:
            if isinstance(g, bool) or not isinstance(g, (list, tuple)):
                raise ValueError(
                    "grad must return a sequence of the length of x in "
                    "vector mode, got %r" % (g,)
                )
            g = [float(gi) for gi in g]
            if len(g) != n:
                raise ValueError(
                    "gradient length %d does not match x length %d" % (len(g), n)
                )
        for gi in g:
            _validate_finite("gradient entry", gi)
        return g

    x_cur = list(x_start)
    fx = evaluate(x_cur)
    iterations = 0
    while True:
        g = evaluate_grad(x_cur)
        gnorm2 = sum(gi * gi for gi in g)
        if math.sqrt(gnorm2) < tol:
            return (x_cur[0] if scalar else tuple(x_cur)), fx, iterations
        if iterations >= max_iter:
            raise ValueError(
                "gradient descent did not converge to gradient tolerance %g "
                "within %d iterations" % (tol, max_iter)
            )
        step = lr
        accepted_candidate = None
        accepted_value = None
        for _ in range(BACKTRACK_MAX):
            candidate = [xi - step * gi for xi, gi in zip(x_cur, g)]
            for xi in candidate:
                _validate_finite("iterate", xi)
            f_candidate = evaluate(candidate)
            if f_candidate <= fx - ARMIJO_C1 * step * gnorm2:
                accepted_candidate = candidate
                accepted_value = f_candidate
                break
            step *= BACKTRACK_FACTOR
        if accepted_candidate is None:
            raise ValueError(
                "Armijo line search failed from x with learning rate %g; "
                "the objective may be non-smooth or the step cannot decrease it"
                % lr
            )
        assert accepted_value is not None  # accepted_candidate implies a value
        x_cur = accepted_candidate
        fx = accepted_value
        iterations += 1


def nelder_mead(f, x0, tol=1e-6, max_iter=10000, seed=None):
    """Derivative-free minimization by the Nelder-Mead simplex method.

    Maintains a simplex of n + 1 vertices (a segment for 1D problems)
    ordered by objective value and replaces the worst vertex through
    reflection (coefficient NM_RHO), expansion (NM_CHI) when the
    reflection is a new best, and inside or outside contraction
    (NM_GAMMA); when no contraction improves the worst vertex the
    simplex shrinks toward the best vertex (NM_SIGMA). No derivatives
    are used. The initial simplex is deterministic: vertex i = x0 with
    coordinate i perturbed by SIMPLEX_H * abs(x0_i), or by
    SIMPLEX_H_ZERO when x0_i is zero, so repeated calls are identical
    and seed is ignored (accepted for interface compatibility).
    Convergence is declared when the spread of the vertex objective
    values, max(f) - min(f), drops below tol. Returns
    (x_min, f_min, iterations) with x_min a float in 1D mode (x0
    scalar) and a tuple of coordinates in vector mode (x0 a sequence).
    Raises ValueError for a non-finite objective at a vertex and for
    non-convergence within max_iter iterations.
    """
    _validate_callable(f, "f")
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    scalar, x0v = _point_from(x0)
    n = len(x0v)

    def evaluate(xlist):
        val = f(xlist[0]) if scalar else f(tuple(xlist))
        _validate_finite("objective value", val)
        return val

    simplex = [[list(x0v), evaluate(x0v)]]
    for i in range(n):
        point = list(x0v)
        if point[i] == 0.0:
            point[i] = SIMPLEX_H_ZERO
        else:
            point[i] += SIMPLEX_H * abs(point[i])
        simplex.append([point, evaluate(point)])

    iterations = 0
    while True:
        simplex.sort(key=lambda row: row[1])
        best = simplex[0][0]
        best_f = simplex[0][1]
        worst_f = simplex[-1][1]
        if worst_f - best_f < tol:
            return (best[0] if scalar else tuple(best)), best_f, iterations
        if iterations >= max_iter:
            raise ValueError(
                "nelder-mead did not converge to tolerance %g within %d iterations"
                % (tol, max_iter)
            )
        worst = simplex[-1][0]
        second_worst_f = simplex[-2][1]
        centroid = [
            sum(simplex[i][0][j] for i in range(n)) / n for j in range(n)
        ]
        reflected = [
            centroid[j] + NM_RHO * (centroid[j] - worst[j]) for j in range(n)
        ]
        f_reflected = evaluate(reflected)
        if f_reflected < best_f:
            expanded = [
                centroid[j] + NM_CHI * (reflected[j] - centroid[j])
                for j in range(n)
            ]
            f_expanded = evaluate(expanded)
            if f_expanded < f_reflected:
                simplex[-1] = [expanded, f_expanded]
            else:
                simplex[-1] = [reflected, f_reflected]
        elif f_reflected < second_worst_f:
            simplex[-1] = [reflected, f_reflected]
        else:
            if f_reflected < worst_f:
                # Outside contraction: pull the reflected point back in.
                contracted = [
                    centroid[j] + NM_GAMMA * (reflected[j] - centroid[j])
                    for j in range(n)
                ]
                f_contracted = evaluate(contracted)
                if f_contracted <= f_reflected:
                    simplex[-1] = [contracted, f_contracted]
                else:
                    _shrink(simplex, best, evaluate)
            else:
                # Inside contraction: pull the worst vertex toward the
                # centroid.
                contracted = [
                    centroid[j] + NM_GAMMA * (worst[j] - centroid[j])
                    for j in range(n)
                ]
                f_contracted = evaluate(contracted)
                if f_contracted < worst_f:
                    simplex[-1] = [contracted, f_contracted]
                else:
                    _shrink(simplex, best, evaluate)
        iterations += 1


def _shrink(simplex, best, evaluate):
    """Shrink every non-best vertex toward the best vertex (NM_SIGMA)."""
    for row in simplex[1:]:
        point = row[0]
        for j in range(len(point)):
            point[j] = best[j] + NM_SIGMA * (point[j] - best[j])
        row[1] = evaluate(point)


def newton_1d_minimize(f, fp, fpp, x0, tol=1e-6, max_iter=100):
    """Minimum of a smooth 1D function by Newton's method on f'.

    Applies Newton iteration to the derivative fp(x) = 0:
    x_{k+1} = x_k - fp(x_k) / fpp(x_k). Quadratic convergence near a
    stationary point when the second derivative fpp is non-zero; the
    method finds a stationary point of f, which is a minimum when
    fpp > 0 there (evaluate fpp at the solution to confirm the
    curvature before accepting the result). Convergence is declared on
    the derivative tolerance abs(fp(x)) < tol. Returns
    (x_min, f_min, iterations). Raises ValueError when fpp is zero at
    a step (the update is undefined), when a derivative or iterate is
    not finite, and when the iteration does not converge within
    max_iter iterations.
    """
    _validate_callable(f, "f")
    _validate_callable(fp, "fp")
    _validate_callable(fpp, "fpp")
    _validate_real("x0", x0)
    _validate_tol(tol)
    _validate_max_iter(max_iter)
    x = float(x0)
    iterations = 0
    while True:
        fpx = fp(x)
        _validate_finite("fp(x)", fpx)
        if abs(fpx) < tol:
            return x, f(x), iterations
        if iterations >= max_iter:
            raise ValueError(
                "newton 1d minimize did not converge to derivative tolerance %g "
                "within %d iterations" % (tol, max_iter)
            )
        fppx = fpp(x)
        _validate_finite("fpp(x)", fppx)
        if fppx == 0.0:
            raise ValueError(
                "second derivative is zero at x = %g; Newton step is undefined" % x
            )
        x_next = x - fpx / fppx
        _validate_finite("iterate", x_next)
        x = x_next
        iterations += 1
