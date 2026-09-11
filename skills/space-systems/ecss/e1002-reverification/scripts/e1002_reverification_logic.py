#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.4.3 re-verification trigger and scope assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system verification standard's re-verification clause identifies four
classes of events that mandate a formal re-assessment of previously
accepted verification evidence -- design changes to the item or its
interfaces, storage beyond the qualified duration or under non-standard
conditions, re-flight of hardware that has been previously flown, and
anomalies observed during testing, storage, or in-service operation.
For each event the clause requires the responsible engineer to categorize
the trigger, determine the minimum scope of re-verification activities,
document which activities were completed, and confirm the item re-enters
the verified database only after all required activities are closed. This
module implements trigger categorization, scope-level derivation,
required-activity enumeration, coverage checking, and the compliant-or-not
assessment; it does not implement the underlying verification methods
themselves (analysis, test, inspection) or the formal waiver approval
process for scope reductions.
"""

KNOWN_TRIGGERS = {
    "design_change_minor": "design_change",
    "design_change_major": "design_change",
    "storage_within_limit": "storage",
    "storage_beyond_limit": "storage",
    "re_flight": "re_flight",
    "anomaly_test": "anomaly",
    "anomaly_operation": "anomaly",
    "anomaly_storage": "anomaly",
}

SCOPE_REQUIRED_ACTIVITIES = {
    "inspection_only": frozenset(["inspection", "documentation_review"]),
    "limited": frozenset(["inspection", "functional_test", "documentation_review"]),
    "delta": frozenset([
        "inspection",
        "delta_qualification",
        "functional_test",
        "documentation_review",
    ]),
    "delta_with_similarity": frozenset([
        "inspection",
        "similarity_assessment",
        "functional_test",
        "documentation_review",
    ]),
    "full": frozenset([
        "inspection",
        "structural_analysis",
        "thermal_analysis",
        "functional_test",
        "environmental_test",
        "documentation_review",
    ]),
    "anomaly": frozenset([
        "anomaly_investigation",
        "inspection",
        "functional_test",
        "documentation_review",
    ]),
}

TRIGGER_SCOPE_MAP = {
    "design_change_minor": "delta",
    "design_change_major": "full",
    "storage_within_limit": "inspection_only",
    "storage_beyond_limit": "limited",
    "re_flight": "delta_with_similarity",
    "anomaly_test": "anomaly",
    "anomaly_operation": "anomaly",
    "anomaly_storage": "anomaly",
}


def categorize_trigger(trigger_type):
    """Trigger category for a trigger_type string: "design_change",
    "storage", "re_flight", or "anomaly".
    Raises ValueError for an unrecognized trigger_type."""
    if trigger_type not in KNOWN_TRIGGERS:
        raise ValueError(
            "unrecognized re-verification trigger type %r under "
            "ECSS-E-ST-10C §5.4.3" % (trigger_type,)
        )
    return KNOWN_TRIGGERS[trigger_type]


def scope_level_for_trigger(trigger_type):
    """Minimum re-verification scope level for a trigger_type.
    Returns one of: "inspection_only", "limited", "delta",
    "delta_with_similarity", "full", "anomaly".
    Raises ValueError for an unrecognized trigger_type."""
    if trigger_type not in TRIGGER_SCOPE_MAP:
        raise ValueError(
            "unrecognized re-verification trigger type %r under "
            "ECSS-E-ST-10C §5.4.3" % (trigger_type,)
        )
    return TRIGGER_SCOPE_MAP[trigger_type]


def required_activities(scope_level):
    """Frozenset of activity identifiers required for a given scope_level.
    Raises ValueError for an unrecognized scope_level."""
    if scope_level not in SCOPE_REQUIRED_ACTIVITIES:
        raise ValueError(
            "unrecognized re-verification scope level %r" % (scope_level,)
        )
    return SCOPE_REQUIRED_ACTIVITIES[scope_level]


def missing_activities(scope_level, documented_activities):
    """Sorted list of activity identifiers required by scope_level but
    absent from documented_activities (iterable). Empty list means all
    required activities are covered. Raises ValueError for an unrecognized
    scope_level. Does not mutate documented_activities."""
    required = required_activities(scope_level)
    documented = frozenset(documented_activities)
    return sorted(required - documented)


def assess_reverification_item(item):
    """Full §5.4.3 re-verification assessment for one item.

    item: {
        "item_id": str,
        "trigger_type": str,            one of KNOWN_TRIGGERS
        "documented_activities": list[str],
        "waiver_on_record": bool,       True if a formal scope-reduction
                                        waiver has been accepted
    }
    Returns {
        "item_id": str,
        "trigger_category": str,
        "scope_level": str,
        "missing": list[str],           empty when complete
        "findings": list[dict],
    }
    Raises ValueError for an unrecognized trigger_type.
    """
    item_id = item["item_id"]
    trigger_type = item["trigger_type"]
    documented = item.get("documented_activities", [])
    waiver = item.get("waiver_on_record", False)

    trigger_category = categorize_trigger(trigger_type)
    scope = scope_level_for_trigger(trigger_type)
    gap = missing_activities(scope, documented)

    findings = []
    if gap and not waiver:
        findings.append({
            "issue": "incomplete_reverification_scope",
            "item": item_id,
            "scope_level": scope,
            "missing_activities": gap,
        })
    elif gap and waiver:
        findings.append({
            "issue": "scope_reduced_by_waiver",
            "item": item_id,
            "scope_level": scope,
            "waived_activities": gap,
        })

    return {
        "item_id": item_id,
        "trigger_category": trigger_category,
        "scope_level": scope,
        "missing": gap,
        "findings": findings,
    }


def is_reverification_complete(assessment):
    """True when the re-verification scope is fully covered with no open
    incomplete-scope findings. An item with a waiver-covered scope reduction
    is treated as complete for gate purposes."""
    for finding in assessment.get("findings", []):
        if finding.get("issue") == "incomplete_reverification_scope":
            return False
    return True
