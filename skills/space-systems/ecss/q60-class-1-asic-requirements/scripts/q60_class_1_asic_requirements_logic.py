"""Routing a class 1 ASIC to the dedicated development standard.

Anchor: ECSS-Q-ST-60C clause 4.6.2 (a class 1 application specific integrated
circuit is developed and reused under the dedicated ASIC and FPGA development
standard, ECSS-Q-ST-60-02, rather than under the general component rules).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the procurement case: the part, the declared route, the heritage
   the reuse claim leans on and the evidence references behind it.
2. Compare the candidate build against the qualified heritage axis by axis and
   group the differences into silicon, design and assembly changes.
3. Check the evidence a reuse claim needs is actually referenced.
4. Check the qualification is still current and that production never stopped.
5. Route the part into the dedicated standard: a full development flow, a
   delta qualification, or a reuse flow, and return the activity set that
   route carries.
"""

__all__ = [
    "SILICON_AXES",
    "DESIGN_AXES",
    "ASSEMBLY_AXES",
    "HERITAGE_AXES",
    "REQUIRED_REUSE_EVIDENCE",
    "DEFAULT_ROUTING_POLICY",
    "FULL_DEVELOPMENT",
    "DELTA_QUALIFICATION",
    "REUSE_ROUTE",
    "HERITAGE_EVIDENCE_INCOMPLETE",
    "ACTIVITY_SETS",
    "validate_routing_policy",
    "validate_heritage",
    "validate_case",
    "changed_axes",
    "group_changed_axes",
    "heritage_delta_index",
    "missing_reuse_evidence",
    "qualification_is_current",
    "activity_set_for_route",
    "route_asic_requirements",
]

# The three ways an ASIC build can differ from the one that was qualified.
# Silicon and design changes invalidate the electrical and functional evidence;
# an assembly change leaves the die alone and touches the package evidence.
SILICON_AXES = ("foundry", "process_node_nm", "mask_set_revision")
DESIGN_AXES = ("design_database_version", "functional_scope")
ASSEMBLY_AXES = ("package_type", "die_attach_process")
HERITAGE_AXES = SILICON_AXES + DESIGN_AXES + ASSEMBLY_AXES

REQUIRED_REUSE_EVIDENCE = (
    "qualification_report",
    "radiation_evaluation",
    "lot_acceptance_data",
)

FULL_DEVELOPMENT = "dedicated-asic-standard-full-development"
DELTA_QUALIFICATION = "dedicated-asic-standard-delta-qualification"
REUSE_ROUTE = "dedicated-asic-standard-reuse-route"
HERITAGE_EVIDENCE_INCOMPLETE = "heritage-evidence-incomplete"

# What each route carries once the part is inside the dedicated standard.
ACTIVITY_SETS = {
    FULL_DEVELOPMENT: (
        "design-flow-review",
        "prototype-validation",
        "radiation-evaluation",
        "qualification-testing",
        "lot-acceptance-testing",
    ),
    DELTA_QUALIFICATION: (
        "change-impact-review",
        "delta-qualification-testing",
        "lot-acceptance-testing",
    ),
    REUSE_ROUTE: (
        "heritage-evidence-review",
        "lot-acceptance-testing",
    ),
    HERITAGE_EVIDENCE_INCOMPLETE: (),
}

_DECLARED_ROUTES = ("new-development", "reuse", "re-target")

