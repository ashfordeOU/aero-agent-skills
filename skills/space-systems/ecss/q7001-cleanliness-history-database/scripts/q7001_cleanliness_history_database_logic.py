#!/usr/bin/env python3
"""Per-unit contamination history: events, measurements and their gaps.

Anchor: ECSS-Q-ST-70-01C, cleanliness records. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The history belongs to the item, not to the facility. For one serial
number the ledger holds three kinds of entry -- a cleaning, which
resets the accumulation; an exposure event, which adds to it; and a
measurement, which states what was actually found. Everything the
database answers (how much has landed since the unit was last known
clean, whether any interval went unmonitored, whether a cleaning was
ever closed by a reading) falls out of that ordered ledger.

Molecular deposition (mg/m2) and particulate obscuration (percentage
area coverage) are kept as separate ledgers and never summed together.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

MOLECULAR = "molecular"
PARTICULATE = "particulate"
CONTAMINANT_KINDS = (MOLECULAR, PARTICULATE)

KIND_CLEANING = "cleaning"
KIND_EXPOSURE = "exposure-event"
KIND_MEASUREMENT = "measurement"

ENTRY_KINDS = (KIND_CLEANING, KIND_EXPOSURE, KIND_MEASUREMENT)

# Entry kinds that carry a contaminant quantity.
QUANTIFIED_KINDS = (KIND_EXPOSURE, KIND_MEASUREMENT)

TOL = 1e-9

STATE_TRACEABLE = "history-traceable"
STATE_INCOMPLETE = "history-incomplete"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %r" % (name, minimum, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def parse_date(name, value):
    """ISO calendar date, rejected rather than guessed when malformed."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (name, value))


def normalise_entry(entry, index=0):
    """One history line, validated against its kind rather than defaulted."""
    if not isinstance(entry, dict):
        raise ValueError("entry[%d] must be a mapping, got %r" % (index, entry))
    kind = entry.get("kind")
    if kind not in ENTRY_KINDS:
        raise ValueError(
            "entry[%d].kind must be one of %s, got %r"
            % (index, ", ".join(ENTRY_KINDS), kind)
        )
    row = {
        "unit_id": _require_text("entry[%d].unit_id" % index, entry.get("unit_id")),
        "kind": kind,
        "date": parse_date("entry[%d].date" % index, entry.get("date")),
        "note": _require_text("entry[%d].note" % index, entry.get("note", "-")),
        "sequence": index,
    }
    if kind in QUANTIFIED_KINDS:
        contaminant = entry.get("contaminant")
        if contaminant not in CONTAMINANT_KINDS:
            raise ValueError(
                "entry[%d].contaminant must be one of %s, got %r"
                % (index, ", ".join(CONTAMINANT_KINDS), contaminant)
            )
        row["contaminant"] = contaminant
        row["value"] = _require_number(
            "entry[%d].value" % index, entry.get("value"), minimum=0.0
        )
    else:
        row["contaminant"] = None
        row["value"] = None
    return row


def _identity(row):
    return (row["unit_id"], row["kind"], row["date"], row["contaminant"], row["value"])


def build_ledger(entries, unit_id):
    """Ordered, de-duplicated history for one serial number."""
    unit = _require_text("unit_id", unit_id)
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list, got %r" % (entries,))
    rows = []
    seen = set()
    for i, entry in enumerate(entries):
        row = normalise_entry(entry, i)
        if row["unit_id"] != unit:
            continue
        key = _identity(row)
        if key in seen:
            raise ValueError(
                "duplicate history entry for %s on %s (%s)"
                % (unit, row["date"].isoformat(), row["kind"])
            )
        seen.add(key)
        rows.append(row)
    rows.sort(key=lambda r: (r["date"], r["sequence"]))
    return tuple(rows)


def last_cleaning(ledger):
    """Most recent cleaning in the ledger, or None if the unit has had none."""
    found = None
    for row in ledger:
        if row["kind"] == KIND_CLEANING:
            found = row
    return found


