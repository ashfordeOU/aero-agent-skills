#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.8 requirement maintenance under
configuration control (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard requires that a
requirement be maintained under configuration control once it is
baselined -- a baselined requirement's content changes only alongside
an approved change request -- and that every such change have its
impact assessed against the requirements derived from it (via the
parent-child traceability link) and against the verification items
linked to it, with both the impact assessment and the change itself
recorded. This module implements the requirement lifecycle transition
check, the configuration-control gate, the derived-requirement and
verification-item impact lookup, and the impact-assessment and
maintenance-record presence checks; it does not define the
traceability or verification data model itself, only how a change is
evaluated against it.
"""

STATES = frozenset({"draft", "proposed", "baselined", "obsolete"})

# Allowed next states for a lifecycle transition. "obsolete" is terminal.
ALLOWED_TRANSITIONS = {
    "draft": frozenset({"proposed", "obsolete"}),
    "proposed": frozenset({"draft", "baselined", "obsolete"}),
    "baselined": frozenset({"obsolete"}),
    "obsolete": frozenset(),
}


def _check_known_state(state):
    if state not in STATES:
        raise ValueError(
            "unrecognized requirement lifecycle state %r under "
            "E-ST-10C clause 5.2.3.8" % (state,)
        )


def validate_state_transition(current_state, target_state):
    """True if current_state -> target_state is an allowed lifecycle
    transition. Raises ValueError if either state is unrecognized or
    the transition is not on the allowed list."""
    _check_known_state(current_state)
    _check_known_state(target_state)
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise ValueError(
            "disallowed requirement lifecycle transition from %r to "
            "%r under E-ST-10C clause 5.2.3.8" % (current_state, target_state)
        )
    return True


def requires_change_control(requirement_state):
    """True when a requirement in this state may only be modified
    alongside an approved change request."""
    _check_known_state(requirement_state)
    return requirement_state == "baselined"


def configuration_control_violations(
    requirement_id, requirement_state, is_being_modified, has_approved_change_request
):
    """Violation list (empty if compliant) for the configuration-
    control gate on one requirement change."""
    if (
        is_being_modified
        and requires_change_control(requirement_state)
        and not has_approved_change_request
    ):
        return [
            {
                "issue": "change_without_configuration_control",
                "requirement": requirement_id,
                "state": requirement_state,
            }
        ]
    return []


def derived_requirement_impact(requirement_id, trace_links):
    """Sorted list of derived (child) requirement ids impacted by a
    change to requirement_id. trace_links: dict mapping a parent
    requirement id to an iterable of derived requirement ids. Returns
    an empty list if requirement_id has no recorded children."""
    return sorted(trace_links.get(requirement_id, []))


def verification_impact(requirement_id, verification_links):
    """Sorted list of verification item ids impacted by a change to
    requirement_id. verification_links: dict mapping a requirement id
    to an iterable of linked verification item ids."""
    return sorted(verification_links.get(requirement_id, []))


def change_impact_assessment(requirement_id, trace_links, verification_links):
    """The full change-impact lookup for one requirement: its derived
    requirements and its linked verification items. Does not mutate
    trace_links or verification_links."""
    return {
        "derived_requirements": derived_requirement_impact(requirement_id, trace_links),
        "verification_items": verification_impact(requirement_id, verification_links),
    }


def impact_assessment_violations(requirement_id, impact, assessment_recorded):
    """Violation list (empty if compliant) for the impact-assessment
    record. impact: result of change_impact_assessment. Flags a
    missing assessment only when there is real impact (a nonempty
    derived-requirements or verification-items list); a requirement
    with no impact needs no assessment record."""
    has_impact = bool(impact["derived_requirements"]) or bool(impact["verification_items"])
    if has_impact and not assessment_recorded:
        return [
            {
                "issue": "missing_change_impact_assessment",
                "requirement": requirement_id,
                "derived_requirements": impact["derived_requirements"],
                "verification_items": impact["verification_items"],
            }
        ]
    return []


def maintenance_record_violations(
    requirement_id, requirement_state, is_being_modified, has_maintenance_record
):
    """Violation list (empty if compliant) for the maintenance
    (change-history) record on a baselined requirement under
    modification."""
    if (
        is_being_modified
        and requirement_state == "baselined"
        and not has_maintenance_record
    ):
        return [
            {
                "issue": "missing_maintenance_record",
                "requirement": requirement_id,
            }
        ]
    return []


def requirement_maintenance_review(change):
    """Full clause 5.2.3.8 maintenance review for one requirement
    change.

    change: {"requirement_id": str, "state": str, "is_being_modified":
    bool, "has_approved_change_request": bool, "has_maintenance_record":
    bool, "assessment_recorded": bool, "trace_links": {parent_id:
    [child_id, ...]}, "verification_links": {requirement_id:
    [verification_item_id, ...]}}. trace_links and verification_links
    default to empty dicts when absent. Returns {"configuration_control":
    [...], "impact_assessment": [...], "maintenance_record": [...]},
    each a violation list. Raises ValueError for an unrecognized state."""
    requirement_id = change["requirement_id"]
    state = change["state"]
    _check_known_state(state)
    is_being_modified = change.get("is_being_modified", False)
    impact = change_impact_assessment(
        requirement_id,
        change.get("trace_links", {}),
        change.get("verification_links", {}),
    )
    return {
        "configuration_control": configuration_control_violations(
            requirement_id,
            state,
            is_being_modified,
            change.get("has_approved_change_request", False),
        ),
        "impact_assessment": impact_assessment_violations(
            requirement_id, impact, change.get("assessment_recorded", False)
        ),
        "maintenance_record": maintenance_record_violations(
            requirement_id, state, is_being_modified, change.get("has_maintenance_record", False)
        ),
    }


def is_maintenance_compliant(review):
    """True when every category in a requirement_maintenance_review
    result is empty -- the change satisfies clause 5.2.3.8."""
    return all(len(violations) == 0 for violations in review.values())
