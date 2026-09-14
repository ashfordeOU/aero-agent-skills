"""Nonconformance reporting and failure handling for lowest-assurance parts.

Anchor: ECSS-Q-ST-60-13C clause 6.5.2 (reporting a nonconformance and handling
the failure behind it, for commercial EEE parts procured to the lowest
assurance class). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the nonconformance record: its mechanism, the stage it was
   detected at, the quantities and the dates.
2. Categorize the finding from its effects, its mechanism and how far it
   escaped, keeping the reasons so the category can be defended.
3. Decide whether a failure analysis is owed at all -- at the lowest class it
   is not owed by default -- and, where it is, derive the depth owed.
4. Grade the analysis performed against the depth owed and the four elements
   that close one.
5. Pick the reporting route the finding earns, from an internal log up to a
   customer notification.
6. Decide whether the proposed disposition is permitted, collecting every
   refusal rather than the first.
7. Size the containment over the lot, its uninspected remainder and any
   declared sister lot, and report the observed fraction over the inspected
   sample only.
8. Time the response from detection against the window the category allows.
"""

import datetime

__all__ = [
    "FAILURE_MECHANISMS",
    "LOT_RELATED_MECHANISMS",
    "DETECTION_STAGES",
    "EFFECT_FLAGS",
    "CATEGORIES",
    "DISPOSITIONS",
    "REPORT_ROUTES",
    "ANALYSIS_DEPTHS",
    "RESPONSE_WINDOW_WORKING_DAYS",
    "RECURRENCE_THRESHOLD",
    "ANALYSIS_ELEMENTS",
    "escape_depth",
    "working_days_between",
    "categorize_finding",
    "analysis_owed",
    "owed_analysis_depth",
    "grade_analysis",
    "reporting_route",
    "disposition_admissible",
    "containment_population",
    "observed_failure_fraction",
    "assess_nonconformance",
]

# Mechanisms a commercial part failure is attributed to.
FAILURE_MECHANISMS = (
    "isolated-random",
    "handling-induced",
    "workmanship",
    "lot-related",
    "unknown",
)

# The mechanisms that reach past the parts that failed into the population.
LOT_RELATED_MECHANISMS = ("lot-related", "unknown")

# Where a finding surfaced, shallowest first. The index is the escape depth.
DETECTION_STAGES = (
    "incoming-verification",
    "board-assembly-test",
    "unit-functional-test",
    "system-test",
    "in-orbit",
)

# Effects a finding can carry, and the category floor each one forces.
EFFECT_FLAGS = {
    "safety": "critical",
    "mission-critical-function": "critical",
    "performance-degradation": "major",
    "schedule": "minor",
    "cosmetic": "minor",
}

# Finding categories, least severe first.
CATEGORIES = ("minor", "major", "critical")

# Analysis depths, shallowest first.
ANALYSIS_DEPTHS = (
    "none",
    "visual-and-electrical",
    "imaging",
    "destructive-physical-analysis",
)

# The four separate elements that close a failure analysis.
ANALYSIS_ELEMENTS = (
    "mechanism_identified",
    "corrective_action_defined",
    "effectivity_stated",
    "action_verified",
)

# Proposed dispositions.
DISPOSITIONS = ("scrap", "return-to-supplier", "rework", "repair", "use-as-is")

# Reporting routes, narrowest first.
REPORT_ROUTES = ("internal-log", "parts-control-board", "customer-notification")

# Working days from detection to a recorded response, by category.
RESPONSE_WINDOW_WORKING_DAYS = {"critical": 3, "major": 10, "minor": 20}

# A second occurrence of the same mechanism stops being isolated at this class.
RECURRENCE_THRESHOLD = 2

# The escape stage at or beyond which a lot-related mechanism grades up.
_LOT_ESCAPE_GRADE_STAGE = "board-assembly-test"

# The escape stage at or beyond which an analysis is owed on the escape alone.
_ANALYSIS_ESCAPE_STAGE = "unit-functional-test"

# The escape stage at or beyond which the customer has to be told.
_CUSTOMER_ESCAPE_STAGE = "system-test"


