"""Storage, handling and transport deliverables scheduled per project review.

Anchor: ECSS-Q-ST-20-08C Annex E, informative (the list of storage, handling
and transportation deliverables and the project review each one is due at).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the Annex E catalogue: each deliverable, the review it is anchored
   to in a project that runs the full review sequence, and whether it is
   expected of every project or only of some.
2. Normalise the project's own review milestone set with its dates, refusing
   a sequence whose dates run backwards through the review order.
3. Anchor each deliverable. A project that does not hold the review a
   deliverable is listed against does not thereby escape the deliverable: it
   is re-anchored to the nearest earlier review the project does hold, and
   the move is reported. A deliverable with no earlier held review has
   nowhere to land and blocks.
4. Turn the anchor review date into a submission due date by stepping back
   the agreed lead in working days, weekends skipped.
5. Grade the planned submission against that due date and return the
   schedule ordered by due date with the late and unplanned items named.
"""

from datetime import date, timedelta

__all__ = [
    "REVIEW_ORDER",
    "DELIVERABLES",
    "DEFAULT_LEAD_WORKING_DAYS",
    "normalise_identifier",
    "parse_day",
    "review_index",
    "subtract_working_days",
    "validate_reviews",
    "validate_submissions",
    "anchor_review",
    "due_day",
    "grade_deliverable",
    "assess_review_deliverables",
]

# The project review sequence a deliverable can be anchored to.
REVIEW_ORDER = ("prr", "srr", "pdr", "cdr", "qr", "ar", "orr", "frr")

# The Annex E catalogue: deliverable -> (review it is due at, expected of
# every project).
DELIVERABLES = {
    "storage-handling-transport-plan": ("pdr", True),
    "handling-and-transport-gse-list": ("pdr", True),
    "container-design-report": ("cdr", True),
    "storage-conditions-specification": ("cdr", True),
    "preservation-and-repackaging-instructions": ("cdr", False),
    "container-qualification-evidence": ("qr", True),
    "handling-procedures": ("qr", True),
    "transport-procedures": ("qr", True),
    "environmental-monitoring-record": ("ar", True),
    "storage-and-transport-nonconformance-record": ("ar", True),
    "long-term-storage-extension-request": ("ar", False),
    "transport-readiness-statement": ("orr", True),
    "packing-list-and-shipping-documents": ("orr", True),
}

# How far ahead of its review a deliverable is submitted, in working days.
DEFAULT_LEAD_WORKING_DAYS = 20

_REVIEW_INDEX = {name: position for position, name in enumerate(REVIEW_ORDER)}


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO calendar day as a date; raise on anything else."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO calendar day, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO calendar day: %r" % (label, value))


def review_index(review):
    """Return the position of a review in the project review sequence."""
    name = normalise_identifier(review, "review")
    if name not in _REVIEW_INDEX:
        raise ValueError(
            "unknown review %r; the review sequence is %s" % (name, "/".join(REVIEW_ORDER))
        )
    return _REVIEW_INDEX[name]


def subtract_working_days(day, working_days):
    """Step back a whole number of working days, skipping weekends."""
    if not isinstance(day, date):
        raise ValueError("day must be a date")
    if not isinstance(working_days, int) or isinstance(working_days, bool):
        raise ValueError("working_days must be an integer, got %r" % (working_days,))
    if working_days < 0:
        raise ValueError("working_days must not be negative, got %d" % working_days)
    current = day
    remaining = working_days
    while remaining > 0:
        current = current - timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def validate_reviews(reviews):
    """Return the project's held reviews keyed by review, dates checked."""
    if not isinstance(reviews, (list, tuple)) or not reviews:
        raise ValueError("reviews must be a non-empty sequence of held milestones")
    held = {}
    for position, item in enumerate(reviews):
        if not isinstance(item, dict):
            raise ValueError("reviews[%d] must be a mapping" % position)
        name = normalise_identifier(item.get("review"), "reviews[%d].review" % position)
        review_index(name)
        if name in held:
            raise ValueError("review %r is held twice" % name)
        held[name] = parse_day(item.get("day"), "reviews[%d].day" % position)
    ordered = sorted(held, key=review_index)
    for position in range(1, len(ordered)):
        earlier = held[ordered[position - 1]]
        later = held[ordered[position]]
        if later < earlier:
            raise ValueError(
                "review %s is dated before %s, which reverses the review sequence"
                % (ordered[position], ordered[position - 1])
            )
    return held


def validate_submissions(submissions):
    """Return the planned submission days keyed by deliverable."""
    if submissions is None:
        submissions = []
    if not isinstance(submissions, (list, tuple)):
        raise ValueError("submissions must be a sequence")
    planned = {}
    for position, item in enumerate(submissions):
        if not isinstance(item, dict):
            raise ValueError("submissions[%d] must be a mapping" % position)
        name = normalise_identifier(
            item.get("deliverable"), "submissions[%d].deliverable" % position
        )
        if name not in DELIVERABLES:
            raise ValueError(
                "submissions[%d] names %r, which is not an Annex E deliverable"
                % (position, name)
            )
        if name in planned:
            raise ValueError("deliverable %r is planned twice" % name)
        planned[name] = parse_day(item.get("day"), "submissions[%d].day" % position)
    return planned


