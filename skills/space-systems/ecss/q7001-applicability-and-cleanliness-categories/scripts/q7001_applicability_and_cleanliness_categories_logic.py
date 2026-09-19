"""Applicability screen and contamination-sensitivity banding of hardware.

Anchor: ECSS-Q-ST-70-01C framework (which items the cleanliness and
contamination-control requirements apply to, and how hardware is grouped by
how much particulate and molecular contamination it can tolerate).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide applicability per item from what the item is and what it touches:
   flight hardware, anything that contacts flight hardware, and anything
   sharing the controlled environment are in scope; an item declared out of
   scope has to carry a justification or the declaration is refused.
2. Band the item on two independent axes. The particulate axis is driven by
   the obscuration (percentage area coverage) the item's function can still
   tolerate; the molecular axis by the areal deposited mass it can still
   tolerate. Both are budgets the programme allocates, not adjectives.
3. Combine the two axes by taking the more demanding band, and name which
   axis drove it -- both, when they are equally demanding.
4. Group an inventory into bands, count each band, and report findings: an
   in-scope item with an unbudgeted axis, an out-of-scope item with no
   justification, and an in-scope item that shares an environment with a
   more demanding item than its own band.
"""

import math

__all__ = [
    "BANDS",
    "PARTICULATE_THRESHOLDS_PERCENT",
    "MOLECULAR_THRESHOLDS_NG_PER_CM2",
    "BAND_TOLERANCE",
    "validate_positive",
    "validate_item",
    "is_applicable",
    "band_rank",
    "more_demanding_band",
    "particulate_band",
    "molecular_band",
    "categorize_item",
    "categorize_inventory",
]

# Bands run from the most tolerant to the most demanding. The order is the
# grading order used everywhere below; nothing else depends on the labels.
BANDS = ("tolerant", "moderate", "sensitive", "highly-sensitive")

# Default banding ladders. A programme declares its own; these are the
# fall-back breakpoints used when no ladder is supplied. Each entry is the
# upper bound of the band it names, reading from the most demanding end.
PARTICULATE_THRESHOLDS_PERCENT = (
    (0.01, "highly-sensitive"),
    (0.1, "sensitive"),
    (1.0, "moderate"),
)
MOLECULAR_THRESHOLDS_NG_PER_CM2 = (
    (10.0, "highly-sensitive"),
    (100.0, "sensitive"),
    (1000.0, "moderate"),
)

# A budget sitting exactly on a breakpoint belongs to the more demanding band.
# The comparison absorbs representation error rather than moving the ladder.
BAND_TOLERANCE = 1e-12


def validate_positive(value, label):
    """Return value as a positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _validate_ladder(ladder, label):
    """Return a banding ladder as ascending (bound, band) pairs."""
    if not isinstance(ladder, (list, tuple)) or not ladder:
        raise ValueError("%s must be a non-empty sequence of (bound, band) pairs" % label)
    pairs = []
    for index, entry in enumerate(ladder):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("%s[%d] must be a (bound, band) pair" % (label, index))
        bound, band = entry
        bound = validate_positive(bound, "%s[%d] bound" % (label, index))
        if band not in BANDS:
            raise ValueError("%s[%d] names an unknown band %r" % (label, index, band))
        pairs.append((bound, band))
    for index in range(1, len(pairs)):
        if pairs[index][0] <= pairs[index - 1][0]:
            raise ValueError("%s bounds must strictly increase (index %d)" % (label, index))
    return pairs


def is_applicable(item):
    """Return the applicability decision and the reason that produced it."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    if item.get("flight_hardware"):
        return {"applicable": True, "reason": "flight hardware"}
    if item.get("contacts_flight_hardware"):
        return {"applicable": True, "reason": "contacts flight hardware"}
    if item.get("shares_controlled_environment"):
        return {
            "applicable": True,
            "reason": "shares the controlled environment with flight hardware",
        }
    justification = item.get("exclusion_justification")
    if not isinstance(justification, str) or not justification.strip():
        raise ValueError(
            "item %r is outside every applicability route and carries no "
            "exclusion_justification" % item.get("name", "<unnamed>")
        )
    return {"applicable": False, "reason": justification.strip()}


def band_rank(band):
    """Return the position of a band in the grading order."""
    if band not in BANDS:
        raise ValueError("unknown band %r" % (band,))
    return BANDS.index(band)


def more_demanding_band(first, second):
    """Return whichever of two bands is the more demanding."""
    return first if band_rank(first) >= band_rank(second) else second


def _band_from_ladder(budget, ladder):
    """Return the band a tolerance budget falls into on an ascending ladder."""
    for bound, band in ladder:
        if budget < bound or math.isclose(budget, bound, rel_tol=BAND_TOLERANCE):
            return band
    return BANDS[0]


