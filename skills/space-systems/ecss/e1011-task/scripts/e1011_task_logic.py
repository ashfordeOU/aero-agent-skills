"""
Task characterization logic for HCD per ECSS-E-ST-10-11C §4.2.1.4.
Offline, deterministic, stdlib only.
"""

import dataclasses
from typing import Dict, List, Tuple

VALID_FREQUENCIES: frozenset = frozenset({"rare", "occasional", "routine"})
VALID_CRITICALITIES: frozenset = frozenset(
    {"safety-critical", "mission-critical", "non-critical"}
)
VALID_DEMAND_LEVELS: frozenset = frozenset({"high", "medium", "low"})

_DEMAND_SCORE: Dict[str, int] = {"high": 3, "medium": 2, "low": 1}


@dataclasses.dataclass(frozen=True)
class TaskWorkload:
    physical: str
    cognitive: str
    time_pressure: str
    error_consequence: str


@dataclasses.dataclass(frozen=True)
class Task:
    name: str
    phase: str
    frequency: str
    criticality: str
    workload: TaskWorkload


def validate_task(task: Task) -> List[str]:
    """Return a list of error strings; empty list means the task is valid."""
    errors: List[str] = []
    if not task.name.strip():
        errors.append("name must not be empty")
    if not task.phase.strip():
        errors.append("phase must not be empty")
    if task.frequency not in VALID_FREQUENCIES:
        errors.append(
            f"frequency '{task.frequency}' must be one of {sorted(VALID_FREQUENCIES)}"
        )
    if task.criticality not in VALID_CRITICALITIES:
        errors.append(
            f"criticality '{task.criticality}' must be one of {sorted(VALID_CRITICALITIES)}"
        )
    for dim, val in (
        ("physical", task.workload.physical),
        ("cognitive", task.workload.cognitive),
        ("time_pressure", task.workload.time_pressure),
        ("error_consequence", task.workload.error_consequence),
    ):
        if val not in VALID_DEMAND_LEVELS:
            errors.append(
                f"workload.{dim} '{val}' must be one of {sorted(VALID_DEMAND_LEVELS)}"
            )
    return errors


def compute_workload_score(workload: TaskWorkload) -> int:
    """
    Sum the four dimension scores (1=low, 2=medium, 3=high).
    Range: 4 (all-low) to 12 (all-high).
    Raises ValueError if any dimension value is unrecognised.
    """
    total = 0
    for dim, val in (
        ("physical", workload.physical),
        ("cognitive", workload.cognitive),
        ("time_pressure", workload.time_pressure),
        ("error_consequence", workload.error_consequence),
    ):
        if val not in _DEMAND_SCORE:
            raise ValueError(f"unrecognised demand level for {dim}: '{val}'")
        total += _DEMAND_SCORE[val]
    return total


def workload_band(score: int) -> str:
    """
    Map a numeric workload score to a band label.
    10-12 → 'high', 7-9 → 'medium', 4-6 → 'low'.
    Raises ValueError for scores outside [4, 12].
    """
    if not (4 <= score <= 12):
        raise ValueError(f"score {score} is outside the valid range [4, 12]")
    if score >= 10:
        return "high"
    if score >= 7:
        return "medium"
    return "low"


def is_high_risk(task: Task) -> bool:
    """
    Return True when a task's criticality is safety-critical or mission-critical
    AND its workload band is 'high'.
    Non-critical tasks cannot be high-risk regardless of workload.
    """
    if task.criticality not in {"safety-critical", "mission-critical"}:
        return False
    score = compute_workload_score(task.workload)
    return workload_band(score) == "high"


def analyze_task_inventory(tasks: List[Task]) -> Dict:
    """
    Validate and analyze a list of tasks.

    Returns a dict with:
      valid_tasks        – names of tasks that passed validation
      invalid_tasks      – dict {name: [error, ...]} for tasks that failed
      high_risk_tasks    – names of valid tasks flagged as high-risk
      workload_scores    – dict {name: (score, band)} for valid tasks
      criticality_counts – dict {criticality: count} for valid tasks
      frequency_counts   – dict {frequency: count} for valid tasks
    """
    valid_tasks: List[str] = []
    invalid_tasks: Dict[str, List[str]] = {}
    high_risk_tasks: List[str] = []
    workload_scores: Dict[str, Tuple[int, str]] = {}
    criticality_counts: Dict[str, int] = {k: 0 for k in VALID_CRITICALITIES}
    frequency_counts: Dict[str, int] = {k: 0 for k in VALID_FREQUENCIES}

    for task in tasks:
        errors = validate_task(task)
        if errors:
            invalid_tasks[task.name] = errors
            continue

        valid_tasks.append(task.name)
        score = compute_workload_score(task.workload)
        band = workload_band(score)
        workload_scores[task.name] = (score, band)
        criticality_counts[task.criticality] += 1
        frequency_counts[task.frequency] += 1
        if is_high_risk(task):
            high_risk_tasks.append(task.name)

    return {
        "valid_tasks": valid_tasks,
        "invalid_tasks": invalid_tasks,
        "high_risk_tasks": high_risk_tasks,
        "workload_scores": workload_scores,
        "criticality_counts": criticality_counts,
        "frequency_counts": frequency_counts,
    }
