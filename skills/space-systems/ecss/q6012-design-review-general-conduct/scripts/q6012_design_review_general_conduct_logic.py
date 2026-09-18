"""General conduct of a microwave design review: convening, attendance, findings.

Anchor: ECSS-Q-ST-60-12C clause 7.3.1 (how a design review is convened, who
has to attend, and how the findings raised in it are recorded and closed).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Measure the convening notice lead time against the required minimum, and
   refuse a notice issued after the review it announces.
2. Test the attendee roster for quorum over the mandatory roles, collapsing
   the case where one person carries two roles and refusing an empty roster.
3. Confirm the chair is independent of the design team, because a review
   chaired by the designer under review is a walkthrough, not a review.
4. Validate every finding register entry for a consistent state: a closed
   entry carries a closure day at or after the day it was raised and a
   recognised disposition; an open entry carries neither.
5. Age the open findings against the response time their severity earns,
   report the closure ratio and the severity-weighted open load, and turn the
   whole lot into a conduct verdict.

Days are integer programme days counted from a common origin, so the module
never needs a calendar and never touches the clock.
"""

import math

__all__ = [
    "SEVERITY_WEIGHTS",
    "DEFAULT_RESPONSE_DAYS",
    "VALID_DISPOSITIONS",
    "RATIO_TOLERANCE",
    "notice_lead_days",
    "validate_attendee",
    "normalise_roster",
    "quorum_status",
    "chair_independence",
    "validate_finding",
    "normalise_register",
    "finding_age_days",
    "closure_ratio",
    "open_severity_load",
    "overdue_findings",
    "assess_review_conduct",
]

# Severity grades a review register uses, and the relative weight each open
# entry contributes to the backlog the chair still owes a closure plan for.
SEVERITY_WEIGHTS = {
    "major": 4.0,
    "minor": 1.0,
    "observation": 0.25,
}

# Response time each severity earns before its entry counts as overdue.
DEFAULT_RESPONSE_DAYS = {
    "major": 15,
    "minor": 30,
    "observation": 60,
}

# A closed entry has to say what was decided, not merely that it is shut.
VALID_DISPOSITIONS = ("accepted", "reworked", "superseded", "withdrawn")

# A closure ratio is a quotient of integers turned into a float; an exact
# equality with the required value can land a few ULPs low. Absorb the
# representation error here instead of relaxing the required ratio.
RATIO_TOLERANCE = 1e-9


def _require_int(value, label, minimum=None):
    """Return value as an int, refusing bools, floats and out-of-range input."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def notice_lead_days(notice_day, review_day):
    """Return how many days of notice the review was convened with."""
    notice = _require_int(notice_day, "notice_day", minimum=0)
    review = _require_int(review_day, "review_day", minimum=0)
    if review < notice:
        raise ValueError(
            "review day %d precedes the convening notice on day %d" % (review, notice)
        )
    return review - notice


def validate_attendee(entry):
    """Return one normalised roster record.

    entry keys: role (str), optional person (str), optional design_team flag,
    optional chair flag.
    """
    if not isinstance(entry, dict):
        raise ValueError("attendee entry must be a mapping, got %r" % (entry,))
    role = entry.get("role")
    if not isinstance(role, str) or not role.strip():
        raise ValueError("attendee role must be a non-empty string, got %r" % (role,))
    person = entry.get("person", role)
    if not isinstance(person, str) or not person.strip():
        raise ValueError("attendee person must be a non-empty string, got %r" % (person,))
    for flag in ("design_team", "chair"):
        if flag in entry and not isinstance(entry[flag], bool):
            raise ValueError("%s flag of role %s must be a boolean" % (flag, role))
    return {
        "role": role.strip(),
        "person": person.strip(),
        "design_team": bool(entry.get("design_team", False)),
        "chair": bool(entry.get("chair", False)),
    }


def normalise_roster(entries):
    """Return the validated roster; refuse an empty roster or two chairs."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("roster must be a non-empty sequence of attendee entries")
    roster = [validate_attendee(entry) for entry in entries]
    chairs = [r for r in roster if r["chair"]]
    if len(chairs) > 1:
        raise ValueError("roster declares %d chairs; a review has one" % len(chairs))
    return roster


def quorum_status(roster, mandatory_roles):
    """Return which mandatory roles the roster covers and which it does not."""
    if not isinstance(mandatory_roles, (list, tuple)) or not mandatory_roles:
        raise ValueError("mandatory_roles must be a non-empty sequence")
    present = set()
    for record in roster:
        present.add(record["role"])
    missing = []
    for role in mandatory_roles:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("mandatory role must be a non-empty string, got %r" % (role,))
        if role.strip() not in present:
            missing.append(role.strip())
    return {
        "present_roles": sorted(present),
        "missing_roles": missing,
        "satisfied": not missing,
    }


def chair_independence(roster):
    """Return the chair record and whether the chair sits outside the design team."""
    chairs = [r for r in roster if r["chair"]]
    if not chairs:
        raise ValueError("roster names no chair; a review has to be chaired")
    chair = chairs[0]
    return {
        "chair_role": chair["role"],
        "chair_person": chair["person"],
        "independent": not chair["design_team"],
    }


