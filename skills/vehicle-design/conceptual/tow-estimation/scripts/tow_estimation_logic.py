#!/usr/bin/env python3
"""Conceptual takeoff gross weight estimation logic (paraphrase,
common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): conceptual sizing iterates the takeoff gross
weight from a fuel-fraction method: W0 = payload / (1 - empty
fraction - fuel fraction), where the empty and fuel fractions are
class-based estimates. The iteration converges when successive
estimates change by less than a tolerance. Thresholds are
project-defined sanity bands.
"""


def tow_estimate(payload, empty_fraction, fuel_fraction):
    """Takeoff gross weight (kg) from payload and class fractions."""
    if payload <= 0:
        raise ValueError("payload must be > 0, got %r" % (payload,))
    if empty_fraction < 0 or fuel_fraction < 0:
        raise ValueError("fractions must be >= 0")
    remaining = 1.0 - empty_fraction - fuel_fraction
    if remaining <= 0:
        raise ValueError("empty + fuel fraction must be < 1")
    return payload / remaining


def tow_converged(series, tol):
    """True when the last two TOW estimates differ by less than tol."""
    if len(series) < 2:
        raise ValueError("series must have at least two estimates")
    if any(v <= 0 for v in series):
        raise ValueError("estimates must be > 0")
    return abs(series[-1] - series[-2]) < tol


def weight_breakdown_ok(empty, fuel, payload, total, tol=0.01):
    """True when empty + fuel + payload balances total within tol."""
    if empty < 0 or fuel < 0 or payload < 0:
        raise ValueError("breakdown terms must be >= 0")
    if total <= 0:
        raise ValueError("total must be > 0")
    return abs((empty + fuel + payload) - total) <= tol * total
