"""Test readiness and post-test reviews.

Anchor: ECSS-Q-ST-20C clause 5.6.5 (the review held before a test to decide
whether it may start, and the review held after it to decide whether it is
finished, each against defined criteria and each leaving a record).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise a review of a declared kind: its criteria and their states, its
   attendance, its action items, its minutes reference and its date.
2. Grade the criteria: every criterion of that kind's list addressed, a waiver
   admissible only on a criterion the kind does not hold mandatory, and every
   waiver carrying a reference and an approver.
3. Grade the record: the chair and product assurance present, minutes
   referenced, and no open action item that was raised as blocking.
4. Grade the schedule: a readiness review closes before the test starts, a
   post-test review is held after it ends.
5. Return the go / no-go decision for the readiness review and the closed /
   open decision for the post-test review, with a readiness fraction as
   evidence rather than a bare verdict.
"""

from datetime import date

__all__ = [
    "TRR_CRITERIA",
    "PTR_CRITERIA",
    "MANDATORY_TRR_CRITERIA",
    "MANDATORY_PTR_CRITERIA",
    "CRITERION_STATES",
    "REQUIRED_ATTENDEES",
    "REVIEW_KINDS",
    "normalise_identifier",
    "parse_iso_date",
    "criteria_for_kind",
    "mandatory_for_kind",
    "validate_review",
    "criterion_findings",
    "record_findings",
    "schedule_findings",
    "readiness_fraction",
    "assess_review",
    "assess_review_pair",
]

# What the readiness review has to settle before a test article is committed.
TRR_CRITERIA = (
    "procedure-approved",
    "article-configuration-known",
    "facility-and-gse-calibrated",
    "safety-clearance-granted",
    "open-nonconformances-dispositioned",
    "personnel-assigned",
)

# What the post-test review has to settle before the test is called finished.
PTR_CRITERIA = (
    "test-data-complete",
    "discrepancies-dispositioned",
    "test-objectives-met",
    "report-issued",
    "article-post-test-inspection",
)

# Criteria no waiver can clear, because clearing them would remove the reason
# the review exists.
MANDATORY_TRR_CRITERIA = (
    "procedure-approved",
    "article-configuration-known",
    "facility-and-gse-calibrated",
    "safety-clearance-granted",
    "open-nonconformances-dispositioned",
)

MANDATORY_PTR_CRITERIA = (
    "test-data-complete",
    "discrepancies-dispositioned",
    "test-objectives-met",
)

CRITERION_STATES = ("met", "not-met", "waived")

# A review without these two in the room is a meeting, not a review.
REQUIRED_ATTENDEES = ("chair", "product-assurance")

REVIEW_KINDS = ("trr", "ptr")


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_iso_date(value, label):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        parts = [int(part) for part in value.strip().split("-")]
    except ValueError:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    if len(parts) != 3:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    try:
        return date(parts[0], parts[1], parts[2])
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (label, value))


def criteria_for_kind(kind):
    """Return the criterion list a review of this kind is graded against."""
    key = normalise_identifier(kind, "review kind")
    if key == "trr":
        return TRR_CRITERIA
    if key == "ptr":
        return PTR_CRITERIA
    raise ValueError("review kind must be one of %s, got %r" % ("/".join(REVIEW_KINDS), kind))


def mandatory_for_kind(kind):
    """Return the criteria of this kind that no waiver may clear."""
    key = normalise_identifier(kind, "review kind")
    if key == "trr":
        return MANDATORY_TRR_CRITERIA
    if key == "ptr":
        return MANDATORY_PTR_CRITERIA
    raise ValueError("review kind must be one of %s, got %r" % ("/".join(REVIEW_KINDS), kind))


def _validate_criteria(raw, kind):
    """Return the normalised criterion states of a review."""
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("review 'criteria' must be a non-empty sequence")
    known = criteria_for_kind(kind)
    states = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("criteria[%d] must be a mapping" % index)
        name = normalise_identifier(item.get("id"), "criteria[%d].id" % index)
        if name in states:
            raise ValueError("duplicate criterion %r" % name)
        if name not in known:
            raise ValueError("criterion %r is not graded by a %s" % (name, kind))
        state = normalise_identifier(item.get("state"), "criteria[%d].state" % index)
        if state not in CRITERION_STATES:
            raise ValueError(
                "criteria[%d].state must be one of %s, got %r"
                % (index, "/".join(CRITERION_STATES), state)
            )
        entry = {"id": name, "state": state, "waiver_reference": None, "waiver_approver": None}
        if state == "waived":
            reference = item.get("waiver_reference")
            approver = item.get("waiver_approver")
            entry["waiver_reference"] = (
                None if reference is None
                else normalise_identifier(reference, "criteria[%d].waiver_reference" % index)
            )
            entry["waiver_approver"] = (
                None if approver is None
                else normalise_identifier(approver, "criteria[%d].waiver_approver" % index)
            )
        states[name] = entry
    return states