def escape_depth(stage):
    """Return how far a finding escaped, as an index into the stage order."""
    if stage not in DETECTION_STAGES:
        raise ValueError(
            "detection stage must be one of %s, got %r"
            % (list(DETECTION_STAGES), stage)
        )
    return DETECTION_STAGES.index(stage)


def _category_rank(category):
    if category not in CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r" % (list(CATEGORIES), category)
        )
    return CATEGORIES.index(category)


def _depth_rank(depth):
    if depth not in ANALYSIS_DEPTHS:
        raise ValueError(
            "analysis depth must be one of %s, got %r" % (list(ANALYSIS_DEPTHS), depth)
        )
    return ANALYSIS_DEPTHS.index(depth)


def _parse_date(value, label):
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _weekdays_to(day):
    """Return the count of Mon-Fri days from the proleptic epoch up to day."""
    ordinal = day.toordinal()
    whole_weeks, remainder = divmod(ordinal, 7)
    return whole_weeks * 5 + min(remainder, 5)


def working_days_between(start, end):
    """Return the Mon-Fri days strictly after start up to and including end."""
    first = _parse_date(start, "start")
    last = _parse_date(end, "end")
    if last < first:
        raise ValueError("end date %s precedes start date %s" % (last, first))
    return _weekdays_to(last) - _weekdays_to(first)


def _validate_mechanism(mechanism):
    if mechanism not in FAILURE_MECHANISMS:
        raise ValueError(
            "mechanism must be one of %s, got %r"
            % (list(FAILURE_MECHANISMS), mechanism)
        )
    return mechanism


def _validate_effects(effects):
    if not isinstance(effects, (list, tuple, set, frozenset)):
        raise ValueError("effects must be a sequence of effect flags")
    seen = []
    for effect in effects:
        if effect not in EFFECT_FLAGS:
            raise ValueError(
                "effect must be one of %s, got %r" % (sorted(EFFECT_FLAGS), effect)
            )
        if effect not in seen:
            seen.append(effect)
    return tuple(seen)


def categorize_finding(effects, mechanism, stage):
    """Return the category the finding earns, with the reasons behind it."""
    recognised = _validate_effects(effects)
    _validate_mechanism(mechanism)
    depth = escape_depth(stage)

    category = "minor"
    reasons = []
    if not recognised:
        reasons.append("no recognised effect was recorded; the floor category stands")
    for effect in recognised:
        floor = EFFECT_FLAGS[effect]
        if _category_rank(floor) > _category_rank(category):
            category = floor
        reasons.append("effect '%s' forces at least %s" % (effect, floor))

    if mechanism in LOT_RELATED_MECHANISMS and depth >= escape_depth(
        _LOT_ESCAPE_GRADE_STAGE
    ):
        if _category_rank("major") > _category_rank(category):
            category = "major"
        reasons.append(
            "a %s mechanism that escaped to %s grades up to at least major"
            % (mechanism, stage)
        )
    return {"category": category, "reasons": reasons}


def analysis_owed(category, mechanism, recurrence_count, stage):
    """Return whether a failure analysis is owed, and every reason it is."""
    _category_rank(category)
    _validate_mechanism(mechanism)
    depth = escape_depth(stage)
    if (
        isinstance(recurrence_count, bool)
        or not isinstance(recurrence_count, int)
        or recurrence_count < 1
    ):
        raise ValueError(
            "recurrence_count must be an integer of at least 1, got %r"
            % (recurrence_count,)
        )
    reasons = []
    if _category_rank(category) >= _category_rank("major"):
        reasons.append("category %s owes an analysis at any class" % category)
    if mechanism in LOT_RELATED_MECHANISMS:
        reasons.append(
            "a %s mechanism is not bounded to the parts that failed" % mechanism
        )
    if recurrence_count >= RECURRENCE_THRESHOLD:
        reasons.append(
            "occurrence %d of the same mechanism is past the recurrence threshold of %d"
            % (recurrence_count, RECURRENCE_THRESHOLD)
        )
    if depth >= escape_depth(_ANALYSIS_ESCAPE_STAGE):
        reasons.append(
            "the finding escaped as far as %s, so the earlier screens cannot be "
            "trusted elsewhere" % stage
        )
    return {"owed": bool(reasons), "reasons": reasons}


