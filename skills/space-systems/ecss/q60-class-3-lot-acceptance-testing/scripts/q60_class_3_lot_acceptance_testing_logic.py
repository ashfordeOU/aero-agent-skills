"""Lot acceptance submission planning for a delivered Class 3 EEE lot.

Anchor: ECSS-Q-ST-60C clause 6.3.5 -- submitting each Class 3 lot or date code
for lot acceptance verification. Paraphrased into an implementable procedure;
no standard text is reproduced.

What this module decides
------------------------
Which parts of a Class 3 delivery still owe a lot acceptance submission, how
many pieces each outstanding submission draws, and whether the delivery can
give those pieces up at all.

1. Population. A Class 3 submission is owed per part number and date code. Two
   shipments of the same part number built in different weeks are two
   populations, and merging them would let one submission stand for pieces it
   never saw.
2. Credit. A manufacturer lot acceptance report discharges a unit only while it
   names the same part number, was raised on a date code inside the production
   window around the submitted one, and is still inside its validity. A report
   that fails any of the three is reported with the reason it failed, never
   quietly stretched to cover the unit.
3. Reduction. A unit from a preferred source, below the quantity ceiling, draws
   a reduced submission rather than a full one. The reduction is a fraction of
   the full draw and never falls under the floor.
4. Sizing. Draws are sized in exact rational arithmetic and rounded up, so the
   same delivery gives the same plan on every platform rather than depending on
   how a division rounded.
5. Feasibility. Submission pieces are consumed. A unit whose spares cannot cover
   its draw is reported as infeasible instead of being under-drawn in silence.
"""

from datetime import date
from fractions import Fraction

__all__ = [
    "ROUTES",
    "DEFAULT_DRAW_FRACTION",
    "MINIMUM_DRAW",
    "MAXIMUM_DRAW",
    "REDUCED_DRAW_FACTOR",
    "REDUCED_QUANTITY_CEILING",
    "DEFAULT_PRODUCTION_WINDOW_WEEKS",
    "DEFAULT_EVIDENCE_VALIDITY_MONTHS",
    "LARGE_DRAW_THRESHOLD",
    "share",
    "parse_day",
    "date_code_week_start",
    "week_distance",
    "months_elapsed",
    "submission_units",
    "submission_draw",
    "reduced_draw",
    "acceptance_number",
    "evidence_covers_unit",
    "unit_route",
    "assess_lot_acceptance_submission",
]

# The three ways a Class 3 unit leaves the plan, most favourable first.
ROUTES = ("manufacturer-data-credit", "reduced-submission", "full-submission")

# Share of a unit drawn for a full Class 3 submission.
DEFAULT_DRAW_FRACTION = Fraction(1, 20)

# No submission draws fewer pieces than this unless the unit is smaller.
MINIMUM_DRAW = 5

# Above this a wider draw buys little; the submission is about the population.
MAXIMUM_DRAW = 45

# A reduced submission draws this share of the full draw.
REDUCED_DRAW_FACTOR = Fraction(1, 2)

# A preferred-source unit larger than this draws a full submission anyway.
REDUCED_QUANTITY_CEILING = 250

# Manufacturer evidence may sit this many weeks either side of the date code.
DEFAULT_PRODUCTION_WINDOW_WEEKS = 13

# Evidence older than this on the planning day no longer discharges a unit.
DEFAULT_EVIDENCE_VALIDITY_MONTHS = 24

