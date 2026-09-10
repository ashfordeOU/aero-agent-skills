#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.7 phasing of verification activities
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification standard ties verification activities to the project life
cycle phases (A through F). Verification planning starts in phase A
with a preliminary verification approach and grows in detail through
each later phase, producing a distinct output at each stage: a
baselined verification plan and requirement verification matrix in
phase B, detailed verification procedures in phase C, and verification
execution plus qualification/acceptance status reports in phase D.
Phases E (utilization) and F (disposal) carry their own confirmation
outputs but only when the project actually has an in-service or
disposal-verification scope. A project may not be considered ready to
enter a given phase's verification activities until every earlier
phase's required outputs are complete, and the project's overall
verification maturity is no better than its least mature requirement.
This module implements phase output requirements, per-phase
completeness checks, phase entry readiness gating, and per-requirement
status roll-up; it does not define verification method selection
(test/analysis/inspection/review-of-design), which is out of scope for
this leaf.
"""

PROJECT_PHASES = ("A", "B", "C", "D", "E", "F")

# Verification outputs required by the end of each phase. Phases A-D
# are unconditionally applicable to every project; phases E and F are
# conditional (see CONDITIONAL_PHASE_FLAGS).
REQUIRED_OUTPUTS_BY_PHASE = {
    "A": frozenset({"verification_approach"}),
    "B": frozenset({"verification_plan", "requirement_verification_matrix"}),
    "C": frozenset({"verification_procedures"}),
    "D": frozenset(
        {"verification_reports", "qualification_status_report", "acceptance_status_report"}
    ),
    "E": frozenset({"in_service_verification_confirmation"}),
    "F": frozenset({"disposal_verification_confirmation"}),
}

# Project-level flag that must be truthy for a conditional phase's
# outputs to be required at all; absent or falsy means the phase is
# not applicable to this project and contributes no required outputs.
CONDITIONAL_PHASE_FLAGS = {
    "E": "has_in_service_phase",
    "F": "has_disposal_verification",
}

# Per-requirement verification status, ordered from least to most
# mature. The project's overall status is only as mature as its
# weakest requirement.
STATUS_SEQUENCE = ("not_started", "planned", "in_progress", "closed")


def phase_index(phase):
    """Position of phase in PROJECT_PHASES (0 = A). Raises ValueError
    for a phase outside the recognized A-F sequence."""
    try:
        return PROJECT_PHASES.index(phase)
    except ValueError:
        raise ValueError(
            "unrecognized project life cycle phase %r under "
            "E-ST-10-02C clause 5.2.7" % (phase,)
        )


def is_phase_applicable(phase, project_flags=None):
    """Whether phase carries a verification output requirement for
    this project. Phases A-D are always applicable. Phase E/F are
    applicable only when the matching CONDITIONAL_PHASE_FLAGS entry is
    truthy in project_flags. Raises ValueError for an unrecognized
    phase."""
    phase_index(phase)
    flag_name = CONDITIONAL_PHASE_FLAGS.get(phase)
    if flag_name is None:
        return True
    project_flags = project_flags or {}
    return bool(project_flags.get(flag_name))


def required_outputs_for_phase(phase, project_flags=None):
    """Required verification output set for phase. Returns an empty
    frozenset for a conditional phase that is not applicable to this
    project. Raises ValueError for an unrecognized phase."""
    if not is_phase_applicable(phase, project_flags):
        return frozenset()
    return REQUIRED_OUTPUTS_BY_PHASE[phase]


def phase_output_gaps(phase, produced_outputs, project_flags=None):
    """Sorted list of required outputs for phase missing from
    produced_outputs (an iterable of output names). Empty when the
    phase is not applicable or every required output is present.
    Raises ValueError for an unrecognized phase."""
    required = required_outputs_for_phase(phase, project_flags)
    produced = set(produced_outputs or [])
    return sorted(required - produced)


def phase_entry_readiness(target_phase, outputs_by_phase, project_flags=None):
    """Blocking issues that prevent entering target_phase's
    verification activities: every phase strictly before target_phase
    in PROJECT_PHASES must have its required outputs complete first.
    outputs_by_phase: {phase: iterable of produced output names}.
    Returns a list of {"issue": "prior_phase_verification_incomplete",
    "phase": ..., "missing_outputs": [...]}, one entry per incomplete
    prior phase, in phase order. Raises ValueError for an unrecognized
    target_phase."""
    target_index = phase_index(target_phase)
    issues = []
    for phase in PROJECT_PHASES[:target_index]:
        produced = (outputs_by_phase or {}).get(phase, [])
        gaps = phase_output_gaps(phase, produced, project_flags)
        if gaps:
            issues.append(
                {
                    "issue": "prior_phase_verification_incomplete",
                    "phase": phase,
                    "missing_outputs": gaps,
                }
            )
    return issues


def requirement_status_rank(status):
    """Maturity rank of a per-requirement verification status (0 =
    least mature). Raises ValueError for a status outside
    STATUS_SEQUENCE."""
    try:
        return STATUS_SEQUENCE.index(status)
    except ValueError:
        raise ValueError("unrecognized verification status %r" % (status,))


def overall_verification_status(requirement_statuses):
    """Project-wide verification status: the least mature status
    present among requirement_statuses (an iterable of per-requirement
    status strings). Raises ValueError for an empty iterable or an
    unrecognized status."""
    statuses = list(requirement_statuses)
    if not statuses:
        raise ValueError("requirement_statuses must not be empty")
    return min(statuses, key=requirement_status_rank)


def project_verification_phasing_review(project):
    """Full clause 5.2.7 phasing review for one project.

    project: {"current_phase": str, "outputs_by_phase": {phase: [str,
    ...]}, "project_flags": {...} | None, "requirement_statuses":
    {req_id: status}}. Returns {"current_phase_gaps": [...],
    "entry_readiness_issues": [...], "overall_requirement_status":
    str}. Raises ValueError for an unrecognized phase, an unrecognized
    status, or an empty requirement_statuses mapping.
    """
    current_phase = project["current_phase"]
    outputs_by_phase = project.get("outputs_by_phase") or {}
    project_flags = project.get("project_flags")
    requirement_statuses = project["requirement_statuses"]

    return {
        "current_phase_gaps": phase_output_gaps(
            current_phase, outputs_by_phase.get(current_phase, []), project_flags
        ),
        "entry_readiness_issues": phase_entry_readiness(
            current_phase, outputs_by_phase, project_flags
        ),
        "overall_requirement_status": overall_verification_status(
            requirement_statuses.values()
        ),
    }


def is_phasing_compliant(review):
    """True when a project_verification_phasing_review result has no
    current-phase gaps and no entry readiness issues. Does not require
    overall_requirement_status to be "closed" -- an in-progress
    project can be phasing-compliant while requirements are still
    being verified."""
    return not review["current_phase_gaps"] and not review["entry_readiness_issues"]
