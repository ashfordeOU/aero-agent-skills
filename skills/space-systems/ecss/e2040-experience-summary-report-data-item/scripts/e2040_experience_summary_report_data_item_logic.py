"""Required contents of the device experience summary report.

Anchor: ECSS-E-ST-20-40C Annex I (experience summary report data item -- the
closing record of the lessons the device development effort produced).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents.
2. Validate the anomaly history (identifier, severity index, phase) and the
   lesson records (identifier, the three priority indices, and the four
   narrative parts: observation, cause, recommendation, owner).
3. Resolve each lesson's anomaly links against the history.
4. Compute the severity-weighted traceability of the anomaly history into the
   lessons, and list the anomalies no lesson captures.
5. Form the occurrence-by-impact-by-detection priority index of each lesson
   and rank the lessons by descending index with the identifier as the
   tie-break, so the order is stable across runs.
6. Report the traceability against the required level together with the
   incomplete lessons and the uncaptured anomalies.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "NARRATIVE_PARTS",
    "SCALE_MIN",
    "SCALE_MAX",
    "TRACEABILITY_TOLERANCE",
    "missing_sections",
    "validate_index",
    "validate_anomaly",
    "validate_anomalies",
    "validate_lesson",
    "validate_lessons",
    "lesson_gaps",
    "priority_index",
    "rank_lessons",
    "captured_anomaly_ids",
    "uncaptured_anomalies",
    "severity_weighted_traceability",
    "assess_experience_report",
]

REQUIRED_SECTIONS = (
    "scope",
    "development-summary",
    "anomaly-history",
    "lessons-learned",
    "recommendations",
    "residual-actions",
)

# The four parts a lesson record needs before it is actionable.
NARRATIVE_PARTS = ("observation", "cause", "recommendation", "owner")

SCALE_MIN = 1
SCALE_MAX = 5

# Traceability is a ratio of sums; an exact equality can land a few ULPs on
# the wrong side of the required level.
TRACEABILITY_TOLERANCE = 1e-12


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _optional_text(value, label):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("%s must be a string or None, got %r" % (label, value))
    out = value.strip()
    return out or None


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_index(value, label):
    """Return a whole ordinal index inside the recognized scale."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole index, got %r" % (label, value))
    if value < SCALE_MIN or value > SCALE_MAX:
        raise ValueError(
            "%s must lie in [%d, %d], got %d" % (label, SCALE_MIN, SCALE_MAX, value)
        )
    return value


def validate_anomaly(anomaly):
    """Return a normalized anomaly-history entry."""
    if not isinstance(anomaly, dict):
        raise ValueError("anomaly must be a mapping")
    for key in ("id", "severity", "phase"):
        if key not in anomaly:
            raise ValueError("anomaly missing required key '%s'" % key)
    identifier = _identifier(anomaly["id"], "anomaly id")
    severity = validate_index(anomaly["severity"], "severity of %s" % identifier)
    phase = _identifier(anomaly["phase"], "phase of %s" % identifier)
    return {"id": identifier, "severity": severity, "phase": phase}


