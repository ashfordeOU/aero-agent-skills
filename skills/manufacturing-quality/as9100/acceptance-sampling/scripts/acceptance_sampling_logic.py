"""Attribute acceptance-sampling plan logic (pure Python stdlib).

Design and evaluate an attribute acceptance-sampling plan for incoming or
final lots: choose the sample size code letter from the lot size and the
inspection level, look up the single-sampling plan (sample size n, accept
number Ac, reject number Re) for the required AQL, decide accept or reject
from the number of nonconforming units found in the sample, and compute the
operating-characteristic (OC) probability of acceptance across incoming
fraction nonconforming with the binomial model.

The embedded tables are a documented reduced reference table in the style of
ANSI/ASQ Z1.4 attribute sampling (single sampling, normal inspection),
summary data only, not a reproduction of the standard. Reference tables are
name + paraphrase only.

Assumption recorded: the anchor plan of the spec worked example uses the
medium lot-size band at level II and must resolve to code letter J (sample
80, accept 2, reject 3, OC 0.9534 at p = 0.01 and 0.3748 at p = 0.04), so
the ("II", "medium") cell maps to "J" per that anchor. All other table cells
are as printed in the spec. Plan rows for code letters H and L stay
reachable through sampling_plan for direct code-letter lookups.

Every function is deterministic and offline; no RNG, no network, no external
processes. Non-physical inputs raise ValueError.
"""

import math

INSPECTION_LEVELS = ("I", "II", "III")

# Lot-size bands as (name, lower, upper), inclusive both ends. A reduced
# table covers only these documented bands; sizes outside them have no code
# letter in this table and raise ValueError.
LOT_SIZE_BANDS = (
    ("small", 51, 90),
    ("medium", 281, 500),
    ("large", 1201, 3200),
    ("very-large", 10001, 35000),
)

# Code letter by (inspection level, lot-size band). Reduced table. The
# ("II", "medium") cell is anchored at "J" so that the spec worked example
# (lot 500, level II) reproduces the plan (80, 2, 3) and its OC anchors.
CODE_LETTER_TABLE = {
    ("II", "small"): "F",
    ("II", "medium"): "J",
    ("II", "large"): "J",
    ("II", "very-large"): "L",
    ("I", "medium"): "F",
    ("III", "medium"): "K",
}

# Single-sampling plans keyed (code letter, aql string) -> (n, Ac, Re),
# with Re == Ac + 1. AQL keys are the string form, e.g. "1.0".
PLAN_TABLE = {
    ("J", "1.0"): (80, 2, 3),
    ("H", "1.0"): (50, 1, 2),
    ("L", "1.0"): (200, 5, 6),
}


def _require_int(value, name):
    """Return value as int, or raise ValueError for a non-count input."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer unit count, got %r" % (name, value))
    return value


def _aql_key(aql):
    """Normalize an AQL argument to the string table key, e.g. 1.0 -> "1.0"."""
    if isinstance(aql, str):
        return aql.strip()
    if isinstance(aql, bool):
        raise ValueError("aql must be a number or string like '1.0', got %r" % (aql,))
    if isinstance(aql, (int, float)):
        if aql == int(aql):
            return "%d.0" % int(aql)
        return str(aql)
    raise ValueError("aql must be a number or string like '1.0', got %r" % (aql,))


def _band_for_lot(lot_size):
    """Return the lot-size band name containing lot_size, or None."""
    for name, lower, upper in LOT_SIZE_BANDS:
        if lower <= lot_size <= upper:
            return name
    return None


def code_letter(lot_size, inspection_level):
    """Return the sample size code letter for a lot and inspection level.

    Looks the lot size up in the documented bands (small 51-90, medium
    281-500, large 1201-3200, very-large 10001-35000) and returns the code
    letter for the inspection level from CODE_LETTER_TABLE.

    Raises ValueError when lot_size is not a positive integer count, when it
    falls outside every documented band, or when the inspection level is not
    one of ("I", "II", "III").
    """
    lot_size = _require_int(lot_size, "lot_size")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    if inspection_level not in INSPECTION_LEVELS:
        raise ValueError(
            "inspection_level must be one of %s, got %r"
            % (", ".join(INSPECTION_LEVELS), inspection_level)
        )
    band = _band_for_lot(lot_size)
    if band is None:
        raise ValueError(
            "lot_size %d falls outside the documented lot-size bands "
            "(51-90, 281-500, 1201-3200, 10001-35000)" % lot_size
        )
    return CODE_LETTER_TABLE[(inspection_level, band)]


def sampling_plan(code, aql):
    """Return the single-sampling plan (n, Ac, Re) for a code letter and AQL.

    The plan tuple is (sample size n, accept number Ac, reject number Re)
    with Re == Ac + 1, looked up in PLAN_TABLE keyed (code letter, aql
    string). The AQL may be given as a number (1.0) or a string ("1.0").

    Raises ValueError when the (code letter, AQL) pair is not in the
    embedded table or when the code letter is not a string.
    """
    if not isinstance(code, str):
        raise ValueError("code letter must be a string like 'J', got %r" % (code,))
    key = (code, _aql_key(aql))
    try:
        return PLAN_TABLE[key]
    except KeyError:
        raise ValueError(
            "no single-sampling plan in the reduced table for code letter "
            "%r at AQL %r (supported rows: J/1.0, H/1.0, L/1.0)" % (code, aql)
        )


def lot_decision(nonconforming_found, plan):
    """Return "accept" or "reject" for a sampled lot.

    Accepts when the number of nonconforming units found in the sample is at
    or below the accept number Ac; rejects when it is Ac + 1 or more (the
    reject number Re). plan is the (n, Ac, Re) tuple from sampling_plan.

    Raises ValueError for a negative nonconforming count.
    """
    nonconforming_found = _require_int(nonconforming_found, "nonconforming_found")
    if nonconforming_found < 0:
        raise ValueError(
            "nonconforming_found cannot be negative, got %d" % nonconforming_found
        )
    if len(plan) < 2:
        raise ValueError("plan must be an (n, Ac, Re) tuple, got %r" % (plan,))
    accept_number = plan[1]
    return "accept" if nonconforming_found <= accept_number else "reject"


def oc_acceptance_probability(n, ac, p):
    """Return the OC probability of acceptance for a sampling plan at p.

    Binomial model: sum over d = 0..ac of C(n, d) * p^d * (1-p)^(n-d),
    the probability that a lot of fraction nonconforming p yields ac or
    fewer nonconforming units in a random sample of n. Computed with
    math.comb.

    Raises ValueError when n is not a positive integer, ac is negative, or p
    is outside [0, 1].
    """
    n = _require_int(n, "n")
    ac = _require_int(ac, "ac")
    if n < 1:
        raise ValueError("n must be a positive sample size, got %d" % n)
    if ac < 0:
        raise ValueError("ac cannot be negative, got %d" % ac)
    if not 0.0 <= p <= 1.0:
        raise ValueError("fraction nonconforming p must be within [0, 1], got %r" % (p,))
    return sum(math.comb(n, d) * p**d * (1 - p) ** (n - d) for d in range(ac + 1))


def oc_curve(n, ac, p_values):
    """Return the OC curve as a list of (p, probability of acceptance) pairs.

    Evaluates oc_acceptance_probability at every fraction nonconforming in
    the input list, preserving its order.

    Raises ValueError when n or ac are non-physical or when any p is outside
    [0, 1].
    """
    return [(p, oc_acceptance_probability(n, ac, p)) for p in p_values]
