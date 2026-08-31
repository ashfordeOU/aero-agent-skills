#!/usr/bin/env python3
"""Nonlinear 1D bar equilibrium solved by Newton-Raphson iteration (stdlib only).

Paraphrase of the standard nonlinear finite element methodology that a
nonlinear CalculiX (ccx) static run applies when the linear assumption
breaks: the stiffness of the structure depends on its own state. The
scalar model is a bar whose axial stiffness grows with displacement,
k(u) = k0 * (1 + alpha * u). The equilibrium residual is
r(u) = k(u) * u - F = k0 * (u + alpha * u**2) - F and the tangent
stiffness is kt(u) = dr/du = k0 * (1 + 2 * alpha * u). Newton-Raphson
iteration updates u_{n+1} = u_n - r(u_n) / kt(u_n) until
abs(r) <= tolerance (converged) or the iteration budget is spent
(not converged). The total load may be applied in load_steps equal
increments, each increment iterating from the previous converged
state, which mirrors the load stepping of a nonlinear run.

Geometric nonlinearity (large displacement) and material nonlinearity
(plasticity) both appear as a state-dependent stiffness; the
convergence verdict compares the final residual norm against the
convergence tolerance.

Units: u in any length unit, F in any force unit, k0 in force per
length, alpha in 1 per length; tolerance inherits the units of F.
"""

import math


def residual(u, load, k0, alpha):
    """Equilibrium residual r(u) = k0 * (u + alpha * u**2) - load.

    The internal force k(u) * u minus the applied load; zero at
    equilibrium.
    """
    return k0 * (u + alpha * u ** 2) - load


def tangent_stiffness(u, k0, alpha):
    """Tangent stiffness kt(u) = dr/du = k0 * (1 + 2 * alpha * u).

    The slope of the residual curve; Newton-Raphson divides the
    residual by this value at every iteration.
    """
    return k0 * (1.0 + 2.0 * alpha * u)


def analytic_root(load, k0, alpha):
    """Closed-form equilibrium displacement solving k(u) * u = load.

    u + alpha * u**2 = load / k0 gives the positive root
    u = (-1 + sqrt(1 + 4 * alpha * load / k0)) / (2 * alpha) for
    alpha != 0, and u = load / k0 for the linear bar (alpha == 0).
    """
    if alpha == 0.0:
        return load / k0
    disc = 1.0 + 4.0 * alpha * load / k0
    if disc < 0.0:
        raise ValueError(
            "no real root: 1 + 4*alpha*load/k0 = %r is negative" % (disc,)
        )
    return (-1.0 + math.sqrt(disc)) / (2.0 * alpha)


def _validate(k0, alpha, tolerance, load_steps):
    """Raise ValueError on nonsensical solver inputs."""
    if k0 <= 0.0:
        raise ValueError("k0 must be positive: got %r" % (k0,))
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive: got %r" % (tolerance,))
    if load_steps < 1:
        raise ValueError("load_steps must be >= 1: got %r" % (load_steps,))
    if alpha < 0.0:
        raise ValueError("alpha must be non-negative: got %r" % (alpha,))


def _solve_increment(load_inc, k0, alpha, u_start, tolerance, max_iter):
    """One load increment: Newton-Raphson from u_start to equilibrium.

    Returns (u, iterations, residual_norm) where iterations counts the
    Newton updates performed inside this increment. A zero tangent
    stiffness aborts the increment (the update would divide by zero).
    """
    u = u_start
    iterations = 0
    for _ in range(max_iter):
        r = residual(u, load_inc, k0, alpha)
        if abs(r) <= tolerance:
            return u, iterations, abs(r)
        kt = tangent_stiffness(u, k0, alpha)
        if kt == 0.0:
            return u, iterations, abs(r)
        u = u - r / kt
        iterations += 1
    return u, iterations, abs(residual(u, load_inc, k0, alpha))


def newton_raphson(load, k0, alpha, u0=0.0, tolerance=1e-8,
                   max_iter=50, load_steps=1):
    """Solve k(u) * u = load by Newton-Raphson with load stepping.

    The total load is split into load_steps equal increments; each
    increment runs Newton-Raphson to equilibrium starting from the
    previous converged state, exactly as a nonlinear ccx run ramps the
    load. Returns a dict:

      displacement: converged displacement u
      iterations: total Newton updates across all increments
      residual_norm: abs(r(u)) at the final state
      converged: bool, residual_norm <= tolerance at the final state
      verdict: "converged" or "not-converged"
      load_steps: number of increments used
    """
    _validate(k0, alpha, tolerance, load_steps)
    u = u0
    total_iterations = 0
    r_norm = 0.0
    load_inc = load / load_steps
    applied = 0.0
    for _ in range(load_steps):
        applied += load_inc
        u, used, r_norm = _solve_increment(
            applied, k0, alpha, u, tolerance, max_iter
        )
        total_iterations += used
    converged = r_norm <= tolerance
    return {
        "displacement": u,
        "iterations": total_iterations,
        "residual_norm": r_norm,
        "converged": converged,
        "verdict": "converged" if converged else "not-converged",
        "load_steps": load_steps,
    }
