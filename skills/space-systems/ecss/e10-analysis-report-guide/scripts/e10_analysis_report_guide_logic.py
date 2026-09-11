"""ECSS-E-ST-10C Annex S analysis report content guideline (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex S is
informative and describes what an engineering analysis report must contain for
its result to be usable as verification evidence under E-ST-10-02: the
objective and the requirement it supports, the model and assumptions, the
input data with its provenance, the method and the tool with its qualification
status, the results with their uncertainty, and a conclusion that states
whether the requirement is met. A report missing any of those is not a shorter
report -- it is one whose result cannot be independently re-derived, which is
the only property that makes it evidence.
"""

REQUIRED_SECTIONS = ("objective", "requirement_ref", "model_and_assumptions",
                     "input_data", "method_and_tool", "results",
                     "uncertainty", "conclusion")
CONCLUSION_VERDICTS = ("requirement_met", "requirement_not_met", "inconclusive")


def validate_verdict(verdict):
    """Return verdict if it is a recognized conclusion, else raise."""
    if verdict not in CONCLUSION_VERDICTS:
        raise ValueError("unknown conclusion verdict: %r" % (verdict,))
    return verdict


def missing_sections(report):
    """Required Annex S sections absent or empty, in declared order."""
    sections = report.get("sections", {})
    return [s for s in REQUIRED_SECTIONS if not (sections.get(s) or "").strip()]


def input_provenance_violations(inputs):
    """Findings for input data with no stated source. An analysis whose inputs
    cannot be traced cannot be re-run, so an untraced input is a finding even
    when the number itself is right."""
    out = []
    for item in inputs:
        name = item.get("name")
        if not name:
            raise ValueError("input datum with no name")
        if not (item.get("source") or "").strip():
            out.append({"input": name, "issue": "input_without_source"})
    return out


def tool_qualification_violations(report):
    """Findings when the analysis tool is unnamed, or named without its
    qualification status. Annex S ties the credibility of the result to the
    credibility of the tool, so an unqualified tool is reportable, not fatal."""
    tool = report.get("tool") or {}
    out = []
    if not (tool.get("name") or "").strip():
        out.append({"issue": "tool_not_named"})
        return out
    if tool.get("qualified") is None:
        out.append({"issue": "tool_qualification_unstated", "tool": tool["name"]})
    elif not tool["qualified"]:
        out.append({"issue": "tool_not_qualified", "tool": tool["name"]})
    return out


def uncertainty_violations(report):
    """Findings for results reported without an uncertainty.

    A result with no uncertainty cannot be compared against a requirement
    margin at all, so it is reported rather than treated as exact.
    """
    out = []
    for r in report.get("results", []):
        name = r.get("quantity")
        if not name:
            raise ValueError("result with no quantity name")
        if r.get("uncertainty") is None:
            out.append({"quantity": name, "issue": "result_without_uncertainty"})
        elif r["uncertainty"] < 0:
            raise ValueError("negative uncertainty for %s" % name)
    return out


def conclusion_supported(report):
    """True when a 'requirement met' conclusion is actually supported by the
    reported results: every result must clear its limit with its uncertainty
    applied in the unfavourable direction. A conclusion asserting compliance
    on a margin smaller than its own uncertainty is the defect this catches.
    """
    if validate_verdict(report.get("conclusion_verdict")) != "requirement_met":
        return True
    for r in report.get("results", []):
        limit = r.get("limit")
        if limit is None:
            return False
        unc = r.get("uncertainty") or 0.0
        if r.get("value", 0.0) + unc > limit:
            return False
    return True


def analysis_report_review(report):
    """Full Annex S analysis report review.

    Returns {"verdict", "findings"}. Raises ValueError for an unknown verdict,
    an unnamed input or result, or a negative uncertainty.
    """
    findings = []
    for s in missing_sections(report):
        findings.append({"section": s, "issue": "missing_section"})
    findings += input_provenance_violations(report.get("inputs", []))
    findings += tool_qualification_violations(report)
    findings += uncertainty_violations(report)
    verdict = validate_verdict(report.get("conclusion_verdict"))
    if not conclusion_supported(report):
        findings.append({"issue": "conclusion_not_supported_by_results"})
    return {"verdict": verdict, "findings": findings}


def is_report_usable_as_evidence(review):
    """True when the report may be cited as verification evidence."""
    return not review["findings"]
