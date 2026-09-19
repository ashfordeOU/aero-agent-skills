"""Temperature-range grouping and allowable-limit margins for a TCS.

Anchor: ECSS-E-ST-31 clauses 3.2, 4.2.1 and 4.2.4 -- placing hardware in the
cryogenic, conventional or high-temperature range, recording its allowable
temperature limits, and turning the predicted temperatures plus their
uncertainties into the design margin the thermal control subsystem works to.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the item: predictions, uncertainties and allowable limits.
2. Inflate the prediction by its direction-specific uncertainty.
3. Place the inflated range against the two range boundaries.
4. Compute the hot and cold margins against the selected limit tier.
5. Decide compliance under a named tolerance and flag an exhausted margin.
6. Aggregate the set: counts per range, breaches, and the design drivers.
"""

import math

__all__ = [
    "ABSOLUTE_ZERO_K",
    "CRYOGENIC_UPPER_K",
    "HIGH_TEMPERATURE_LOWER_K",
    "RANGE_CRYOGENIC",
    "RANGE_CONVENTIONAL",
    "RANGE_HIGH",
    "TEMPERATURE_RANGES",
    "TIER_OPERATIONAL",
    "TIER_SURVIVAL",
    "LIMIT_TIERS",
    "MARGIN_TOLERANCE_K",
    "temperature_range_of",
    "ranges_spanned",
    "validate_item",
    "inflated_prediction",
    "limit_margins",
    "assess_item",
    "group_hardware_by_range",
]

ABSOLUTE_ZERO_K = 0.0

# Range boundaries. Below the cryogenic upper bound the cryogenic rules apply;
# above the high-temperature lower bound the high-temperature and thermal
# protection rules apply; between them the conventional rules.
CRYOGENIC_UPPER_K = 200.0
HIGH_TEMPERATURE_LOWER_K = 470.0

RANGE_CRYOGENIC = "cryogenic"
RANGE_CONVENTIONAL = "conventional"
RANGE_HIGH = "high-temperature"
TEMPERATURE_RANGES = (RANGE_CRYOGENIC, RANGE_CONVENTIONAL, RANGE_HIGH)

TIER_OPERATIONAL = "operational"
TIER_SURVIVAL = "survival"
LIMIT_TIERS = (TIER_OPERATIONAL, TIER_SURVIVAL)

# Margins are differences of sums; a margin that should be exactly zero can
# land a few ULP either side. Absorb that here rather than by moving a limit.
MARGIN_TOLERANCE_K = 1e-9


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _kelvin(label, value):
    v = _real(label, value)
    if v <= ABSOLUTE_ZERO_K:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def temperature_range_of(temperature_k):
    """Return the range a single temperature falls in."""
    t = _kelvin("temperature_k", temperature_k)
    if t < CRYOGENIC_UPPER_K - MARGIN_TOLERANCE_K:
        return RANGE_CRYOGENIC
    if t > HIGH_TEMPERATURE_LOWER_K + MARGIN_TOLERANCE_K:
        return RANGE_HIGH
    return RANGE_CONVENTIONAL


def ranges_spanned(minimum_k, maximum_k):
    """Return every range an inflated prediction interval touches."""
    low = _kelvin("minimum_k", minimum_k)
    high = _kelvin("maximum_k", maximum_k)
    if high < low:
        raise ValueError("maximum_k %g must not be below minimum_k %g" % (high, low))
    touched = []
    if low < CRYOGENIC_UPPER_K - MARGIN_TOLERANCE_K:
        touched.append(RANGE_CRYOGENIC)
    conventional_low = max(low, CRYOGENIC_UPPER_K)
    conventional_high = min(high, HIGH_TEMPERATURE_LOWER_K)
    if conventional_high >= conventional_low - MARGIN_TOLERANCE_K and not (
        high < CRYOGENIC_UPPER_K - MARGIN_TOLERANCE_K
        or low > HIGH_TEMPERATURE_LOWER_K + MARGIN_TOLERANCE_K
    ):
        touched.append(RANGE_CONVENTIONAL)
    if high > HIGH_TEMPERATURE_LOWER_K + MARGIN_TOLERANCE_K:
        touched.append(RANGE_HIGH)
    return touched


