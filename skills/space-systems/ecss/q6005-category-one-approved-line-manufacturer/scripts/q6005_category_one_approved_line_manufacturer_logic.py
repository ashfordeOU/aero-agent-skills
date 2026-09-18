"""Category one hybrid manufacturer assessment: approved line plus a complete PID.

Anchor: ECSS-Q-ST-60-05 clause 5.2.1 (the preferred procurement case for a
hybrid, where the part is produced on a production line that already carries an
approval, or an approval in progress, and where a process identification
document describes that line with a mandated content set). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the manufacturer record: the maker, the line the hybrid is actually
   built on, the line the approval was granted against, the approval state and
   the dates that bound it.
2. Decide approval currency at the procurement date. An approved line that has
   run past its expiry is not an approved line; an approval still in progress
   is admissible only while the application predates the assessment and the
   documentation carries no gaps.
3. Audit the process identification document against every content item the
   clause mandates, and report the gap set rather than a single yes/no.
4. Confirm the build line is the line the approval names. A second line in the
   same plant is a different line and moves the part out of the preferred case.
5. Return the category decision with every reason that drove it, so a buyer can
   see which single item has to move to recover the preferred route.
"""

import datetime

__all__ = [
    "MANDATED_PID_CONTENT",
    "APPROVAL_STATES",
    "ADMISSIBLE_APPROVAL_STATES",
    "parse_date",
    "normalize_line_identity",
    "validate_manufacturer_record",
    "audit_pid_content",
    "approval_currency",
    "line_identity_matches",
    "categorize_manufacturer",
]

# The content a process identification document has to carry before the line it
# describes can be leaned on. Order is the order a reviewer reads them in.
MANDATED_PID_CONTENT = (
    "line-identification",
    "materials-and-parts-list",
    "process-flow-sequence",
    "die-attach-parameters",
    "interconnection-parameters",
    "sealing-and-encapsulation",
    "screening-and-qualification-flow",
    "in-process-controls",
    "change-control-procedure",
    "traceability-scheme",
)

APPROVAL_STATES = ("approved", "pending", "lapsed", "withdrawn", "none")

# Only these two states can carry a part into the preferred case at all; the
# remaining three are the category two conversation, not this one.
ADMISSIBLE_APPROVAL_STATES = ("approved", "pending")

_REQUIRED_RECORD_KEYS = (
    "manufacturer",
    "build_line",
    "approved_line",
    "approval_state",
)


def parse_date(value, label="date"):
    """Return a datetime.date from an ISO day string or a date instance."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def normalize_line_identity(value, label="line"):
    """Return a comparable form of a production line identity."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string identity, got %r" % (label, value))
    collapsed = " ".join(value.split()).strip().lower()
    if not collapsed:
        raise ValueError("%s must not be blank" % label)
    return collapsed.replace("_", "-").replace(" ", "-")


