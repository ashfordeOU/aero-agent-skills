"""Naming the unit accountable for electronic part control at reliability Class 2.

Anchor: ECSS-Q-ST-60C clause 5.1.2.1 (the organizational unit accountable for
electronic part control activities on a Class 2 programme is named).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared unit: an identifier, the form its appointment was
   recorded in, the line it reports through, and whether an escalation route
   to product assurance has been declared.
2. Validate every activity assignment and dispose of it. An assignment that
   names an unknown unit, an activity outside the mandated set, a unit whose
   appointment was never recorded, an unqualified holder, or a delegation of
   a duty that cannot be lent is not an accepted ownership.
3. Read ownership from the accepted assignments only. An activity carried by
   two different units is contested, not covered twice: nobody is accountable
   for it, which is the failure this clause exists to prevent.
4. Weight the covered activities by declared criticality, so losing the
   selection-approval duty does not cost the same as losing supply
   monitoring.
5. Test independence where it matters. A unit reporting inside the design
   authority whose parts it approves needs a declared escalation route; one
   reporting through product assurance or programme management does not.
6. Cap how much one holder may carry alone, and return one accountability
   verdict with ranked findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "CONTROL_ACTIVITIES",
    "NON_DELEGABLE_ACTIVITIES",
    "APPOINTMENT_FORMS",
    "REPORTING_LINES",
    "MANDATORY_ASSIGNMENT_ATTRIBUTES",
    "validate_unit_id",
    "validate_activity",
    "appointment_is_recorded",
    "independence_state",
    "assignment_completeness",
    "evaluate_assignment",
    "activity_ownership",
    "activity_coverage",
    "holder_load",
    "assess_parts_control_organization",
]

# Coverage is a ratio of summed integer weights. An exactly-met requirement can
# land a few ULPs low; absorb the representation error here rather than
# lowering the level the programme agreed.
COVERAGE_TOLERANCE = 1e-9

# The part control activities a Class 2 programme has to place with a named
# unit, and the criticality weight each carries in the coverage figure.
CONTROL_ACTIVITIES = {
    "part-selection-approval": 5,
    "nonconformance-disposition": 5,
    "procurement-specification-release": 4,
    "alert-and-advisory-handling": 4,
    "component-control-plan-maintenance": 4,
    "declared-components-list-issue": 3,
    "derating-and-worst-case-verification": 3,
    "incoming-inspection-release": 3,
    "obsolescence-and-supply-monitoring": 2,
}

# Duties the accountable unit exercises itself. They may be supported, but the
# decision cannot be handed to another unit and still be the named unit's.
NON_DELEGABLE_ACTIVITIES = frozenset(
    {"part-selection-approval", "nonconformance-disposition"}
)

# How an appointment was recorded -> does it stand as an appointment at all.
APPOINTMENT_FORMS = {
    "contract-annex": True,
    "programme-directive": True,
    "quality-manual": True,
    "organization-chart-issue": True,
    "meeting-minute": False,
    "email-note": False,
    "verbal": False,
    "none": False,
}

# Reporting line -> is the unit structurally separate from the design authority
# whose part choices it has to be able to refuse.
REPORTING_LINES = {
    "product-assurance": True,
    "programme-management": True,
    "corporate-quality": True,
    "design-authority": False,
    "subsystem-design-office": False,
}

# The attributes without which an assignment cannot be disposed of at all.
MANDATORY_ASSIGNMENT_ATTRIBUTES = (
    "assignment_id",
    "activity",
    "unit_id",
    "holder",
)

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "unknown-unit": 1,
    "unknown-activity": 2,
    "unit-not-appointed": 3,
    "non-delegable-activity-delegated": 4,
    "holder-not-qualified": 5,
    "activity-contested": 6,
    "activity-unassigned": 7,
    "escalation-route-absent": 8,
    "holder-overloaded": 9,
    "accepted": 10,
}

_ACCEPTED = "accepted"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_unit_id(value):
    """Return the validated identifier of one declared unit."""
    return _require_text(value, "unit_id")


def validate_activity(value):
    """Return the canonical name of one mandated control activity."""
    name = _require_text(value, "activity").lower()
    if name not in CONTROL_ACTIVITIES:
        raise ValueError(
            "unknown activity %r; mandated: %s"
            % (value, ", ".join(sorted(CONTROL_ACTIVITIES)))
        )
    return name


def appointment_is_recorded(appointment_form):
    """Return True when the appointment form stands as a recorded appointment."""
    form = _require_text(appointment_form, "appointment_form").lower()
    if form not in APPOINTMENT_FORMS:
        raise ValueError(
            "unknown appointment_form %r; known: %s"
            % (appointment_form, ", ".join(sorted(APPOINTMENT_FORMS)))
        )
    return APPOINTMENT_FORMS[form]


def independence_state(reporting_line, escalation_route_declared):
    """Return how a unit stands against the design authority it must refuse."""
    line = _require_text(reporting_line, "reporting_line").lower()
    if line not in REPORTING_LINES:
        raise ValueError(
            "unknown reporting_line %r; known: %s"
            % (reporting_line, ", ".join(sorted(REPORTING_LINES)))
        )
    declared = _require_bool(escalation_route_declared, "escalation_route_declared")
    if REPORTING_LINES[line]:
        return "independent"
    return "embedded-with-escalation" if declared else "embedded-without-escalation"


def assignment_completeness(assignment):
    """Return (missing_attributes, completeness_fraction) for one assignment."""
    if not isinstance(assignment, dict):
        raise ValueError(
            "each assignment must be a mapping, got %r" % (type(assignment).__name__,)
        )
    missing = []
    for attribute in MANDATORY_ASSIGNMENT_ATTRIBUTES:
        if attribute not in assignment:
            missing.append(attribute)
            continue
        value = assignment[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_ASSIGNMENT_ATTRIBUTES)
    fraction = (total - len(missing)) / total
    return (tuple(missing), fraction)


def validate_unit(unit):
    """Return one validated declared unit record."""
    if not isinstance(unit, dict):
        raise ValueError("each unit must be a mapping")
    unit_id = validate_unit_id(unit.get("unit_id"))
    form = _require_text(unit.get("appointment_form"), "appointment_form").lower()
    appointed = appointment_is_recorded(form)
    state = independence_state(
        unit.get("reporting_line"),
        _require_bool(
            unit.get("escalation_route_declared", False), "escalation_route_declared"
        ),
    )
    return {
        "unit_id": unit_id,
        "appointment_form": form,
        "appointed": appointed,
        "independence": state,
    }


def evaluate_assignment(assignment, unit_index):
    """Return the disposition record of one declared activity assignment."""
    if not isinstance(unit_index, dict) or not unit_index:
        raise ValueError("unit_index must be a non-empty mapping of unit_id -> unit")
    missing, completeness = assignment_completeness(assignment)
    raw_label = assignment.get("assignment_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unnamed>"
    )
    record = {
        "assignment_id": label,
        "activity": None,
        "unit_id": None,
        "holder": None,
        "missing_attributes": missing,
        "completeness": completeness,
        "delegated": False,
        "disposition": "record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    unit_id = validate_unit_id(assignment["unit_id"])
    record["unit_id"] = unit_id
    if unit_id not in unit_index:
        record["disposition"] = "unknown-unit"
        return record

    activity = _require_text(assignment["activity"], "activity").lower()
    record["activity"] = activity
    if activity not in CONTROL_ACTIVITIES:
        record["disposition"] = "unknown-activity"
        return record

    record["holder"] = _require_text(assignment["holder"], "holder")
    delegated = _require_bool(assignment.get("delegated", False), "delegated")
    record["delegated"] = delegated

    if not unit_index[unit_id]["appointed"]:
        record["disposition"] = "unit-not-appointed"
        return record
    if delegated and activity in NON_DELEGABLE_ACTIVITIES:
        record["disposition"] = "non-delegable-activity-delegated"
        return record
    if not _require_bool(assignment.get("holder_qualified", True), "holder_qualified"):
        record["disposition"] = "holder-not-qualified"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def activity_ownership(records):
    """Return activity -> the distinct units holding it under an accepted record."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of assignment records")
    owners = {}
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] != _ACCEPTED:
            continue
        owners.setdefault(record["activity"], set()).add(record["unit_id"])
    return {activity: tuple(sorted(units)) for activity, units in owners.items()}


