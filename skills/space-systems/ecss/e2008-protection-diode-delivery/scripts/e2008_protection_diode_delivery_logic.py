"""Dispatch of ordered protection diodes with their required documentation.

Anchor: ECSS-E-ST-20-08C clause 9.9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Two arms have to close before a protection diode shipment leaves, and
grading one of them is the failure this check exists to catch.

    hardware arm        the diodes themselves: each one drawn from a lot,
                        each one carrying a function and a reverse-voltage
                        rating band, each one either clean, clean only
                        because a concession was accepted, or held
    documentation arm   the document SET the lot owes. Not one file: a
                        lot data package, the screening test data and a
                        declaration of conformance, each with its own
                        release state. A diode whose lot is short one of
                        them is a diode nobody downstream can trace

A count that reaches the ordered quantity therefore proves nothing on its
own. The quantity can be met entirely by diodes drawn from a lot that
never released its screening data, and a pure counting check passes it.

Protection diodes add a substitution question a cell-level delivery never
has to answer, and it has two different shapes:

    function        categorical. A bypass diode and a blocking diode do
                    different jobs in the array, so one never stands in
                    for the other. No order permission unlocks this; a
                    function mismatch is refused outright.
    rating band     a ladder. A line asking for a lower reverse-voltage
                    band may be filled from a higher band when the order
                    permits the upgrade, because the customer receives
                    more margin than was bought. It may never be filled
                    from a lower band, which is a downgrade of the part
                    dressed up as a substitution.

Allocation is therefore ordered: the exact rating band is spent first and
only then a permitted upgrade, so a high-band diode is not consumed by a
low line while a high line goes short.

What is left over is not slack. A shippable diode that no order line asks
for is surplus the shipment was never asked to carry, and it is reported
rather than quietly loaded.

Finally a partial dispatch is a decision, not an accident. The order
declares the fraction of a line below which a partial delivery is refused
outright; a line that clears that floor without being complete still goes,
and is still named as partial.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "CONCESSION_STATES",
    "DIODE_DISPOSITIONS",
    "DIODE_FUNCTIONS",
    "DISPATCH_HELD",
    "DISPATCH_RELEASABLE",
    "DOCUMENT_STATES",
    "FILL_TOLERANCE",
    "HELD",
    "LINE_COMPLETE",
    "LINE_PARTIAL",
    "LINE_REFUSED",
    "RATING_LADDER",
    "REQUIRED_LOT_DOCUMENTS",
    "SHIPPABLE",
    "SHIPPABLE_ON_CONCESSION",
    "allocate_diodes_to_lines",
    "assess_diode",
    "assess_diodes",
    "assess_lot_documents",
    "evaluate_delivery",
    "lot_document_index",
    "normalize_function",
    "normalize_rating",
    "rating_rank",
    "validate_order",
    "validate_order_line",
]

# Categorical. A bypass diode never stands in for a blocking diode and
# the reverse is equally refused; the two sit in different places in the
# array and answer different faults.
DIODE_FUNCTIONS = ("bypass", "blocking")

# Lowest reverse-voltage band first. Rank is the index, so a higher rank
# carries more standoff margin and an upgrade is a move up this ladder.
RATING_LADDER = ("rating-band-low", "rating-band-medium", "rating-band-high")

# The documentation arm is a SET, not a flag. Every one of these has to
# be released for the lot before a diode drawn from it may travel.
REQUIRED_LOT_DOCUMENTS = (
    "lot-data-package",
    "screening-test-data",
    "declaration-of-conformance",
)

DOCUMENT_STATES = ("released", "draft", "withdrawn")

CONCESSION_STATES = ("accepted", "submitted", "rejected")

SHIPPABLE = "shippable"
SHIPPABLE_ON_CONCESSION = "shippable-on-accepted-concession"
HELD = "held"

DIODE_DISPOSITIONS = (SHIPPABLE, SHIPPABLE_ON_CONCESSION, HELD)

LINE_COMPLETE = "line-complete"
LINE_PARTIAL = "line-partial-within-floor"
LINE_REFUSED = "line-below-partial-delivery-floor"

DISPATCH_RELEASABLE = "dispatch-releasable"
DISPATCH_HELD = "dispatch-held"

# A fill fraction is a ratio of two small integers, but the declared floor
# arrives as a decimal literal. Comparing them without a tolerance makes a
# line that exactly meets its floor pass on one platform and fail on
# another, so the comparison absorbs representation error by name.
FILL_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _count(value, label):
    """Return a positive integer count, refusing a bool or a float."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def normalize_function(value, label="diode function"):
    """Return a recognized protection diode function."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = value.strip().lower()
    if cleaned not in DIODE_FUNCTIONS:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, value, ", ".join(DIODE_FUNCTIONS))
        )
    return cleaned


def normalize_rating(value, label="rating band"):
    """Return a recognized reverse-voltage rating band."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = value.strip().lower()
    if cleaned not in RATING_LADDER:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, value, ", ".join(RATING_LADDER))
        )
    return cleaned