def validate_manufacturer_record(record):
    """Return the validated and normalized manufacturer record."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in _REQUIRED_RECORD_KEYS:
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    maker = record["manufacturer"]
    if not isinstance(maker, str) or not maker.strip():
        raise ValueError("manufacturer must be a non-empty name")
    state = record["approval_state"]
    if not isinstance(state, str):
        raise ValueError("approval_state must be a string")
    state = state.strip().lower()
    if state not in APPROVAL_STATES:
        raise ValueError(
            "approval_state must be one of %s, got %r" % (", ".join(APPROVAL_STATES), record["approval_state"])
        )
    normalized = {
        "manufacturer": maker.strip(),
        "build_line": normalize_line_identity(record["build_line"], "build_line"),
        "approved_line": normalize_line_identity(record["approved_line"], "approved_line"),
        "approval_state": state,
        "approval_body": record.get("approval_body"),
    }
    granted = record.get("approval_date")
    expires = record.get("approval_expiry")
    applied = record.get("application_date")
    normalized["approval_date"] = parse_date(granted, "approval_date") if granted is not None else None
    normalized["approval_expiry"] = parse_date(expires, "approval_expiry") if expires is not None else None
    normalized["application_date"] = parse_date(applied, "application_date") if applied is not None else None
    if normalized["approval_date"] and normalized["approval_expiry"]:
        if normalized["approval_expiry"] < normalized["approval_date"]:
            raise ValueError("approval_expiry precedes approval_date")
    if state == "approved" and normalized["approval_expiry"] is None:
        raise ValueError("an approved line must carry an approval_expiry")
    if state == "pending" and normalized["application_date"] is None:
        raise ValueError("a pending line must carry an application_date")
    return normalized


def audit_pid_content(pid):
    """Return the content audit of a process identification document."""
    if pid is None:
        raise ValueError("pid must be provided; a missing document is not an empty one")
    if isinstance(pid, dict):
        declared = {}
        for key, value in pid.items():
            if not isinstance(key, str):
                raise ValueError("pid content keys must be strings, got %r" % (key,))
            declared[key.strip().lower()] = bool(value)
    elif isinstance(pid, (list, tuple, set, frozenset)):
        declared = {}
        for key in pid:
            if not isinstance(key, str):
                raise ValueError("pid content items must be strings, got %r" % (key,))
            declared[key.strip().lower()] = True
    else:
        raise ValueError("pid must be a mapping or a sequence of content keys")
    unknown = sorted(k for k in declared if k not in MANDATED_PID_CONTENT)
    if unknown:
        raise ValueError("pid names content outside the mandated set: %s" % ", ".join(unknown))
    present = [k for k in MANDATED_PID_CONTENT if declared.get(k)]
    missing = [k for k in MANDATED_PID_CONTENT if not declared.get(k)]
    return {
        "present": present,
        "missing": missing,
        "mandated_count": len(MANDATED_PID_CONTENT),
        "completeness": len(present) / float(len(MANDATED_PID_CONTENT)),
        "complete": not missing,
    }


def approval_currency(record, assessment_date):
    """Return the currency of the line approval at the assessment date."""
    # validate_manufacturer_record is idempotent, so an already-normalized
    # record can be handed straight back in without a second spelling of the rules.
    normalized = validate_manufacturer_record(record)
    day = parse_date(assessment_date, "assessment_date")
    state = normalized["approval_state"]
    expiry = normalized["approval_expiry"]
    applied = normalized["application_date"]
    days_remaining = None
    current = False
    reason = ""
    if state == "approved":
        days_remaining = (expiry - day).days
        current = days_remaining >= 0
        reason = "approval in force" if current else "approval expired %d day(s) ago" % (-days_remaining)
    elif state == "pending":
        if applied > day:
            reason = "application is dated after the assessment day"
        else:
            current = True
            reason = "approval application lodged and open"
    else:
        reason = "approval state '%s' is outside the preferred case" % state
    return {
        "state": state,
        "assessment_date": day,
        "days_remaining": days_remaining,
        "current": current,
        "reason": reason,
    }


def line_identity_matches(build_line, approved_line):
    """Return True when the hybrid is built on the line the approval names."""
    return normalize_line_identity(build_line, "build_line") == normalize_line_identity(
        approved_line, "approved_line"
    )


def categorize_manufacturer(record, pid, assessment_date):
    """Return the clause 5.2.1 category decision for one hybrid source.

    Keys returned: manufacturer, category, preferred, currency, pid_audit,
    line_match, findings.
    """
    normalized = validate_manufacturer_record(record)
    audit = audit_pid_content(pid)
    currency = approval_currency(normalized, assessment_date)
    match = normalized["build_line"] == normalized["approved_line"]
    findings = []
    if normalized["approval_state"] not in ADMISSIBLE_APPROVAL_STATES:
        findings.append(
            "line approval state '%s' keeps this source out of the preferred case"
            % normalized["approval_state"]
        )
    elif not currency["current"]:
        findings.append(currency["reason"])
    if not match:
        findings.append(
            "the hybrid is built on line '%s' while the approval names line '%s'"
            % (normalized["build_line"], normalized["approved_line"])
        )
    if audit["missing"]:
        findings.append(
            "process identification document is missing %d mandated item(s): %s"
            % (len(audit["missing"]), ", ".join(audit["missing"]))
        )
    preferred = not findings
    return {
        "manufacturer": normalized["manufacturer"],
        "category": "category-1" if preferred else "not-category-1",
        "preferred": preferred,
        "currency": currency,
        "pid_audit": audit,
        "line_match": match,
        "findings": findings,
    }
