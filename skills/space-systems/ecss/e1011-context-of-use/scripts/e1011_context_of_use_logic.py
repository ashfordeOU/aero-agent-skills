"""
Context-of-use description logic — ECSS-E-ST-10-11C §4.2.2.

Deterministic, offline, stdlib only.

Key concepts
------------
UserRole   — named role with experience level and training pathway.
Task       — named task owned by a role, tagged with mission phases and criticality.
EnvElement — physical or organisational environment element tagged with phases.
ContextRecord — container that aggregates roles, tasks, and environment elements
                for a single product/system boundary; validates completeness and
                produces a gap list.

EXPERIENCE_LEVELS (ordered low → high): novice, trained, expert.
CRITICALITY values: safety-critical, mission-critical, routine.
ENV_CATEGORIES: physical, organisational.
VALID_PHASES: launch, ascent, orbit-insertion, on-orbit-nominal,
              on-orbit-contingency, eva-prep, eva, re-entry, landing,
              post-landing, all-phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

EXPERIENCE_LEVELS = ("novice", "trained", "expert")
CRITICALITY_VALUES = ("safety-critical", "mission-critical", "routine")
ENV_CATEGORIES = ("physical", "organisational")
VALID_PHASES = frozenset({
    "launch", "ascent", "orbit-insertion", "on-orbit-nominal",
    "on-orbit-contingency", "eva-prep", "eva", "re-entry",
    "landing", "post-landing", "all-phases",
})

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserRole:
    name: str
    count: int
    min_experience: str
    max_experience: str
    training_pathway: Optional[str]

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.name or not self.name.strip():
            issues.append("UserRole: name is empty")
        if self.count < 1:
            issues.append(f"UserRole '{self.name}': count must be >= 1, got {self.count}")
        if self.min_experience not in EXPERIENCE_LEVELS:
            issues.append(
                f"UserRole '{self.name}': min_experience '{self.min_experience}' "
                f"not in {EXPERIENCE_LEVELS}"
            )
        if self.max_experience not in EXPERIENCE_LEVELS:
            issues.append(
                f"UserRole '{self.name}': max_experience '{self.max_experience}' "
                f"not in {EXPERIENCE_LEVELS}"
            )
        if (
            self.min_experience in EXPERIENCE_LEVELS
            and self.max_experience in EXPERIENCE_LEVELS
            and EXPERIENCE_LEVELS.index(self.min_experience)
            > EXPERIENCE_LEVELS.index(self.max_experience)
        ):
            issues.append(
                f"UserRole '{self.name}': min_experience must be <= max_experience"
            )
        if not self.training_pathway or not self.training_pathway.strip():
            issues.append(f"UserRole '{self.name}': training_pathway is missing (mandatory)")
        return issues


@dataclass
class Task:
    name: str
    goal: str
    owning_role: str
    triggering_condition: str
    nominal_step_count: int
    frequency: str
    criticality: str
    max_error_rate: float  # fraction 0.0–1.0
    phases: List[str]

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.name or not self.name.strip():
            issues.append("Task: name is empty")
        if not self.goal or not self.goal.strip():
            issues.append(f"Task '{self.name}': goal is empty")
        if not self.owning_role or not self.owning_role.strip():
            issues.append(f"Task '{self.name}': owning_role is missing (mandatory)")
        if self.nominal_step_count < 1:
            issues.append(
                f"Task '{self.name}': nominal_step_count must be >= 1, got {self.nominal_step_count}"
            )
        if self.criticality not in CRITICALITY_VALUES:
            issues.append(
                f"Task '{self.name}': criticality '{self.criticality}' "
                f"not in {CRITICALITY_VALUES}"
            )
        if not (0.0 <= self.max_error_rate <= 1.0):
            issues.append(
                f"Task '{self.name}': max_error_rate {self.max_error_rate} must be in [0.0, 1.0]"
            )
        if not self.phases:
            issues.append(f"Task '{self.name}': at least one phase tag is mandatory")
        else:
            for ph in self.phases:
                if ph not in VALID_PHASES:
                    issues.append(f"Task '{self.name}': phase '{ph}' is not a recognised phase")
        return issues


@dataclass
class EnvElement:
    name: str
    category: str
    description: str
    phases: List[str]

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.name or not self.name.strip():
            issues.append("EnvElement: name is empty")
        if self.category not in ENV_CATEGORIES:
            issues.append(
                f"EnvElement '{self.name}': category '{self.category}' "
                f"not in {ENV_CATEGORIES}"
            )
        if not self.description or not self.description.strip():
            issues.append(f"EnvElement '{self.name}': description is empty")
        if not self.phases:
            issues.append(f"EnvElement '{self.name}': at least one phase tag is mandatory")
        else:
            for ph in self.phases:
                if ph not in VALID_PHASES:
                    issues.append(
                        f"EnvElement '{self.name}': phase '{ph}' is not a recognised phase"
                    )
        return issues


# ---------------------------------------------------------------------------
# Context record
# ---------------------------------------------------------------------------

@dataclass
class ContextRecord:
    product_boundary: str
    roles: List[UserRole] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    env_elements: List[EnvElement] = field(default_factory=list)

    def _validate_cross_references(self) -> List[str]:
        """Each task's owning_role must reference a declared role name."""
        issues: List[str] = []
        known_roles = {r.name for r in self.roles}
        for task in self.tasks:
            if task.owning_role and task.owning_role not in known_roles:
                issues.append(
                    f"Task '{task.name}': owning_role '{task.owning_role}' "
                    f"is not declared in the user population"
                )
        return issues

    def build_gap_list(self) -> List[str]:
        """
        Return a list of gap strings.  An empty list means the record
        is complete and ready for HCD planning.
        """
        gaps: List[str] = []

        if not self.product_boundary or not self.product_boundary.strip():
            gaps.append("ContextRecord: product_boundary is missing")

        if not self.roles:
            gaps.append("ContextRecord: no user roles defined")
        for role in self.roles:
            gaps.extend(role.validate())

        if not self.tasks:
            gaps.append("ContextRecord: no tasks defined")
        for task in self.tasks:
            gaps.extend(task.validate())

        if not self.env_elements:
            gaps.append("ContextRecord: no environment elements defined")
        for elem in self.env_elements:
            gaps.extend(elem.validate())

        gaps.extend(self._validate_cross_references())
        return gaps

    def is_complete(self) -> bool:
        return len(self.build_gap_list()) == 0

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def role_names(self) -> List[str]:
        return [r.name for r in self.roles]

    def tasks_for_role(self, role_name: str) -> List[Task]:
        return [t for t in self.tasks if t.owning_role == role_name]

    def tasks_in_phase(self, phase: str) -> List[Task]:
        if phase not in VALID_PHASES:
            raise ValueError(f"Unrecognised phase '{phase}'. Valid: {sorted(VALID_PHASES)}")
        if phase == "all-phases":
            return list(self.tasks)
        return [t for t in self.tasks if phase in t.phases or "all-phases" in t.phases]

    def env_elements_by_category(self, category: str) -> List[EnvElement]:
        if category not in ENV_CATEGORIES:
            raise ValueError(f"Unrecognised category '{category}'. Valid: {ENV_CATEGORIES}")
        return [e for e in self.env_elements if e.category == category]

    def safety_critical_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.criticality == "safety-critical"]


# ---------------------------------------------------------------------------
# Standalone helper — validate a single phase string
# ---------------------------------------------------------------------------

def validate_phase(phase: str) -> bool:
    """Return True if phase is a recognised mission phase identifier."""
    return phase in VALID_PHASES
