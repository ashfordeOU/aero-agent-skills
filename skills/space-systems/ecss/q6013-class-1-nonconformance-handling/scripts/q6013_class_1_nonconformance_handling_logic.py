"""Nonconformance reporting and disposition for highest-assurance commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 4.5.2 (nonconformance handling for class 1
commercial EEE parts). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the nonconformance record: the lot identity, the detection stage,
   the inspected and failed quantities against the lot size, and the two clock
   readings that time the report.
2. Categorize the finding as major or minor from its effect on safety,
   interchangeability, specified limits and mission reliability, and from the
   stage at which it escaped detection.
3. Derive the reporting deadline the category earns and compare the elapsed
   hours with it under a named tolerance, so an exact-deadline report is timely.
4. Derive the concurrence the proposed disposition needs: a design-affecting
   disposition (use-as-is, repair) always reaches the customer, a major finding
   always reaches the review board.
5. Decide whether the proposed disposition is permitted at all: use-as-is is
   refused while the root cause is unknown, while the mechanism is lot-related,
   and whenever safety is affected; repair and rework need a qualified
   procedure; return-to-supplier needs the part physically removed.
6. Size the containment: a lot-related mechanism puts the whole receiving lot
   at risk, an isolated mechanism only the parts that failed.
"""

import math

__all__ = [
    "REPORT_TOLERANCE_H",
    "MAJOR_DEADLINE_H",
    "MINOR_DEADLINE_H",
    "DISPOSITIONS",
    "DETECTION_STAGES",
    "validate_record",
    "categorize_severity",
    "reporting_deadline_h",
    "assess_reporting",
    "required_concurrence",
    "disposition_permitted",
    "containment",
    "assess_nonconformance",
]

# A report filed exactly on the deadline is on time. Clock arithmetic is a
# difference of floats, so absorb representation error here rather than by
# moving the deadline.
REPORT_TOLERANCE_H = 1e-9

# Hours allowed between detection and the written report.
MAJOR_DEADLINE_H = 24.0
MINOR_DEADLINE_H = 120.0

DISPOSITIONS = (
    "use-as-is",
    "repair",
    "rework",
    "scrap",
    "return-to-supplier",
)

# Ordered by how far the part had travelled before the finding surfaced.
DETECTION_STAGES = {
    "incoming-inspection": 0,
    "lot-acceptance-test": 1,
    "board-assembly-test": 2,
    "system-test": 3,
    "in-service": 4,
}

# A finding that surfaced at or beyond this stage escaped the part-level
# screens, so a lot-related mechanism is graded up to major.
ESCAPE_STAGE = DETECTION_STAGES["board-assembly-test"]

_EFFECT_FLAGS = (
    "affects_safety",
    "affects_interchangeability",
    "outside_specified_limits",
    "affects_mission_reliability",
)

_BOOL_FLAGS = _EFFECT_FLAGS + (
    "root_cause_known",
    "mechanism_is_lot_related",
    "qualified_procedure_available",
    "part_removed",
)


def _number(value, label, positive=True, allow_zero=False):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if number < 0.0:
                raise ValueError("%s must be non-negative, got %g" % (label, number))
        elif number <= 0.0:
            raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _count(value, label):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _flag(record, name):
    """Return a required boolean flag from the record."""
    if name not in record:
        raise ValueError("record missing required flag '%s'" % name)
    value = record[name]
    if not isinstance(value, bool):
        raise ValueError("record['%s'] must be a boolean, got %r" % (name, value))
    return value