def owed_analysis_depth(category, mechanism, recurrence_count, stage):
    """Return the deepest analysis the finding earns, not the first that applies."""
    verdict = analysis_owed(category, mechanism, recurrence_count, stage)
    if not verdict["owed"]:
        return "none"
    depth = "visual-and-electrical"
    escape = escape_depth(stage)

    def deepen(candidate):
        return candidate if _depth_rank(candidate) > _depth_rank(depth) else depth

    if _category_rank(category) >= _category_rank("major"):
        depth = deepen("imaging")
    if escape >= escape_depth(_ANALYSIS_ESCAPE_STAGE):
        depth = deepen("imaging")
    if mechanism in LOT_RELATED_MECHANISMS:
        depth = deepen("destructive-physical-analysis")
    if recurrence_count >= RECURRENCE_THRESHOLD:
        depth = deepen("destructive-physical-analysis")
    if _category_rank(category) >= _category_rank("critical"):
        depth = deepen("destructive-physical-analysis")
    if escape >= escape_depth(_CUSTOMER_ESCAPE_STAGE):
        depth = deepen("destructive-physical-analysis")
    return depth


def grade_analysis(performed, depth_owed):
    """Return whether the analysis performed closes, naming every missing element."""
    if not isinstance(performed, dict):
        raise ValueError("performed analysis must be a mapping")
    _depth_rank(depth_owed)
    depth_done = performed.get("depth", "none")
    _depth_rank(depth_done)
    missing = []
    if _depth_rank(depth_done) < _depth_rank(depth_owed):
        missing.append(
            "analysis reached %s where %s was owed" % (depth_done, depth_owed)
        )
    for element in ANALYSIS_ELEMENTS:
        value = performed.get(element, False)
        if not isinstance(value, bool):
            raise ValueError("analysis element '%s' must be a boolean" % element)
        if not value:
            missing.append("analysis element '%s' is not closed" % element)
    return {
        "depth_performed": depth_done,
        "depth_owed": depth_owed,
        "complete": not missing,
        "missing": missing,
    }


def reporting_route(category, effects, stage, analysis_is_owed, hardware_delivered):
    """Return the narrowest reporting route the finding still satisfies."""
    _category_rank(category)
    recognised = _validate_effects(effects)
    depth = escape_depth(stage)
    if not isinstance(analysis_is_owed, bool):
        raise ValueError("analysis_is_owed must be a boolean")
    if not isinstance(hardware_delivered, bool):
        raise ValueError("hardware_delivered must be a boolean")

    route = "internal-log"

    def widen(candidate):
        return (
            candidate
            if REPORT_ROUTES.index(candidate) > REPORT_ROUTES.index(route)
            else route
        )

    if analysis_is_owed or _category_rank(category) >= _category_rank("major"):
        route = widen("parts-control-board")
    if _category_rank(category) >= _category_rank("critical"):
        route = widen("customer-notification")
    if "safety" in recognised:
        route = widen("customer-notification")
    if depth >= escape_depth(_CUSTOMER_ESCAPE_STAGE):
        route = widen("customer-notification")
    if hardware_delivered:
        route = widen("customer-notification")
    return route


def disposition_admissible(
    disposition,
    analysis_closed,
    mechanism,
    effects,
    part_removed,
    procedure_qualified,
):
    """Return whether the proposed disposition is permitted, with every refusal."""
    if disposition not in DISPOSITIONS:
        raise ValueError(
            "disposition must be one of %s, got %r" % (list(DISPOSITIONS), disposition)
        )
    _validate_mechanism(mechanism)
    recognised = _validate_effects(effects)
    for name, value in (
        ("analysis_closed", analysis_closed),
        ("part_removed", part_removed),
        ("procedure_qualified", procedure_qualified),
    ):
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % name)

    refusals = []
    if disposition == "return-to-supplier" and not part_removed:
        refusals.append("a return needs the part physically removed from the assembly")
    if disposition in ("rework", "repair") and not procedure_qualified:
        refusals.append("%s needs a qualified procedure" % disposition)
    if disposition == "repair" and not analysis_closed:
        refusals.append("a repair needs the failure analysis closed first")
    if disposition == "use-as-is":
        if not analysis_closed:
            refusals.append("use-as-is needs the failure analysis closed first")
        if mechanism in LOT_RELATED_MECHANISMS:
            refusals.append(
                "use-as-is needs the mechanism bounded to the parts that failed, and "
                "'%s' is not" % mechanism
            )
        if "safety" in recognised:
            refusals.append("use-as-is is refused against a safety effect")
    return {
        "disposition": disposition,
        "permitted": not refusals,
        "refusals": refusals,
    }


