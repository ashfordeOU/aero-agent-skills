"""
ECSS-E-ST-10-11C §4.4.1–4.4.2 HCD planning logic.

Validates and analyses a Human-Centred Design plan: mandatory activity
completeness, project-phase schedule mapping, phase-order consistency,
and responsibility assignment per Annex A requirements.

No third-party dependencies — stdlib only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants (paraphrased from ECSS-E-ST-10-11C Annex A)
# ---------------------------------------------------------------------------

REQUIRED_ACTIVITIES: tuple[str, ...] = (
    "context_of_use_analysis",
    "user_requirements_specification",
    "design_solution",
    "evaluation",
    "implementation_verification",
)

# ECSS project phases in chronological order (ECSS-M-ST-10C §4)
PROJECT_PHASES: tuple[str, ...] = ("0", "A", "B", "C", "D", "E", "F")
_PHASE_ORDER: dict[str, int] = {p: i for i, p in enumerate(PROJECT_PHASES)}

VALID_ROLES: frozenset[str] = frozenset({
    "hf_specialist",
    "project_manager",
    "system_engineer",
    "subsystem_engineer",
    "test_engineer",
    "operator",
})

# Every activity must include this role
MANDATORY_ROLE: str = "hf_specialist"

# (earlier_activity, later_or_equal_activity) — phase of earlier must be <= later
PHASE_ORDER_CONSTRAINTS: tuple[tuple[str, str], ...] = (
    ("context_of_use_analysis", "user_requirements_specification"),
    ("user_requirements_specification", "design_solution"),
    ("design_solution", "evaluation"),
)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class HCDPlanError(ValueError):
    """Base class for all HCD planning violations."""


class ActivityError(HCDPlanError):
    """Activity list is incomplete, duplicated, or contains unrecognised entries."""


class ScheduleError(HCDPlanError):
    """Phase identifier is invalid or phase-order constraint is violated."""


class ResponsibilityError(HCDPlanError):
    """Responsibility assignment is missing, empty, or references an unrecognised role."""


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_activity_list(activities: list[str]) -> None:
    """
    Check that all mandatory Annex A activities are present and that no
    activity appears more than once.

    Raises ActivityError on the first violation found.
    Extra activities beyond the required set are permitted.
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for act in activities:
        if act in seen:
            duplicates.append(act)
        seen.add(act)
    if duplicates:
        raise ActivityError(f"Duplicate activities detected: {duplicates}")

    missing = [a for a in REQUIRED_ACTIVITIES if a not in seen]
    if missing:
        raise ActivityError(f"Missing mandatory HCD activities: {missing}")


def validate_phase(phase: str) -> None:
    """
    Raise ScheduleError if phase is not a recognised ECSS project phase
    identifier (0, A, B, C, D, E, F — case-sensitive).
    """
    if phase not in _PHASE_ORDER:
        raise ScheduleError(
            f"Unrecognised project phase '{phase}'. "
            f"Valid identifiers: {PROJECT_PHASES}"
        )


def validate_schedule_mapping(activity_schedule: dict[str, str]) -> None:
    """
    Check that every activity in the schedule dict maps to a valid ECSS
    project phase.  Raises ScheduleError on the first invalid phase found.
    """
    for activity, phase in activity_schedule.items():
        try:
            validate_phase(phase)
        except ScheduleError as exc:
            raise ScheduleError(
                f"Activity '{activity}': {exc}"
            ) from exc


