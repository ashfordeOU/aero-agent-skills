"""Nonconformance control and failure analysis at the intermediate EEE class.

Anchor: ECSS-Q-ST-60-13C clause 5.5.2 (nonconformance control and failure
analysis for commercial EEE parts procured at the intermediate assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Categorize the finding major or minor from its effects, its mechanism and
   the stage it surfaced at, keeping the reasons so the category can be
   defended later.
2. Decide whether a failure analysis is owed at all, and at what depth:
   visual and electrical, non-destructive imaging, or destructive physical
   analysis.
3. Grade the analysis actually performed against the depth owed and against
   the four things that make an analysis closed: an identified mechanism, a
   defined corrective action, a stated effectivity and a verification.
4. Decide whether the proposed disposition is permitted, collecting every
   refusal rather than the first.
5. Size the containment: a lot-related mechanism reaches the whole receiving
   lot, its uninspected remainder and any sister lot sharing the date code;
   an isolated mechanism reaches the parts that failed.
6. Time the analysis start against the response owed by the category.
7. Close on one verdict.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "MAJOR_EFFECTS",
    "DETECTION_STAGES",
    "ANALYSIS_DEPTHS",
    "DISPOSITIONS",
    "MECHANISMS",
    "RESPONSE_HOURS",
    "DEFAULT_RECURRENCE_THRESHOLD",
    "categorize_finding",
    "failure_analysis_required",
    "owed_analysis_depth",
    "analysis_completeness",
    "disposition_admissible",
    "containment_scope",
    "response_timeliness",
    "assess_class_two_nonconformance",
]

# Elapsed hours and failure fractions are differences and quotients of
# measured values, so a case landing exactly on a bound can fall a few ULP on
# the wrong side. Absorb that here, never by moving the bound.
BOUND_TOLERANCE = 1e-9

# Effects that make a finding major on their own.
MAJOR_EFFECTS = (
    "safety",
    "interchangeability",
    "specified-limit-exceeded",
    "mission-reliability",
)

# Detection stages, earliest first. The index is the escape depth.
DETECTION_STAGES = (
    "incoming-inspection",
    "part-screening",
    "board-assembly-test",
    "system-test",
    "flight-operations",
)

# Failure analysis depths, shallowest first.
ANALYSIS_DEPTHS = (
    "visual-and-electrical",
    "non-destructive-imaging",
    "destructive-physical-analysis",
)

DISPOSITIONS = (
    "scrap",
    "return-to-supplier",
    "rework",
    "repair",
    "use-as-is",
)

MECHANISMS = ("isolated", "lot-related", "unknown")

# Hours a category allows between detection and the start of the analysis.
RESPONSE_HOURS = {"major": 24.0, "minor": 120.0}

DEFAULT_RECURRENCE_THRESHOLD = 2


def _require_text(value, label):
    """Return a stripped non-empty string or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _optional_text(value):
    """Return a stripped string, or None when the field is blank or absent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("reference fields must be strings, got %r" % (value,))
    stripped = value.strip()
    return stripped or None


def _require_member(value, allowed, label):
    """Return a validated member of a closed vocabulary."""
    key = _require_text(value, label).lower()
    if key not in allowed:
        raise ValueError("%s %r is not one of %r" % (label, value, list(allowed)))
    return key


def _require_count(value, label):
    """Return a validated non-negative integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_moment(value, label):
    """Return a datetime parsed from an ISO timestamp or a datetime object."""
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s %r is not an ISO timestamp" % (label, value))
    raise ValueError("%s must be an ISO timestamp or a datetime, got %r" % (label, value))


def _validate_effects(effects):
    """Return the recognised effects declared against a finding."""
    if effects is None:
        return []
    if not isinstance(effects, (list, tuple, set, frozenset)):
        raise ValueError("effects must be a sequence or set")
    seen = []
    for item in effects:
        key = _require_text(item, "effect").lower()
        if key not in MAJOR_EFFECTS:
            raise ValueError("effect %r is not one of %r" % (item, list(MAJOR_EFFECTS)))
        if key not in seen:
            seen.append(key)
    return sorted(seen)


