"""
Users manual HFE input validation — ECSS-E-ST-10-11C §4.3.4.

Deterministic, offline, stdlib only.

Key concepts
------------
ProcedureStep  — one step in a task procedure; may be marked safety-critical.
TaskProcedure  — ordered steps with phase applicability and a unique ID.
UserCategory   — categorized description of a user type with skill, physical,
                 cognitive, and language attributes.
ErrorRecovery  — recovery description linked to a procedure by its ID.
UsersManual    — top-level record that assembles sections and validates
                 completeness via a gap list.

REQUIRED_SECTION_TYPES:
    user-population, task-procedures, interface-description, error-recovery,
    mission-phase-applicability, training-requirements.

VALID_PHASES:
    pre-launch, launch, ascent, on-orbit, eva-prep, eva, de-orbit,
    landing, post-landing, contingency, all-phases.

SKILL_LEVELS: novice, trained, expert  (ordered low to high).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

REQUIRED_SECTION_TYPES: tuple = (
    "user-population",
    "task-procedures",
    "interface-description",
    "error-recovery",
    "mission-phase-applicability",
    "training-requirements",
)

VALID_PHASES = frozenset({
    "pre-launch",
    "launch",
    "ascent",
    "on-orbit",
    "eva-prep",
    "eva",
    "de-orbit",
    "landing",
    "post-landing",
    "contingency",
    "all-phases",
})

SKILL_LEVELS = ("novice", "trained", "expert")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProcedureStep:
    """One step in a task procedure."""

    step_id: str
    action: str
    safety_critical: bool = False
    warning_note: str = ""

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.step_id or not self.step_id.strip():
            issues.append("ProcedureStep: step_id is empty")
        if not self.action or not self.action.strip():
            issues.append(f"ProcedureStep '{self.step_id}': action is empty")
        if self.safety_critical and not (self.warning_note and self.warning_note.strip()):
            issues.append(
                f"ProcedureStep '{self.step_id}': safety_critical=True but "
                "warning_note is absent or empty"
            )
        return issues


@dataclass
class TaskProcedure:
    """Step-by-step procedure for one user task."""

    procedure_id: str
    description: str
    phases: List[str]
    steps: List[ProcedureStep] = field(default_factory=list)

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.procedure_id or not self.procedure_id.strip():
            issues.append("TaskProcedure: procedure_id is empty")
        if not self.description or not self.description.strip():
            issues.append(f"TaskProcedure '{self.procedure_id}': description is empty")
        if not self.steps:
            issues.append(
                f"TaskProcedure '{self.procedure_id}': at least one step is required"
            )
        if not self.phases:
            issues.append(
                f"TaskProcedure '{self.procedure_id}': at least one mission-phase tag is required"
            )
        else:
            for ph in self.phases:
                if ph not in VALID_PHASES:
                    issues.append(
                        f"TaskProcedure '{self.procedure_id}': phase '{ph}' "
                        f"is not a recognised phase"
                    )
        for step in self.steps:
            issues.extend(step.validate())
        return issues

    def has_safety_critical_steps(self) -> bool:
        return any(s.safety_critical for s in self.steps)


@dataclass
class UserCategory:
    """Categorized description of a user type with mandatory HFE attributes."""

    name: str
    skill_level: str
    physical_constraints: str
    cognitive_load_limits: str
    operating_language: str

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.name or not self.name.strip():
            issues.append("UserCategory: name is empty")
        if self.skill_level not in SKILL_LEVELS:
            issues.append(
                f"UserCategory '{self.name}': skill_level '{self.skill_level}' "
                f"not in {SKILL_LEVELS}"
            )
        if not self.physical_constraints or not self.physical_constraints.strip():
            issues.append(
                f"UserCategory '{self.name}': physical_constraints is missing or empty"
            )
        if not self.cognitive_load_limits or not self.cognitive_load_limits.strip():
            issues.append(
                f"UserCategory '{self.name}': cognitive_load_limits is missing or empty"
            )
        if not self.operating_language or not self.operating_language.strip():
            issues.append(
                f"UserCategory '{self.name}': operating_language is missing or empty"
            )
        return issues


@dataclass
class ErrorRecovery:
    """Recovery procedure linked to a task procedure by its ID."""

    procedure_id: str
    recovery_description: str

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.procedure_id or not self.procedure_id.strip():
            issues.append("ErrorRecovery: procedure_id is empty")
        if not self.recovery_description or not self.recovery_description.strip():
            issues.append(
                f"ErrorRecovery for '{self.procedure_id}': "
                "recovery_description is missing or empty"
            )
        return issues


# ---------------------------------------------------------------------------
# Top-level manual record
# ---------------------------------------------------------------------------

@dataclass
class UsersManual:
    """
    Top-level users manual record.  Aggregates the six required HFE input
    sections and validates completeness via build_gap_list().
    """

    product_name: str
    user_categories: List[UserCategory] = field(default_factory=list)
    task_procedures: List[TaskProcedure] = field(default_factory=list)
    interface_description: str = ""
    error_recovery_entries: List[ErrorRecovery] = field(default_factory=list)
    mission_phase_applicability: str = ""
    training_requirements: str = ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _present_sections(self) -> List[str]:
        present = []
        if self.user_categories:
            present.append("user-population")
        if self.task_procedures:
            present.append("task-procedures")
        if self.interface_description and self.interface_description.strip():
            present.append("interface-description")
        if self.error_recovery_entries:
            present.append("error-recovery")
        if self.mission_phase_applicability and self.mission_phase_applicability.strip():
            present.append("mission-phase-applicability")
        if self.training_requirements and self.training_requirements.strip():
            present.append("training-requirements")
        return present

    def _missing_sections(self) -> List[str]:
        present = set(self._present_sections())
        return [s for s in REQUIRED_SECTION_TYPES if s not in present]

    def _safety_critical_coverage_gaps(self) -> List[str]:
        """Return IDs of procedures with safety-critical steps but no recovery entry."""
        covered_ids = {er.procedure_id for er in self.error_recovery_entries}
        gaps = []
        for proc in self.task_procedures:
            if proc.has_safety_critical_steps() and proc.procedure_id not in covered_ids:
                gaps.append(proc.procedure_id)
        return gaps

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_gap_list(self) -> List[str]:
        """
        Return a list of gap strings describing every HFE compliance defect.
        An empty list means the manual is HFE-compliant at this validation level.
        """
        gaps: List[str] = []

        if not self.product_name or not self.product_name.strip():
            gaps.append("UsersManual: product_name is missing")

        missing = self._missing_sections()
        for s in missing:
            gaps.append(f"UsersManual: required section '{s}' is absent or empty")

        for uc in self.user_categories:
            gaps.extend(uc.validate())

        for proc in self.task_procedures:
            gaps.extend(proc.validate())

        for er in self.error_recovery_entries:
            gaps.extend(er.validate())

        for proc_id in self._safety_critical_coverage_gaps():
            gaps.append(
                f"TaskProcedure '{proc_id}': has safety-critical steps but no "
                "linked error-recovery entry"
            )

        return gaps

    def is_compliant(self) -> bool:
        return len(self.build_gap_list()) == 0

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def procedures_in_phase(self, phase: str) -> List[TaskProcedure]:
        if phase not in VALID_PHASES:
            raise ValueError(
                f"Unrecognised phase '{phase}'. Valid phases: {sorted(VALID_PHASES)}"
            )
        if phase == "all-phases":
            return list(self.task_procedures)
        return [
            p for p in self.task_procedures
            if phase in p.phases or "all-phases" in p.phases
        ]

    def safety_critical_procedures(self) -> List[TaskProcedure]:
        return [p for p in self.task_procedures if p.has_safety_critical_steps()]

    def recovery_for_procedure(self, procedure_id: str) -> Optional[ErrorRecovery]:
        for er in self.error_recovery_entries:
            if er.procedure_id == procedure_id:
                return er
        return None


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------

def validate_phase(phase: str) -> bool:
    """Return True if phase is a recognised mission phase identifier."""
    return phase in VALID_PHASES


def validate_skill_level(level: str) -> bool:
    """Return True if level is a recognised skill level."""
    return level in SKILL_LEVELS
