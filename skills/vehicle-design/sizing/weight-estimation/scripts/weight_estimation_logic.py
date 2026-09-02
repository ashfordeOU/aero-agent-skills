#!/usr/bin/env python3
"""Vehicle weight estimation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): weight and balance computes moments (weight * arm) and the
center of gravity as the ratio of total moment to total weight; the
CG must lie within the forward and aft envelope limits. Class-I
weight estimation uses typical empty-weight fraction bands per
aircraft category; validate the bands against program data. Invalid
inputs raise ValueError throughout.
"""

EMPTY_WEIGHT_FRACTION_BANDS = {
    "transport": (0.42, 0.55),
    "general-aviation": (0.55, 0.68),
    "turboprop": (0.50, 0.62),
}


def moment(weight, arm):
    """Moment about the reference datum: weight * arm.

    Raises ValueError for a negative weight.
    """
    if weight < 0:
        raise ValueError("weight must be non-negative: %r" % (weight,))
    return weight * arm


def cg_from_moments(weights, arms):
    """Center of gravity: sum(weight*arm) / sum(weight).

    Raises ValueError if the lists differ in length, are empty, or
    the total weight is not positive.
    """
    if len(weights) != len(arms):
        raise ValueError(
            "weights and arms length mismatch: %d vs %d" % (len(weights), len(arms))
        )
    if len(weights) == 0:
        raise ValueError("weights and arms must not be empty")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("total weight must be positive: %r" % (total_weight,))
    total_moment = sum(w * a for w, a in zip(weights, arms))
    return total_moment / total_weight


def cg_within_envelope(cg, fwd_limit, aft_limit):
    """True if the CG lies within the envelope: fwd_limit <= cg <= aft_limit.

    Raises ValueError if the forward limit exceeds the aft limit.
    """
    if fwd_limit > aft_limit:
        raise ValueError(
            "forward limit %r exceeds aft limit %r" % (fwd_limit, aft_limit)
        )
    return fwd_limit <= cg <= aft_limit


def empty_weight_fraction_band(category):
    """Typical empty-weight fraction band for an aircraft category.

    Raises ValueError on an unknown category.
    """
    if category not in EMPTY_WEIGHT_FRACTION_BANDS:
        raise ValueError("unknown category: %r" % (category,))
    return EMPTY_WEIGHT_FRACTION_BANDS[category]


def check_empty_weight_fraction(empty_kg, mtow_kg, category):
    """Return (in_band, band, fraction): is the empty-weight fraction
    empty_kg/mtow_kg inside the category band?

    Raises ValueError if the MTOW is not positive or the empty
    weight is negative.
    """
    if mtow_kg <= 0:
        raise ValueError("MTOW must be positive: %r" % (mtow_kg,))
    if empty_kg < 0:
        raise ValueError("empty weight must be non-negative: %r" % (empty_kg,))
    band = empty_weight_fraction_band(category)
    fraction = empty_kg / mtow_kg
    return band[0] <= fraction <= band[1], band, fraction
