"""Nonconformance and failure control for lowest-assurance-class EEE parts.

Anchor: ECSS-Q-ST-60C clause 6.5.2 (operating a nonconformance and failure
control system for class 3 parts across a programme). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the report, then decide who owns it. At class 3 the supplier's own
   system carries a finding raised at or before goods-in on a part in an
   uncritical function; everything past that point is the programme's.
2. Categorize the report minor, major or critical from the effect, the point at
   which it was detected and the criticality of the function the part sits in.
3. Derive the dispositions the category allows. A critical report has no
   use-as-is route at this class, and the records each disposition earns are
   derived with it.
4. Set the depth of the failure analysis from the mechanism, the category and
   whether the mode has already repeated.
5. Widen containment to the coarsest identity the receipt records actually
   support, because a class 3 delivery frequently carries no lot identity at
   all, and widen one step further again when the mechanism is still unknown.
6. Count occurrences of the same mode in the rolling window; reaching the
   threshold turns the finding into a case for reviewing the assurance class
   the part was bought at.
7. Count response working days against the deadline the category sets.
"""

import datetime

__all__ = [
    "EFFECT_CATEGORIES",
    "DETECTION_POINTS",
    "FUNCTION_CRITICALITIES",
    "MECHANISMS",
    "CATEGORIES",
    "CATEGORY_DISPOSITIONS",
    "CATEGORY_RESPONSE_DAYS",
    "DISPOSITION_RECORDS",
    "ANALYSIS_DEPTHS",
    "IDENTITY_DEPTHS",
    "CONTAINMENT_SCOPES",
    "RECURRENCE_THRESHOLD",
    "RECURRENCE_WINDOW_DAYS",
    "working_days_between",
    "report_ownership",
    "categorize_report",
    "allowed_dispositions",
    "disposition_records",
    "analysis_depth",
    "containment_scope",
    "containment_units",
    "recurrence_state",
    "assess_class_3_nonconformance",
]

# Effect on the part or on the assembly, least to most severe.
EFFECT_CATEGORIES = {
    "documentation-only": 0,
    "cosmetic": 1,
    "parametric-drift": 2,
    "out-of-specification": 3,
    "functional-failure": 4,
}

# Where the finding surfaced, earliest to latest.
DETECTION_POINTS = {
    "supplier-site": 0,
    "goods-in": 1,
    "board-assembly": 2,
    "unit-test": 3,
    "system-test": 4,
    "in-service": 5,
}

# What the function the part sits in would lose.
FUNCTION_CRITICALITIES = {
    "non-critical": 0,
    "mission-degrading": 1,
    "mission-critical": 2,
    "safety-critical": 3,
}

# Mechanism behind the finding, as understood when the report is dispositioned.
MECHANISMS = ("unknown", "handling-induced", "lot-related", "design-related")

CATEGORIES = ("minor", "major", "critical")

# Dispositions each category opens. A critical report has no use-as-is route at
# this assurance class: the part leaves the build or is replaced by one bought
# at a higher class.
CATEGORY_DISPOSITIONS = {
    "minor": ("use-as-is", "rework", "return-to-supplier", "scrap"),
    "major": ("rework", "repair", "return-to-supplier", "scrap", "use-as-is"),
    "critical": ("return-to-supplier", "scrap", "replace-with-upgraded-part"),
}

# Working days from raising to a recorded response, by category.
CATEGORY_RESPONSE_DAYS = {"minor": 20, "major": 10, "critical": 5}

# Records and signatures each disposition earns, by category.
DISPOSITION_RECORDS = {
    ("minor", "use-as-is"): ("product-assurance",),
    ("minor", "rework"): ("product-assurance",),
    ("minor", "return-to-supplier"): ("product-assurance",),
    ("minor", "scrap"): ("product-assurance",),
    ("major", "use-as-is"): (
        "product-assurance",
        "parts-control-board",
        "application-justification",
    ),
    ("major", "repair"): ("product-assurance", "parts-control-board"),
    ("major", "rework"): ("product-assurance",),
    ("major", "return-to-supplier"): ("product-assurance",),
    ("major", "scrap"): ("product-assurance",),
    ("critical", "return-to-supplier"): ("product-assurance", "parts-control-board"),
    ("critical", "scrap"): ("product-assurance", "parts-control-board"),
    ("critical", "replace-with-upgraded-part"): (
        "product-assurance",
        "parts-control-board",
        "customer",
    ),
}