def activity_coverage(owners):
    """Return (coverage, unassigned, contested) over the mandated activities."""
    if not isinstance(owners, dict):
        raise ValueError("owners must be a mapping of activity -> owning units")
    total = sum(CONTROL_ACTIVITIES.values())
    covered = 0
    unassigned = []
    contested = []
    for activity, weight in CONTROL_ACTIVITIES.items():
        holders = owners.get(activity, ())
        if not holders:
            unassigned.append(activity)
        elif len(holders) > 1:
            contested.append(activity)
        else:
            covered += weight
    return (covered / total, tuple(sorted(unassigned)), tuple(sorted(contested)))


def holder_load(records):
    """Return holder -> the number of activities that holder owns outright."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of assignment records")
    load = {}
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] != _ACCEPTED:
            continue
        load[record["holder"]] = load.get(record["holder"], 0) + 1
    return load


def assess_parts_control_organization(spec):
    """Run the full clause 5.1.2.1 accountable-unit assessment.

    spec keys: units (sequence of unit mappings), assignments (sequence of
    activity assignment mappings), optional required_coverage (default 1.0)
    and max_activities_per_holder (default 4).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "assignments"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    units = spec["units"]
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("spec['units'] must be a non-empty sequence of unit mappings")
    unit_index = {}
    for unit in units:
        validated = validate_unit(unit)
        if validated["unit_id"] in unit_index:
            raise ValueError("unit %s is declared twice" % validated["unit_id"])
        unit_index[validated["unit_id"]] = validated

    assignments = spec["assignments"]
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("spec['assignments'] must be a sequence")

    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],)
        )
    cap = _require_positive_int(
        spec.get("max_activities_per_holder", 4), "max_activities_per_holder"
    )

    records = []
    seen_ids = set()
    for assignment in assignments:
        record = evaluate_assignment(assignment, unit_index)
        if record["assignment_id"] != "<unnamed>":
            if record["assignment_id"] in seen_ids:
                raise ValueError(
                    "assignment %s appears twice" % record["assignment_id"]
                )
            seen_ids.add(record["assignment_id"])
        records.append(record)

    owners = activity_ownership(records)
    coverage, unassigned, contested = activity_coverage(owners)
    load = holder_load(records)

    findings = []
    for record in records:
        if record["disposition"] == _ACCEPTED:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["disposition"], 9),
                "reference": record["assignment_id"],
                "disposition": record["disposition"],
                "detail": _finding_detail(record),
            }
        )
    for activity in contested:
        findings.append(
            {
                "severity": _SEVERITY["activity-contested"],
                "reference": activity,
                "disposition": "activity-contested",
                "detail": "two units are named for this activity, so neither is accountable",
            }
        )
    for activity in unassigned:
        findings.append(
            {
                "severity": _SEVERITY["activity-unassigned"],
                "reference": activity,
                "disposition": "activity-unassigned",
                "detail": "no appointed unit was named for this control activity",
            }
        )

    owning_units = sorted({u for holders in owners.values() for u in holders})
    embedded_without_route = tuple(
        unit_id
        for unit_id in owning_units
        if unit_index[unit_id]["independence"] == "embedded-without-escalation"
    )
    for unit_id in embedded_without_route:
        findings.append(
            {
                "severity": _SEVERITY["escalation-route-absent"],
                "reference": unit_id,
                "disposition": "escalation-route-absent",
                "detail": "unit reports inside the design authority with no declared escalation route",
            }
        )

    overloaded = tuple(sorted(name for name, count in load.items() if count > cap))
    for name in overloaded:
        findings.append(
            {
                "severity": _SEVERITY["holder-overloaded"],
                "reference": name,
                "disposition": "holder-overloaded",
                "detail": "one holder carries %d activities against a cap of %d"
                % (load[name], cap),
            }
        )

    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    constituted = meets and not findings
    return {
        "units": tuple(sorted(unit_index)),
        "records": records,
        "ownership": owners,
        "activity_coverage": coverage,
        "required_coverage": required,
        "unassigned_activities": unassigned,
        "contested_activities": contested,
        "holder_load": load,
        "overloaded_holders": overloaded,
        "units_without_escalation_route": embedded_without_route,
        "findings": findings,
        "accountable": constituted,
        "verdict": "unit accountable" if constituted else "accountability not established",
    }


def _finding_detail(record):
    """Return the human-readable reason one assignment is not an ownership."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "assignment lacks %s; it cannot be disposed of" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "unknown-unit":
        return "assignment names a unit that was never declared"
    if disposition == "unknown-activity":
        return "assignment names an activity outside the mandated control set"
    if disposition == "unit-not-appointed":
        return "the named unit has no appointment recorded in a form that stands"
    if disposition == "non-delegable-activity-delegated":
        return "a duty the named unit must exercise itself was handed to another unit"
    if disposition == "holder-not-qualified":
        return "the named holder is not qualified for the activity placed with them"
    return "assignment is not an accepted ownership"
