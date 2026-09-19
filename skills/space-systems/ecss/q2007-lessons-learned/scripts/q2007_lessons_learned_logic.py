"""Lessons-learned review after a test campaign at a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.8.3 (lessons learned from test activities).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each register entry: the event it came from, the category it sits
   in, the recommendation it carries, its owner, its target day and status,
   and the three ordinal judgements that rank it.
2. Rank the entry by the product of recurrence, consequence and detectability
   and place it in a priority band; the band drives what the review owes.
3. Route the entry to the process or document that has to absorb it, which
   is a property of the category and not of the person who raised it.
4. Grade the register at a review day: closure fraction, overdue entries,
   and the capture ratio of entries against the anomalies of the campaign.
5. Conclude: the review is complete only when every high-band entry is owned,
   dated and routed, no high-band entry is silently overdue, and the capture
   ratio reaches the required value.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "CATEGORIES",
    "FEEDBACK_ROUTE",
    "ORDINAL_MIN",
    "ORDINAL_MAX",
    "HIGH_BAND_MIN",
    "MEDIUM_BAND_MIN",
    "STATUSES",
    "priority_index",
    "priority_band",
    "feedback_route",
    "validate_lesson",
    "overdue_days",
    "assess_lesson",
    "capture_ratio",
    "register_metrics",
    "assess_lessons_review",
]

# Closure and capture fractions are quotients; a value meant to sit exactly on
# its requirement can land a few ULP either side.
FRACTION_TOLERANCE = 1e-9

CATEGORIES = (
    "procedure",
    "facility",
    "instrumentation",
    "training",
    "interface",
    "planning",
)

# Where a lesson has to land to change anything. A lesson with no route is a
# note; a lesson with a route is a change to a controlled item.
FEEDBACK_ROUTE = {
    "procedure": "test procedure and test specification revision",
    "facility": "facility maintenance and configuration baseline",
    "instrumentation": "measurement chain and calibration plan",
    "training": "operator qualification and training syllabus",
    "interface": "test request and customer interface agreement",
    "planning": "test programme schedule and resource plan",
}

ORDINAL_MIN = 1
ORDINAL_MAX = 5

# Bands on the product of three 1..5 ordinals, so the bounds are exact integers.
HIGH_BAND_MIN = 60
MEDIUM_BAND_MIN = 24

STATUSES = ("open", "in-work", "closed")


def _ordinal(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < ORDINAL_MIN or value > ORDINAL_MAX:
        raise ValueError(
            "%s must lie in [%d, %d], got %d" % (label, ORDINAL_MIN, ORDINAL_MAX, value)
        )
    return value


def priority_index(recurrence, consequence, detectability):
    """Return the integer priority index of a lesson from its three ordinals."""
    r = _ordinal("recurrence", recurrence)
    c = _ordinal("consequence", consequence)
    d = _ordinal("detectability", detectability)
    return r * c * d


def priority_band(index):
    """Return 'high', 'medium' or 'low' for a priority index."""
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("priority index must be an integer, got %r" % (index,))
    if index < ORDINAL_MIN or index > ORDINAL_MAX ** 3:
        raise ValueError(
            "priority index must lie in [%d, %d], got %d"
            % (ORDINAL_MIN, ORDINAL_MAX ** 3, index)
        )
    if index >= HIGH_BAND_MIN:
        return "high"
    if index >= MEDIUM_BAND_MIN:
        return "medium"
    return "low"


def feedback_route(category):
    """Return the controlled item a lesson of this category has to feed back into."""
    if category not in FEEDBACK_ROUTE:
        raise ValueError(
            "unknown lesson category %r; expected one of %s"
            % (category, ", ".join(CATEGORIES))
        )
    return FEEDBACK_ROUTE[category]


def validate_lesson(lesson):
    """Return a normalised register entry, raising on anything unusable."""
    if not isinstance(lesson, dict):
        raise ValueError("lesson must be a mapping")
    for key in (
        "id",
        "source_event",
        "category",
        "recommendation",
        "recurrence",
        "consequence",
        "detectability",
    ):
        if key not in lesson:
            raise ValueError("lesson missing required key '%s'" % key)
    for key in ("id", "source_event", "recommendation"):
        value = lesson[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("lesson '%s' must be a non-empty string" % key)
    category = lesson["category"]
    if category not in FEEDBACK_ROUTE:
        raise ValueError("unknown lesson category %r" % (category,))
    status = lesson.get("status", "open")
    if status not in STATUSES:
        raise ValueError(
            "unknown status %r; expected one of %s" % (status, ", ".join(STATUSES))
        )
    owner = lesson.get("owner")
    if owner is not None and (not isinstance(owner, str) or not owner.strip()):
        raise ValueError("lesson owner must be a non-empty string when given")
    target_day = lesson.get("target_day")
    if target_day is not None:
        if not isinstance(target_day, int) or isinstance(target_day, bool):
            raise ValueError("target_day must be an integer day number")
        if target_day < 0:
            raise ValueError("target_day must not be negative, got %d" % target_day)
    index = priority_index(
        lesson["recurrence"], lesson["consequence"], lesson["detectability"]
    )
    return {
        "id": lesson["id"],
        "source_event": lesson["source_event"],
        "category": category,
        "recommendation": lesson["recommendation"],
        "owner": owner,
        "target_day": target_day,
        "status": status,
        "priority_index": index,
        "priority_band": priority_band(index),
        "route": feedback_route(category),
    }


def overdue_days(target_day, review_day):
    """Return the days a target is past, or zero when it is not past."""
    for label, value in (("target_day", target_day), ("review_day", review_day)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer day number" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    return max(0, review_day - target_day)


def assess_lesson(lesson, review_day):
    """Assess one register entry at a review day."""
    record = validate_lesson(lesson)
    if not isinstance(review_day, int) or isinstance(review_day, bool):
        raise ValueError("review_day must be an integer day number")
    if review_day < 0:
        raise ValueError("review_day must not be negative")
    findings = []
    high = record["priority_band"] == "high"
    if record["status"] != "closed":
        if record["owner"] is None:
            findings.append("%s has no owner" % record["id"])
        if record["target_day"] is None:
            findings.append("%s has no target day" % record["id"])
    late = 0
    if record["status"] != "closed" and record["target_day"] is not None:
        late = overdue_days(record["target_day"], review_day)
        if late > 0:
            findings.append(
                "%s is %d day(s) past its target and still %s"
                % (record["id"], late, record["status"])
            )
    if high and record["status"] == "open" and record["owner"] is None:
        findings.append(
            "%s is a high-band lesson left unowned; the review cannot be complete"
            % record["id"]
        )
    record["overdue_days"] = late
    record["findings"] = findings
    record["actionable"] = not findings
    return record


def capture_ratio(lesson_count, anomaly_count):
    """Return the entries captured per anomaly of the campaign."""
    for label, value in (
        ("lesson_count", lesson_count),
        ("anomaly_count", anomaly_count),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if anomaly_count == 0:
        raise ValueError(
            "a capture ratio is undefined with no anomalies; report the count instead"
        )
    return float(lesson_count) / float(anomaly_count)


def register_metrics(records):
    """Return the closure and band metrics of the assessed register."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    total = len(records)
    if total == 0:
        return {
            "total": 0,
            "closed": 0,
            "closed_fraction": 0.0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "overdue": 0,
        }
    closed = sum(1 for r in records if r["status"] == "closed")
    bands = {"high": 0, "medium": 0, "low": 0}
    for record in records:
        bands[record["priority_band"]] += 1
    return {
        "total": total,
        "closed": closed,
        "closed_fraction": float(closed) / float(total),
        "high": bands["high"],
        "medium": bands["medium"],
        "low": bands["low"],
        "overdue": sum(1 for r in records if r.get("overdue_days", 0) > 0),
    }


