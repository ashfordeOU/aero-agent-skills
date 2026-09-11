#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.3.4 analysis tool/model qualification and
correlation (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard requires that an
analysis method, tool or model be qualified before its results are
used to support engineering decisions. A tool with a heritage record
whose applicability domain (physics regime, parameter range) is
confirmed for the new analysis may be reused directly; any other tool
(new, or heritage applied outside its confirmed domain) must be
qualified by correlating its predicted output against an independent
reference (test data or a validated benchmark method), and the
correlation error must fall within an acceptance tolerance set by how
critical the analysis is to the engineering decision it supports. This
module implements the qualification-basis classification, the
correlation-error and tolerance computation, the per-tool
qualification verdict, and the aggregated review across every tool
used in one analysis; it does not define the underlying physics of any
specific analysis discipline.
"""

QUALIFICATION_BASES = frozenset({"heritage_reuse", "requires_correlation"})

# Acceptance tolerance (percent) for a tool's correlation error, keyed by
# how critical the analysis is to the engineering decision it supports.
# A more critical analysis demands a tighter correlation before the tool
# backing it is trusted.
ACCEPTANCE_TOLERANCE_PERCENT = {
    "high": 5.0,
    "medium": 10.0,
    "low": 20.0,
}

STATUS_QUALIFIED = "qualified"
STATUS_CORRELATION_EXCEEDED = "not_qualified_correlation_exceeded"


def classify_qualification_basis(is_heritage, domain_applicability_confirmed):
    """Qualification basis for a tool: "heritage_reuse" when it is a
    heritage tool (is_heritage True) and its applicability domain for
    this analysis has been confirmed (domain_applicability_confirmed
    True); "requires_correlation" otherwise (a new tool, or a heritage
    tool applied outside its confirmed domain)."""
    if is_heritage and domain_applicability_confirmed:
        return "heritage_reuse"
    return "requires_correlation"


def acceptance_tolerance_percent(criticality):
    """Correlation-error acceptance tolerance (percent) for the given
    analysis criticality ("high", "medium", "low"). Raises ValueError
    for an unrecognized criticality."""
    if criticality not in ACCEPTANCE_TOLERANCE_PERCENT:
        raise ValueError(
            "unrecognized analysis criticality %r under E-ST-10C "
            "clause 5.3.4" % (criticality,)
        )
    return ACCEPTANCE_TOLERANCE_PERCENT[criticality]


def correlation_error_percent(predicted_value, reference_value):
    """Relative correlation error (percent) between a tool's predicted
    value and an independently-derived reference value (test data or a
    validated benchmark method): abs(predicted - reference) /
    abs(reference) * 100. Raises ValueError when reference_value is 0
    (percent error is undefined against a zero reference)."""
    if reference_value == 0:
        raise ValueError(
            "reference_value must be nonzero to compute a correlation "
            "error percentage"
        )
    return abs(predicted_value - reference_value) / abs(reference_value) * 100.0


def tool_qualification_status(qualification_basis, correlation_error_pct=None, tolerance_pct=None):
    """Qualification verdict for one tool: STATUS_QUALIFIED or
    STATUS_CORRELATION_EXCEEDED. A "heritage_reuse" basis is always
    qualified. A "requires_correlation" basis is qualified only when
    correlation_error_pct <= tolerance_pct; both must be supplied (not
    None) for that basis. Raises ValueError for an unrecognized
    qualification_basis or for missing correlation data on a
    "requires_correlation" basis."""
    if qualification_basis not in QUALIFICATION_BASES:
        raise ValueError(
            "unrecognized qualification basis %r" % (qualification_basis,)
        )
    if qualification_basis == "heritage_reuse":
        return STATUS_QUALIFIED
    if correlation_error_pct is None or tolerance_pct is None:
        raise ValueError(
            "correlation_error_pct and tolerance_pct are required for a "
            "requires_correlation basis"
        )
    if correlation_error_pct <= tolerance_pct:
        return STATUS_QUALIFIED
    return STATUS_CORRELATION_EXCEEDED


def tool_review(tool):
    """Full clause 5.3.4 qualification review for one analysis tool.

    tool: {"tool_id": str, "is_heritage": bool,
    "domain_applicability_confirmed": bool, "criticality": str,
    "predicted_value": float, "reference_value": float}. The
    "criticality", "predicted_value" and "reference_value" keys are
    only required when the tool does not qualify for heritage reuse.
    Returns {"tool_id": str, "qualification_basis": str, "status": str,
    "correlation_error_pct": float | None, "tolerance_pct": float |
    None, "issues": [...]}."""
    tool_id = tool["tool_id"]
    basis = classify_qualification_basis(
        tool["is_heritage"], tool["domain_applicability_confirmed"]
    )
    if basis == "heritage_reuse":
        status = tool_qualification_status(basis)
        result = {
            "tool_id": tool_id,
            "qualification_basis": basis,
            "status": status,
            "correlation_error_pct": None,
            "tolerance_pct": None,
            "issues": [],
        }
        return result

    tolerance_pct = acceptance_tolerance_percent(tool["criticality"])
    error_pct = correlation_error_percent(
        tool["predicted_value"], tool["reference_value"]
    )
    status = tool_qualification_status(basis, error_pct, tolerance_pct)
    issues = []
    if status != STATUS_QUALIFIED:
        issues.append(
            {
                "issue": "tool_correlation_exceeds_tolerance",
                "tool_id": tool_id,
                "correlation_error_pct": error_pct,
                "tolerance_pct": tolerance_pct,
            }
        )
    return {
        "tool_id": tool_id,
        "qualification_basis": basis,
        "status": status,
        "correlation_error_pct": error_pct,
        "tolerance_pct": tolerance_pct,
        "issues": issues,
    }


def analysis_qualification_review(tools):
    """Aggregated clause 5.3.4 qualification review across every tool
    used in one analysis. tools: iterable of tool dicts (see
    tool_review). Returns {"tool_reviews": [...], "issues": [...],
    "is_analysis_valid": bool}. Raises ValueError for a duplicate
    tool_id (each tool backing an analysis is reviewed once) or for
    an empty tools sequence (an analysis with no reviewed tool has
    nothing to qualify it)."""
    tools = list(tools)
    if not tools:
        raise ValueError("at least one tool is required to review an analysis")

    seen_ids = set()
    tool_reviews = []
    issues = []
    for tool in tools:
        tool_id = tool["tool_id"]
        if tool_id in seen_ids:
            raise ValueError("duplicate tool_id %r in analysis review" % (tool_id,))
        seen_ids.add(tool_id)
        review = tool_review(tool)
        tool_reviews.append(review)
        issues.extend(review["issues"])

    return {
        "tool_reviews": tool_reviews,
        "issues": issues,
        "is_analysis_valid": len(issues) == 0,
    }


def is_analysis_valid(review):
    """True when an analysis_qualification_review result carries no
    issues -- every tool backing the analysis is qualified per clause
    5.3.4."""
    return len(review["issues"]) == 0
