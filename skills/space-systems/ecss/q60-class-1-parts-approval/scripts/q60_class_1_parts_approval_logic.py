"""Customer approval assessment for parts proposed for class 1 flight use.

Anchor: ECSS-Q-ST-60C clause 4.2.4 — the customer review and sign-off every
electrical, electronic and electromechanical part proposed for class 1 flight
use has to carry before it may be built into flight hardware. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each submission: the part identity it is about, the evidence
   package behind it, the disposition the customer returned, who signed it and
   on what date.
2. Hold the evidence package to the mandatory evidence set; an absent item is
   a submission that cannot be reviewed, not a submission with nothing to
   object to.
3. Test the signatory twice: is this name on the customer's approver roster at
   all, and is the signatory independent of the organisation that submitted
   the part.
4. Age the sign-off against the review date and refuse one that has run past
   its validity window, or one dated after the review itself.
5. Read the disposition. A conditional approval releases nothing until every
   condition attached to it carries a closure record.
6. Compare the submitted set against the parts the design actually proposes
   for flight and name every proposed part that was never submitted.
7. Return the per-part records, the never-submitted parts and a release
   verdict carrying every finding rather than only the first.
"""

import datetime

__all__ = [
    "DISPOSITIONS",
    "RELEASING_DISPOSITIONS",
    "MANDATORY_EVIDENCE",
    "normalize_token",
    "parse_review_date",
    "approval_age_days",
    "validate_approver",
    "validate_submission",
    "missing_evidence",
    "open_conditions",
    "assess_submission",
    "unsubmitted_parts",
    "assess_approval_round",
]

# Dispositions a customer review can return. Normalized (lower case,
# hyphenated) so a free-text disposition cannot slip past the comparison.
DISPOSITIONS = (
    "approved",
    "approved-with-conditions",
    "rejected",
    "pending",
)

# Dispositions that can release a part at all; a conditional one still has to
# clear its conditions before the part is released.
RELEASING_DISPOSITIONS = ("approved", "approved-with-conditions")

# Evidence a submission has to carry before the customer can review it.
MANDATORY_EVIDENCE = (
    "part-identity",
    "evaluation-record",
    "application-data",
    "procurement-specification",
)


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_count(value, label, minimum=0):
    """Return a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def normalize_token(value, label="token"):
    """Return a token in the normalized lower-case hyphenated form."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def parse_review_date(value, label="date"):
    """Return a calendar date parsed from an ISO day stamp."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar day, got '%s'" % (label, text))


def approval_age_days(decision_date, review_date):
    """Return how many whole days old a sign-off is at the review date."""
    decided = parse_review_date(decision_date, "decision_date")
    reviewed = parse_review_date(review_date, "review_date")
    age = (reviewed - decided).days
    if age < 0:
        raise ValueError("decision_date is later than review_date")
    return age


def validate_approver(approver, label="approver"):
    """Return the validated signatory of one customer disposition."""
    if not isinstance(approver, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("name", "organisation"):
        if key not in approver:
            raise ValueError("%s missing required key '%s'" % (label, key))
    return {
        "name": _require_text(approver["name"], "%s name" % label),
        "organisation": normalize_token(approver["organisation"], "%s organisation" % label),
    }


def validate_submission(submission):
    """Return one validated part-approval submission record."""
    if not isinstance(submission, dict):
        raise ValueError("each submission must be a mapping")
    for key in ("part_number", "manufacturer", "submitter_organisation", "evidence",
                "disposition"):
        if key not in submission:
            raise ValueError("submission missing required key '%s'" % key)
    part_number = _require_text(submission["part_number"], "part_number")
    manufacturer = _require_text(submission["manufacturer"], "manufacturer")
    submitter = normalize_token(submission["submitter_organisation"],
                                "submitter_organisation")
    raw_evidence = submission["evidence"]
    if not isinstance(raw_evidence, (list, tuple)):
        raise ValueError("evidence for '%s' must be a sequence" % part_number)
    evidence = []
    for index, item in enumerate(raw_evidence):
        token = normalize_token(item, "evidence[%d]" % index)
        if token in evidence:
            raise ValueError("evidence item '%s' is listed twice" % token)
        evidence.append(token)
    disposition = normalize_token(submission["disposition"], "disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError(
            "disposition must be one of %s, got '%s'" % (list(DISPOSITIONS), disposition)
        )
    approver = submission.get("approver")
    if approver is not None:
        approver = validate_approver(approver)
    decision_date = submission.get("decision_date")
    if decision_date is not None:
        decision_date = parse_review_date(decision_date, "decision_date")
    raw_conditions = submission.get("conditions", [])
    if not isinstance(raw_conditions, (list, tuple)):
        raise ValueError("conditions for '%s' must be a sequence" % part_number)
    conditions = []
    seen = set()
    for index, condition in enumerate(raw_conditions):
        if not isinstance(condition, dict) or "reference" not in condition:
            raise ValueError("conditions[%d] must be a mapping carrying 'reference'" % index)
        reference = normalize_token(condition["reference"], "conditions[%d] reference" % index)
        if reference in seen:
            raise ValueError("condition '%s' is listed twice" % reference)
        seen.add(reference)
        closed = condition.get("closed", False)
        if not isinstance(closed, bool):
            raise ValueError("condition '%s' closure flag must be a boolean" % reference)
        conditions.append({"reference": reference, "closed": closed})
    return {
        "part_number": part_number,
        "manufacturer": manufacturer,
        "submitter_organisation": submitter,
        "evidence": evidence,
        "disposition": disposition,
        "approver": approver,
        "decision_date": decision_date,
        "conditions": conditions,
    }


def missing_evidence(submission):
    """Return the mandatory evidence items a submission does not carry."""
    record = validate_submission(submission)
    return [item for item in MANDATORY_EVIDENCE if item not in record["evidence"]]


def open_conditions(submission):
    """Return the references of conditions that carry no closure record."""
    record = validate_submission(submission)
    return [c["reference"] for c in record["conditions"] if not c["closed"]]


def assess_submission(submission, context):
    """Return one submission record carrying its release verdict and findings."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping")
    for key in ("review_date", "authorized_approvers", "validity_days"):
        if key not in context:
            raise ValueError("context missing required key '%s'" % key)
    review_date = parse_review_date(context["review_date"], "review_date")
    roster = context["authorized_approvers"]
    if not isinstance(roster, (list, tuple)) or not roster:
        raise ValueError("authorized_approvers must be a non-empty sequence")
    roster_names = set()
    for index, name in enumerate(roster):
        roster_names.add(_require_text(name, "authorized_approvers[%d]" % index))
    validity_days = _require_count(context["validity_days"], "validity_days", minimum=1)

    record = validate_submission(submission)
    findings = []

    absent = [item for item in MANDATORY_EVIDENCE if item not in record["evidence"]]
    for item in absent:
        findings.append(
            "submission for '%s' carries no %s" % (record["part_number"], item)
        )

    approver = record["approver"]
    if approver is None:
        findings.append("submission for '%s' carries no signatory" % record["part_number"])
    else:
        if approver["name"] not in roster_names:
            findings.append(
                "'%s' signed off '%s' but is not on the customer approver roster"
                % (approver["name"], record["part_number"])
            )
        if approver["organisation"] == record["submitter_organisation"]:
            findings.append(
                "sign-off for '%s' is not independent of the submitting organisation"
                % record["part_number"]
            )

    age_days = None
    if record["decision_date"] is None:
        findings.append("sign-off for '%s' is undated" % record["part_number"])
    else:
        age_days = approval_age_days(record["decision_date"], review_date)
        if age_days > validity_days:
            findings.append(
                "sign-off for '%s' is %d days old against a %d day validity window"
                % (record["part_number"], age_days, validity_days)
            )

    still_open = [c["reference"] for c in record["conditions"] if not c["closed"]]
    if record["disposition"] == "approved-with-conditions":
        if not record["conditions"]:
            raise ValueError(
                "'%s' is approved with conditions but lists none" % record["part_number"]
            )
        for reference in still_open:
            findings.append(
                "condition '%s' on '%s' carries no closure record"
                % (reference, record["part_number"])
            )
    if record["disposition"] not in RELEASING_DISPOSITIONS:
        findings.append(
            "'%s' carries a '%s' disposition and is not released"
            % (record["part_number"], record["disposition"])
        )

    record["missing_evidence"] = absent
    record["open_conditions"] = still_open
    record["age_days"] = age_days
    record["findings"] = findings
    record["released"] = not findings
    return record


