#!/usr/bin/env python3
"""Spacecraft thermal design logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, ecss: free download):
ECSS-E-ST-31 covers spacecraft thermal control. The radiator sizing
here is the textbook Stefan-Boltzmann balance: a radiator at
temperature T_rad radiating to a sink at T_sink dissipates
Q = eps * sigma * A * (T_rad^4 - T_sink^4). Equilibrium temperature
follows from the same balance solved for temperature. Margin
thresholds are project-defined sanity bands.
"""

SIGMA = 5.67e-8  # W/m2/K4


def radiator_area(heat_load, t_rad, t_sink, eps):
    """Radiator area (m2) for a heat load (W) at radiator temperature
    T_rad (K) radiating to a sink at T_sink (K)."""
    if heat_load < 0:
        raise ValueError("heat load must be >= 0, got %r" % (heat_load,))
    if t_rad <= t_sink:
        raise ValueError("radiator temperature must exceed sink temperature")
    if not (0.0 < eps <= 1.0):
        raise ValueError("emissivity must be in (0, 1], got %r" % (eps,))
    return heat_load / (eps * SIGMA * (t_rad ** 4 - t_sink ** 4))


def equilibrium_temp(heat_load, area, t_sink, eps):
    """Equilibrium radiator temperature (K) for a heat load and area."""
    if heat_load <= 0:
        raise ValueError("heat load must be > 0, got %r" % (heat_load,))
    if area <= 0:
        raise ValueError("area must be > 0, got %r" % (area,))
    if not (0.0 < eps <= 1.0):
        raise ValueError("emissivity must be in (0, 1], got %r" % (eps,))
    return (t_sink ** 4 + heat_load / (eps * SIGMA * area)) ** 0.25


def thermal_margin_ok(available, required, margin=0.1):
    """True when available dissipation covers required with margin."""
    if available <= 0 or required <= 0:
        raise ValueError("available and required must be > 0")
    return available >= required * (1.0 + margin)
