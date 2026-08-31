#!/usr/bin/env python3
"""Climb performance from excess power (fixed-wing), SI units.

Contract: docs/harness-contract.md gate 3 - rate of climb from
excess power, climb gradient, time to climb at average rate of
climb, and service ceiling where the rate of climb decays to
0.5 m/s (100 ft/min). All functions raise ValueError on invalid
inputs. Units are SI throughout: thrust T, drag D, and weight W in
newtons (N), speed V in m/s, rate of climb in m/s, altitude
delta_h in meters (m), time in seconds (s), gradient dimensionless
(radians, percent = radians * 100).
"""


def rate_of_climb(T, D, V, W):
    """Rate of climb from excess power.

    ROC = (T - D) * V / W in m/s, where (T - D) * V is the excess
    power in watts.
    Units: T, D, W in N; V in m/s; ROC in m/s.
    Raises ValueError if W <= 0, V <= 0, or T - D < 0 (no climb).
    """
    if W <= 0:
        raise ValueError("weight W must be positive (N)")
    if V <= 0:
        raise ValueError("speed V must be positive (m/s)")
    if T - D < 0:
        raise ValueError("no climb: thrust T must exceed drag D (no excess power)")
    return (T - D) * V / W


def climb_gradient(T, D, W):
    """Climb gradient from excess thrust.

    gamma = (T - D) / W, dimensionless. Returns a dict with keys
    radians and percent, where percent = radians * 100.
    Units: T, D, W in N; gamma in radians (percent is dimensionless).
    Raises ValueError if W <= 0 or T - D < 0 (no climb).
    """
    if W <= 0:
        raise ValueError("weight W must be positive (N)")
    if T - D < 0:
        raise ValueError("no climb: thrust T must exceed drag D (no excess thrust)")
    radians = (T - D) / W
    return {"radians": radians, "percent": radians * 100}


def time_to_climb(delta_h, roc_a, roc_b):
    """Time to climb between two altitudes at the average rate of climb.

    t = delta_h / ((roc_a + roc_b) / 2) in seconds, using the mean
    of the rate of climb at the lower and upper altitudes.
    Units: delta_h in m; roc_a, roc_b in m/s; t in s.
    Raises ValueError if delta_h <= 0, or if either endpoint rate of
    climb is <= 0 (a zero ROC endpoint makes the average method
    degenerate: the aircraft is not climbing at that altitude).
    """
    if delta_h <= 0:
        raise ValueError("altitude gain delta_h must be positive (m)")
    if roc_a <= 0 or roc_b <= 0:
        raise ValueError("rate of climb at each altitude must be positive (m/s)")
    avg_roc = (roc_a + roc_b) / 2.0
    return delta_h / avg_roc


def service_ceiling(roc_sea_level, lapse_rate):
    """Service ceiling: altitude where ROC decays to 0.5 m/s (100 ft/min).

    h = (roc_sea_level - 0.5) / lapse_rate in m, assuming a linear
    decay of the rate of climb with altitude (constant ROC lapse
    rate).
    Units: roc_sea_level in m/s; lapse_rate in (m/s) per m; h in m.
    Raises ValueError if roc_sea_level <= 0.5 or lapse_rate <= 0.
    """
    if roc_sea_level <= 0.5:
        raise ValueError("sea-level rate of climb must exceed 0.5 m/s")
    if lapse_rate <= 0:
        raise ValueError("ROC lapse rate must be positive ((m/s) per m)")
    return (roc_sea_level - 0.5) / lapse_rate
