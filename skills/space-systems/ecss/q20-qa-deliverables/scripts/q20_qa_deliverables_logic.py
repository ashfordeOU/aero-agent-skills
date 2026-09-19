"""Quality assurance deliverable documents per project review.

Anchor: ECSS-Q-ST-20C Annex I (informative), the table mapping each quality
assurance deliverable document to the project reviews at which it is owed.
The mapping is used here as the delivery schedule of a project: which QA
document is owed at which review, at what maturity, how long before the
review it has to be in the customer's hands, and where the first blocking
review sits. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Hold the review sequence and the deliverable mapping: for each document
   the review it is first owed at, the review by which it is approved,
   whether it is reissued at every review in that window, and its lead time.
2. Resolve the deliverables a given review owes for the scope the project
   actually declared, so a project with no software does not owe a software
   product assurance plan.
3. Grade one review's submitted set: missing, below the maturity owed, late
   against the lead time, or not on the schedule at all.
4. Score the review readiness as the satisfied fraction of what it owed.
5. Walk the whole sequence and report the first review that does not clear
   the readiness threshold.
"""

import math

__all__ = [
    "REVIEW_SEQUENCE",
    "REVIEW_ALIASES",
    "MATURITY_LADDER",
    "SCOPE_FLAGS",
    "DELIVERABLES",
    "READINESS_TOLERANCE",
    "normalise_identifier",
    "normalise_review",
    "review_index",
    "maturity_rank",
    "normalise_scope",
    "deliverable_entry",
    "owed_at_review",
    "required_maturity",
    "deliverables_for_review",
    "delivery_schedule",
    "parse_day",
    "day_difference",
    "evaluate_review",
    "review_readiness",
    "clears_threshold",
    "first_blocking_review",
]

# Project reviews in the order the mapping walks them.
REVIEW_SEQUENCE = ("prr", "srr", "pdr", "cdr", "qr", "ar", "orr")

REVIEW_ALIASES = {
    "preliminary-requirements-review": "prr",
    "system-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
    "operational-readiness-review": "orr",
}

# A delivery may exceed the maturity owed, never fall below it.
MATURITY_LADDER = ("draft", "issued", "approved")

# Scope switches that turn parts of the mapping on.
SCOPE_FLAGS = ("software", "procured-items", "ground-support-equipment")

# document -> first review owed, review by which approved, reissued at every
# review in the window, lead time in days, scope flag gating it.
DELIVERABLES = {
    "quality-assurance-plan": ("prr", "pdr", False, 30, None),
    "product-assurance-requirements-matrix": ("srr", "pdr", False, 21, None),
    "audit-plan-and-schedule": ("srr", "cdr", False, 21, None),
    "critical-item-list": ("pdr", "cdr", True, 21, None),
    "nonconformance-status-list": ("pdr", "ar", True, 14, None),
    "deviation-and-waiver-list": ("cdr", "ar", True, 14, None),
    "qualification-status-list": ("cdr", "qr", True, 21, None),
    "as-built-configuration-list": ("qr", "ar", False, 14, None),
    "acceptance-test-report-list": ("qr", "ar", False, 14, None),
    "end-item-data-package": ("ar", "ar", False, 14, None),
    "handover-and-open-work-list": ("ar", "orr", True, 7, None),
    "software-product-assurance-plan": ("srr", "pdr", False, 30, "software"),
    "software-problem-report-list": ("cdr", "ar", True, 14, "software"),
    "supplier-control-status-list": ("pdr", "cdr", True, 21, "procured-items"),
    "procured-item-inspection-record-list": ("cdr", "ar", True, 14, "procured-items"),
    "ground-support-equipment-status-list": ("pdr", "ar", True, 14,
                                             "ground-support-equipment"),
}

# Readiness is a ratio of small integers; an exact threshold hit is a pass.
READINESS_TOLERANCE = 1e-12

_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def normalise_review(review):
    """Return the short name of a project review."""
    key = normalise_identifier(review, "review")
    key = REVIEW_ALIASES.get(key, key)
    if key not in REVIEW_SEQUENCE:
        raise ValueError(
            "review must be one of %s, got %r" % ("/".join(REVIEW_SEQUENCE), review)
        )
    return key


