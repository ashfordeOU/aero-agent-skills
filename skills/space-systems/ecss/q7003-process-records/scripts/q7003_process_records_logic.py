#!/usr/bin/env python3
"""Batch process record for an anodizing run.

Anchor: ECSS-Q-ST-70-03 records clause on anodizing. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

The record is what survives the batch. Once the parts have shipped, the
only evidence that they were processed inside the qualified window is
what was written down at the time, so the record is graded on four
things:

completeness   every field the traceability chain needs is present. A
               record that cannot name its tank, its rack count or the
               qualification it ran under cannot be tied back to the
               line that produced it.
control        every recorded parameter inside the window the line was
               qualified for, and no parameter silently absent. A blank
               is not a nominal value.
sequence       the process steps in their proper order with
               non-decreasing times. A record whose seal timestamp
               precedes its anodize timestamp is describing something
               that did not happen.
timeliness     the delay between rinse and seal. A freshly anodized
               coating is porous and open, so a long wait before sealing
               takes up whatever the rinse water and the air offer it.

Retention is computed rather than assumed: the record has to outlive the
hardware it covers, and the expiry date is derived from the record date
and the declared retention period.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

REQUIRED_RECORD_FIELDS = (
    "batch_id",
    "part_numbers",
    "alloy",
    "tank_id",
    "qualification_id",
    "rack_count",
    "operator_id",
    "record_date",
)

PROCESS_STEPS = ("degrease", "etch", "desmut", "anodize", "rinse", "seal")

DEFAULT_MAX_SEAL_DELAY_MINUTES = 30

RECORD_COMPLETE = "record-complete"
RECORD_DEFICIENT = "record-deficient"
RECORD_REJECTED = "record-rejected"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _within(value, low, high):
    """low <= value <= high, absorbing floating-point representation error.

    A parameter set on a window edge is logged through a conversion and
    can read a few units in the last place outside its own bound. The
    window is never widened; only the comparison tolerates the error.
    """
    if value < low and not math.isclose(
        value, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return False
    if value > high and not math.isclose(
        value, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return False
    return True


def _parse_timestamp(name, value):
    if isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO timestamp string, got %r" % (name, value))
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a readable ISO timestamp: %r" % (name, value))


def _parse_date(name, value):
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a readable ISO date: %r" % (name, value))


def missing_fields(record):
    """Traceability fields the record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = []
    for field in REQUIRED_RECORD_FIELDS:
        value = record.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
        elif isinstance(value, (list, tuple, set)) and not value:
            missing.append(field)
    return missing


def check_parameter_record(parameters, windows):
    """Grade recorded process parameters against the qualified window."""
    if not isinstance(windows, dict) or not windows:
        raise ValueError("windows must be a non-empty mapping of parameter to bounds")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping, got %r" % (parameters,))
    excursions = []
    unrecorded = []
    for name in sorted(windows):
        bounds = windows[name]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("window for %s must be a (low, high) pair" % name)
        low = _require_number("%s low bound" % name, bounds[0])
        high = _require_number("%s high bound" % name, bounds[1])
        if high < low:
            raise ValueError("window for %s is inverted" % name)
        if name not in parameters:
            unrecorded.append(name)
            continue
        value = _require_number(name, parameters[name])
        if not _within(value, low, high):
            excursions.append(
                "%s recorded %.4f outside the %.4f to %.4f window" % (name, value, low, high)
            )
    findings = list(excursions)
    if unrecorded:
        findings.append(
            "parameter(s) left blank on the record: %s" % ", ".join(unrecorded)
        )
    return {
        "in_control": not excursions,
        "complete": not unrecorded,
        "excursions": excursions,
        "unrecorded": unrecorded,
        "findings": findings,
    }


