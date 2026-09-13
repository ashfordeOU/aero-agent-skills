#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.4.2 -- interference safety margin demonstration
for critical circuits and electro-explosive device firing circuits.

Deterministic, offline, stdlib only. Clause 6.3.1.3 fixes what margin a
critical point owes; this module is the demonstration side of the same
programme: the evidence that the margin was actually shown, on the right
hardware, over the operating conditions that matter, with the induced
quantity converted onto the decibel scale by the law that quantity
obeys.

No verbatim standard text is reproduced; the clause is the anchor only.
"""

import math

# Circuit categories a demonstration can be run for. The firing circuit
# of an electro-explosive device is kept apart from the other critical
# circuits because both its demanded separation and the evidence it
# admits are different.
CIRCUIT_CATEGORIES = (
    "electro-explosive-device",
    "safety-critical",
    "mission-critical",
    "non-critical",
)

# Separation each category owes, in decibels. Project-tailorable through
# the ladder argument; the ordering is not.
DEFAULT_MARGIN_LADDER = {
    "electro-explosive-device": 20.0,
    "safety-critical": 6.0,
    "mission-critical": 6.0,
    "non-critical": 0.0,
}

# Evidence a demonstration can rest on.
EVIDENCE_KINDS = (
    "instrumented-measurement",
    "analysis",
    "similarity",
)

# Evidence each category admits. A firing circuit is measured on
# representative hardware; a paper argument does not demonstrate it.
ADMISSIBLE_EVIDENCE = {
    "electro-explosive-device": ("instrumented-measurement",),
    "safety-critical": ("instrumented-measurement", "analysis"),
    "mission-critical": ("instrumented-measurement", "analysis"),
    "non-critical": EVIDENCE_KINDS,
}

# Operating conditions the demonstration has to exercise per category.
MANDATED_CONDITIONS = {
    "electro-explosive-device": (
        "flight-transmitters-keyed",
        "launch-site-radiated-environment",
        "worst-case-harness-routing",
        "ground-support-equipment-connected",
    ),
    "safety-critical": (
        "flight-transmitters-keyed",
        "worst-case-harness-routing",
    ),
    "mission-critical": (
        "flight-transmitters-keyed",
        "worst-case-harness-routing",
    ),
    "non-critical": (),
}

# Decibel law per induced quantity: a field quantity (current, voltage)
# goes as twenty times the logarithm of the ratio, an energy quantity
# (power) as ten times.
QUANTITY_LAWS = {
    "current": 20.0,
    "voltage": 20.0,
    "power": 10.0,
}

# A demonstrated separation is a difference of decibel levels or a
# logarithm of a ratio; a case that is exactly on the demand in
# engineering terms can land a few units in the last place below it.
DB_TOLERANCE = 1e-9


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number (got %r)" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite (got %r)" % (label, value))
    return number


def _strictly_positive(value, label):
    number = _finite(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive (got %r)" % (label, value))
    return number


def required_margin_db(category, ladder=None):
    """Read the demanded separation for a circuit category, in decibels."""
    if category not in CIRCUIT_CATEGORIES:
        raise ValueError(
            "unknown circuit category %r (expected one of %s)"
            % (category, ", ".join(CIRCUIT_CATEGORIES))
        )
    table = DEFAULT_MARGIN_LADDER if ladder is None else ladder
    if not isinstance(table, dict):
        raise ValueError("margin ladder must be a mapping (got %r)" % (table,))
    if category not in table:
        raise ValueError("margin ladder does not cover category %r" % (category,))
    demand = _finite(table[category], "margin demand for %r" % category)
    if demand < 0.0:
        raise ValueError("margin demand for %r cannot be negative" % category)
    return demand


def mandated_conditions(category):
    """The operating conditions a demonstration for this category owes."""
    if category not in MANDATED_CONDITIONS:
        raise ValueError(
            "unknown circuit category %r (expected one of %s)"
            % (category, ", ".join(CIRCUIT_CATEGORIES))
        )
    return MANDATED_CONDITIONS[category]


def evidence_is_admissible(category, evidence_kind):
    """Whether this evidence kind can demonstrate this category at all."""
    if category not in ADMISSIBLE_EVIDENCE:
        raise ValueError(
            "unknown circuit category %r (expected one of %s)"
            % (category, ", ".join(CIRCUIT_CATEGORIES))
        )
    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(
            "unknown evidence kind %r (expected one of %s)"
            % (evidence_kind, ", ".join(EVIDENCE_KINDS))
        )
    return evidence_kind in ADMISSIBLE_EVIDENCE[category]


def derate_no_fire_threshold(no_fire_value, derating_factor):
    """Bring a declared no-fire value down to the demonstration value."""
    value = _strictly_positive(no_fire_value, "no-fire value")
    factor = _finite(derating_factor, "derating factor")
    if factor <= 0.0 or factor > 1.0:
        raise ValueError(
            "derating factor must lie in the half-open range 0..1 (got %r)"
            % (derating_factor,)
        )
    return value * factor


def bridgewire_no_fire_power(no_fire_current, bridgewire_resistance):
    """Convert a maximum no-fire current into the matching no-fire power."""
    current = _strictly_positive(no_fire_current, "no-fire current")
    resistance = _strictly_positive(bridgewire_resistance, "bridgewire resistance")
    return current * current * resistance


def margin_from_linear(threshold, induced, quantity):
    """Separation in decibels between a threshold and an induced level."""
    if quantity not in QUANTITY_LAWS:
        raise ValueError(
            "unknown induced quantity %r (expected one of %s)"
            % (quantity, ", ".join(sorted(QUANTITY_LAWS)))
        )
    top = _strictly_positive(threshold, "threshold level")
    bottom = _strictly_positive(induced, "induced level")
    return QUANTITY_LAWS[quantity] * math.log10(top / bottom)


def margin_from_levels(threshold_db, induced_db):
    """Separation when both levels already sit on the decibel scale."""
    top = _finite(threshold_db, "threshold level in decibels")
    bottom = _finite(induced_db, "induced level in decibels")
    return top - bottom


def meets_required_margin(margin_db, required_db):
    """Compare a demonstrated separation against the demand.

    The separation is a difference of decibel levels or the logarithm of
    a ratio, so a case that sits exactly on the demand in engineering
    terms can land a few units in the last place below it: 33.3 less
    13.3 yields 19.999999999999996, not 20. That representation error is
    absorbed here; the demanded separation itself is never lowered.
    """
    margin = _finite(margin_db, "demonstrated separation")
    demand = _finite(required_db, "demanded separation")
    if demand < 0.0:
        raise ValueError("demanded separation cannot be negative")
    if margin >= demand:
        return True
    return math.isclose(margin, demand, rel_tol=0.0, abs_tol=DB_TOLERANCE)


def normalise_demonstration(record):
    """Canonicalise one circuit demonstration record."""
    if not isinstance(record, dict):
        raise ValueError("demonstration record must be a mapping (got %r)" % (record,))
    ident = str(record.get("id", "")).strip()
    if not ident:
        raise ValueError("demonstration record needs a non-empty id")
    category = record.get("category")
    if category not in CIRCUIT_CATEGORIES:
        raise ValueError(
            "demonstration %r has unknown circuit category %r" % (ident, category)
        )
    evidence = record.get("evidence")
    if evidence not in EVIDENCE_KINDS:
        raise ValueError(
            "demonstration %r has unknown evidence kind %r" % (ident, evidence)
        )
    has_db = record.get("threshold_db") is not None
    has_linear = record.get("no_fire_value") is not None
    if has_db and has_linear:
        raise ValueError(
            "demonstration %r declares both a decibel threshold and a no-fire "
            "value; pick the scale the measurement was taken on" % ident
        )
    if not has_db and not has_linear:
        raise ValueError(
            "demonstration %r declares no threshold to measure against" % ident
        )
    quantity = None
    threshold = None
    threshold_db = None
    if has_linear:
        quantity = record.get("quantity")
        if quantity not in QUANTITY_LAWS:
            raise ValueError(
                "demonstration %r has unknown induced quantity %r" % (ident, quantity)
            )
        threshold = derate_no_fire_threshold(
            record.get("no_fire_value"), record.get("derating_factor", 1.0)
        )
    else:
        threshold_db = _finite(record.get("threshold_db"), "threshold of %r" % ident)
    raw_points = record.get("measurements")
    if raw_points is None:
        raise ValueError("demonstration %r carries no measurement list" % ident)
    points = []
    seen = set()
    for raw in raw_points:
        if not isinstance(raw, dict):
            raise ValueError(
                "demonstration %r has a measurement that is not a mapping" % ident
            )
        condition = str(raw.get("condition", "")).strip()
        if not condition:
            raise ValueError(
                "demonstration %r has a measurement with no operating condition" % ident
            )
        if condition in seen:
            raise ValueError(
                "demonstration %r repeats the operating condition %r" % (ident, condition)
            )
        seen.add(condition)
        if has_linear:
            induced = _strictly_positive(
                raw.get("induced"), "induced level of %r at %r" % (ident, condition)
            )
            points.append({"condition": condition, "induced": induced})
        else:
            induced_db = _finite(
                raw.get("induced_db"),
                "induced level of %r at %r" % (ident, condition),
            )
            points.append({"condition": condition, "induced_db": induced_db})
    return {
        "id": ident,
        "category": category,
        "evidence": evidence,
        "quantity": quantity,
        "threshold": threshold,
        "threshold_db": threshold_db,
        "measurements": points,
    }


def condition_margins(demonstration):
    """Separation demonstrated at each exercised operating condition."""
    margins = {}
    for point in demonstration["measurements"]:
        if demonstration["threshold_db"] is None:
            margins[point["condition"]] = margin_from_linear(
                demonstration["threshold"], point["induced"], demonstration["quantity"]
            )
        else:
            margins[point["condition"]] = margin_from_levels(
                demonstration["threshold_db"], point["induced_db"]
            )
    return margins


def governing_condition(margins):
    """The condition that governs: smallest separation, name as tie-break."""
    if not margins:
        raise ValueError("no demonstrated separation to govern")
    ordered = sorted(margins.items(), key=lambda item: (item[1], item[0]))
    return ordered[0][0], ordered[0][1]


def missing_conditions(demonstration):
    """Mandated operating conditions this demonstration never exercised."""
    exercised = set(point["condition"] for point in demonstration["measurements"])
    return [
        condition
        for condition in mandated_conditions(demonstration["category"])
        if condition not in exercised
    ]


def demonstrate_circuit(record, ladder=None):
    """Run the clause 6.4.2 demonstration check for one circuit."""
    demonstration = normalise_demonstration(record)
    demand = required_margin_db(demonstration["category"], ladder)
    findings = []
    if not evidence_is_admissible(demonstration["category"], demonstration["evidence"]):
        findings.append(
            "circuit %s is a %s circuit and cannot be demonstrated by %s evidence"
            % (demonstration["id"], demonstration["category"], demonstration["evidence"])
        )
    gaps = missing_conditions(demonstration)
    for gap in gaps:
        findings.append(
            "circuit %s was never exercised under %s" % (demonstration["id"], gap)
        )
    margins = condition_margins(demonstration)
    condition = None
    margin = None
    if not margins:
        if demand > 0.0:
            findings.append(
                "circuit %s demands %.1f dB and carries no demonstrated separation"
                % (demonstration["id"], demand)
            )
    else:
        condition, margin = governing_condition(margins)
        if demand > 0.0 and not meets_required_margin(margin, demand):
            findings.append(
                "circuit %s shows %.3f dB under %s, short of the %.1f dB demanded"
                % (demonstration["id"], margin, condition, demand)
            )
    return {
        "id": demonstration["id"],
        "category": demonstration["category"],
        "evidence": demonstration["evidence"],
        "required_margin_db": demand,
        "margins": margins,
        "governing_condition": condition,
        "governing_margin_db": margin,
        "missing_conditions": gaps,
        "findings": findings,
        "demonstrated": not findings,
    }


def review_demonstrations(records, ladder=None):
    """Aggregate the demonstration review over a set of circuits."""
    if records is None:
        raise ValueError("no demonstration records to review")
    results = []
    seen = set()
    for record in records:
        result = demonstrate_circuit(record, ladder)
        if result["id"] in seen:
            raise ValueError("duplicate circuit id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
    if not results:
        raise ValueError("no demonstration records to review")
    findings = []
    for result in sorted(results, key=lambda item: item["id"]):
        findings.extend(result["findings"])
    firing = [r for r in results if r["category"] == "electro-explosive-device"]
    return {
        "circuits": results,
        "findings": findings,
        "firing_circuit_count": len(firing),
        "worst_margin_db": min(
            (r["governing_margin_db"] for r in results if r["governing_margin_db"] is not None),
            default=None,
        ),
        "demonstrated": not findings,
    }