def validate_record(record):
    """Return a normalised nonconformance record.

    Required keys: lot_id, detection_stage, lot_size, quantity_inspected,
    quantity_failed, detected_at_h, reported_at_h, proposed_disposition, plus
    every boolean flag in _BOOL_FLAGS.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")

    lot_id = record.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("record['lot_id'] must be a non-empty string")

    stage = record.get("detection_stage")
    if stage not in DETECTION_STAGES:
        raise ValueError(
            "record['detection_stage'] must be one of %s, got %r"
            % (sorted(DETECTION_STAGES), stage)
        )

    disposition = record.get("proposed_disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError(
            "record['proposed_disposition'] must be one of %s, got %r"
            % (list(DISPOSITIONS), disposition)
        )

    lot_size = _count(record.get("lot_size"), "lot_size")
    inspected = _count(record.get("quantity_inspected"), "quantity_inspected")
    failed = _count(record.get("quantity_failed"), "quantity_failed")
    if lot_size == 0:
        raise ValueError("lot_size must be at least one part")
    if inspected == 0:
        raise ValueError("quantity_inspected must be at least one part")
    if inspected > lot_size:
        raise ValueError(
            "quantity_inspected %d exceeds lot_size %d" % (inspected, lot_size)
        )
    if failed > inspected:
        raise ValueError(
            "quantity_failed %d exceeds quantity_inspected %d" % (failed, inspected)
        )
    if failed == 0:
        raise ValueError("a nonconformance record needs at least one failed part")

    detected_at_h = _number(record.get("detected_at_h"), "detected_at_h",
                            positive=True, allow_zero=True)
    reported_at_h = _number(record.get("reported_at_h"), "reported_at_h",
                            positive=True, allow_zero=True)
    if reported_at_h < detected_at_h:
        raise ValueError(
            "reported_at_h %g precedes detected_at_h %g" % (reported_at_h, detected_at_h)
        )

    normalised = {
        "lot_id": lot_id.strip(),
        "detection_stage": stage,
        "stage_rank": DETECTION_STAGES[stage],
        "lot_size": lot_size,
        "quantity_inspected": inspected,
        "quantity_failed": failed,
        "detected_at_h": detected_at_h,
        "reported_at_h": reported_at_h,
        "proposed_disposition": disposition,
    }
    for name in _BOOL_FLAGS:
        normalised[name] = _flag(record, name)
    return normalised


def categorize_severity(record):
    """Return {'severity': 'major'|'minor', 'reasons': [...]} for the record."""
    normalised = record if "stage_rank" in record else validate_record(record)
    reasons = []
    if normalised["affects_safety"]:
        reasons.append("the finding affects safety")
    if normalised["affects_interchangeability"]:
        reasons.append("the finding affects interchangeability of the part")
    if normalised["outside_specified_limits"]:
        reasons.append("a measured parameter sits outside its specified limit")
    if normalised["affects_mission_reliability"]:
        reasons.append("the finding affects mission reliability")
    if normalised["mechanism_is_lot_related"] and normalised["stage_rank"] >= ESCAPE_STAGE:
        reasons.append(
            "a lot-related mechanism escaped the part-level screens and surfaced at %s"
            % normalised["detection_stage"]
        )
    severity = "major" if reasons else "minor"
    return {"severity": severity, "reasons": reasons}


def reporting_deadline_h(severity):
    """Return the hours allowed between detection and the written report."""
    if severity == "major":
        return MAJOR_DEADLINE_H
    if severity == "minor":
        return MINOR_DEADLINE_H
    raise ValueError("severity must be 'major' or 'minor', got %r" % (severity,))


def assess_reporting(detected_at_h, reported_at_h, severity):
    """Return the reporting clock assessment for the given severity."""
    detected = _number(detected_at_h, "detected_at_h", positive=True, allow_zero=True)
    reported = _number(reported_at_h, "reported_at_h", positive=True, allow_zero=True)
    if reported < detected:
        raise ValueError(
            "reported_at_h %g precedes detected_at_h %g" % (reported, detected)
        )
    deadline = reporting_deadline_h(severity)
    elapsed = reported - detected
    timely = elapsed < deadline or math.isclose(
        elapsed, deadline, rel_tol=0.0, abs_tol=REPORT_TOLERANCE_H
    )
    overdue = 0.0 if timely else elapsed - deadline
    return {
        "elapsed_h": elapsed,
        "deadline_h": deadline,
        "timely": timely,
        "overdue_h": overdue,
    }


def required_concurrence(severity, disposition):
    """Return the ordered authorities that must concur with the disposition."""
    if severity not in ("major", "minor"):
        raise ValueError("severity must be 'major' or 'minor', got %r" % (severity,))
    if disposition not in DISPOSITIONS:
        raise ValueError("disposition must be one of %s" % list(DISPOSITIONS))
    authorities = {"project-review-board"}
    if severity == "major":
        authorities.add("customer")
    if disposition in ("use-as-is", "repair"):
        # Both leave a part in the build that no longer meets its drawing.
        authorities.add("customer")
        authorities.add("design-authority")
    if disposition == "return-to-supplier":
        authorities.add("procurement-authority")
    return tuple(sorted(authorities))


def disposition_permitted(record):
    """Return {'permitted': bool, 'objections': [...]} for the proposed disposition."""
    normalised = record if "stage_rank" in record else validate_record(record)
    disposition = normalised["proposed_disposition"]
    objections = []

    if disposition == "use-as-is":
        if not normalised["root_cause_known"]:
            objections.append(
                "use-as-is needs an understood failure mechanism; the root cause is open"
            )
        if normalised["mechanism_is_lot_related"]:
            objections.append(
                "use-as-is cannot cover a lot-related mechanism that the whole lot shares"
            )
        if normalised["affects_safety"]:
            objections.append("use-as-is is not available for a safety-affecting finding")
    elif disposition == "repair":
        if not normalised["qualified_procedure_available"]:
            objections.append("repair needs a qualified repair procedure for the part type")
        if normalised["affects_safety"]:
            objections.append("repair is not available for a safety-affecting finding")
        if not normalised["root_cause_known"]:
            objections.append(
                "repair needs an understood failure mechanism; the root cause is open"
            )
    elif disposition == "rework":
        if not normalised["qualified_procedure_available"]:
            objections.append("rework needs a qualified rework procedure for the part type")
    elif disposition == "return-to-supplier":
        if normalised["stage_rank"] >= ESCAPE_STAGE and not normalised["part_removed"]:
            objections.append(
                "return-to-supplier needs the part removed from the assembly first"
            )
    # scrap carries no objection: it always closes the finding.
    return {"permitted": not objections, "objections": objections}


def containment(record):
    """Return the parts put at risk by the finding and the observed failure rate."""
    normalised = record if "stage_rank" in record else validate_record(record)
    inspected = normalised["quantity_inspected"]
    failed = normalised["quantity_failed"]
    lot_size = normalised["lot_size"]
    lot_related = normalised["mechanism_is_lot_related"]
    parts_at_risk = lot_size if lot_related else failed
    return {
        "lot_id": normalised["lot_id"],
        "lot_related": lot_related,
        "parts_at_risk": parts_at_risk,
        "uninspected_at_risk": (lot_size - inspected) if lot_related else 0,
        "observed_failure_fraction": failed / inspected,
        "scope": "whole-receiving-lot" if lot_related else "failed-parts-only",
    }


def assess_nonconformance(record):
    """Run the full clause 4.5.2 nonconformance assessment for one record."""
    normalised = validate_record(record)
    categorization = categorize_severity(normalised)
    severity = categorization["severity"]
    reporting = assess_reporting(
        normalised["detected_at_h"], normalised["reported_at_h"], severity
    )
    concurrence = required_concurrence(severity, normalised["proposed_disposition"])
    permission = disposition_permitted(normalised)
    scope = containment(normalised)

    findings = []
    if not reporting["timely"]:
        findings.append(
            "the %s finding on lot %s was reported %.3f h after detection, %.3f h "
            "past the %.1f h deadline"
            % (severity, normalised["lot_id"], reporting["elapsed_h"],
               reporting["overdue_h"], reporting["deadline_h"])
        )
    findings.extend(permission["objections"])
    if scope["uninspected_at_risk"] > 0:
        findings.append(
            "%d parts of lot %s were never inspected and share the lot-related "
            "mechanism; containment covers the whole lot"
            % (scope["uninspected_at_risk"], scope["lot_id"])
        )

    return {
        "lot_id": normalised["lot_id"],
        "severity": severity,
        "severity_reasons": categorization["reasons"],
        "reporting": reporting,
        "required_concurrence": concurrence,
        "proposed_disposition": normalised["proposed_disposition"],
        "disposition_permitted": permission["permitted"],
        "containment": scope,
        "findings": findings,
        "closeable": permission["permitted"] and reporting["timely"],
    }
