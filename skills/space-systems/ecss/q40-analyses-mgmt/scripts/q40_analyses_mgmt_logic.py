"""Selection and management of the safety analysis suite per lifecycle phase.

Anchor: ECSS-Q-ST-40C clauses 7.2 to 7.4 with the Annex A analyses
applicability matrix (which safety analyses a project owes at which phase, and
how the worst severity carried moves an analysis between mandatory and
recommended). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Hold the project phases in order and the applicability matrix that maps
   each analysis onto each phase.
2. Degrade a nominally mandatory analysis to recommended when the worst
   severity the project carries does not reach the severity floor that
   analysis exists for, so a benign payload is not made to run a suite built
   for a catastrophic one.
3. Resolve, for a phase and a worst severity, the mandatory set and the
   recommended set.
4. Compare the declared analysis plan against that resolution: the mandatory
   analyses missing from the plan, the recommended ones nobody took up, and
   the planned analyses the phase has no use for.
5. Flag every planned analysis whose due phase falls after the phase where it
   is owed, and report the coverage the plan actually achieves.
"""

__all__ = [
    "PROJECT_PHASES",
    "PHASE_REVIEWS",
    "ANALYSES",
    "APPLICABILITY",
    "SEVERITY_ORDER",
    "SEVERITY_FLOOR",
    "validate_phase",
    "validate_severity",
    "validate_analysis",
    "severity_rank",
    "phase_index",
    "applicability",
    "effective_applicability",
    "required_analyses",
    "recommended_analyses",
    "validate_plan",
    "plan_gaps",
    "late_analyses",
    "coverage_ratio",
    "assess_analyses_management",
]

# Project phases in lifecycle order.
PROJECT_PHASES = ("phase-0", "phase-a", "phase-b", "phase-c", "phase-d", "phase-e")

# The review that closes each phase; the deadline an analysis is late against.
PHASE_REVIEWS = {
    "phase-0": "mission-definition-review",
    "phase-a": "preliminary-requirements-review",
    "phase-b": "preliminary-design-review",
    "phase-c": "critical-design-review",
    "phase-d": "qualification-and-acceptance-review",
    "phase-e": "flight-readiness-review",
}

# The analyses the matrix covers.
ANALYSES = (
    "hazard-analysis",
    "failure-modes-and-effects-analysis",
    "fault-tree-analysis",
    "common-cause-analysis",
    "sneak-analysis",
    "human-factors-safety-analysis",
    "warning-time-analysis",
    "software-safety-analysis",
)

# Severity categories, most severe first.
SEVERITY_ORDER = ("catastrophic", "critical", "major", "minor")

# The Annex A style applicability matrix: analysis against project phase.
APPLICABILITY = {
    "hazard-analysis": {
        "phase-0": "recommended",
        "phase-a": "mandatory",
        "phase-b": "mandatory",
        "phase-c": "mandatory",
        "phase-d": "mandatory",
        "phase-e": "recommended",
    },
    "failure-modes-and-effects-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "recommended",
        "phase-b": "mandatory",
        "phase-c": "mandatory",
        "phase-d": "mandatory",
        "phase-e": "recommended",
    },
    "fault-tree-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "recommended",
        "phase-b": "mandatory",
        "phase-c": "mandatory",
        "phase-d": "recommended",
        "phase-e": "not-applicable",
    },
    "common-cause-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "not-applicable",
        "phase-b": "recommended",
        "phase-c": "mandatory",
        "phase-d": "recommended",
        "phase-e": "not-applicable",
    },
    "sneak-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "not-applicable",
        "phase-b": "not-applicable",
        "phase-c": "mandatory",
        "phase-d": "recommended",
        "phase-e": "not-applicable",
    },
    "human-factors-safety-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "recommended",
        "phase-b": "mandatory",
        "phase-c": "mandatory",
        "phase-d": "mandatory",
        "phase-e": "mandatory",
    },
    "warning-time-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "not-applicable",
        "phase-b": "recommended",
        "phase-c": "mandatory",
        "phase-d": "mandatory",
        "phase-e": "mandatory",
    },
    "software-safety-analysis": {
        "phase-0": "not-applicable",
        "phase-a": "recommended",
        "phase-b": "mandatory",
        "phase-c": "mandatory",
        "phase-d": "mandatory",
        "phase-e": "recommended",
    },
}

# The worst severity a project must carry before an analysis is owed outright.
SEVERITY_FLOOR = {
    "hazard-analysis": "minor",
    "failure-modes-and-effects-analysis": "major",
    "fault-tree-analysis": "critical",
    "common-cause-analysis": "critical",
    "sneak-analysis": "catastrophic",
    "human-factors-safety-analysis": "critical",
    "warning-time-analysis": "critical",
    "software-safety-analysis": "critical",
}


