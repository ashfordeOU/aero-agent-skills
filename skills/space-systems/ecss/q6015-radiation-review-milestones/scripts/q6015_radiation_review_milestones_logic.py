"""Radiation analysis reporting against the project milestone reviews.

Anchor: ECSS-Q-ST-60-15C clause 4.5 (how the radiation analysis reporting
feeds each milestone review, with the depth and the timing set by the
equipment category). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Read the reporting depth a review demands from the equipment category and
   the review itself, both taken from closed sets.
2. Turn that depth into a submission deadline by counting working days back
   from the review date, so a deeper report buys the review board more
   reading time.
3. Grade each submission on three separate questions: was it delivered, was
   it deep enough, and was it delivered by its own deadline.
4. Return one reporting verdict per project with the findings that produced
   it.
"""

import datetime

__all__ = [
    "REVIEW_SEQUENCE",
    "DEPTH_SEQUENCE",
    "EQUIPMENT_CATEGORIES",
    "DEPTH_MATRIX",
    "LEAD_TIME_WORKING_DAYS",
    "normalize_review",
    "review_index",
    "normalize_depth",
    "depth_rank",
    "normalize_category",
    "required_depth",
    "required_lead_days",
    "as_date",
    "working_days_before",
    "submission_deadline",
    "grade_submission",
    "assess_review_reporting",
]

REVIEW_SEQUENCE = (
    "system-requirements-review",
    "preliminary-design-review",
    "critical-design-review",
    "qualification-review",
    "acceptance-review",
)

# Reporting depths, shallowest first. A deeper report satisfies a shallower
# demand; the reverse never holds.
DEPTH_SEQUENCE = (
    "summary",
    "assessment",
    "detailed-analysis",
    "full-verification-dossier",
)

EQUIPMENT_CATEGORIES = ("category-1", "category-2", "category-3")

# What each equipment category owes at each review. A category-1 equipment
# carries a radiation-critical function and its reporting deepens earliest.
DEPTH_MATRIX = {
    "category-1": {
        "system-requirements-review": "summary",
        "preliminary-design-review": "assessment",
        "critical-design-review": "detailed-analysis",
        "qualification-review": "full-verification-dossier",
        "acceptance-review": "full-verification-dossier",
    },
    "category-2": {
        "system-requirements-review": "summary",
        "preliminary-design-review": "summary",
        "critical-design-review": "assessment",
        "qualification-review": "detailed-analysis",
        "acceptance-review": "detailed-analysis",
    },
    "category-3": {
        "system-requirements-review": "summary",
        "preliminary-design-review": "summary",
        "critical-design-review": "summary",
        "qualification-review": "assessment",
        "acceptance-review": "assessment",
    },
}

# Working days the board is owed before the review, by depth of the report.
LEAD_TIME_WORKING_DAYS = {
    "summary": 5,
    "assessment": 10,
    "detailed-analysis": 20,
    "full-verification-dossier": 30,
}

SATURDAY = 5