def rating_rank(value):
    """Return the ladder position of a rating band; higher carries more margin."""
    return RATING_LADDER.index(normalize_rating(value))


def validate_order_line(line, label="order line"):
    """Return one validated order line."""
    if not isinstance(line, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("line_id", "function", "rating_band", "ordered_count"):
        if key not in line:
            raise ValueError("%s missing required key '%s'" % (label, key))
    allow = line.get("allow_rating_upgrade", False)
    if not isinstance(allow, bool):
        raise ValueError(
            "%s allow_rating_upgrade must be a boolean, got %r" % (label, allow)
        )
    return {
        "line_id": _identifier(line["line_id"], "%s line_id" % label),
        "function": normalize_function(line["function"], "%s function" % label),
        "rating_band": normalize_rating(
            line["rating_band"], "%s rating_band" % label
        ),
        "ordered_count": _count(line["ordered_count"], "%s ordered_count" % label),
        "allow_rating_upgrade": allow,
    }


def validate_order(order):
    """Return the validated order, with its partial-delivery floor."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    for key in ("order_id", "lines", "partial_delivery_floor"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    floor = order["partial_delivery_floor"]
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("partial_delivery_floor must be a number, got %r" % (floor,))
    floor = float(floor)
    if not 0.0 <= floor <= 1.0:
        raise ValueError(
            "partial_delivery_floor must lie between 0 and 1, got %r" % (floor,)
        )
    lines = order["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("order must carry at least one line")
    validated = []
    seen = set()
    for index, line in enumerate(lines):
        entry = validate_order_line(line, "order line[%d]" % index)
        if entry["line_id"] in seen:
            raise ValueError("order line %s appears twice" % entry["line_id"])
        seen.add(entry["line_id"])
        validated.append(entry)
    return {
        "order_id": _identifier(order["order_id"], "order_id"),
        "lines": tuple(validated),
        "partial_delivery_floor": floor,
    }


def assess_lot_documents(lot, label="lot"):
    """Grade one lot's document set on release state, not on presence.

    A document listed in the register with its release still pending is a
    document that is not released. Reading the register for the entry
    rather than for the state is the quiet way this arm goes green.
    """
    if not isinstance(lot, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("lot_id", "documents"):
        if key not in lot:
            raise ValueError("%s missing required key '%s'" % (label, key))
    lot_id = _identifier(lot["lot_id"], "%s lot_id" % label)
    documents = lot["documents"]
    if not isinstance(documents, (list, tuple)):
        raise ValueError("lot %s documents must be a sequence" % lot_id)
    states = {}
    for index, doc in enumerate(documents):
        if not isinstance(doc, dict):
            raise ValueError("lot %s documents[%d] must be a mapping" % (lot_id, index))
        for key in ("document_id", "state"):
            if key not in doc:
                raise ValueError(
                    "lot %s documents[%d] missing key '%s'" % (lot_id, index, key)
                )
        doc_id = _identifier(
            doc["document_id"], "lot %s documents[%d] document_id" % (lot_id, index)
        ).lower()
        if doc_id not in REQUIRED_LOT_DOCUMENTS:
            raise ValueError(
                "lot %s lists unrecognized document %r; recognized: %s"
                % (lot_id, doc["document_id"], ", ".join(REQUIRED_LOT_DOCUMENTS))
            )
        if doc_id in states:
            raise ValueError("lot %s lists document %s twice" % (lot_id, doc_id))
        state = doc["state"]
        if not isinstance(state, str) or state.strip().lower() not in DOCUMENT_STATES:
            raise ValueError(
                "lot %s document %s state must be one of %s, got %r"
                % (lot_id, doc_id, ", ".join(DOCUMENT_STATES), state)
            )
        states[doc_id] = state.strip().lower()

    released = tuple(d for d in REQUIRED_LOT_DOCUMENTS if states.get(d) == "released")
    missing = tuple(d for d in REQUIRED_LOT_DOCUMENTS if states.get(d) != "released")
    absent = tuple(d for d in REQUIRED_LOT_DOCUMENTS if d not in states)
    unreleased = tuple(
        d for d in REQUIRED_LOT_DOCUMENTS if d in states and states[d] != "released"
    )
    return {
        "lot_id": lot_id,
        "document_states": dict(states),
        "released_documents": released,
        "missing_documents": missing,
        "absent_documents": absent,
        "unreleased_documents": unreleased,
        "document_set_complete": not missing,
    }


def lot_document_index(lots):
    """Return a lot id to document assessment mapping, refusing duplicates."""
    if not isinstance(lots, (list, tuple)):
        raise ValueError("lots must be a sequence of lot document mappings")
    index = {}
    for position, lot in enumerate(lots):
        assessment = assess_lot_documents(lot, "lots[%d]" % position)
        if assessment["lot_id"] in index:
            raise ValueError("lot %s has two document entries" % assessment["lot_id"])
        index[assessment["lot_id"]] = assessment
    return index


def _concession(value, label):
    """Return a validated concession, or None when none is offered."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping or None" % label)
    for key in ("reference", "state"):
        if key not in value:
            raise ValueError("%s missing key '%s'" % (label, key))
    state = value["state"]
    if not isinstance(state, str) or state.strip().lower() not in CONCESSION_STATES:
        raise ValueError(
            "%s state must be one of %s, got %r"
            % (label, ", ".join(CONCESSION_STATES), state)
        )
    return {
        "reference": _identifier(value["reference"], "%s reference" % label),
        "state": state.strip().lower(),
    }


