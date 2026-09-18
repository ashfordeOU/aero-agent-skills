"""Procurement grading for passive elements delivered as bare chips.

Anchor: ECSS-Q-ST-60-05C clause 8.2 (purchase of passive chip elements --
chip resistors, chip capacitors, chip inductors bought in bare, unencapsulated
form for hybrid assembly). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the element type on the order line to one the clause covers, so the
   type-specific ordering data set can be picked.
2. Merge that type-specific set with the data set every bare passive chip
   carries, and name what the order line failed to declare.
3. Check the termination metallization against the attachment method the
   assembly will use, because the pair -- not either alone -- decides whether
   the joint is a metallurgical problem.
4. Form the applied-to-rated stress ratio of the element and compare it with
   the derating limit its type carries.
5. Confirm the delivery is drawn from one production lot, since a split
   delivery breaks the traceability the rest of the order line rests on.
6. Combine the four checks into a disposition -- release, hold or reject --
   and report the governing reason.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "BASELINE_DATA_ITEMS",
    "ELEMENT_TYPE_DATA_ITEMS",
    "DERATING_LIMITS",
    "DISPOSITION_ORDER",
    "normalize_element_type",
    "required_data_items",
    "missing_data_items",
    "derating_limit",
    "stress_ratio",
    "assess_derating",
    "assess_termination",
    "assess_lot_structure",
    "assess_order_line",
    "summarize_order",
]

# Stress ratios are a division of two declared numbers: an element rated at
# exactly twice its applied stress must not fall on the wrong side of a 0.5
# limit through representation error alone.
RATIO_TOLERANCE = 1e-9

# Carried by every bare passive chip, whatever the element does.
BASELINE_DATA_ITEMS = (
    "manufacturer-part-identification",
    "procurement-specification",
    "lot-identification",
    "termination-metallization",
    "quality-level",
)

# Added on top of the baseline by the element type.
ELEMENT_TYPE_DATA_ITEMS = {
    "chip-resistor": (
        "resistive-film-system",
        "resistance-tolerance",
        "trim-method",
    ),
    "chip-capacitor": (
        "dielectric-category",
        "capacitance-tolerance",
        "destructive-physical-analysis",
    ),
    "chip-inductor": (
        "core-material",
        "inductance-tolerance",
        "self-resonant-frequency",
    ),
}

# Fraction of the rated quantity the applied stress may reach.
DERATING_LIMITS = {
    "chip-resistor": 0.50,
    "chip-capacitor": 0.60,
    "chip-inductor": 0.70,
}

# Worst disposition wins when an order line collects several findings.
DISPOSITION_ORDER = ("release", "hold", "reject")

# Termination/attachment pairs that need a barrier or a different finish.
# value is the reason the pair is not taken as delivered.
_TERMINATION_CONFLICTS = {
    ("gold", "solder"): "gold termination dissolves into tin-bearing solder and embrittles the joint",
    ("palladium-silver", "gold-wire-bond"): "silver-bearing termination is not a gold-wire bonding surface",
    ("tin", "gold-wire-bond"): "tin termination is a solder finish, not a bonding surface",
    ("aluminium", "solder"): "aluminium termination cannot be soldered without a plated overlay",
    ("silver", "solder"): "unbarriered silver termination leaches into the solder joint",
}

_TERMINATIONS = ("gold", "palladium-silver", "silver", "tin", "aluminium", "nickel-barrier-tin")
_ATTACH_METHODS = ("solder", "conductive-adhesive", "gold-wire-bond", "aluminium-wire-bond")


def _require_text(value, label):
    """Return a lowercased, stripped token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def _require_positive(value, label):
    """Return a finite positive float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def normalize_element_type(element_type):
    """Return the canonical element type, raising on one the clause misses."""
    token = _require_text(element_type, "element_type")
    token = token.replace("_", "-").replace(" ", "-")
    aliases = {
        "resistor": "chip-resistor",
        "chip-resistors": "chip-resistor",
        "capacitor": "chip-capacitor",
        "chip-capacitors": "chip-capacitor",
        "inductor": "chip-inductor",
        "chip-inductors": "chip-inductor",
    }
    token = aliases.get(token, token)
    if token not in ELEMENT_TYPE_DATA_ITEMS:
        raise ValueError(
            "element type %r is not a passive chip type covered here (%s)"
            % (element_type, ", ".join(sorted(ELEMENT_TYPE_DATA_ITEMS)))
        )
    return token


def required_data_items(element_type):
    """Return the sorted ordering data items an order line for this type owes."""
    canonical = normalize_element_type(element_type)
    return tuple(sorted(set(BASELINE_DATA_ITEMS) | set(ELEMENT_TYPE_DATA_ITEMS[canonical])))


def missing_data_items(element_type, declared_items):
    """Return the sorted required items the order line did not declare."""
    if not isinstance(declared_items, (list, tuple, set, frozenset)):
        raise ValueError("declared_items must be a sequence of item names")
    declared = set()
    for item in declared_items:
        declared.add(_require_text(item, "declared data item").replace("_", "-").replace(" ", "-"))
    return tuple(sorted(set(required_data_items(element_type)) - declared))


def derating_limit(element_type):
    """Return the applied-to-rated fraction this element type may reach."""
    return DERATING_LIMITS[normalize_element_type(element_type)]


def stress_ratio(applied, rated):
    """Return the applied-to-rated stress ratio of the element."""
    applied_value = _require_positive(applied, "applied")
    rated_value = _require_positive(rated, "rated")
    return applied_value / rated_value


def assess_derating(element_type, applied, rated):
    """Compare the stress ratio with the derating limit of the element type."""
    limit = derating_limit(element_type)
    ratio = stress_ratio(applied, rated)
    compliant = ratio < limit or math.isclose(ratio, limit, rel_tol=0.0, abs_tol=RATIO_TOLERANCE)
    return {
        "element_type": normalize_element_type(element_type),
        "ratio": ratio,
        "limit": limit,
        "compliant": compliant,
        "finding": None
        if compliant
        else "applied stress reaches %.4f of rated, past the %.2f derating limit" % (ratio, limit),
    }


def assess_termination(termination, attach_method):
    """Judge the termination metallization against the attachment method."""
    finish = _require_text(termination, "termination").replace("_", "-").replace(" ", "-")
    method = _require_text(attach_method, "attach_method").replace("_", "-").replace(" ", "-")
    if finish not in _TERMINATIONS:
        raise ValueError(
            "termination %r is not a recognised chip finish (%s)"
            % (termination, ", ".join(_TERMINATIONS))
        )
    if method not in _ATTACH_METHODS:
        raise ValueError(
            "attach_method %r is not a recognised attachment (%s)"
            % (attach_method, ", ".join(_ATTACH_METHODS))
        )
    reason = _TERMINATION_CONFLICTS.get((finish, method))
    return {
        "termination": finish,
        "attach_method": method,
        "compatible": reason is None,
        "finding": None if reason is None else reason,
    }


def assess_lot_structure(lot_identifiers, quantity):
    """Confirm the delivered quantity comes from one identified production lot."""
    if not isinstance(lot_identifiers, (list, tuple)):
        raise ValueError("lot_identifiers must be a sequence")
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValueError("quantity must be an integer, got %r" % (quantity,))
    if quantity <= 0:
        raise ValueError("quantity must be positive, got %d" % quantity)
    seen = []
    for identifier in lot_identifiers:
        token = _require_text(identifier, "lot identifier")
        if token not in seen:
            seen.append(token)
    if not seen:
        return {
            "lot_count": 0,
            "quantity": quantity,
            "single_lot": False,
            "finding": "delivery carries no lot identifier, so no element is traceable",
        }
    if len(seen) > 1:
        return {
            "lot_count": len(seen),
            "quantity": quantity,
            "single_lot": False,
            "finding": "delivery is drawn from %d lots; one lot per delivery is the condition"
            % len(seen),
        }
    return {"lot_count": 1, "quantity": quantity, "single_lot": True, "finding": None}


def assess_order_line(line):
    """Grade one passive chip order line and return its disposition.

    line keys: element_type, declared_items, termination, attach_method,
    applied, rated, lot_identifiers, quantity.
    """
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping")
    for key in ("element_type", "declared_items", "termination", "attach_method",
                "applied", "rated", "lot_identifiers", "quantity"):
        if key not in line:
            raise ValueError("order line missing required key '%s'" % key)
    canonical = normalize_element_type(line["element_type"])
    missing = missing_data_items(canonical, line["declared_items"])
    derating = assess_derating(canonical, line["applied"], line["rated"])
    termination = assess_termination(line["termination"], line["attach_method"])
    lot = assess_lot_structure(line["lot_identifiers"], line["quantity"])

    findings = []
    disposition = "release"
    if missing:
        findings.append("ordering data not declared: %s" % ", ".join(missing))
        disposition = "hold"
    if not lot["single_lot"]:
        findings.append(lot["finding"])
        disposition = "reject"
    if not termination["compatible"]:
        findings.append(termination["finding"])
        disposition = "reject"
    if not derating["compliant"]:
        findings.append(derating["finding"])
        if disposition == "release":
            disposition = "hold"
    return {
        "element_type": canonical,
        "required_items": required_data_items(canonical),
        "missing_items": missing,
        "derating": derating,
        "termination": termination,
        "lot": lot,
        "disposition": disposition,
        "findings": tuple(findings),
        "governing_finding": findings[0] if findings else None,
    }


def summarize_order(lines):
    """Summarize a set of order lines and return the governing disposition."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence of order lines")
    results = [assess_order_line(line) for line in lines]
    counts = {name: 0 for name in DISPOSITION_ORDER}
    worst_index = 0
    for result in results:
        counts[result["disposition"]] += 1
        index = DISPOSITION_ORDER.index(result["disposition"])
        if index > worst_index:
            worst_index = index
    governing = None
    for result in results:
        if result["disposition"] == DISPOSITION_ORDER[worst_index] and result["governing_finding"]:
            governing = result["governing_finding"]
            break
    return {
        "lines": tuple(results),
        "counts": counts,
        "disposition": DISPOSITION_ORDER[worst_index],
        "governing_finding": governing,
        "releasable": DISPOSITION_ORDER[worst_index] == "release",
    }
