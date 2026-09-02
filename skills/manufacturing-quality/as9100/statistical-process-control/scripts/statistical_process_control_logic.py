#!/usr/bin/env python3
"""Statistical process control (SPC) math for aerospace manufacturing.

Deterministic, offline, stdlib-only helpers for variable control
charts and process capability: X-bar and R chart control limits from
subgroup data, the process standard deviation estimate from the
average range, the Cp and Cpk capability indices against the
specification limits, and the Western Electric out-of-control rules.

The chart constants A2, D3, D4, and d2 for subgroup sizes 2 through
10 are common published SPC constants (summary values, not reproduced
tables from any standard; per standards-map.yaml as9100 is
reference-only).

Contract exercised by scripts/test_statistical_process_control.py.
"""

import math

# Standard SPC control chart constants for subgroup sizes 2..10.
# A2 scales the X-bar chart limits, D3 and D4 scale the R chart
# limits, d2 converts the average range to the process sigma.
A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577,
      6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
D3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
      6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114,
      6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
      6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}


def _check_n(n):
    """Return int(n) when n is an integer in 2..10, else raise ValueError."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("subgroup size must be an integer, got %r" % (n,))
    if n not in A2:
        raise ValueError(
            "subgroup size %d outside the supported range 2..10" % n
        )
    return n


def xbar_r_limits(xbar, rbar, n):
    """Return (xbar_ucl, xbar_lcl, r_ucl, r_lcl) for X-bar and R charts.

    X-bar limits: UCL = xbar + A2 * rbar, LCL = xbar - A2 * rbar.
    R limits: UCL = D4 * rbar, LCL = D3 * rbar.

    Raises ValueError for a negative average range or a subgroup size
    outside 2..10.
    """
    n = _check_n(n)
    if rbar < 0:
        raise ValueError("average range must be >= 0, got %r" % (rbar,))
    return (xbar + A2[n] * rbar, xbar - A2[n] * rbar,
            D4[n] * rbar, D3[n] * rbar)


def process_sigma(rbar, n):
    """Estimate the process standard deviation from the average range.

    sigma = rbar / d2. The range-based estimate is the standard SPC
    approach for small subgroups (n = 2..10).

    Raises ValueError for a negative average range or an unsupported
    subgroup size.
    """
    n = _check_n(n)
    if rbar < 0:
        raise ValueError("average range must be >= 0, got %r" % (rbar,))
    return rbar / D2[n]


def capability_indices(usl, lsl, xbar, sigma):
    """Return (cp, cpu, cpl, cpk) against the specification limits.

    Cp = (USL - LSL) / (6 * sigma), CPU = (USL - xbar) / (3 * sigma),
    CPL = (xbar - LSL) / (3 * sigma), Cpk = min(CPU, CPL).

    Raises ValueError when USL does not exceed LSL or sigma is not
    positive.
    """
    if usl <= lsl:
        raise ValueError(
            "USL must exceed LSL, got USL %r LSL %r" % (usl, lsl)
        )
    if sigma <= 0:
        raise ValueError("sigma must be > 0, got %r" % (sigma,))
    cp = (usl - lsl) / (6.0 * sigma)
    cpu = (usl - xbar) / (3.0 * sigma)
    cpl = (xbar - lsl) / (3.0 * sigma)
    return (cp, cpu, cpl, min(cpu, cpl))


def out_of_control_rules(points, centerline, sigma):
    """Return the names of the Western Electric rules the points violate.

    Rule 1: one point beyond 3 sigma of the centerline.
    Rule 2: eight consecutive points on the same side of the
    centerline.
    Rule 3: two of three consecutive points beyond 2 sigma on the
    same side of the centerline.
    Rule 4: four of five consecutive points beyond 1 sigma on the
    same side of the centerline.

    Returns a list of rule names in ascending rule order, empty when
    the process is in control. Raises ValueError for a non-positive
    sigma or fewer than two points.
    """
    if len(points) < 2:
        raise ValueError(
            "at least two points required for rule detection, got %d" % len(points)
        )
    if sigma <= 0:
        raise ValueError("sigma must be > 0, got %r" % (sigma,))
    violated = []

    # Rule 1: any point beyond 3 sigma.
    for p in points:
        if abs(p - centerline) > 3.0 * sigma:
            violated.append("rule1")
            break

    # Rule 2: run of eight consecutive points on one side.
    run = 0
    for p in points:
        if p > centerline:
            run = run + 1 if run > 0 else 1
        elif p < centerline:
            run = run - 1 if run < 0 else -1
        else:
            run = 0
        if abs(run) >= 8:
            violated.append("rule2")
            break

    # Rule 3: two of three consecutive points beyond 2 sigma, same side.
    for i in range(len(points) - 2):
        window = points[i:i + 3]
        above = sum(1 for p in window if p - centerline > 2.0 * sigma)
        below = sum(1 for p in window if centerline - p > 2.0 * sigma)
        if above >= 2 or below >= 2:
            violated.append("rule3")
            break

    # Rule 4: four of five consecutive points beyond 1 sigma, same side.
    for i in range(len(points) - 4):
        window = points[i:i + 5]
        above = sum(1 for p in window if p - centerline > 1.0 * sigma)
        below = sum(1 for p in window if centerline - p > 1.0 * sigma)
        if above >= 4 or below >= 4:
            violated.append("rule4")
            break

    return violated
