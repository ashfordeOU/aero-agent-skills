"""Shelf-life to process-control interface: release or block a material issue.

Anchor: ECSS-Q-ST-70-22C, interface clause -- the gate that sits between
shelf-life control and the process standards that consume the material
(the ECSS-Q-ST-70C family, including the -70-16C and -70-31C process flows),
so that expired or quarantined material cannot enter a controlled process.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the operation window from the planned start and the application
   duration; the material has to stay inside its shelf life for the whole of
   that window, not merely at the moment the drum is opened.
2. Compare the window against the lot's shelf-life deadline, which runs to the
   end of the expiry day, and separate "already expired" from "expires part
   way through the operation" -- they have different recoveries.
3. Check the lot's stores status against the releasable set, and refuse a lot
   carrying an open deviation.
4. Check that the process the operation runs is on the lot's approved-process
   list and that the process standard cited is one the interface recognises.
5. Where the material is mixed or activated, check the operation duration
   against the pot life left at the planned start.
6. Return a release or block decision with machine-readable reason codes, so
   the calling process-control system can act on the refusal rather than
   re-reading prose.
"""

import datetime
import math

__all__ = [
    "RECOGNISED_PROCESS_STANDARDS",
    "RELEASABLE_STATUSES",
    "WINDOW_TOLERANCE_S",
    "REASON_CODES",
    "parse_date",
    "parse_timestamp",
    "shelf_life_deadline",
    "operation_window",
    "shelf_life_reason_codes",
    "status_reason_codes",
    "process_reason_codes",
    "pot_life_reason_codes",
    "evaluate_material_release",
]

# Process standards this interface is wired to; an operation citing anything
# else is refused rather than waved through on an unrecognised reference.
RECOGNISED_PROCESS_STANDARDS = (
    "ecss-q-st-70c",
    "ecss-q-st-70-16c",
    "ecss-q-st-70-31c",
)

# The only stores statuses a controlled process may draw against.
RELEASABLE_STATUSES = ("released", "released-restricted")

# Window comparisons are datetime differences in seconds; an operation ending
# exactly on the deadline is a representation question, absorbed here rather
# than by extending the shelf life.
WINDOW_TOLERANCE_S = 1e-6

REASON_CODES = (
    "expired-before-use",
    "expires-during-operation",
    "status-not-released",
    "open-deviation",
    "process-not-approved",
    "unrecognised-process-standard",
    "pot-life-exceeded",
    "pot-life-already-spent",
)


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def parse_date(value, label="date"):
    """Return an ISO date string or date object as a datetime.date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError("three components expected")
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except Exception:
        raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))


def parse_timestamp(value, label="timestamp"):
    """Return an ISO yyyy-mm-ddThh:mm[:ss] string or datetime as a datetime."""
    if isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO timestamp string or a datetime, got %r"
                         % (label, value))
    text = value.strip().replace(" ", "T")
    if not text:
        raise ValueError("%s must not be empty" % label)
    if "T" not in text:
        raise ValueError("%s must carry a time of day, got %r" % (label, value))
    day_part, time_part = text.split("T", 1)
    day = parse_date(day_part, label)
    bits = time_part.split(":")
    if len(bits) not in (2, 3):
        raise ValueError("%s time must be hh:mm or hh:mm:ss, got %r" % (label, value))
    try:
        hour = int(bits[0])
        minute = int(bits[1])
        second = int(float(bits[2])) if len(bits) == 3 else 0
        return datetime.datetime(day.year, day.month, day.day, hour, minute, second)
    except Exception:
        raise ValueError("%s is not a valid ISO timestamp, got %r" % (label, value))


def shelf_life_deadline(expiry_date):
    """Return the instant the shelf life runs out: the end of the expiry day."""
    expiry = parse_date(expiry_date, "expiry_date")
    return datetime.datetime(expiry.year, expiry.month, expiry.day) + datetime.timedelta(days=1)


def _positive_duration(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    duration = float(value)
    if not math.isfinite(duration):
        raise ValueError("%s must be finite" % label)
    if duration <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, duration))
    return duration


def operation_window(start, duration_hours):
    """Return the (start, end) datetimes the material is in use across."""
    begin = parse_timestamp(start, "start")
    hours = _positive_duration(duration_hours, "duration_hours")
    return (begin, begin + datetime.timedelta(hours=hours))


def shelf_life_reason_codes(lot, window):
    """Compare the operation window against the lot's shelf-life deadline."""
    _require_mapping(lot, "lot")
    if lot.get("expiry_date") is None:
        raise ValueError("lot missing required key 'expiry_date'")
    deadline = shelf_life_deadline(lot["expiry_date"])
    begin, end = window
    codes = []
    if (begin - deadline).total_seconds() >= -WINDOW_TOLERANCE_S:
        codes.append("expired-before-use")
    elif (end - deadline).total_seconds() > WINDOW_TOLERANCE_S:
        codes.append("expires-during-operation")
    return codes


