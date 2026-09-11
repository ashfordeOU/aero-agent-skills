"""ECSS-E-ST-10-02 clause 5.3.2.6 additional verification documentation.

Common-knowledge summary (standards-map.yaml, ecss: gated false): clause
5.3.2.6 allows verification documentation beyond the four report DRDs when the
circumstances of an activity are not captured by them. The clause is
permissive, which is exactly why it needs a decision rule: without one, teams
either produce nothing where a record is genuinely needed, or generate reports
that restate a DRD report already covering the activity. A condition triggers
an additional report; an additional report that duplicates the scope of a DRD
report is a finding, not diligence; and whatever is produced still carries the
minimum identification that makes it citable in the verification control
document.
"""

TRIGGER_CONDITIONS = ("multi_facility_campaign", "supplier_performed",
                      "test_analysis_correlation", "deviation_invoked",
                      "heritage_evidence_reused", "multi_article_activity")
DRD_REPORT_TYPES = ("test_report", "analysis_report", "inspection_report",
                    "review_of_design_report")
REQUIRED_FIELDS = ("report_id", "requirement_refs", "activity_ref", "author",
                   "approver")


def validate_trigger(condition):
    """Return condition if it is a recognized trigger, else raise."""
    if condition not in TRIGGER_CONDITIONS:
        raise ValueError("unknown trigger condition: %r" % (condition,))
    return condition


def active_triggers(activity):
    """Trigger conditions holding for this activity, in declared order."""
    flags = activity.get("conditions", {})
    for c in flags:
        validate_trigger(c)
    return [c for c in TRIGGER_CONDITIONS if flags.get(c)]


def additional_report_required(activity):
    """True when at least one trigger condition holds. Clause 5.3.2.6 is
    permissive, so the decision is made from the activity's circumstances
    rather than left to preference."""
    return bool(active_triggers(activity))


def duplication_violations(report, drd_reports_present):
    """Findings where an additional report restates the scope of a DRD report
    already produced for the same activity. Duplication is a finding because
    two documents describing one activity will eventually disagree, and the
    verification control document cannot say which governs."""
    overlap = set(report.get("covers_scope_of") or []) & set(drd_reports_present)
    return [{"report_id": report.get("report_id"), "duplicates": d,
             "issue": "duplicates_drd_report"} for d in sorted(overlap)]


def field_violations(report):
    """Findings for the minimum identification an additional report needs to
    be citable from the verification control document."""
    out = []
    for f in REQUIRED_FIELDS:
        value = report.get(f)
        if not value or (isinstance(value, (list, tuple)) and not value):
            out.append({"report_id": report.get("report_id"),
                        "issue": "missing_field", "field": f})
    return out


def approval_violations(report):
    """Finding when the author also approved the report. Self-approval removes
    the second pair of eyes that makes the record worth citing."""
    author, approver = report.get("author"), report.get("approver")
    if author and approver and author == approver:
        return [{"report_id": report.get("report_id"),
                 "issue": "author_approved_own_report"}]
    return []


def missing_report_violations(activity, reports):
    """Finding when an activity meets a trigger condition and no additional
    report exists for it."""
    if additional_report_required(activity) and not reports:
        return [{"activity_ref": activity.get("activity_ref"),
                 "triggers": active_triggers(activity),
                 "issue": "additional_report_required_but_absent"}]
    return []


def other_reports_review(activity, reports, drd_reports_present):
    """Full clause 5.3.2.6 review for one verification activity.

    activity: {"activity_ref": str, "conditions": {trigger: bool}}
    reports: [{"report_id", "requirement_refs", "activity_ref", "author",
               "approver", "covers_scope_of": [drd_report_type]}]

    Returns {"required", "triggers", "findings"}.
    """
    reports = list(reports)
    findings = list(missing_report_violations(activity, reports))
    seen = set()
    for rep in reports:
        rid = rep.get("report_id")
        if rid and rid in seen:
            raise ValueError("duplicate report_id: %s" % rid)
        if rid:
            seen.add(rid)
        findings += field_violations(rep)
        findings += approval_violations(rep)
        findings += duplication_violations(rep, drd_reports_present)
    return {"required": additional_report_required(activity),
            "triggers": active_triggers(activity), "findings": findings}


def is_documentation_sufficient(review):
    """True when the activity's additional documentation is neither missing
    nor duplicative nor unciteable."""
    return not review["findings"]