def categorize_finding(effects, mechanism, detection_stage):
    """Return the category of a finding and the reasons that produced it.

    A finding is major on any recognised effect, and a lot-related mechanism
    that escaped the part-level screens is graded up on the escape alone.
    """
    declared = _validate_effects(effects)
    mech = _require_member(mechanism, MECHANISMS, "mechanism")
    stage = _require_member(detection_stage, DETECTION_STAGES, "detection_stage")
    reasons = ["effect on %s" % effect for effect in declared]
    escaped = DETECTION_STAGES.index(stage) >= DETECTION_STAGES.index("board-assembly-test")
    if mech == "lot-related" and escaped:
        reasons.append("lot-related mechanism escaped to %s" % stage)
    category = "major" if reasons else "minor"
    return {
        "category": category,
        "reasons": reasons,
        "effects": declared,
        "mechanism": mech,
        "detection_stage": stage,
        "escaped_part_screens": escaped,
    }


def failure_analysis_required(category, mechanism, detection_stage, recurrence_count=0,
                              recurrence_threshold=DEFAULT_RECURRENCE_THRESHOLD):
    """Return whether a failure analysis is owed, and the reasons it is owed."""
    cat = _require_member(category, ("major", "minor"), "category")
    mech = _require_member(mechanism, MECHANISMS, "mechanism")
    stage = _require_member(detection_stage, DETECTION_STAGES, "detection_stage")
    count = _require_count(recurrence_count, "recurrence_count")
    threshold = _require_count(recurrence_threshold, "recurrence_threshold")
    if threshold == 0:
        raise ValueError("recurrence_threshold must be positive")
    reasons = []
    if cat == "major":
        reasons.append("category is major")
    if mech == "lot-related":
        reasons.append("mechanism is shared by the lot")
    if mech == "unknown":
        reasons.append("mechanism is not yet known")
    if count >= threshold:
        reasons.append("the mechanism has recurred %d times" % count)
    if DETECTION_STAGES.index(stage) >= DETECTION_STAGES.index("system-test"):
        reasons.append("the finding surfaced at %s" % stage)
    return {"required": bool(reasons), "reasons": reasons}


def owed_analysis_depth(category, mechanism, detection_stage, recurrence_count=0,
                        recurrence_threshold=DEFAULT_RECURRENCE_THRESHOLD):
    """Return the deepest failure analysis the circumstances owe."""
    cat = _require_member(category, ("major", "minor"), "category")
    mech = _require_member(mechanism, MECHANISMS, "mechanism")
    stage = _require_member(detection_stage, DETECTION_STAGES, "detection_stage")
    count = _require_count(recurrence_count, "recurrence_count")
    threshold = _require_count(recurrence_threshold, "recurrence_threshold")
    if threshold == 0:
        raise ValueError("recurrence_threshold must be positive")
    level = 0
    if cat == "major" or DETECTION_STAGES.index(stage) >= DETECTION_STAGES.index(
        "board-assembly-test"
    ):
        level = max(level, 1)
    if (
        mech == "lot-related"
        or count >= threshold
        or DETECTION_STAGES.index(stage) >= DETECTION_STAGES.index("system-test")
    ):
        level = max(level, 2)
    return ANALYSIS_DEPTHS[level]


def analysis_completeness(analysis, owed_depth):
    """Return whether a failure analysis is closed at the depth it owes.

    Every missing element is named, because an analysis short of two things
    does not become closed by fixing one of them.
    """
    owed = _require_member(owed_depth, ANALYSIS_DEPTHS, "owed_depth")
    if analysis is None:
        return {
            "complete": False,
            "depth_performed": None,
            "missing": [
                "no-analysis-performed",
                "mechanism-not-identified",
                "corrective-action-not-defined",
                "effectivity-not-stated",
                "corrective-action-not-verified",
            ],
        }
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping, got %r" % (analysis,))
    performed = _require_member(
        analysis.get("depth_performed"), ANALYSIS_DEPTHS, "depth_performed"
    )
    missing = []
    if ANALYSIS_DEPTHS.index(performed) < ANALYSIS_DEPTHS.index(owed):
        missing.append("depth-below-owed")
    if not _require_bool(
        analysis.get("mechanism_identified", False), "mechanism_identified"
    ):
        missing.append("mechanism-not-identified")
    if _optional_text(analysis.get("corrective_action")) is None:
        missing.append("corrective-action-not-defined")
    if _optional_text(analysis.get("effectivity")) is None:
        missing.append("effectivity-not-stated")
    if not _require_bool(
        analysis.get("corrective_action_verified", False), "corrective_action_verified"
    ):
        missing.append("corrective-action-not-verified")
    return {"complete": not missing, "depth_performed": performed, "missing": missing}


