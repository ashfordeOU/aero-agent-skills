"""Verifying hardware cleanliness at goods receipt and after transport.

Anchor: the goods-receipt and transport provisions of the contamination
and cleanliness control practice of ECSS-Q-ST-70-01C (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Two independent stories arrive with the package. The measurements
   say what the surface is now; the packaging and transport records say
   what happened to it on the way. Either can condemn the item, and a
   clean measurement does not clear a breached bag, because the breach
   says the measurement is not representative of the whole surface.
2. A measurement with no method named is not a measurement. Residue by
   solvent rinse and residue by tape lift are different numbers, and a
   figure with no method behind it cannot be compared with a limit or
   repeated by anybody else.
3. Limits here are upper bounds in which a smaller number is cleaner.
   The margin worth reporting is the fraction of the limit consumed, so
   an item at nine tenths of its residue limit on arrival is visibly a
   problem even though it passes.
4. A limit exceeded is not automatically a rejection. Contamination
   that recleaning routinely removes is sent to recleaning and
   re-verification; contamination beyond what recleaning recovers goes
   to nonconformance, and the boundary between them is declared, not
   improvised per item.
5. The receipt inspection itself is a contamination event. Opening a
   precision-clean item in a hall dirtier than it requires puts more on
   the surface than the transport did, so the area the inspection
   happened in is graded alongside the item.
6. Cleanliness has a shelf life. An item within limits, correctly
   packaged and long past the interval since its last verified
   cleaning, is re-verified rather than accepted on the strength of a
   certificate written a year ago.

Stdlib only, offline, deterministic.
"""

# Dispositions, in increasing order of consequence.
ACCEPT = "accept"
ACCEPT_AFTER_REVERIFICATION = "accept-after-re-verification"
RECLEAN_AND_REVERIFY = "reclean-and-re-verify"
QUARANTINE_PENDING_MEASUREMENT = "quarantine-pending-re-measurement"
NONCONFORMANCE = "raise-a-nonconformance"
DISPOSITION_ORDER = (
    ACCEPT,
    ACCEPT_AFTER_REVERIFICATION,
    RECLEAN_AND_REVERIFY,
    QUARANTINE_PENDING_MEASUREMENT,
    NONCONFORMANCE,
)

# How far past a limit recleaning is still expected to recover.
DEFAULT_RECLEAN_CEILING_FACTOR = 5.0

# Contamination indicator states a bag can arrive in.
INDICATOR_INTACT = "intact"
INDICATOR_TRIPPED = "tripped"
INDICATOR_ABSENT = "absent"
INDICATOR_STATES = (INDICATOR_INTACT, INDICATOR_TRIPPED, INDICATOR_ABSENT)

# A measured value equal to its limit passes.
RELATIVE_TOLERANCE = 1.0e-12


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return float(value)


