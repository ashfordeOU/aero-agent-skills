#!/usr/bin/env python3
"""CalculiX linear static FEA post-processing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25: gated false):
Linear static finite element analysis with CalculiX (ccx) produces
element/node stresses that are compared against material allowables.
Margin of safety is MS = allowable/actual - 1.0 (negative = failed
structure at the applied load). Von Mises equivalent stress is the
standard scalar comparison for ductile metals. FAR-25 sets the loads
and structural-proof context (25.301-25.307); this module computes
the margin and unit-discipline checks, not the loads.
"""

import math

STRESS_UNITS_PA = {
    "Pa": 1.0,
    "kPa": 1e3,
    "MPa": 1e6,
    "GPa": 1e9,
    "psi": 6894.757,
    "ksi": 6894757.0,
}


def margin_of_safety(allowable, actual):
    """Margin of safety: MS = allowable/actual - 1.0.

    Negative margin means the applied stress exceeds the allowable.
    Both inputs must be positive; invalid input raises ValueError.
    """
    if allowable <= 0:
        raise ValueError("allowable must be positive: %r" % (allowable,))
    if actual <= 0:
        raise ValueError("actual must be positive: %r" % (actual,))
    return allowable / actual - 1.0


def mos_status(ms, min_ms=0.0):
    """Classify a margin of safety: 'pass' if ms >= min_ms else 'fail'.

    A negative margin of safety means the structure fails at the
    applied load.
    """
    return "pass" if ms >= min_ms else "fail"


def stress_to_pa(value, unit):
    """Convert a stress value to Pa; raises ValueError on unknown unit."""
    if unit not in STRESS_UNITS_PA:
        raise ValueError("unknown stress unit: %r" % (unit,))
    return value * STRESS_UNITS_PA[unit]


def mos_units_discipline(allowable, actual, unit_allowable, unit_actual):
    """Margin of safety with both stresses converted to Pa first.

    Forces unit discipline: allowables and FEA stresses are compared
    in consistent units, never silently in mismatched ones. Unknown
    units raise ValueError.
    """
    return margin_of_safety(
        stress_to_pa(allowable, unit_allowable),
        stress_to_pa(actual, unit_actual),
    )


def von_mises(s1, s2, s3):
    """Von Mises equivalent stress from the three principal stresses:
    sqrt(0.5*((s1-s2)^2 + (s2-s3)^2 + (s3-s1)^2))."""
    return math.sqrt(0.5 * ((s1 - s2) ** 2 + (s2 - s3) ** 2 + (s3 - s1) ** 2))
