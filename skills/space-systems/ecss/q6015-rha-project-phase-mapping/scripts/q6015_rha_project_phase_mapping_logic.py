"""Mapping of radiation hardness assurance work onto the project phases.

Anchor: ECSS-Q-ST-60-15C clause 4.4 (radiation hardness assurance activities and
deliverables placed on the project lifecycle). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise every declared phase token against the canonical phase sequence.
2. Place each declared assurance activity inside its earliest-to-latest phase
   window and grade it in-window, too-early or too-late.
3. Enforce the precedence pairs: an activity that consumes another activity's
   output cannot sit in an earlier phase than the activity producing it.
4. List the phase deliverables that the plan owes up to the phase it is being
   graded through but never declares.
5. Return one plan-level verdict with the findings that produced it.
"""

__all__ = [
    "PHASE_SEQUENCE",
    "ACTIVITY_WINDOWS",
    "PHASE_DELIVERABLES",
    "PRECEDENCE_PAIRS",
    "normalize_phase",
    "phase_index",
    "compare_phases",
    "normalize_activity",
    "activity_window",
    "place_activity",
    "place_activities",
    "precedence_findings",
    "phase_deliverables",
    "owed_deliverables",
    "missing_deliverables",
    "map_phase_plan",
]

# The canonical project phase sequence the assurance work is hung on.
PHASE_SEQUENCE = ("0", "A", "B", "C", "D", "E")

# Earliest and latest phase each assurance activity may be scheduled in. The
# window is inclusive at both ends; a window of one phase pins the activity.
ACTIVITY_WINDOWS = {
    "mission-environment-definition": ("0", "A"),
    "preliminary-radiation-requirements": ("0", "B"),
    "requirements-consolidation": ("A", "B"),
    "early-part-screening": ("A", "B"),
    "shielding-concept-assessment": ("A", "B"),
    "part-characterization-testing": ("B", "C"),
    "equipment-shielding-assessment": ("B", "C"),
    "hardness-assurance-baseline-freeze": ("C", "C"),
    "flight-lot-verification-testing": ("C", "D"),
    "radiation-action-closeout": ("D", "D"),
    "in-flight-dose-monitoring": ("E", "E"),
}

# What each phase owes as a written deliverable once it has been passed.
PHASE_DELIVERABLES = {
    "0": ("mission-environment-specification",),
    "A": ("preliminary-radiation-requirements-set",),
    "B": ("consolidated-radiation-requirements", "shielding-concept-report"),
    "C": ("radiation-analysis-report", "hardness-assurance-baseline"),
    "D": ("lot-verification-test-report", "radiation-verification-closeout"),
    "E": ("in-flight-radiation-record",),
}

# (producer, consumer): the consumer may share the producer's phase but never
# precede it, because it is built on the producer's output.
PRECEDENCE_PAIRS = (
    ("mission-environment-definition", "preliminary-radiation-requirements"),
    ("preliminary-radiation-requirements", "requirements-consolidation"),
    ("requirements-consolidation", "early-part-screening"),
    ("requirements-consolidation", "part-characterization-testing"),
    ("shielding-concept-assessment", "equipment-shielding-assessment"),
    ("part-characterization-testing", "hardness-assurance-baseline-freeze"),
    ("equipment-shielding-assessment", "hardness-assurance-baseline-freeze"),
    ("hardness-assurance-baseline-freeze", "flight-lot-verification-testing"),
    ("flight-lot-verification-testing", "radiation-action-closeout"),
)


def normalize_phase(value):
    """Return the canonical phase token for a declared phase value."""
    if not isinstance(value, str):
        raise ValueError("phase must be a string, got %r" % (value,))
    token = value.strip().lower()
    if not token:
        raise ValueError("phase must not be empty")
    if token.startswith("phase"):
        token = token[len("phase"):].strip()
    token = token.replace("_", "-").strip("-")
    if not token:
        raise ValueError("phase must name a phase, got %r" % (value,))
    canonical = token.upper()
    if canonical == "0":
        return "0"
    if canonical in PHASE_SEQUENCE:
        return canonical
    raise ValueError(
        "unknown project phase %r; expected one of %s" % (value, ", ".join(PHASE_SEQUENCE))
    )


def phase_index(value):
    """Return the position of a phase in the canonical sequence."""
    return PHASE_SEQUENCE.index(normalize_phase(value))


