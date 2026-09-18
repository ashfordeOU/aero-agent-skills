"""Hybrid manufacturer validation: purpose and the path the activity follows.

Anchor: ECSS-Q-ST-60-05 clause 6.1 (what the manufacturer validation activity
is for, and the overall route it runs through for a hybrid supplier).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the purpose of the activity as a set of objectives, each evidenced by
   one stage of the path: capability demonstrated on real hardware, the process
   documentation confirmed against the line, a technology scope fixed, and a
   surveillance baseline set so the validation stays true after it is granted.
2. Hold the path as an ordered stage list with explicit prerequisites, so a
   plan can be graded on ordering rather than on the presence of stage names.
3. Grade a proposed plan: unknown stages, repeated stages, mandatory stages
   left out and stages placed ahead of their prerequisites.
4. From the stages actually complete, name the next executable stage, report
   the completion fraction and say which objectives the purpose still owes.
5. Test a requested build against the technology scope a granted validation
   covers, since a validation is granted for a scope and not for a company.
"""

__all__ = [
    "VALIDATION_STAGES",
    "STAGE_NAMES",
    "MANDATORY_STAGES",
    "VALIDATION_OBJECTIVES",
    "stage_record",
    "stage_index",
    "validate_plan",
    "ordering_violations",
    "next_stage",
    "completion_fraction",
    "objective_status",
    "planned_duration_days",
    "scope_covers",
    "assess_validation_path",
]

# The path, in the order it runs. Each entry carries the stages that have to be
# complete before it can start, and a nominal working-day duration used for the
# stage-count question a supplier always asks first.
VALIDATION_STAGES = (
    {"name": "validation-request", "prerequisites": (), "nominal_days": 5, "mandatory": True},
    {"name": "documentation-review", "prerequisites": ("validation-request",), "nominal_days": 20, "mandatory": True},
    {"name": "manufacturer-audit", "prerequisites": ("documentation-review",), "nominal_days": 10, "mandatory": True},
    {"name": "validation-vehicle-definition", "prerequisites": ("documentation-review",), "nominal_days": 15, "mandatory": True},
    {
        "name": "validation-vehicle-build",
        "prerequisites": ("manufacturer-audit", "validation-vehicle-definition"),
        "nominal_days": 45,
        "mandatory": True,
    },
    {"name": "evaluation-testing", "prerequisites": ("validation-vehicle-build",), "nominal_days": 60, "mandatory": True},
    {"name": "validation-review", "prerequisites": ("evaluation-testing",), "nominal_days": 15, "mandatory": True},
    {"name": "validation-granted", "prerequisites": ("validation-review",), "nominal_days": 5, "mandatory": True},
    {"name": "surveillance", "prerequisites": ("validation-granted",), "nominal_days": 0, "mandatory": False},
)

STAGE_NAMES = tuple(stage["name"] for stage in VALIDATION_STAGES)

MANDATORY_STAGES = tuple(stage["name"] for stage in VALIDATION_STAGES if stage["mandatory"])

# What the activity is for, and the stage that evidences each objective. An
# objective with no completed evidencing stage is still owed.
VALIDATION_OBJECTIVES = (
    ("demonstrated-process-capability", "evaluation-testing"),
    ("process-documentation-confirmed", "manufacturer-audit"),
    ("technology-scope-fixed", "validation-granted"),
    ("surveillance-baseline-set", "surveillance"),
)

_STAGE_BY_NAME = dict((stage["name"], stage) for stage in VALIDATION_STAGES)


def _normalize_stage_name(value, label="stage"):
    if not isinstance(value, str):
        raise ValueError("%s must be a string name, got %r" % (label, value))
    name = " ".join(value.split()).strip().lower().replace("_", "-").replace(" ", "-")
    if not name:
        raise ValueError("%s must not be blank" % label)
    return name


def stage_record(name):
    """Return the path record for one stage."""
    key = _normalize_stage_name(name)
    if key not in _STAGE_BY_NAME:
        raise ValueError("unknown validation stage %r" % (name,))
    return dict(_STAGE_BY_NAME[key])


def stage_index(name):
    """Return the position of a stage on the path, counting from zero."""
    return STAGE_NAMES.index(stage_record(name)["name"])


def validate_plan(plan):
    """Return the normalized plan, refusing unknown, repeated or absent stages."""
    if not isinstance(plan, (list, tuple)):
        raise ValueError("plan must be a sequence of stage names")
    if not plan:
        raise ValueError("plan must name at least one stage")
    normalized = []
    for entry in plan:
        name = stage_record(entry)["name"]
        if name in normalized:
            raise ValueError("stage '%s' appears more than once in the plan" % name)
        normalized.append(name)
    return normalized


