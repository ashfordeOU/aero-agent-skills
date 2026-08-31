#!/usr/bin/env python3
"""Spacecraft attitude control sizing logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, ecss: free download):
ECSS-E-ST-60 covers spacecraft control. Momentum-wheel sizing for a
slew is textbook angular momentum: H = I * omega for a spacecraft of
inertia I slewing at rate omega; the wheel must store that momentum
with margin. Detumble and margin thresholds are project-defined
sanity bands.
"""

import math


def slew_momentum_from_deg(inertia, slew_rate_deg_s):
    """Required wheel momentum (N m s) to slew inertia (kg m2) at a
    rate in degrees per second."""
    if inertia <= 0:
        raise ValueError("inertia must be > 0, got %r" % (inertia,))
    if slew_rate_deg_s < 0:
        raise ValueError("slew rate must be >= 0, got %r" % (slew_rate_deg_s,))
    return inertia * math.radians(slew_rate_deg_s)


def detumble_ok(rate_deg_s, allowed_deg_s):
    """True when the current angular rate is within the allowed rate."""
    if rate_deg_s < 0:
        raise ValueError("rate must be >= 0, got %r" % (rate_deg_s,))
    if allowed_deg_s <= 0:
        raise ValueError("allowed rate must be > 0, got %r" % (allowed_deg_s,))
    return rate_deg_s <= allowed_deg_s


def wheel_margin_ok(available, required, margin=0.3):
    """True when available wheel momentum covers required with margin."""
    if available <= 0 or required <= 0:
        raise ValueError("available and required must be > 0")
    return available >= required * (1.0 + margin)