def _non_negative(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def escalate(current, candidate):
    """Return whichever of two dispositions has the greater consequence."""
    for name in (current, candidate):
        if name not in DISPOSITION_ORDER:
            raise ValueError("unknown disposition %r" % (name,))
    if DISPOSITION_ORDER.index(candidate) > DISPOSITION_ORDER.index(current):
        return candidate
    return current


def consumed_fraction(measured, limit):
    """Fraction of an upper-bound limit a measurement consumes."""
    value = _non_negative("measured", measured)
    bound = _positive("limit", limit)
    return value / bound


def within_limit(measured, limit):
    """True when a measurement sits at or under its upper-bound limit."""
    value = _non_negative("measured", measured)
    bound = _positive("limit", limit)
    return value <= bound * (1.0 + RELATIVE_TOLERANCE)


def validate_measurement(name, measurement):
    """Validate one measurement: a value, a limit and the method used."""
    if not isinstance(measurement, dict):
        raise ValueError("%s measurement must be a mapping" % name)
    limit = _positive("%s limit" % name, measurement.get("limit"))
    value = measurement.get("measured")
    method = measurement.get("method")
    if value is None:
        return {"name": name, "limit": limit, "measured": None, "method": None}
    value = _non_negative("%s measured" % name, value)
    if method is None or not str(method).strip():
        return {"name": name, "limit": limit, "measured": value, "method": None}
    return {
        "name": name,
        "limit": limit,
        "measured": value,
        "method": _text("%s method" % name, method),
    }


def assess_measurement(name, measurement, reclean_ceiling_factor):
    """Grade one measurement and say what it drives the disposition to."""
    norm = validate_measurement(name, measurement)
    findings = []
    disposition = ACCEPT
    if norm["measured"] is None:
        findings.append("%s-not-measured-at-receipt" % name)
        return {
            "name": name,
            "limit": norm["limit"],
            "measured": None,
            "method": None,
            "consumed_fraction": None,
            "within_limit": None,
            "findings": findings,
            "disposition": QUARANTINE_PENDING_MEASUREMENT,
        }
    if norm["method"] is None:
        findings.append("%s-reported-with-no-method-named" % name)
        disposition = escalate(disposition, QUARANTINE_PENDING_MEASUREMENT)
    consumed = consumed_fraction(norm["measured"], norm["limit"])
    inside = within_limit(norm["measured"], norm["limit"])
    if not inside:
        ceiling = _positive("reclean_ceiling_factor", reclean_ceiling_factor)
        if consumed <= ceiling * (1.0 + RELATIVE_TOLERANCE):
            findings.append("%s-above-its-limit-but-within-recleaning-reach" % name)
            disposition = escalate(disposition, RECLEAN_AND_REVERIFY)
        else:
            findings.append("%s-beyond-what-recleaning-recovers" % name)
            disposition = escalate(disposition, NONCONFORMANCE)
    return {
        "name": name,
        "limit": norm["limit"],
        "measured": norm["measured"],
        "method": norm["method"],
        "consumed_fraction": consumed,
        "within_limit": inside,
        "findings": findings,
        "disposition": disposition,
    }


def assess_packaging(packaging):
    """Grade the packaging the item arrived in."""
    if not isinstance(packaging, dict):
        raise ValueError("packaging must be a mapping")
    outer = _boolean("packaging outer_bag_intact", packaging.get("outer_bag_intact"))
    inner = _boolean("packaging inner_bag_intact", packaging.get("inner_bag_intact"))
    seal = _boolean("packaging seal_intact", packaging.get("seal_intact"))
    indicator = _text("packaging indicator_state", packaging.get("indicator_state"))
    if indicator not in INDICATOR_STATES:
        raise ValueError(
            "packaging indicator_state %r is not one of %r"
            % (indicator, list(INDICATOR_STATES))
        )
    purge = packaging.get("purge_pressure_kpa")
    minimum_purge = packaging.get("minimum_purge_pressure_kpa")
    findings = []
    disposition = ACCEPT
    if not outer:
        findings.append("outer-bag-breached-in-transit")
        disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
    if not inner:
        findings.append("inner-bag-breached-in-transit")
        disposition = escalate(disposition, RECLEAN_AND_REVERIFY)
    if not seal:
        findings.append("seal-broken-before-goods-receipt")
        disposition = escalate(disposition, RECLEAN_AND_REVERIFY)
    if indicator == INDICATOR_TRIPPED:
        findings.append("contamination-indicator-tripped")
        disposition = escalate(disposition, RECLEAN_AND_REVERIFY)
    if indicator == INDICATOR_ABSENT:
        findings.append("no-contamination-indicator-in-the-package")
        disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
    if minimum_purge is not None:
        floor = _positive("minimum_purge_pressure_kpa", minimum_purge)
        if purge is None:
            findings.append("purge-required-but-no-pressure-recorded")
            disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
        else:
            measured = _non_negative("purge_pressure_kpa", purge)
            if measured < floor * (1.0 - RELATIVE_TOLERANCE):
                findings.append("purge-pressure-lost-in-transit")
                disposition = escalate(disposition, RECLEAN_AND_REVERIFY)
    return {
        "outer_bag_intact": outer,
        "inner_bag_intact": inner,
        "seal_intact": seal,
        "indicator_state": indicator,
        "findings": findings,
        "disposition": disposition,
    }


def assess_transport(transport, limits):
    """Grade the transport record against the environment the item allows."""
    if not isinstance(transport, dict):
        raise ValueError("transport must be a mapping")
    if not isinstance(limits, dict):
        raise ValueError("transport limits must be a mapping")
    findings = []
    disposition = ACCEPT
    shock = _non_negative("transport max_shock_g", transport.get("max_shock_g", 0.0))
    shock_limit = _positive("shock limit", limits.get("max_shock_g", 5.0))
    if shock > shock_limit * (1.0 + RELATIVE_TOLERANCE):
        findings.append("transport-shock-above-what-the-item-allows")
        disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
    humidity = _non_negative(
        "transport max_humidity_pct", transport.get("max_humidity_pct", 0.0)
    )
    humidity_limit = _positive("humidity limit", limits.get("max_humidity_pct", 60.0))
    if humidity > humidity_limit * (1.0 + RELATIVE_TOLERANCE):
        findings.append("transport-humidity-above-what-the-item-allows")
        disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
    days = _non_negative(
        "days_since_verified_cleaning", transport.get("days_since_verified_cleaning", 0.0)
    )
    shelf_life = _positive("shelf_life_days", limits.get("shelf_life_days", 365.0))
    if days > shelf_life * (1.0 + RELATIVE_TOLERANCE):
        findings.append("cleanliness-certificate-older-than-the-shelf-life")
        disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
    return {
        "max_shock_g": shock,
        "max_humidity_pct": humidity,
        "days_since_verified_cleaning": days,
        "shelf_life_days": shelf_life,
        "findings": findings,
        "disposition": disposition,
    }


def assess_receipt(item, receipt):
    """Grade an arriving item at goods receipt and name a disposition."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a mapping")
    item_id = _text("item id", item.get("id"))
    required_class = item.get("required_area_class")
    reclean_factor = _positive(
        "reclean_ceiling_factor",
        item.get("reclean_ceiling_factor", DEFAULT_RECLEAN_CEILING_FACTOR),
    )

    measurements = receipt.get("measurements")
    if not isinstance(measurements, dict) or not measurements:
        raise ValueError("receipt must carry at least one measurement")
    rows = []
    findings = []
    disposition = ACCEPT
    for name in sorted(measurements):
        row = assess_measurement(_text("measurement name", name),
                                 measurements[name], reclean_factor)
        findings.extend(row["findings"])
        disposition = escalate(disposition, row["disposition"])
        rows.append(row)

    packaging = assess_packaging(receipt.get("packaging", {}))
    findings.extend(packaging["findings"])
    disposition = escalate(disposition, packaging["disposition"])

    transport = assess_transport(
        receipt.get("transport", {}), item.get("transport_limits", {})
    )
    findings.extend(transport["findings"])
    disposition = escalate(disposition, transport["disposition"])

    if required_class is not None:
        if not isinstance(required_class, int) or isinstance(required_class, bool):
            raise ValueError("required_area_class must be an integer class")
        inspection_class = receipt.get("inspection_area_class")
        if inspection_class is None:
            findings.append("inspection-area-class-not-recorded")
            disposition = escalate(disposition, ACCEPT_AFTER_REVERIFICATION)
        else:
            if not isinstance(inspection_class, int) or isinstance(
                inspection_class, bool
            ):
                raise ValueError("inspection_area_class must be an integer class")
            if inspection_class > required_class:
                findings.append("receipt-opened-in-an-area-dirtier-than-the-item-needs")
                disposition = escalate(disposition, RECLEAN_AND_REVERIFY)

    measured_rows = [row for row in rows if row["consumed_fraction"] is not None]
    worst = None
    if measured_rows:
        worst = max(measured_rows, key=lambda r: r["consumed_fraction"])
    return {
        "item_id": item_id,
        "measurements": rows,
        "packaging": packaging,
        "transport": transport,
        "worst_measurement": worst["name"] if worst else None,
        "worst_consumed_fraction": worst["consumed_fraction"] if worst else None,
        "findings": findings,
        "disposition": disposition,
        "accepted_as_is": disposition == ACCEPT,
        "clear": not findings,
    }