def anchor_review(deliverable, held_reviews):
    """Return (anchor review, re-anchored) for a deliverable in this project."""
    name = normalise_identifier(deliverable, "deliverable")
    if name not in DELIVERABLES:
        raise ValueError("%r is not an Annex E deliverable" % name)
    if not isinstance(held_reviews, dict) or not held_reviews:
        raise ValueError("held_reviews must be the non-empty normalised review mapping")
    listed = DELIVERABLES[name][0]
    if listed in held_reviews:
        return (listed, False)
    limit = review_index(listed)
    candidates = [r for r in held_reviews if review_index(r) < limit]
    if not candidates:
        return (None, True)
    return (max(candidates, key=review_index), True)


def due_day(review_day, lead_working_days=DEFAULT_LEAD_WORKING_DAYS):
    """Return the submission due day for a review held on review_day."""
    return subtract_working_days(review_day, lead_working_days)


def grade_deliverable(deliverable, held_reviews, planned,
                      lead_working_days=DEFAULT_LEAD_WORKING_DAYS):
    """Grade one Annex E deliverable against the project review schedule."""
    name = normalise_identifier(deliverable, "deliverable")
    if name not in DELIVERABLES:
        raise ValueError("%r is not an Annex E deliverable" % name)
    listed, expected = DELIVERABLES[name]
    anchor, moved = anchor_review(name, held_reviews)
    record = {
        "deliverable": name,
        "listed_review": listed,
        "anchor_review": anchor,
        "reanchored": moved,
        "expected_of_every_project": expected,
        "due_day": None,
        "planned_day": planned.get(name),
        "slack_days": None,
        "status": None,
    }
    if anchor is None:
        record["status"] = "no-anchor-review"
        return record
    record["due_day"] = due_day(held_reviews[anchor], lead_working_days)
    if record["planned_day"] is None:
        record["status"] = "not-planned"
        return record
    record["slack_days"] = (record["due_day"] - record["planned_day"]).days
    record["status"] = "on-time" if record["slack_days"] >= 0 else "late"
    return record


def assess_review_deliverables(spec):
    """Schedule the Annex E deliverables against a project's review milestones.

    spec keys: reviews (held milestones with days), submissions (planned days),
    optional lead_working_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "reviews" not in spec:
        raise ValueError("spec missing required key 'reviews'")
    held = validate_reviews(spec["reviews"])
    planned = validate_submissions(spec.get("submissions"))
    lead = spec.get("lead_working_days", DEFAULT_LEAD_WORKING_DAYS)
    if not isinstance(lead, int) or isinstance(lead, bool) or lead < 0:
        raise ValueError("lead_working_days must be a non-negative integer, got %r" % (lead,))
    records = [grade_deliverable(name, held, planned, lead) for name in sorted(DELIVERABLES)]
    findings = []
    for record in records:
        severity = "blocking" if record["expected_of_every_project"] else "advisory"
        if record["status"] == "no-anchor-review":
            findings.append({
                "code": "deliverable-has-no-anchor-review",
                "severity": "blocking",
                "deliverable": record["deliverable"],
                "message": "%s is listed against %s and the project holds no earlier review"
                           % (record["deliverable"], record["listed_review"]),
            })
            continue
        if record["reanchored"]:
            findings.append({
                "code": "deliverable-reanchored",
                "severity": "advisory",
                "deliverable": record["deliverable"],
                "message": "%s moves from %s to %s, which this project holds"
                           % (record["deliverable"], record["listed_review"],
                              record["anchor_review"]),
            })
        if record["status"] == "not-planned":
            findings.append({
                "code": "deliverable-not-planned",
                "severity": severity,
                "deliverable": record["deliverable"],
                "message": "%s has no planned submission and is due %s"
                           % (record["deliverable"], record["due_day"].isoformat()),
            })
        elif record["status"] == "late":
            findings.append({
                "code": "deliverable-planned-late",
                "severity": severity,
                "deliverable": record["deliverable"],
                "message": "%s is planned %d day(s) after its due day %s"
                           % (record["deliverable"], -record["slack_days"],
                              record["due_day"].isoformat()),
            })
    scheduled = [r for r in records if r["due_day"] is not None]
    scheduled.sort(key=lambda r: (r["due_day"], r["deliverable"]))
    on_time = sum(1 for r in records if r["status"] == "on-time")
    blocking = [f for f in findings if f["severity"] == "blocking"]
    return {
        "records": {r["deliverable"]: r for r in records},
        "schedule": scheduled,
        "lead_working_days": lead,
        "on_time_fraction": on_time / float(len(records)),
        "findings": findings,
        "blocking_findings": blocking,
        "decision": "schedule-rejected" if blocking else "schedule-accepted",
    }