def assess_diode(diode, lot_index):
    """Disposition one protection diode against both arms of the dispatch."""
    if not isinstance(diode, dict):
        raise ValueError("diode must be a mapping")
    if not isinstance(lot_index, dict):
        raise ValueError("lot_index must be a mapping of lot id to assessment")
    for key in ("diode_id", "lot_id", "function", "rating_band", "nonconformance_open"):
        if key not in diode:
            raise ValueError("diode missing required key '%s'" % key)
    diode_id = _identifier(diode["diode_id"], "diode_id")
    lot_id = _identifier(diode["lot_id"], "lot_id")
    function = normalize_function(diode["function"], "diode %s function" % diode_id)
    rating = normalize_rating(
        diode["rating_band"], "diode %s rating_band" % diode_id
    )
    open_ncr = diode["nonconformance_open"]
    if not isinstance(open_ncr, bool):
        raise ValueError(
            "diode %s nonconformance_open must be a boolean, got %r"
            % (diode_id, open_ncr)
        )
    concession = _concession(
        diode.get("concession"), "diode %s concession" % diode_id
    )

    reasons = []
    lot = lot_index.get(lot_id)
    if lot is None:
        documented = False
        missing = REQUIRED_LOT_DOCUMENTS
        reasons.append(
            "diode %s names lot %s, which has no document register entry at all"
            % (diode_id, lot_id)
        )
    else:
        documented = lot["document_set_complete"]
        missing = lot["missing_documents"]
        if not documented:
            reasons.append(
                "diode %s comes from lot %s, whose document set is short %s, so "
                "nothing downstream can trace it"
                % (diode_id, lot_id, ", ".join(missing))
            )

    on_concession = False
    if open_ncr:
        if concession is None:
            reasons.append(
                "diode %s carries an open nonconformance and no concession" % diode_id
            )
        elif concession["state"] != "accepted":
            reasons.append(
                "diode %s carries an open nonconformance and concession %s is '%s' "
                "rather than accepted"
                % (diode_id, concession["reference"], concession["state"])
            )
        else:
            on_concession = True

    if reasons:
        disposition = HELD
    elif on_concession:
        disposition = SHIPPABLE_ON_CONCESSION
    else:
        disposition = SHIPPABLE

    return {
        "diode_id": diode_id,
        "lot_id": lot_id,
        "function": function,
        "rating_band": rating,
        "rating_rank": RATING_LADDER.index(rating),
        "documentation_complete": documented,
        "missing_documents": tuple(missing),
        "concession": concession,
        "disposition": disposition,
        "shippable": disposition != HELD,
        "reasons": tuple(reasons),
    }


def assess_diodes(diodes, lot_index):
    """Disposition every offered diode, refusing a repeated diode id."""
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("diodes must be a non-empty sequence of offered diodes")
    seen = set()
    out = []
    for diode in diodes:
        result = assess_diode(diode, lot_index)
        if result["diode_id"] in seen:
            raise ValueError("diode %s is offered twice" % result["diode_id"])
        seen.add(result["diode_id"])
        out.append(result)
    return tuple(out)


