"""Step 1 of the hazard-analysis process: implementation requirements.

Anchor: ECSS-Q-ST-40-02C clause 5.2.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the project type. Crew presence, the segments flown, whether
   hardware is recovered and whether a third party is exposed are the
   attributes that decide how deep the analysis has to go. Depth is
   derived from them, never volunteered.
2. Derive the analysis scope elements the project owes -- the item
   classes, interfaces and operational regimes the hazard analysis has
   to walk -- from those same attributes.
3. Derive the technique set. A deeper project does not simply run the
   same techniques harder; it owes techniques an uncrewed spacecraft
   does not, and a ground segment owes techniques an orbital one does
   not.
4. Derive the disciplines the safety team must hold, so a team list
   can be checked against the analysis it is meant to perform rather
   than against a headcount.
5. Compare each derived set against the declared plan and report what
   is missing, what was declared outside the derived set, and whether
   the declared depth is under the derived one.

Stdlib only, offline, deterministic.
"""

VALID_SEGMENTS = ("ground", "launch", "orbital", "re-entry")

# Analysis depth, shallow to deep. The ordinal is the comparison key.
DEPTH_LEVELS = ("baseline", "enhanced", "crewed-safety-critical")
DEPTH_ORDINAL = {name: i for i, name in enumerate(DEPTH_LEVELS)}

# Scope elements by driver. Every project owns the baseline set.
BASELINE_SCOPE = (
    "flight-hardware-items",
    "ground-support-equipment",
    "handling-and-transport-operations",
    "software-driven-functions",
)

SEGMENT_SCOPE = {
    "ground": ("facility-and-personnel-interfaces",),
    "launch": ("launch-vehicle-interfaces", "range-third-party-exposure"),
    "orbital": ("on-orbit-autonomous-operations", "space-environment-interactions"),
    "re-entry": ("re-entry-thermal-and-debris-footprint", "recovery-operations"),
}

CREWED_SCOPE = (
    "crew-interfaces-and-habitability",
    "crew-emergency-and-escape-provisions",
)

RECOVERY_SCOPE = ("post-flight-safing-operations",)

# Techniques by driver.
BASELINE_TECHNIQUES = (
    "generic-hazard-library-walkthrough",
    "functional-hazard-identification",
    "operational-hazard-identification",
)

SEGMENT_TECHNIQUES = {
    "ground": ("ground-operations-task-analysis",),
    "launch": ("launch-phase-sequence-analysis",),
    "orbital": ("on-orbit-failure-propagation-analysis",),
    "re-entry": ("re-entry-debris-casualty-assessment",),
}

CREWED_TECHNIQUES = (
    "crew-task-and-error-analysis",
    "failure-tolerance-demonstration",
)

THIRD_PARTY_TECHNIQUES = ("third-party-risk-assessment",)

# Disciplines by driver.
BASELINE_DISCIPLINES = (
    "system-engineering",
    "product-assurance-safety",
    "operations-engineering",
)

SEGMENT_DISCIPLINES = {
    "ground": ("facility-safety",),
    "launch": ("propulsion-and-pyrotechnics",),
    "orbital": ("avionics-and-software-safety",),
    "re-entry": ("thermal-protection-engineering",),
}

CREWED_DISCIPLINES = ("human-factors", "life-support-engineering")


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _sequence(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, value))
    return list(value)


def validate_project_type(project):
    """Validate the project-type record and return a normalized copy."""
    if not isinstance(project, dict):
        raise ValueError("project must be a mapping")
    name = project.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project needs a non-empty string name")
    segments = _sequence("project segments", project.get("segments", []))
    if not segments:
        raise ValueError("project needs at least one segment")
    for seg in segments:
        if seg not in VALID_SEGMENTS:
            raise ValueError(
                "unknown segment %r (expected one of %s)"
                % (seg, ", ".join(VALID_SEGMENTS))
            )
    crewed = _boolean("project crewed", project.get("crewed", False))
    recovered = _boolean("project recovered", project.get("recovered", False))
    third_party = _boolean(
        "project third_party_exposure", project.get("third_party_exposure", False)
    )
    if crewed and "orbital" not in segments and "re-entry" not in segments:
        raise ValueError(
            "a crewed project must fly an orbital or a re-entry segment"
        )
    if recovered and "re-entry" not in segments:
        raise ValueError("a recovered project must fly the re-entry segment")
    return {
        "name": name.strip(),
        "segments": [str(s) for s in segments],
        "crewed": crewed,
        "recovered": recovered,
        "third_party_exposure": third_party,
    }


