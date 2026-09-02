#!/usr/bin/env python3
"""Multidisciplinary design optimization logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): MDO couples disciplines through shared coupling variables. A
classic aero-structural example: the aerodynamic discipline sees a
lift coefficient CL = CL_alpha * (alpha_geom - delta), where the
structural deflection index delta reduces the effective angle of
attack, and the structures discipline reacts to the aerodynamic load
with delta = k_def * q * CL, q the dynamic pressure in Pa. Both
equations must hold at once, so the coupled state is the fixed point
CL* = CL_alpha * alpha_geom / (1 + CL_alpha * k_def * q). Fixed-point
iteration CL_{n+1} = CL_alpha * (alpha_geom - k_def * q * CL_n)
converges when the contraction factor r = CL_alpha * k_def * q < 1;
each iteration multiplies the error by r.

The optimizer is a one-dimensional grid search over a design variable
with an exterior penalty for a violated constraint: minimize
f(x) = (x - 2.0)^2 subject to x >= x_min. Infeasible points carry a
large penalty so the returned optimum is feasible. A central-difference
gradient is provided for the sensitivity check.

Units are SI: alpha_geom in degrees (converted internally to rad),
CL_alpha in 1/rad, q in Pa, k_def in 1/Pa, delta in rad. Invalid
inputs raise ValueError throughout.
"""

import math

PENALTY_WEIGHT = 1.0e6  # exterior penalty weight for infeasible points


def aero_structural_fixed_point(
    CL_alpha, alpha_geom_deg, q, k_def, CL_guess=0.5, tol=1.0e-10, max_iter=200
):
    """Converge the aero-structural coupling by fixed-point iteration.

    Iterates CL_{n+1} = CL_alpha * (alpha_geom - k_def * q * CL_n)
    with alpha_geom in degrees, CL_alpha in 1/rad, q in Pa, and k_def
    in 1/Pa until the change in CL is below tol. Returns
    {"CL": value, "delta": value, "iterations": count, "converged":
    True, "contraction_factor": r} with delta in rad. Raises
    RuntimeError when max_iter is exhausted (r >= 1 diverges) and
    ValueError for invalid inputs.
    """
    if CL_alpha <= 0:
        raise ValueError("CL_alpha must be positive, got %r" % (CL_alpha,))
    if alpha_geom_deg <= 0:
        raise ValueError(
            "alpha_geom_deg must be positive, got %r" % (alpha_geom_deg,)
        )
    if q <= 0:
        raise ValueError("dynamic pressure q must be positive, got %r" % (q,))
    if k_def <= 0:
        raise ValueError("deflection factor k_def must be positive, got %r" % (k_def,))
    if CL_guess < 0:
        raise ValueError("CL_guess must be non-negative, got %r" % (CL_guess,))
    if tol <= 0:
        raise ValueError("tolerance tol must be positive, got %r" % (tol,))
    if max_iter < 1:
        raise ValueError("max_iter must be at least 1, got %r" % (max_iter,))

    contraction = CL_alpha * k_def * q
    alpha_geom = math.radians(alpha_geom_deg)
    CL = CL_guess
    for n in range(1, max_iter + 1):
        delta = k_def * q * CL
        CL_new = CL_alpha * (alpha_geom - delta)
        if abs(CL_new - CL) <= tol:
            return {
                "CL": CL_new,
                "delta": delta,
                "iterations": n,
                "converged": True,
                "contraction_factor": contraction,
            }
        CL = CL_new
    raise RuntimeError(
        "fixed-point iteration did not converge in %d iterations "
        "(contraction factor %r must be below 1)" % (max_iter, contraction)
    )


def objective(x):
    """Unimodal test objective f(x) = (x - 2.0)^2, minimum at x = 2.0."""
    return (x - 2.0) ** 2


def constraint_min_x(x, x_min):
    """Feasibility check: the design variable x must be >= x_min."""
    return x >= x_min


def penalized_objective(x, x_min):
    """Objective plus exterior penalty when x violates x >= x_min.

    Returns f(x) + PENALTY_WEIGHT * (x_min - x)^2 for infeasible x and
    f(x) otherwise, so infeasible grid points are never selected.
    """
    base = objective(x)
    if x < x_min:
        return base + PENALTY_WEIGHT * (x_min - x) ** 2
    return base


def grid_search_optimize(lb, ub, step, x_min):
    """Grid-search the penalized objective over one design variable.

    Evaluates penalized_objective on the grid lb, lb + step, ... up to
    ub (inclusive) and returns {"x_opt": value, "f_opt": value,
    "feasible": bool}; the returned point always satisfies x_opt >=
    x_min because infeasible grid points carry the exterior penalty.
    Raises ValueError if lb >= ub or step <= 0.
    """
    if lb >= ub:
        raise ValueError(
            "lower bound lb must be below upper bound ub, got lb=%r ub=%r" % (lb, ub)
        )
    if step <= 0:
        raise ValueError("step must be positive, got %r" % (step,))

    best_x = None
    best_f = None
    n = 0
    while True:
        x = lb + n * step
        if x > ub + 1.0e-12:
            break
        f = penalized_objective(x, x_min)
        if best_f is None or f < best_f:
            best_f = f
            best_x = x
        n += 1
    feasible = best_x is not None and constraint_min_x(best_x, x_min)
    return {"x_opt": best_x, "f_opt": best_f, "feasible": feasible}


def finite_difference_gradient(f, x, h=1.0e-6):
    """Central-difference gradient of f at x (sensitivity check).

    Returns (f(x + h) - f(x - h)) / (2.0 * h). Raises ValueError if
    h is not positive.
    """
    if h <= 0:
        raise ValueError("step h must be positive, got %r" % (h,))
    return (f(x + h) - f(x - h)) / (2.0 * h)
