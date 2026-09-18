"""General requirements for a space-project hazard analysis.

Anchor: ECSS-Q-ST-40-02C clause 5.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the project profile -- the segments it flies, whether it carries
   crew, whether anything comes back -- into the set of mission phases
   the hazard analysis has to reach. The phase set is derived, not
   declared, so a programme cannot shrink its own obligation by leaving
   a phase out of its plan.
2. Compare the declared phase coverage against the derived set and
   place every planned operation inside a phase. An operation sitting
   in a phase the analysis never reaches is a hole in the coverage,
   not a scheduling detail.
3. Check the custody duties: a hazard log with a named custodian and an
   update interval that does not outrun the project, and a hazard
   report raised for every severity the project agreed reports for.
4. Check that the analysis techniques and the supporting tools are
   named before the work starts, because an undeclared technique
   cannot be reviewed for fitness.
5. Check the re-analysis triggers. The events that force the analysis
   to be reopened are written down or they are left to judgement, and
   judgement is not an auditable trigger.
6. Aggregate into one verdict with the findings that produced it.

Stdlib only, offline, deterministic.
"""

# Mission phases a space project can own. The derived requirement picks
# from this ordered tuple; the order is the order the project lives it.
MISSION_PHASES = (
    "manufacturing",
    "assembly-integration-and-test",
    "transport-and-storage",
    "pre-launch-ground-operations",
    "launch-and-ascent",
    "orbital-operations",
    "crewed-habitation-operations",
    "re-entry-and-descent",
    "landing-and-recovery",
    "disposal",
)

# Phases every project owns regardless of what it flies.
BASELINE_PHASES = (
    "manufacturing",
    "assembly-integration-and-test",
    "transport-and-storage",
    "disposal",
)

VALID_SEGMENTS = ("ground", "launch", "orbital", "re-entry")

SEGMENT_PHASES = {
    "ground": ("pre-launch-ground-operations",),
    "launch": ("pre-launch-ground-operations", "launch-and-ascent"),
    "orbital": ("orbital-operations",),
    "re-entry": ("re-entry-and-descent", "landing-and-recovery"),
}

CREWED_PHASES = ("crewed-habitation-operations",)

# Severities a hazard report is owed for. A project may agree to report
# on more, never on fewer.
MANDATORY_REPORT_SEVERITIES = ("catastrophic", "critical")
VALID_SEVERITIES = ("catastrophic", "critical", "major", "minor")

# Events that reopen the analysis. Missing any of these leaves the
# reopening to judgement.
REQUIRED_REVIEW_TRIGGERS = (
    "design-change",
    "operational-anomaly",
    "procedure-change",
    "milestone-review",
    "new-hazard-identified",
)

# The longest the hazard log may sit without a status update.
MAX_LOG_UPDATE_INTERVAL_DAYS = 180

# Coverage is a quotient of two counts, so a fully covered programme can
# land a few units in the last place under 1.0.
COVERAGE_TOLERANCE = 1.0e-12


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _sequence(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, value))
    return list(value)


