"""Incoming inspection on receipt of a highest-assurance commercial part lot.

Anchor: ECSS-Q-ST-60-13C clause 4.3.7 (inspection performed when a delivery of
commercial parts of the highest assurance category is received). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Reconcile the delivery against the purchase order: part number, date code
   and quantity. A substituted part number is a quarantine, not a discrepancy
   to be noted and passed on.
2. Size the external visual sample from the received quantity with an exact
   square-root plan, bounded by a declared floor and cap, so the sample is
   reproducible and never larger than the lot.
3. Judge the external visual findings against the sample's accept number.
4. Read the moisture barrier: bag seal integrity, the humidity indicator card
   against its limit, and the elapsed factory-floor exposure against the floor
   life of the declared moisture sensitivity level.
5. Check the documents that had to arrive with the parts, then dispose the
   delivery: released into bonded store only when every check holds, otherwise
   quarantined with every reason named.
"""

import math

__all__ = [
    "MSL_FLOOR_LIFE_HOURS",
    "REQUIRED_DOCUMENTS",
    "RECEIPT_TOLERANCE",
    "DEFAULT_SAMPLE_FLOOR",
    "DEFAULT_SAMPLE_CAP",
    "reconcile_part_number",
    "quantity_discrepancy",
    "visual_sample_size",
    "visual_verdict",
    "humidity_indicator_verdict",
    "floor_life_status",
    "missing_documents",
    "assess_incoming_inspection",
]

# Factory-floor life of a dry-packed lot, in hours, by moisture sensitivity
# level. Level 1 needs no dry storage; level 6 has to be baked before use, so
# any exposure at all puts the lot outside its floor life.
MSL_FLOOR_LIFE_HOURS = {
    "1": float("inf"),
    "2": 8760.0,
    "2a": 672.0,
    "3": 168.0,
    "4": 72.0,
    "5": 48.0,
    "5a": 24.0,
    "6": 0.0,
}

# The paperwork that has to be in the box, not promised to follow.
REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "lot-acceptance-data",
    "screening-data",
    "date-code-traceability",
)

# Humidity and floor-life comparisons land on their limit exactly in the normal
# case; absorb representation error here rather than by moving the limit.
RECEIPT_TOLERANCE = 1e-9

