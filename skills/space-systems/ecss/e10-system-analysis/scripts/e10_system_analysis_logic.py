#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.3.1 system analysis scope and schedule
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard requires a project to
scope and schedule the system analyses that support its design
decisions, grouped into five types -- mission, functional, interface,
environmental, operational -- each with a defined objective and defined
outputs. A project phase (feasibility, preliminary design, detailed
design, verification) accumulates a required set of analysis types, and
each analysis type has an earliest phase that first requires it; an
analysis must be scheduled to complete no later than that earliest
phase to be useful to the decision it supports. This module implements
analysis-type categorization, objective/output completeness checking,
schedule-versus-earliest-requirement checking, and phase-coverage
checking; it does not perform the technical content of any individual
analysis (the mission, functional, interface, environmental, or
operational study itself).
"""

PHASES = ("feasibility", "preliminary_design", "detailed_design", "verification")
PHASE_ORDER = {phase: index for index, phase in enumerate(PHASES)}

ANALYSIS_TYPES = frozenset(
    {"mission", "functional", "interface", "environmental", "operational"}
)

# Required analysis types accumulate: each phase requires everything an
# earlier phase required, plus whatever is newly added at that phase.
REQUIRED_ANALYSES_BY_PHASE = {
    "feasibility": frozenset({"mission"}),
    "preliminary_design": frozenset({"mission", "functional", "environmental"}),
    "detailed_design": frozenset(
        {"mission", "functional", "interface", "environmental", "operational"}
    ),
    "verification": frozenset(
        {"mission", "functional", "interface", "environmental", "operational"}
    ),
}


def validate_phase(phase):
    """Returns phase if it is a recognized project phase. Raises
    ValueError otherwise."""
    if phase not in PHASE_ORDER:
        raise ValueError(
            "unrecognized project phase %r under E-ST-10C clause 5.3.1" % (phase,)
        )
    return phase


def validate_analysis_type(analysis_type):
    """Returns analysis_type if it is one of the five recognized system
    analysis types. Raises ValueError otherwise."""
    if analysis_type not in ANALYSIS_TYPES:
        raise ValueError(
            "unrecognized system analysis type %r under E-ST-10C clause 5.3.1"
            % (analysis_type,)
        )
    return analysis_type


def required_analysis_types(phase):
    """Cumulative set of analysis types required by phase. Raises
    ValueError for an unrecognized phase."""
    validate_phase(phase)
    return REQUIRED_ANALYSES_BY_PHASE[phase]


def earliest_required_phase(analysis_type):
    """First phase (in PHASES order) whose required set includes
    analysis_type. Raises ValueError for an unrecognized analysis
    type."""
    validate_analysis_type(analysis_type)
    for phase in PHASES:
        if analysis_type in REQUIRED_ANALYSES_BY_PHASE[phase]:
            return phase
    raise ValueError(
        "no project phase requires system analysis type %r" % (analysis_type,)
    )


def missing_required_analyses(phase, scoped_analysis_types):
    """Sorted list of analysis types required by phase but absent from
    scoped_analysis_types. Raises ValueError for an unrecognized
    phase. Does not mutate scoped_analysis_types."""
    required = required_analysis_types(phase)
    return sorted(required - set(scoped_analysis_types))


def analysis_definition_violations(analysis):
    """Violation list (empty if fully scoped and scheduled) for one
    system analysis.

    analysis: {"analysis_id": str, "analysis_type": str,
    "objective": str | None, "outputs": list | None,
    "scheduled_phase": str | None}. Raises ValueError for an
    unrecognized analysis_type or an unrecognized (non-None)
    scheduled_phase."""
    analysis_id = analysis["analysis_id"]
    analysis_type = analysis["analysis_type"]
    validate_analysis_type(analysis_type)

    violations = []
    if not analysis.get("objective"):
        violations.append({"issue": "missing_objective", "analysis": analysis_id})
    if not analysis.get("outputs"):
        violations.append({"issue": "missing_outputs", "analysis": analysis_id})

    scheduled_phase = analysis.get("scheduled_phase")
    if scheduled_phase is None:
        violations.append({"issue": "missing_schedule", "analysis": analysis_id})
    else:
        validate_phase(scheduled_phase)
        earliest = earliest_required_phase(analysis_type)
        if PHASE_ORDER[scheduled_phase] > PHASE_ORDER[earliest]:
            violations.append(
                {
                    "issue": "analysis_scheduled_too_late",
                    "analysis": analysis_id,
                    "scheduled_phase": scheduled_phase,
                    "earliest_required_phase": earliest,
                }
            )
    return violations


def system_analysis_review(project):
    """Full clause 5.3.1 scope-and-schedule review for one project.

    project: {"phase": str, "analyses": [{"analysis_id": str,
    "analysis_type": str, "objective": str | None,
    "outputs": list | None, "scheduled_phase": str | None}, ...]}.
    Raises ValueError for an unrecognized project phase, analysis
    type, or scheduled phase. Returns {"per_analysis":
    {analysis_id: [violations]}, "missing_analyses": [types]}."""
    phase = project["phase"]
    validate_phase(phase)

    per_analysis = {}
    scoped_types = set()
    for analysis in project.get("analyses", []):
        per_analysis[analysis["analysis_id"]] = analysis_definition_violations(
            analysis
        )
        scoped_types.add(analysis["analysis_type"])

    return {
        "per_analysis": per_analysis,
        "missing_analyses": missing_required_analyses(phase, scoped_types),
    }


def is_system_analysis_scoped(review):
    """True when a system_analysis_review result has no missing
    required analysis types and no per-analysis violations -- the
    project satisfies clause 5.3.1 for this assessment."""
    if review["missing_analyses"]:
        return False
    return all(len(violations) == 0 for violations in review["per_analysis"].values())