def status_reason_codes(lot):
    """Check the stores status and any open deviation on the lot."""
    _require_mapping(lot, "lot")
    status = lot.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("lot 'status' must be a non-empty string")
    codes = []
    if status.strip().lower() not in RELEASABLE_STATUSES:
        codes.append("status-not-released")
    if lot.get("open_deviation", False) is True:
        codes.append("open-deviation")
    return codes


def process_reason_codes(operation, lot):
    """Check the process against the lot's approved list and the standard cited."""
    _require_mapping(operation, "operation")
    _require_mapping(lot, "lot")
    process = operation.get("process_id")
    if not isinstance(process, str) or not process.strip():
        raise ValueError("operation 'process_id' must be a non-empty string")
    standard = operation.get("process_standard")
    if not isinstance(standard, str) or not standard.strip():
        raise ValueError("operation 'process_standard' must be a non-empty string")
    approved = lot.get("approved_processes")
    if approved is None:
        raise ValueError("lot missing required key 'approved_processes'")
    if not isinstance(approved, (list, tuple, set, frozenset)):
        raise ValueError("lot 'approved_processes' must be a sequence of process identifiers")
    approved_lower = {str(p).strip().lower() for p in approved}
    codes = []
    if process.strip().lower() not in approved_lower:
        codes.append("process-not-approved")
    if standard.strip().lower() not in RECOGNISED_PROCESS_STANDARDS:
        codes.append("unrecognised-process-standard")
    return codes


def pot_life_reason_codes(operation, lot, window):
    """Check the operation against the pot life left on a mixed material."""
    _require_mapping(operation, "operation")
    _require_mapping(lot, "lot")
    pot_life_min = lot.get("pot_life_min")
    mixed_at = lot.get("mixed_at")
    if pot_life_min is None and mixed_at is None:
        return []
    if pot_life_min is None or mixed_at is None:
        raise ValueError(
            "a mixed lot needs both 'mixed_at' and 'pot_life_min'; one without the "
            "other cannot bound the working time"
        )
    minutes = _positive_duration(pot_life_min, "pot_life_min")
    mixed = parse_timestamp(mixed_at, "mixed_at")
    begin, end = window
    expiry_instant = mixed + datetime.timedelta(minutes=minutes)
    codes = []
    if (begin - expiry_instant).total_seconds() >= -WINDOW_TOLERANCE_S:
        codes.append("pot-life-already-spent")
    elif (end - expiry_instant).total_seconds() > WINDOW_TOLERANCE_S:
        codes.append("pot-life-exceeded")
    return codes


def evaluate_material_release(operation, lot):
    """Release or block a material issue into a controlled process.

    operation keys: process_id, process_standard, start, duration_hours.
    lot keys: lot_id, expiry_date, status, approved_processes, optional
    open_deviation, mixed_at and pot_life_min.
    """
    _require_mapping(operation, "operation")
    _require_mapping(lot, "lot")
    window = operation_window(operation.get("start"), operation.get("duration_hours"))
    codes = []
    codes.extend(shelf_life_reason_codes(lot, window))
    codes.extend(status_reason_codes(lot))
    codes.extend(process_reason_codes(operation, lot))
    codes.extend(pot_life_reason_codes(operation, lot, window))
    for code in codes:
        if code not in REASON_CODES:
            raise ValueError("internal reason-code error: %r" % (code,))
    findings = [_explain(code, operation, lot, window) for code in codes]
    return {
        "lot_id": lot.get("lot_id"),
        "process_id": operation.get("process_id"),
        "window_start": window[0].isoformat(),
        "window_end": window[1].isoformat(),
        "reason_codes": codes,
        "findings": findings,
        "decision": "block" if codes else "release",
    }


def _explain(code, operation, lot, window):
    """Return the human-readable finding behind one reason code."""
    begin, end = window
    if code == "expired-before-use":
        return ("lot %s was already past its expiry date %s at the planned start %s"
                % (lot.get("lot_id"), lot.get("expiry_date"), begin.isoformat()))
    if code == "expires-during-operation":
        return ("lot %s expires on %s, part way through an operation running to %s"
                % (lot.get("lot_id"), lot.get("expiry_date"), end.isoformat()))
    if code == "status-not-released":
        return ("lot %s carries stores status '%s', which is not a releasable status"
                % (lot.get("lot_id"), lot.get("status")))
    if code == "open-deviation":
        return "lot %s carries an open deviation and may not be issued" % lot.get("lot_id")
    if code == "process-not-approved":
        return ("process %s is not on the approved-process list for lot %s"
                % (operation.get("process_id"), lot.get("lot_id")))
    if code == "unrecognised-process-standard":
        return ("operation cites process standard '%s', which this interface does not "
                "recognise" % operation.get("process_standard"))
    if code == "pot-life-already-spent":
        return ("the pot life of lot %s was already spent at the planned start %s"
                % (lot.get("lot_id"), begin.isoformat()))
    if code == "pot-life-exceeded":
        return ("the operation runs to %s, past the pot life of lot %s"
                % (end.isoformat(), lot.get("lot_id")))
    raise ValueError("no explanation for reason code %r" % (code,))
