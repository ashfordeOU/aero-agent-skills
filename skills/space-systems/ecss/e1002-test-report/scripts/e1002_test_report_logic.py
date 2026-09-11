"""ECSS-E-ST-10-02 clause 5.3.2.1 / Annex C test report DRD (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex C
Document Requirements Definition governs the test report produced by a
verification-by-test activity. The report identifies the test article and its
configuration, the facility, and the test procedure BY REVISION -- a report
citing a procedure revision other than the one actually run describes a
different test. Every test objective carries its own verdict; a report is not
a pass because most objectives passed. Every discrepancy observed during the
test is linked to a raised nonconformance, because a discrepancy recorded
without one is an observation nobody is obliged to close.
"""

OBJECTIVE_VERDICTS = ("pass", "fail", "not_performed")
REQUIRED_IDENTIFICATION = ("test_article", "article_configuration", "facility",
                           "procedure_ref", "procedure_revision")


def validate_verdict(verdict):
    """Return verdict if it is a recognized objective verdict, else raise."""
    if verdict not in OBJECTIVE_VERDICTS:
        raise ValueError("unknown objective verdict: %r" % (verdict,))
    return verdict


def identification_violations(report):
    """Findings for identification fields absent from the report. Without them
    the data cannot be attributed to a specific article and run."""
    out = []
    for f in REQUIRED_IDENTIFICATION:
        if not (str(report.get(f) or "")).strip():
            out.append({"issue": "missing_identification", "field": f})
    return out


def procedure_revision_violations(report, as_run_revision):
    """Finding when the report cites a procedure revision other than the one
    actually executed. This is not a typo class of defect: the report then
    describes a test that was not run."""
    cited = report.get("procedure_revision")
    if not cited:
        return []
    if cited != as_run_revision:
        return [{"issue": "procedure_revision_mismatch", "cited": cited,
                 "as_run": as_run_revision}]
    return []


def objective_violations(objectives):
    """Findings for test objectives with no verdict, and duplicate objective
    ids. Raises ValueError for an unrecognized verdict."""
    out = []
    seen = set()
    for obj in objectives:
        oid = obj.get("objective_id")
        if not oid:
            raise ValueError("test objective with no objective_id")
        if oid in seen:
            raise ValueError("duplicate objective_id: %s" % oid)
        seen.add(oid)
        verdict = obj.get("verdict")
        if verdict is None:
            out.append({"objective_id": oid, "issue": "objective_without_verdict"})
            continue
        validate_verdict(verdict)
        if verdict == "not_performed" and not (obj.get("reason") or "").strip():
            out.append({"objective_id": oid,
                        "issue": "objective_not_performed_without_reason"})
    return out


def discrepancy_violations(discrepancies):
    """Findings for discrepancies with no nonconformance raised against them.
    A discrepancy without an NCR is an observation nobody must close."""
    out = []
    for d in discrepancies:
        did = d.get("discrepancy_id")
        if not did:
            raise ValueError("discrepancy with no discrepancy_id")
        if not (d.get("nonconformance_ref") or "").strip():
            out.append({"discrepancy_id": did,
                        "issue": "discrepancy_without_nonconformance"})
    return out


def data_reference_violations(report):
    """Finding when measured data is summarized without a reference to the
    recorded data set. A summary that cannot be traced to its raw data cannot
    be re-analysed, and re-analysis is what makes test data evidence."""
    if not (report.get("measured_data_ref") or "").strip():
        return [{"issue": "no_measured_data_reference"}]
    return []


def report_verdict(objectives):
    """Overall verdict across objectives, severity ordered: any failed
    objective fails the report; otherwise any objective not performed leaves
    it incomplete; only an all-pass set passes. Raises ValueError on an
    unrecognized verdict, and for an empty objective set -- a test report with
    no objective verifies nothing."""
    verdicts = [validate_verdict(o["verdict"]) for o in objectives
                if o.get("verdict") is not None]
    if not verdicts:
        raise ValueError("test report has no objective with a verdict")
    if "fail" in verdicts:
        return "fail"
    if "not_performed" in verdicts:
        return "incomplete"
    return "pass"


def test_report_review(report, as_run_revision):
    """Full Annex C test report review.

    Returns {"verdict", "findings"}. Raises ValueError for a malformed
    objective or discrepancy, or an objective set with no verdicts.
    """
    findings = []
    findings += identification_violations(report)
    findings += procedure_revision_violations(report, as_run_revision)
    findings += objective_violations(report.get("objectives", []))
    findings += discrepancy_violations(report.get("discrepancies", []))
    findings += data_reference_violations(report)
    return {"verdict": report_verdict(report.get("objectives", [])),
            "findings": findings}


def is_test_report_acceptable(review):
    """True when the report passes every objective and carries no findings."""
    return review["verdict"] == "pass" and not review["findings"]
