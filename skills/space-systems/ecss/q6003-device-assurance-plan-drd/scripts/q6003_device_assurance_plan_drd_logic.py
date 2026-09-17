"""Device-development product assurance plan DRD evaluation.

Anchor: ECSS-Q-ST-60-03C Annex A (the document requirements definition
that fixes the content a product assurance plan for a device development
has to carry). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Read the drafted plan as section key -> section body and refuse a
   section that is present but empty. A heading with nothing behind it
   is a placeholder, not a procedure, and the DRD asks for the content.
2. Check every assurance function the plan has to cover is owned by a
   role that the plan's organisation section actually defines. An
   unowned function is a gap even when the function is discussed.
3. Check every declared development milestone carries at least one
   planned assurance activity, and that each activity's owner is one of
   the defined roles rather than a name that appears nowhere else.
4. Resolve every deliverable item the plan owes to the milestone that
   issues it; a deliverable issued at a milestone the plan never
   declared is a dangling commitment.
5. Aggregate the four checks into one verdict, naming every gap rather
   than stopping at the first, because a plan is reworked once.
"""

__all__ = [
    "REQUIRED_PLAN_SECTIONS",
    "ASSURANCE_FUNCTIONS",
    "REQUIRED_DELIVERABLES",
    "missing_plan_sections",
    "unowned_assurance_functions",
    "milestones_without_activities",
    "activities_with_unknown_owner",
    "dangling_deliverables",
    "assess_device_assurance_plan_drd",
]

# The content blocks Annex A expects a device-development assurance plan
# to carry, in the order the DRD lists them.
REQUIRED_PLAN_SECTIONS = (
    "introduction",
    "applicable-and-reference-documents",
    "organisation-and-responsibilities",
    "development-flow-and-milestones",
    "design-and-verification-assurance",
    "part-and-material-selection",
    "nonconformance-and-alert-handling",
    "reuse-and-heritage-policy",
    "deliverable-items-and-records",
)

# The assurance functions the plan has to place under a named owner.
ASSURANCE_FUNCTIONS = (
    "design-authority",
    "product-assurance",
    "verification-and-validation",
    "configuration-management",
    "procurement-and-supplier-control",
    "customer-interface",
)

# The records the plan commits to issue during the device development.
REQUIRED_DELIVERABLES = (
    "device-assurance-plan",
    "device-assurance-report",
    "device-reuse-file",
    "device-verification-record",
    "device-nonconformance-register",
)


def _nonempty_text(label, value):
    """Return a stripped non-empty string, raising on anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    """Return a list copy of a sequence argument, raising on anything else."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, value))
    return list(value)