def validate_item(item):
    """Return one validated hardware item ready for grouping."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item needs a non-empty name")
    tier = item.get("limit_tier", TIER_OPERATIONAL)
    if tier not in LIMIT_TIERS:
        raise ValueError(
            "limit_tier of %s must be one of %s, got %r"
            % (name, ", ".join(LIMIT_TIERS), tier)
        )
    predicted_min = _kelvin("predicted_min_k of %s" % name, item.get("predicted_min_k"))
    predicted_max = _kelvin("predicted_max_k of %s" % name, item.get("predicted_max_k"))
    if predicted_max < predicted_min:
        raise ValueError(
            "predicted_max_k of %s must not be below predicted_min_k" % name
        )
    allowable_min = _kelvin("allowable_min_k of %s" % name, item.get("allowable_min_k"))
    allowable_max = _kelvin("allowable_max_k of %s" % name, item.get("allowable_max_k"))
    if allowable_max <= allowable_min:
        raise ValueError(
            "allowable_max_k of %s must be strictly above allowable_min_k" % name
        )
    return {
        "name": name.strip(),
        "limit_tier": tier,
        "predicted_min_k": predicted_min,
        "predicted_max_k": predicted_max,
        "uncertainty_cold_k": _non_negative(
            "uncertainty_cold_k of %s" % name, item.get("uncertainty_cold_k", 0.0)
        ),
        "uncertainty_hot_k": _non_negative(
            "uncertainty_hot_k of %s" % name, item.get("uncertainty_hot_k", 0.0)
        ),
        "allowable_min_k": allowable_min,
        "allowable_max_k": allowable_max,
    }


def inflated_prediction(item):
    """Return the prediction widened by its direction-specific uncertainty."""
    low = item["predicted_min_k"] - item["uncertainty_cold_k"]
    high = item["predicted_max_k"] + item["uncertainty_hot_k"]
    if low <= ABSOLUTE_ZERO_K:
        raise ValueError(
            "inflated cold prediction of %s falls to or below absolute zero"
            % item["name"]
        )
    return low, high


def limit_margins(item):
    """Return the hot and cold margins against the item's allowable limits."""
    low, high = inflated_prediction(item)
    return {
        "inflated_min_k": low,
        "inflated_max_k": high,
        "cold_margin_k": low - item["allowable_min_k"],
        "hot_margin_k": item["allowable_max_k"] - high,
    }


def assess_item(item):
    """Group one item by range and grade it against its allowable limits."""
    checked = validate_item(item)
    margins = limit_margins(checked)
    touched = ranges_spanned(margins["inflated_min_k"], margins["inflated_max_k"])
    findings = []
    cold_breach = margins["cold_margin_k"] < -MARGIN_TOLERANCE_K
    hot_breach = margins["hot_margin_k"] < -MARGIN_TOLERANCE_K
    cold_exhausted = abs(margins["cold_margin_k"]) <= MARGIN_TOLERANCE_K
    hot_exhausted = abs(margins["hot_margin_k"]) <= MARGIN_TOLERANCE_K
    if cold_breach:
        findings.append(
            "cold case breaches the allowable minimum by %g K"
            % (-margins["cold_margin_k"])
        )
    if hot_breach:
        findings.append(
            "hot case breaches the allowable maximum by %g K"
            % (-margins["hot_margin_k"])
        )
    if cold_exhausted:
        findings.append("cold margin is exhausted; nothing is left on the cold side")
    if hot_exhausted:
        findings.append("hot margin is exhausted; nothing is left on the hot side")
    if len(touched) > 1:
        findings.append(
            "spans %s; both rule sets apply to this item" % ", ".join(touched)
        )
    if checked["limit_tier"] == TIER_SURVIVAL:
        findings.append(
            "graded against survival limits; an operating case needs the "
            "operational tier"
        )
    record = dict(checked)
    record.update(margins)
    record["ranges"] = touched
    record["primary_range"] = temperature_range_of(
        0.5 * (margins["inflated_min_k"] + margins["inflated_max_k"])
    )
    record["compliant"] = not (cold_breach or hot_breach)
    record["margin_exhausted"] = cold_exhausted or hot_exhausted
    record["findings"] = findings
    return record


def group_hardware_by_range(items):
    """Group a hardware list by temperature range and report the drivers."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    records = []
    seen = set()
    for item in items:
        record = assess_item(item)
        if record["name"] in seen:
            raise ValueError("duplicate item name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    counts = {name: 0 for name in TEMPERATURE_RANGES}
    for record in records:
        for name in record["ranges"]:
            counts[name] += 1
    breaches = [r["name"] for r in records if not r["compliant"]]
    exhausted = [
        r["name"] for r in records if r["compliant"] and r["margin_exhausted"]
    ]
    multi = [r["name"] for r in records if len(r["ranges"]) > 1]
    cold_driver = min(records, key=lambda r: (r["cold_margin_k"], r["name"]))
    hot_driver = min(records, key=lambda r: (r["hot_margin_k"], r["name"]))
    findings = []
    if breaches:
        findings.append("allowable limits breached by: %s" % ", ".join(sorted(breaches)))
    if exhausted:
        findings.append("margin exhausted on: %s" % ", ".join(sorted(exhausted)))
    if multi:
        findings.append(
            "items owing more than one rule set: %s" % ", ".join(sorted(multi))
        )
    return {
        "records": records,
        "counts": counts,
        "breaches": sorted(breaches),
        "exhausted": sorted(exhausted),
        "multi_range": sorted(multi),
        "cold_driver": cold_driver["name"],
        "cold_driver_margin_k": cold_driver["cold_margin_k"],
        "hot_driver": hot_driver["name"],
        "hot_driver_margin_k": hot_driver["hot_margin_k"],
        "compliant": not breaches,
        "findings": findings,
    }