def validate_profile(profile):
    """Validate a project profile and return a normalized copy."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping")
    segments = _sequence("profile segments", profile.get("segments", []))
    if not segments:
        raise ValueError("profile needs at least one segment")
    for seg in segments:
        if seg not in VALID_SEGMENTS:
            raise ValueError(
                "unknown segment %r (expected one of %s)"
                % (seg, ", ".join(VALID_SEGMENTS))
            )
    crewed = _boolean("profile crewed", profile.get("crewed", False))
    if crewed and "orbital" not in segments:
        raise ValueError("a crewed profile must include the orbital segment")
    return {
        "segments": [str(s) for s in segments],
        "crewed": crewed,
    }


def required_phases(profile):
    """Mission phases the hazard analysis has to reach, in project order."""
    norm = validate_profile(profile)
    needed = set(BASELINE_PHASES)
    for seg in norm["segments"]:
        needed.update(SEGMENT_PHASES[seg])
    if norm["crewed"]:
        needed.update(CREWED_PHASES)
    return tuple(p for p in MISSION_PHASES if p in needed)


def validate_programme(programme):
    """Validate a hazard-analysis programme record and normalize it."""
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    profile = validate_profile(programme.get("profile"))
    covered = _sequence("covered_phases", programme.get("covered_phases", []))
    for phase in covered:
        if phase not in MISSION_PHASES:
            raise ValueError("unknown mission phase %r" % (phase,))
    operations = _sequence("operations", programme.get("operations", []))
    norm_ops = []
    seen_ops = set()
    for op in operations:
        if not isinstance(op, dict):
            raise ValueError("each operation must be a mapping")
        op_id = _string("operation id", op.get("id"))
        if op_id in seen_ops:
            raise ValueError("duplicate operation id %r" % (op_id,))
        seen_ops.add(op_id)
        phase = op.get("phase")
        if phase not in MISSION_PHASES:
            raise ValueError("operation %s has unknown phase %r" % (op_id, phase))
        norm_ops.append({"id": op_id, "phase": phase})
    log = programme.get("hazard_log")
    if not isinstance(log, dict):
        raise ValueError("programme needs a hazard_log mapping")
    custodian = log.get("custodian")
    if custodian is not None:
        custodian = _string("hazard_log custodian", custodian)
    interval = log.get("update_interval_days")
    if interval is not None:
        if not isinstance(interval, int) or isinstance(interval, bool):
            raise ValueError("hazard_log update_interval_days must be an int")
        if interval <= 0:
            raise ValueError("hazard_log update_interval_days must be positive")
    report_sevs = _sequence(
        "report_severities", programme.get("report_severities", [])
    )
    for sev in report_sevs:
        if sev not in VALID_SEVERITIES:
            raise ValueError("unknown report severity %r" % (sev,))
    techniques = _sequence("techniques", programme.get("techniques", []))
    tools = _sequence("tools", programme.get("tools", []))
    triggers = _sequence("review_triggers", programme.get("review_triggers", []))
    return {
        "profile": profile,
        "covered_phases": [str(p) for p in covered],
        "operations": norm_ops,
        "hazard_log": {
            "maintained": _boolean(
                "hazard_log maintained", log.get("maintained", False)
            ),
            "custodian": custodian,
            "update_interval_days": interval,
        },
        "report_severities": [str(s) for s in report_sevs],
        "techniques": [_string("technique", t) for t in techniques],
        "tools": [_string("tool", t) for t in tools],
        "review_triggers": [str(t) for t in triggers],
    }


def phase_coverage(programme):
    """Derived phases against declared phases, with the fraction covered."""
    norm = validate_programme(programme)
    required = required_phases(norm["profile"])
    declared = set(norm["covered_phases"])
    covered = [p for p in required if p in declared]
    missing = [p for p in required if p not in declared]
    outside = [p for p in norm["covered_phases"] if p not in required]
    fraction = float(len(covered)) / float(len(required))
    return {
        "required": list(required),
        "covered": covered,
        "missing": missing,
        "outside_scope": sorted(set(outside)),
        "coverage_fraction": fraction,
    }


def uncovered_operations(programme):
    """Planned operations that sit in a phase the analysis never reaches."""
    norm = validate_programme(programme)
    declared = set(norm["covered_phases"])
    return [op["id"] for op in norm["operations"] if op["phase"] not in declared]


def log_duty_findings(programme):
    """Findings about hazard-log custody and hazard-report duty."""
    norm = validate_programme(programme)
    log = norm["hazard_log"]
    findings = []
    if not log["maintained"]:
        findings.append("hazard-log-not-maintained")
    if log["custodian"] is None:
        findings.append("hazard-log-has-no-named-custodian")
    if log["update_interval_days"] is None:
        findings.append("hazard-log-update-interval-not-agreed")
    elif log["update_interval_days"] > MAX_LOG_UPDATE_INTERVAL_DAYS:
        findings.append("hazard-log-update-interval-too-long")
    declared = set(norm["report_severities"])
    for sev in MANDATORY_REPORT_SEVERITIES:
        if sev not in declared:
            findings.append("no-hazard-report-duty-for-%s-hazards" % sev)
    return findings


def method_declaration_findings(programme):
    """Findings about undeclared analysis techniques and tools."""
    norm = validate_programme(programme)
    findings = []
    if not norm["techniques"]:
        findings.append("no-analysis-technique-declared")
    if not norm["tools"]:
        findings.append("no-supporting-tool-declared")
    return findings


def missing_review_triggers(programme):
    """Re-analysis triggers the programme leaves to judgement."""
    norm = validate_programme(programme)
    declared = set(norm["review_triggers"])
    return [t for t in REQUIRED_REVIEW_TRIGGERS if t not in declared]


def assess_hazard_analysis_requirements(programme):
    """Assess one hazard-analysis programme against clause 5.1."""
    norm = validate_programme(programme)
    coverage = phase_coverage(norm)
    orphan_ops = uncovered_operations(norm)
    findings = []
    for phase in coverage["missing"]:
        findings.append("mission-phase-not-covered:%s" % phase)
    for op_id in orphan_ops:
        findings.append("operation-outside-covered-phases:%s" % op_id)
    findings.extend(log_duty_findings(norm))
    findings.extend(method_declaration_findings(norm))
    for trigger in missing_review_triggers(norm):
        findings.append("review-trigger-not-declared:%s" % trigger)
    return {
        "coverage": coverage,
        "uncovered_operations": orphan_ops,
        "missing_review_triggers": missing_review_triggers(norm),
        "findings": findings,
        "compliant": not findings,
    }