def _token(value, label, allowed):
    """Return a trimmed lowercase token drawn from allowed; raise otherwise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if token not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (label, ", ".join(allowed), value))
    return token


def validate_phase(value):
    """Return a known project phase."""
    return _token(value, "phase", PROJECT_PHASES)


def validate_severity(value):
    """Return a known severity category."""
    return _token(value, "severity", SEVERITY_ORDER)


def validate_analysis(value):
    """Return a known analysis name."""
    return _token(value, "analysis", ANALYSES)


def severity_rank(severity):
    """Return the rank of a severity; zero is the most severe."""
    return SEVERITY_ORDER.index(validate_severity(severity))


def phase_index(phase):
    """Return the lifecycle position of a phase; zero is the earliest."""
    return PROJECT_PHASES.index(validate_phase(phase))


def applicability(analysis, phase):
    """Return the raw matrix entry for an analysis at a phase."""
    return APPLICABILITY[validate_analysis(analysis)][validate_phase(phase)]


def effective_applicability(analysis, phase, worst_severity):
    """Return the matrix entry after the severity floor is applied."""
    name = validate_analysis(analysis)
    status = applicability(name, phase)
    if status != "mandatory":
        return status
    if severity_rank(worst_severity) > severity_rank(SEVERITY_FLOOR[name]):
        return "recommended"
    return "mandatory"


def required_analyses(phase, worst_severity):
    """Return the analyses a phase owes outright, in declaration order."""
    return tuple(
        name
        for name in ANALYSES
        if effective_applicability(name, phase, worst_severity) == "mandatory"
    )


def recommended_analyses(phase, worst_severity):
    """Return the analyses a phase recommends, in declaration order."""
    return tuple(
        name
        for name in ANALYSES
        if effective_applicability(name, phase, worst_severity) == "recommended"
    )


def validate_plan(planned):
    """Return the normalised analysis plan: one entry per analysis."""
    if not isinstance(planned, (list, tuple)):
        raise ValueError("planned must be a sequence of plan entries")
    result = []
    seen = set()
    for index, entry in enumerate(planned):
        if not isinstance(entry, dict):
            raise ValueError("planned[%d] must be a mapping" % index)
        unknown = sorted(key for key in entry if key not in ("analysis", "due_phase"))
        if unknown:
            raise ValueError(
                "planned[%d] carries unknown keys: %s" % (index, ", ".join(unknown))
            )
        name = validate_analysis(entry.get("analysis"))
        if name in seen:
            raise ValueError("planned lists %r twice" % name)
        seen.add(name)
        result.append({"analysis": name, "due_phase": validate_phase(entry.get("due_phase"))})
    return result


def plan_gaps(planned, phase, worst_severity):
    """Return what the plan misses, skips and carries without a use."""
    entries = validate_plan(planned)
    names = {entry["analysis"] for entry in entries}
    mandatory = required_analyses(phase, worst_severity)
    advised = recommended_analyses(phase, worst_severity)
    return {
        "missing_mandatory": tuple(name for name in mandatory if name not in names),
        "recommended_not_planned": tuple(name for name in advised if name not in names),
        "planned_without_use": tuple(
            name
            for name in ANALYSES
            if name in names
            and effective_applicability(name, phase, worst_severity) == "not-applicable"
        ),
    }


def late_analyses(planned, phase, worst_severity):
    """Return the mandatory analyses whose due phase falls after this phase."""
    entries = validate_plan(planned)
    limit = phase_index(phase)
    mandatory = set(required_analyses(phase, worst_severity))
    return tuple(
        entry["analysis"]
        for entry in entries
        if entry["analysis"] in mandatory and phase_index(entry["due_phase"]) > limit
    )


def coverage_ratio(planned, phase, worst_severity):
    """Return the share of the mandatory set the plan covers."""
    entries = validate_plan(planned)
    names = {entry["analysis"] for entry in entries}
    mandatory = required_analyses(phase, worst_severity)
    if not mandatory:
        return 1.0
    covered = sum(1 for name in mandatory if name in names)
    return covered / len(mandatory)


def assess_analyses_management(spec):
    """Scope and grade the safety analysis suite for one phase.

    spec keys: phase, worst_severity, planned (sequence of {analysis,
    due_phase}).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("phase", "worst_severity", "planned"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    phase = validate_phase(spec["phase"])
    severity = validate_severity(spec["worst_severity"])
    entries = validate_plan(spec["planned"])
    mandatory = required_analyses(phase, severity)
    advised = recommended_analyses(phase, severity)
    gaps = plan_gaps(entries, phase, severity)
    late = late_analyses(entries, phase, severity)
    findings = []
    for name in gaps["missing_mandatory"]:
        findings.append("%s is owed at %s and is not in the plan" % (name, phase))
    for name in late:
        findings.append(
            "%s is owed by the %s and is planned for a later phase"
            % (name, PHASE_REVIEWS[phase])
        )
    for name in gaps["planned_without_use"]:
        findings.append("%s is planned at %s where the matrix has no use for it" % (name, phase))
    return {
        "phase": phase,
        "closing_review": PHASE_REVIEWS[phase],
        "worst_severity": severity,
        "mandatory": mandatory,
        "recommended": advised,
        "planned": tuple(entry["analysis"] for entry in entries),
        "missing_mandatory": gaps["missing_mandatory"],
        "recommended_not_planned": gaps["recommended_not_planned"],
        "planned_without_use": gaps["planned_without_use"],
        "late": late,
        "coverage_ratio": coverage_ratio(entries, phase, severity),
        "findings": findings,
        "verdict": "suite-complete" if not findings else "suite-incomplete",
    }
