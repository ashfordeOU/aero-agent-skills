"""Lot acceptance submission routing for Class 2 EEE lots.

Anchor: ECSS-Q-ST-60C clause 5.3.5 -- submitting each Class 2 lot, or each date
code within a delivery, for lot acceptance verification. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Not a single pass/fail verdict on a lot acceptance test. The question one step
earlier, and at Class 2 one level finer than at Class 1: WHICH submission units
a delivery breaks into, and then, GROUP BY GROUP, which acceptance test groups
of each unit are already discharged by evidence on file and which still have to
be submitted.

1. Split the delivery into submission units. A part number plus a date code
   plus a manufacturer lot identifier names one unit; pieces built in different
   weeks are different material and cannot share one submission.
2. Settle each acceptance test group of a unit separately. A unit is rarely
   wholly covered or wholly open: manufacturer evidence typically discharges
   the endpoint group and leaves the endurance group outstanding.
3. Apply the Class 2 evidence rule. Endpoint and environmental groups are
   lot-level questions and need evidence naming that lot. The endurance group
   is the Class 2 relaxation: evidence from another lot of the same technology
   family is creditable, because the endurance group asks about the family and
   the process, not about the individual week of build.
4. Size the outstanding draw per group with exact rational arithmetic, rounding
   the percentage rule UP, raising it to the declared per-group floor and
   capping it at the unit quantity. A float percentage is converted through its
   decimal text so the rounding direction is the same on every platform.
5. Route each unit: evidence accepted when every group is closed, a partial
   submission when some group survives, a full submission when none is closed.
"""

from datetime import date
from fractions import Fraction

__all__ = [
    "TEST_GROUPS",
    "FAMILY_CREDITABLE_GROUPS",
    "DEFAULT_GROUP_DRAW",
    "DEFAULT_GROUP_VALIDITY_MONTHS",
    "normalize_date_code",
    "parse_day",
    "months_elapsed",
    "submission_units",
    "group_draw",
    "evidence_covers_group",
    "unit_route",
    "assess_lot_acceptance_submission",
]

# The acceptance test groups a Class 2 submission is settled in. They are
# settled one at a time; a unit is almost never wholly open or wholly closed.
TEST_GROUPS = ("electrical-endpoint", "environmental", "endurance")

# The Class 2 relaxation. Evidence from another lot of the same technology
# family discharges these groups; every other group needs evidence that names
# the lot itself.
FAMILY_CREDITABLE_GROUPS = ("endurance",)

# Per group: (percentage of the unit drawn, minimum pieces drawn).
DEFAULT_GROUP_DRAW = {
    "electrical-endpoint": (Fraction(2), 5),
    "environmental": (Fraction(1), 3),
    "endurance": (Fraction(1, 2), 2),
}

# How many whole calendar months a record of each group stays evidence. The
# endurance group runs longer and ages more slowly than an endpoint sweep.
DEFAULT_GROUP_VALIDITY_MONTHS = {
    "electrical-endpoint": 24,
    "environmental": 24,
    "endurance": 36,
}


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


