"""ADS-B surveillance category and coverage logic (DO-260B-style).

Pure stdlib module for assessing an ADS-B Out installation and an
ADS-B In reception geometry: it maps NIC, NACp and SIL categories to
their published DO-260B-style bounds (containment radius, 95-percent
accuracy, per-flight-hour integrity probability), selects the category
whose bound covers a required value, and computes the 1090 MHz
extended squitter radio line-of-sight range between two altitudes.

The category tables are treated as data (module constants), stated as
a paraphrase of the published DO-260B category definitions, never as a
reproduction of MOPS tables.
"""

import math

# DO-260B-style navigation integrity category (NIC) containment radius
# in metres. Higher NIC = tighter containment; 0 means unknown.
NIC_RADIUS_M = {11: 7.5, 10: 25.0, 9: 75.0, 8: 185.2, 7: 370.4, 6: 1111.2,
                5: 1852.0, 4: 3704.0, 3: 7408.0, 2: 14816.0, 1: 37040.0,
                0: None}

# DO-260B-style navigation accuracy category for position (NACp)
# 95-percent horizontal accuracy bound in metres. 0 means unknown.
NACp_95_M = {11: 3.0, 10: 10.0, 9: 30.0, 8: 92.6, 7: 185.2, 6: 370.4,
             5: 926.0, 4: 1852.0, 3: 3704.0, 2: 7408.0, 1: 18520.0,
             0: None}

# DO-260B-style source integrity level (SIL) maximum probability of an
# undetected failure per flight hour. 0 means unknown.
SIL_PROB = {3: 1e-7, 2: 1e-5, 1: 1e-3, 0: None}

# Radio horizon coefficient, km per sqrt(metres altitude), for the
# standard-atmosphere 4/3-earth-radius line-of-sight model.
RANGE_COEFF = 4.12

# Feet to metres conversion factor.
FT_TO_M = 0.3048

_NIC_RANGE = range(0, 12)      # valid NIC and NACp category integers 0-11
_SIL_RANGE = range(0, 4)       # valid SIL integers 0-3


def _require_int(value, lo, hi, name):
    """Raise ValueError unless value is an integer category in [lo, hi]."""
    if isinstance(value, bool) or not isinstance(value, int) \
            or not lo <= value <= hi:
        raise ValueError("%s must be an integer in %d-%d" % (name, lo, hi))
    return value


def nic_containment_radius(nic):
    """Return the containment radius in metres for a NIC category.

    Returns None for NIC 0 (unknown). Raises ValueError if nic is not
    an integer in 0-11.
    """
    _require_int(nic, 0, 11, "nic")
    return NIC_RADIUS_M[nic]


def nacp_accuracy(nacp):
    """Return the 95-percent horizontal accuracy bound in metres for NACp.

    Returns None for NACp 0 (unknown). Raises ValueError if nacp is not
    an integer in 0-11.
    """
    _require_int(nacp, 0, 11, "nacp")
    return NACp_95_M[nacp]


def sil_probability(sil):
    """Return the maximum integrity probability per flight hour for SIL.

    Returns None for SIL 0 (unknown). Raises ValueError if sil is not an
    integer in 0-3.
    """
    _require_int(sil, 0, 3, "sil")
    return SIL_PROB[sil]


def _category_for_required(required, table, name):
    """Select the tightest category whose bound covers the requirement.

    Iterates the categories from highest number (tightest bound) down to
    category 1 and returns the first whose bound is >= required, i.e.
    the least-integrity category that still bounds the requirement.
    Returns 0 when no category bound covers the requirement. Category 0
    (unknown) is skipped.
    """
    if required <= 0:
        raise ValueError("%s required bound must be positive" % name)
    for cat in range(len(table) - 1, 0, -1):
        bound = table[cat]
        if bound >= required:
            return cat
    return 0


def nic_for_radius(required_radius_m):
    """Return the NIC whose containment radius covers a required radius.

    Chooses the tightest category whose containment radius is >=
    required_radius_m (least-integrity category that still bounds the
    requirement); returns 0 when even NIC 1 is too small. Raises
    ValueError if required_radius_m <= 0.
    """
    return _category_for_required(required_radius_m, NIC_RADIUS_M, "nic")


def nacp_for_accuracy(required_95_m):
    """Return the NACp whose 95-percent bound covers a required accuracy.

    Chooses the tightest category whose 95-percent bound is >=
    required_95_m; returns 0 when even NACp 1 is too small. Raises
    ValueError if required_95_m <= 0.
    """
    return _category_for_required(required_95_m, NACp_95_M, "nacp")


def adsb_range_km(alt_ft_own, alt_ft_other=0.0):
    """Radio line-of-sight range (km) between own and other altitudes.

    d = RANGE_COEFF * (sqrt(alt_own * FT_TO_M) +
    sqrt(alt_other * FT_TO_M)), the 4/3-earth 1090 MHz radio horizon in
    standard atmosphere. Raises ValueError for a negative altitude.
    """
    if alt_ft_own < 0 or alt_ft_other < 0:
        raise ValueError("altitudes must be non-negative")
    return RANGE_COEFF * (math.sqrt(alt_ft_own * FT_TO_M)
                          + math.sqrt(alt_ft_other * FT_TO_M))


def adsb_assessment(nic, nacp, sil, alt_ft_own, alt_ft_other=0.0):
    """Assess an ADS-B surveillance case in one call.

    Returns the dict {containment_radius_m, accuracy_95_m,
    integrity_prob, range_km} built from the category lookups and the
    radio line-of-sight range. ValueErrors from the individual
    functions propagate.
    """
    return {
        "containment_radius_m": nic_containment_radius(nic),
        "accuracy_95_m": nacp_accuracy(nacp),
        "integrity_prob": sil_probability(sil),
        "range_km": adsb_range_km(alt_ft_own, alt_ft_other),
    }
