#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.1 SE management assessment (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering (SE) function of a project runs a defined set of SE
activities, each of which must have a single responsible role assigned
per the System Engineering Plan (SEP), and each of which may require a
recorded interface to another project function (project management,
product assurance, an engineering discipline, or the customer) before
it is considered under control. Each activity also carries a status
(planned, in progress, complete, or blocked) that must be internally
consistent: a blocked activity records why, and a completed activity
does not depend on another activity that is not itself complete. This
module implements activity-kind categorization, responsibility
assignment checking, required-interface coverage checking, and status
consistency checking, and aggregates the three into a per-activity and
per-program SE management review; it does not define the SEP's actual
role list or interface set for a given project, which is
project-specific and supplied by the caller.
"""

SE_ACTIVITY_KINDS = frozenset(
    {
        "technical_management",
        "requirements_engineering",
        "analysis",
        "design_definition",
        "verification",
        "product_assurance_interface",
        "risk_management",
    }
)

VALID_ROLES = frozenset(
    {
        "se_manager",
        "lead_engineer",
        "subsystem_engineer",
        "product_assurance_engineer",
        "project_manager",
        "customer_representative",
    }
)

VALID_STATUSES = frozenset({"planned", "in_progress", "complete", "blocked"})

VALID_EXTERNAL_FUNCTIONS = frozenset(
    {"project_management", "product_assurance", "engineering_discipline", "customer"}
)

# The external project functions each SE activity kind must interface
# with per the SEP, before that activity is considered under control.
REQUIRED_INTERFACES = {
    "technical_management": frozenset({"project_management"}),
    "requirements_engineering": frozenset({"customer"}),
    "analysis": frozenset(),
    "design_definition": frozenset({"engineering_discipline"}),
    "verification": frozenset({"product_assurance"}),
    "product_assurance_interface": frozenset({"product_assurance"}),
    "risk_management": frozenset({"project_management"}),
}


def classify_activity_kind(kind):
    """The recognized SE activity kind for an activity's declared kind.
    Raises ValueError for a kind outside SE_ACTIVITY_KINDS."""
    if kind not in SE_ACTIVITY_KINDS:
        raise ValueError(
            "unrecognized SE activity kind %r under E-ST-10C clause 5.6.1" % (kind,)
        )
    return kind


def responsibility_findings(activity):
    """Finding list (empty if fine) for an activity's SEP responsibility
    assignment. An activity with no owner is flagged as unassigned.
    Raises ValueError if an owner is present but not a recognized SEP
    role."""
    owner = activity.get("owner")
    if not owner:
        return [
            {
                "issue": "unassigned_responsibility",
                "activity": activity["id"],
            }
        ]
    if owner not in VALID_ROLES:
        raise ValueError("unrecognized responsible role %r" % (owner,))
    return []


def interface_coverage_findings(activity):
    """Finding list (empty if fine) for the required-interface coverage
    of one activity. activity["interfaces"] is an iterable of dicts
    each carrying a "counterpart" key. Raises ValueError for an
    unrecognized activity kind or an unrecognized interface
    counterpart."""
    kind = classify_activity_kind(activity["kind"])
    required = REQUIRED_INTERFACES[kind]
    present = set()
    for interface in activity.get("interfaces", []):
        counterpart = interface["counterpart"]
        if counterpart not in VALID_EXTERNAL_FUNCTIONS:
            raise ValueError("unrecognized interface counterpart %r" % (counterpart,))
        present.add(counterpart)
    missing = sorted(required - present)
    return [
        {
            "issue": "missing_required_interface",
            "activity": activity["id"],
            "counterpart": counterpart,
        }
        for counterpart in missing
    ]


def status_findings(activity, activities_by_id):
    """Finding list (empty if fine) for one activity's status
    consistency: a blocked activity must record a blocking_reason, and
    a complete activity must not depend on an activity that is not
    itself complete. Raises ValueError for an unrecognized status or a
    dependency id absent from activities_by_id."""
    status = activity.get("status")
    if status not in VALID_STATUSES:
        raise ValueError("unrecognized activity status %r" % (status,))
    findings = []
    if status == "blocked" and not activity.get("blocking_reason"):
        findings.append(
            {"issue": "blocked_without_reason", "activity": activity["id"]}
        )
    if status == "complete":
        for dep_id in activity.get("depends_on", []):
            dependency = activities_by_id.get(dep_id)
            if dependency is None:
                raise ValueError("unknown dependency id %r" % (dep_id,))
            if dependency.get("status") != "complete":
                findings.append(
                    {
                        "issue": "incomplete_dependency",
                        "activity": activity["id"],
                        "dependency": dep_id,
                    }
                )
    return findings


def se_management_review(activity, activities_by_id):
    """Full clause 5.6.1 SE management review for one activity.

    activity: {"id": str, "kind": str, "owner": str | None,
    "interfaces": [{"counterpart": str}, ...], "status": str,
    "blocking_reason": str | None, "depends_on": [str, ...]}.
    activities_by_id: every activity in the program, keyed by "id",
    used to resolve depends_on references. Returns {"responsibility":
    [...], "interface": [...], "status": [...]}, each a finding list.
    Raises ValueError for an unrecognized kind, role, interface
    counterpart, status, or dependency id."""
    return {
        "responsibility": responsibility_findings(activity),
        "interface": interface_coverage_findings(activity),
        "status": status_findings(activity, activities_by_id),
    }


def is_se_management_compliant(review):
    """True when every category in a se_management_review result is
    empty -- the activity is under SE management control per clause
    5.6.1 for this assessment."""
    return all(len(findings) == 0 for findings in review.values())


def se_management_program_review(activities):
    """SE management review for every activity in a program.

    activities: iterable of activity dicts (see se_management_review).
    Returns a dict mapping activity id to its review. Raises ValueError
    for a duplicate activity id or any per-activity error raised by
    se_management_review."""
    activities_by_id = {}
    for activity in activities:
        activity_id = activity["id"]
        if activity_id in activities_by_id:
            raise ValueError("duplicate activity id %r" % (activity_id,))
        activities_by_id[activity_id] = activity
    return {
        activity_id: se_management_review(activity, activities_by_id)
        for activity_id, activity in activities_by_id.items()
    }


def is_program_compliant(program_review):
    """True when every activity's review in a se_management_program_review
    result is compliant."""
    return all(
        is_se_management_compliant(review) for review in program_review.values()
    )
