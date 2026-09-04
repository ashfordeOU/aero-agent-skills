"""ICA/CMR/ALI item classification and ALS coverage logic (pure stdlib).

Classifies candidate maintenance and limitation items from certification
into ALI (airworthiness limitation items), CMR (certification maintenance
requirements) or routine scheduled maintenance, then computes the ALS
coverage of a submitted maintenance program against the type-certificate
airworthiness limitations and the per-item interval compliance against the
ALS maximum intervals.

Conventions
-----------
An item is a tuple (name, driver, interval). The driver is the
certification driver that makes the item mandatory. Classification rule:
driver in ALI_DRIVERS -> ALI; driver == "CMR" -> CMR; driver == "ROUTINE"
-> routine. ALS coverage is the number of the ALS_MAX_INTERVALS canonical
items present in the program divided by the total canonical count.
Interval compliance applies only to canonical items whose kind is ALI:
compliant when the program interval is at most the ALS maximum.
"""

ALLOWED_DRIVERS = ("LLP", "DT", "FF", "CMR", "ROUTINE")
"""Certification drivers that a submitted item may carry: life-limited
part (LLP), damage-tolerance inspection (DT), fuel-tank flammability
check (FF), certification maintenance requirement (CMR), routine task
(ROUTINE)."""

ALI_DRIVERS = ("LLP", "DT", "FF")
"""Certification drivers that make an item a mandatory airworthiness
limitation item (ALI)."""

ALS_MAX_INTERVALS = {
    "APU shaft LLP": 20000.0,  # flight cycles
    "wing spar DT inspection": 4000.0,  # flight cycles
    "fuel-tank flammability check": 12000.0,  # flight hours
}
"""Type-certificate ALS maximum intervals for the anchor program, keyed
by the canonical ALS item names. Intervals carry the item's own unit,
flight cycles or flight hours as labeled."""

_DRIVER_RATIONALE = {
    "LLP": ("life-limited part; mandatory, and published in the "
            "Airworthiness Limitations Section of the ICA"),
    "DT": ("damage-tolerance inspection; mandatory, and published in the "
           "Airworthiness Limitations Section of the ICA"),
    "FF": ("fuel-tank flammability check; mandatory, and published in the "
           "Airworthiness Limitations Section of the ICA"),
    "CMR": ("certification maintenance requirement; mandatory and "
            "authority-controlled"),
    "ROUTINE": ("routine scheduled maintenance; non-mandatory"),
}


def classify_item(name, driver, interval):
    """Classify one item by its certification driver.

    Returns {"name", "driver", "kind", "rationale"} with kind one of
    "ALI", "CMR" or "routine". Raises ValueError for an unknown driver
    (not in ALLOWED_DRIVERS) or a non-positive interval.
    """
    if driver not in ALLOWED_DRIVERS:
        raise ValueError(
            "unknown certification driver %r; allowed drivers are %s"
            % (driver, ", ".join(ALLOWED_DRIVERS)))
    if interval <= 0:
        raise ValueError("interval must be positive, got %r" % (interval,))
    if driver in ALI_DRIVERS:
        kind = "ALI"
    elif driver == "CMR":
        kind = "CMR"
    else:
        kind = "routine"
    return {
        "name": name,
        "driver": driver,
        "kind": kind,
        "rationale": "%s: %s" % (driver, _DRIVER_RATIONALE[driver]),
    }


def als_coverage(items):
    """ALS coverage of the submitted maintenance program.

    Returns {"matched", "required", "coverage_fraction"} where required
    is the number of canonical ALS items in ALS_MAX_INTERVALS and
    matched is how many of those canonical names appear in the program.
    Raises ValueError when items is empty.
    """
    if not items:
        raise ValueError("items must not be empty")
    present = {name for name, _driver, _interval in items}
    matched = len(present & set(ALS_MAX_INTERVALS))
    required = len(ALS_MAX_INTERVALS)
    return {
        "matched": matched,
        "required": required,
        "coverage_fraction": matched / required,
    }


def interval_compliance(name, interval):
    """Interval compliance of one canonical ALS item against its maximum.

    Returns {"name", "max_interval", "compliant"} with compliant True
    when the program interval is at most the ALS maximum. Raises
    ValueError for a name outside ALS_MAX_INTERVALS or a non-positive
    interval.
    """
    if name not in ALS_MAX_INTERVALS:
        raise ValueError(
            "%r is not a canonical ALS item; canonical items are %s"
            % (name, ", ".join(sorted(ALS_MAX_INTERVALS))))
    if interval <= 0:
        raise ValueError("interval must be positive, got %r" % (interval,))
    max_interval = ALS_MAX_INTERVALS[name]
    return {
        "name": name,
        "max_interval": max_interval,
        "compliant": interval <= max_interval,
    }


def ica_cmr_ali_review(items):
    """Full review of a submitted maintenance program.

    Returns {"per_item", "class_counts", "coverage", "non_compliant",
    "missing_als_items"}: per-item classification dicts in program
    order, class counts keyed ALI/CMR/routine, the ALS coverage dict,
    the names of canonical items whose kind is ALI and whose interval
    exceeds the ALS maximum, and the canonical ALS item names absent from the
    program (in ALS_MAX_INTERVALS order). Raises ValueError for an empty
    program, an unknown driver or a non-positive interval.
    """
    if not items:
        raise ValueError("items must not be empty")
    per_item = [classify_item(name, driver, interval)
                for (name, driver, interval) in items]
    class_counts = {"ALI": 0, "CMR": 0, "routine": 0}
    for entry in per_item:
        class_counts[entry["kind"]] += 1
    non_compliant = []
    for (name, _driver, interval), entry in zip(items, per_item):
        if (entry["kind"] == "ALI"
                and name in ALS_MAX_INTERVALS
                and interval > ALS_MAX_INTERVALS[name]):
            non_compliant.append(name)
    present = {name for name, _driver, _interval in items}
    missing = [name for name in ALS_MAX_INTERVALS if name not in present]
    return {
        "per_item": per_item,
        "class_counts": class_counts,
        "coverage": als_coverage(items),
        "non_compliant": non_compliant,
        "missing_als_items": missing,
    }
