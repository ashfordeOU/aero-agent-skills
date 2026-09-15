"""Nonconformance and failure control for the highest-assurance EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.5.2 (running a nonconformance and failure
control system over class 1 parts for a whole programme). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the nonconformance report: the lot it names, the effect it had and
   where the affected parts had already reached.
2. Grade the report as major or minor from the effect, the reach and the
   safety consequence, because the grade is what every later decision keys on.
3. Derive the dispositions the grade allows and the approval signatures each
   disposition earns, so a use-as-is on a major report cannot be signed by the
   project alone.
4. Decide whether a failure analysis is owed rather than optional, and widen
   containment to every sibling lot that shares the wafer lot or the date code
   of the failing lot.
5. Detect a failure mode that has repeated often enough inside the rolling
   window to be systematic rather than a one-off lot escape.
6. Count the closure working days from raising to closure and compare them
   with the deadline the grade sets.
"""

import datetime

__all__ = [
    "EFFECT_CATEGORIES",
    "REACH_STATES",
    "GRADE_DISPOSITIONS",
    "GRADE_CLOSURE_DAYS",
    "DISPOSITION_APPROVALS",
    "RECURRENCE_THRESHOLD",
    "RECURRENCE_WINDOW_DAYS",
    "grade_nonconformance",
    "allowed_dispositions",
    "approval_chain",
    "failure_analysis_required",
    "containment_lots",
    "recurrence_state",
    "working_days_between",
    "assess_nonconformance",
]

# Effect on the part or the assembly, ordered from the least to the most severe.
EFFECT_CATEGORIES = {
    "documentation-only": 0,
    "cosmetic": 1,
    "parametric-drift": 2,
    "out-of-specification": 3,
    "functional-failure": 4,
}

# How far the affected parts had already travelled when the report was raised.
REACH_STATES = {
    "incoming": 0,
    "stores": 1,
    "kitted": 2,
    "assembled": 3,
    "delivered": 4,
}

# Dispositions a grade allows. A major report cannot be dispositioned by
# accepting the part as it stands without the board and the customer.
GRADE_DISPOSITIONS = {
    "minor": ("use-as-is", "rework", "return-to-supplier", "scrap"),
    "major": ("repair", "rework", "return-to-supplier", "scrap", "use-as-is"),
}

# Working days from raising to closure, by grade.
GRADE_CLOSURE_DAYS = {"minor": 20, "major": 10}

# Signatures each disposition earns, by grade.
DISPOSITION_APPROVALS = {
    ("minor", "use-as-is"): ("product-assurance",),
    ("minor", "rework"): ("product-assurance",),
    ("minor", "return-to-supplier"): ("product-assurance",),
    ("minor", "scrap"): ("product-assurance",),
    ("major", "use-as-is"): ("product-assurance", "failure-review-board", "customer"),
    ("major", "repair"): ("product-assurance", "failure-review-board", "customer"),
    ("major", "rework"): ("product-assurance", "failure-review-board"),
    ("major", "return-to-supplier"): ("product-assurance", "failure-review-board"),
    ("major", "scrap"): ("product-assurance", "failure-review-board"),
}

# A failure mode seen this many times inside the window is systematic.
RECURRENCE_THRESHOLD = 3
RECURRENCE_WINDOW_DAYS = 365


def _parse_date(value, label):
    """Return an ISO date string or date object as a date."""
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


def _check_effect(effect):
    if effect not in EFFECT_CATEGORIES:
        raise ValueError(
            "effect must be one of %s, got %r" % (sorted(EFFECT_CATEGORIES), effect)
        )
    return effect


def _check_reach(reach):
    if reach not in REACH_STATES:
        raise ValueError(
            "reach must be one of %s, got %r" % (sorted(REACH_STATES), reach)
        )
    return reach


def grade_nonconformance(effect, reach, safety_relevant):
    """Return 'major' or 'minor' for one nonconformance report.

    A safety-relevant report is always major. So is any effect at or past the
    out-of-specification level, and so is anything that reached assembled or
    delivered hardware, because the escape itself is the severity.
    """
    _check_effect(effect)
    _check_reach(reach)
    if not isinstance(safety_relevant, bool):
        raise ValueError("safety_relevant must be a bool, got %r" % (safety_relevant,))
    if safety_relevant:
        return "major"
    if EFFECT_CATEGORIES[effect] >= EFFECT_CATEGORIES["out-of-specification"]:
        return "major"
    if REACH_STATES[reach] >= REACH_STATES["assembled"]:
        return "major"
    return "minor"