def _validate_quantities(failed, inspected, lot_quantity, sister_lot_quantity):
    for name, value in (
        ("failed_quantity", failed),
        ("inspected_quantity", inspected),
        ("lot_quantity", lot_quantity),
        ("sister_lot_quantity", sister_lot_quantity),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    if inspected < 1:
        raise ValueError("inspected_quantity must be at least 1")
    if failed > inspected:
        raise ValueError(
            "failed_quantity %d cannot exceed inspected_quantity %d" % (failed, inspected)
        )
    if inspected > lot_quantity:
        raise ValueError(
            "inspected_quantity %d cannot exceed lot_quantity %d"
            % (inspected, lot_quantity)
        )
    return failed, inspected, lot_quantity, sister_lot_quantity


def observed_failure_fraction(failed, inspected):
    """Return the failed share of the inspected sample, not of the lot."""
    failed, inspected, _, _ = _validate_quantities(failed, inspected, inspected, 0)
    return failed / inspected


def containment_population(
    mechanism, failed, inspected, lot_quantity, sister_lot_quantity=0
):
    """Return the population the containment has to reach."""
    _validate_mechanism(mechanism)
    failed, inspected, lot_quantity, sister = _validate_quantities(
        failed, inspected, lot_quantity, sister_lot_quantity
    )
    uninspected_remainder = lot_quantity - inspected
    if mechanism in LOT_RELATED_MECHANISMS:
        return {
            "mechanism": mechanism,
            "scope": "lot-and-sister-lots",
            "contained_quantity": lot_quantity + sister,
            "uninspected_remainder": uninspected_remainder,
            "sister_lot_quantity": sister,
            "reason": "a %s mechanism reaches the population nobody measured"
            % mechanism,
        }
    return {
        "mechanism": mechanism,
        "scope": "failed-parts-only",
        "contained_quantity": failed,
        "uninspected_remainder": uninspected_remainder,
        "sister_lot_quantity": sister,
        "reason": "an isolated %s mechanism is bounded to the parts that failed"
        % mechanism,
    }


_RECORD_KEYS = (
    "nonconformance_id",
    "mechanism",
    "detection_stage",
    "detection_date",
    "response_date",
    "effects",
    "recurrence_count",
    "failed_quantity",
    "inspected_quantity",
    "lot_quantity",
    "sister_lot_quantity",
    "disposition",
    "analysis",
    "part_removed",
    "procedure_qualified",
    "hardware_delivered",
)


def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("nonconformance record must be a mapping")
    for key in record:
        if key not in _RECORD_KEYS:
            raise ValueError("nonconformance record carries unknown key '%s'" % key)
    for key in (
        "nonconformance_id",
        "mechanism",
        "detection_stage",
        "detection_date",
        "effects",
        "failed_quantity",
        "inspected_quantity",
        "lot_quantity",
        "disposition",
    ):
        if key not in record:
            raise ValueError("nonconformance record missing required key '%s'" % key)
    ncr_id = record["nonconformance_id"]
    if not isinstance(ncr_id, str) or not ncr_id.strip():
        raise ValueError("nonconformance_id must be a non-empty string")
    mechanism = _validate_mechanism(record["mechanism"])
    stage = record["detection_stage"]
    escape_depth(stage)
    effects = _validate_effects(record["effects"])
    recurrence = record.get("recurrence_count", 1)
    detection = _parse_date(record["detection_date"], "detection_date")
    response = record.get("response_date")
    if response is not None:
        response = _parse_date(response, "response_date")
        if response < detection:
            raise ValueError("response_date precedes detection_date")
    failed, inspected, lot_quantity, sister = _validate_quantities(
        record["failed_quantity"],
        record["inspected_quantity"],
        record["lot_quantity"],
        record.get("sister_lot_quantity", 0),
    )
    if record["disposition"] not in DISPOSITIONS:
        raise ValueError(
            "disposition must be one of %s, got %r"
            % (list(DISPOSITIONS), record["disposition"])
        )
    analysis = record.get("analysis", {})
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping")
    flags = {}
    for name in ("part_removed", "procedure_qualified", "hardware_delivered"):
        value = record.get(name, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % name)
        flags[name] = value
    return {
        "nonconformance_id": ncr_id.strip(),
        "mechanism": mechanism,
        "detection_stage": stage,
        "detection_date": detection,
        "response_date": response,
        "effects": effects,
        "recurrence_count": recurrence,
        "failed_quantity": failed,
        "inspected_quantity": inspected,
        "lot_quantity": lot_quantity,
        "sister_lot_quantity": sister,
        "disposition": record["disposition"],
        "analysis": analysis,
        "part_removed": flags["part_removed"],
        "procedure_qualified": flags["procedure_qualified"],
        "hardware_delivered": flags["hardware_delivered"],
    }


def assess_nonconformance(record, as_of_date):
    """Run the full clause 6.5.2 nonconformance assessment to one verdict."""
    data = _validate_record(record)
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < data["detection_date"]:
        raise ValueError("as_of_date precedes detection_date")

    categorization = categorize_finding(
        data["effects"], data["mechanism"], data["detection_stage"]
    )
    category = categorization["category"]
    owed = analysis_owed(
        category, data["mechanism"], data["recurrence_count"], data["detection_stage"]
    )
    depth_owed = owed_analysis_depth(
        category, data["mechanism"], data["recurrence_count"], data["detection_stage"]
    )
    analysis = grade_analysis(data["analysis"], depth_owed)
    route = reporting_route(
        category,
        data["effects"],
        data["detection_stage"],
        owed["owed"],
        data["hardware_delivered"],
    )
    disposition = disposition_admissible(
        data["disposition"],
        analysis["complete"],
        data["mechanism"],
        data["effects"],
        data["part_removed"],
        data["procedure_qualified"],
    )
    containment = containment_population(
        data["mechanism"],
        data["failed_quantity"],
        data["inspected_quantity"],
        data["lot_quantity"],
        data["sister_lot_quantity"],
    )
    fraction = observed_failure_fraction(
        data["failed_quantity"], data["inspected_quantity"]
    )

    window = RESPONSE_WINDOW_WORKING_DAYS[category]
    if data["response_date"] is None:
        elapsed = working_days_between(data["detection_date"], as_of)
        response_state = "open"
    else:
        elapsed = working_days_between(data["detection_date"], data["response_date"])
        response_state = "recorded"
    within_window = elapsed <= window

    findings = list(analysis["missing"]) + list(disposition["refusals"])
    if not within_window:
        findings.append(
            "response stands at %d working days from detection, past the %d day "
            "window a %s finding allows" % (elapsed, window, category)
        )
    if containment["scope"] == "lot-and-sister-lots":
        findings.append(
            "%d part(s) of the receiving lot were never inspected and are inside the "
            "containment" % containment["uninspected_remainder"]
        )

    if not disposition["permitted"]:
        verdict = "disposition-refused"
    elif owed["owed"] and not analysis["complete"]:
        verdict = "failure-analysis-incomplete"
    elif not within_window:
        verdict = "response-late"
    elif containment["scope"] == "lot-and-sister-lots":
        verdict = "closed-with-lot-containment"
    else:
        verdict = "closed"

    return {
        "nonconformance_id": data["nonconformance_id"],
        "category": category,
        "category_reasons": categorization["reasons"],
        "analysis_owed": owed["owed"],
        "analysis_owed_reasons": owed["reasons"],
        "analysis_depth_owed": depth_owed,
        "analysis": analysis,
        "reporting_route": route,
        "disposition": disposition,
        "containment": containment,
        "observed_failure_fraction": fraction,
        "response_working_days": elapsed,
        "response_window_days": window,
        "response_state": response_state,
        "response_within_window": within_window,
        "findings": findings,
        "verdict": verdict,
        "closed": verdict in ("closed", "closed-with-lot-containment"),
    }
