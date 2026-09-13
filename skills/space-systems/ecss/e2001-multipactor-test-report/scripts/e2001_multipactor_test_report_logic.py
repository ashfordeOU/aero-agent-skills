"""ECSS-E-ST-20-01C clause 8.7 -- multipactor test report content audit.

Deterministic, offline, stdlib-only implementation of the content check a
multipactor test report must pass before the customer approves it once
radio-frequency testing is complete.  Every rule is a paraphrase of the
clause intent expressed as an implementable procedure; no standard text is
reproduced.

Where the clause 8.6 procedure audit asks "is this plan approvable", the
report audit asks a harder pair of questions: is the as-run test traceable
to the approved plan, and does the evidence actually support the compliance
statement the report makes.  The module therefore

1. audits the report's section list for content completeness,
2. checks traceability -- the approved-procedure identifier and a
   customer-agreed waiver behind every as-run deviation,
3. checks that every detection technique credited with the result has a
   recorded trace,
4. checks that every non-conformance raised carries an agreed disposition,
5. derives the outcome and the achieved margin from the recorded powers
   rather than reading the report's own conclusion.
"""

import math

# Tolerances absorb floating-point representation error exactly at a
# compliance boundary.  They never widen the engineering limit itself.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Content items clause 8.7 expects a multipactor test report to carry.
REQUIRED_SECTIONS = (
    "test-item-identification",
    "as-built-configuration",
    "approved-procedure-reference",
    "facility-and-calibration-records",
    "as-run-vacuum-conditions",
    "as-run-seeding-arrangement",
    "drive-levels-applied",
    "detection-traces",
    "threshold-determination",
    "achieved-margin",
    "deviation-record",
    "non-conformance-record",
    "pass-fail-statement",
    "customer-approval-block",
)

# Dispositions a raised non-conformance may close with.
NCR_DISPOSITIONS = (
    "repair",
    "rework",
    "use-as-is",
    "scrap",
    "retest",
)

# Outcome labels the audit derives from the recorded powers.
OUTCOME_MARGIN_DEMONSTRATED = "no-event-margin-demonstrated"
OUTCOME_MARGIN_NOT_DEMONSTRATED = "no-event-margin-not-demonstrated"
OUTCOME_EVENT_ABOVE_MARGIN = "event-above-required-margin"
OUTCOME_EVENT_BELOW_MARGIN = "event-below-required-margin"

DEFAULT_REQUIRED_MARGIN_DB = 3.0


