#!/usr/bin/env python3
"""Fatigue cumulative damage logic, Palmgren-Miner rule (paraphrase,
common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25.571 damage tolerance practice uses
cumulative damage models for fatigue evaluation. The Palmgren-Miner
rule sums the ratio of applied cycles n to cycles to failure N at
each load level; failure is predicted when the accumulated fraction
reaches 1.0. The limit is a project-defined sanity band.
"""


def cumulative_damage(cycles):
    """Palmgren-Miner damage fraction over (n, N) cycle blocks.

    Raises ValueError on an empty list, a non-positive N, or a
    negative n."""
    if not cycles:
        raise ValueError("cycle blocks must not be empty")
    total = 0.0
    for n, n_fail in cycles:
        if n < 0:
            raise ValueError("applied cycles must be >= 0, got %r" % (n,))
        if n_fail <= 0:
            raise ValueError("cycles to failure must be > 0, got %r" % (n_fail,))
        total += n / float(n_fail)
    return total


def damage_ok(damage, limit=1.0):
    """True when cumulative damage is within the life limit."""
    if damage < 0:
        raise ValueError("damage must be >= 0, got %r" % (damage,))
    return damage <= limit


def life_consumed_pct(damage):
    """Percent of fatigue life consumed."""
    if damage < 0:
        raise ValueError("damage must be >= 0, got %r" % (damage,))
    return damage * 100.0