def allowed_dispositions(grade):
    """Return the dispositions a grade allows."""
    if grade not in GRADE_DISPOSITIONS:
        raise ValueError(
            "grade must be one of %s, got %r" % (sorted(GRADE_DISPOSITIONS), grade)
        )
    return GRADE_DISPOSITIONS[grade]


def approval_chain(grade, disposition):
    """Return the signatures a disposition earns under a grade."""
    if grade not in GRADE_DISPOSITIONS:
        raise ValueError(
            "grade must be one of %s, got %r" % (sorted(GRADE_DISPOSITIONS), grade)
        )
    if disposition not in GRADE_DISPOSITIONS[grade]:
        raise ValueError(
            "disposition %r is not allowed for a %s report; allowed: %s"
            % (disposition, grade, list(GRADE_DISPOSITIONS[grade]))
        )
    return DISPOSITION_APPROVALS[(grade, disposition)]


def failure_analysis_required(effect, grade):
    """Return True when the report owes a failure analysis.

    A functional failure always owes one, because the mechanism is what feeds
    the containment decision. So does any major report other than one raised
    purely on paperwork.
    """
    _check_effect(effect)
    if grade not in GRADE_DISPOSITIONS:
        raise ValueError(
            "grade must be one of %s, got %r" % (sorted(GRADE_DISPOSITIONS), grade)
        )
    if effect == "functional-failure":
        return True
    if grade == "major" and effect != "documentation-only":
        return True
    return False


def containment_lots(failing_lot, inventory):
    """Return the sibling lots that share the failing lot's origin.

    A lot is a sibling when it carries the same part number and either the same
    wafer lot or the same date code. The failing lot itself is always included.
    """
    if not isinstance(failing_lot, dict):
        raise ValueError("failing_lot must be a mapping")
    for key in ("lot_id", "part_number"):
        if key not in failing_lot:
            raise ValueError("failing_lot missing required key '%s'" % key)
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of lot records")
    part = str(failing_lot["part_number"]).strip().upper()
    wafer = failing_lot.get("wafer_lot")
    date_code = failing_lot.get("date_code")
    contained = [str(failing_lot["lot_id"]).strip()]
    for index, entry in enumerate(inventory):
        if not isinstance(entry, dict):
            raise ValueError("inventory[%d] must be a mapping" % index)
        for key in ("lot_id", "part_number"):
            if key not in entry:
                raise ValueError("inventory[%d] missing required key '%s'" % (index, key))
        lot_id = str(entry["lot_id"]).strip()
        if lot_id in contained:
            continue
        if str(entry["part_number"]).strip().upper() != part:
            continue
        same_wafer = bool(wafer) and entry.get("wafer_lot") == wafer
        same_code = bool(date_code) and entry.get("date_code") == date_code
        if same_wafer or same_code:
            contained.append(lot_id)
    return tuple(contained)


def recurrence_state(part_number, failure_mode, history, as_of_date):
    """Return the recurrence verdict for one part number and failure mode.

    History entries carry a part number, a failure mode and a raised date. Only
    entries inside the rolling window count; reaching the threshold makes the
    mode systematic and escalates it beyond the single lot.
    """
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
    matches = []
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
        matches.append(raised.isoformat())
    count = len(matches)
    return {
        "part_number": part,
        "failure_mode": mode,
        "occurrences_in_window": count,
        "window_days": RECURRENCE_WINDOW_DAYS,
        "threshold": RECURRENCE_THRESHOLD,
        "systematic": count >= RECURRENCE_THRESHOLD,
        "occurrence_dates": tuple(sorted(matches)),
    }