def validate_finding(entry):
    """Return one normalised finding record.

    entry keys: id, severity (a key of SEVERITY_WEIGHTS), raised_day, optional
    closed_day, optional disposition.
    """
    if not isinstance(entry, dict):
        raise ValueError("finding entry must be a mapping, got %r" % (entry,))
    ident = entry.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("finding id must be a non-empty string, got %r" % (ident,))
    severity = entry.get("severity")
    if not isinstance(severity, str) or severity not in SEVERITY_WEIGHTS:
        raise ValueError(
            "finding %s has severity %r, not one of %s"
            % (ident, severity, ", ".join(sorted(SEVERITY_WEIGHTS)))
        )
    raised_day = _require_int(entry.get("raised_day"), "raised_day", minimum=0)
    closed_day = entry.get("closed_day")
    disposition = entry.get("disposition")
    if closed_day is None:
        if disposition is not None:
            raise ValueError(
                "finding %s carries a disposition but no closure day" % ident
            )
    else:
        closed_day = _require_int(closed_day, "closed_day", minimum=0)
        if closed_day < raised_day:
            raise ValueError(
                "finding %s closes on day %d before it was raised on day %d"
                % (ident, closed_day, raised_day)
            )
        if disposition not in VALID_DISPOSITIONS:
            raise ValueError(
                "finding %s closes with disposition %r, not one of %s"
                % (ident, disposition, ", ".join(VALID_DISPOSITIONS))
            )
    return {
        "id": ident.strip(),
        "severity": severity,
        "raised_day": raised_day,
        "closed_day": closed_day,
        "closed": closed_day is not None,
        "disposition": disposition,
    }


def normalise_register(entries):
    """Return the validated finding register; an empty register is allowed."""
    if entries is None:
        return []
    if not isinstance(entries, (list, tuple)):
        raise ValueError("register must be a sequence of finding entries")
    register = [validate_finding(entry) for entry in entries]
    seen = set()
    for record in register:
        if record["id"] in seen:
            raise ValueError("finding %s declared twice" % record["id"])
        seen.add(record["id"])
    return register


def finding_age_days(record, as_of_day):
    """Return how many days a finding has been open, or took to close."""
    as_of = _require_int(as_of_day, "as_of_day", minimum=0)
    if not isinstance(record, dict) or "raised_day" not in record:
        raise ValueError("record must be a normalised finding mapping")
    end = record["closed_day"] if record["closed"] else as_of
    if end < record["raised_day"]:
        raise ValueError(
            "as_of_day %d precedes the day finding %s was raised" % (as_of, record["id"])
        )
    return end - record["raised_day"]


def closure_ratio(register):
    """Return the share of register entries that are closed; 1.0 when empty."""
    if not register:
        return 1.0
    closed = sum(1 for record in register if record["closed"])
    return closed / len(register)


def open_severity_load(register):
    """Return the severity-weighted count of entries still open."""
    return sum(
        SEVERITY_WEIGHTS[record["severity"]] for record in register if not record["closed"]
    )


def overdue_findings(register, as_of_day, response_days=None):
    """Return the open entries older than the response time their severity earns."""
    table = dict(DEFAULT_RESPONSE_DAYS)
    if response_days is not None:
        if not isinstance(response_days, dict):
            raise ValueError("response_days must be a mapping of severity to days")
        for severity, days in response_days.items():
            if severity not in SEVERITY_WEIGHTS:
                raise ValueError("response_days names unknown severity %r" % (severity,))
            table[severity] = _require_int(days, "response day count", minimum=0)
    overdue = []
    for record in register:
        if record["closed"]:
            continue
        if finding_age_days(record, as_of_day) > table[record["severity"]]:
            overdue.append(record["id"])
    return overdue


def assess_review_conduct(spec):
    """Run the full clause 7.3.1 conduct assessment.

    spec keys: notice_day, review_day, required_notice_days, roster,
    mandatory_roles, optional findings, as_of_day, required_closure_ratio,
    response_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("notice_day", "review_day", "required_notice_days", "roster",
                "mandatory_roles"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_notice = _require_int(
        spec["required_notice_days"], "required_notice_days", minimum=0
    )
    lead = notice_lead_days(spec["notice_day"], spec["review_day"])
    roster = normalise_roster(spec["roster"])
    quorum = quorum_status(roster, spec["mandatory_roles"])
    chair = chair_independence(roster)
    register = normalise_register(spec.get("findings"))
    as_of = spec.get("as_of_day", spec["review_day"])
    ratio = closure_ratio(register)
    required_ratio = spec.get("required_closure_ratio", 1.0)
    if isinstance(required_ratio, bool) or not isinstance(required_ratio, (int, float)):
        raise ValueError("required_closure_ratio must be a real number")
    required_ratio = float(required_ratio)
    if not math.isfinite(required_ratio) or required_ratio < 0.0 or required_ratio > 1.0:
        raise ValueError("required_closure_ratio must lie in [0, 1]")
    ratio_ok = ratio > required_ratio or math.isclose(
        ratio, required_ratio, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    overdue = overdue_findings(register, as_of, spec.get("response_days"))
    notice_ok = lead >= required_notice

    findings = []
    if not notice_ok:
        findings.append(
            "review convened on %d days notice, below the required %d"
            % (lead, required_notice)
        )
    if not quorum["satisfied"]:
        findings.append(
            "quorum not met; mandatory roles absent: %s" % ", ".join(quorum["missing_roles"])
        )
    if not chair["independent"]:
        findings.append(
            "chair %s sits inside the design team under review" % chair["chair_role"]
        )
    if not ratio_ok:
        findings.append(
            "finding closure ratio %.4f is below the required %.4f" % (ratio, required_ratio)
        )
    if overdue:
        findings.append("open findings past their response time: %s" % ", ".join(overdue))
    return {
        "notice_lead_days": lead,
        "required_notice_days": required_notice,
        "notice_met": notice_ok,
        "quorum": quorum,
        "chair": chair,
        "register": register,
        "closure_ratio": ratio,
        "required_closure_ratio": required_ratio,
        "closure_ratio_met": ratio_ok,
        "open_severity_load": open_severity_load(register),
        "overdue_findings": overdue,
        "findings": findings,
        "conducted_properly": notice_ok and quorum["satisfied"] and chair["independent"],
        "closed_out": ratio_ok and not overdue,
    }