# Depth of failure analysis owed, shallowest to deepest.
ANALYSIS_DEPTHS = (
    "none",
    "electrical-characterization",
    "construction-analysis",
    "full-root-cause",
)

# How finely the receipt records let a delivered unit be named, coarsest first.
IDENTITY_DEPTHS = {
    "part-number": 0,
    "date-code": 1,
    "receipt-batch": 2,
    "lot": 3,
}

# Containment scopes, narrowest to widest.
CONTAINMENT_SCOPES = (
    "affected-units-only",
    "same-lot",
    "same-receipt-batch",
    "same-date-code",
    "all-stock-of-part-number",
)

# Two of the same mode inside the window is already systematic at class 3,
# because nothing lot-level was screened out before the parts were issued.
RECURRENCE_THRESHOLD = 2
RECURRENCE_WINDOW_DAYS = 180


def _parse_date(value, label):
    """Return an ISO date string or a date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _weekdays_to(day):
    """Return the count of Mon-Fri days from the proleptic epoch up to day."""
    ordinal = day.toordinal()
    whole_weeks, remainder = divmod(ordinal, 7)
    return whole_weeks * 5 + min(remainder, 5)


def working_days_between(start, end):
    """Return the Mon-Fri days strictly after start up to and including end."""
    first = _parse_date(start, "start")
    last = _parse_date(end, "end")
    if last < first:
        raise ValueError("end date %s precedes start date %s" % (last, first))
    return _weekdays_to(last) - _weekdays_to(first)


def _check(value, table, label):
    if value not in table:
        raise ValueError("%s must be one of %s, got %r" % (label, sorted(table), value))
    return value


def report_ownership(detection_point, function_criticality, effect):
    """Return 'supplier-resolved' or 'programme-controlled' for one report.

    At class 3 the supplier's own control system is allowed to carry a finding
    that never left the supply chain and never touched a critical function.
    Once the part has passed goods-in, or the function or the effect is serious,
    the programme takes the report over itself.
    """
    _check(detection_point, DETECTION_POINTS, "detection_point")
    _check(function_criticality, FUNCTION_CRITICALITIES, "function_criticality")
    _check(effect, EFFECT_CATEGORIES, "effect")
    if DETECTION_POINTS[detection_point] > DETECTION_POINTS["goods-in"]:
        return "programme-controlled"
    if (
        FUNCTION_CRITICALITIES[function_criticality]
        >= FUNCTION_CRITICALITIES["mission-critical"]
    ):
        return "programme-controlled"
    if EFFECT_CATEGORIES[effect] >= EFFECT_CATEGORIES["out-of-specification"]:
        return "programme-controlled"
    return "supplier-resolved"


def categorize_report(effect, detection_point, function_criticality):
    """Return 'minor', 'major' or 'critical' for one report.

    The three inputs are read together. A functional failure found in service,
    and anything at or past out-of-specification in a safety-critical function,
    is critical. Below that, severity of effect, lateness of detection and
    criticality of function each on their own can raise a report to major.
    """
    _check(effect, EFFECT_CATEGORIES, "effect")
    _check(detection_point, DETECTION_POINTS, "detection_point")
    _check(function_criticality, FUNCTION_CRITICALITIES, "function_criticality")
    severity = EFFECT_CATEGORIES[effect]
    lateness = DETECTION_POINTS[detection_point]
    criticality = FUNCTION_CRITICALITIES[function_criticality]
    if severity >= EFFECT_CATEGORIES["out-of-specification"]:
        if criticality >= FUNCTION_CRITICALITIES["safety-critical"]:
            return "critical"
        if (
            severity == EFFECT_CATEGORIES["functional-failure"]
            and lateness >= DETECTION_POINTS["in-service"]
        ):
            return "critical"
        return "major"
    if severity == EFFECT_CATEGORIES["documentation-only"]:
        return "minor"
    if lateness >= DETECTION_POINTS["unit-test"]:
        return "major"
    if criticality >= FUNCTION_CRITICALITIES["mission-critical"]:
        return "major"
    return "minor"


def allowed_dispositions(category):
    """Return the dispositions a category opens."""
    _check(category, CATEGORY_DISPOSITIONS, "category")
    return CATEGORY_DISPOSITIONS[category]


def disposition_records(category, disposition):
    """Return the records and signatures a disposition earns under a category."""
    _check(category, CATEGORY_DISPOSITIONS, "category")
    if disposition not in CATEGORY_DISPOSITIONS[category]:
        raise ValueError(
            "disposition %r is not open to a %s report; open: %s"
            % (disposition, category, list(CATEGORY_DISPOSITIONS[category]))
        )
    return DISPOSITION_RECORDS[(category, disposition)]


def analysis_depth(mechanism, category, recurrent):
    """Return how deep the failure analysis owed by this report goes.

    A one-off handling mark on a minor report owes nothing. A mode that has
    already repeated, a design-related mechanism and any critical report owe a
    full root cause. Otherwise a lot-related or major finding owes construction
    analysis, and anything left owes electrical characterization.
    """
    if mechanism not in MECHANISMS:
        raise ValueError(
            "mechanism must be one of %s, got %r" % (list(MECHANISMS), mechanism)
        )
    _check(category, CATEGORY_DISPOSITIONS, "category")
    if not isinstance(recurrent, bool):
        raise ValueError("recurrent must be a bool, got %r" % (recurrent,))
    if recurrent or mechanism == "design-related" or category == "critical":
        return "full-root-cause"
    if category == "minor" and mechanism == "handling-induced":
        return "none"
    if mechanism == "lot-related" or category == "major":
        return "construction-analysis"
    return "electrical-characterization"


def containment_scope(identity_depth, mechanism):
    """Return the containment scope this report earns.

    Containment follows the records, not the shelf. A design-related mechanism
    takes every unit of the part number. A known lot-related mechanism takes the
    finest identity the receipt records support. An unknown mechanism is
    contained one identity step wider than a lot-related one, because at this
    class nothing screened the neighbouring units either.
    """
    _check(identity_depth, IDENTITY_DEPTHS, "identity_depth")
    if mechanism not in MECHANISMS:
        raise ValueError(
            "mechanism must be one of %s, got %r" % (list(MECHANISMS), mechanism)
        )
    if mechanism == "handling-induced":
        return "affected-units-only"
    if mechanism == "design-related":
        return "all-stock-of-part-number"
    by_depth = {
        "lot": "same-lot",
        "receipt-batch": "same-receipt-batch",
        "date-code": "same-date-code",
        "part-number": "all-stock-of-part-number",
    }
    scope = by_depth[identity_depth]
    if mechanism == "unknown":
        index = CONTAINMENT_SCOPES.index(scope)
        scope = CONTAINMENT_SCOPES[min(index + 1, len(CONTAINMENT_SCOPES) - 1)]
    return scope


def _unit_key(entry, key):
    value = entry.get(key)
    if value is None:
        return None
    return str(value).strip().upper()


def containment_units(scope, failing_unit, inventory):
    """Return the unit identifiers the scope impounds, failing unit first."""
    if scope not in CONTAINMENT_SCOPES:
        raise ValueError(
            "scope must be one of %s, got %r" % (list(CONTAINMENT_SCOPES), scope)
        )
    if not isinstance(failing_unit, dict):
        raise ValueError("failing_unit must be a mapping")
    for key in ("unit_id", "part_number"):
        if key not in failing_unit:
            raise ValueError("failing_unit missing required key '%s'" % key)
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of unit records")
    part = _unit_key(failing_unit, "part_number")
    held = [str(failing_unit["unit_id"]).strip()]
    if scope == "affected-units-only":
        return tuple(held)
    for index, entry in enumerate(inventory):
        if not isinstance(entry, dict):
            raise ValueError("inventory[%d] must be a mapping" % index)
        for key in ("unit_id", "part_number"):
            if key not in entry:
                raise ValueError(
                    "inventory[%d] missing required key '%s'" % (index, key)
                )
        unit_id = str(entry["unit_id"]).strip()
        if unit_id in held:
            continue
        if _unit_key(entry, "part_number") != part:
            continue
        if scope == "all-stock-of-part-number":
            held.append(unit_id)
            continue
        axis = {
            "same-lot": "lot_id",
            "same-receipt-batch": "receipt_batch",
            "same-date-code": "date_code",
        }[scope]
        wanted = _unit_key(failing_unit, axis)
        if wanted is None:
            raise ValueError(
                "failing_unit carries no '%s' but scope %s needs one" % (axis, scope)
            )
        if _unit_key(entry, axis) == wanted:
            held.append(unit_id)
    return tuple(held)


def recurrence_state(part_number, failure_mode, history, as_of_date):
    """Return the recurrence verdict for one part number and failure mode."""
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("part_number must be a non-empty string")
    if not isinstance(failure_mode, str) or not failure_mode.strip():
        raise ValueError("failure_mode must be a non-empty string")
    if not isinstance(history, (list, tuple)):
        raise ValueError("history must be a sequence of past report records")
    as_of = _parse_date(as_of_date, "as_of_date")
    window_start = as_of - datetime.timedelta(days=RECURRENCE_WINDOW_DAYS)
    part = part_number.strip().upper()
    mode = failure_mode.strip().lower()
    dates = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            raise ValueError("history[%d] must be a mapping" % index)
        for key in ("part_number", "failure_mode", "raised_date"):
            if key not in entry:
                raise ValueError("history[%d] missing required key '%s'" % (index, key))
        raised = _parse_date(entry["raised_date"], "history[%d]['raised_date']" % index)
        if raised > as_of:
            raise ValueError("history[%d] was raised after as_of_date" % index)
        if str(entry["part_number"]).strip().upper() != part:
            continue
        if str(entry["failure_mode"]).strip().lower() != mode:
            continue
        if raised < window_start:
            continue
        dates.append(raised.isoformat())
    count = len(dates)
    systematic = count >= RECURRENCE_THRESHOLD
    return {
        "part_number": part,
        "failure_mode": mode,
        "occurrences_in_window": count,
        "window_days": RECURRENCE_WINDOW_DAYS,
        "threshold": RECURRENCE_THRESHOLD,
        "systematic": systematic,
        "occurrence_dates": tuple(sorted(dates)),
        "escalation": (
            "assurance-class-upgrade-review" if systematic else "project-level"
        ),
    }


def _validate_report(report):
    """Return a normalised class 3 nonconformance report."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    required = (
        "report_id",
        "unit_id",
        "part_number",
        "effect",
        "detection_point",
        "function_criticality",
        "mechanism",
        "identity_depth",
        "failure_mode",
        "raised_date",
    )
    for key in required:
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    for key in ("report_id", "unit_id", "part_number", "failure_mode"):
        value = report[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("report['%s'] must be a non-empty string" % key)
    quantity = report.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("report['quantity'] must be a positive integer")
    mechanism = report["mechanism"]
    if mechanism not in MECHANISMS:
        raise ValueError(
            "report['mechanism'] must be one of %s, got %r" % (list(MECHANISMS), mechanism)
        )
    return {
        "report_id": report["report_id"].strip(),
        "unit_id": report["unit_id"].strip(),
        "part_number": report["part_number"].strip().upper(),
        "lot_id": report.get("lot_id"),
        "receipt_batch": report.get("receipt_batch"),
        "date_code": report.get("date_code"),
        "effect": _check(report["effect"], EFFECT_CATEGORIES, "report['effect']"),
        "detection_point": _check(
            report["detection_point"], DETECTION_POINTS, "report['detection_point']"
        ),
        "function_criticality": _check(
            report["function_criticality"],
            FUNCTION_CRITICALITIES,
            "report['function_criticality']",
        ),
        "mechanism": mechanism,
        "identity_depth": _check(
            report["identity_depth"], IDENTITY_DEPTHS, "report['identity_depth']"
        ),
        "failure_mode": report["failure_mode"].strip().lower(),
        "quantity": quantity,
        "raised_date": _parse_date(report["raised_date"], "raised_date"),
        "proposed_disposition": report.get("proposed_disposition"),
        "analysis_reference": report.get("analysis_reference"),
        "records_held": tuple(report.get("records_held", ())),
        "responded_date": report.get("responded_date"),
    }


def assess_class_3_nonconformance(report, inventory, history, as_of_date):
    """Run the full clause 6.5.2 control assessment over one class 3 report."""
    record = _validate_report(report)
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of unit records")
    if not isinstance(history, (list, tuple)):
        raise ValueError("history must be a sequence of past report records")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < record["raised_date"]:
        raise ValueError("as_of_date precedes the date the report was raised")

    ownership = report_ownership(
        record["detection_point"], record["function_criticality"], record["effect"]
    )
    category = categorize_report(
        record["effect"], record["detection_point"], record["function_criticality"]
    )
    recurrence = recurrence_state(
        record["part_number"], record["failure_mode"], history, as_of
    )
    depth = analysis_depth(record["mechanism"], category, recurrence["systematic"])
    scope = containment_scope(record["identity_depth"], record["mechanism"])
    held = containment_units(
        scope,
        {
            "unit_id": record["unit_id"],
            "part_number": record["part_number"],
            "lot_id": record["lot_id"],
            "receipt_batch": record["receipt_batch"],
            "date_code": record["date_code"],
        },
        inventory,
    )

    findings = []
    notes = []
    dispositions = allowed_dispositions(category)
    proposed = record["proposed_disposition"]
    required_records = ()
    if proposed is None:
        findings.append("report %s carries no proposed disposition" % record["report_id"])
    elif proposed not in dispositions:
        findings.append(
            "disposition %s is not open to a %s report on %s"
            % (proposed, category, record["report_id"])
        )
        if category == "critical" and proposed == "use-as-is":
            notes.append(
                "a critical class 3 finding has no use-as-is route; the part is "
                "removed or replaced by one bought at a higher assurance class"
            )
    else:
        required_records = disposition_records(category, proposed)
        missing = [r for r in required_records if r not in record["records_held"]]
        if missing:
            findings.append(
                "report %s is missing the %s record(s) its %s disposition earns"
                % (record["report_id"], ", ".join(missing), proposed)
            )

    if depth != "none" and not record["analysis_reference"]:
        findings.append(
            "report %s owes a %s failure analysis and none is referenced"
            % (record["report_id"], depth)
        )

    if ownership == "supplier-resolved":
        notes.append(
            "the finding never left the supply chain and the supplier system may "
            "carry it, with the outcome recorded against the delivery"
        )

    if record["responded_date"] is None:
        response_days = working_days_between(record["raised_date"], as_of)
        response_state = "open"
    else:
        response_days = working_days_between(
            record["raised_date"], record["responded_date"]
        )
        response_state = "responded"
    deadline = CATEGORY_RESPONSE_DAYS[category]
    within_deadline = response_days <= deadline
    if not within_deadline:
        findings.append(
            "report %s has run %d working days against a %d day limit"
            % (record["report_id"], response_days, deadline)
        )

    if recurrence["systematic"]:
        findings.append(
            "failure mode '%s' on %s has recurred %d times in %d days; the "
            "assurance class the part is bought at is the open question, not the unit"
            % (
                recurrence["failure_mode"],
                record["part_number"],
                recurrence["occurrences_in_window"],
                RECURRENCE_WINDOW_DAYS,
            )
        )

    if len(held) > 1:
        notes.append(
            "%d further unit(s) fall inside the %s containment scope"
            % (len(held) - 1, scope)
        )

    if record["detection_point"] == "in-service":
        findings.append(
            "report %s was raised in service; an impact statement is owed to the "
            "customer alongside the disposition" % record["report_id"]
        )

    return {
        "report_id": record["report_id"],
        "ownership": ownership,
        "category": category,
        "allowed_dispositions": dispositions,
        "proposed_disposition": proposed,
        "required_records": required_records,
        "analysis_depth": depth,
        "containment_scope": scope,
        "contained_units": held,
        "contained_unit_count": len(held),
        "recurrence": recurrence,
        "escalation": recurrence["escalation"],
        "response_working_days": response_days,
        "response_deadline_days": deadline,
        "response_state": response_state,
        "within_deadline": within_deadline,
        "findings": findings,
        "notes": notes,
        "closeable": not findings and response_state == "responded",
    }