DEFAULT_SAMPLE_FLOOR = 5
DEFAULT_SAMPLE_CAP = 125


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value, allow_infinite=False):
    """Return value as a float, raising unless it is a real number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not allow_infinite and not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def reconcile_part_number(ordered, received):
    """Return the part-number reconciliation between order and delivery.

    Comparison ignores case and surrounding space only; an internal difference
    is a substituted part, which is what this check exists to catch.
    """
    want = _text("ordered part number", ordered)
    got = _text("received part number", received)
    return {
        "ordered": want,
        "received": got,
        "matches": want.lower() == got.lower(),
    }


def quantity_discrepancy(ordered, received):
    """Return the quantity reconciliation between order and delivery."""
    want = _count("ordered quantity", ordered)
    got = _count("received quantity", received)
    if want < 1:
        raise ValueError("ordered quantity must be at least 1, got %d" % want)
    return {
        "ordered": want,
        "received": got,
        "shortfall": max(0, want - got),
        "overage": max(0, got - want),
        "matches": want == got,
    }


def visual_sample_size(lot_size, floor=DEFAULT_SAMPLE_FLOOR, cap=DEFAULT_SAMPLE_CAP):
    """Return the external visual sample size for a received lot.

    Exact ceiling of the square root of the lot size, raised to the declared
    floor, limited by the declared cap and never larger than the lot itself.
    Integer arithmetic throughout, so the same lot gives the same sample on
    every platform.
    """
    lot = _count("lot_size", lot_size)
    low = _count("floor", floor)
    high = _count("cap", cap)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if low < 1:
        raise ValueError("floor must be at least 1, got %d" % low)
    if high < low:
        raise ValueError("cap %d is below floor %d" % (high, low))
    root = math.isqrt(lot)
    if root * root < lot:
        root += 1
    size = max(root, low)
    size = min(size, high)
    return min(size, lot)


def visual_verdict(sample_size, defects, accept_number=0):
    """Return the external visual inspection verdict for the drawn sample."""
    sample = _count("sample_size", sample_size)
    found = _count("defects", defects)
    accept = _count("accept_number", accept_number)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    if found > sample:
        raise ValueError("defects %d exceed the sample size %d" % (found, sample))
    return {
        "sample_size": sample,
        "defects": found,
        "accept_number": accept,
        "defect_fraction": found / sample,
        "accepted": found <= accept,
    }


def humidity_indicator_verdict(reading_percent, limit_percent):
    """Return the dry-pack humidity indicator card verdict.

    A card reading exactly at its limit is admissible; the tolerance absorbs
    representation error only and does not move the limit.
    """
    reading = _real("reading_percent", reading_percent)
    limit = _real("limit_percent", limit_percent)
    for label, value in (("reading_percent", reading), ("limit_percent", limit)):
        if value < 0.0 or value > 100.0:
            raise ValueError("%s must lie in 0..100, got %g" % (label, value))
    within = reading < limit or math.isclose(
        reading, limit, rel_tol=0.0, abs_tol=RECEIPT_TOLERANCE
    )
    return {
        "reading_percent": reading,
        "limit_percent": limit,
        "within_limit": within,
        "margin_percent": limit - reading,
    }


def floor_life_status(msl, exposed_hours):
    """Return the factory-floor life status of a dry-packed delivery."""
    if not isinstance(msl, str):
        raise ValueError("msl must be a moisture sensitivity level string, got %r" % (msl,))
    key = msl.strip().lower()
    if key not in MSL_FLOOR_LIFE_HOURS:
        raise ValueError(
            "unknown moisture sensitivity level %r; known levels are %s"
            % (msl, ", ".join(sorted(MSL_FLOOR_LIFE_HOURS)))
        )
    exposed = _real("exposed_hours", exposed_hours)
    if exposed < 0.0:
        raise ValueError("exposed_hours must be non-negative, got %g" % exposed)
    limit = MSL_FLOOR_LIFE_HOURS[key]
    if math.isinf(limit):
        within = True
        remaining = float("inf")
    else:
        within = exposed < limit or math.isclose(
            exposed, limit, rel_tol=0.0, abs_tol=RECEIPT_TOLERANCE
        )
        remaining = limit - exposed
    return {
        "msl": key,
        "floor_life_hours": limit,
        "exposed_hours": exposed,
        "remaining_hours": remaining,
        "within_floor_life": within,
    }


def missing_documents(documents, required=REQUIRED_DOCUMENTS):
    """Return the required delivery documents absent or marked not-received."""
    if isinstance(documents, (list, tuple, set, frozenset)):
        documents = {str(item): True for item in documents}
    if not isinstance(documents, dict):
        raise ValueError("documents must be a mapping or a sequence of document names")
    present = {}
    for key, value in documents.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("document names must be non-empty strings, got %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("documents['%s'] must be True or False" % key.strip())
        present[key.strip().lower()] = value
    absent = []
    for item in required:
        if not present.get(item.strip().lower(), False):
            absent.append(item.strip().lower())
    return absent


def assess_incoming_inspection(spec):
    """Run the full clause 4.3.7 incoming inspection of one received delivery.

    spec keys: ordered_part_number, received_part_number, ordered_quantity,
    received_quantity, date_code_ordered, date_code_received, bag_seal_intact,
    humidity_reading_percent, humidity_limit_percent, msl, exposed_hours,
    documents, visual_defects, and optional accept_number, sample_floor and
    sample_cap.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "ordered_part_number",
        "received_part_number",
        "ordered_quantity",
        "received_quantity",
        "date_code_ordered",
        "date_code_received",
        "bag_seal_intact",
        "humidity_reading_percent",
        "humidity_limit_percent",
        "msl",
        "exposed_hours",
        "documents",
        "visual_defects",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    part = reconcile_part_number(spec["ordered_part_number"], spec["received_part_number"])
    quantity = quantity_discrepancy(spec["ordered_quantity"], spec["received_quantity"])
    want_code = _text("date_code_ordered", spec["date_code_ordered"])
    got_code = _text("date_code_received", spec["date_code_received"])
    date_code_matches = want_code == got_code
    seal = spec["bag_seal_intact"]
    if not isinstance(seal, bool):
        raise ValueError("bag_seal_intact must be True or False")
    if quantity["received"] < 1:
        raise ValueError("received_quantity must be at least 1 to inspect a delivery")
    sample = visual_sample_size(
        quantity["received"],
        spec.get("sample_floor", DEFAULT_SAMPLE_FLOOR),
        spec.get("sample_cap", DEFAULT_SAMPLE_CAP),
    )
    visual = visual_verdict(sample, spec["visual_defects"], spec.get("accept_number", 0))
    humidity = humidity_indicator_verdict(
        spec["humidity_reading_percent"], spec["humidity_limit_percent"]
    )
    floor_life = floor_life_status(spec["msl"], spec["exposed_hours"])
    absent = missing_documents(spec["documents"])
    findings = []
    if not part["matches"]:
        findings.append(
            "part number received '%s' is not the ordered '%s'" % (part["received"], part["ordered"])
        )
    if quantity["shortfall"]:
        findings.append("delivery short by %d unit(s)" % quantity["shortfall"])
    if quantity["overage"]:
        findings.append("delivery over by %d unit(s)" % quantity["overage"])
    if not date_code_matches:
        findings.append(
            "date code received '%s' is not the ordered '%s'" % (got_code, want_code)
        )
    if not seal:
        findings.append("moisture barrier bag seal was not intact on receipt")
    if not visual["accepted"]:
        findings.append(
            "%d external visual defect(s) in a sample of %d exceed the accept number %d"
            % (visual["defects"], visual["sample_size"], visual["accept_number"])
        )
    if not humidity["within_limit"]:
        findings.append(
            "humidity indicator read %.2f%% against a limit of %.2f%%"
            % (humidity["reading_percent"], humidity["limit_percent"])
        )
    if not floor_life["within_floor_life"]:
        findings.append(
            "exposure of %.2f h exceeds the level %s floor life of %.2f h"
            % (floor_life["exposed_hours"], floor_life["msl"], floor_life["floor_life_hours"])
        )
    if absent:
        findings.append("delivery documents not received: %s" % ", ".join(absent))
    accepted = not findings
    return {
        "part_number": part,
        "quantity": quantity,
        "date_code_matches": date_code_matches,
        "bag_seal_intact": seal,
        "visual": visual,
        "humidity": humidity,
        "floor_life": floor_life,
        "missing_documents": absent,
        "accepted": accepted,
        "disposition": "release-to-bonded-store" if accepted else "quarantine",
        "findings": findings,
    }
