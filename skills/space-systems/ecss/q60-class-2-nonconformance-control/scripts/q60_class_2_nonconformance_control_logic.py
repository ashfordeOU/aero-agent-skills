"""Nonconformance and failure control for class 2 EEE parts, programme wide.

Anchor: ECSS-Q-ST-60C clause 5.5.2 (operating a nonconformance and failure
control system for class 2 parts across the programme). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the report: the lot it names, the effect it had, how far the parts
   had already travelled, and the function the part was sitting in.
2. Decide whether the part's own usage escalates the handling regime, because
   a class 2 part in a safety-critical or single-point-failure function is
   worked to a harder standard than its procurement class alone would ask.
3. Grade the report minor, major or critical from the effect, the reach, the
   safety consequence and that escalation.
4. Derive the dispositions the grade allows and the signatures each earns, so
   a critical report cannot be closed by accepting the part as it stands.
5. Decide whether a failure analysis is owed rather than optional, and widen
   containment over the sibling lots the failure mode family actually reaches:
   a lot-related mode by shared date code, a design-related mode across every
   date code, a workmanship mode over no sibling lot at all.
6. Detect a mode that has repeated often enough inside the rolling window to
   be systematic, and count the closure working days against the grade's
   deadline.
"""

import datetime

__all__ = [
    "GRADES",
    "EFFECT_CATEGORIES",
    "REACH_STATES",
    "USAGE_CRITICALITIES",
    "MODE_FAMILIES",
    "GRADE_DISPOSITIONS",
    "GRADE_CLOSURE_DAYS",
    "DISPOSITION_APPROVALS",
    "RECURRENCE_THRESHOLD",
    "RECURRENCE_WINDOW_DAYS",
    "escalated_handling",
    "grade_nonconformance",
    "allowed_dispositions",
    "approval_chain",
    "failure_analysis_required",
    "containment_lots",
    "recurrence_state",
    "recurrence_rate",
    "working_days_between",
    "closure_state",
    "assess_class_2_nonconformance",
]

# Report grades, least to most severe.
GRADES = ("minor", "major", "critical")

# Effect on the part or the assembly, ordered from least to most severe.
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

# The function the part was sitting in. The last two pull a class 2 part into
# the harder handling regime whatever its procurement class says.
USAGE_CRITICALITIES = {
    "non-critical": 0,
    "mission-critical": 1,
    "safety-critical": 2,
}

# Failure mode families, which decide how far containment has to reach.
MODE_FAMILIES = (
    "lot-related",
    "design-related",
    "assembly-induced",
    "handling-induced",
)

# Dispositions each grade allows. A critical report cannot be dispositioned by
# accepting the part as it stands, at any signature level.
GRADE_DISPOSITIONS = {
    "minor": ("use-as-is", "rework", "return-to-supplier", "scrap"),
    "major": ("rework", "repair", "return-to-supplier", "scrap", "use-as-is"),
    "critical": ("return-to-supplier", "scrap"),
}

# Working days from raising to closure, by grade.
GRADE_CLOSURE_DAYS = {"minor": 20, "major": 10, "critical": 5}

# Signatures each disposition earns, by grade.
DISPOSITION_APPROVALS = {
    ("minor", "use-as-is"): ("product-assurance",),
    ("minor", "rework"): ("product-assurance",),
    ("minor", "return-to-supplier"): ("product-assurance",),
    ("minor", "scrap"): ("product-assurance",),
    ("major", "use-as-is"): ("product-assurance", "parts-control-board", "customer"),
    ("major", "repair"): ("product-assurance", "parts-control-board", "customer"),
    ("major", "rework"): ("product-assurance", "parts-control-board"),
    ("major", "return-to-supplier"): ("product-assurance", "parts-control-board"),
    ("major", "scrap"): ("product-assurance", "parts-control-board"),
    ("critical", "return-to-supplier"): (
        "product-assurance", "parts-control-board", "customer",
    ),
    ("critical", "scrap"): (
        "product-assurance", "parts-control-board", "customer",
    ),
}

# Occurrences of one mode inside the window that make it systematic.
RECURRENCE_THRESHOLD = 3

# Rolling window, in calendar days, the recurrence count is taken over.
RECURRENCE_WINDOW_DAYS = 365


