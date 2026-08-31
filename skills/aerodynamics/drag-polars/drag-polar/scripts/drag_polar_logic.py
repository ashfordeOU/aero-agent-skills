#!/usr/bin/env python3
"""Parabolic drag polar logic (common knowledge, dimensionless).

The parabolic drag polar CD = CD0 + k * CL^2 with k = 1 / (pi * e * AR)
models total drag as zero-lift drag plus lift-induced drag. Oswald
span-efficiency e is the ratio of ideal (elliptic loading) induced drag
to the actual induced drag at the same lift and aspect ratio: e = 1 for
elliptic loading, typical wings 0.7 to 0.85. AR is span^2 over area.
All coefficients (CD0, CD, CL, k) are dimensionless. NACA Report 824
(public domain, standards-map.yaml) supplies measured section polars
that a parabolic fit should reproduce within fit tolerance.
"""

import math


def induced_drag_factor(e, ar):
    """Induced drag factor k = 1 / (pi * e * AR).

    Raises ValueError when e is not in (0, 1] or ar is not > 0.
    """
    if e <= 0 or e > 1:
        raise ValueError("Oswald span-efficiency e must be in (0, 1], got %r" % (e,))
    if ar <= 0:
        raise ValueError("aspect ratio must be > 0, got %r" % (ar,))
    return 1.0 / (math.pi * e * ar)


def drag_coefficient(cd0, cl, e, ar):
    """Total drag coefficient CD = CD0 + k * CL^2 at lift CL.

    Raises ValueError when cd0 is not > 0 or the span-efficiency or
    aspect ratio are invalid.
    """
    if cd0 <= 0:
        raise ValueError("zero-lift drag coefficient cd0 must be > 0, got %r" % (cd0,))
    k = induced_drag_factor(e, ar)
    return cd0 + k * cl * cl


def lift_to_drag(cl, cd):
    """Lift to drag ratio at one polar point; raises when cd <= 0."""
    if cd <= 0:
        raise ValueError("drag coefficient must be > 0, got %r" % (cd,))
    return cl / cd


def max_lift_to_drag(cd0, e, ar):
    """Peak of the polar: cl_opt and the maximum lift to drag ratio.

    Returns {'cl_opt', 'ld_max', 'k'}; raises ValueError for cd0 <= 0
    or invalid span-efficiency or aspect ratio.
    """
    if cd0 <= 0:
        raise ValueError("zero-lift drag coefficient cd0 must be > 0, got %r" % (cd0,))
    k = induced_drag_factor(e, ar)
    cl_opt = math.sqrt(cd0 / k)
    ld_max = 1.0 / (2.0 * math.sqrt(cd0 * k))
    return {"cl_opt": cl_opt, "ld_max": ld_max, "k": k}


def fit_parabolic_polar(cl1, cd1, cl2, cd2):
    """Fit the parabolic polar to two measured (cl, cd) points.

    k = (cd2 - cd1) / (cl2^2 - cl1^2), cd0 = cd1 - k * cl1^2.
    Returns {'cd0', 'k'}; raises ValueError when the denominator
    vanishes or the fitted k is not > 0.
    """
    denom = cl2 * cl2 - cl1 * cl1
    if denom == 0:
        raise ValueError(
            "fit points must differ in cl squared (cl1=%r, cl2=%r)" % (cl1, cl2)
        )
    k = (cd2 - cd1) / denom
    if k <= 0:
        raise ValueError("fitted k must be > 0, got %r" % (k,))
    cd0 = cd1 - k * cl1 * cl1
    return {"cd0": cd0, "k": k}
