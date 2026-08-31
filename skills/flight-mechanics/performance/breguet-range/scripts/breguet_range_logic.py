#!/usr/bin/env python3
"""Breguet cruise range performance logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the Breguet range equation estimates still-air
cruise range from speed, thrust specific fuel consumption, lift to
drag ratio, and the initial and final masses:
R = (V / (TSFC * g0)) * (L/D) * ln(m0 / m1), with g0 = 9.80665
m/s^2. Units: speed in m/s, TSFC in kg/(N s), masses in kg, range
in meters, cruise time in seconds.
"""

import math


def breguet_range(v_ms, tsfc_kg_per_n_s, ld, m0_kg, m1_kg, g0=9.80665):
    """Breguet still-air cruise range in meters.

    Raises ValueError on non-positive speed, TSFC, lift-to-drag, or
    masses, and on m1 >= m0 (no fuel burned, undefined ratio).
    """
    if v_ms <= 0:
        raise ValueError("speed must be > 0 m/s, got %r" % (v_ms,))
    if tsfc_kg_per_n_s <= 0:
        raise ValueError("TSFC must be > 0 kg/(N s), got %r" % (tsfc_kg_per_n_s,))
    if ld <= 0:
        raise ValueError("lift to drag ratio must be > 0, got %r" % (ld,))
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0 kg, got %r" % (m0_kg,))
    if m1_kg <= 0:
        raise ValueError("final mass must be > 0 kg, got %r" % (m1_kg,))
    if m1_kg >= m0_kg:
        raise ValueError("final mass must be < initial mass, got m1 %r >= m0 %r" % (m1_kg, m0_kg))
    return (v_ms / (tsfc_kg_per_n_s * g0)) * ld * math.log(m0_kg / m1_kg)


def cruise_time(range_m, v_ms):
    """Cruise time in seconds for a range at constant speed."""
    if range_m < 0:
        raise ValueError("range must be >= 0 m, got %r" % (range_m,))
    if v_ms <= 0:
        raise ValueError("speed must be > 0 m/s, got %r" % (v_ms,))
    return range_m / v_ms


def final_mass(m0_kg, fuel_fraction):
    """Mass after burning the given fuel fraction: m0 * (1 - f)."""
    if m0_kg <= 0:
        raise ValueError("initial mass must be > 0 kg, got %r" % (m0_kg,))
    if fuel_fraction < 0:
        raise ValueError("fuel fraction must be >= 0, got %r" % (fuel_fraction,))
    if fuel_fraction >= 1.0:
        raise ValueError("fuel fraction must be < 1.0, got %r" % (fuel_fraction,))
    return m0_kg * (1.0 - fuel_fraction)
