#!/usr/bin/env python3
"""Grid convergence verification logic (Richardson extrapolation + GCI).

Paraphrase of the standard discretization error estimation
procedure. NACA Report 824 is the pack's public-domain anchor
(standards-map.yaml); convergence verification is generic numerical
methodology, not RTCA or SAE content.

Conventions: f1 finest solution, f2 medium, f3 coarse, refinement
ratio r = h_coarse / h_fine > 1, safety factor Fs = 1.25 for
three-grid studies. The observed order is
p = ln((f3-f2)/(f2-f1)) / ln(r), valid only for a monotone sequence
(ratio (f3-f2)/(f2-f1) > 0). Richardson extrapolation gives
f_exact = f1 + (f1 - f2) / (r**p - 1) and the grid convergence index
is gci = Fs * abs((f1 - f2) / f1) / (r**p - 1).

convergence_verdict classifies from ratio (f3-f2)/(f2-f1): monotone
converged when ratio > 0, oscillatory when ratio < 0, diverging when
abs(ratio) > 1 (diverging takes precedence on the negative branch,
ratio < -1). For non-monotone sequences the observed order is not a
real number, so order, extrapolated, and gci are None.

Units: f1, f2, f3 in any consistent solution units; r, p, and gci
are dimensionless; gci is a fraction, not a percentage.
"""

import math


def observed_order(f1, f2, f3, r):
    """Observed order of accuracy p = ln((f3-f2)/(f2-f1)) / ln(r).

    Raises ValueError when r <= 1, when f2 == f1 (degenerate, the
    ratio is undefined), or when the ratio (f3-f2)/(f2-f1) <= 0
    (non-monotone sequence).
    """
    if r <= 1.0:
        raise ValueError("refinement ratio must be > 1: got r=%r" % (r,))
    diff = f2 - f1
    if diff == 0.0:
        raise ValueError(
            "degenerate: f2 == f1 (%r), ratio undefined" % (f1,)
        )
    ratio = (f3 - f2) / diff
    if ratio <= 0.0:
        raise ValueError(
            "non-monotone sequence: ratio (f3-f2)/(f2-f1) = %r <= 0"
            % (ratio,)
        )
    return math.log(ratio) / math.log(r)


def richardson_extrapolation(f1, f2, r, p):
    """Richardson extrapolated exact solution.

    f_exact = f1 + (f1 - f2) / (r**p - 1). The denominator is zero
    when p == 0 (r**p == 1); callers check the observed order before
    trusting the value.
    """
    return f1 + (f1 - f2) / (r ** p - 1.0)


def grid_convergence_index(f1, f2, r, p, fs=1.25):
    """Grid convergence index, as a fraction (not a percentage).

    gci = fs * abs((f1 - f2) / f1) / (r**p - 1). fs defaults to 1.25
    for three-grid studies (2.0 for two-grid studies).
    """
    return fs * abs((f1 - f2) / f1) / (r ** p - 1.0)


def convergence_verdict(f1, f2, f3, r):
    """Classify the three-solution grid study.

    Returns a dict with 'order', 'extrapolated', 'gci', and
    'verdict'. Verdict from ratio (f3-f2)/(f2-f1): 'monotone
    converged' when ratio > 0, 'oscillatory' when ratio < 0,
    'diverging' when abs(ratio) > 1, with diverging taking
    precedence over oscillatory on the negative branch (ratio < -1).
    A flat ratio of zero (f3 == f2) is treated as oscillatory. For
    non-monotone sequences (ratio <= 0) the observed order is not a
    real number: order, extrapolated, and gci are None. Raises
    ValueError when r <= 1 or f2 == f1.
    """
    if r <= 1.0:
        raise ValueError("refinement ratio must be > 1: got r=%r" % (r,))
    diff = f2 - f1
    if diff == 0.0:
        raise ValueError(
            "degenerate: f2 == f1 (%r), ratio undefined" % (f1,)
        )
    ratio = (f3 - f2) / diff
    if ratio > 0.0:
        p = math.log(ratio) / math.log(r)
        denom = r ** p - 1.0
        if abs(denom) < 1e-12:
            return {
                "order": p,
                "extrapolated": None,
                "gci": None,
                "verdict": "monotone converged",
            }
        f_exact = f1 + (f1 - f2) / denom
        gci = 1.25 * abs((f1 - f2) / f1) / denom
        return {
            "order": p,
            "extrapolated": f_exact,
            "gci": gci,
            "verdict": "monotone converged",
        }
    if ratio < 0.0:
        verdict = "diverging" if abs(ratio) > 1.0 else "oscillatory"
    else:  # ratio == 0.0: f3 == f2, flat non-monotone
        verdict = "oscillatory"
    return {"order": None, "extrapolated": None, "gci": None, "verdict": verdict}