def review_index(review):
    """Return the position of a review in the sequence."""
    return REVIEW_SEQUENCE.index(normalise_review(review))


def maturity_rank(maturity):
    """Return the rung a document maturity sits on."""
    key = normalise_identifier(maturity, "maturity")
    if key not in MATURITY_LADDER:
        raise ValueError(
            "maturity must be one of %s, got %r" % ("/".join(MATURITY_LADDER), maturity)
        )
    return MATURITY_LADDER.index(key)


def normalise_scope(scope):
    """Return the declared scope flags as a sorted tuple."""
    if scope is None:
        return ()
    if not isinstance(scope, (list, tuple, set, frozenset)):
        raise ValueError("scope must be a sequence of scope flags")
    flags = set()
    for item in scope:
        key = normalise_identifier(item, "scope flag")
        if key not in SCOPE_FLAGS:
            raise ValueError(
                "scope flag must be one of %s, got %r" % ("/".join(SCOPE_FLAGS), item)
            )
        flags.add(key)
    return tuple(sorted(flags))


def deliverable_entry(document):
    """Return the mapping row of one deliverable document."""
    key = normalise_identifier(document, "document")
    if key not in DELIVERABLES:
        raise ValueError("document %r is not on the deliverable mapping" % document)
    first, approved, recurring, lead_days, flag = DELIVERABLES[key]
    return {
        "document": key,
        "first_review": first,
        "approved_by_review": approved,
        "recurring": recurring,
        "lead_days": lead_days,
        "scope_flag": flag,
    }


def owed_at_review(document, review):
    """Return whether a document is owed at a given review."""
    entry = deliverable_entry(document)
    position = review_index(review)
    first = review_index(entry["first_review"])
    last = review_index(entry["approved_by_review"])
    if position < first:
        return False
    if entry["recurring"]:
        return position <= last
    return position in (first, last)


def required_maturity(document, review):
    """Return the maturity a document owes at a review."""
    entry = deliverable_entry(document)
    if not owed_at_review(document, review):
        raise ValueError(
            "%s is not owed at %s" % (entry["document"], normalise_review(review))
        )
    position = review_index(review)
    if position >= review_index(entry["approved_by_review"]):
        return "approved"
    if position > review_index(entry["first_review"]):
        return "issued"
    return "draft" if entry["first_review"] != entry["approved_by_review"] else "approved"


def deliverables_for_review(review, scope=None):
    """Return the documents a review owes, with their maturity and lead time."""
    key = normalise_review(review)
    flags = set(normalise_scope(scope))
    owed = []
    for document in sorted(DELIVERABLES):
        entry = deliverable_entry(document)
        if entry["scope_flag"] is not None and entry["scope_flag"] not in flags:
            continue
        if not owed_at_review(document, key):
            continue
        owed.append({
            "document": document,
            "review": key,
            "maturity": required_maturity(document, key),
            "lead_days": entry["lead_days"],
        })
    return owed


def delivery_schedule(scope=None):
    """Return the whole sequence as review -> owed deliverables."""
    return {
        review: deliverables_for_review(review, scope) for review in REVIEW_SEQUENCE
    }


def _days_in_month(year, month):
    """Return the length of a month, leap years included."""
    if month != 2:
        return _MONTH_LENGTHS[month - 1]
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    return 29 if leap else 28


def parse_day(value, label):
    """Return an ISO calendar day as a (year, month, day) triple."""
    text = normalise_identifier(value, label)
    parts = text.split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("%s must be an ISO day, got %r" % (label, value))
    if (len(parts[0]), len(parts[1]), len(parts[2])) != (4, 2, 2):
        raise ValueError("%s must be an ISO day, got %r" % (label, value))
    year, month, day = (int(part) for part in parts)
    if not 1 <= month <= 12:
        raise ValueError("%s has month %d" % (label, month))
    if not 1 <= day <= _days_in_month(year, month):
        raise ValueError("%s has day %d in month %d" % (label, day, month))
    return (year, month, day)


def _ordinal(day):
    """Return a day count from a fixed epoch for a (year, month, day) triple."""
    year, month, dom = day
    total = 0
    for y in range(1, year):
        total += 366 if ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0) else 365
    for m in range(1, month):
        total += _days_in_month(year, m)
    return total + dom