DEFAULT_ROUTING_POLICY = {
    # How long a qualification stands before the evidence has to be refreshed.
    "max_qualification_age_months": 60,
    # Whether a break in production forces a delta qualification.
    "production_break_forces_delta": True,
    # Whether an assembly-only change may stay on the reuse route.
    "assembly_change_stays_on_reuse": False,
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_routing_policy(policy=None):
    """Return a complete routing policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_ROUTING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("routing policy must be a mapping")
    merged = dict(DEFAULT_ROUTING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_ROUTING_POLICY:
            raise ValueError("unknown routing policy key %r" % (key,))
        merged[key] = value
    if not _is_int(merged["max_qualification_age_months"]):
        raise ValueError("max_qualification_age_months must be an integer")
    if merged["max_qualification_age_months"] <= 0:
        raise ValueError("max_qualification_age_months must be positive")
    for key in ("production_break_forces_delta", "assembly_change_stays_on_reuse"):
        if not isinstance(merged[key], bool):
            raise ValueError("%s must be a boolean" % key)
    return merged


def validate_heritage(heritage, label):
    """Return a normalised heritage record covering every axis."""
    if not isinstance(heritage, dict):
        raise ValueError("%s heritage must be a mapping" % label)
    record = {}
    for axis in HERITAGE_AXES:
        value = heritage.get(axis)
        if _is_int(value):
            if value <= 0:
                raise ValueError("%s heritage axis %r must be positive" % (label, axis))
            record[axis] = value
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "%s heritage carries no %r; the axis cannot be compared and the "
                "route cannot be decided" % (label, axis)
            )
        record[axis] = value.strip()
    unknown = set(heritage) - set(HERITAGE_AXES)
    if unknown:
        raise ValueError(
            "%s heritage carries unknown axis %s" % (label, ", ".join(sorted(unknown)))
        )
    return record


def validate_case(case):
    """Return a normalised procurement case for an ASIC."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    part = case.get("part_id")
    if not isinstance(part, str) or not part.strip():
        raise ValueError("case needs a non-empty 'part_id'")
    route = case.get("declared_route")
    if route not in _DECLARED_ROUTES:
        raise ValueError(
            "declared_route must be one of %s, got %r" % (", ".join(_DECLARED_ROUTES), route)
        )
    record = {"part_id": part.strip(), "declared_route": route}
    if route == "new-development":
        if case.get("candidate") is not None:
            record["candidate"] = validate_heritage(case["candidate"], "candidate")
        record["qualified"] = None
        record.setdefault("candidate", None)
    else:
        if "candidate" not in case or "qualified" not in case:
            raise ValueError(
                "a %r case needs both a 'candidate' and a 'qualified' heritage" % (route,)
            )
        record["candidate"] = validate_heritage(case["candidate"], "candidate")
        record["qualified"] = validate_heritage(case["qualified"], "qualified")
    evidence = case.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping of reference name to reference")
    cleaned = {}
    for key, value in evidence.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("every evidence entry needs a non-empty name")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("evidence %r carries no reference" % (key,))
        cleaned[key.strip()] = value.strip()
    record["evidence"] = cleaned
    age = case.get("qualification_age_months", 0)
    if not _is_int(age) or age < 0:
        raise ValueError("qualification_age_months must be a non-negative integer")
    record["qualification_age_months"] = age
    broken = case.get("production_break", False)
    if not isinstance(broken, bool):
        raise ValueError("production_break must be a boolean")
    record["production_break"] = broken
    return record


def changed_axes(candidate, qualified):
    """Return the heritage axes on which the candidate differs from the qualified build."""
    if candidate is None or qualified is None:
        raise ValueError("both heritage records are needed to compare axes")
    left = validate_heritage(candidate, "candidate") if set(candidate) != set(HERITAGE_AXES) else candidate
    right = validate_heritage(qualified, "qualified") if set(qualified) != set(HERITAGE_AXES) else qualified
    return [axis for axis in HERITAGE_AXES if left[axis] != right[axis]]


def group_changed_axes(axes):
    """Return the changed axes grouped into silicon, design and assembly."""
    if not isinstance(axes, (list, tuple)):
        raise ValueError("axes must be a sequence")
    grouped = {"silicon": [], "design": [], "assembly": []}
    for axis in axes:
        if axis in SILICON_AXES:
            grouped["silicon"].append(axis)
        elif axis in DESIGN_AXES:
            grouped["design"].append(axis)
        elif axis in ASSEMBLY_AXES:
            grouped["assembly"].append(axis)
        else:
            raise ValueError("unknown heritage axis %r" % (axis,))
    return grouped


def heritage_delta_index(axes):
    """Return the share of the heritage axes that moved."""
    if not isinstance(axes, (list, tuple)):
        raise ValueError("axes must be a sequence")
    for axis in axes:
        if axis not in HERITAGE_AXES:
            raise ValueError("unknown heritage axis %r" % (axis,))
    return float(len(set(axes))) / float(len(HERITAGE_AXES))


def missing_reuse_evidence(evidence):
    """Return the evidence references a reuse claim still lacks."""
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping")
    return [name for name in REQUIRED_REUSE_EVIDENCE if name not in evidence]


def qualification_is_current(age_months, policy=None):
    """Return whether the qualification evidence is still inside its validity."""
    settings = validate_routing_policy(policy)
    if not _is_int(age_months) or age_months < 0:
        raise ValueError("age_months must be a non-negative integer")
    return age_months <= settings["max_qualification_age_months"]


def activity_set_for_route(route):
    """Return the activity set the dedicated standard attaches to a route."""
    if route not in ACTIVITY_SETS:
        raise ValueError("unknown route %r" % (route,))
    return list(ACTIVITY_SETS[route])


def route_asic_requirements(case):
    """Route a class 1 ASIC into the dedicated development standard.

    case keys: part_id, declared_route, candidate/qualified heritage records,
    evidence, qualification_age_months, production_break, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    settings = validate_routing_policy(case.get("policy"))
    record = validate_case(case)
    findings = []

    if record["declared_route"] == "new-development":
        route = FULL_DEVELOPMENT
        moved = []
        grouped = {"silicon": [], "design": [], "assembly": []}
        missing = []
        current = True
        findings.append(
            "a new development enters the dedicated standard at its full flow"
        )
    else:
        moved = changed_axes(record["candidate"], record["qualified"])
        grouped = group_changed_axes(moved)
        missing = missing_reuse_evidence(record["evidence"])
        current = qualification_is_current(record["qualification_age_months"], settings)
        for name in missing:
            findings.append("the reuse claim references no %s" % name.replace("_", " "))
        for axis in grouped["silicon"]:
            findings.append("%s moved; the electrical evidence does not carry over" % axis)
        for axis in grouped["design"]:
            findings.append("%s moved; the functional evidence does not carry over" % axis)
        for axis in grouped["assembly"]:
            findings.append("%s moved; the package evidence has to be refreshed" % axis)
        if not current:
            findings.append(
                "the qualification is %d months old against a %d month validity"
                % (record["qualification_age_months"],
                   settings["max_qualification_age_months"])
            )
        if record["production_break"] and settings["production_break_forces_delta"]:
            findings.append("production stopped since qualification")

        if missing:
            route = HERITAGE_EVIDENCE_INCOMPLETE
        elif grouped["silicon"] or grouped["design"]:
            route = FULL_DEVELOPMENT
        elif grouped["assembly"] and not settings["assembly_change_stays_on_reuse"]:
            route = DELTA_QUALIFICATION
        elif not current:
            route = DELTA_QUALIFICATION
        elif record["production_break"] and settings["production_break_forces_delta"]:
            route = DELTA_QUALIFICATION
        else:
            route = REUSE_ROUTE

    return {
        "part_id": record["part_id"],
        "declared_route": record["declared_route"],
        "route": route,
        "referred_to_dedicated_standard": route != HERITAGE_EVIDENCE_INCOMPLETE,
        "changed_axes": moved,
        "changed_axis_groups": grouped,
        "heritage_delta_index": heritage_delta_index(moved),
        "missing_reuse_evidence": missing,
        "qualification_current": current,
        "qualification_age_months": record["qualification_age_months"],
        "production_break": record["production_break"],
        "required_activities": activity_set_for_route(route),
        "findings": findings,
    }
