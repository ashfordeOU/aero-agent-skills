#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.9.5 training requirements definition
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
Human Factors Engineering standard's training requirements clause
requires that operator training needs be derived from the operational
products produced during the development lifecycle (operations concept,
task analyses, operations procedures, interface control documents); each
identified operator task is assessed on task complexity, procedural
novelty, and safety criticality, and those three attributes together
determine the training need tier for the task; the tier prescribes a
minimum set of training materials that must be completed and reviewed
before operational use; every personnel role performing the task must
hold a training assignment; and the available training time must meet
the tier minimum within the remaining calendar window before the
operational deadline. This module implements tier determination,
required-material derivation, personnel-role coverage checking,
schedule adequacy assessment, and full per-task training requirement
review.
"""

# Training need tiers, ordered from least to most demanding.
TRAINING_NEED_TIERS = ("routine", "standard", "enhanced", "specialized")

# Minimum training materials required by tier. Higher tiers include all
# materials required by lower tiers plus additional ones.
REQUIRED_MATERIALS = {
    "routine": frozenset({"procedure_checklist"}),
    "standard": frozenset({"procedure_checklist", "training_manual", "knowledge_assessment"}),
    "enhanced": frozenset({"procedure_checklist", "training_manual", "knowledge_assessment", "simulation_exercise"}),
    "specialized": frozenset({"procedure_checklist", "training_manual", "knowledge_assessment", "simulation_exercise", "certification_record"}),
}

# Minimum training hours required by tier before the task can be declared
# operationally ready.
REQUIRED_HOURS = {
    "routine": 1.0,
    "standard": 8.0,
    "enhanced": 24.0,
    "specialized": 40.0,
}


def determine_training_tier(task_complexity, novel_procedure, safety_critical):
    """Training need tier for one operator task, derived from its three
    attributes per §4.9.5:
    - "specialized" if task_complexity=="high" AND novel_procedure AND
      safety_critical
    - "enhanced" if safety_critical OR task_complexity=="high"
    - "standard" if novel_procedure OR task_complexity=="medium"
    - "routine" otherwise.

    task_complexity: "low" | "medium" | "high".
    novel_procedure: bool — True if the procedure is not previously
    mastered by the target crew.
    safety_critical: bool — True if an error can result in loss of
    mission, crew injury, or hardware damage.
    Raises ValueError for an unrecognized task_complexity."""
    if task_complexity not in ("low", "medium", "high"):
        raise ValueError(
            "unrecognized task_complexity %r; expected 'low', 'medium', or 'high'"
            % (task_complexity,)
        )
    if safety_critical and novel_procedure and task_complexity == "high":
        return "specialized"
    if safety_critical or task_complexity == "high":
        return "enhanced"
    if novel_procedure or task_complexity == "medium":
        return "standard"
    return "routine"


def check_material_completeness(tier, provided_materials):
    """Sorted list of material types that are required for the given
    training need tier but absent from provided_materials. Returns an
    empty list when all required materials are present.
    Raises ValueError for an unrecognized tier."""
    if tier not in REQUIRED_MATERIALS:
        raise ValueError(
            "unrecognized training need tier %r; expected one of %s"
            % (tier, TRAINING_NEED_TIERS)
        )
    required = REQUIRED_MATERIALS[tier]
    provided = set(provided_materials)
    return sorted(required - provided)


def check_role_coverage(required_roles, training_assignments):
    """Sorted list of personnel roles that have a training need for the
    task but no training assignment on record. required_roles: iterable
    of role identifiers that must be trained before first operational
    use. training_assignments: iterable of role identifiers that have
    already been assigned training. Returns an empty list when every
    required role is covered. Does not mutate either input."""
    covered = set(training_assignments)
    return sorted(set(required_roles) - covered)


def check_schedule_adequacy(tier, available_hours, days_until_operational):
    """True when the training programme for the given tier can be
    completed before the operational deadline.

    The schedule is adequate when:
    - available_hours >= REQUIRED_HOURS[tier], AND
    - for non-routine tiers, days_until_operational > 0 (at least one
      calendar day remains for formal scheduling).
    Routine tier only requires the hours check because a checklist
    review can be completed same-day.

    Raises ValueError for a negative available_hours or
    days_until_operational, or an unrecognized tier."""
    if tier not in REQUIRED_HOURS:
        raise ValueError(
            "unrecognized training need tier %r; expected one of %s"
            % (tier, TRAINING_NEED_TIERS)
        )
    if available_hours < 0:
        raise ValueError("available_hours must be >= 0, got %r" % (available_hours,))
    if days_until_operational < 0:
        raise ValueError(
            "days_until_operational must be >= 0, got %r" % (days_until_operational,)
        )
    if available_hours < REQUIRED_HOURS[tier]:
        return False
    if tier != "routine" and days_until_operational == 0:
        return False
    return True


def assess_training_requirement(task_record):
    """Full §4.9.5 training requirement assessment for one operator task.

    task_record keys:
      task_id: str
      task_complexity: str          "low" | "medium" | "high"
      novel_procedure: bool
      safety_critical: bool
      provided_materials: list[str] material type identifiers present
      required_roles: list[str]     roles that must be trained
      training_assignments: list[str] roles that have an assignment
      available_hours: float        total hours available for training
      days_until_operational: int   calendar days before first use

    Returns a dict:
      task_id: str
      tier: str
      missing_materials: list[str]
      uncovered_roles: list[str]
      schedule_adequate: bool
      compliant: bool               True when all three checks pass

    Raises ValueError for invalid inputs (propagated from sub-functions)."""
    task_id = task_record["task_id"]
    tier = determine_training_tier(
        task_record["task_complexity"],
        task_record["novel_procedure"],
        task_record["safety_critical"],
    )
    missing_materials = check_material_completeness(
        tier, task_record.get("provided_materials", [])
    )
    uncovered_roles = check_role_coverage(
        task_record.get("required_roles", []),
        task_record.get("training_assignments", []),
    )
    schedule_ok = check_schedule_adequacy(
        tier,
        task_record.get("available_hours", 0.0),
        task_record.get("days_until_operational", 0),
    )
    compliant = (
        len(missing_materials) == 0
        and len(uncovered_roles) == 0
        and schedule_ok
    )
    return {
        "task_id": task_id,
        "tier": tier,
        "missing_materials": missing_materials,
        "uncovered_roles": uncovered_roles,
        "schedule_adequate": schedule_ok,
        "compliant": compliant,
    }
