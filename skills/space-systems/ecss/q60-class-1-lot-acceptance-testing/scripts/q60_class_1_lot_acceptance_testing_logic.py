"""Lot acceptance submission planning for Class 1 EEE lots.

Anchor: ECSS-Q-ST-60C clause 4.3.5 -- submitting each Class 1 lot, or each date
code within a delivery, for lot acceptance verification. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Not the pass/fail verdict of a lot acceptance test -- the question one step
earlier: WHICH submission units exist in a delivery, which of them still owe a
lot acceptance submission, and how many pieces each submission draws.

1. Split the delivery into submission units. A part number plus a date code
   plus a manufacturer lot identifier is one unit; pieces built in different
   weeks are different material and cannot share one submission.
2. Size each submission by exact rational arithmetic, rounding the percentage
   rule UP and clamping it between the declared floor and the unit quantity.
   A float percentage is converted through its decimal text so the rounding
   direction is the same on every platform.
3. Test each existing lot acceptance record for coverage: same part number,
   same date code, same lot identifier where both carry one, not dated after
   the submission date, and inside the declared validity window counted in
   whole calendar months.
4. Report every unit that still owes a submission, and never let a record from
   a neighbouring date code close a unit it does not name.
"""

from datetime import date
from fractions import Fraction

__all__ = [
    "DEFAULT_VALIDITY_MONTHS",
    "DEFAULT_MINIMUM_SAMPLE",
    "normalize_date_code",
    "parse_day",
    "months_elapsed",
    "group_delivery",
    "submission_sample_size",
    "record_covers_unit",
    "assess_lot_acceptance_submission",
]

# A lot acceptance record older than this many whole calendar months no longer
# covers a submission unless the caller declares a different window.
DEFAULT_VALIDITY_MONTHS = 24

# No submission draws fewer pieces than this unless the unit itself is smaller.
DEFAULT_MINIMUM_SAMPLE = 5


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def normalize_date_code(code):
    """Return the canonical four-digit YYWW form of a manufacturing date code."""
    text = _text("date_code", code)
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (code,))
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (code,))
    return text


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def months_elapsed(earlier, later):
    """Return whole calendar months from earlier to later.

    Integer month arithmetic only: a day-of-month that has not yet come round
    does not count as a completed month, and no float ever enters the age.
    """
    start = parse_day("earlier", earlier)
    end = parse_day("later", later)
    if end < start:
        raise ValueError("later day %s precedes earlier day %s" % (end, start))
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def group_delivery(units):
    """Return the submission units a delivery breaks down into.

    One unit is one (part_number, date_code, lot_id) triple; quantities of the
    same triple add together, and a delivery spanning several date codes owes
    one submission per date code rather than a single pooled one.
    """
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of delivery records")
    grouped = {}
    order = []
    for index, item in enumerate(units):
        if not isinstance(item, dict):
            raise ValueError("units[%d] must be a mapping" % index)
        for key in ("part_number", "date_code", "quantity"):
            if key not in item:
                raise ValueError("units[%d] missing required key '%s'" % (index, key))
        part = _text("units[%d] part_number" % index, item["part_number"])
        code = normalize_date_code(item["date_code"])
        lot_id = item.get("lot_id", "")
        if lot_id not in (None, ""):
            lot_id = _text("units[%d] lot_id" % index, lot_id)
        else:
            lot_id = ""
        quantity = _count("units[%d] quantity" % index, item["quantity"])
        if quantity < 1:
            raise ValueError("units[%d] quantity must be at least 1" % index)
        key = (part, code, lot_id)
        if key not in grouped:
            grouped[key] = 0
            order.append(key)
        grouped[key] += quantity
    return [
        {
            "part_number": key[0],
            "date_code": key[1],
            "lot_id": key[2],
            "quantity": grouped[key],
        }
        for key in order
    ]