def day_difference(later, earlier):
    """Return how many days separate two ISO days, later minus earlier."""
    return _ordinal(parse_day(later, "later")) - _ordinal(parse_day(earlier, "earlier"))


def evaluate_review(review, submissions, scope=None, review_date=None):
    """Grade one review's submitted deliverable set."""
    key = normalise_review(review)
    owed = {item["document"]: item for item in deliverables_for_review(key, scope)}
    if not isinstance(submissions, (list, tuple)):
        raise ValueError("submissions must be a sequence")
    seen = {}
    unplanned = []
    for index, item in enumerate(submissions):
        if not isinstance(item, dict):
            raise ValueError("submissions[%d] must be a mapping" % index)
        for field in ("document", "maturity"):
            if field not in item:
                raise ValueError("submissions[%d] is missing '%s'" % (index, field))
        document = normalise_identifier(item["document"], "submissions[%d].document"
                                        % index)
        if document in seen:
            raise ValueError("document %r is submitted twice" % document)
        record = {
            "document": document,
            "maturity": normalise_identifier(item["maturity"],
                                             "submissions[%d].maturity" % index),
            "submitted_on": item.get("submitted_on"),
        }
        maturity_rank(record["maturity"])
        seen[document] = record
        if document not in owed:
            unplanned.append(document)
    missing = sorted(document for document in owed if document not in seen)
    immature = []
    late = []
    satisfied = 0
    for document, expectation in sorted(owed.items()):
        record = seen.get(document)
        if record is None:
            continue
        if maturity_rank(record["maturity"]) < maturity_rank(expectation["maturity"]):
            immature.append(
                "%s is %s at %s and owes %s"
                % (document, record["maturity"], key, expectation["maturity"])
            )
            continue
        if review_date is not None and record["submitted_on"] is not None:
            lead = day_difference(review_date, record["submitted_on"])
            if lead < expectation["lead_days"]:
                late.append(
                    "%s reached the review %d days ahead and owes %d"
                    % (document, lead, expectation["lead_days"])
                )
                continue
        satisfied += 1
    findings = []
    if missing:
        findings.append("deliverables not submitted at %s: %s"
                        % (key, ", ".join(missing)))
    findings.extend(immature)
    findings.extend(late)
    return {
        "review": key,
        "owed_count": len(owed),
        "satisfied_count": satisfied,
        "missing": missing,
        "immature": immature,
        "late": late,
        "unplanned": sorted(unplanned),
        "findings": findings,
    }


def review_readiness(result):
    """Return the satisfied fraction of what a review owed."""
    if not isinstance(result, dict):
        raise ValueError("result must be the mapping returned by evaluate_review")
    for key in ("owed_count", "satisfied_count"):
        if key not in result:
            raise ValueError("result is missing '%s'" % key)
    if result["owed_count"] <= 0:
        raise ValueError("owed_count must be positive to score a review")
    return result["satisfied_count"] / float(result["owed_count"])


def clears_threshold(readiness, threshold):
    """Return whether a readiness score clears a threshold."""
    for label, value in (("readiness", readiness), ("threshold", threshold)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("%s must lie between zero and one" % label)
    return float(readiness) > float(threshold) or math.isclose(
        float(readiness), float(threshold), rel_tol=0.0, abs_tol=READINESS_TOLERANCE
    )


def first_blocking_review(submitted_by_review, scope=None, threshold=1.0,
                          review_dates=None):
    """Return the first review in the sequence that does not clear the threshold."""
    if not isinstance(submitted_by_review, dict):
        raise ValueError("submitted_by_review must be a mapping of review to set")
    dates = review_dates or {}
    if not isinstance(dates, dict):
        raise ValueError("review_dates must be a mapping of review to ISO day")
    rollup = []
    blocking = None
    for review in REVIEW_SEQUENCE:
        owed = deliverables_for_review(review, scope)
        if not owed:
            continue
        submissions = submitted_by_review.get(review, [])
        result = evaluate_review(review, submissions, scope, dates.get(review))
        readiness = review_readiness(result)
        cleared = clears_threshold(readiness, threshold)
        rollup.append({
            "review": review,
            "readiness": readiness,
            "cleared": cleared,
            "findings": result["findings"],
        })
        if blocking is None and not cleared:
            blocking = review
    return {"rollup": rollup, "first_blocking_review": blocking}