def allocate_diodes_to_lines(assessed, order):
    """Fill each order line from the shippable diodes, exact band first.

    The function has to match exactly: no order permission makes a bypass
    diode answer for a blocking one. Within the matching function, the
    exact rating band is spent before any permitted upgrade, so a
    higher-band diode is not consumed by a lower line while a higher line
    goes short. A lower band never fills a higher line.
    """
    validated = validate_order(order)
    pool = [d for d in assessed if d["shippable"]]
    taken = set()
    lines = []
    for line in validated["lines"]:
        wanted = line["ordered_count"]
        line_rank = RATING_LADDER.index(line["rating_band"])
        allocated = []
        candidates = sorted(
            (d for d in pool if d["diode_id"] not in taken),
            key=lambda d: (d["rating_rank"], d["diode_id"]),
        )
        for diode in candidates:
            if len(allocated) >= wanted:
                break
            if diode["function"] != line["function"]:
                continue
            if diode["rating_rank"] == line_rank:
                allocated.append(diode)
                taken.add(diode["diode_id"])
        if len(allocated) < wanted and line["allow_rating_upgrade"]:
            for diode in candidates:
                if len(allocated) >= wanted:
                    break
                if diode["diode_id"] in taken:
                    continue
                if diode["function"] != line["function"]:
                    continue
                if diode["rating_rank"] > line_rank:
                    allocated.append(diode)
                    taken.add(diode["diode_id"])
        shipped = len(allocated)
        fill = shipped / float(wanted)
        substituted = tuple(
            d["diode_id"] for d in allocated if d["rating_rank"] > line_rank
        )
        if shipped >= wanted:
            state = LINE_COMPLETE
        elif fill + FILL_TOLERANCE >= validated["partial_delivery_floor"]:
            state = LINE_PARTIAL
        else:
            state = LINE_REFUSED
        lines.append(
            {
                "line_id": line["line_id"],
                "function": line["function"],
                "rating_band": line["rating_band"],
                "ordered_count": wanted,
                "shipped_count": shipped,
                "short_count": max(0, wanted - shipped),
                "fill_fraction": fill,
                "substituted_diode_ids": substituted,
                "allocated_diode_ids": tuple(d["diode_id"] for d in allocated),
                "state": state,
                "accepted": state != LINE_REFUSED,
            }
        )
    surplus = tuple(d["diode_id"] for d in pool if d["diode_id"] not in taken)
    return {"lines": tuple(lines), "surplus_diode_ids": surplus}


def evaluate_delivery(spec):
    """Run the clause 9.9 dispatch check over one offered diode shipment.

    spec keys: shipment_id, order, lots, diodes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("shipment_id", "order", "lots", "diodes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    shipment_id = _identifier(spec["shipment_id"], "shipment_id")
    order = validate_order(spec["order"])
    lot_index = lot_document_index(spec["lots"])
    assessed = assess_diodes(spec["diodes"], lot_index)
    allocation = allocate_diodes_to_lines(assessed, order)

    findings = []
    for diode in assessed:
        findings.extend(diode["reasons"])
    for line in allocation["lines"]:
        if line["state"] == LINE_REFUSED:
            findings.append(
                "order line %s shipped %d of %d ordered diodes, below the declared "
                "partial-delivery floor"
                % (line["line_id"], line["shipped_count"], line["ordered_count"])
            )
    for diode_id in allocation["surplus_diode_ids"]:
        findings.append(
            "shipment %s offers diode %s, which no line of order %s asks for"
            % (shipment_id, diode_id, order["order_id"])
        )

    ordered_total = sum(l["ordered_count"] for l in allocation["lines"])
    shipped_total = sum(l["shipped_count"] for l in allocation["lines"])
    incomplete_lots = tuple(
        lot_id
        for lot_id in sorted(lot_index)
        if not lot_index[lot_id]["document_set_complete"]
    )
    return {
        "shipment_id": shipment_id,
        "order_id": order["order_id"],
        "lots": lot_index,
        "incomplete_lot_ids": incomplete_lots,
        "diodes": assessed,
        "lines": allocation["lines"],
        "surplus_diode_ids": allocation["surplus_diode_ids"],
        "held_diode_ids": tuple(
            d["diode_id"] for d in assessed if not d["shippable"]
        ),
        "concession_diode_ids": tuple(
            d["diode_id"] for d in assessed
            if d["disposition"] == SHIPPABLE_ON_CONCESSION
        ),
        "substituted_diode_ids": tuple(
            sorted(
                d
                for line in allocation["lines"]
                for d in line["substituted_diode_ids"]
            )
        ),
        "ordered_total": ordered_total,
        "shipped_total": shipped_total,
        "shipment_fill_fraction": shipped_total / float(ordered_total),
        "partial": shipped_total < ordered_total,
        "findings": findings,
        "verdict": DISPATCH_RELEASABLE if not findings else DISPATCH_HELD,
        "accepted": not findings,
    }