def unsubmitted_parts(proposed, records):
    """Return the proposed part numbers that never reached a customer review."""
    if not isinstance(proposed, (list, tuple)):
        raise ValueError("proposed must be a sequence of part numbers")
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of submission records")
    submitted = set()
    for record in records:
        if not isinstance(record, dict) or "part_number" not in record:
            raise ValueError("each record must be a mapping carrying 'part_number'")
        submitted.add(record["part_number"])
    absent = []
    for index, part_number in enumerate(proposed):
        name = _require_text(part_number, "proposed[%d]" % index)
        if name not in submitted and name not in absent:
            absent.append(name)
    return absent


def assess_approval_round(spec):
    """Run the full clause 4.2.4 customer approval assessment.

    spec keys: proposed_parts, submissions, review_date, authorized_approvers,
    validity_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("proposed_parts", "submissions", "review_date", "authorized_approvers",
                "validity_days"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    proposed = spec["proposed_parts"]
    if not isinstance(proposed, (list, tuple)) or not proposed:
        raise ValueError("spec['proposed_parts'] must be a non-empty sequence")
    submissions = spec["submissions"]
    if not isinstance(submissions, (list, tuple)):
        raise ValueError("spec['submissions'] must be a sequence")
    context = {
        "review_date": spec["review_date"],
        "authorized_approvers": spec["authorized_approvers"],
        "validity_days": spec["validity_days"],
    }

    records = []
    seen = set()
    for submission in submissions:
        record = assess_submission(submission, context)
        if record["part_number"] in seen:
            raise ValueError("'%s' is submitted twice" % record["part_number"])
        seen.add(record["part_number"])
        records.append(record)

    absent = unsubmitted_parts(proposed, records)
    findings = [
        "'%s' is proposed for flight but was never submitted for review" % name
        for name in absent
    ]
    for record in records:
        findings.extend(record["findings"])

    released = [r["part_number"] for r in records if r["released"]]
    return {
        "review_date": parse_review_date(spec["review_date"], "review_date"),
        "submissions": records,
        "unsubmitted_parts": absent,
        "released_parts": released,
        "released_count": len(released),
        "proposed_count": len(set(proposed)),
        "round_clean": not findings,
        "findings": findings,
    }
