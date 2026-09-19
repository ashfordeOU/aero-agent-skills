"""Laboratory quality control for a mechanical test campaign.

Anchor: ECSS-Q-ST-70-45 quality clause -- the control a test laboratory keeps
over its written procedures, the people who run the tests and the records of
the equipment they run them on, before a campaign is accepted as competently
performed. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Resolve calendar days honestly: a qualification or a certificate runs out a
   whole number of months after it was granted, and a month end falls back to
   the end of a shorter month rather than rolling into the next one.
2. Decide authorisation per operator per method on the run day, not on today,
   and separate an operator whose qualification has lapsed from one whose
   qualification is about to.
3. Grade each written procedure: issued rather than draft or superseded, and
   the revision named by the campaign is the revision that is current.
4. Grade each equipment record: an identified certificate, a traceability
   chain that is not empty, and a calibration still current on the run day.
5. Cover the campaign method by method: every method owes an authorised
   operator, an approved procedure and every item of equipment it names.
"""

from datetime import date

__all__ = [
    "APPROVED_PROCEDURE_STATUSES",
    "DEFAULT_DUE_SOON_DAYS",
    "parse_day",
    "add_months",
    "days_remaining",
    "competency_status",
    "authorised_operators",
    "procedure_findings",
    "equipment_findings",
    "method_coverage",
    "assess_laboratory_control",
]

# A procedure in any other state is not something a test may be run to.
APPROVED_PROCEDURE_STATUSES = ("issued", "approved")

