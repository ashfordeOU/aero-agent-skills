"""
ECSS-E-ST-10-11C §4.4.3 Human-Centred Design activities.

Implements deterministic, checkable logic for the four HCD activity types:
task analysis, user and organisational requirements, design solution
production, and design evaluation. Stdlib only; no external dependencies.
"""

CRITICALITY_LEVELS = frozenset({"low", "medium", "high", "critical"})
REQUIREMENT_SOURCES = frozenset({"user", "organisational"})
REQUIREMENT_CATEGORIES = frozenset({"functional", "performance", "safety", "comfort", "organisational"})
EVALUATION_OUTCOMES = frozenset({"pass", "fail", "conditional"})
HCD_ACTIVITY_TYPES = frozenset({
    "task_analysis",
    "user_requirements",
    "design_production",
    "design_evaluation",
})


class HCDError(ValueError):
    """Raised when an HCD activity record fails validation."""


def validate_task_entry(task: dict) -> dict:
    """
    Validate a single task-analysis entry.

    Required fields:
    - task_id: non-empty str
    - description: non-empty str
    - performer: non-empty str (crew role or operator category)
    - criticality: one of CRITICALITY_LEVELS
    - steps: list of at least one non-empty str

    Returns the entry unchanged if valid; raises HCDError otherwise.
    """
    required = ("task_id", "description", "performer", "criticality", "steps")
    missing = [f for f in required if f not in task]
    if missing:
        raise HCDError(f"Task entry missing required fields: {missing}")

    for str_field in ("task_id", "description", "performer"):
        if not isinstance(task[str_field], str) or not task[str_field].strip():
            raise HCDError(f"'{str_field}' must be a non-empty string")

    if task["criticality"] not in CRITICALITY_LEVELS:
        raise HCDError(
            f"'criticality' must be one of {sorted(CRITICALITY_LEVELS)}, "
            f"got: {task['criticality']!r}"
        )

    if not isinstance(task["steps"], list) or len(task["steps"]) < 1:
        raise HCDError("'steps' must be a list with at least one entry")

    return task


def validate_user_requirement(req: dict) -> dict:
    """
    Validate a user or organisational requirement entry.

    Required fields:
    - req_id: non-empty str
    - source: "user" or "organisational"
    - category: one of REQUIREMENT_CATEGORIES
    - statement: non-empty str
    - priority: int in range 1–5 (1 = highest)

    Returns the entry unchanged if valid; raises HCDError otherwise.
    """
    required = ("req_id", "source", "category", "statement", "priority")
    missing = [f for f in required if f not in req]
    if missing:
        raise HCDError(f"Requirement entry missing required fields: {missing}")

    for str_field in ("req_id", "statement"):
        if not isinstance(req[str_field], str) or not req[str_field].strip():
            raise HCDError(f"'{str_field}' must be a non-empty string")

    if req["source"] not in REQUIREMENT_SOURCES:
        raise HCDError(
            f"'source' must be one of {sorted(REQUIREMENT_SOURCES)}, "
            f"got: {req['source']!r}"
        )

    if req["category"] not in REQUIREMENT_CATEGORIES:
        raise HCDError(
            f"'category' must be one of {sorted(REQUIREMENT_CATEGORIES)}, "
            f"got: {req['category']!r}"
        )

    if not isinstance(req["priority"], int) or not (1 <= req["priority"] <= 5):
        raise HCDError(
            f"'priority' must be an integer in range 1–5, got: {req['priority']!r}"
        )

    return req


def validate_design_element(element: dict) -> dict:
    """
    Validate a design solution element.

    Required fields:
    - element_id: non-empty str
    - description: non-empty str
    - addresses: list of req_id strings (may be empty)
    - rationale: non-empty str

    Returns the entry unchanged if valid; raises HCDError otherwise.
    """
    required = ("element_id", "description", "addresses", "rationale")
    missing = [f for f in required if f not in element]
    if missing:
        raise HCDError(f"Design element missing required fields: {missing}")

    for str_field in ("element_id", "description", "rationale"):
        if not isinstance(element[str_field], str) or not element[str_field].strip():
            raise HCDError(f"'{str_field}' must be a non-empty string")

    if not isinstance(element["addresses"], list):
        raise HCDError("'addresses' must be a list (may be empty)")

    return element


def check_design_coverage(requirements: list, design_elements: list) -> dict:
    """
    Verify that every requirement is addressed by at least one design element.

    Args:
        requirements: list of validated requirement dicts
        design_elements: list of validated design element dicts

    Returns:
        {
            "covered": [req_id, ...],
            "uncovered": [req_id, ...],
            "coverage_ratio": float (0.0–1.0),
        }
    """
    addressed = set()
    for elem in design_elements:
        for rid in elem.get("addresses", []):
            addressed.add(rid)

    covered = []
    uncovered = []
    for req in requirements:
        rid = req["req_id"]
        if rid in addressed:
            covered.append(rid)
        else:
            uncovered.append(rid)

    total = len(requirements)
    ratio = len(covered) / total if total > 0 else 0.0

    return {
        "covered": covered,
        "uncovered": uncovered,
        "coverage_ratio": ratio,
    }


