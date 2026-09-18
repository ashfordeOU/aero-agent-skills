"""Step 4 of the hazard-analysis process: track, communicate, accept.

Anchor: ECSS-Q-ST-40-02C clause 5.2.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Drive each hazard report through the status states of the hazard log
   in a legal order. The states exist so a reviewer can tell an open
   hazard from a controlled one from an accepted one; a jump that skips
   a state destroys that distinction and is rejected here rather than
   discovered later.
2. Match the acceptance authority to the residual severity. The worse
   the residual consequence, the higher the level that has to sign it,
   and a signature at working level on a catastrophic residual is the
   defect this check exists for.
3. Grade the acceptance record itself: rationale, supporting evidence,
   a named signatory and a date. An acceptance with no rationale is a
   status change wearing the word accepted.
4. Work out who still owes a notification. Each status change has an
   audience, and a change communicated to nobody leaves the people who
   act on the hazard working from the previous state.
5. Aggregate the log: the entries stuck in a state, the acceptances
   signed at the wrong level, the incomplete records and the
   outstanding notifications.

Stdlib only, offline, deterministic.
"""

# Hazard-report status states, in the order a report walks them.
STATUS_STATES = ("open", "in-work", "controlled", "verified", "accepted", "closed")
STATUS_ORDINAL = {name: i for i, name in enumerate(STATUS_STATES)}

# The transitions the log permits. A report may move forward one state,
# or fall back to in-work when new information reopens it.
LEGAL_TRANSITIONS = {
    "open": ("in-work",),
    "in-work": ("controlled",),
    "controlled": ("verified", "in-work"),
    "verified": ("accepted", "in-work"),
    "accepted": ("closed", "in-work"),
    "closed": (),
}

SEVERITY_CATEGORIES = ("catastrophic", "critical", "major", "minor")
SEVERITY_ORDINAL = {name: i for i, name in enumerate(SEVERITY_CATEGORIES)}

# Acceptance authority levels, highest first.
AUTHORITY_LEVELS = (
    "customer-safety-review-board",
    "project-manager",
    "product-assurance-manager",
    "working-level-engineer",
)
AUTHORITY_ORDINAL = {name: i for i, name in enumerate(AUTHORITY_LEVELS)}

# Minimum authority that may accept a residual of each severity.
MINIMUM_AUTHORITY_BY_SEVERITY = {
    "catastrophic": "customer-safety-review-board",
    "critical": "project-manager",
    "major": "product-assurance-manager",
    "minor": "working-level-engineer",
}

# Audiences a status change is owed to, by the state being entered.
NOTIFICATION_AUDIENCE = {
    "open": ("safety-engineering",),
    "in-work": ("safety-engineering", "responsible-design-authority"),
    "controlled": ("safety-engineering", "operations-engineering"),
    "verified": ("safety-engineering", "product-assurance"),
    "accepted": ("safety-engineering", "product-assurance", "customer"),
    "closed": ("safety-engineering", "customer"),
}

ACCEPTANCE_RECORD_FIELDS = ("rationale", "evidence_reference", "signatory", "date")


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, value))
    return list(value)


def transition_is_legal(from_state, to_state):
    """Whether one hazard-report status change is permitted."""
    if from_state not in STATUS_ORDINAL:
        raise ValueError("unknown from_state %r" % (from_state,))
    if to_state not in STATUS_ORDINAL:
        raise ValueError("unknown to_state %r" % (to_state,))
    return to_state in LEGAL_TRANSITIONS[from_state]


def replay_status_history(history):
    """Replay a status history and return the illegal transitions."""
    states = _sequence("history", history)
    if not states:
        raise ValueError("history must not be empty")
    if states[0] != "open":
        raise ValueError("a hazard report history starts at open, got %r" % (states[0],))
    illegal = []
    for index in range(1, len(states)):
        previous, current = states[index - 1], states[index]
        if not transition_is_legal(previous, current):
            illegal.append("illegal-transition:%s->%s" % (previous, current))
    return illegal


def minimum_authority(severity):
    """Lowest authority level permitted to accept this residual severity."""
    if severity not in SEVERITY_ORDINAL:
        raise ValueError(
            "unknown severity %r (expected one of %s)"
            % (severity, ", ".join(SEVERITY_CATEGORIES))
        )
    return MINIMUM_AUTHORITY_BY_SEVERITY[severity]