def _validate_actions(raw):
    """Return the normalised action items raised by a review."""
    if raw is None:
        raw = []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("review 'actions' must be a sequence")
    actions = []
    seen = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("actions[%d] must be a mapping" % index)
        action_id = normalise_identifier(item.get("id"), "actions[%d].id" % index)
        if action_id in seen:
            raise ValueError("duplicate action id %r" % action_id)
        seen.add(action_id)
        actions.append(
            {
                "id": action_id,
                "owner": normalise_identifier(item.get("owner"), "actions[%d].owner" % index),
                "due_date": parse_iso_date(item.get("due_date"), "actions[%d].due_date" % index),
                "closed": bool(item.get("closed", False)),
                "blocking": bool(item.get("blocking", False)),
            }
        )
    return actions


def validate_review(review):
    """Return a normalised review record; raise on a malformed one."""
    if not isinstance(review, dict):
        raise ValueError("review must be a mapping")
    kind = normalise_identifier(review.get("kind"), "review kind")
    if kind not in REVIEW_KINDS:
        raise ValueError("review kind must be one of %s, got %r" % ("/".join(REVIEW_KINDS), kind))
    raw_attendees = review.get("attendees", [])
    if not isinstance(raw_attendees, (list, tuple)):
        raise ValueError("review 'attendees' must be a sequence")
    minutes = review.get("minutes_reference")
    return {
        "kind": kind,
        "criteria": _validate_criteria(review.get("criteria"), kind),
        "attendees": [
            normalise_identifier(role, "attendees[%d]" % i)
            for i, role in enumerate(raw_attendees)
        ],
        "actions": _validate_actions(review.get("actions")),
        "minutes_reference": (
            None if minutes is None else normalise_identifier(minutes, "minutes_reference")
        ),
        "held_on": parse_iso_date(review.get("held_on"), "held_on"),
    }


def criterion_findings(record):
    """Return the criterion findings of one normalised review."""
    known = criteria_for_kind(record["kind"])
    mandatory = mandatory_for_kind(record["kind"])
    findings = []
    unaddressed = [name for name in known if name not in record["criteria"]]
    if unaddressed:
        findings.append(
            "criteria the review never addressed: %s" % ", ".join(unaddressed)
        )
    for name in known:
        entry = record["criteria"].get(name)
        if entry is None:
            continue
        if entry["state"] == "not-met":
            findings.append("criterion %s is not met" % name)
        elif entry["state"] == "waived":
            if name in mandatory:
                findings.append("criterion %s is mandatory and cannot be waived" % name)
                continue
            if entry["waiver_reference"] is None:
                findings.append("waiver on %s carries no reference" % name)
            if entry["waiver_approver"] is None:
                findings.append("waiver on %s carries no approver" % name)
    return findings


def record_findings(record):
    """Return the record-keeping findings of one normalised review."""
    findings = []
    for role in REQUIRED_ATTENDEES:
        if role not in record["attendees"]:
            findings.append("review was held without %s" % role)
    if record["minutes_reference"] is None:
        findings.append("review records no minutes reference")
    open_blocking = [a["id"] for a in record["actions"] if a["blocking"] and not a["closed"]]
    if open_blocking:
        findings.append("blocking actions still open: %s" % ", ".join(sorted(open_blocking)))
    return findings


def schedule_findings(record, test_start, test_end):
    """Return the scheduling findings of one normalised review."""
    start = parse_iso_date(test_start, "test_start")
    end = parse_iso_date(test_end, "test_end")
    if end < start:
        raise ValueError("test_end precedes test_start")
    if record["kind"] == "trr":
        if record["held_on"] > start:
            return ["readiness review was held after the test started"]
        return []
    if record["held_on"] < end:
        return ["post-test review was held before the test ended"]
    return []


def readiness_fraction(record):
    """Return the fraction of this kind's criteria that are met or waived."""
    known = criteria_for_kind(record["kind"])
    cleared = 0
    for name in known:
        entry = record["criteria"].get(name)
        if entry is not None and entry["state"] in ("met", "waived"):
            cleared += 1
    return cleared / float(len(known))


def assess_review(review, test_start, test_end):
    """Assess one review and return its decision record."""
    record = validate_review(review)
    findings = []
    findings.extend(criterion_findings(record))
    findings.extend(record_findings(record))
    findings.extend(schedule_findings(record, test_start, test_end))
    clean = not findings
    if record["kind"] == "trr":
        decision = "go" if clean else "no-go"
    else:
        decision = "closed" if clean else "open"
    return {
        "kind": record["kind"],
        "held_on": record["held_on"],
        "readiness_fraction": readiness_fraction(record),
        "findings": findings,
        "decision": decision,
    }


def assess_review_pair(readiness_review, post_test_review, test_start, test_end):
    """Assess the readiness and post-test reviews of one test together."""
    trr = assess_review(readiness_review, test_start, test_end)
    if trr["kind"] != "trr":
        raise ValueError("the first review must be the readiness review")
    result = {"readiness": trr, "post_test": None, "findings": list(trr["findings"])}
    if post_test_review is None:
        result["post_test"] = None
        result["verdict"] = "test-not-closed" if trr["decision"] == "go" else "test-not-started"
        return result
    ptr = assess_review(post_test_review, test_start, test_end)
    if ptr["kind"] != "ptr":
        raise ValueError("the second review must be the post-test review")
    result["post_test"] = ptr
    result["findings"].extend(ptr["findings"])
    if trr["decision"] == "go" and ptr["decision"] == "closed":
        result["verdict"] = "test-closed"
    elif trr["decision"] != "go":
        result["verdict"] = "test-not-started"
    else:
        result["verdict"] = "test-not-closed"
    return result