def validate_anomalies(anomalies):
    """Return the normalized anomaly history, rejecting duplicate identifiers."""
    if not isinstance(anomalies, (list, tuple)) or not anomalies:
        raise ValueError("anomalies must be a non-empty sequence")
    records = []
    seen = set()
    for item in anomalies:
        record = validate_anomaly(item)
        if record["id"] in seen:
            raise ValueError("duplicate anomaly identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def validate_lesson(lesson, known_anomaly_ids):
    """Return a normalized lesson record with its resolved anomaly links."""
    if not isinstance(lesson, dict):
        raise ValueError("lesson must be a mapping")
    for key in ("id", "occurrence", "impact", "detection_difficulty"):
        if key not in lesson:
            raise ValueError("lesson missing required key '%s'" % key)
    identifier = _identifier(lesson["id"], "lesson id")
    occurrence = validate_index(lesson["occurrence"], "occurrence of %s" % identifier)
    impact = validate_index(lesson["impact"], "impact of %s" % identifier)
    detection = validate_index(
        lesson["detection_difficulty"], "detection_difficulty of %s" % identifier
    )
    record = {
        "id": identifier,
        "occurrence": occurrence,
        "impact": impact,
        "detection_difficulty": detection,
    }
    for part in NARRATIVE_PARTS:
        record[part] = _optional_text(lesson.get(part), "%s of %s" % (part, identifier))
    links = lesson.get("anomaly_ids", [])
    if not isinstance(links, (list, tuple)):
        raise ValueError("anomaly_ids of %s must be a sequence" % identifier)
    resolved = []
    for i, ref in enumerate(links):
        ref_id = _identifier(ref, "%s anomaly_ids[%d]" % (identifier, i))
        if ref_id not in known_anomaly_ids:
            raise ValueError(
                "lesson %s links anomaly %r, which the history does not carry"
                % (identifier, ref_id)
            )
        if ref_id not in resolved:
            resolved.append(ref_id)
    record["anomaly_ids"] = resolved
    return record


def validate_lessons(lessons, known_anomaly_ids):
    """Return the normalized lesson set, rejecting duplicate identifiers."""
    if not isinstance(lessons, (list, tuple)) or not lessons:
        raise ValueError("lessons must be a non-empty sequence")
    records = []
    seen = set()
    for item in lessons:
        record = validate_lesson(item, known_anomaly_ids)
        if record["id"] in seen:
            raise ValueError("duplicate lesson identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def lesson_gaps(lesson):
    """Return the narrative parts a lesson record is missing, in order."""
    return [part for part in NARRATIVE_PARTS if not lesson.get(part)]


def priority_index(lesson):
    """Return the occurrence-by-impact-by-detection priority index of a lesson."""
    for key in ("occurrence", "impact", "detection_difficulty"):
        if key not in lesson:
            raise ValueError("lesson missing required key '%s'" % key)
        validate_index(lesson[key], key)
    return lesson["occurrence"] * lesson["impact"] * lesson["detection_difficulty"]


def rank_lessons(lessons):
    """Return the lesson identifiers by descending priority, ties broken by id."""
    if not isinstance(lessons, (list, tuple)) or not lessons:
        raise ValueError("lessons must be a non-empty sequence")
    scored = [(priority_index(lesson), lesson["id"]) for lesson in lessons]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [identifier for _, identifier in scored]


def captured_anomaly_ids(lessons):
    """Return the set of anomaly identifiers any lesson captures."""
    captured = set()
    for lesson in lessons:
        for ref in lesson.get("anomaly_ids", []):
            captured.add(ref)
    return captured


def uncaptured_anomalies(anomalies, lessons):
    """Return the anomalies no lesson captures, in history order."""
    captured = captured_anomaly_ids(lessons)
    return [record["id"] for record in anomalies if record["id"] not in captured]


def severity_weighted_traceability(anomalies, lessons):
    """Return the captured anomaly severity over the total anomaly severity."""
    if not anomalies:
        raise ValueError("cannot compute traceability over an empty anomaly history")
    captured = captured_anomaly_ids(lessons)
    total = 0.0
    covered = 0.0
    for record in anomalies:
        total += float(record["severity"])
        if record["id"] in captured:
            covered += float(record["severity"])
    if total <= 0.0:
        raise ValueError("total anomaly severity must be positive")
    return covered / total


def assess_experience_report(report):
    """Run the full Annex I experience summary report content assessment.

    report keys: sections, anomalies, lessons, required_traceability.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    for key in ("sections", "anomalies", "lessons", "required_traceability"):
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    required = _real(report["required_traceability"], "required_traceability")
    if required < 0.0 or required > 1.0:
        raise ValueError("required_traceability must lie in [0, 1], got %g" % required)

    absent = missing_sections(report["sections"])
    anomalies = validate_anomalies(report["anomalies"])
    lessons = validate_lessons(report["lessons"], set(r["id"] for r in anomalies))

    graded = []
    for lesson in lessons:
        record = dict(lesson)
        record["priority_index"] = priority_index(lesson)
        record["gaps"] = lesson_gaps(lesson)
        record["complete"] = not record["gaps"]
        graded.append(record)

    ranking = rank_lessons(lessons)
    traceability = severity_weighted_traceability(anomalies, lessons)
    uncaptured = uncaptured_anomalies(anomalies, lessons)

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the report" % name)
    for record in graded:
        if record["gaps"]:
            findings.append(
                "lesson %s is incomplete, missing: %s" % (record["id"], ", ".join(record["gaps"]))
            )
    for ref in uncaptured:
        findings.append("anomaly %s closed with no lesson recorded" % ref)
    traceability_met = traceability > required or math.isclose(
        traceability, required, rel_tol=0.0, abs_tol=TRACEABILITY_TOLERANCE
    )
    if not traceability_met:
        findings.append(
            "severity-weighted traceability %.4f is below the required %.4f"
            % (traceability, required)
        )
    by_id = dict((record["id"], record) for record in graded)
    return {
        "missing_sections": absent,
        "anomalies": anomalies,
        "lessons": graded,
        "ranking": ranking,
        "top_lesson": ranking[0],
        "top_priority_index": by_id[ranking[0]]["priority_index"],
        "traceability": traceability,
        "required_traceability": required,
        "traceability_met": traceability_met,
        "uncaptured_anomalies": uncaptured,
        "incomplete_lessons": [r["id"] for r in graded if not r["complete"]],
        "compliant": not findings,
        "findings": findings,
    }