def disposition_admissible(disposition, category, mechanism, effects, analysis_state,
                           part_removed=False, qualified_procedure=False):
    """Return whether the proposed disposition may be taken, and every refusal."""
    proposed = _require_member(disposition, DISPOSITIONS, "disposition")
    _require_member(category, ("major", "minor"), "category")
    mech = _require_member(mechanism, MECHANISMS, "mechanism")
    declared = _validate_effects(effects)
    if not isinstance(analysis_state, dict) or "complete" not in analysis_state:
        raise ValueError("analysis_state must carry a completeness flag")
    removed = _require_bool(part_removed, "part_removed")
    procedure = _require_bool(qualified_procedure, "qualified_procedure")
    refusals = []
    if proposed == "return-to-supplier" and not removed:
        refusals.append("the part is still installed and cannot be returned")
    if proposed in ("rework", "repair") and not procedure:
        refusals.append("no qualified procedure is declared for %s" % proposed)
    if proposed == "repair" and not analysis_state.get("complete"):
        refusals.append("a repair needs the failure analysis closed first")
    if proposed == "use-as-is":
        if not analysis_state.get("complete"):
            refusals.append("use-as-is needs the failure analysis closed at the owed depth")
        if mech != "isolated":
            refusals.append("use-as-is cannot bound a mechanism that is not isolated")
        if "safety" in declared:
            refusals.append("use-as-is is refused on a finding with a safety effect")
    return {"disposition": proposed, "permitted": not refusals, "refusals": refusals}


def containment_scope(mechanism, lot_size, inspected_quantity, failed_quantity,
                      sister_lot_sizes=None):
    """Return the population a finding contains, and the observed fraction.

    The observed fraction is a sample statistic over the inspected quantity,
    never a lot failure rate.
    """
    mech = _require_member(mechanism, MECHANISMS, "mechanism")
    lot = _require_count(lot_size, "lot_size")
    inspected = _require_count(inspected_quantity, "inspected_quantity")
    failed = _require_count(failed_quantity, "failed_quantity")
    if lot == 0:
        raise ValueError("lot_size must be positive")
    if inspected == 0:
        raise ValueError("inspected_quantity must be positive")
    if inspected > lot:
        raise ValueError("inspected %d exceeds the lot size %d" % (inspected, lot))
    if failed > inspected:
        raise ValueError("failed %d exceeds the inspected quantity %d" % (failed, inspected))
    sisters = []
    if sister_lot_sizes is not None:
        if not isinstance(sister_lot_sizes, (list, tuple)):
            raise ValueError("sister_lot_sizes must be a sequence")
        for index, size in enumerate(sister_lot_sizes):
            value = _require_count(size, "sister_lot_sizes[%d]" % index)
            if value == 0:
                raise ValueError("sister_lot_sizes[%d] must be positive" % index)
            sisters.append(value)
    if mech == "isolated":
        contained = failed
        remainder = 0
        sister_total = 0
    else:
        sister_total = sum(sisters)
        contained = lot + sister_total
        remainder = lot - inspected
    return {
        "mechanism": mech,
        "contained_quantity": contained,
        "uninspected_remainder": remainder,
        "sister_lot_quantity": sister_total,
        "observed_failure_fraction": failed / inspected,
    }


