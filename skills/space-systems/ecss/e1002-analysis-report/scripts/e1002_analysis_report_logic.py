"""ECSS-E-ST-10-02 clause 5.3.2.2 analysis report as evidence (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): clause
5.3.2.2 governs the analysis report where analysis is the verification method.
Beyond the report's own content, verification asks three further questions
that a content check cannot: does the analysis cover every case the
requirement's envelope demands, was it run against the design baseline
actually being verified, and does the case-by-case result roll up to a verdict
for the requirement? An analysis run on a superseded model configuration is
evidence about a design that no longer exists, and a case matrix with a hole
in it verifies the envelope only where somebody looked.
"""

CASE_VERDICTS = ("pass", "fail", "not_run")


def validate_case_verdict(verdict):
    """Return verdict if it is a recognized case verdict, else raise."""
    if verdict not in CASE_VERDICTS:
        raise ValueError("unknown case verdict: %r" % (verdict,))
    return verdict


def uncovered_cases(required_cases, analysed_cases):
    """Required envelope cases with no analysis case, in declared order. The
    envelope is verified only where a case was actually run."""
    have = {c.get("case_id") for c in analysed_cases}
    return [c for c in required_cases if c not in have]


def extraneous_cases(required_cases, analysed_cases):
    """Analysis cases outside the required envelope, in input order. Not a
    defect in itself -- extra coverage is welcome -- but reported so a case
    matrix that drifted from the requirement is visible."""
    need = set(required_cases)
    return [c.get("case_id") for c in analysed_cases
            if c.get("case_id") not in need]


def baseline_violations(report, design_baseline):
    """Findings when the analysis was not run against the design baseline
    under verification. An unstated baseline and a superseded one are
    different failures: one is unrecorded, the other is known-wrong."""
    declared = report.get("model_baseline")
    if not declared:
        return [{"issue": "model_baseline_unstated"}]
    if declared != design_baseline:
        return [{"issue": "model_baseline_superseded", "declared": declared,
                 "design_baseline": design_baseline}]
    return []


def case_violations(cases):
    """Findings for analysis cases missing a verdict, and for a case marked
    not run with no reason. Raises ValueError for a duplicate or absent case
    id, or an unrecognized verdict."""
    out = []
    seen = set()
    for c in cases:
        cid = c.get("case_id")
        if not cid:
            raise ValueError("analysis case with no case_id")
        if cid in seen:
            raise ValueError("duplicate case_id: %s" % cid)
        seen.add(cid)
        verdict = c.get("verdict")
        if verdict is None:
            out.append({"case_id": cid, "issue": "case_without_verdict"})
            continue
        validate_case_verdict(verdict)
        if verdict == "not_run" and not (c.get("reason") or "").strip():
            out.append({"case_id": cid, "issue": "case_not_run_without_reason"})
    return out


def requirement_verdict(cases):
    """Roll the case verdicts up to the requirement, severity ordered: one
    failing case fails the requirement, any case not run leaves it incomplete,
    and only an all-pass matrix verifies it. Raises ValueError when no case
    carries a verdict -- there is nothing to roll up."""
    verdicts = [validate_case_verdict(c["verdict"]) for c in cases
                if c.get("verdict") is not None]
    if not verdicts:
        raise ValueError("no analysis case carries a verdict")
    if "fail" in verdicts:
        return "fail"
    if "not_run" in verdicts:
        return "incomplete"
    return "pass"


def analysis_report_verification_review(report, required_cases, design_baseline):
    """Full clause 5.3.2.2 verification review of an analysis report.

    report: {"requirement_id", "model_baseline", "cases": [{"case_id",
             "verdict", "reason"}]}

    Returns {"requirement_id", "verdict", "findings"}.
    """
    rid = report.get("requirement_id")
    if not rid:
        raise ValueError("analysis report with no requirement_id")
    cases = list(report.get("cases", []))
    findings = []
    findings += baseline_violations(report, design_baseline)
    findings += case_violations(cases)
    for cid in uncovered_cases(required_cases, cases):
        findings.append({"case_id": cid, "issue": "envelope_case_not_analysed"})
    for cid in extraneous_cases(required_cases, cases):
        findings.append({"case_id": cid, "issue": "case_outside_required_envelope"})
    return {"requirement_id": rid, "verdict": requirement_verdict(cases),
            "findings": findings}


def is_requirement_verified_by_analysis(review):
    """True when the analysis verifies the requirement across its envelope
    with no findings outstanding."""
    return review["verdict"] == "pass" and not review["findings"]
