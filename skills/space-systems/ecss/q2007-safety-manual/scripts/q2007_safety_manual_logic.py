"""Safety manual of a space test centre: content and update control.

Anchor: ECSS-Q-ST-20-07C clause 5.9.3 (the safety manual of the test centre:
what it has to contain and how it is kept up to date). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the manual carries every chapter it owes: the hazard inventory, the
   controls, the responsibilities, the emergency plans and the working
   documents that hang off them.
2. Parse and order issue.revision identifiers so the manual and its chapters
   can be compared; a chapter ahead of the manual it sits in is an
   uncontrolled update, not a newer chapter.
3. Grade the manual's currency against its review interval, and against the
   hazard changes that happened after the issue day.
4. Grade distribution: the acknowledged fraction of the controlled copies
   and the withdrawal of the superseded ones.
5. Aggregate: the manual is controlled only when nothing is missing, nothing
   is ahead of the manual, the content is not stale against the hazard
   register, and the distribution is closed out.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "REQUIRED_CHAPTERS",
    "parse_revision",
    "revision_key",
    "compare_revisions",
    "missing_chapters",
    "validate_chapter",
    "update_currency",
    "stale_hazard_changes",
    "distribution_acknowledgement",
    "assess_chapter",
    "assess_safety_manual",
]

FRACTION_TOLERANCE = 1e-9

# The chapters a test-centre safety manual owes. The first four are the
# content of the clause; the rest are the working documents they depend on.
REQUIRED_CHAPTERS = (
    "hazard-inventory",
    "hazard-controls",
    "responsibilities",
    "emergency-plans",
    "permit-to-work",
    "training-requirements",
    "incident-reporting",
)


def _day(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer day number" % label)
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def parse_revision(text):
    """Return the (issue, revision) pair of an 'issue.revision' identifier."""
    if not isinstance(text, str):
        raise ValueError("revision identifier must be a string, got %r" % (text,))
    token = text.strip().upper()
    if not token:
        raise ValueError("revision identifier must not be empty")
    if token.count(".") != 1:
        raise ValueError(
            "revision identifier %r must be written issue.revision, e.g. B.3" % text
        )
    issue, number = token.split(".")
    if not issue or not issue.isalpha():
        raise ValueError(
            "the issue part of %r must be one or more letters, e.g. B.3" % text
        )
    if not number or not number.isdigit():
        raise ValueError(
            "the revision part of %r must be a non-negative integer, e.g. B.3" % text
        )
    return (issue, int(number))


def revision_key(text):
    """Return a sortable key for an issue.revision identifier."""
    issue, number = parse_revision(text)
    return (len(issue), issue, number)


def compare_revisions(left, right):
    """Return -1, 0 or 1 ordering two issue.revision identifiers."""
    a = revision_key(left)
    b = revision_key(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def missing_chapters(chapters):
    """Return the required chapters the manual does not carry."""
    if not isinstance(chapters, (list, tuple)):
        raise ValueError("chapters must be a sequence")
    present = []
    for item in chapters:
        if isinstance(item, dict):
            name = item.get("name")
        else:
            name = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each chapter must carry a non-empty name")
        token = name.strip().lower()
        if token not in present:
            present.append(token)
    return tuple(c for c in REQUIRED_CHAPTERS if c not in present)


def validate_chapter(chapter):
    """Return a normalised chapter record, raising on anything unusable."""
    if not isinstance(chapter, dict):
        raise ValueError("chapter must be a mapping")
    for key in ("name", "revision", "approved_by", "pages"):
        if key not in chapter:
            raise ValueError("chapter missing required key '%s'" % key)
    name = chapter["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("chapter name must be a non-empty string")
    approved_by = chapter["approved_by"]
    if approved_by is not None and not isinstance(approved_by, str):
        raise ValueError("chapter approved_by must be a name or None")
    pages = chapter["pages"]
    if not isinstance(pages, int) or isinstance(pages, bool):
        raise ValueError("chapter pages must be an integer")
    if pages < 1:
        raise ValueError("chapter %s has no pages" % name)
    issue, number = parse_revision(chapter["revision"])
    return {
        "name": name.strip().lower(),
        "revision": "%s.%d" % (issue, number),
        "issue": issue,
        "revision_number": number,
        "approved_by": approved_by.strip() if isinstance(approved_by, str) else None,
        "pages": pages,
    }


def update_currency(issue_day, review_interval_days, today):
    """Return 'current', 'due' or 'overdue' for the manual's review."""
    issue = _day("issue_day", issue_day)
    interval = _day("review_interval_days", review_interval_days)
    now = _day("today", today)
    if interval == 0:
        raise ValueError("review_interval_days must be at least one day")
    if now < issue:
        raise ValueError("today %d precedes the issue day %d" % (now, issue))
    elapsed = now - issue
    if elapsed > interval:
        return "overdue"
    if elapsed == interval:
        return "due"
    return "current"