def _slug(label, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in key:
        key = key.replace("--", "-")
    key = key.strip("-")
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_review(value):
    """Return the canonical milestone review token."""
    key = _slug("review", value)
    if key not in REVIEW_SEQUENCE:
        raise ValueError(
            "unknown review %r; expected one of %s" % (value, ", ".join(REVIEW_SEQUENCE))
        )
    return key


def review_index(value):
    """Return the position of a review in the project sequence."""
    return REVIEW_SEQUENCE.index(normalize_review(value))


def normalize_depth(value):
    """Return the canonical reporting depth token."""
    key = _slug("reporting depth", value)
    if key not in DEPTH_SEQUENCE:
        raise ValueError(
            "unknown reporting depth %r; expected one of %s"
            % (value, ", ".join(DEPTH_SEQUENCE))
        )
    return key


def depth_rank(value):
    """Return the ordinal rank of a reporting depth, shallowest first."""
    return DEPTH_SEQUENCE.index(normalize_depth(value))


def normalize_category(value):
    """Return the canonical equipment category token."""
    key = _slug("equipment category", value)
    if key not in DEPTH_MATRIX:
        raise ValueError(
            "unknown equipment category %r; expected one of %s"
            % (value, ", ".join(EQUIPMENT_CATEGORIES))
        )
    return key


def required_depth(category, review):
    """Return the reporting depth an equipment category owes at a review."""
    return DEPTH_MATRIX[normalize_category(category)][normalize_review(review)]


def required_lead_days(depth):
    """Return the working days of reading time a reporting depth owes."""
    return LEAD_TIME_WORKING_DAYS[normalize_depth(depth)]


def as_date(value):
    """Return a date from an ISO string or a date object."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("date must not be empty")
        try:
            return datetime.date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("date %r is not an ISO calendar date" % (value,)) from exc
    raise ValueError("date must be an ISO string or a date, got %r" % (value,))


def working_days_before(reference, days):
    """Step back a whole number of working days from a reference date."""
    date = as_date(reference)
    if not isinstance(days, int) or isinstance(days, bool):
        raise ValueError("days must be an integer, got %r" % (days,))
    if days < 0:
        raise ValueError("days must not be negative, got %d" % days)
    remaining = days
    while remaining > 0:
        date = date - datetime.timedelta(days=1)
        if date.weekday() < SATURDAY:
            remaining -= 1
    return date


def submission_deadline(review_date, category, review):
    """Return the latest working day a report may be submitted on."""
    depth = required_depth(category, review)
    return working_days_before(review_date, required_lead_days(depth))


def grade_submission(submission, category, review_date):
    """Grade one report submission against its review."""
    if not isinstance(submission, dict):
        raise ValueError("submission must be a mapping")
    review = normalize_review(submission.get("review"))
    demanded = required_depth(category, review)
    deadline = submission_deadline(review_date, category, review)
    record = {
        "review": review,
        "required_depth": demanded,
        "deadline": deadline,
        "submitted_depth": None,
        "submitted_date": None,
        "delivered": False,
        "deep_enough": False,
        "on_time": False,
        "findings": [],
    }
    depth_value = submission.get("submitted_depth")
    date_value = submission.get("submitted_date")
    if depth_value is None and date_value is None:
        record["findings"].append(
            "%s: the %s report was never submitted" % (review, demanded)
        )
        return record
    if depth_value is None or date_value is None:
        raise ValueError(
            "submission for %s needs both a submitted depth and a submitted date" % review
        )
    submitted_depth = normalize_depth(depth_value)
    submitted_date = as_date(date_value)
    record["submitted_depth"] = submitted_depth
    record["submitted_date"] = submitted_date
    record["delivered"] = True
    record["deep_enough"] = depth_rank(submitted_depth) >= depth_rank(demanded)
    record["on_time"] = submitted_date <= deadline
    if not record["deep_enough"]:
        record["findings"].append(
            "%s: report submitted at %s depth where %s is owed"
            % (review, submitted_depth, demanded)
        )
    if not record["on_time"]:
        record["findings"].append(
            "%s: report submitted on %s, after the %s deadline"
            % (review, submitted_date.isoformat(), deadline.isoformat())
        )
    return record


def assess_review_reporting(spec):
    """Run the clause 4.5 reporting assessment for one equipment.

    spec keys: category, reviews (sequence of records carrying review,
    review_date and, when delivered, submitted_depth and submitted_date).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "reviews"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    category = normalize_category(spec["category"])
    reviews = spec["reviews"]
    if not isinstance(reviews, (list, tuple)) or not reviews:
        raise ValueError("reviews must be a non-empty sequence")
    graded = []
    seen = set()
    for entry in reviews:
        if not isinstance(entry, dict):
            raise ValueError("each review entry must be a mapping")
        if "review_date" not in entry:
            raise ValueError("review entry missing 'review_date'")
        record = grade_submission(entry, category, entry["review_date"])
        record["review_date"] = as_date(entry["review_date"])
        if record["review"] in seen:
            raise ValueError("duplicate review entry for %s" % record["review"])
        seen.add(record["review"])
        graded.append(record)
    graded.sort(key=lambda item: REVIEW_SEQUENCE.index(item["review"]))
    findings = []
    for record in graded:
        findings.extend(record["findings"])
    return {
        "category": category,
        "reviews": graded,
        "reviews_covered": sorted(seen, key=REVIEW_SEQUENCE.index),
        "findings": findings,
        "reporting_compliant": not findings,
    }
