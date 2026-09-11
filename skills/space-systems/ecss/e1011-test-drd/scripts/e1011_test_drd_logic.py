#!/usr/bin/env python3
"""ECSS-E-ST-10-11C Annex D HFE test report DRD validation
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
Human Factors Engineering standard's Annex D specifies a normative
Document Requirements Definition (DRD) for the HFE test report. The
report must include eight mandatory sections (document identification,
objectives, test environment, participants, test scenarios, results,
findings, recommendations); participant counts must meet minimums that
vary by test type (formative: 3, summative: 5); each finding must carry
a severity category drawn from exactly three levels (critical, major,
minor); every finding must be traceable to at least one recommendation
by finding identifier; and all planned test scenarios must appear in the
execution record. This module implements section completeness checking,
participant count validation, finding severity validation,
finding-to-recommendation linkage checking, and scenario coverage
checking; it does not define success criteria for individual test results
or specify the format of quantitative metrics.
"""

REQUIRED_REPORT_SECTIONS = frozenset({
    "document_id",
    "objectives",
    "test_environment",
    "participants",
    "test_scenarios",
    "results",
    "findings",
    "recommendations",
})

FINDING_SEVERITY_LEVELS = frozenset({"critical", "major", "minor"})

MIN_PARTICIPANTS = {
    "formative": 3,
    "summative": 5,
}

TEST_TYPES = frozenset({"formative", "summative"})


def check_required_sections(present_sections):
    """Return a sorted list of section names missing from present_sections.

    Each name in the returned list is a DRD non-conformance. Returns an
    empty list when all required sections are present."""
    present = frozenset(present_sections)
    return sorted(REQUIRED_REPORT_SECTIONS - present)


def validate_finding_severity(severity):
    """Return severity if it is a recognized HFE finding level.

    Raises ValueError for any string not in {critical, major, minor}."""
    if severity not in FINDING_SEVERITY_LEVELS:
        raise ValueError(
            "unrecognized finding severity %r under "
            "E-ST-10-11C Annex D; expected one of %s"
            % (severity, sorted(FINDING_SEVERITY_LEVELS))
        )
    return severity


def check_participant_count(test_type, participant_count):
    """Return a violation dict when participant_count is below the minimum
    for test_type, otherwise return None.

    Raises ValueError for an unrecognized test_type or a negative count.
    Violation dict keys: issue, test_type, actual, minimum."""
    if test_type not in TEST_TYPES:
        raise ValueError(
            "unrecognized test type %r; expected one of %s"
            % (test_type, sorted(TEST_TYPES))
        )
    if participant_count < 0:
        raise ValueError("participant_count must be >= 0")
    minimum = MIN_PARTICIPANTS[test_type]
    if participant_count < minimum:
        return {
            "issue": "insufficient_participants",
            "test_type": test_type,
            "actual": participant_count,
            "minimum": minimum,
        }
    return None


def check_finding_recommendation_linkage(findings, recommendations):
    """Return a list of finding IDs that have no linked recommendation.

    findings: iterable of dicts with an "id" key.
    recommendations: iterable of dicts with a "finding_id" key.
    Does not mutate either argument. An empty list means full coverage."""
    covered = frozenset(r["finding_id"] for r in recommendations)
    return [f["id"] for f in findings if f["id"] not in covered]


def check_scenario_coverage(planned_scenarios, executed_scenarios):
    """Return a sorted list of planned scenario IDs absent from
    executed_scenarios.

    Does not mutate either argument. An empty list means all planned
    scenarios have an execution record."""
    executed = frozenset(executed_scenarios)
    return sorted(s for s in planned_scenarios if s not in executed)


def validate_hfe_test_report(report):
    """Full Annex D DRD validation for one HFE test report.

    report: {
        "sections": iterable of section name strings,
        "test_type": str ("formative" or "summative"),
        "participant_count": int (>= 0),
        "findings": [{"id": str, "severity": str}, ...],
        "recommendations": [{"finding_id": str, ...}, ...],
        "planned_scenarios": iterable of scenario ID strings,
        "executed_scenarios": iterable of scenario ID strings,
    }

    Returns:
    {
        "missing_sections": sorted list of missing section names,
        "participant_violation": violation dict or None,
        "invalid_severity_findings": list of finding IDs with bad severity,
        "unlinked_findings": list of finding IDs with no recommendation,
        "uncovered_scenarios": sorted list of unexecuted planned scenarios,
    }

    Raises ValueError for an unrecognized test_type or negative
    participant_count. Does not mutate report."""
    missing_sections = check_required_sections(report.get("sections", []))

    participant_violation = check_participant_count(
        report["test_type"], report["participant_count"]
    )

    invalid_severity_findings = []
    for finding in report.get("findings", []):
        try:
            validate_finding_severity(finding["severity"])
        except ValueError:
            invalid_severity_findings.append(finding["id"])

    unlinked_findings = check_finding_recommendation_linkage(
        report.get("findings", []),
        report.get("recommendations", []),
    )

    uncovered_scenarios = check_scenario_coverage(
        report.get("planned_scenarios", []),
        report.get("executed_scenarios", []),
    )

    return {
        "missing_sections": missing_sections,
        "participant_violation": participant_violation,
        "invalid_severity_findings": invalid_severity_findings,
        "unlinked_findings": unlinked_findings,
        "uncovered_scenarios": uncovered_scenarios,
    }


def is_report_compliant(validation_result):
    """Return True when a validate_hfe_test_report result contains no
    violations across all five check categories."""
    return (
        not validation_result["missing_sections"]
        and validation_result["participant_violation"] is None
        and not validation_result["invalid_severity_findings"]
        and not validation_result["unlinked_findings"]
        and not validation_result["uncovered_scenarios"]
    )
