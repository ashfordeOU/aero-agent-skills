#!/usr/bin/env python3
"""Assembly tolerance stack-up analysis logic (common engineering methodology).

Summary (standards-map.yaml, as9102/as9100: quality context, reference-only):
a linear dimension chain combines signed nominal dimensions into the
assembly nominal dimension, and the part tolerances combine two ways.
The worst case total is the sum of the absolute tolerances; the
statistical total is the root sum square (RSS) of the tolerances,
valid when the parts are independent and centered. The assembly limits
are the nominal plus and minus the chosen tolerance total. The RSS
variance share of part i is 100 * t_i^2 / sum_j(t_j^2), which ranks
the dominant contributor. Units: any consistent length unit (mm, in);
all inputs must share one unit system.
"""

import math


def nominal_total(nominals, directions):
    """Signed sum of the nominal dimensions: sum(n_i * d_i).

    directions[i] is +1 when the part adds to the chain and -1 when it
    subtracts. Raises ValueError on empty lists or length mismatch.
    """
    if not nominals:
        raise ValueError("nominals must be a non-empty list")
    if len(nominals) != len(directions):
        raise ValueError(
            "nominals and directions length mismatch: %d vs %d"
            % (len(nominals), len(directions))
        )
    return sum(n * d for n, d in zip(nominals, directions))


def worst_case_total(tolerances):
    """Worst case stack-up total: the sum of the absolute tolerances."""
    if not tolerances:
        raise ValueError("tolerances must be a non-empty list")
    for t in tolerances:
        if t < 0:
            raise ValueError("tolerance must be >= 0, got %r" % (t,))
    return sum(abs(t) for t in tolerances)


def rss_total(tolerances):
    """Statistical (root sum square) stack-up total: sqrt(sum(t_i**2)).

    Valid when the part variations are independent and centered on the
    nominal; it is always less than or equal to the worst case total.
    """
    if not tolerances:
        raise ValueError("tolerances must be a non-empty list")
    for t in tolerances:
        if t < 0:
            raise ValueError("tolerance must be >= 0, got %r" % (t,))
    return math.sqrt(sum(t * t for t in tolerances))


def stackup_limits(nominal, tolerance_total):
    """Assembly limits (minimum, maximum) = nominal +- tolerance_total."""
    if tolerance_total < 0:
        raise ValueError(
            "tolerance total must be >= 0, got %r" % (tolerance_total,)
        )
    return (nominal - tolerance_total, nominal + tolerance_total)


def rss_shares(tolerances):
    """Percent RSS variance share of each part: 100 * t_i^2 / sum(t_j^2).

    Shares sum to 100; the largest share identifies the dominant
    contributor that tightening would reduce most.
    """
    if not tolerances:
        raise ValueError("tolerances must be a non-empty list")
    for t in tolerances:
        if t < 0:
            raise ValueError("tolerance must be >= 0, got %r" % (t,))
    denom = sum(t * t for t in tolerances)
    if denom == 0:
        raise ValueError("all tolerances are zero; no stack-up spread")
    return [100.0 * (t * t) / denom for t in tolerances]