# A draw at or above this size carries an acceptance number of one.
LARGE_DRAW_THRESHOLD = 20


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


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def _share(label, value):
    """Return value as a Fraction strictly inside (0, 1]."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ValueError("%s must be an int or Fraction share, got %r" % (label, value))
    share = Fraction(value)
    if share <= 0 or share > 1:
        raise ValueError("%s must lie in (0, 1], got %s" % (label, share))
    return share


def _ceil(value):
    """Return the ceiling of a Fraction as an int, without float rounding."""
    return -(-value.numerator // value.denominator)


def share(numerator, denominator):
    """Return an exact rational share built from two integers.

    Callers hand sizing shares in as rationals so the arithmetic stays exact.
    This builds one without the caller reaching for a module of its own; the
    range is checked where the share is used, not here, so an out-of-range
    share can still be constructed and refused at the point that cares.
    """
    for label, value in (("numerator", numerator), ("denominator", denominator)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if denominator == 0:
        raise ValueError("denominator must not be zero")
    return Fraction(numerator, denominator)


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def date_code_week_start(date_code, century_base=2000):
    """Return the first day of the build week a YYWW date code names.

    A week number a calendar year does not have is refused rather than rolled
    into the next year, which would silently move the unit to another window.
    """
    text = _text("date_code", date_code)
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (date_code,))
    base = _count("century_base", century_base)
    if base % 100:
        raise ValueError("century_base must be a whole century, got %d" % base)
    year = base + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (date_code,))
    try:
        return date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError("calendar year %d has no week %02d" % (year, week))


def week_distance(first_code, second_code, century_base=2000):
    """Return the whole weeks between two date codes, unsigned."""
    first = date_code_week_start(first_code, century_base)
    second = date_code_week_start(second_code, century_base)
    return abs((first - second).days) // 7


def months_elapsed(start_day, end_day):
    """Return the whole calendar months from start_day to end_day."""
    start = parse_day("start_day", start_day)
    end = parse_day("end_day", end_day)
    if end < start:
        raise ValueError("end day %s precedes start day %s" % (end, start))
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def submission_units(lines, century_base=2000):
    """Return one submission unit per part number and date code.

    lines: sequence of mappings with part_number, date_code, quantity and
    optional build_demand and preferred_source. Lines that share a part number
    and a date code are one unit; a unit counts as preferred-source only when
    every line feeding it declares one.
    """
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence of delivery lines")
    merged = {}
    order = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ValueError("lines[%d] must be a mapping" % index)
        for key in ("part_number", "date_code", "quantity"):
            if key not in line:
                raise ValueError("lines[%d] missing required key '%s'" % (index, key))
        part = _text("lines[%d].part_number" % index, line["part_number"])
        code = _text("lines[%d].date_code" % index, line["date_code"])
        date_code_week_start(code, century_base)
        quantity = _count("lines[%d].quantity" % index, line["quantity"])
        if quantity < 1:
            raise ValueError("lines[%d].quantity must be at least 1" % index)
        demand = _count("lines[%d].build_demand" % index, line.get("build_demand", 0))
        if demand > quantity:
            raise ValueError(
                "lines[%d] build demand %d exceeds the delivered quantity %d"
                % (index, demand, quantity)
            )
        preferred = _flag(
            "lines[%d].preferred_source" % index, line.get("preferred_source", False)
        )
        key = (part, code)
        if key not in merged:
            merged[key] = {
                "part_number": part,
                "date_code": code,
                "quantity": 0,
                "build_demand": 0,
                "preferred_source": True,
            }
            order.append(key)
        unit = merged[key]
        unit["quantity"] += quantity
        unit["build_demand"] += demand
        unit["preferred_source"] = unit["preferred_source"] and preferred
    units = []
    for key in sorted(order):
        unit = merged[key]
        unit["spare"] = unit["quantity"] - unit["build_demand"]
        units.append(unit)
    return units


def submission_draw(
    quantity,
    draw_fraction=DEFAULT_DRAW_FRACTION,
    minimum=MINIMUM_DRAW,
    maximum=MAXIMUM_DRAW,
):
    """Return the pieces a full Class 3 submission draws from a unit.

    Exact rational arithmetic rounded up, raised to the floor, held under the
    cap and never above the unit itself.
    """
    held = _count("quantity", quantity)
    if held < 1:
        raise ValueError("quantity must be at least 1, got %d" % held)
    share = _share("draw_fraction", draw_fraction)
    floor_draw = _count("minimum", minimum)
    cap = _count("maximum", maximum)
    if floor_draw < 1:
        raise ValueError("minimum must be at least 1, got %d" % floor_draw)
    if cap < floor_draw:
        raise ValueError("maximum %d is below minimum %d" % (cap, floor_draw))
    drawn = _ceil(Fraction(held) * share)
    if drawn < floor_draw:
        drawn = floor_draw
    if drawn > cap:
        drawn = cap
    if drawn > held:
        drawn = held
    return drawn


def reduced_draw(full_draw, factor=REDUCED_DRAW_FACTOR, minimum=MINIMUM_DRAW):
    """Return the pieces a reduced Class 3 submission draws."""
    full = _count("full_draw", full_draw)
    if full < 1:
        raise ValueError("full_draw must be at least 1, got %d" % full)
    share = _share("factor", factor)
    floor_draw = _count("minimum", minimum)
    if floor_draw < 1:
        raise ValueError("minimum must be at least 1, got %d" % floor_draw)
    drawn = _ceil(Fraction(full) * share)
    if drawn < floor_draw:
        drawn = floor_draw
    if drawn > full:
        drawn = full
    return drawn


def acceptance_number(draw, threshold=LARGE_DRAW_THRESHOLD):
    """Return the failures a submission of this size may carry and still pass."""
    drawn = _count("draw", draw)
    if drawn < 1:
        raise ValueError("draw must be at least 1, got %d" % drawn)
    limit = _count("threshold", threshold)
    if limit < 1:
        raise ValueError("threshold must be at least 1, got %d" % limit)
    return 1 if drawn >= limit else 0


def evidence_covers_unit(
    unit,
    record,
    as_of_day,
    window_weeks=DEFAULT_PRODUCTION_WINDOW_WEEKS,
    validity_months=DEFAULT_EVIDENCE_VALIDITY_MONTHS,
    century_base=2000,
):
    """Return whether one manufacturer report discharges one submission unit.

    record keys: part_number, date_code and issued_day. The reasons list names
    every test the record failed, so a near miss is visible in the plan.
    """
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping")
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("part_number", "date_code"):
        if key not in unit:
            raise ValueError("unit missing required key '%s'" % key)
    for key in ("part_number", "date_code", "issued_day"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    window = _count("window_weeks", window_weeks)
    validity = _count("validity_months", validity_months)
    if validity < 1:
        raise ValueError("validity_months must be at least 1, got %d" % validity)
    unit_part = _text("unit.part_number", unit["part_number"])
    record_part = _text("record.part_number", record["part_number"])
    distance = week_distance(unit["date_code"], record["date_code"], century_base)
    age = months_elapsed(record["issued_day"], as_of_day)
    reasons = []
    if unit_part.lower() != record_part.lower():
        reasons.append(
            "report names part '%s', the unit is part '%s'" % (record_part, unit_part)
        )
    if distance > window:
        reasons.append(
            "report date code sits %d week(s) from the unit, outside the %d week window"
            % (distance, window)
        )
    if age > validity:
        reasons.append(
            "report is %d month(s) old against a %d month validity" % (age, validity)
        )
    return {
        "record_part_number": record_part,
        "week_distance": distance,
        "age_months": age,
        "credited": not reasons,
        "reasons": reasons,
    }


def unit_route(unit, records, as_of_day, options=None):
    """Return the submission route and draw for one unit.

    Credit is tried first, then the reduction, then a full submission. A unit
    that cannot spare its draw keeps its route but is reported infeasible.
    """
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping")
    for key in ("part_number", "date_code", "quantity", "spare"):
        if key not in unit:
            raise ValueError("unit missing required key '%s'" % key)
    if records is None:
        records = ()
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of manufacturer reports")
    settings = dict(options or {})
    if not isinstance(settings, dict):
        raise ValueError("options must be a mapping")
    window = settings.get("production_window_weeks", DEFAULT_PRODUCTION_WINDOW_WEEKS)
    validity = settings.get("validity_months", DEFAULT_EVIDENCE_VALIDITY_MONTHS)
    century_base = settings.get("century_base", 2000)
    ceiling = _count(
        "reduced_quantity_ceiling",
        settings.get("reduced_quantity_ceiling", REDUCED_QUANTITY_CEILING),
    )
    assessments = []
    credited = None
    for record in records:
        verdict = evidence_covers_unit(
            unit, record, as_of_day, window, validity, century_base
        )
        assessments.append(verdict)
        if verdict["credited"] and credited is None:
            credited = verdict
    full = submission_draw(
        unit["quantity"],
        settings.get("draw_fraction", DEFAULT_DRAW_FRACTION),
        settings.get("minimum_draw", MINIMUM_DRAW),
        settings.get("maximum_draw", MAXIMUM_DRAW),
    )
    preferred = _flag("unit.preferred_source", unit.get("preferred_source", False))
    if credited is not None:
        route = "manufacturer-data-credit"
        draw = 0
    elif preferred and unit["quantity"] <= ceiling:
        route = "reduced-submission"
        draw = reduced_draw(
            full,
            settings.get("reduced_draw_factor", REDUCED_DRAW_FACTOR),
            settings.get("minimum_draw", MINIMUM_DRAW),
        )
    else:
        route = "full-submission"
        draw = full
    spare = _count("unit.spare", unit["spare"])
    feasible = draw <= spare
    findings = []
    if not feasible:
        findings.append(
            "part %s date code %s owes %d piece(s) but only %d spare(s) remain"
            % (unit["part_number"], unit["date_code"], draw, spare)
        )
    return {
        "part_number": unit["part_number"],
        "date_code": unit["date_code"],
        "quantity": unit["quantity"],
        "spare": spare,
        "preferred_source": preferred,
        "full_draw": full,
        "route": route,
        "draw": draw,
        "acceptance_number": acceptance_number(draw) if draw else 0,
        "evidence": assessments,
        "feasible": feasible,
        "findings": findings,
    }


def assess_lot_acceptance_submission(spec):
    """Return the clause 6.3.5 submission plan for one Class 3 delivery.

    spec keys: delivery and as_of_day, optional evidence plus the sizing and
    window settings carried through to unit_route.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("delivery", "as_of_day"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    century_base = spec.get("century_base", 2000)
    options = {
        "production_window_weeks": spec.get(
            "production_window_weeks", DEFAULT_PRODUCTION_WINDOW_WEEKS
        ),
        "validity_months": spec.get(
            "validity_months", DEFAULT_EVIDENCE_VALIDITY_MONTHS
        ),
        "reduced_quantity_ceiling": spec.get(
            "reduced_quantity_ceiling", REDUCED_QUANTITY_CEILING
        ),
        "draw_fraction": spec.get("draw_fraction", DEFAULT_DRAW_FRACTION),
        "minimum_draw": spec.get("minimum_draw", MINIMUM_DRAW),
        "maximum_draw": spec.get("maximum_draw", MAXIMUM_DRAW),
        "reduced_draw_factor": spec.get("reduced_draw_factor", REDUCED_DRAW_FACTOR),
        "century_base": century_base,
    }
    units = submission_units(spec["delivery"], century_base)
    records = spec.get("evidence", ())
    routed = [unit_route(unit, records, spec["as_of_day"], options) for unit in units]
    findings = []
    for entry in routed:
        findings.extend(entry["findings"])
    credited = [e for e in routed if e["route"] == "manufacturer-data-credit"]
    outstanding = [e for e in routed if e["route"] != "manufacturer-data-credit"]
    total_draw = sum(e["draw"] for e in routed)
    if not credited:
        findings.append(
            "no manufacturer lot acceptance report discharged any unit of this delivery"
        )
    return {
        "units": routed,
        "unit_count": len(routed),
        "credited_units": len(credited),
        "outstanding_units": len(outstanding),
        "total_draw": total_draw,
        "feasible": all(e["feasible"] for e in routed),
        "plan_complete": all(e["feasible"] for e in routed),
        "findings": findings,
    }
