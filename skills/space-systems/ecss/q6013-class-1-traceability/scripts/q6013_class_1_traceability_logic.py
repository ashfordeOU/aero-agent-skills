"""Lot-identity traceability from receipt through storage into assembly.

Anchor: ECSS-Q-ST-60-13C clause 4.5.4 (keeping the lot identity of a class 1
commercial EEE procurement traceable across its whole custody chain).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every custody event of one lot: a known event type, a positive
   quantity, a finite clock reading, and the board serial an installation needs.
2. Validate the chain as a whole: exactly one receipt, no event before it, no
   duplicated event identity.
3. Find the identity breaks: an event carrying no lot code, an event carrying a
   different lot code with no cross-reference to the original, and an event
   whose date code contradicts the receipt.
4. Reconcile the quantities: received against installed, scrapped and returned,
   with the remainder that should still be in stores.
5. Build the forward trace (lot to board serials) and the backward trace (board
   serial to lot), and refuse a serial the chain never installed onto.
6. Score identity completeness across the chain and compare it with the
   required level under a named tolerance.
"""

import math

__all__ = [
    "COMPLETENESS_TOLERANCE",
    "EVENT_TYPES",
    "CONSUMING_EVENTS",
    "validate_event",
    "validate_chain",
    "identity_breaks",
    "reconcile_quantities",
    "forward_trace",
    "backward_trace",
    "identity_completeness",
    "assess_traceability",
]

# Completeness is a ratio of counts turned into a float; an exactly complete
# chain must not fail its own threshold on a representation error.
COMPLETENESS_TOLERANCE = 1e-9

EVENT_TYPES = (
    "receipt",
    "incoming-inspection",
    "stores-in",
    "stores-out",
    "kitting",
    "assembly-install",
    "scrap",
    "return-to-supplier",
)

# Events that take parts permanently out of the received quantity.
CONSUMING_EVENTS = ("assembly-install", "scrap", "return-to-supplier")

_IDENTITY_FIELDS = ("lot_code", "date_code", "coc_reference")