def ordering_violations(plan):
    """Return the (stage, prerequisite) pairs the plan puts in the wrong order."""
    normalized = validate_plan(plan)
    position = dict((name, i) for i, name in enumerate(normalized))
    violations = []
    for name in normalized:
        for prerequisite in _STAGE_BY_NAME[name]["prerequisites"]:
            if prerequisite not in position:
                violations.append((name, prerequisite))
            elif position[prerequisite] > position[name]:
                violations.append((name, prerequisite))
    return violations


def next_stage(completed):
    """Return the first stage whose prerequisites are complete and itself is not."""
    if completed is None:
        done = []
    else:
        if not isinstance(completed, (list, tuple, set, frozenset)):
            raise ValueError("completed must be a sequence of stage names")
        done = [stage_record(name)["name"] for name in completed]
    done_set = set(done)
    for stage in VALIDATION_STAGES:
        if stage["name"] in done_set:
            continue
        if all(prerequisite in done_set for prerequisite in stage["prerequisites"]):
            return stage["name"]
    return None


def completion_fraction(completed):
    """Return the share of the path already complete."""
    if completed is None:
        return 0.0
    if not isinstance(completed, (list, tuple, set, frozenset)):
        raise ValueError("completed must be a sequence of stage names")
    done = set(stage_record(name)["name"] for name in completed)
    return len(done) / float(len(STAGE_NAMES))


def objective_status(completed):
    """Return, per purpose objective, whether the stage that evidences it is done."""
    if completed is None:
        done = set()
    else:
        if not isinstance(completed, (list, tuple, set, frozenset)):
            raise ValueError("completed must be a sequence of stage names")
        done = set(stage_record(name)["name"] for name in completed)
    return dict((objective, evidence in done) for objective, evidence in VALIDATION_OBJECTIVES)


def planned_duration_days(plan):
    """Return the nominal working-day total of the stages a plan names."""
    normalized = validate_plan(plan)
    return sum(_STAGE_BY_NAME[name]["nominal_days"] for name in normalized)


def scope_covers(granted_scope, requested):
    """Return True when a granted validation scope covers a requested technology."""
    if not isinstance(granted_scope, (list, tuple, set, frozenset)):
        raise ValueError("granted_scope must be a sequence of technology names")
    covered = set(_normalize_stage_name(item, "granted_scope entry") for item in granted_scope)
    if not covered:
        raise ValueError("granted_scope must name at least one technology")
    return _normalize_stage_name(requested, "requested technology") in covered


def assess_validation_path(programme):
    """Grade a hybrid manufacturer validation programme against clause 6.1.

    programme keys: manufacturer, plan (sequence of stage names), optional
    completed (sequence of stage names), granted_scope and requested_technology.
    """
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    for key in ("manufacturer", "plan"):
        if key not in programme:
            raise ValueError("programme missing required key '%s'" % key)
    maker = programme["manufacturer"]
    if not isinstance(maker, str) or not maker.strip():
        raise ValueError("manufacturer must be a non-empty name")
    plan = validate_plan(programme["plan"])
    completed = programme.get("completed")
    if completed is not None:
        completed = [stage_record(name)["name"] for name in completed]
        outside = [name for name in completed if name not in plan]
        if outside:
            raise ValueError(
                "completed names stage(s) the plan does not contain: %s" % ", ".join(sorted(outside))
            )
    violations = ordering_violations(plan)
    missing = [name for name in MANDATORY_STAGES if name not in plan]
    findings = []
    if missing:
        findings.append("plan leaves out %d mandatory stage(s): %s" % (len(missing), ", ".join(missing)))
    for stage, prerequisite in violations:
        findings.append("stage '%s' is placed ahead of its prerequisite '%s'" % (stage, prerequisite))
    scope_finding = None
    granted = programme.get("granted_scope")
    requested = programme.get("requested_technology")
    if granted is not None and requested is not None:
        if not scope_covers(granted, requested):
            scope_finding = "requested technology '%s' sits outside the granted validation scope" % requested
            findings.append(scope_finding)
    objectives = objective_status(completed)
    return {
        "manufacturer": maker.strip(),
        "purpose": tuple(objective for objective, _ in VALIDATION_OBJECTIVES),
        "plan": plan,
        "missing_mandatory_stages": missing,
        "ordering_violations": violations,
        "objectives": objectives,
        "objectives_outstanding": [name for name, met in objectives.items() if not met],
        "completion": completion_fraction(completed),
        "next_stage": next_stage(completed),
        "planned_duration_days": planned_duration_days(plan),
        "coherent": not findings,
        "findings": findings,
    }
