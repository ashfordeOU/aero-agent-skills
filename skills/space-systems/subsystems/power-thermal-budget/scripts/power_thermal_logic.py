#!/usr/bin/env python3
"""Spacecraft power / thermal budget logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
ECSS-E-ST-20C (electrical and electronic) and ECSS-E-ST-10C
(systems engineering) form the European baseline for spacecraft
power budgets. During eclipse the spacecraft runs on battery:
required capacity = eclipse power * eclipse duration / (depth of
discharge * efficiency). The solar array must cover day-side
demand plus margin while generating only in daylight. Invalid
inputs raise ValueError throughout.
"""


def eclipse_fraction(orbit_period_min, eclipse_min):
    """Fraction of the orbit spent in eclipse: eclipse_min / orbit_period_min.

    Raises ValueError if the orbit period is not positive or the
    eclipse is not strictly between zero and the orbit period.
    """
    if orbit_period_min <= 0:
        raise ValueError("orbit period must be positive: %r" % (orbit_period_min,))
    if not (0.0 < eclipse_min < orbit_period_min):
        raise ValueError(
            "eclipse must satisfy 0 < eclipse < orbit period: %r vs %r"
            % (eclipse_min, orbit_period_min)
        )
    return eclipse_min / orbit_period_min


def battery_capacity_required(power_w, eclipse_min, dod, efficiency=0.9):
    """Battery capacity in Wh for eclipse survival:
    C = power_w * (eclipse_min/60.0) / (dod * efficiency)."""
    if power_w <= 0:
        raise ValueError("power must be positive: %r" % (power_w,))
    if eclipse_min <= 0:
        raise ValueError("eclipse duration must be positive: %r" % (eclipse_min,))
    if not (0.0 < dod <= 1.0):
        raise ValueError("depth of discharge must be in (0, 1]: %r" % (dod,))
    if not (0.0 < efficiency <= 1.0):
        raise ValueError("efficiency must be in (0, 1]: %r" % (efficiency,))
    return power_w * (eclipse_min / 60.0) / (dod * efficiency)


def battery_capacity_ok(required_wh, sized_wh, margin=0.20):
    """True if the sized capacity covers required * (1 + margin)."""
    return sized_wh >= required_wh * (1.0 + margin)


def solar_array_power_required(power_w, eclipse_fraction, efficiency, margin=0.20):
    """Solar array power for daylight-only generation:
    P_sa = power_w / (efficiency * (1 - eclipse_fraction)) * (1 + margin)."""
    if power_w <= 0:
        raise ValueError("power must be positive: %r" % (power_w,))
    if not (0.0 < eclipse_fraction < 1.0):
        raise ValueError("eclipse fraction must be in (0, 1): %r" % (eclipse_fraction,))
    if not (0.0 < efficiency <= 1.0):
        raise ValueError("efficiency must be in (0, 1]: %r" % (efficiency,))
    if margin < 0.0:
        raise ValueError("margin must be >= 0: %r" % (margin,))
    return power_w / (efficiency * (1.0 - eclipse_fraction)) * (1.0 + margin)


def power_margin_ok(available_w, required_w, min_margin=0.20):
    """Power margin and pass/fail: returns (margin, ok) with
    margin = available/required - 1. Raises ValueError if the
    required power is not positive.
    """
    if required_w <= 0:
        raise ValueError("required power must be positive: %r" % (required_w,))
    margin = available_w / required_w - 1.0
    return margin, margin >= min_margin