def _text(value):
    """Return a stripped string, or None when the value is absent or blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("identity fields must be strings or None, got %r" % (value,))
    stripped = value.strip()
    return stripped or None


def validate_event(event, index=0):
    """Return a normalised custody event."""
    if not isinstance(event, dict):
        raise ValueError("event[%d] must be a mapping" % index)
    for key in ("event_id", "type", "timestamp_h", "quantity"):
        if key not in event:
            raise ValueError("event[%d] missing required key '%s'" % (index, key))

    event_id = event["event_id"]
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event[%d]['event_id'] must be a non-empty string" % index)

    event_type = event["type"]
    if event_type not in EVENT_TYPES:
        raise ValueError(
            "event[%d]['type'] must be one of %s, got %r"
            % (index, list(EVENT_TYPES), event_type)
        )

    timestamp = event["timestamp_h"]
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        raise ValueError("event[%d]['timestamp_h'] must be a real number" % index)
    timestamp = float(timestamp)
    if not math.isfinite(timestamp) or timestamp < 0.0:
        raise ValueError(
            "event[%d]['timestamp_h'] must be finite and non-negative" % index
        )

    quantity = event["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("event[%d]['quantity'] must be a positive integer" % index)

    board_serial = _text(event.get("board_serial"))
    if event_type == "assembly-install" and not board_serial:
        raise ValueError(
            "event[%d] is an assembly-install with no board_serial" % index
        )
    if event_type != "assembly-install" and board_serial:
        raise ValueError(
            "event[%d] carries a board_serial but is not an assembly-install" % index
        )

    return {
        "event_id": event_id.strip(),
        "type": event_type,
        "timestamp_h": timestamp,
        "quantity": quantity,
        "lot_code": _text(event.get("lot_code")),
        "date_code": _text(event.get("date_code")),
        "coc_reference": _text(event.get("coc_reference")),
        "board_serial": board_serial,
        "cross_reference": _text(event.get("cross_reference")),
    }


def validate_chain(events):
    """Return the custody events ordered by clock, with chain-level checks done."""
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events must be a non-empty sequence of custody events")
    records = [validate_event(event, index) for index, event in enumerate(events)]

    seen = set()
    for record in records:
        if record["event_id"] in seen:
            raise ValueError("duplicate event_id %r in the chain" % record["event_id"])
        seen.add(record["event_id"])

    receipts = [record for record in records if record["type"] == "receipt"]
    if len(receipts) != 1:
        raise ValueError(
            "the chain of one lot needs exactly one receipt event, found %d"
            % len(receipts)
        )

    ordered = sorted(records, key=lambda record: (record["timestamp_h"],
                                                  record["event_id"]))
    if ordered[0]["type"] != "receipt":
        raise ValueError(
            "event %r is timed before the receipt of the lot" % ordered[0]["event_id"]
        )
    return ordered


def _ordered(events):
    """Return a validated, clock-ordered chain, accepting an already-ordered one."""
    if (
        isinstance(events, list)
        and events
        and isinstance(events[0], dict)
        and "cross_reference" in events[0]
    ):
        return events
    return validate_chain(events)


def identity_breaks(lot_id, events):
    """Return the list of identity breaks found across the ordered chain."""
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string")
    expected_lot = lot_id.strip()
    ordered = _ordered(events)

    receipt = ordered[0]
    receipt_date_code = receipt["date_code"]
    breaks = []
    for record in ordered:
        if not record["lot_code"]:
            breaks.append(
                "event %s (%s) carries no lot code; the identity stops there"
                % (record["event_id"], record["type"])
            )
            continue
        if record["lot_code"] != expected_lot and not record["cross_reference"]:
            breaks.append(
                "event %s carries lot code %s instead of %s with no cross-reference"
                % (record["event_id"], record["lot_code"], expected_lot)
            )
        if (
            receipt_date_code
            and record["date_code"]
            and record["date_code"] != receipt_date_code
        ):
            breaks.append(
                "event %s carries date code %s against the received %s"
                % (record["event_id"], record["date_code"], receipt_date_code)
            )
    return breaks


def reconcile_quantities(events):
    """Return the received, consumed and remaining quantities of the lot."""
    ordered = _ordered(events)
    received = ordered[0]["quantity"]
    installed = sum(r["quantity"] for r in ordered if r["type"] == "assembly-install")
    scrapped = sum(r["quantity"] for r in ordered if r["type"] == "scrap")
    returned = sum(r["quantity"] for r in ordered if r["type"] == "return-to-supplier")
    consumed = installed + scrapped + returned
    remaining = received - consumed
    return {
        "received": received,
        "installed": installed,
        "scrapped": scrapped,
        "returned": returned,
        "consumed": consumed,
        "remaining": remaining,
        "balanced": remaining >= 0,
        "over_issued": max(0, -remaining),
    }


def forward_trace(events):
    """Return {board_serial: installed quantity} for the lot."""
    ordered = _ordered(events)
    trace = {}
    for record in ordered:
        if record["type"] == "assembly-install":
            serial = record["board_serial"]
            trace[serial] = trace.get(serial, 0) + record["quantity"]
    return trace


def backward_trace(lot_id, events, board_serial):
    """Return the lot identity behind one board serial, refusing an unknown one."""
    serial = _text(board_serial)
    if not serial:
        raise ValueError("board_serial must be a non-empty string")
    ordered = _ordered(events)
    trace = forward_trace(ordered)
    if serial not in trace:
        raise ValueError("board serial %r was never built from this lot" % serial)
    receipt = ordered[0]
    return {
        "board_serial": serial,
        "lot_id": lot_id.strip(),
        "quantity": trace[serial],
        "date_code": receipt["date_code"],
        "coc_reference": receipt["coc_reference"],
        "receipt_event_id": receipt["event_id"],
    }


def identity_completeness(events):
    """Return the fraction of events carrying lot code, date code and certificate."""
    ordered = _ordered(events)
    complete = 0
    for record in ordered:
        if all(record[field] for field in _IDENTITY_FIELDS):
            complete += 1
    return complete / len(ordered)


def assess_traceability(lot_id, events, required_completeness=1.0):
    """Run the full clause 4.5.4 traceability assessment for one lot."""
    if not isinstance(required_completeness, (int, float)) or isinstance(
        required_completeness, bool
    ):
        raise ValueError("required_completeness must be a real number")
    required = float(required_completeness)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_completeness must lie in 0..1, got %r"
                         % (required_completeness,))

    ordered = validate_chain(events)
    breaks = identity_breaks(lot_id, ordered)
    quantities = reconcile_quantities(ordered)
    forward = forward_trace(ordered)
    completeness = identity_completeness(ordered)
    meets_completeness = completeness > required or math.isclose(
        completeness, required, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )

    findings = list(breaks)
    if not quantities["balanced"]:
        findings.append(
            "lot %s issued %d parts more than the %d received; the chain is not a "
            "single lot" % (lot_id.strip(), quantities["over_issued"],
                            quantities["received"])
        )
    if not meets_completeness:
        findings.append(
            "identity completeness %.4f is below the required %.4f across %d events"
            % (completeness, required, len(ordered))
        )
    if quantities["installed"] > 0 and not forward:
        findings.append("parts were installed but no board serial was recorded")

    return {
        "lot_id": lot_id.strip(),
        "events": ordered,
        "identity_breaks": breaks,
        "quantities": quantities,
        "forward_trace": forward,
        "identity_completeness": completeness,
        "required_completeness": required,
        "meets_completeness": meets_completeness,
        "findings": findings,
        "traceable": not breaks and quantities["balanced"] and meets_completeness,
    }
