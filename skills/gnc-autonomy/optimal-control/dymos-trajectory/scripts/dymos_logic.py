#!/usr/bin/env python3
"""Dymos trajectory optimization logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, arp4754a: gated,
reference-only): ARP4754A frames development assurance for aircraft
systems; Dymos is an open-source optimal-control tool that transcribes
trajectory problems with pseudospectral collocation into phases. A
usable phase needs enough collocation nodes (5 or more in this
contract), initial- and final-state bounds, and an objective; solved
trajectories are checked for convergence, state continuity across
segment boundaries, and total delta-v against expected budgets.
"""


def _is_bool(x):
    return isinstance(x, bool)


def phase_setup_ok(nodes, has_initial_state_bounds, has_final_bounds, has_objective):
    """Check a Dymos phase definition is complete.

    Returns (ok, reasons): ok is False with a reasons list when the
    collocation node count is below the minimum (5) or any required
    bound/objective flag is missing; (True, []) when complete.
    """
    if not isinstance(nodes, (int, float)) or isinstance(nodes, bool):
        raise ValueError("nodes must be numeric, got %r" % (nodes,))
    flags = (has_initial_state_bounds, has_final_bounds, has_objective)
    if not all(_is_bool(f) for f in flags):
        raise ValueError("bound/objective flags must be booleans, got %r" % (flags,))
    reasons = []
    if nodes < 5:
        reasons.append("fewer than 5 collocation nodes (minimum 5)")
    if not has_initial_state_bounds:
        reasons.append("missing initial-state bounds")
    if not has_final_bounds:
        reasons.append("missing final-state bounds")
    if not has_objective:
        reasons.append("missing objective")
    return (len(reasons) == 0, reasons)


def convergence_check(iterations, tol, max_iter=50, tol_limit=1e-4):
    """Check optimizer convergence: iterations within max_iter and
    tolerance within tol_limit.

    Returns {"converged": bool, "reason": str}.
    """
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 0:
        raise ValueError("iterations must be a non-negative int, got %r" % (iterations,))
    if not isinstance(tol, (int, float)) or isinstance(tol, bool) or tol < 0:
        raise ValueError("tol must be a non-negative number, got %r" % (tol,))
    if iterations <= max_iter and tol <= tol_limit:
        return {
            "converged": True,
            "reason": "converged within iteration and tolerance limits",
        }
    reasons = []
    if iterations > max_iter:
        reasons.append("iterations %d exceed max_iter %d" % (iterations, max_iter))
    if tol > tol_limit:
        reasons.append("tol %g exceeds tol_limit %g" % (tol, tol_limit))
    return {"converged": False, "reason": "; ".join(reasons)}


def state_continuity_ok(segment_ends_equal):
    """True when adjacent segment endpoint states match (continuity);
    non-bool input raises ValueError."""
    if not _is_bool(segment_ends_equal):
        raise ValueError(
            "segment_ends_equal must be a bool, got %r" % (segment_ends_equal,)
        )
    return segment_ends_equal


def trajectory_delta_v_sanity(dv_mps, expected_mps, tol=0.10):
    """True when the trajectory total delta-v is within tol (fraction)
    of the expected budget."""
    if expected_mps <= 0:
        raise ValueError("expected delta-v must be > 0, got %r" % (expected_mps,))
    return abs(dv_mps - expected_mps) / expected_mps <= tol