def _rational(label, value):
    """Return value as an exact Fraction, going through decimal text for floats."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("%s must be finite, got %r" % (label, value))
        return Fraction(str(value))
    return Fraction(value)


def _group_name(label, value):
    """Return value as one of the acceptance test groups."""
    name = _text(label, value)
    if name not in TEST_GROUPS:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(TEST_GROUPS), value)
        )
    return name


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


def submission_units(lines):
    """Return the submission units a Class 2 delivery breaks down into.

    One unit is one (part_number, date_code, lot_id) triple; quantities of the
    same triple add, and a delivery spanning several date codes owes one
    submission per date code rather than a single pooled one. The technology
    family travels with the unit because the endurance group is settled on it.
    """
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence of delivery records")
    grouped = {}
    families = {}
    order = []
    for index, item in enumerate(lines):
        if not isinstance(item, dict):
            raise ValueError("lines[%d] must be a mapping" % index)
        for key in ("part_number", "date_code", "quantity"):
            if key not in item:
                raise ValueError("lines[%d] missing required key '%s'" % (index, key))
        part = _text("lines[%d] part_number" % index, item["part_number"])
        code = normalize_date_code(item["date_code"])
        lot_id = item.get("lot_id", "")
        lot_id = _text("lines[%d] lot_id" % index, lot_id) if lot_id not in (None, "") else ""
        family = item.get("family", "")
        family = _text("lines[%d] family" % index, family) if family not in (None, "") else ""
        quantity = _count("lines[%d] quantity" % index, item["quantity"])
        if quantity < 1:
            raise ValueError("lines[%d] quantity must be at least 1" % index)
        key = (part, code, lot_id)
        if key not in grouped:
            grouped[key] = 0
            families[key] = family
            order.append(key)
        elif family and families[key] and family != families[key]:
            raise ValueError(
                "lines[%d] gives lot %s the family %s after %s"
                % (index, lot_id or code, family, families[key])
            )
        elif family and not families[key]:
            families[key] = family
        grouped[key] += quantity
    return [
        {
            "part_number": key[0],
            "date_code": key[1],
            "lot_id": key[2],
            "family": families[key],
            "quantity": grouped[key],
        }
        for key in order
    ]


def group_draw(quantity, group, draw_table=None):
    """Return the pieces one acceptance test group draws from a unit.

    The percentage rule rounds UP, the per-group floor raises a small draw, and
    neither may ask for more pieces than the unit holds. All exact rational
    arithmetic, so a rate landing on a whole number of pieces does not round up
    an extra one on one platform and not on another.
    """
    held = _count("quantity", quantity)
    if held < 1:
        raise ValueError("quantity must be at least 1, got %d" % held)
    name = _group_name("group", group)
    table = DEFAULT_GROUP_DRAW if draw_table is None else draw_table
    if not isinstance(table, dict) or name not in table:
        raise ValueError("draw_table has no entry for group %r" % (group,))
    entry = table[name]
    if not isinstance(entry, (list, tuple)) or len(entry) != 2:
        raise ValueError("draw_table[%r] must be a (percent, floor) pair" % (group,))
    rate = _rational("draw_table[%r] percent" % name, entry[0])
    if rate < 0 or rate > 100:
        raise ValueError("draw_table[%r] percent must lie in 0..100" % (group,))
    floor_sample = _count("draw_table[%r] floor" % name, entry[1])
    exact = rate * held / 100
    drawn = int(exact)
    if exact > drawn:
        drawn += 1
    if drawn < floor_sample:
        drawn = floor_sample
    if drawn > held:
        drawn = held
    return drawn


def evidence_covers_group(record, unit, group, submission_day, validity_months=None):
    """Return (covered, reason) for one acceptance record against one group.

    The reason is returned either way, so a record that was set aside can be
    shown to the reviewer instead of silently dropped.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping")
    for key in ("part_number", "date_code", "day", "groups"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    name = _group_name("group", group)
    windows = DEFAULT_GROUP_VALIDITY_MONTHS if validity_months is None else validity_months
    if not isinstance(windows, dict) or name not in windows:
        raise ValueError("validity_months has no entry for group %r" % (group,))
    window = _count("validity_months[%r]" % name, windows[name])
    if window < 1:
        raise ValueError("validity_months[%r] must be at least 1" % (group,))
    groups = record["groups"]
    if not isinstance(groups, (list, tuple, set, frozenset)):
        raise ValueError("record['groups'] must be a sequence of test groups")
    covered_groups = {_group_name("record group", item) for item in groups}
    scope = record.get("scope", "lot")
    scope = _text("record scope", scope)
    if scope not in ("lot", "family"):
        raise ValueError("record scope must be lot or family, got %r" % (scope,))
    part = _text("record part_number", record["part_number"])
    code = normalize_date_code(record["date_code"])
    record_day = parse_day("record day", record["day"])
    asked = parse_day("submission_day", submission_day)

    if name not in covered_groups:
        return (False, "record does not carry the %s group" % name)
    if scope == "family":
        if name not in FAMILY_CREDITABLE_GROUPS:
            return (False, "family evidence cannot discharge the %s group" % name)
        record_family = record.get("family", "")
        record_family = _text("record family", record_family) if record_family not in (None, "") else ""
        if not record_family or not unit.get("family"):
            return (False, "family evidence needs a technology family on both sides")
        if record_family != unit["family"]:
            return (
                False,
                "record covers family %s, not %s" % (record_family, unit["family"]),
            )
    else:
        if part != unit["part_number"]:
            return (False, "record covers part %s, not %s" % (part, unit["part_number"]))
        if code != unit["date_code"]:
            return (
                False,
                "record covers date code %s, not %s" % (code, unit["date_code"]),
            )
        record_lot = record.get("lot_id", "")
        record_lot = _text("record lot_id", record_lot) if record_lot not in (None, "") else ""
        if record_lot and unit["lot_id"] and record_lot != unit["lot_id"]:
            return (False, "record covers lot %s, not %s" % (record_lot, unit["lot_id"]))
    if record_day > asked:
        return (
            False,
            "record dated %s is later than the submission day %s" % (record_day, asked),
        )
    age = months_elapsed(record_day, asked)
    if age > window:
        return (False, "record is %d months old against a %d month window" % (age, window))
    return (
        True,
        "%s evidence dated %s closes the %s group, %d of %d months used"
        % (scope, record_day, name, age, window),
    )


def unit_route(open_groups, required_groups):
    """Return how a unit is settled given the groups still open."""
    if not isinstance(open_groups, (list, tuple, set, frozenset)):
        raise ValueError("open_groups must be a sequence of test groups")
    if not isinstance(required_groups, (list, tuple, set, frozenset)) or not required_groups:
        raise ValueError("required_groups must be a non-empty sequence of test groups")
    still_open = {_group_name("open group", item) for item in open_groups}
    required = {_group_name("required group", item) for item in required_groups}
    if not still_open <= required:
        raise ValueError("open_groups holds a group that was never required")
    if not still_open:
        return "evidence-accepted"
    if still_open == required:
        return "full-submission"
    return "partial-submission"


# Rejection reasons ordered least to most specific. A record for another part
# says nothing about this unit; a record that named the right material and had
# just gone out of window is the one worth reporting.
_REASON_ORDER = (
    "does not carry",
    "cannot discharge",
    "family",
    "covers part",
    "covers date code",
    "covers lot",
    "later than",
    "months old",
)


def _reason_rank(reason):
    """Return how specific a rejection reason is, -1 when it is unranked."""
    rank = -1
    for position, token in enumerate(_REASON_ORDER):
        if token in reason:
            rank = position
    return rank


def assess_lot_acceptance_submission(spec):
    """Return the clause 5.3.5 submission plan for one Class 2 delivery.

    spec keys: lines, submission_day, optional records, required_groups,
    draw_table and validity_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lines", "submission_day"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    asked = parse_day("submission_day", spec["submission_day"])
    records = spec.get("records", [])
    if not isinstance(records, (list, tuple)):
        raise ValueError("spec['records'] must be a sequence of acceptance records")
    required = spec.get("required_groups", TEST_GROUPS)
    if not isinstance(required, (list, tuple, set, frozenset)) or not required:
        raise ValueError("spec['required_groups'] must be a non-empty sequence")
    required = [_group_name("required group", item) for item in required]
    draw_table = spec.get("draw_table")
    windows = spec.get("validity_months")
    units = submission_units(spec["lines"])

    planned = []
    findings = []
    for unit in units:
        groups = {}
        open_groups = []
        for name in required:
            covered_by = None
            reason = "no acceptance record carries the %s group for this unit" % name
            rejected = []
            for index, record in enumerate(records):
                ok, why = evidence_covers_group(record, unit, name, asked, windows)
                if ok:
                    covered_by = record.get("reference", "record[%d]" % index)
                    reason = why
                    rejected = []
                    break
                rejected.append(why)
            if covered_by is None and rejected:
                reason = max(rejected, key=_reason_rank)
            draw = 0 if covered_by else group_draw(unit["quantity"], name, draw_table)
            groups[name] = {
                "group": name,
                "covered_by": covered_by,
                "reason": reason,
                "rejected": rejected,
                "draw": draw,
                "status": "covered" if covered_by else "submit",
            }
            if covered_by is None:
                open_groups.append(name)
        entry = dict(unit)
        entry["groups"] = groups
        entry["open_groups"] = open_groups
        entry["draw_pieces"] = sum(groups[name]["draw"] for name in required)
        entry["route"] = unit_route(open_groups, required)
        planned.append(entry)
        if open_groups:
            findings.append(
                "%s date code %s (%d pieces) owes the %s group and draws %d pieces"
                % (
                    unit["part_number"],
                    unit["date_code"],
                    unit["quantity"],
                    ", ".join(open_groups),
                    entry["draw_pieces"],
                )
            )
    outstanding = [entry for entry in planned if entry["open_groups"]]
    if len(units) > 1:
        findings.append(
            "delivery breaks into %d submission units; each takes its own submission"
            % len(units)
        )
    return {
        "submission_day": asked.isoformat(),
        "required_groups": list(required),
        "units": planned,
        "outstanding": [entry["date_code"] for entry in outstanding],
        "outstanding_pieces": sum(entry["draw_pieces"] for entry in outstanding),
        "complete": not outstanding,
        "disposition": (
            "all-units-covered" if not outstanding else "submit-outstanding-groups"
        ),
        "findings": findings,
    }