def exposure_since_cleaning(ledger):
    """Molecular and particulate accumulated since the unit was last cleaned."""
    cleaning = last_cleaning(ledger)
    totals = {MOLECULAR: 0.0, PARTICULATE: 0.0}
    counted = 0
    for row in ledger:
        if row["kind"] != KIND_EXPOSURE:
            continue
        if cleaning is not None and (
            row["date"] < cleaning["date"]
            or (
                row["date"] == cleaning["date"]
                and row["sequence"] < cleaning["sequence"]
            )
        ):
            continue
        totals[row["contaminant"]] += row["value"]
        counted += 1
    return {
        "since": cleaning["date"].isoformat() if cleaning else None,
        "molecular": totals[MOLECULAR],
        "particulate": totals[PARTICULATE],
        "events_counted": counted,
    }


def latest_measurement(ledger, contaminant):
    """Last reading on one ledger, which is what the unit is known to be at."""
    if contaminant not in CONTAMINANT_KINDS:
        raise ValueError(
            "contaminant must be one of %s, got %r"
            % (", ".join(CONTAMINANT_KINDS), contaminant)
        )
    found = None
    for row in ledger:
        if row["kind"] == KIND_MEASUREMENT and row["contaminant"] == contaminant:
            found = row
    return found


def monitoring_gaps(ledger, max_interval_days, as_of=None):
    """Intervals between readings longer than the declared maximum."""
    limit = _require_count("max_interval_days", max_interval_days, minimum=1)
    dates = [row["date"] for row in ledger if row["kind"] == KIND_MEASUREMENT]
    gaps = []
    for earlier, later in zip(dates, dates[1:]):
        span = (later - earlier).days
        if span > limit:
            gaps.append(
                {
                    "from": earlier.isoformat(),
                    "to": later.isoformat(),
                    "days": span,
                    "over_by_days": span - limit,
                }
            )
    if as_of is not None and dates:
        today = parse_date("as_of", as_of)
        span = (today - dates[-1]).days
        if span > limit:
            gaps.append(
                {
                    "from": dates[-1].isoformat(),
                    "to": today.isoformat(),
                    "days": span,
                    "over_by_days": span - limit,
                }
            )
    return tuple(gaps)


def cleaning_closed_by_reading(ledger):
    """Was the last cleaning followed by a measurement that states its level."""
    cleaning = last_cleaning(ledger)
    if cleaning is None:
        return False
    for row in ledger:
        if row["kind"] != KIND_MEASUREMENT:
            continue
        if row["date"] > cleaning["date"] or (
            row["date"] == cleaning["date"] and row["sequence"] > cleaning["sequence"]
        ):
            return True
    return False


def record_contamination_history(case):
    """Full per-unit history state: accumulation, gaps and what is missing."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    unit = _require_text("unit_id", case.get("unit_id"))
    ledger = build_ledger(case.get("entries"), unit)
    max_interval = _require_count(
        "max_interval_days", case.get("max_interval_days", 30), minimum=1
    )
    gaps = monitoring_gaps(ledger, max_interval, case.get("as_of"))
    accumulation = exposure_since_cleaning(ledger)
    missing = []
    if not ledger:
        missing.append("the unit has no history entries at all")
    if last_cleaning(ledger) is None:
        missing.append("no cleaning operation is on record")
    elif not cleaning_closed_by_reading(ledger):
        missing.append("the last cleaning was never closed by a verification reading")
    for contaminant in CONTAMINANT_KINDS:
        if latest_measurement(ledger, contaminant) is None:
            missing.append("no %s measurement is on record" % contaminant)
    for gap in gaps:
        missing.append(
            "monitoring gap of %d days from %s to %s, %d over the declared maximum"
            % (gap["days"], gap["from"], gap["to"], gap["over_by_days"])
        )
    return {
        "unit_id": unit,
        "entry_count": len(ledger),
        "first_entry": ledger[0]["date"].isoformat() if ledger else None,
        "last_entry": ledger[-1]["date"].isoformat() if ledger else None,
        "last_cleaning": accumulation["since"],
        "exposure_since_cleaning": accumulation,
        "latest_molecular": (
            latest_measurement(ledger, MOLECULAR)["value"]
            if latest_measurement(ledger, MOLECULAR)
            else None
        ),
        "latest_particulate": (
            latest_measurement(ledger, PARTICULATE)["value"]
            if latest_measurement(ledger, PARTICULATE)
            else None
        ),
        "monitoring_gaps": gaps,
        "missing": tuple(missing),
        "traceable": not missing,
        "state": STATE_TRACEABLE if not missing else STATE_INCOMPLETE,
    }
