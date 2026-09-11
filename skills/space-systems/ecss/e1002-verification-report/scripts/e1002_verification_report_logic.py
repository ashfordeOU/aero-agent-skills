"""ECSS-E-ST-10-02 clause 5.3.2.5 / Annex F verification report (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex F
Verification Report (VRPT) is the summary layer: for every requirement it
states which verification events were carried out, cites the underlying
report that holds the evidence, and gives the requirement's verification
status. It is a roll-up, so its integrity depends on two cross-checks a
per-event view cannot make: the methods actually executed must match the
methods the verification control document planned, and a requirement cannot
be reported verified on an event whose own underlying report did not pass.
A summary that disagrees with its sources is worse than no summary.
"""

EVENT_STATUSES = ("passed", "failed", "not_executed")
METHODS = ("test", "analysis", "inspection", "review_of_design")


def validate_method(method):
    """Return method if it is a recognized verification method, else raise."""
    if method not in METHODS:
        raise ValueError("unknown verification method: %r" % (method,))
    return method


def validate_event_status(status):
    """Return status if it is a recognized event status, else raise."""
    if status not in EVENT_STATUSES:
        raise ValueError("unknown event status: %r" % (status,))
    return status


def evidence_violations(requirement_id, events):
    """Findings for verification events that cite no underlying report. The
    VRPT is a summary; an entry with nothing beneath it summarizes nothing."""
    out = []
    for ev in events:
        if not (ev.get("report_ref") or "").strip():
            out.append({"requirement_id": requirement_id,
                        "method": ev.get("method"),
                        "issue": "event_without_supporting_report"})
    return out


def method_agreement_violations(requirement_id, planned_methods, events):
    """Findings where the executed methods disagree with the planned set.

    Both directions matter: a planned method with no event was not carried
    out, and an executed method nobody planned was not agreed. Each is
    reported once, against the method.
    """
    executed = {validate_method(ev.get("method")) for ev in events}
    planned = {validate_method(m) for m in planned_methods}
    out = []
    for m in sorted(planned - executed):
        out.append({"requirement_id": requirement_id, "method": m,
                    "issue": "planned_method_not_executed"})
    for m in sorted(executed - planned):
        out.append({"requirement_id": requirement_id, "method": m,
                    "issue": "executed_method_not_planned"})
    return out


def source_agreement_violations(requirement_id, events, source_verdicts):
    """Findings where a VRPT event's status contradicts the verdict of the
    report it cites. This is the defect that makes a summary dangerous: the
    roll-up says verified while the evidence beneath says otherwise."""
    out = []
    for ev in events:
        ref = (ev.get("report_ref") or "").strip()
        if not ref or ref not in source_verdicts:
            continue
        claimed = validate_event_status(ev.get("status"))
        actual = source_verdicts[ref]
        if claimed == "passed" and actual != "pass":
            out.append({"requirement_id": requirement_id, "report_ref": ref,
                        "issue": "status_contradicts_source_report",
                        "claimed": claimed, "source_verdict": actual})
    return out


def requirement_status(events):
    """Verification status of one requirement from its events, severity
    ordered: any failed event fails it, any event not executed leaves it
    open, and only an all-passed set verifies it. Raises ValueError when a
    requirement carries no event -- nothing has been verified."""
    statuses = [validate_event_status(e.get("status")) for e in events]
    if not statuses:
        raise ValueError("requirement has no verification event")
    if "failed" in statuses:
        return "failed"
    if "not_executed" in statuses:
        return "open"
    return "verified"


def verification_report_review(vrpt, planned_methods_by_requirement,
                               source_verdicts):
    """Full Annex F verification report review.

    vrpt: {"requirements": [{"requirement_id", "events": [{"method",
           "report_ref", "status"}]}]}
    planned_methods_by_requirement: {requirement_id: [method, ...]}
    source_verdicts: {report_ref: "pass"|"fail"|"incomplete"}

    Returns {"verified", "open", "failed", "findings"}.
    """
    buckets = {"verified": [], "open": [], "failed": []}
    findings = []
    seen = set()
    for req in vrpt.get("requirements", []):
        rid = req.get("requirement_id")
        if not rid:
            raise ValueError("VRPT entry with no requirement_id")
        if rid in seen:
            raise ValueError("duplicate requirement_id: %s" % rid)
        seen.add(rid)
        events = list(req.get("events", []))
        findings += evidence_violations(rid, events)
        findings += method_agreement_violations(
            rid, planned_methods_by_requirement.get(rid, []), events)
        findings += source_agreement_violations(rid, events, source_verdicts)
        buckets[requirement_status(events)].append(rid)
    return {"verified": buckets["verified"], "open": buckets["open"],
            "failed": buckets["failed"], "findings": findings}


def is_verification_report_complete(review):
    """True when every requirement is verified and the summary agrees with its
    sources -- nothing open, nothing failed, no finding."""
    return not (review["open"] or review["failed"] or review["findings"])
