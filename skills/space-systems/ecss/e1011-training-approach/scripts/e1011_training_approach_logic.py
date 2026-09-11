"""
ECSS-E-ST-10-11C §4.3.5 — Training Approach logic.

Implements deterministic, offline procedures to:
  1. Derive the required training level from task criticality and error consequence.
  2. Return the admissible training means for a given level.
  3. Return the maximum recurrent-training interval for a given level.
  4. Validate a complete TrainingApproachRecord.
  5. Check coverage of all identified tasks against recorded approach entries.

stdlib only — no third-party dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# ── Allowed value sets ────────────────────────────────────────────────────────

TASK_CRITICALITY = frozenset({"high", "medium", "low"})
ERROR_CONSEQUENCES = frozenset({"catastrophic", "critical", "marginal", "negligible"})
TRAINING_STRATEGIES = frozenset({"initial", "recurrent", "refresher", "qualification"})
TRAINING_LEVELS = frozenset({"awareness", "procedural", "expert"})
TRAINING_MEANS = frozenset({"simulation", "cbt", "classroom", "ojt", "handbook", "briefing"})

# ── Level rank (used to compare levels) ───────────────────────────────────────

_LEVEL_RANK: dict[str, int] = {"awareness": 0, "procedural": 1, "expert": 2}

# ── Level-selection table ─────────────────────────────────────────────────────
# Rows: criticality; Columns: error consequence → required training level.
# Derived from the normative §4.3.5 decision rationale (not verbatim ECSS text).

_LEVEL_TABLE: dict[str, dict[str, str]] = {
    "high": {
        "catastrophic": "expert",
        "critical":     "expert",
        "marginal":     "procedural",
        "negligible":   "procedural",
    },
    "medium": {
        "catastrophic": "expert",
        "critical":     "procedural",
        "marginal":     "procedural",
        "negligible":   "awareness",
    },
    "low": {
        "catastrophic": "procedural",
        "critical":     "procedural",
        "marginal":     "awareness",
        "negligible":   "awareness",
    },
}

# ── Admissible means per level (ordered by preference) ───────────────────────

_ADMISSIBLE_MEANS: dict[str, list[str]] = {
    "expert":     ["simulation", "ojt", "classroom"],
    "procedural": ["simulation", "cbt", "classroom", "ojt"],
    "awareness":  ["briefing", "cbt", "handbook", "classroom"],
}

# ── Maximum recurrent interval (months) per level ────────────────────────────
# Expert training must recur most frequently; awareness training may recur less often.

MAX_RECURRENT_INTERVAL_MONTHS: dict[str, int] = {
    "expert":     6,
    "procedural": 12,
    "awareness":  24,
}


# ── Core functions ─────────────────────────────────────────────────────────────

def select_training_level(criticality: str, error_consequence: str) -> str:
    """Return the required training level for a task given its criticality and
    worst-case error consequence.

    Raises ValueError for inputs outside the defined value sets.
    """
    if criticality not in TASK_CRITICALITY:
        raise ValueError(
            f"Unknown criticality '{criticality}'; expected one of {sorted(TASK_CRITICALITY)}"
        )
    if error_consequence not in ERROR_CONSEQUENCES:
        raise ValueError(
            f"Unknown error consequence '{error_consequence}'; "
            f"expected one of {sorted(ERROR_CONSEQUENCES)}"
        )
    return _LEVEL_TABLE[criticality][error_consequence]


def admissible_means(training_level: str) -> list[str]:
    """Return the list of admissible training means for a level, in preference order.

    Raises ValueError for an unrecognized level.
    """
    if training_level not in TRAINING_LEVELS:
        raise ValueError(
            f"Unknown training level '{training_level}'; expected one of {sorted(TRAINING_LEVELS)}"
        )
    return list(_ADMISSIBLE_MEANS[training_level])


def max_recurrent_interval(training_level: str) -> int:
    """Return the maximum allowed recurrent-training interval in months for the given level.

    Raises ValueError for an unrecognized level.
    """
    if training_level not in TRAINING_LEVELS:
        raise ValueError(
            f"Unknown training level '{training_level}'; expected one of {sorted(TRAINING_LEVELS)}"
        )
    return MAX_RECURRENT_INTERVAL_MONTHS[training_level]


# ── Record dataclass ──────────────────────────────────────────────────────────

@dataclass
class TrainingApproachRecord:
    task_id: str
    criticality: str
    error_consequence: str
    assigned_level: str
    strategy: str
    means: str
    recurrent_interval_months: Optional[int] = None


# ── Validation ────────────────────────────────────────────────────────────────

def validate_training_approach_record(record: TrainingApproachRecord) -> list[str]:
    """Validate a TrainingApproachRecord against §4.3.5 constraints.

    Returns a list of finding strings. An empty list means the record is valid.
    """
    findings: list[str] = []
    tid = record.task_id

    if record.criticality not in TASK_CRITICALITY:
        findings.append(
            f"Task {tid}: unrecognized criticality '{record.criticality}'"
        )

    if record.error_consequence not in ERROR_CONSEQUENCES:
        findings.append(
            f"Task {tid}: unrecognized error_consequence '{record.error_consequence}'"
        )

    if record.assigned_level not in TRAINING_LEVELS:
        findings.append(
            f"Task {tid}: unrecognized training level '{record.assigned_level}'"
        )
        return findings  # further level-dependent checks are meaningless

    # Confirm assigned level meets the required minimum
    if record.criticality in TASK_CRITICALITY and record.error_consequence in ERROR_CONSEQUENCES:
        required = select_training_level(record.criticality, record.error_consequence)
        if _LEVEL_RANK[record.assigned_level] < _LEVEL_RANK[required]:
            findings.append(
                f"Task {tid}: assigned level '{record.assigned_level}' is below the "
                f"required level '{required}' for criticality='{record.criticality}' "
                f"and error_consequence='{record.error_consequence}'"
            )

    # Confirm means is known and admissible for the assigned level
    if record.means not in TRAINING_MEANS:
        findings.append(
            f"Task {tid}: unrecognized training means '{record.means}'"
        )
    elif record.means not in admissible_means(record.assigned_level):
        findings.append(
            f"Task {tid}: means '{record.means}' is not admissible for level "
            f"'{record.assigned_level}' (admissible: {admissible_means(record.assigned_level)})"
        )

    # Confirm strategy is known
    if record.strategy not in TRAINING_STRATEGIES:
        findings.append(
            f"Task {tid}: unrecognized strategy '{record.strategy}'"
        )

    # Recurrent / refresher strategies must carry an interval within the allowed maximum
    if record.strategy in {"recurrent", "refresher"}:
        max_interval = max_recurrent_interval(record.assigned_level)
        if record.recurrent_interval_months is None:
            findings.append(
                f"Task {tid}: strategy '{record.strategy}' requires "
                f"recurrent_interval_months to be set"
            )
        elif record.recurrent_interval_months > max_interval:
            findings.append(
                f"Task {tid}: recurrent_interval_months "
                f"{record.recurrent_interval_months} exceeds the maximum "
                f"{max_interval} for level '{record.assigned_level}'"
            )

    return findings


def check_coverage(task_ids: list[str], records: list[TrainingApproachRecord]) -> list[str]:
    """Return the list of task_ids that have no corresponding TrainingApproachRecord.

    An empty return means all tasks are covered.
    """
    covered = {r.task_id for r in records}
    return [tid for tid in task_ids if tid not in covered]