def response_timeliness(detected_at, analysis_started_at, category,
                        response_hours=None):
    """Return the elapsed hours to the analysis start against the owed response."""
    detected = _require_moment(detected_at, "detected_at")
    started = _require_moment(analysis_started_at, "analysis_started_at")
    cat = _require_member(category, ("major", "minor"), "category")
    if started < detected:
        raise ValueError("analysis_started_at %s precedes detected_at %s" % (started, detected))
    table = RESPONSE_HOURS if response_hours is None else response_hours
    if not isinstance(table, dict) or cat not in table:
        raise ValueError("response_hours must be a mapping carrying %r" % cat)
    owed = table[cat]
    if not isinstance(owed, (int, float)) or isinstance(owed, bool):
        raise ValueError("owed response hours must be a real number, got %r" % (owed,))
    owed = float(owed)
    if not math.isfinite(owed) or owed <= 0.0:
        raise ValueError("owed response hours must be finite and positive, got %g" % owed)
    elapsed = (started - detected).total_seconds() / 3600.0
    on_time = elapsed <= owed or math.isclose(
        elapsed, owed, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    return {
        "elapsed_hours": elapsed,
        "owed_hours": owed,
        "on_time": on_time,
        "overrun_hours": 0.0 if on_time else elapsed - owed,
    }


REQUIRED_KEYS = (
    "nonconformance_id",
    "mechanism",
    "detection_stage",
    "disposition",
    "lot_size",
    "inspected_quantity",
    "failed_quantity",
    "detected_at",
    "analysis_started_at",
)


def assess_class_two_nonconformance(record):
    """Grade one class 2 commercial EEE nonconformance against clause 5.5.2.

    record keys: nonconformance_id, mechanism, detection_stage, disposition,
    lot_size, inspected_quantity, failed_quantity, detected_at,
    analysis_started_at, and optionally effects, analysis, recurrence_count,
    recurrence_threshold, sister_lot_sizes, part_removed and
    qualified_procedure.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in REQUIRED_KEYS:
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    identity = _require_text(record["nonconformance_id"], "nonconformance_id")
    threshold = record.get("recurrence_threshold", DEFAULT_RECURRENCE_THRESHOLD)
    recurrence = record.get("recurrence_count", 0)

    categorization = categorize_finding(
        record.get("effects"), record["mechanism"], record["detection_stage"]
    )
    category = categorization["category"]
    analysis_owed = failure_analysis_required(
        category,
        categorization["mechanism"],
        categorization["detection_stage"],
        recurrence,
        threshold,
    )
    depth = owed_analysis_depth(
        category,
        categorization["mechanism"],
        categorization["detection_stage"],
        recurrence,
        threshold,
    )
    analysis_state = analysis_completeness(record.get("analysis"), depth)
    disposition = disposition_admissible(
        record["disposition"],
        category,
        categorization["mechanism"],
        categorization["effects"],
        analysis_state,
        record.get("part_removed", False),
        record.get("qualified_procedure", False),
    )
    containment = containment_scope(
        categorization["mechanism"],
        record["lot_size"],
        record["inspected_quantity"],
        record["failed_quantity"],
        record.get("sister_lot_sizes"),
    )
    timeliness = response_timeliness(
        record["detected_at"], record["analysis_started_at"], category
    )

    if not disposition["permitted"]:
        verdict = "disposition-refused"
    elif analysis_owed["required"] and not analysis_state["complete"]:
        verdict = "failure-analysis-incomplete"
    elif not timeliness["on_time"]:
        verdict = "response-late"
    elif categorization["mechanism"] == "lot-related":
        verdict = "closed-with-lot-containment"
    else:
        verdict = "closed"
    return {
        "nonconformance_id": identity,
        "category": category,
        "category_reasons": categorization["reasons"],
        "escaped_part_screens": categorization["escaped_part_screens"],
        "analysis_required": analysis_owed["required"],
        "analysis_reasons": analysis_owed["reasons"],
        "owed_analysis_depth": depth,
        "analysis_state": analysis_state,
        "disposition": disposition,
        "containment": containment,
        "timeliness": timeliness,
        "verdict": verdict,
        "closed": verdict in ("closed", "closed-with-lot-containment"),
    }