def _validate_report(report):
    """Return a normalised nonconformance report."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    required = (
        "report_id",
        "lot_id",
        "part_number",
        "effect",
        "reach",
        "failure_mode",
        "raised_date",
    )
    for key in required:
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    report_id = report["report_id"]
    if not isinstance(report_id, str) or not report_id.strip():
        raise ValueError("report['report_id'] must be a non-empty string")
    lot_id = report["lot_id"]
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("report['lot_id'] must be a non-empty string")
    part_number = report["part_number"]
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("report['part_number'] must be a non-empty string")
    quantity = report.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("report['quantity'] must be a positive integer")
    safety = report.get("safety_relevant", False)
    if not isinstance(safety, bool):
        raise ValueError("report['safety_relevant'] must be a bool")
    return {
        "report_id": report_id.strip(),
        "lot_id": lot_id.strip(),
        "part_number": part_number.strip().upper(),
        "wafer_lot": report.get("wafer_lot"),
        "date_code": report.get("date_code"),
        "effect": _check_effect(report["effect"]),
        "reach": _check_reach(report["reach"]),
        "failure_mode": str(report["failure_mode"]).strip().lower(),
        "quantity": quantity,
        "safety_relevant": safety,
        "raised_date": _parse_date(report["raised_date"], "raised_date"),
        "proposed_disposition": report.get("proposed_disposition"),
        "failure_analysis_reference": report.get("failure_analysis_reference"),
        "signatures": tuple(report.get("signatures", ())),
        "closed_date": report.get("closed_date"),
    }


def assess_nonconformance(report, inventory, history, as_of_date):
    """Run the full clause 4.5.2 control assessment over one report."""
    record = _validate_report(report)
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of lot records")
    if not isinstance(history, (list, tuple)):
        raise ValueError("history must be a sequence of past report records")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < record["raised_date"]:
        raise ValueError("as_of_date precedes the date the report was raised")

    grade = grade_nonconformance(
        record["effect"], record["reach"], record["safety_relevant"]
    )
    dispositions = allowed_dispositions(grade)
    analysis_owed = failure_analysis_required(record["effect"], grade)
    contained = containment_lots(
        {
            "lot_id": record["lot_id"],
            "part_number": record["part_number"],
            "wafer_lot": record["wafer_lot"],
            "date_code": record["date_code"],
        },
        inventory,
    )
    recurrence = recurrence_state(
        record["part_number"], record["failure_mode"], history, as_of
    )

    findings = []
    notes = []
    proposed = record["proposed_disposition"]
    required_signatures = ()
    if proposed is not None:
        if proposed not in dispositions:
            findings.append(
                "disposition %s is not open to a %s report on %s"
                % (proposed, grade, record["report_id"])
            )
        else:
            required_signatures = approval_chain(grade, proposed)
            missing = [
                signature
                for signature in required_signatures
                if signature not in record["signatures"]
            ]
            if missing:
                findings.append(
                    "report %s is missing the %s signature(s) its %s disposition earns"
                    % (record["report_id"], ", ".join(missing), proposed)
                )
    else:
        findings.append(
            "report %s carries no proposed disposition" % record["report_id"]
        )

    if analysis_owed and not record["failure_analysis_reference"]:
        findings.append(
            "report %s owes a failure analysis and none is referenced"
            % record["report_id"]
        )

    if record["closed_date"] is None:
        closure_days = working_days_between(record["raised_date"], as_of)
        closure_state = "open"
    else:
        closure_days = working_days_between(record["raised_date"], record["closed_date"])
        closure_state = "closed"
    deadline = GRADE_CLOSURE_DAYS[grade]
    within_deadline = closure_days <= deadline
    if not within_deadline:
        findings.append(
            "report %s has run %d working days against a %d day limit"
            % (record["report_id"], closure_days, deadline)
        )

    if len(contained) > 1:
        notes.append(
            "%d sibling lot(s) share the failing lot's origin and are impounded "
            "with it" % (len(contained) - 1)
        )
    if recurrence["systematic"]:
        findings.append(
            "failure mode '%s' on %s has recurred %d times in %d days and is "
            "systematic, not a lot escape"
            % (
                recurrence["failure_mode"],
                record["part_number"],
                recurrence["occurrences_in_window"],
                RECURRENCE_WINDOW_DAYS,
            )
        )
    if record["reach"] == "delivered":
        findings.append(
            "affected parts on report %s are already delivered; an in-service "
            "impact statement is owed to the customer" % record["report_id"]
        )

    return {
        "report_id": record["report_id"],
        "grade": grade,
        "allowed_dispositions": dispositions,
        "proposed_disposition": proposed,
        "required_signatures": required_signatures,
        "failure_analysis_required": analysis_owed,
        "containment_lots": contained,
        "contained_lot_count": len(contained),
        "recurrence": recurrence,
        "escalation": (
            "corrective-action-board" if recurrence["systematic"] else "project-level"
        ),
        "closure_working_days": closure_days,
        "closure_deadline_days": deadline,
        "closure_state": closure_state,
        "within_deadline": within_deadline,
        "findings": findings,
        "notes": notes,
        "closeable": not findings and closure_state == "closed",
    }