def authority_is_sufficient(severity, authority):
    """Whether an authority level may sign off this residual severity."""
    if authority not in AUTHORITY_ORDINAL:
        raise ValueError(
            "unknown authority %r (expected one of %s)"
            % (authority, ", ".join(AUTHORITY_LEVELS))
        )
    required = minimum_authority(severity)
    return AUTHORITY_ORDINAL[authority] <= AUTHORITY_ORDINAL[required]


def acceptance_record_findings(record):
    """Fields an acceptance record is missing."""
    if record is None:
        return ["acceptance-record-absent"]
    if not isinstance(record, dict):
        raise ValueError("acceptance record must be a mapping")
    findings = []
    for field in ACCEPTANCE_RECORD_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append("acceptance-record-missing:%s" % field)
    return findings


def outstanding_notifications(state, notified):
    """Audiences still owed a notification for the current state."""
    if state not in STATUS_ORDINAL:
        raise ValueError("unknown state %r" % (state,))
    told = set(_sequence("notified", notified))
    return [a for a in NOTIFICATION_AUDIENCE[state] if a not in told]


def validate_hazard_report(report):
    """Validate one hazard report and return a normalized copy."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    report_id = _string("report id", report.get("id"))
    severity = report.get("residual_severity")
    if severity not in SEVERITY_ORDINAL:
        raise ValueError(
            "report %s has unknown residual_severity %r" % (report_id, severity)
        )
    history = _sequence("report %s history" % report_id, report.get("history", []))
    for state in history:
        if state not in STATUS_ORDINAL:
            raise ValueError("report %s has unknown state %r" % (report_id, state))
    if not history:
        raise ValueError("report %s has no status history" % report_id)
    authority = report.get("acceptance_authority")
    if authority is not None and authority not in AUTHORITY_ORDINAL:
        raise ValueError(
            "report %s has unknown acceptance_authority %r" % (report_id, authority)
        )
    return {
        "id": report_id,
        "residual_severity": severity,
        "history": [str(s) for s in history],
        "state": str(history[-1]),
        "acceptance_authority": authority,
        "acceptance_record": report.get("acceptance_record"),
        "notified": [
            str(a) for a in _sequence("report %s notified" % report_id,
                                      report.get("notified", []))
        ],
    }


def assess_hazard_report(report):
    """Assess the tracking, acceptance and communication of one report."""
    norm = validate_hazard_report(report)
    findings = list(replay_status_history(norm["history"]))
    state = norm["state"]
    accepted = STATUS_ORDINAL[state] >= STATUS_ORDINAL["accepted"]
    if accepted:
        if norm["acceptance_authority"] is None:
            findings.append("acceptance-authority-not-recorded")
        elif not authority_is_sufficient(
            norm["residual_severity"], norm["acceptance_authority"]
        ):
            findings.append(
                "acceptance-authority-below-%s-minimum" % norm["residual_severity"]
            )
        findings.extend(acceptance_record_findings(norm["acceptance_record"]))
    outstanding = outstanding_notifications(state, norm["notified"])
    for audience in outstanding:
        findings.append("notification-outstanding:%s" % audience)
    return {
        "id": norm["id"],
        "state": state,
        "residual_severity": norm["residual_severity"],
        "minimum_authority": minimum_authority(norm["residual_severity"]),
        "accepted": accepted,
        "outstanding_notifications": outstanding,
        "findings": findings,
        "controlled": not findings,
    }


def assess_hazard_log(reports):
    """Assess a whole hazard log against clause 5.2.4 step 4."""
    if not isinstance(reports, list) or not reports:
        raise ValueError("reports must be a non-empty list")
    results = []
    seen = set()
    for report in reports:
        result = assess_hazard_report(report)
        if result["id"] in seen:
            raise ValueError("duplicate report id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    by_state = {}
    for result in results:
        by_state[result["state"]] = by_state.get(result["state"], 0) + 1
    return {
        "reports": results,
        "state_distribution": by_state,
        "open_ids": [
            r["id"] for r in results
            if STATUS_ORDINAL[r["state"]] < STATUS_ORDINAL["accepted"]
        ],
        "finding_ids": [r["id"] for r in results if r["findings"]],
        "controlled": all(r["controlled"] for r in results),
    }