def missing_plan_sections(plan):
    """Return the required plan sections that are absent or blank.

    plan maps a section key to its body text. A body that is not a string,
    or that is blank once stripped, counts as absent because the DRD asks
    for content and not for a heading. Returns the missing keys in the
    DRD's own order. Raises ValueError when plan is not a mapping.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of section key to body, got %r" % (plan,))
    missing = []
    for key in REQUIRED_PLAN_SECTIONS:
        body = plan.get(key)
        if not isinstance(body, str) or not body.strip():
            missing.append(key)
    return missing


def unowned_assurance_functions(roles):
    """Return the assurance functions no declared role owns.

    roles is a non-empty sequence of mappings with a 'role' name and a
    'functions' list drawn from ASSURANCE_FUNCTIONS (matched without
    regard to case or surrounding space). Returns the uncovered functions
    in the order ASSURANCE_FUNCTIONS declares them. Raises ValueError on a
    malformed entry or on a function name outside the known set, because
    a silently ignored name is how a gap survives review.
    """
    entries = _sequence("roles", roles)
    if not entries:
        raise ValueError("roles must name at least one role")
    covered = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("roles[%d] must be a mapping, got %r" % (index, entry))
        for key in ("role", "functions"):
            if key not in entry:
                raise ValueError("roles[%d] is missing required key '%s'" % (index, key))
        _nonempty_text("roles[%d]['role']" % index, entry["role"])
        for name in _sequence("roles[%d]['functions']" % index, entry["functions"]):
            if not isinstance(name, str):
                raise ValueError("roles[%d] function names must be strings" % index)
            key = name.strip().lower()
            if key not in ASSURANCE_FUNCTIONS:
                raise ValueError(
                    "unknown assurance function %r; expected one of %s"
                    % (name, ", ".join(ASSURANCE_FUNCTIONS))
                )
            covered.add(key)
    return [f for f in ASSURANCE_FUNCTIONS if f not in covered]


def _declared_roles(roles):
    """Return the set of role names a well-formed roles sequence declares."""
    names = set()
    for entry in _sequence("roles", roles):
        if isinstance(entry, dict) and isinstance(entry.get("role"), str):
            names.add(entry["role"].strip())
    return names


def milestones_without_activities(milestones, activities):
    """Return declared milestones carrying no planned assurance activity.

    milestones is a non-empty sequence of milestone identifiers.
    activities is a sequence of mappings each carrying 'activity_id',
    'milestone' and 'owner_role'. Returns the milestone identifiers that
    no activity is attached to, in the order they were declared. Raises
    ValueError on a duplicate milestone or a malformed activity, since
    both make the coverage count meaningless.
    """
    names = []
    for index, name in enumerate(_sequence("milestones", milestones)):
        label = _nonempty_text("milestones[%d]" % index, name)
        if label in names:
            raise ValueError("milestone %r is declared more than once" % label)
        names.append(label)
    if not names:
        raise ValueError("milestones must declare at least one milestone")
    attached = set()
    for index, entry in enumerate(_sequence("activities", activities)):
        if not isinstance(entry, dict):
            raise ValueError("activities[%d] must be a mapping, got %r" % (index, entry))
        for key in ("activity_id", "milestone", "owner_role"):
            if key not in entry:
                raise ValueError("activities[%d] is missing required key '%s'" % (index, key))
        _nonempty_text("activities[%d]['activity_id']" % index, entry["activity_id"])
        milestone = _nonempty_text("activities[%d]['milestone']" % index, entry["milestone"])
        if milestone not in names:
            raise ValueError(
                "activity %r is attached to milestone %r, which the plan never declares"
                % (entry["activity_id"], milestone)
            )
        attached.add(milestone)
    return [name for name in names if name not in attached]


def activities_with_unknown_owner(activities, roles):
    """Return activity identifiers whose owner is not a declared role.

    The owner is matched against the role names the organisation section
    declares. Returns the offending identifiers in input order. Raises
    ValueError on a malformed activity entry.
    """
    known = _declared_roles(roles)
    unknown = []
    for index, entry in enumerate(_sequence("activities", activities)):
        if not isinstance(entry, dict):
            raise ValueError("activities[%d] must be a mapping, got %r" % (index, entry))
        for key in ("activity_id", "owner_role"):
            if key not in entry:
                raise ValueError("activities[%d] is missing required key '%s'" % (index, key))
        activity_id = _nonempty_text("activities[%d]['activity_id']" % index, entry["activity_id"])
        owner = _nonempty_text("activities[%d]['owner_role']" % index, entry["owner_role"])
        if owner not in known:
            unknown.append(activity_id)
    return unknown


def dangling_deliverables(deliverables, milestones):
    """Return the deliverable record for a plan's declared deliverable list.

    deliverables is a sequence of mappings with 'item' and
    'issued_at_milestone'. Returns a mapping with 'missing' (required
    items the plan never commits to), 'duplicated' (items committed twice,
    which leaves two issue points for one record) and 'unknown_milestone'
    (items issued at a milestone the plan never declared). Raises
    ValueError on a malformed entry.
    """
    declared_milestones = set()
    for index, name in enumerate(_sequence("milestones", milestones)):
        declared_milestones.add(_nonempty_text("milestones[%d]" % index, name))
    seen = []
    duplicated = []
    unknown_milestone = []
    for index, entry in enumerate(_sequence("deliverables", deliverables)):
        if not isinstance(entry, dict):
            raise ValueError("deliverables[%d] must be a mapping, got %r" % (index, entry))
        for key in ("item", "issued_at_milestone"):
            if key not in entry:
                raise ValueError("deliverables[%d] is missing required key '%s'" % (index, key))
        item = _nonempty_text("deliverables[%d]['item']" % index, entry["item"])
        milestone = _nonempty_text(
            "deliverables[%d]['issued_at_milestone']" % index, entry["issued_at_milestone"]
        )
        if item in seen:
            if item not in duplicated:
                duplicated.append(item)
        else:
            seen.append(item)
        if milestone not in declared_milestones and item not in unknown_milestone:
            unknown_milestone.append(item)
    return {
        "declared": seen,
        "missing": [item for item in REQUIRED_DELIVERABLES if item not in seen],
        "duplicated": duplicated,
        "unknown_milestone": unknown_milestone,
    }


def assess_device_assurance_plan_drd(spec):
    """Return the aggregate Annex A verdict for a drafted assurance plan.

    spec keys: plan (section key -> body), roles, milestones, activities
    and deliverables. Returns a mapping carrying every individual finding
    list, a flat 'findings' list naming each gap, and a 'disposition' of
    'plan-drd-compliant' or 'plan-drd-rework'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    for key in ("plan", "roles", "milestones", "activities", "deliverables"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    missing_sections = missing_plan_sections(spec["plan"])
    unowned = unowned_assurance_functions(spec["roles"])
    uncovered_milestones = milestones_without_activities(
        spec["milestones"], spec["activities"]
    )
    unknown_owners = activities_with_unknown_owner(spec["activities"], spec["roles"])
    deliverable_record = dangling_deliverables(spec["deliverables"], spec["milestones"])
    findings = []
    for key in missing_sections:
        findings.append("required plan section '%s' is absent or blank" % key)
    for function in unowned:
        findings.append("assurance function '%s' has no owning role" % function)
    for milestone in uncovered_milestones:
        findings.append("milestone '%s' carries no planned assurance activity" % milestone)
    for activity_id in unknown_owners:
        findings.append("activity '%s' is owned by a role the plan never declares" % activity_id)
    for item in deliverable_record["missing"]:
        findings.append("deliverable '%s' is never committed to a milestone" % item)
    for item in deliverable_record["duplicated"]:
        findings.append("deliverable '%s' is committed at more than one milestone" % item)
    for item in deliverable_record["unknown_milestone"]:
        findings.append("deliverable '%s' is issued at an undeclared milestone" % item)
    compliant = not findings
    return {
        "missing_sections": missing_sections,
        "unowned_functions": unowned,
        "milestones_without_activities": uncovered_milestones,
        "activities_with_unknown_owner": unknown_owners,
        "deliverables": deliverable_record,
        "findings": findings,
        "compliant": compliant,
        "disposition": "plan-drd-compliant" if compliant else "plan-drd-rework",
    }
