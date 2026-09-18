#!/usr/bin/env python3
"""Per-unit painting records: lots, application parameters and inspection.

Anchor: ECSS-Q-ST-70-31C, the Records clause on painting documentation. The
procedure below is a paraphrased, implementable restatement -- no verbatim
standard text. Offline, deterministic, Python standard library only.

The painting record is what survives the paint shop. It has to say which unit
was coated, which primer and topcoat lots went onto it, how they were mixed and
applied, that the mixed material was used inside its pot life and that each lot
was inside its shelf life when it was mixed, which inspection results it
carries, and how long the record itself is kept. This module grades one unit
record on all of that and returns the gaps by name.
"""

import math

__all__ = [
    "REQUIRED_FIELDS",
    "REQUIRED_PARAMETERS",
    "DEFAULT_RETENTION_YEARS",
    "parse_day",
    "parse_timestamp",
    "add_months",
    "day_number",
    "minutes_between",
    "missing_fields",
    "missing_parameters",
    "pot_life_findings",
    "shelf_life_expiry_day",
    "lot_shelf_life_findings",
    "traceability_gaps",
    "retention_end_day",
    "assess_unit_record",
    "assess_record_set",
]

# A pot life used right up to its stated minute is used inside it. Minute
# arithmetic is exact in integers, so these tolerances only guard the decimal
# pot-life and shelf-life figures a datasheet can carry; no limit is widened.
RECORD_REL_TOL = 1e-9
RECORD_ABS_TOL = 1e-12

DEFAULT_RETENTION_YEARS = 10

REQUIRED_FIELDS = (
    "unit_id",
    "drawing_issue",
    "primer_lot_id",
    "topcoat_lot_id",
    "mix_timestamp",
    "application_end_timestamp",
    "operator_id",
    "inspection_result",
    "record_day",
)

REQUIRED_PARAMETERS = (
    "mix_ratio",
    "spray_pressure_bar",
    "gun_distance_mm",
    "pass_count",
    "flash_off_minutes",
    "cure_temperature_c",
    "cure_duration_minutes",
)

INSPECTION_RESULTS = ("accepted", "rejected", "held")


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=RECORD_REL_TOL, abs_tol=RECORD_ABS_TOL)


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    return [31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31][month - 1]


def parse_day(label, text):
    """Parse a strict ISO calendar day into a comparable (year, month, day) tuple."""
    if not isinstance(text, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    parts = text.strip().split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) or len(parts[0]) != 4:
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    year, month, day = (int(p) for p in parts)
    if year < 1:
        raise ValueError("%s needs a year of 1 or later, got %r" % (label, text))
    if not 1 <= month <= 12:
        raise ValueError("%s has no month %d" % (label, month))
    if not 1 <= day <= _days_in_month(year, month):
        raise ValueError("%s has no day %d in month %d of %d" % (label, day, month, year))
    return (year, month, day)


def parse_timestamp(label, text):
    """Parse an ISO yyyy-mm-ddThh:mm stamp into (day tuple, hour, minute).

    Pot life is spent in minutes, so the record carries a time and not only a
    date. A stamp with no time is refused rather than assumed to be midnight,
    because midnight would silently hand back a whole extra pot life.
    """
    if not isinstance(text, str) or "T" not in text:
        raise ValueError("%s must be an ISO yyyy-mm-ddThh:mm stamp, got %r" % (label, text))
    day_part, time_part = text.strip().split("T", 1)
    day = parse_day(label, day_part)
    pieces = time_part.split(":")
    if len(pieces) != 2 or not all(p.isdigit() for p in pieces):
        raise ValueError("%s must carry an hh:mm time, got %r" % (label, text))
    hour, minute = (int(p) for p in pieces)
    if not 0 <= hour <= 23:
        raise ValueError("%s has no hour %d" % (label, hour))
    if not 0 <= minute <= 59:
        raise ValueError("%s has no minute %d" % (label, minute))
    return (day, hour, minute)