def particulate_band(allowed_obscuration_percent, ladder=None):
    """Return the particulate sensitivity band for an obscuration budget."""
    budget = validate_positive(
        allowed_obscuration_percent, "allowed_obscuration_percent"
    )
    if budget >= 100.0:
        raise ValueError("allowed_obscuration_percent must stay below a fully covered surface")
    pairs = _validate_ladder(
        ladder if ladder is not None else PARTICULATE_THRESHOLDS_PERCENT,
        "particulate ladder",
    )
    return _band_from_ladder(budget, pairs)


def molecular_band(allowed_deposition_ng_per_cm2, ladder=None):
    """Return the molecular sensitivity band for an areal deposition budget."""
    budget = validate_positive(
        allowed_deposition_ng_per_cm2, "allowed_deposition_ng_per_cm2"
    )
    pairs = _validate_ladder(
        ladder if ladder is not None else MOLECULAR_THRESHOLDS_NG_PER_CM2,
        "molecular ladder",
    )
    return _band_from_ladder(budget, pairs)


def validate_item(item):
    """Return a validated hardware item record."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item name must be a non-empty string")
    return dict(item, name=name.strip())


def categorize_item(item, particulate_ladder=None, molecular_ladder=None):
    """Band one hardware item on both contamination axes."""
    record = validate_item(item)
    applicability = is_applicable(record)
    result = {
        "name": record["name"],
        "environment": record.get("environment"),
        "applicable": applicability["applicable"],
        "applicability_reason": applicability["reason"],
        "particulate_band": None,
        "molecular_band": None,
        "overall_band": None,
        "driving_axis": None,
        "unbudgeted_axes": [],
    }
    if not applicability["applicable"]:
        return result
    obscuration = record.get("allowed_obscuration_percent")
    deposition = record.get("allowed_deposition_ng_per_cm2")
    if obscuration is not None:
        result["particulate_band"] = particulate_band(obscuration, particulate_ladder)
    else:
        result["unbudgeted_axes"].append("particulate")
    if deposition is not None:
        result["molecular_band"] = molecular_band(deposition, molecular_ladder)
    else:
        result["unbudgeted_axes"].append("molecular")
    bands = [b for b in (result["particulate_band"], result["molecular_band"]) if b]
    if not bands:
        return result
    overall = bands[0]
    for band in bands[1:]:
        overall = more_demanding_band(overall, band)
    result["overall_band"] = overall
    if result["particulate_band"] == result["molecular_band"]:
        result["driving_axis"] = "both"
    elif result["particulate_band"] == overall:
        result["driving_axis"] = "particulate"
    else:
        result["driving_axis"] = "molecular"
    return result


def categorize_inventory(items, particulate_ladder=None, molecular_ladder=None):
    """Group a hardware inventory into bands and report the coverage findings."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item mappings")
    records = []
    seen = set()
    for item in items:
        record = categorize_item(item, particulate_ladder, molecular_ladder)
        if record["name"] in seen:
            raise ValueError("duplicate item name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    grouped = {band: [] for band in BANDS}
    findings = []
    for record in records:
        if record["overall_band"]:
            grouped[record["overall_band"]].append(record["name"])
        if record["applicable"] and record["unbudgeted_axes"]:
            findings.append(
                "in-scope item %r has no budget on the %s axis, so it cannot be banded "
                "on it" % (record["name"], " and ".join(record["unbudgeted_axes"]))
            )
        if not record["applicable"]:
            findings.append(
                "item %r is outside the applicability of the requirements: %s"
                % (record["name"], record["applicability_reason"])
            )
    banded = [r for r in records if r["overall_band"]]
    driving = None
    if banded:
        driving = banded[0]
        for record in banded[1:]:
            if band_rank(record["overall_band"]) > band_rank(driving["overall_band"]):
                driving = record
    for record in banded:
        shared = record.get("environment")
        if not shared or driving is None:
            continue
        for other in banded:
            if other is record or other.get("environment") != shared:
                continue
            if band_rank(other["overall_band"]) > band_rank(record["overall_band"]):
                findings.append(
                    "item %r shares environment %r with the more demanding item %r; "
                    "the environment is held to the more demanding band"
                    % (record["name"], shared, other["name"])
                )
                break
    return {
        "records": records,
        "grouped": grouped,
        "counts": {band: len(names) for band, names in grouped.items()},
        "applicable_count": sum(1 for r in records if r["applicable"]),
        "driving_item": None if driving is None else driving["name"],
        "driving_band": None if driving is None else driving["overall_band"],
        "findings": findings,
    }
