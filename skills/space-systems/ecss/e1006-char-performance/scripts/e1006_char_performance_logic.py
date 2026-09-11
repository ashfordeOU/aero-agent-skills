#!/usr/bin/env python3
"""ECSS-E-ST-10C §8.2.1 performance requirement content check
(paraphrase, not copy).

Common-knowledge summary: the system engineering standard requires each
performance requirement to carry at least one quantified performance
parameter — a numeric threshold or range, the engineering unit in which
it is measured, and a comparison operator defining the direction of
compliance (at most, at least, equal to, or within a range). A
performance requirement that names an attribute without a numeric value
is incompletely specified. This module implements requirement type
categorization, per-parameter quantification checking (value, unit,
operator), requirement-level performance content checking, and an
aggregate review that returns all findings for a set of requirements.
"""

PERFORMANCE_REQ_TYPES = frozenset({
    "performance",
    "timing",
    "accuracy",
    "capacity",
    "throughput",
    "efficiency",
    "data_rate",
})

NON_PERFORMANCE_REQ_TYPES = frozenset({
    "functional",
    "interface",
    "design_constraint",
    "operational",
    "safety",
})

VALID_OPERATORS = frozenset({"leq", "geq", "eq", "lt", "gt", "range"})


def categorize_requirement(req_type):
    """Requirement category: "performance" or "non_performance".
    Raises ValueError for an unrecognized type."""
    if req_type in PERFORMANCE_REQ_TYPES:
        return "performance"
    if req_type in NON_PERFORMANCE_REQ_TYPES:
        return "non_performance"
    raise ValueError(
        "unrecognized requirement type %r under E-ST-10C §8.2.1" % (req_type,)
    )


def check_parameter(param):
    """Finding list for one performance parameter dict.
    A fully quantified parameter has a numeric value, a non-empty unit
    string, and a recognized comparison operator. Each missing component
    generates its own finding. Returns [] when all three are present
    and valid. Does not mutate param."""
    findings = []
    param_name = param.get("name")

    value = param.get("value")
    if value is None or not isinstance(value, (int, float)):
        findings.append({
            "issue": "missing_numeric_value",
            "parameter": param_name,
        })

    unit = param.get("unit")
    if not unit or not isinstance(unit, str) or not unit.strip():
        findings.append({
            "issue": "missing_unit",
            "parameter": param_name,
        })

    operator = param.get("operator")
    if operator not in VALID_OPERATORS:
        findings.append({
            "issue": "invalid_or_missing_operator",
            "parameter": param_name,
            "provided": operator,
        })

    return findings


def check_requirement_performance_content(req):
    """Finding list for one requirement's §8.2.1 performance content.
    Non-performance requirements return [] (no quantification check).
    A performance requirement with no parameters is flagged without
    inspecting individual parameters. For each parameter present,
    check_parameter findings are accumulated and tagged with req_id.
    Raises ValueError for an unrecognized req_type."""
    req_id = req.get("req_id", "<unknown>")
    req_type = req.get("req_type", "")
    category = categorize_requirement(req_type)

    if category == "non_performance":
        return []

    params = req.get("performance_parameters", [])
    if not params:
        return [{
            "issue": "performance_requirement_has_no_parameters",
            "req_id": req_id,
        }]

    findings = []
    for param in params:
        for finding in check_parameter(param):
            finding["req_id"] = req_id
            findings.append(finding)
    return findings


def performance_content_review(requirements):
    """Aggregate §8.2.1 performance content check for a list of
    requirement dicts. Returns a dict mapping req_id to a list of
    findings (empty list means that requirement has no findings).
    Raises ValueError if any requirement carries an unrecognized
    req_type. Does not mutate any input dict."""
    result = {}
    for req in requirements:
        req_id = req.get("req_id", "<unknown>")
        result[req_id] = check_requirement_performance_content(req)
    return result


def is_performance_compliant(review):
    """True when every requirement in a performance_content_review
    result has an empty findings list — the full set satisfies §8.2.1
    for this check."""
    return all(len(findings) == 0 for findings in review.values())