def compare_phases(left, right):
    """Return -1, 0 or 1 ordering two phases on the canonical sequence."""
    a = phase_index(left)
    b = phase_index(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def normalize_activity(value):
    """Return the canonical activity key for a declared activity name."""
    if not isinstance(value, str):
        raise ValueError("activity must be a string, got %r" % (value,))
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in key:
        key = key.replace("--", "-")
    key = key.strip("-")
    if not key:
        raise ValueError("activity must not be empty")
    return key


def activity_window(activity):
    """Return the (earliest, latest) phase window of an assurance activity."""
    key = normalize_activity(activity)
    if key not in ACTIVITY_WINDOWS:
        raise ValueError("unknown assurance activity %r" % (activity,))
    return ACTIVITY_WINDOWS[key]


def place_activity(activity, planned_phase):
    """Grade one activity against its phase window."""
    key = normalize_activity(activity)
    earliest, latest = activity_window(key)
    phase = normalize_phase(planned_phase)
    if compare_phases(phase, earliest) < 0:
        status = "too-early"
    elif compare_phases(phase, latest) > 0:
        status = "too-late"
    else:
        status = "in-window"
    return {
        "activity": key,
        "phase": phase,
        "earliest_phase": earliest,
        "latest_phase": latest,
        "status": status,
    }


def place_activities(activities):
    """Grade a mapping of activity to planned phase, ordered by phase then name."""
    if not isinstance(activities, dict) or not activities:
        raise ValueError("activities must be a non-empty mapping of activity to phase")
    placements = [place_activity(name, phase) for name, phase in activities.items()]
    placements.sort(key=lambda rec: (PHASE_SEQUENCE.index(rec["phase"]), rec["activity"]))
    return placements


def precedence_findings(placements):
    """Return the precedence pairs an activity placement inverts."""
    if not isinstance(placements, (list, tuple)):
        raise ValueError("placements must be a sequence of placement records")
    by_activity = {}
    for record in placements:
        if not isinstance(record, dict) or "activity" not in record or "phase" not in record:
            raise ValueError("each placement must carry 'activity' and 'phase'")
        by_activity[record["activity"]] = record["phase"]
    findings = []
    for producer, consumer in PRECEDENCE_PAIRS:
        if producer in by_activity and consumer in by_activity:
            if compare_phases(by_activity[consumer], by_activity[producer]) < 0:
                findings.append(
                    "%s is planned in phase %s, before %s in phase %s that it depends on"
                    % (consumer, by_activity[consumer], producer, by_activity[producer])
                )
    return findings


def phase_deliverables(phase):
    """Return the deliverables a single phase owes."""
    return PHASE_DELIVERABLES[normalize_phase(phase)]


def owed_deliverables(through_phase):
    """Return every deliverable owed from phase 0 up to and including a phase."""
    last = phase_index(through_phase)
    owed = []
    for phase in PHASE_SEQUENCE[: last + 1]:
        owed.extend(PHASE_DELIVERABLES[phase])
    return owed


def missing_deliverables(declared, through_phase):
    """Return the owed deliverables a plan never declares, in owed order."""
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared deliverables must be a sequence")
    present = set()
    for item in declared:
        if not isinstance(item, str):
            raise ValueError("deliverable must be a string, got %r" % (item,))
        key = item.strip().lower().replace("_", "-").replace(" ", "-")
        if not key:
            raise ValueError("deliverable must not be empty")
        present.add(key)
    return [item for item in owed_deliverables(through_phase) if item not in present]


def map_phase_plan(plan):
    """Grade a whole clause 4.4 phase plan.

    plan keys: activities (mapping activity -> phase), through_phase,
    optional deliverables (sequence of declared deliverable names).
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for key in ("activities", "through_phase"):
        if key not in plan:
            raise ValueError("plan missing required key '%s'" % key)
    through = normalize_phase(plan["through_phase"])
    placements = place_activities(plan["activities"])
    out_of_phase = [rec for rec in placements if rec["status"] != "in-window"]
    precedence = precedence_findings(placements)
    missing = missing_deliverables(plan.get("deliverables", ()), through)
    findings = []
    for record in out_of_phase:
        findings.append(
            "%s is planned in phase %s, %s its %s-%s window"
            % (
                record["activity"],
                record["phase"],
                "before" if record["status"] == "too-early" else "after",
                record["earliest_phase"],
                record["latest_phase"],
            )
        )
    findings.extend(precedence)
    for item in missing:
        findings.append("phase deliverable %s is owed through phase %s but not declared"
                        % (item, through))
    return {
        "through_phase": through,
        "placements": placements,
        "out_of_phase": out_of_phase,
        "precedence_violations": precedence,
        "missing_deliverables": missing,
        "compliant": not findings,
        "findings": findings,
    }
