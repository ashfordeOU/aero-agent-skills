#!/usr/bin/env python3
"""Stress-life (S-N) fatigue analysis (stdlib only).

Builds and applies the Basquin S-N curve:

    S = A * N**b

with stress amplitude S, cycles to failure N, fatigue strength
coefficient A (the stress amplitude at N = 1 cycle), and fatigue
strength exponent b (negative for metals, typically -0.05 to -0.15).

Worked anchors for A = 1000 MPa, b = -0.1:

    S(1e4)  = 1000 * 1e4**-0.1  = 398.1 MPa
    S(1e5)  = 1000 * 1e5**-0.1  = 316.2 MPa
    S(1e6)  = 1000 * 1e6**-0.1  = 251.2 MPa
    S(1e7)  = 1000 * 1e7**-0.1  = 199.5 MPa   (runout level)

    N(300)  = (300 / 1000)**(1 / -0.1) = 1.6935e5 cycles
    Se(1e7) = 1000 * 1e7**-0.1 = 199.5 MPa  (endurance limit at a
             1e7-cycle runout threshold)

The log-log fit uses linear regression of log S on log N:

    log S = log A + b * log N

Generic mechanical engineering methodology; FAR-25 / CS-25 / MMPDS
are cited reference-only in the skill, nothing here quotes any of
them.

Conventions: all stresses share one unit (MPa or ksi); N is in
cycles. The exponent b is the slope of the line in log-log space and
is negative for metals; the parameterization S = A * N**b differs
from the equivalent life form N = C * S**-m used by some references.
"""

import math


def basquin_stress(A, b, N):
    """Stress amplitude S = A * N**b at the given life N.

    Worked anchor: A = 1000, b = -0.1, N = 1e5 gives
    S = 1000 * 1e5**-0.1 = 316.2 MPa.
    """
    if not A > 0.0:
        raise ValueError("A must be positive, got %r" % (A,))
    if not N > 0.0:
        raise ValueError("N must be positive, got %r" % (N,))
    return A * N ** b


def basquin_life(A, b, S):
    """Cycles to failure N = (S / A)**(1 / b) at stress amplitude S.

    Life prediction for a given stress amplitude. Worked anchor:
    A = 1000, b = -0.1, S = 300 gives N = 0.3**-10 = 1.6935e5.
    """
    if not A > 0.0:
        raise ValueError("A must be positive, got %r" % (A,))
    if not S > 0.0:
        raise ValueError("S must be positive, got %r" % (S,))
    if b == 0.0:
        raise ValueError("b must be nonzero (a horizontal S-N line has no finite life)")
    life = (S / A) ** (1.0 / b)
    if not life > 0.0:
        raise ValueError(
            "life is not positive for A=%r, b=%r, S=%r" % (A, b, S)
        )
    return life


def fit_basquin(points):
    """Fit S = A * N**b to (N, S) fatigue test points.

    Least squares on the log-log form log S = log A + b * log N.
    Returns (A, b). Requires at least 2 points with N > 0 and S > 0.
    Worked anchor: the three exact points (1e3, 501.2), (1e4, 398.1),
    (1e5, 316.2) on A = 1000, b = -0.1 recover A ~ 1000 and
    b ~ -0.1.
    """
    if len(points) < 2:
        raise ValueError(
            "at least 2 (N, S) points required, got %d" % len(points)
        )
    xs = []
    ys = []
    for i, (n, s) in enumerate(points):
        if not n > 0.0:
            raise ValueError("point %d: N must be positive, got %r" % (i, n))
        if not s > 0.0:
            raise ValueError("point %d: S must be positive, got %r" % (i, s))
        xs.append(math.log(n))
        ys.append(math.log(s))
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0.0:
        raise ValueError("all N identical; cannot fit a slope")
    b = cov / var
    a_log = my - b * mx
    return math.exp(a_log), b


def endurance_limit(A, b, runout_cycles):
    """Endurance limit Se = A * runout_cycles**b at the runout
    threshold, the stress amplitude the material survives for the
    runout life.

    Worked anchor: A = 1000, b = -0.1, runout_cycles = 1e7 gives
    Se = 1000 * 1e7**-0.1 = 199.5 MPa.
    """
    if not runout_cycles > 0.0:
        raise ValueError(
            "runout_cycles must be positive, got %r" % (runout_cycles,)
        )
    return basquin_stress(A, b, runout_cycles)


def runout_stress_level(points, runout_cycles):
    """Highest tested stress amplitude whose recorded life reached the
    runout threshold (N >= runout_cycles).

    Read directly off the test data, independent of any fitted curve.
    Raises ValueError when no test point reached runout: the data set
    then defines no endurance limit at that threshold.
    """
    if not runout_cycles > 0.0:
        raise ValueError(
            "runout_cycles must be positive, got %r" % (runout_cycles,)
        )
    best = None
    for i, (n, s) in enumerate(points):
        if not n > 0.0:
            raise ValueError("point %d: N must be positive, got %r" % (i, n))
        if not s > 0.0:
            raise ValueError("point %d: S must be positive, got %r" % (i, s))
        if n >= runout_cycles and (best is None or s > best):
            best = s
    if best is None:
        raise ValueError(
            "no test point reached runout at %r cycles" % (runout_cycles,)
        )
    return best