def _at_least(value, limit):
    """True when value meets or exceeds limit, absorbing representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def compute_achieved_margin_db(operating_power_w, observed_power_w):
    """Margin in dB that an observed power represents over operating-power."""
    for label, value in (("operating", operating_power_w), ("observed", observed_power_w)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s power must be numeric, got %r" % (label, value))
        if value <= 0.0:
            raise ValueError("%s power must be positive, got %r" % (label, value))
    return 10.0 * math.log10(float(observed_power_w) / float(operating_power_w))


def categorize_test_outcome(
    operating_power_w,
    max_applied_power_w,
    threshold_power_w=None,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Derive the outcome and the margin actually demonstrated by the run.

    threshold_power_w is the lowest power at which a multipactor event was
    detected, or None when no event was detected up to the highest power
    applied.  An event recorded above the highest applied power is
    physically impossible and raises ValueError rather than being reported.
    """
    if required_margin_db < 0.0:
        raise ValueError("required margin cannot be negative, got %r" % (required_margin_db,))
    top_margin_db = compute_achieved_margin_db(operating_power_w, max_applied_power_w)
    if threshold_power_w is None:
        demonstrated = _at_least(top_margin_db, float(required_margin_db))
        return {
            "outcome": (
                OUTCOME_MARGIN_DEMONSTRATED if demonstrated
                else OUTCOME_MARGIN_NOT_DEMONSTRATED
            ),
            "event_detected": False,
            "demonstrated_margin_db": top_margin_db,
            "margin_is_lower_bound": True,
            "required_margin_db": float(required_margin_db),
            "compliant": demonstrated,
        }
    threshold_margin_db = compute_achieved_margin_db(operating_power_w, threshold_power_w)
    if float(threshold_power_w) > float(max_applied_power_w) and not math.isclose(
        float(threshold_power_w), float(max_applied_power_w), rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError("recorded threshold exceeds the highest power applied")
    demonstrated = _at_least(threshold_margin_db, float(required_margin_db))
    return {
        "outcome": (
            OUTCOME_EVENT_ABOVE_MARGIN if demonstrated else OUTCOME_EVENT_BELOW_MARGIN
        ),
        "event_detected": True,
        "demonstrated_margin_db": threshold_margin_db,
        "margin_is_lower_bound": False,
        "required_margin_db": float(required_margin_db),
        "compliant": demonstrated,
    }


def audit_report_sections(sections):
    """Compare the report's section list with the expected content items."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list")
    present = []
    for section in sections:
        if not isinstance(section, str) or not section.strip():
            raise ValueError("section name must be a non-empty string")
        key = section.strip().lower()
        if key not in present:
            present.append(key)
    missing = [s for s in REQUIRED_SECTIONS if s not in present]
    extra = [s for s in present if s not in REQUIRED_SECTIONS]
    return {
        "present": present,
        "missing": missing,
        "extra": extra,
        "complete": not missing,
    }


def check_procedure_traceability(reported_procedure_id, approved_procedure_id, deviations):
    """Tie the as-run test back to the plan the customer approved.

    A report that cites a different procedure identifier than the approved
    one is untraceable, and every departure from the approved plan needs a
    customer-agreed waiver reference before the result can be credited.
    """
    if not isinstance(reported_procedure_id, str) or not reported_procedure_id.strip():
        raise ValueError("reported procedure identifier must be a non-empty string")
    if not isinstance(approved_procedure_id, str) or not approved_procedure_id.strip():
        raise ValueError("approved procedure identifier must be a non-empty string")
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a list")
    findings = []
    if reported_procedure_id.strip().lower() != approved_procedure_id.strip().lower():
        findings.append(
            "report cites procedure '%s' but the approved procedure is '%s'"
            % (reported_procedure_id, approved_procedure_id)
        )
    unwaived = []
    for deviation in deviations:
        if not isinstance(deviation, dict):
            raise ValueError("each deviation must be a mapping")
        dev_id = deviation.get("id")
        if not isinstance(dev_id, str) or not dev_id.strip():
            raise ValueError("each deviation needs a non-empty id")
        waiver = deviation.get("waiver_reference")
        if not isinstance(waiver, str) or not waiver.strip():
            unwaived.append(dev_id)
    if unwaived:
        findings.append("as-run deviations without an agreed waiver: %s" % ", ".join(unwaived))
    return {
        "deviation_count": len(deviations),
        "unwaived_deviations": unwaived,
        "findings": findings,
        "traceable": not findings,
    }


def check_evidence_completeness(credited_methods, recorded_traces):
    """Every detection technique credited with the result needs its trace.

    A technique named in the conclusion but with no recorded trace makes the
    conclusion unverifiable; a trace for a technique nobody credited is
    recorded as surplus evidence, not a finding.
    """
    if not isinstance(credited_methods, (list, tuple)) or not credited_methods:
        raise ValueError("credited detection techniques must be a non-empty list")
    if not isinstance(recorded_traces, (list, tuple)):
        raise ValueError("recorded traces must be a list")
    credited = []
    for method in credited_methods:
        if not isinstance(method, str) or not method.strip():
            raise ValueError("detection technique must be a non-empty string")
        key = method.strip().lower()
        if key not in credited:
            credited.append(key)
    traced = []
    for trace in recorded_traces:
        if not isinstance(trace, str) or not trace.strip():
            raise ValueError("recorded trace must name a non-empty technique")
        key = trace.strip().lower()
        if key not in traced:
            traced.append(key)
    untraced = [m for m in credited if m not in traced]
    surplus = [t for t in traced if t not in credited]
    findings = []
    if untraced:
        findings.append("credited techniques with no recorded trace: %s" % ", ".join(untraced))
    if len(credited) < 2:
        findings.append("fewer than two independent detection techniques credited")
    return {
        "credited": credited,
        "traced": traced,
        "untraced": untraced,
        "surplus_traces": surplus,
        "findings": findings,
        "complete": not findings,
    }


def check_nonconformance_dispositions(nonconformances):
    """Every non-conformance raised during the run needs an agreed close-out."""
    if not isinstance(nonconformances, (list, tuple)):
        raise ValueError("non-conformances must be a list")
    open_items = []
    dispositions = {}
    for item in nonconformances:
        if not isinstance(item, dict):
            raise ValueError("each non-conformance must be a mapping")
        ncr_id = item.get("id")
        if not isinstance(ncr_id, str) or not ncr_id.strip():
            raise ValueError("each non-conformance needs a non-empty id")
        disposition = item.get("disposition")
        if disposition is None:
            open_items.append(ncr_id)
            continue
        if not isinstance(disposition, str):
            raise ValueError("disposition must be a string or None")
        key = disposition.strip().lower()
        if key not in NCR_DISPOSITIONS:
            raise ValueError("unrecognized disposition '%s' on %s" % (disposition, ncr_id))
        dispositions[ncr_id] = key
    findings = []
    if open_items:
        findings.append("non-conformances left open: %s" % ", ".join(open_items))
    return {
        "raised": len(nonconformances),
        "open_items": open_items,
        "dispositions": dispositions,
        "findings": findings,
        "closed_out": not findings,
    }


def assess_test_report(report, approved_procedure_id):
    """Run the full clause 8.7 content audit over one submitted report.

    Returns every sub-audit plus the derived outcome and an aggregate
    finding list.  The report is approvable only when the content is
    complete, the run is traceable, the evidence supports the credited
    techniques, every non-conformance is closed out, and the derived
    outcome itself demonstrates the required margin.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    for key in ("sections", "procedure_id", "operating_power_w", "max_applied_power_w"):
        if key not in report:
            raise ValueError("report missing required key: %s" % key)
    sections = audit_report_sections(report["sections"])
    traceability = check_procedure_traceability(
        report["procedure_id"], approved_procedure_id, report.get("deviations", [])
    )
    evidence = check_evidence_completeness(
        report.get("credited_methods", []), report.get("recorded_traces", [])
    )
    ncrs = check_nonconformance_dispositions(report.get("nonconformances", []))
    outcome = categorize_test_outcome(
        report["operating_power_w"],
        report["max_applied_power_w"],
        report.get("threshold_power_w"),
        report.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
    )
    findings = []
    if sections["missing"]:
        findings.append("missing report content: %s" % ", ".join(sections["missing"]))
    findings.extend(traceability["findings"])
    findings.extend(evidence["findings"])
    findings.extend(ncrs["findings"])
    if not outcome["compliant"]:
        findings.append(
            "derived outcome %s: %.4f dB demonstrated against %.4f dB required"
            % (
                outcome["outcome"],
                outcome["demonstrated_margin_db"],
                outcome["required_margin_db"],
            )
        )
    return {
        "sections": sections,
        "traceability": traceability,
        "evidence": evidence,
        "nonconformances": ncrs,
        "outcome": outcome,
        "findings": findings,
        "approvable": not findings,
    }