def assess_lessons_review(spec):
    """Run the full clause 5.8.3 lessons-learned review assessment.

    spec keys: lessons, review_day, anomaly_count, optional
    required_capture_ratio (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lessons", "review_day", "anomaly_count"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lessons = spec["lessons"]
    if not isinstance(lessons, (list, tuple)):
        raise ValueError("spec['lessons'] must be a sequence")
    required = spec.get("required_capture_ratio", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_capture_ratio must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0:
        raise ValueError("required_capture_ratio must be non-negative and finite")
    records = [assess_lesson(item, spec["review_day"]) for item in lessons]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicate lesson id %r" % record["id"])
        seen.add(record["id"])
    metrics = register_metrics(records)
    ratio = capture_ratio(len(records), spec["anomaly_count"])
    findings = []
    for record in records:
        findings.extend(record["findings"])
    captured = ratio > required or math.isclose(
        ratio, required, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    if not captured:
        findings.append(
            "the campaign captured %.4f entries per anomaly, below the required %.4f"
            % (ratio, required)
        )
    routes = sorted({r["route"] for r in records})
    return {
        "records": records,
        "metrics": metrics,
        "capture_ratio": ratio,
        "required_capture_ratio": required,
        "routes": routes,
        "findings": findings,
        "review_complete": not findings,
    }