def day_number(day):
    """Whole days elapsed to this calendar day, for exact interval arithmetic."""
    year, month, dom = day
    total = 365 * (year - 1) + (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400
    for m in range(1, month):
        total += _days_in_month(year, m)
    return total + dom


def minutes_between(start, end):
    """Whole minutes from one timestamp to another, refusing a reversed pair."""
    start_day, start_hour, start_minute = start
    end_day, end_hour, end_minute = end
    start_total = day_number(start_day) * 1440 + start_hour * 60 + start_minute
    end_total = day_number(end_day) * 1440 + end_hour * 60 + end_minute
    if end_total < start_total:
        raise ValueError("the end stamp precedes the start stamp")
    return end_total - start_total


def add_months(day, months):
    """Advance a calendar day by whole months, clamping to the shorter month."""
    if isinstance(months, bool) or not isinstance(months, int) or months < 0:
        raise ValueError("months must be a non-negative integer, got %r" % (months,))
    year, month, dom = day
    index = (year * 12 + (month - 1)) + months
    new_year, new_month = divmod(index, 12)
    new_month += 1
    return (new_year, new_month, min(dom, _days_in_month(new_year, new_month)))


def missing_fields(record, required=REQUIRED_FIELDS):
    """Required record fields that are absent or blank."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % type(record))
    gaps = []
    for field in required:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            gaps.append(field)
    return sorted(gaps)


def missing_parameters(parameters, required=REQUIRED_PARAMETERS):
    """Application parameters the record fails to state.

    A parameter recorded as a blank or as a non-number is missing, not zero: an
    unstated cure temperature is exactly the gap this clause exists to close.
    """
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping, got %r" % type(parameters))
    gaps = []
    for name in required:
        if name not in parameters:
            gaps.append(name)
            continue
        value = parameters[name]
        if name == "mix_ratio":
            if not isinstance(value, str) or not value.strip():
                gaps.append(name)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(float(value)):
            gaps.append(name)
    return sorted(gaps)


def pot_life_findings(mix_timestamp, application_end_timestamp, pot_life_minutes):
    """Findings about the working life of the mixed material.

    Material used right up to the stated pot life is inside it; material still
    going on afterwards has been applied past the point the datasheet supports.
    """
    life = _finite_number(pot_life_minutes, "pot_life_minutes")
    if life <= 0.0:
        raise ValueError("pot life must be strictly positive, got %r" % (pot_life_minutes,))
    mix = parse_timestamp("mix_timestamp", mix_timestamp)
    end = parse_timestamp("application_end_timestamp", application_end_timestamp)
    used = minutes_between(mix, end)
    findings = [] if _at_or_below(used, life) else ["pot-life-exceeded"]
    return {"minutes_used": used, "pot_life_minutes": life, "findings": findings}


def shelf_life_expiry_day(manufacture_day, shelf_months):
    """Day a paint lot stops being usable, from its manufacture day."""
    if isinstance(shelf_months, bool) or not isinstance(shelf_months, int) or shelf_months < 1:
        raise ValueError("shelf_months must be a positive integer, got %r" % (shelf_months,))
    return add_months(parse_day("manufacture_day", manufacture_day), shelf_months)


def lot_shelf_life_findings(lots, mix_day):
    """Findings for every paint lot mixed after its shelf life had run out."""
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("at least one paint lot is required")
    mixed = parse_day("mix_day", mix_day)
    findings = []
    for index, lot in enumerate(lots):
        if not isinstance(lot, dict):
            raise ValueError("lot %d must be a mapping" % index)
        lot_id = lot.get("lot_id")
        if not isinstance(lot_id, str) or not lot_id.strip():
            raise ValueError("lot %d requires a non-empty lot_id" % index)
        expiry = shelf_life_expiry_day(lot.get("manufacture_day"), lot.get("shelf_months"))
        if mixed > expiry:
            findings.append("lot-past-shelf-life:%s" % lot_id.strip())
    return sorted(findings)


def traceability_gaps(applied_lot_ids, received_register):
    """Lots applied to the unit that the received-lots register does not hold.

    The chain is only closed when every lot on the part can be walked back to a
    receipt; a lot that appears only in the paint shop's own note is a gap.
    """
    if not isinstance(applied_lot_ids, (list, tuple)) or not applied_lot_ids:
        raise ValueError("at least one applied lot id is required")
    if not isinstance(received_register, (list, tuple, set, frozenset)):
        raise ValueError("received_register must be a sequence or set of lot ids")
    register = set()
    for item in received_register:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("received register entries must be non-empty strings")
        register.add(item.strip().lower())
    gaps = []
    for index, lot_id in enumerate(applied_lot_ids):
        if not isinstance(lot_id, str) or not lot_id.strip():
            raise ValueError("applied lot %d must be a non-empty string" % index)
        if lot_id.strip().lower() not in register:
            gaps.append(lot_id.strip())
    return sorted(set(gaps))


def retention_end_day(record_day, retention_years=DEFAULT_RETENTION_YEARS):
    """Day the painting record may first be disposed of."""
    if isinstance(retention_years, bool) or not isinstance(retention_years, int) \
            or retention_years < 1:
        raise ValueError("retention_years must be a positive integer, got %r" % (retention_years,))
    return add_months(parse_day("record_day", record_day), retention_years * 12)


def assess_unit_record(record):
    """Grade one per-unit painting record and return its gaps by name."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % type(record))
    findings = []
    gaps = missing_fields(record)
    findings.extend("record-field-missing:%s" % f for f in gaps)
    findings.extend(
        "application-parameter-missing:%s" % p
        for p in missing_parameters(record.get("parameters", {}))
    )

    result = record.get("inspection_result")
    if result is not None and result not in INSPECTION_RESULTS:
        raise ValueError("inspection_result must be one of %s, got %r"
                         % (INSPECTION_RESULTS, result))

    pot_life = None
    if "mix_timestamp" not in gaps and "application_end_timestamp" not in gaps:
        pot_life = pot_life_findings(
            record["mix_timestamp"],
            record["application_end_timestamp"],
            record.get("pot_life_minutes", 240.0),
        )
        findings.extend(pot_life["findings"])
    else:
        findings.append("pot-life-not-evaluated")

    if "mix_timestamp" not in gaps:
        mix_day_text = record["mix_timestamp"].split("T", 1)[0]
        findings.extend(lot_shelf_life_findings(record.get("lots"), mix_day_text))

    findings.extend(
        "traceability-gap:%s" % lot_id
        for lot_id in traceability_gaps(
            record.get("applied_lot_ids"), record.get("received_register", [])
        )
    )

    retention = None
    if "record_day" not in gaps:
        retention = retention_end_day(
            record["record_day"], record.get("retention_years", DEFAULT_RETENTION_YEARS)
        )

    findings = sorted(set(findings))
    blocking = [
        f for f in findings
        if f.startswith("traceability-gap")
        or f.startswith("lot-past-shelf-life")
        or f == "pot-life-exceeded"
    ]
    if not findings:
        state = "record-complete"
    elif blocking:
        state = "record-invalid"
    else:
        state = "record-incomplete"
    return {
        "unit_id": record.get("unit_id"),
        "pot_life": pot_life,
        "retention_end_day": retention,
        "findings": findings,
        "state": state,
        "complete": state == "record-complete",
    }


def assess_record_set(records):
    """Grade a set of unit records; the set closes only when every record does."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("at least one unit record is required")
    results = [assess_unit_record(item) for item in records]
    identifiers = [item["unit_id"] for item in results]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("unit ids must be unique within a record set")
    open_findings = sorted(
        "%s:%s" % (item["unit_id"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "records": results,
        "invalid_records": sorted(
            str(i["unit_id"]) for i in results if i["state"] == "record-invalid"
        ),
        "open_findings": open_findings,
        "set_closed": not open_findings,
    }