def _require_mapping(value, label):
    """Return a validated mapping or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, value))
    return value


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _require_member(value, table, label):
    """Return a validated member of a name table or raise."""
    name = _require_text(value, label).casefold()
    if name not in table:
        raise ValueError(
            "%s must be one of %r, got %r" % (label, sorted(table), value)
        )
    return name


def parse_iso_date(value, label="date"):
    """Return an ISO date string or date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def escalated_handling(report):
    """Return True when the part's usage pulls it into the harder regime.

    report keys read here: usage_criticality and single_point_failure.
    """
    _require_mapping(report, "report")
    usage = _require_member(report.get("usage_criticality", "non-critical"),
                            USAGE_CRITICALITIES, "usage_criticality")
    single_point = _require_flag(report.get("single_point_failure", False),
                                 "single_point_failure")
    return USAGE_CRITICALITIES[usage] >= USAGE_CRITICALITIES["safety-critical"] \
        or single_point


def grade_nonconformance(report):
    """Return the grade a class 2 nonconformance report carries.

    report keys read here: effect, reach, safety_consequence, plus the usage
    keys the escalation test reads.
    """
    _require_mapping(report, "report")
    effect = _require_member(report.get("effect"), EFFECT_CATEGORIES, "effect")
    reach = _require_member(report.get("reach"), REACH_STATES, "reach")
    safety = _require_flag(report.get("safety_consequence", False),
                           "safety_consequence")
    effect_rank = EFFECT_CATEGORIES[effect]
    reach_rank = REACH_STATES[reach]
    if effect_rank >= EFFECT_CATEGORIES["functional-failure"]:
        index = 1
    elif effect_rank >= EFFECT_CATEGORIES["out-of-specification"]:
        index = 1 if reach_rank >= REACH_STATES["assembled"] else 0
    else:
        index = 0
    if safety:
        index = 2
    if escalated_handling(report):
        index = min(index + 1, 2)
    return GRADES[index]


def allowed_dispositions(grade):
    """Return the dispositions a grade allows, most contained first."""
    name = _require_member(grade, set(GRADE_DISPOSITIONS), "grade")
    return list(GRADE_DISPOSITIONS[name])


def approval_chain(grade, disposition):
    """Return the signatures a disposition earns at a grade."""
    grade_name = _require_member(grade, set(GRADE_DISPOSITIONS), "grade")
    choice = _require_text(disposition, "disposition").casefold()
    if choice not in GRADE_DISPOSITIONS[grade_name]:
        raise ValueError(
            "disposition %r is not allowed at grade %r; allowed: %r"
            % (disposition, grade_name, list(GRADE_DISPOSITIONS[grade_name]))
        )
    return list(DISPOSITION_APPROVALS[(grade_name, choice)])


def failure_analysis_required(report, grade, systematic=False):
    """Return True when a failure analysis is owed rather than optional."""
    _require_mapping(report, "report")
    grade_name = _require_member(grade, set(GRADE_DISPOSITIONS), "grade")
    if not isinstance(systematic, bool):
        raise ValueError("systematic must be true or false, got %r" % (systematic,))
    effect = _require_member(report.get("effect"), EFFECT_CATEGORIES, "effect")
    if grade_name != "minor":
        return True
    if systematic:
        return True
    return effect == "functional-failure"


def containment_lots(report, inventory):
    """Return the sibling lots impounded with the failing lot.

    A lot-related mode reaches the lots sharing the failing lot's part number,
    manufacturer and date code. A design-related mode reaches every lot of that
    part number and manufacturer. A workmanship mode reaches no sibling lot.
    """
    _require_mapping(report, "report")
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of lot records")
    family = _require_member(report.get("mode_family"), set(MODE_FAMILIES),
                             "mode_family")
    failing_lot = _require_text(report.get("lot_id"), "lot_id")
    part_number = _require_text(report.get("part_number"), "part_number")
    manufacturer = _require_text(report.get("manufacturer"), "manufacturer")
    date_code = _require_text(report.get("date_code"), "date_code")
    if family in ("assembly-induced", "handling-induced"):
        return []
    impounded = []
    for record in inventory:
        _require_mapping(record, "inventory record")
        lot_id = _require_text(record.get("lot_id"), "lot_id")
        if lot_id == failing_lot:
            continue
        if _require_text(record.get("part_number"), "part_number") != part_number:
            continue
        if _require_text(record.get("manufacturer"), "manufacturer") != manufacturer:
            continue
        if family == "lot-related":
            if _require_text(record.get("date_code"), "date_code") != date_code:
                continue
        impounded.append(lot_id)
    return sorted(impounded)