def check_process_sequence(events):
    """Check the process steps are all present, in order, and in time."""
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events must be a non-empty sequence of process steps")
    seen = {}
    ordered = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("event %d must be a mapping" % index)
        step = event.get("step")
        if step not in PROCESS_STEPS:
            raise ValueError(
                "event %d names step %r; expected one of %s"
                % (index, step, ", ".join(PROCESS_STEPS))
            )
        if step in seen:
            raise ValueError("step %s is recorded more than once" % step)
        stamp = _parse_timestamp("timestamp for %s" % step, event.get("at"))
        seen[step] = stamp
        ordered.append((step, stamp))
    missing = [step for step in PROCESS_STEPS if step not in seen]
    out_of_order = []
    previous_step = None
    previous_stamp = None
    for step in PROCESS_STEPS:
        if step not in seen:
            continue
        stamp = seen[step]
        if previous_stamp is not None and stamp < previous_stamp:
            out_of_order.append(
                "%s is timestamped before %s" % (step, previous_step)
            )
        previous_step, previous_stamp = step, stamp
    findings = []
    if missing:
        findings.append("process step(s) not recorded: %s" % ", ".join(missing))
    findings.extend(out_of_order)
    return {
        "complete": not missing,
        "in_order": not out_of_order,
        "missing": missing,
        "out_of_order": out_of_order,
        "findings": findings,
    }


def seal_delay_minutes(events):
    """Whole minutes between the final rinse and the seal step."""
    sequence = check_process_sequence(events)
    stamps = {event["step"]: _parse_timestamp("timestamp", event["at"]) for event in events}
    if "rinse" not in stamps or "seal" not in stamps:
        raise ValueError(
            "a seal delay needs both a rinse and a seal timestamp on the record"
        )
    if not sequence["in_order"]:
        raise ValueError("the process sequence is out of order; the delay is meaningless")
    delta = stamps["seal"] - stamps["rinse"]
    return int(delta.total_seconds()) // 60


def check_seal_delay(events, max_minutes=DEFAULT_MAX_SEAL_DELAY_MINUTES):
    """Grade the rinse-to-seal delay against the declared maximum."""
    limit = _require_count("max_minutes", max_minutes, minimum=1)
    delay = seal_delay_minutes(events)
    acceptable = delay <= limit
    findings = []
    if not acceptable:
        findings.append(
            "%d minutes between rinse and seal exceeds the %d minute maximum; the "
            "open coating was left to take up whatever was around it" % (delay, limit)
        )
    return {
        "delay_minutes": delay,
        "max_minutes": limit,
        "acceptable": acceptable,
        "findings": findings,
    }


def retention_expiry(record_date, retention_years):
    """Date the batch record may be released from retention."""
    start = _parse_date("record_date", record_date)
    years = _require_count("retention_years", retention_years, minimum=1)
    year = start.year + years
    try:
        return start.replace(year=year)
    except ValueError:
        # 29 February in a record year that has no 29 February ahead of it.
        return start.replace(year=year, day=28)


def assess_batch_record(case):
    """Full completeness and control verdict for one batch process record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    record = case.get("record")
    gaps = missing_fields(record)
    parameters = check_parameter_record(
        record.get("parameters", {}), case.get("parameter_windows")
    )
    sequence = check_process_sequence(record.get("events"))
    findings = []
    if gaps:
        findings.append(
            "traceability field(s) absent from the record: %s" % ", ".join(gaps)
        )
    findings.extend(parameters["findings"])
    findings.extend(sequence["findings"])
    seal = None
    if sequence["complete"] and sequence["in_order"]:
        seal = check_seal_delay(
            record["events"],
            case.get("max_seal_delay_minutes", DEFAULT_MAX_SEAL_DELAY_MINUTES),
        )
        findings.extend(seal["findings"])
    expiry = None
    if "record_date" not in gaps:
        expiry = retention_expiry(
            record["record_date"], case.get("retention_years", 10)
        )
    rejected = (
        not parameters["in_control"]
        or not sequence["in_order"]
        or (seal is not None and not seal["acceptable"])
    )
    if rejected:
        verdict = RECORD_REJECTED
    elif gaps or not parameters["complete"] or not sequence["complete"]:
        verdict = RECORD_DEFICIENT
    else:
        verdict = RECORD_COMPLETE
    return {
        "verdict": verdict,
        "missing_fields": gaps,
        "parameters": parameters,
        "sequence": sequence,
        "seal_delay": seal,
        "retention_expiry": expiry,
        "findings": findings,
    }
