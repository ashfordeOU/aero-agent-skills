#!/usr/bin/env python3
"""ECSS-E-ST-10-11C Annex C HFE continuous assessment process DRD —
generation and validation (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors engineering standard's normative Annex C specifies a Data
Requirements Document for the HFE continuous assessment process report;
each report must identify its assessment scope (system under review,
mission phase, review gate), the assessment method or methods applied
(inspection, walkthrough, simulation, or user trial), a finding register
where each entry carries an HFE criterion label, a severity level
(critical, major, minor, or observation), and a recommendation, and a
corrective-action register that links each finding to an owner and a
status (open, in_progress, accepted, or closed). The overall result is
derived from the open severity profile: FAIL when any critical finding
is unresolved, CONDITIONAL when a critical finding is in progress or any
major finding is open or in progress, PASS otherwise. This module
implements: mission-phase validation, assessment-method validation,
finding-severity categorization, finding-record and corrective-action
completeness checks, resolution-status derivation, overall-result
derivation, mandatory-section presence check, and full-report
validation; it does not define the HFE criterion vocabulary or the
measurement models used during the assessment itself.
"""

VALID_MISSION_PHASES = frozenset({
    "pre_phase_a", "phase_a", "phase_b", "phase_c",
    "phase_d", "phase_e", "phase_f",
})

VALID_ASSESSMENT_METHODS = frozenset({
    "inspection", "walkthrough", "simulation", "user_trial",
})

FINDING_SEVERITY_LEVELS = ("critical", "major", "minor", "observation")

FINDING_REQUIRED_FIELDS = frozenset({
    "id", "description", "hfe_criterion", "severity", "recommendation",
})

ACTION_REQUIRED_FIELDS = frozenset({
    "finding_id", "action", "owner", "status",
})

VALID_ACTION_STATUSES = frozenset({
    "open", "in_progress", "accepted", "closed",
})

DRD_MANDATORY_SECTIONS = frozenset({
    "report_id",
    "report_date",
    "assessment_scope",
    "mission_phase",
    "review_gate",
    "assessment_methods",
    "hfe_criteria_covered",
    "findings",
    "corrective_actions",
})


def validate_mission_phase(phase):
    """Accept a mission phase token and return it; raise ValueError when
    the token is not one of the recognized phases (pre_phase_a through
    phase_f) per ECSS-E-ST-10-11C Table 1."""
    if phase not in VALID_MISSION_PHASES:
        raise ValueError(
            "unrecognized mission phase %r; expected one of %s"
            % (phase, sorted(VALID_MISSION_PHASES))
        )
    return phase


def validate_assessment_method(method):
    """Accept an assessment method token and return it; raise ValueError
    when the token is not one of the DRD-recognized methods (inspection,
    walkthrough, simulation, user_trial)."""
    if method not in VALID_ASSESSMENT_METHODS:
        raise ValueError(
            "unrecognized assessment method %r; expected one of %s"
            % (method, sorted(VALID_ASSESSMENT_METHODS))
        )
    return method


def categorize_finding_severity(severity):
    """Confirm a finding severity label is one of the four recognized
    levels (critical, major, minor, observation) and return it; raise
    ValueError for an unrecognized label."""
    if severity not in FINDING_SEVERITY_LEVELS:
        raise ValueError(
            "unrecognized finding severity %r; expected one of %s"
            % (severity, FINDING_SEVERITY_LEVELS)
        )
    return severity


def check_finding_record(finding):
    """Validate a finding dict against the DRD required fields.
    Returns a list of issue strings; an empty list means the record is
    structurally complete. Raises ValueError when the severity field is
    present but not a recognized level. Does not mutate finding."""
    issues = []
    for field in sorted(FINDING_REQUIRED_FIELDS):
        if not finding.get(field):
            issues.append("finding missing required field: %s" % field)
    severity = finding.get("severity")
    if severity:
        categorize_finding_severity(severity)
    return issues


def check_action_record(action):
    """Validate a corrective-action dict against the DRD required fields.
    Returns a list of issue strings; an empty list means the record is
    structurally complete. Does not mutate action."""
    issues = []
    for field in sorted(ACTION_REQUIRED_FIELDS):
        if not action.get(field):
            issues.append("action missing required field: %s" % field)
    status = action.get("status")
    if status and status not in VALID_ACTION_STATUSES:
        issues.append(
            "action status %r not in %s"
            % (status, sorted(VALID_ACTION_STATUSES))
        )
    return issues


def _finding_resolution_status(finding_id, corrective_actions):
    """Best resolution status for one finding across its linked corrective
    actions: 'closed' when any linked action is closed, 'in_progress' when
    any linked action is in_progress or accepted (but none closed), 'open'
    when no actions are linked or all linked actions have status 'open'."""
    linked = [
        a for a in corrective_actions
        if a.get("finding_id") == finding_id
    ]
    if not linked:
        return "open"
    statuses = {a.get("status") for a in linked}
    if "closed" in statuses:
        return "closed"
    if "in_progress" in statuses or "accepted" in statuses:
        return "in_progress"
    return "open"


def derive_overall_result(findings, corrective_actions):
    """Derive the DRD overall assessment result from the open severity
    profile of the finding register against the corrective-action register.

    Returns 'FAIL' when any critical finding is unresolved (no linked
    action or all linked actions are open), 'CONDITIONAL' when any
    critical finding has a best action status of in_progress or accepted,
    or any major finding is open or in_progress, and 'PASS' otherwise.
    Does not mutate either argument."""
    for finding in findings:
        if finding.get("severity") == "critical":
            resolution = _finding_resolution_status(
                finding.get("id"), corrective_actions
            )
            if resolution == "open":
                return "FAIL"
    for finding in findings:
        severity = finding.get("severity")
        resolution = _finding_resolution_status(
            finding.get("id"), corrective_actions
        )
        if severity == "critical" and resolution == "in_progress":
            return "CONDITIONAL"
        if severity == "major" and resolution in ("open", "in_progress"):
            return "CONDITIONAL"
    return "PASS"


def check_drd_missing_sections(report):
    """Return a frozenset of mandatory DRD section names absent from the
    report dict (key absent or mapped to None). An empty frozenset means
    the report is structurally complete per Annex C. Does not mutate
    report."""
    return frozenset(
        section
        for section in DRD_MANDATORY_SECTIONS
        if section not in report or report[section] is None
    )


def validate_assessment_report(report):
    """Full Annex C DRD validation for one HFE continuous assessment report.

    report: dict whose keys correspond to DRD_MANDATORY_SECTIONS.
    Returns {
        'missing_sections': frozenset of absent mandatory section names,
        'finding_issues': list of field-level issue strings,
        'action_issues': list of field-level issue strings,
        'overall_result': 'FAIL' | 'CONDITIONAL' | 'PASS',
    }. Raises ValueError for an unrecognized finding severity. Does not
    mutate report."""
    missing = check_drd_missing_sections(report)
    finding_issues = []
    for finding in report.get("findings") or []:
        finding_issues.extend(check_finding_record(finding))
    action_issues = []
    for action in report.get("corrective_actions") or []:
        action_issues.extend(check_action_record(action))
    overall = derive_overall_result(
        report.get("findings") or [],
        report.get("corrective_actions") or [],
    )
    return {
        "missing_sections": missing,
        "finding_issues": finding_issues,
        "action_issues": action_issues,
        "overall_result": overall,
    }