def _window_occurrences(history, failure_mode, part_number, as_of, window_days):
    """Return the dated occurrences of one mode inside the rolling window."""
    if not isinstance(history, (list, tuple)):
        raise ValueError("history must be a sequence of past reports")
    if not isinstance(window_days, int) or isinstance(window_days, bool):
        raise ValueError("window_days must be an integer, got %r" % (window_days,))
    if window_days <= 0:
        raise ValueError("window_days must be positive, got %d" % window_days)
    end = parse_iso_date(as_of, "as_of")
    start = end - datetime.timedelta(days=window_days)
    hits = []
    for entry in history:
        _require_mapping(entry, "history entry")
        mode = _require_text(entry.get("failure_mode"), "failure_mode").casefold()
        number = _require_text(entry.get("part_number"), "part_number")
        raised = parse_iso_date(entry.get("raised_on"), "raised_on")
        if mode != failure_mode or number != part_number:
            continue
        if raised < start or raised > end:
            continue
        hits.append(raised)
    return sorted(hits)


def recurrence_state(report, history, as_of, window_days=RECURRENCE_WINDOW_DAYS):
    """Return the recurrence count and whether the mode reads as systematic."""
    _require_mapping(report, "report")
    mode = _require_text(report.get("failure_mode"), "failure_mode").casefold()
    part_number = _require_text(report.get("part_number"), "part_number")
    hits = _window_occurrences(history, mode, part_number, as_of, window_days)
    count = len(hits)
    return {
        "failure_mode": mode,
        "occurrences_in_window": count,
        "window_days": window_days,
        "first_in_window": hits[0].isoformat() if hits else None,
        "last_in_window": hits[-1].isoformat() if hits else None,
        "systematic": count >= RECURRENCE_THRESHOLD,
    }


def recurrence_rate(occurrences, lots_examined):
    """Return the share of examined lots that showed the mode."""
    for value, label in ((occurrences, "occurrences"),
                         (lots_examined, "lots_examined")):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if lots_examined <= 0:
        raise ValueError("lots_examined must be positive, got %d" % lots_examined)
    if occurrences < 0:
        raise ValueError("occurrences must not be negative, got %d" % occurrences)
    if occurrences > lots_examined:
        raise ValueError(
            "occurrences %d exceeds lots_examined %d" % (occurrences, lots_examined)
        )
    return occurrences / float(lots_examined)


def working_days_between(start, end):
    """Return the working days from a raising date to a closing date."""
    first = parse_iso_date(start, "start")
    last = parse_iso_date(end, "end")
    if last < first:
        raise ValueError("end %s precedes start %s" % (last, first))
    days = 0
    cursor = first
    while cursor < last:
        cursor = cursor + datetime.timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    return days


def closure_state(grade, raised_on, closed_on=None, as_of=None):
    """Return the working days used and whether the grade's deadline held."""
    grade_name = _require_member(grade, set(GRADE_CLOSURE_DAYS), "grade")
    deadline = GRADE_CLOSURE_DAYS[grade_name]
    endpoint = closed_on if closed_on is not None else as_of
    if endpoint is None:
        raise ValueError("either closed_on or as_of must be given")
    used = working_days_between(raised_on, endpoint)
    return {
        "grade": grade_name,
        "deadline_working_days": deadline,
        "working_days_used": used,
        "closed": closed_on is not None,
        "within_deadline": used <= deadline,
        "overdue_by": max(0, used - deadline),
    }


def assess_class_2_nonconformance(report, inventory=(), history=(), as_of=None,
                                  disposition=None):
    """Run the clause 5.5.2 assessment over one class 2 nonconformance report.

    report keys: lot_id, part_number, manufacturer, date_code, failure_mode,
    mode_family, effect, reach, raised_on, and the optional safety_consequence,
    usage_criticality, single_point_failure and closed_on.
    """
    _require_mapping(report, "report")
    grade = grade_nonconformance(report)
    reference = as_of if as_of is not None else report.get("raised_on")
    recurrence = recurrence_state(report, history, reference)
    systematic = recurrence["systematic"]
    allowed = allowed_dispositions(grade)
    approvals = approval_chain(grade, disposition) if disposition else []
    closure = closure_state(grade, report.get("raised_on"),
                            report.get("closed_on"), reference)
    return {
        "grade": grade,
        "escalated": escalated_handling(report),
        "allowed_dispositions": allowed,
        "chosen_disposition": disposition,
        "approval_chain": approvals,
        "failure_analysis_required": failure_analysis_required(
            report, grade, systematic
        ),
        "impounded_lots": containment_lots(report, list(inventory)),
        "recurrence": recurrence,
        "closure": closure,
    }