def stale_hazard_changes(issue_day, hazard_change_days):
    """Return the hazard-register change days that postdate the manual issue."""
    issue = _day("issue_day", issue_day)
    if not isinstance(hazard_change_days, (list, tuple)):
        raise ValueError("hazard_change_days must be a sequence")
    later = []
    for i, value in enumerate(hazard_change_days):
        day = _day("hazard_change_days[%d]" % i, value)
        if day > issue:
            later.append(day)
    return sorted(later)


def distribution_acknowledgement(acknowledged, issued):
    """Return the fraction of controlled copies whose receipt is acknowledged."""
    for label, value in (("acknowledged", acknowledged), ("issued", issued)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if issued == 0:
        raise ValueError(
            "no controlled copy was issued; an acknowledgement fraction is undefined"
        )
    if acknowledged > issued:
        raise ValueError(
            "%d acknowledgements exceed the %d copies issued" % (acknowledged, issued)
        )
    return float(acknowledged) / float(issued)


def assess_chapter(chapter, manual_revision):
    """Assess one chapter against the manual revision it sits in."""
    record = validate_chapter(chapter)
    findings = []
    if record["approved_by"] is None or not record["approved_by"]:
        findings.append("%s carries no approval" % record["name"])
    if compare_revisions(record["revision"], manual_revision) > 0:
        findings.append(
            "%s is at %s, ahead of the manual at %s; the update was not controlled"
            % (record["name"], record["revision"], manual_revision)
        )
    record["findings"] = findings
    record["controlled"] = not findings
    return record


def assess_safety_manual(spec):
    """Run the full clause 5.9.3 safety-manual assessment.

    spec keys: revision, issue_day, review_interval_days, today, chapters,
    copies_issued, copies_acknowledged; optional hazard_change_days,
    obsolete_copies_withdrawn, required_acknowledgement (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("revision", "issue_day", "review_interval_days", "today",
                "chapters", "copies_issued", "copies_acknowledged"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    chapters = spec["chapters"]
    if not isinstance(chapters, (list, tuple)) or not chapters:
        raise ValueError("spec['chapters'] must be a non-empty sequence")
    issue, number = parse_revision(spec["revision"])
    manual_revision = "%s.%d" % (issue, number)
    required_ack = spec.get("required_acknowledgement", 1.0)
    if not isinstance(required_ack, (int, float)) or isinstance(required_ack, bool):
        raise ValueError("required_acknowledgement must be a real number")
    required_ack = float(required_ack)
    if not math.isfinite(required_ack) or required_ack < 0.0 or required_ack > 1.0:
        raise ValueError("required_acknowledgement must lie in [0, 1]")
    withdrawn = spec.get("obsolete_copies_withdrawn", False)
    if not isinstance(withdrawn, bool):
        raise ValueError("'obsolete_copies_withdrawn' must be a boolean")
    records = [assess_chapter(c, manual_revision) for c in chapters]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicate chapter %r" % record["name"])
        seen.add(record["name"])
    absent = missing_chapters(chapters)
    currency = update_currency(
        spec["issue_day"], spec["review_interval_days"], spec["today"]
    )
    stale = stale_hazard_changes(spec["issue_day"], spec.get("hazard_change_days", []))
    ack = distribution_acknowledgement(
        spec["copies_acknowledged"], spec["copies_issued"]
    )
    findings = []
    if absent:
        findings.append("the manual carries no chapter on %s" % ", ".join(absent))
    for record in records:
        findings.extend(record["findings"])
    if currency == "overdue":
        findings.append("the manual review is overdue against its stated interval")
    if stale:
        findings.append(
            "%d hazard-register change(s) postdate manual issue %s; the content "
            "is stale" % (len(stale), manual_revision)
        )
    ack_met = ack > required_ack or math.isclose(
        ack, required_ack, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    if not ack_met:
        findings.append(
            "%.4f of the controlled copies are acknowledged, below the required "
            "%.4f" % (ack, required_ack)
        )
    if not withdrawn:
        findings.append("the superseded controlled copies are not withdrawn")
    return {
        "revision": manual_revision,
        "chapters": records,
        "missing_chapters": absent,
        "currency": currency,
        "stale_hazard_changes": stale,
        "acknowledgement": ack,
        "required_acknowledgement": required_ack,
        "obsolete_copies_withdrawn": withdrawn,
        "findings": findings,
        "manual_controlled": not findings,
    }