def validate_phase_order(activity_schedule: dict[str, str]) -> None:
    """
    Enforce that dependent HCD activities are scheduled in a logically
    consistent phase order.  The constraint set is:

      context_of_use_analysis  <= user_requirements_specification
      user_requirements_specification <= design_solution
      design_solution          <= evaluation

    A constraint is only checked when both activities appear in the schedule.
    Raises ScheduleError on the first violation.
    """
    for earlier, later in PHASE_ORDER_CONSTRAINTS:
        phase_e = activity_schedule.get(earlier)
        phase_l = activity_schedule.get(later)
        if phase_e is None or phase_l is None:
            continue
        if phase_e not in _PHASE_ORDER or phase_l not in _PHASE_ORDER:
            # Unknown phase identifiers are already flagged by validate_schedule_mapping;
            # skip the ordering check here to avoid a KeyError.
            continue
        if _PHASE_ORDER[phase_e] > _PHASE_ORDER[phase_l]:
            raise ScheduleError(
                f"Phase order violation: '{earlier}' scheduled in phase "
                f"{phase_e} but must not occur after '{later}' in phase {phase_l}."
            )


def validate_responsibility_assignment(
    activity_responsibilities: dict[str, list[str]]
) -> None:
    """
    Check that every activity in the responsibilities dict has:
    - at least one role assigned
    - only roles drawn from VALID_ROLES
    - the mandatory HF specialist role present

    Raises ResponsibilityError on the first violation.
    """
    for activity, roles in activity_responsibilities.items():
        if not roles:
            raise ResponsibilityError(
                f"Activity '{activity}' has no responsibility assigned."
            )
        unknown = [r for r in roles if r not in VALID_ROLES]
        if unknown:
            raise ResponsibilityError(
                f"Activity '{activity}' references unrecognised roles: {unknown}. "
                f"Valid roles: {sorted(VALID_ROLES)}"
            )
        if MANDATORY_ROLE not in roles:
            raise ResponsibilityError(
                f"Activity '{activity}' must include '{MANDATORY_ROLE}' "
                f"as a responsible party."
            )


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def compute_schedule_coverage(activity_schedule: dict[str, str]) -> dict[str, list[str]]:
    """
    Return a mapping of each ECSS project phase to the list of activities
    scheduled in that phase.  Phases with no activities map to an empty list.
    """
    coverage: dict[str, list[str]] = {p: [] for p in PROJECT_PHASES}
    for activity, phase in activity_schedule.items():
        if phase in coverage:
            coverage[phase].append(activity)
    return coverage


def summarize_plan_completeness(plan: dict) -> dict:
    """
    Return a completeness summary dict for an HCD plan without raising.

    Expected plan keys:
      activities      – list[str]
      schedule        – dict[str, str]  {activity: phase}
      responsibilities – dict[str, list[str]]  {activity: [roles]}

    Returns:
      {
        "activity_count":      int,
        "missing_activities":  list[str],
        "phases_used":         list[str],   # sorted by phase order
        "errors":              list[str],   # empty means compliant
      }
    """
    activities: list[str] = plan.get("activities", [])
    schedule: dict[str, str] = plan.get("schedule", {})
    responsibilities: dict[str, list[str]] = plan.get("responsibilities", {})

    errors: list[str] = []
    missing = [a for a in REQUIRED_ACTIVITIES if a not in activities]
    phases_used = sorted(
        set(schedule.values()),
        key=lambda p: _PHASE_ORDER.get(p, len(PROJECT_PHASES)),
    )

    for validator in (
        lambda: validate_activity_list(activities),
        lambda: validate_schedule_mapping(schedule),
        lambda: validate_phase_order(schedule),
        lambda: validate_responsibility_assignment(responsibilities),
    ):
        try:
            validator()
        except HCDPlanError as exc:
            errors.append(str(exc))

    return {
        "activity_count": len(activities),
        "missing_activities": missing,
        "phases_used": phases_used,
        "errors": errors,
    }


def validate_hcd_plan(plan: dict) -> None:
    """
    Validate a complete HCD plan dict, raising on the first violation found.

    Expected plan keys:
      activities       – list[str]
      schedule         – dict[str, str]
      responsibilities – dict[str, list[str]]
    """
    validate_activity_list(plan.get("activities", []))
    validate_schedule_mapping(plan.get("schedule", {}))
    validate_phase_order(plan.get("schedule", {}))
    validate_responsibility_assignment(plan.get("responsibilities", {}))