def required_depth(project):
    """Analysis depth the project type forces."""
    norm = validate_project_type(project)
    if norm["crewed"]:
        return "crewed-safety-critical"
    if norm["third_party_exposure"] or "launch" in norm["segments"]:
        return "enhanced"
    return "baseline"


def _collect(baseline, segment_map, segments, extras):
    out = set(baseline)
    for seg in segments:
        out.update(segment_map.get(seg, ()))
    for extra in extras:
        out.update(extra)
    return sorted(out)


def required_scope_elements(project):
    """Scope elements the hazard analysis has to walk, sorted."""
    norm = validate_project_type(project)
    extras = []
    if norm["crewed"]:
        extras.append(CREWED_SCOPE)
    if norm["recovered"]:
        extras.append(RECOVERY_SCOPE)
    return _collect(BASELINE_SCOPE, SEGMENT_SCOPE, norm["segments"], extras)


def required_techniques(project):
    """Analysis techniques the project type owes, sorted."""
    norm = validate_project_type(project)
    extras = []
    if norm["crewed"]:
        extras.append(CREWED_TECHNIQUES)
    if norm["third_party_exposure"]:
        extras.append(THIRD_PARTY_TECHNIQUES)
    return _collect(BASELINE_TECHNIQUES, SEGMENT_TECHNIQUES, norm["segments"], extras)


def required_disciplines(project):
    """Specialist disciplines the safety team must hold, sorted."""
    norm = validate_project_type(project)
    extras = []
    if norm["crewed"]:
        extras.append(CREWED_DISCIPLINES)
    return _collect(
        BASELINE_DISCIPLINES, SEGMENT_DISCIPLINES, norm["segments"], extras
    )


def _gap(required, declared, label):
    declared_set = set(declared)
    missing = [item for item in required if item not in declared_set]
    extra = sorted(set(declared) - set(required))
    return {
        "label": label,
        "required": list(required),
        "declared": sorted(set(declared)),
        "missing": missing,
        "declared_outside_requirement": extra,
    }


def validate_plan(plan):
    """Validate the declared step-1 plan and normalize it."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    depth = plan.get("declared_depth")
    if depth not in DEPTH_LEVELS:
        raise ValueError(
            "declared_depth must be one of %s, got %r" % (", ".join(DEPTH_LEVELS), depth)
        )
    return {
        "declared_depth": depth,
        "scope_elements": [
            str(s) for s in _sequence("plan scope_elements", plan.get("scope_elements", []))
        ],
        "techniques": [
            str(s) for s in _sequence("plan techniques", plan.get("techniques", []))
        ],
        "team_disciplines": [
            str(s)
            for s in _sequence(
                "plan team_disciplines", plan.get("team_disciplines", [])
            )
        ],
    }


def depth_finding(project, plan):
    """Finding when the declared depth sits under the derived one."""
    needed = required_depth(project)
    declared = validate_plan(plan)["declared_depth"]
    if DEPTH_ORDINAL[declared] < DEPTH_ORDINAL[needed]:
        return "declared-depth-below-required-%s" % needed
    return None


def assess_step1_implementation(project, plan):
    """Assess the step-1 implementation requirements of clause 5.2.1."""
    norm_project = validate_project_type(project)
    norm_plan = validate_plan(plan)
    gaps = [
        _gap(required_scope_elements(norm_project), norm_plan["scope_elements"], "scope"),
        _gap(required_techniques(norm_project), norm_plan["techniques"], "technique"),
        _gap(
            required_disciplines(norm_project),
            norm_plan["team_disciplines"],
            "discipline",
        ),
    ]
    findings = []
    depth = depth_finding(norm_project, norm_plan)
    if depth:
        findings.append(depth)
    for gap in gaps:
        for item in gap["missing"]:
            findings.append("%s-not-planned:%s" % (gap["label"], item))
    return {
        "project": norm_project["name"],
        "required_depth": required_depth(norm_project),
        "declared_depth": norm_plan["declared_depth"],
        "gaps": gaps,
        "findings": findings,
        "complete": not findings,
    }