# Inside this many days of running out, a qualification or a certificate is
# reported as due rather than silently accepted.
DEFAULT_DUE_SOON_DAYS = 30

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _month_length(year, month):
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def parse_day(value):
    """Return an ISO day string or a date as a date, refusing a day the calendar lacks."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("a day must be an ISO yyyy-mm-dd string or a date, got %r" % (value,))
    parts = value.split("-")
    if len(parts) != 3 or len(parts[0]) != 4:
        raise ValueError("day %r is not in yyyy-mm-dd form" % (value,))
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        raise ValueError("day %r is not in yyyy-mm-dd form" % (value,))
    if not 1 <= month <= 12:
        raise ValueError("day %r names month %d" % (value, month))
    if not 1 <= day <= _month_length(year, month):
        raise ValueError("day %r does not exist in the calendar" % (value,))
    return date(year, month, day)


def add_months(day, months):
    """Return the day a whole number of calendar months later."""
    start = parse_day(day)
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be a whole number, got %r" % (months,))
    if months < 0:
        raise ValueError("months must not be negative, got %d" % months)
    index = (start.year * 12 + start.month - 1) + months
    year = index // 12
    month = index % 12 + 1
    return date(year, month, min(start.day, _month_length(year, month)))


def days_remaining(due_day, run_day):
    """Return the whole days from the run day to the day something runs out."""
    due = parse_day(due_day)
    run = parse_day(run_day)
    return (due - run).days


def competency_status(competency, run_day, due_soon_days=DEFAULT_DUE_SOON_DAYS):
    """Return the standing of one operator competency on the run day."""
    if not isinstance(competency, dict):
        raise ValueError("a competency must be a mapping")
    for key in ("method", "qualified_on", "validity_months"):
        if key not in competency:
            raise ValueError("competency missing required key '%s'" % key)
    if not isinstance(due_soon_days, int) or isinstance(due_soon_days, bool) or due_soon_days < 0:
        raise ValueError("due_soon_days must be a non-negative whole number, got %r" % (due_soon_days,))
    due = add_months(competency["qualified_on"], competency["validity_months"])
    left = days_remaining(due, run_day)
    return {
        "method": competency["method"],
        "due_day": due,
        "days_remaining": left,
        "current": left >= 0,
        "due_soon": 0 <= left <= due_soon_days,
    }


def authorised_operators(operators, method, run_day, due_soon_days=DEFAULT_DUE_SOON_DAYS):
    """Return the operators authorised on a method on the run day.

    A lapsed or nearly lapsed operator is an advisory about the record, not a
    blocker, as long as somebody else is authorised; a method with nobody
    authorised is the blocking condition and is raised by the caller.
    """
    if not isinstance(operators, (list, tuple)):
        raise ValueError("operators must be a sequence of operator records")
    if not isinstance(method, str) or not method:
        raise ValueError("method must be a non-empty name, got %r" % (method,))
    authorised = []
    lapsed = []
    advisories = []
    for index, record in enumerate(operators):
        if not isinstance(record, dict) or "id" not in record:
            raise ValueError("operators[%d] must be a mapping carrying 'id'" % index)
        for competency in record.get("competencies", []):
            status = competency_status(competency, run_day, due_soon_days)
            if status["method"] != method:
                continue
            if status["current"]:
                authorised.append(record["id"])
                if status["due_soon"]:
                    advisories.append(
                        "operator '%s' is qualified on '%s' for a further %d day(s)"
                        % (record["id"], method, status["days_remaining"])
                    )
            else:
                lapsed.append(record["id"])
                advisories.append(
                    "operator '%s' lapsed on '%s' %d day(s) before the run day"
                    % (record["id"], method, -status["days_remaining"])
                )
    return {"authorised": authorised, "lapsed": lapsed, "advisories": advisories}


def procedure_findings(procedure, required_revision=None):
    """Grade one written procedure for status and revision currency."""
    if not isinstance(procedure, dict):
        raise ValueError("a procedure must be a mapping")
    for key in ("id", "status", "revision"):
        if key not in procedure:
            raise ValueError("procedure missing required key '%s'" % key)
    findings = []
    status = str(procedure["status"]).strip().lower()
    if status not in APPROVED_PROCEDURE_STATUSES:
        findings.append(
            "procedure '%s' is '%s'; a test may only be run to %s"
            % (procedure["id"], procedure["status"], " or ".join(APPROVED_PROCEDURE_STATUSES))
        )
    current = procedure.get("current_revision", procedure["revision"])
    if str(procedure["revision"]) != str(current):
        findings.append(
            "procedure '%s' is held at revision %s while revision %s is current"
            % (procedure["id"], procedure["revision"], current)
        )
    if required_revision is not None and str(procedure["revision"]) != str(required_revision):
        findings.append(
            "the campaign names revision %s of procedure '%s' and the laboratory holds %s"
            % (required_revision, procedure["id"], procedure["revision"])
        )
    return {"id": procedure["id"], "usable": not findings, "findings": findings}


def equipment_findings(item, run_day, due_soon_days=DEFAULT_DUE_SOON_DAYS):
    """Grade one equipment record for traceability and calibration currency.

    A missing certificate, an empty traceability chain and a calibration that
    has run out are blocking findings; a calibration inside its warning window
    is an advisory, because the equipment is still usable on the run day.
    """
    if not isinstance(item, dict):
        raise ValueError("an equipment record must be a mapping")
    for key in ("id", "calibrated_on", "interval_months"):
        if key not in item:
            raise ValueError("equipment record missing required key '%s'" % key)
    findings = []
    advisories = []
    if not item.get("certificate"):
        findings.append("equipment '%s' carries no calibration certificate reference" % item["id"])
    chain = item.get("traceability", [])
    if not isinstance(chain, (list, tuple)):
        raise ValueError("equipment '%s' traceability must be a sequence" % item["id"])
    if len(chain) == 0:
        findings.append(
            "equipment '%s' has an empty traceability chain; the certificate leads nowhere"
            % item["id"]
        )
    due = add_months(item["calibrated_on"], item["interval_months"])
    left = days_remaining(due, run_day)
    if left < 0:
        findings.append(
            "equipment '%s' ran out of calibration %d day(s) before the run day"
            % (item["id"], -left)
        )
    elif left <= due_soon_days:
        advisories.append(
            "equipment '%s' holds calibration for a further %d day(s)" % (item["id"], left)
        )
    return {
        "id": item["id"],
        "due_day": due,
        "days_remaining": left,
        "usable": not findings,
        "findings": findings,
        "advisories": advisories,
    }


def method_coverage(method_spec, operators, procedures, equipment, run_day,
                    due_soon_days=DEFAULT_DUE_SOON_DAYS):
    """Cover one campaign method: an operator, a procedure and its equipment."""
    if not isinstance(method_spec, dict):
        raise ValueError("a method entry must be a mapping")
    for key in ("name", "procedure_id"):
        if key not in method_spec:
            raise ValueError("method entry missing required key '%s'" % key)
    name = method_spec["name"]
    findings = []
    advisories = []

    people = authorised_operators(operators, name, run_day, due_soon_days)
    advisories.extend(people["advisories"])
    if not people["authorised"]:
        findings.append("method '%s' has no operator authorised on the run day" % name)

    procedure = None
    for candidate in procedures:
        if not isinstance(candidate, dict) or "id" not in candidate:
            raise ValueError("every procedure must be a mapping carrying 'id'")
        if candidate["id"] == method_spec["procedure_id"]:
            procedure = candidate
            break
    if procedure is None:
        findings.append(
            "method '%s' names procedure '%s', which the laboratory does not hold"
            % (name, method_spec["procedure_id"])
        )
        procedure_state = None
    else:
        procedure_state = procedure_findings(procedure, method_spec.get("procedure_revision"))
        findings.extend(procedure_state["findings"])

    held = {}
    for item in equipment:
        if not isinstance(item, dict) or "id" not in item:
            raise ValueError("every equipment record must be a mapping carrying 'id'")
        held[item["id"]] = item
    equipment_states = []
    for wanted in method_spec.get("equipment_ids", []):
        if wanted not in held:
            findings.append(
                "method '%s' needs equipment '%s', which has no record" % (name, wanted)
            )
            continue
        state = equipment_findings(held[wanted], run_day, due_soon_days)
        equipment_states.append(state)
        findings.extend(state["findings"])
        advisories.extend(state["advisories"])

    return {
        "method": name,
        "authorised_operators": people["authorised"],
        "lapsed_operators": people["lapsed"],
        "procedure": procedure_state,
        "equipment": equipment_states,
        "findings": findings,
        "advisories": advisories,
        "ready": not findings,
    }


def assess_laboratory_control(spec):
    """Run the whole laboratory-control assessment for one test campaign.

    spec keys: run_day, methods, operators, procedures, equipment. Optional:
    due_soon_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("run_day", "methods", "operators", "procedures", "equipment"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    run_day = parse_day(spec["run_day"])
    if not isinstance(spec["methods"], (list, tuple)) or not spec["methods"]:
        raise ValueError("a campaign needs at least one method")
    due_soon_days = spec.get("due_soon_days", DEFAULT_DUE_SOON_DAYS)
    coverage = []
    findings = []
    advisories = []
    for entry in spec["methods"]:
        state = method_coverage(
            entry, spec["operators"], spec["procedures"], spec["equipment"], run_day, due_soon_days
        )
        coverage.append(state)
        findings.extend(state["findings"])
        advisories.extend(state["advisories"])
    return {
        "run_day": run_day,
        "methods": coverage,
        "methods_ready": [state["method"] for state in coverage if state["ready"]],
        "findings": findings,
        "advisories": advisories,
        "ready": not findings,
    }
