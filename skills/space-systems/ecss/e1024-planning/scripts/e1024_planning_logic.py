"""
e1024_planning_logic.py — Interface Management Planning (ECSS-E-ST-10C §5.1)

Deterministic, offline logic for validating and assessing an Interface
Management Plan (IMP) against the ECSS-E-ST-10C §5.1 requirements.
No external dependencies; stdlib only.
"""

# Required top-level fields in an IMP document.
REQUIRED_IMP_FIELDS = frozenset([
    "name",
    "purpose",
    "scope",
    "responsibilities",
    "process_steps",
    "schedule",
    "sep_reference",
])

# Required IM process steps per §5.1.
REQUIRED_PROCESS_STEPS = frozenset([
    "identify",
    "document",
    "review",
    "approve",
    "baseline",
    "control",
    "verify",
])

# Project lifecycle phase labels (ECSS phases 0 through F).
LIFECYCLE_PHASES = ("0", "A", "B", "C", "D", "E", "F")

# Minimum set of lifecycle phases that must carry at least one IM milestone.
REQUIRED_PHASE_COVERAGE = frozenset(["A", "B", "C", "D"])

# Interface types that must each have an assigned responsible party.
INTERFACE_TYPES = frozenset([
    "mechanical",
    "electrical",
    "thermal",
    "data",
    "rf",
    "software",
    "operational",
])


def validate_imp_fields(plan):
    """
    Return a sorted list of required field names absent from plan.
    plan: dict representing the IMP document.
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict")
    missing = sorted(REQUIRED_IMP_FIELDS - set(plan.keys()))
    return missing


def check_process_completeness(steps):
    """
    Return a sorted list of required IM process steps not present in steps.
    steps: iterable of step-name strings (case-insensitive).
    """
    if not hasattr(steps, "__iter__"):
        raise TypeError("steps must be iterable")
    present = frozenset(s.lower() for s in steps)
    missing = sorted(REQUIRED_PROCESS_STEPS - present)
    return missing


def check_schedule_coverage(schedule):
    """
    Verify that the IM schedule covers each phase in REQUIRED_PHASE_COVERAGE
    with at least one non-empty milestone entry.
    schedule: dict mapping phase label (str) -> list of milestone strings.
    Returns a sorted list of issue strings; empty list means schedule is valid.
    """
    if not isinstance(schedule, dict):
        raise TypeError("schedule must be a dict")
    issues = []
    for phase in sorted(REQUIRED_PHASE_COVERAGE):
        if phase not in schedule:
            issues.append("phase {}: no IM milestones defined".format(phase))
        elif not schedule[phase]:
            issues.append("phase {}: milestone list is empty".format(phase))
    return issues


def check_sep_integration(plan):
    """
    Verify the three SEP-integration conditions required by §5.1:
      1. sep_reference: non-empty string identifying the SEP document.
      2. sep_im_section: non-empty string naming the IM section within the SEP.
      3. listed_as_deliverable: boolean True — IMP is a required SEP deliverable.
    plan: dict representing the IMP document.
    Returns a list of issue strings; empty list means SEP integration is valid.
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict")
    issues = []

    ref = plan.get("sep_reference", "")
    if not ref or not str(ref).strip():
        issues.append("sep_reference is missing or empty")

    section = plan.get("sep_im_section", "")
    if not section or not str(section).strip():
        issues.append("sep_im_section is missing or empty")

    deliverable = plan.get("listed_as_deliverable", None)
    if deliverable is None:
        issues.append("listed_as_deliverable field is absent")
    elif deliverable is not True:
        issues.append("IMP is not listed as a required deliverable in the SEP")

    return issues


def check_responsibility_matrix(matrix):
    """
    Verify that every interface type in INTERFACE_TYPES has a non-empty
    responsible party string in matrix.
    matrix: dict mapping interface-type string -> owner string.
    Returns a sorted list of issue strings; empty list means matrix is complete.
    """
    if not isinstance(matrix, dict):
        raise TypeError("matrix must be a dict")
    issues = []
    for itype in sorted(INTERFACE_TYPES):
        owner = matrix.get(itype, "")
        if not owner or not str(owner).strip():
            issues.append("interface type '{}': no responsible party assigned".format(itype))
    return issues


def assess_im_plan(plan):
    """
    Full §5.1 assessment of an IMP.
    plan: dict representing the IMP document.
    Returns a dict with keys:
      field_issues         — list of missing required top-level fields
      process_issues       — list of missing required IM process steps
      schedule_issues      — list of schedule coverage gaps
      sep_issues           — list of SEP-integration failures
      responsibility_issues — list of uncovered interface types
      compliant            — bool, True only when all issue lists are empty
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict")

    field_issues = validate_imp_fields(plan)
    process_issues = check_process_completeness(plan.get("process_steps", []))
    schedule_issues = check_schedule_coverage(plan.get("schedule", {}))
    sep_issues = check_sep_integration(plan)
    responsibility_issues = check_responsibility_matrix(plan.get("responsibilities", {}))

    compliant = not any([
        field_issues,
        process_issues,
        schedule_issues,
        sep_issues,
        responsibility_issues,
    ])

    return {
        "field_issues": field_issues,
        "process_issues": process_issues,
        "schedule_issues": schedule_issues,
        "sep_issues": sep_issues,
        "responsibility_issues": responsibility_issues,
        "compliant": compliant,
    }
