"""Activity-set audit for the communication system engineering process.

Anchor: ECSS-E-ST-50C clause 5.2.1.2 -- the activities the communication system
engineering step performs. Paraphrased into an implementable procedure; no
standard text is reproduced.

The single normative item fixes the activity set for the step: the activities
are the ones the clause names, not a list a project assembles from whatever it
had time for. That turns into three checkable properties, and this module grades
a declared plan against all three:

  1. coverage     -- every required activity is declared by somebody;
  2. connection   -- every declared activity consumes at least one input and
                     produces at least one output, so it sits in the flow rather
                     than beside it;
  3. satisfiable  -- every input an activity consumes is either available to the
                     step or produced by another activity of the step.

A plan can pass any one of these and still be undeliverable. Coverage with no
connection is a list of titles; connection with an unsatisfied input is an
activity that can never start.
"""

__all__ = [
    "CONFORMANT",
    "NON_CONFORMANT",
    "normalize_activity",
    "validate_activity_set",
    "assess_coverage",
    "find_disconnected_activities",
    "find_unsatisfied_inputs",
    "audit_activities",
]

CONFORMANT = "conformant"
NON_CONFORMANT = "non-conformant"


def _clean_name(value, field):
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % field)
    token = value.strip()
    if not token:
        raise ValueError("%s must not be empty" % field)
    return token


def _clean_name_list(values, field):
    if isinstance(values, str):
        raise ValueError("%s must be a list of names, not a single string" % field)
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple" % field)
    cleaned = []
    for i, value in enumerate(values):
        cleaned.append(_clean_name(value, "%s[%d]" % (field, i)))
    return cleaned


def normalize_activity(record):
    """Return one declared activity as a validated dict.

    An activity is a name plus what it consumes and what it produces. All three
    are required; a name on its own is a heading, not an activity.
    """
    if not isinstance(record, dict):
        raise ValueError("activity must be a mapping with name, inputs and outputs")
    missing = [key for key in ("name", "inputs", "outputs") if key not in record]
    if missing:
        raise ValueError("activity is missing %s" % ", ".join(sorted(missing)))
    return {
        "name": _clean_name(record["name"], "activity name"),
        "inputs": _clean_name_list(record["inputs"], "inputs"),
        "outputs": _clean_name_list(record["outputs"], "outputs"),
    }


def validate_activity_set(activities):
    """Return the declared activities validated, rejecting duplicates."""
    if isinstance(activities, dict) or not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a list or tuple of activity mappings")
    if not activities:
        raise ValueError("activities must not be empty")
    normalized = [normalize_activity(record) for record in activities]
    seen = set()
    for activity in normalized:
        if activity["name"] in seen:
            raise ValueError("activity %r declared more than once" % activity["name"])
        seen.add(activity["name"])
    return normalized


def assess_coverage(required, activities):
    """Compare the required activity set against what the plan declares."""
    wanted = _clean_name_list(required, "required")
    if not wanted:
        raise ValueError("required must not be empty")
    declared = [activity["name"] for activity in validate_activity_set(activities)]
    declared_set = set(declared)
    covered = [name for name in wanted if name in declared_set]
    missing = [name for name in wanted if name not in declared_set]
    wanted_set = set(wanted)
    additional = [name for name in declared if name not in wanted_set]
    return {
        "required": wanted,
        "covered": covered,
        "missing": missing,
        "additional": additional,
        "coverage_fraction": float(len(covered)) / float(len(wanted)),
    }


def find_disconnected_activities(activities):
    """Name the activities that consume nothing or produce nothing.

    Both are dead ends: one cannot be started from the step's inputs, the other
    cannot contribute to the step's outputs.
    """
    findings = []
    for activity in validate_activity_set(activities):
        if not activity["inputs"]:
            findings.append(
                "activity %r consumes no input and cannot be started from the "
                "step's inputs" % activity["name"]
            )
        if not activity["outputs"]:
            findings.append(
                "activity %r produces no output and cannot contribute to the "
                "step's outputs" % activity["name"]
            )
    return findings


def find_unsatisfied_inputs(activities, available_inputs):
    """Name inputs no activity can obtain.

    An input is satisfied when the step already has it, or when another activity
    of the step produces it.
    """
    normalized = validate_activity_set(activities)
    available = set(_clean_name_list(available_inputs, "available_inputs"))
    produced = set()
    for activity in normalized:
        produced.update(activity["outputs"])
    findings = []
    for activity in normalized:
        for item in activity["inputs"]:
            if item not in available and item not in produced:
                findings.append(
                    "activity %r consumes %r, which is neither available to the "
                    "step nor produced by another activity" % (activity["name"], item)
                )
    return findings


def audit_activities(required, activities, available_inputs):
    """Grade a declared activity set against the clause in one pass."""
    coverage = assess_coverage(required, activities)
    disconnected = find_disconnected_activities(activities)
    unsatisfied = find_unsatisfied_inputs(activities, available_inputs)
    findings = []
    if coverage["missing"]:
        findings.append(
            "%d required activity(ies) not declared: %s"
            % (len(coverage["missing"]), ", ".join(coverage["missing"]))
        )
    findings.extend(disconnected)
    findings.extend(unsatisfied)
    return {
        "coverage_fraction": coverage["coverage_fraction"],
        "missing": coverage["missing"],
        "additional": coverage["additional"],
        "disconnected": disconnected,
        "unsatisfied_inputs": unsatisfied,
        "findings": findings,
        "verdict": CONFORMANT if not findings else NON_CONFORMANT,
    }
