#!/usr/bin/env python3
"""CFD convergence practice logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain validation anchor): computational fluid dynamics runs are
judged converged when residuals drop below a tolerance and stay
decreasing, when the Courant number respects the stability limit of
the scheme, and when mesh refinement changes the answer by less
than a threshold. Thresholds here are project-defined sanity bands.
"""


def residual_converged(history, tol, window=3):
    """True when the last `window` residuals are below tol and the
    latest is the smallest (monotone decrease over the window)."""
    if len(history) < window:
        raise ValueError("residual history too short")
    tail = history[-window:]
    if any(r < 0 for r in tail):
        raise ValueError("residuals must be >= 0")
    monotone = all(tail[i] > tail[i + 1] for i in range(len(tail) - 1))
    return tail[-1] < tol and monotone


def cfl_ok(cfl, explicit=True):
    """True when the Courant number is within the scheme stability
    limit (explicit: 1, implicit: 2, project-defined bands)."""
    if cfl <= 0:
        raise ValueError("CFL must be > 0, got %r" % (cfl,))
    limit = 1.0 if explicit else 2.0
    return cfl <= limit


def mesh_refinement_ok(relative_change, threshold):
    """True when the relative change between mesh levels is below the
    convergence threshold."""
    if relative_change < 0:
        raise ValueError("relative change must be >= 0")
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    return relative_change < threshold