def evaluate_design_element(element: dict, criteria: list) -> dict:
    """
    Evaluate a design element against a list of evaluation criteria.

    Each criterion dict must contain:
    - criterion_id: str
    - outcome: one of EVALUATION_OUTCOMES

    Overall outcome rules:
    - "fail" if any criterion outcome is "fail"
    - "conditional" if no criterion fails but at least one is "conditional"
    - "pass" if every criterion passes

    Args:
        element: validated design element dict
        criteria: non-empty list of criterion dicts

    Returns:
        {
            "element_id": str,
            "criteria_results": list,
            "overall_outcome": str,
            "fail_count": int,
            "conditional_count": int,
        }
    """
    if not isinstance(criteria, list) or len(criteria) < 1:
        raise HCDError("'criteria' must be a non-empty list")

    fail_count = 0
    conditional_count = 0

    for c in criteria:
        missing = [f for f in ("criterion_id", "outcome") if f not in c]
        if missing:
            raise HCDError(f"Criterion missing required fields: {missing}")
        if c["outcome"] not in EVALUATION_OUTCOMES:
            raise HCDError(
                f"Criterion outcome must be one of {sorted(EVALUATION_OUTCOMES)}, "
                f"got: {c['outcome']!r}"
            )
        if c["outcome"] == "fail":
            fail_count += 1
        elif c["outcome"] == "conditional":
            conditional_count += 1

    if fail_count > 0:
        overall = "fail"
    elif conditional_count > 0:
        overall = "conditional"
    else:
        overall = "pass"

    return {
        "element_id": element["element_id"],
        "criteria_results": list(criteria),
        "overall_outcome": overall,
        "fail_count": fail_count,
        "conditional_count": conditional_count,
    }


def check_hcd_activity_completeness(activity_log: list) -> dict:
    """
    Check whether all four mandatory HCD activity types have been completed.

    Each entry in activity_log must have:
    - activity_type: str (one of HCD_ACTIVITY_TYPES)
    - completed: bool

    Returns:
        {
            "present": sorted list of completed activity types,
            "absent": sorted list of missing activity types,
            "complete": bool (True only when absent is empty),
        }
    """
    completed_types = set()
    for entry in activity_log:
        if entry.get("completed", False):
            atype = entry.get("activity_type", "")
            if atype in HCD_ACTIVITY_TYPES:
                completed_types.add(atype)

    present = sorted(t for t in HCD_ACTIVITY_TYPES if t in completed_types)
    absent = sorted(t for t in HCD_ACTIVITY_TYPES if t not in completed_types)

    return {
        "present": present,
        "absent": absent,
        "complete": len(absent) == 0,
    }


def summarise_hcd_assessment(
    tasks: list,
    requirements: list,
    design_elements: list,
    evaluation_results: list,
) -> dict:
    """
    Produce a summary verdict for the full HCD activities assessment.

    Args:
        tasks: list of task-analysis dicts (validated internally)
        requirements: list of requirement dicts (validated internally)
        design_elements: list of design element dicts (validated internally)
        evaluation_results: list of dicts returned by evaluate_design_element

    Returns a dict with counts, error lists, coverage ratio, and overall
    pass/fail verdict. The verdict is True only when all validation passes,
    every requirement is covered, and no evaluation result carries "fail".
    """
    task_errors = []
    valid_tasks = []
    for t in tasks:
        try:
            valid_tasks.append(validate_task_entry(t))
        except HCDError as exc:
            task_errors.append(str(exc))

    req_errors = []
    valid_reqs = []
    for r in requirements:
        try:
            valid_reqs.append(validate_user_requirement(r))
        except HCDError as exc:
            req_errors.append(str(exc))

    elem_errors = []
    valid_elems = []
    for e in design_elements:
        try:
            valid_elems.append(validate_design_element(e))
        except HCDError as exc:
            elem_errors.append(str(exc))

    coverage = check_design_coverage(valid_reqs, valid_elems)

    eval_fail_count = sum(
        1 for r in evaluation_results if r.get("overall_outcome") == "fail"
    )

    passed = (
        not task_errors
        and not req_errors
        and not elem_errors
        and not coverage["uncovered"]
        and eval_fail_count == 0
    )

    return {
        "task_count": len(valid_tasks),
        "task_errors": task_errors,
        "requirement_count": len(valid_reqs),
        "req_errors": req_errors,
        "design_element_count": len(valid_elems),
        "elem_errors": elem_errors,
        "coverage_ratio": coverage["coverage_ratio"],
        "uncovered_requirements": coverage["uncovered"],
        "evaluation_fail_count": eval_fail_count,
        "passed": passed,
    }