def _rational(label, value):
    """Return value as an exact Fraction, going through decimal text for floats."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("%s must be finite, got %r" % (label, value))
        return Fraction(str(value))
    return Fraction(value)


def submission_sample_size(quantity, percent, minimum_sample=DEFAULT_MINIMUM_SAMPLE):
    """Return the number of pieces one submission draws from a unit.

    The percentage rule rounds UP, the declared floor raises a small draw, and
    neither may ask for more pieces than the unit holds. All of it is exact
    rational arithmetic, so the boundary case lands the same way everywhere.
    """
    held = _count("quantity", quantity)
    if held < 1:
        raise ValueError("quantity must be at least 1, got %d" % held)
    rate = _rational("percent", percent)
    if rate < 0 or rate > 100:
        raise ValueError("percent must lie in 0..100, got %s" % (percent,))
    floor_sample = _count("minimum_sample", minimum_sample)
    exact = rate * held / 100
    drawn = int(exact)
    if exact > drawn:
        drawn += 1
    if drawn < floor_sample:
        drawn = floor_sample
    if drawn > held:
        drawn = held
    return drawn


def record_covers_unit(record, unit, submission_day, validity_months=DEFAULT_VALIDITY_MONTHS):
    """Return (covered, reason) for one lot acceptance record against one unit.

    A record closes a unit only when it names the same material. The reason is
    returned either way so a rejected record can be shown, not just dropped.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping")
    for key in ("part_number", "date_code", "day"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    window = _count("validity_months", validity_months)
    if window < 1:
        raise ValueError("validity_months must be at least 1, got %d" % window)
    part = _text("record part_number", record["part_number"])
    code = normalize_date_code(record["date_code"])
    record_day = parse_day("record day", record["day"])
    asked = parse_day("submission_day", submission_day)
    record_lot = record.get("lot_id", "")
    if record_lot not in (None, ""):
        record_lot = _text("record lot_id", record_lot)
    else:
        record_lot = ""
    if part != unit["part_number"]:
        return (False, "record covers part %s, not %s" % (part, unit["part_number"]))
    if code != unit["date_code"]:
        return (False, "record covers date code %s, not %s" % (code, unit["date_code"]))
    if record_lot and unit["lot_id"] and record_lot != unit["lot_id"]:
        return (False, "record covers lot %s, not %s" % (record_lot, unit["lot_id"]))
    if record_day > asked:
        return (False, "record dated %s is later than the submission day %s" % (record_day, asked))
    age = months_elapsed(record_day, asked)
    if age > window:
        return (False, "record is %d months old against a %d month window" % (age, window))
    return (True, "record dated %s covers the unit, %d of %d months used" % (record_day, age, window))


# Rejection reasons ordered from the least to the most specific. A record for
# another part number says nothing about this unit; a record that names the
# right material and fell outside its window is the one worth reporting.
_REASON_ORDER = ("covers part", "covers date code", "covers lot", "later than", "months old")


def _reason_rank(reason):
    """Return how specific a rejection reason is, -1 when it is unranked."""
    for position, token in enumerate(_REASON_ORDER):
        if token in reason:
            return position
    return -1


def assess_lot_acceptance_submission(spec):
    """Return the clause 4.3.5 submission plan for one Class 1 delivery.

    spec keys: units, submission_day, sample_percent, optional records,
    optional minimum_sample and validity_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "submission_day", "sample_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    asked = parse_day("submission_day", spec["submission_day"])
    window = _count("validity_months", spec.get("validity_months", DEFAULT_VALIDITY_MONTHS))
    if window < 1:
        raise ValueError("validity_months must be at least 1, got %d" % window)
    floor_sample = spec.get("minimum_sample", DEFAULT_MINIMUM_SAMPLE)
    records = spec.get("records", [])
    if not isinstance(records, (list, tuple)):
        raise ValueError("spec['records'] must be a sequence of lot acceptance records")
    units = group_delivery(spec["units"])
    planned = []
    findings = []
    for unit in units:
        sample = submission_sample_size(unit["quantity"], spec["sample_percent"], floor_sample)
        covered_by = None
        reason = "no lot acceptance record names this unit"
        rejected = []
        for index, record in enumerate(records):
            ok, why = record_covers_unit(record, unit, asked, window)
            if ok:
                covered_by = record.get("reference", "record[%d]" % index)
                reason = why
                rejected = []
                break
            rejected.append(why)
        if covered_by is None and rejected:
            reason = max(rejected, key=_reason_rank)
        entry = dict(unit)
        entry["sample_size"] = sample
        entry["covered_by"] = covered_by
        entry["reason"] = reason
        entry["rejected"] = rejected
        entry["status"] = "covered" if covered_by else "submit"
        planned.append(entry)
        if covered_by is None:
            findings.append(
                "%s date code %s (%d pieces) owes a lot acceptance submission of %d pieces"
                % (unit["part_number"], unit["date_code"], unit["quantity"], sample)
            )
    outstanding = [entry for entry in planned if entry["status"] == "submit"]
    if len(units) > 1:
        findings.append(
            "delivery breaks into %d submission units; each takes its own submission"
            % len(units)
        )
    return {
        "submission_day": asked.isoformat(),
        "validity_months": window,
        "units": planned,
        "outstanding": [entry["date_code"] for entry in outstanding],
        "outstanding_pieces": sum(entry["sample_size"] for entry in outstanding),
        "complete": not outstanding,
        "disposition": "all-units-covered" if not outstanding else "submit-outstanding-units",
        "findings": findings,
    }
