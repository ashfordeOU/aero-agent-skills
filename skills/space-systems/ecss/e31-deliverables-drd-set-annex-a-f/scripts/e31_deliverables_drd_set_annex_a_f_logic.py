"""Thermal control deliverables and the document requirement definition set.

Anchor: ECSS-E-ST-31C clause 4.9 and its annexes A to F (the thermal control
deliverables and the document requirement definitions behind them: the thermal
mathematical model specification, the thermal and geometrical model
description, the thermal analysis report, the thermal interface control
document, the thermal balance test specification and the detailed design
description). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Hold the six deliverables, the content each one owes, the review each one
   is due at, and the deliverable each one depends on, as one register.
2. Grade a programme's declared deliverable plan against that register: which
   documents are absent, which are present but missing content, and which are
   planned against the wrong review.
3. Compute schedule slack in days between each planned issue date and the date
   of the review the deliverable is due at, so a late document is a number of
   days late rather than a boolean.
4. Enforce the dependency order: a model description cannot issue before the
   model specification it implements, an analysis report cannot issue before
   the model it reports on, and a balance test specification cannot issue
   before the analysis that sizes its cases.
5. Roll the set up: completeness fraction, the deliverable with the least
   slack, and the ordered findings.
"""

import datetime

__all__ = [
    "MILESTONES",
    "DRD_SET",
    "milestone_rank",
    "validate_date",
    "validate_document_key",
    "required_sections",
    "missing_documents",
    "missing_sections",
    "schedule_slack_days",
    "milestone_findings",
    "dependency_findings",
    "evaluate_deliverable",
    "assess_deliverable_set",
]

# Programme reviews in chronological order.
MILESTONES = ("srr", "pdr", "cdr", "qr", "ar")

# The six thermal control deliverables of the annex set. Each carries the
# content it owes, the review it is due at, and the deliverable it depends on.
DRD_SET = {
    "thermal-mathematical-model-specification": {
        "annex": "A",
        "due": "pdr",
        "depends_on": (),
        "sections": (
            "nodal-breakdown-rules",
            "conductor-derivation-rules",
            "boundary-condition-set",
            "model-exchange-format",
        ),
    },
    "thermal-and-geometrical-model-description": {
        "annex": "B",
        "due": "cdr",
        "depends_on": ("thermal-mathematical-model-specification",),
        "sections": (
            "geometry-description",
            "optical-properties",
            "nodal-map",
            "conductor-listing",
            "model-validation-record",
        ),
    },
    "thermal-analysis-report": {
        "annex": "C",
        "due": "cdr",
        "depends_on": ("thermal-and-geometrical-model-description",),
        "sections": (
            "case-definition",
            "predicted-temperatures",
            "margin-summary",
            "model-uncertainty",
        ),
    },
    "thermal-interface-control-document": {
        "annex": "D",
        "due": "pdr",
        "depends_on": (),
        "sections": (
            "interface-temperatures",
            "interface-conductance",
            "heat-flow-budget",
            "mounting-requirements",
        ),
    },
    "thermal-balance-test-specification": {
        "annex": "E",
        "due": "cdr",
        "depends_on": ("thermal-analysis-report",),
        "sections": (
            "test-objectives",
            "test-configuration",
            "test-cases",
            "success-criteria",
            "instrumentation-plan",
        ),
    },
    "thermal-control-detailed-design-description": {
        "annex": "F",
        "due": "cdr",
        "depends_on": ("thermal-interface-control-document",),
        "sections": (
            "hardware-list",
            "surface-finishes",
            "heater-and-control-design",
            "mli-design",
            "margin-policy",
        ),
    },
}


def milestone_rank(milestone):
    """Return the chronological ordinal of a programme review."""
    if not isinstance(milestone, str):
        raise ValueError("milestone must be a string")
    name = milestone.strip().lower()
    if name not in MILESTONES:
        raise ValueError("unknown milestone %r; expected one of %s" % (milestone, MILESTONES))
    return MILESTONES.index(name)


def validate_date(value, label):
    """Return a validated calendar date from an ISO day string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        raise ValueError("%s must be a calendar day, not a timestamp" % label)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def validate_document_key(key):
    """Return a validated deliverable key from the annex set."""
    if not isinstance(key, str):
        raise ValueError("document key must be a string")
    name = key.strip().lower()
    if name not in DRD_SET:
        raise ValueError("unknown deliverable %r; expected one of %s"
                         % (key, tuple(sorted(DRD_SET))))
    return name


def required_sections(key):
    """Return the content sections a deliverable owes."""
    return DRD_SET[validate_document_key(key)]["sections"]


def missing_documents(declared):
    """Return the deliverables of the annex set that a plan does not declare."""
    if not isinstance(declared, (list, tuple, set, frozenset, dict)):
        raise ValueError("declared must be a collection of deliverable keys")
    names = set()
    for key in declared:
        names.add(validate_document_key(key))
    return sorted(set(DRD_SET) - names)


def missing_sections(key, declared_sections):
    """Return the content sections a declared deliverable does not carry."""
    name = validate_document_key(key)
    if not isinstance(declared_sections, (list, tuple, set, frozenset)):
        raise ValueError("declared sections must be a collection of section names")
    present = set()
    for section in declared_sections:
        if not isinstance(section, str) or not section.strip():
            raise ValueError("section names must be non-empty strings")
        present.add(section.strip().lower())
    return [section for section in DRD_SET[name]["sections"] if section not in present]


def schedule_slack_days(planned_issue_date, milestone_date):
    """Return the whole days between a planned issue and the review it serves."""
    planned = validate_date(planned_issue_date, "planned_issue_date")
    milestone = validate_date(milestone_date, "milestone_date")
    return (milestone - planned).days


def milestone_findings(key, planned_milestone):
    """Return the finding raised when a deliverable is planned against a later review."""
    name = validate_document_key(key)
    due = DRD_SET[name]["due"]
    planned = planned_milestone
    if milestone_rank(planned) > milestone_rank(due):
        return ["%s: planned for %s, owed at %s"
                % (name, planned.strip().lower(), due)]
    return []


def dependency_findings(key, planned_dates):
    """Return the findings raised when a deliverable precedes what it depends on."""
    name = validate_document_key(key)
    if not isinstance(planned_dates, dict) or not planned_dates:
        raise ValueError("planned_dates must be a non-empty mapping of deliverable to date")
    normalised = {}
    for other, value in planned_dates.items():
        normalised[validate_document_key(other)] = validate_date(
            value, "planned date for %r" % other
        )
    if name not in normalised:
        raise ValueError("planned_dates must contain the deliverable being graded")
    findings = []
    for dependency in DRD_SET[name]["depends_on"]:
        if dependency not in normalised:
            findings.append("%s: depends on %s, which the plan does not carry"
                            % (name, dependency))
            continue
        if normalised[name] < normalised[dependency]:
            findings.append(
                "%s: planned to issue %d days before %s, which it depends on"
                % (name, (normalised[dependency] - normalised[name]).days, dependency)
            )
    return findings


def evaluate_deliverable(entry, milestone_dates, planned_dates):
    """Evaluate one declared deliverable against its annex requirement."""
    if not isinstance(entry, dict):
        raise ValueError("deliverable entry must be a mapping")
    for key in ("key", "sections", "planned_milestone", "planned_issue_date"):
        if key not in entry:
            raise ValueError("deliverable entry missing required key '%s'" % key)
    name = validate_document_key(entry["key"])
    if not isinstance(milestone_dates, dict) or not milestone_dates:
        raise ValueError("milestone_dates must be a non-empty mapping")
    due = DRD_SET[name]["due"]
    if due not in {m.strip().lower() for m in milestone_dates if isinstance(m, str)}:
        raise ValueError("milestone_dates must carry the %r review that %s is owed at"
                         % (due, name))
    due_date = None
    for milestone, value in milestone_dates.items():
        if isinstance(milestone, str) and milestone.strip().lower() == due:
            due_date = validate_date(value, "date of the %r review" % due)
    slack = schedule_slack_days(entry["planned_issue_date"], due_date)
    gaps = missing_sections(name, entry["sections"])
    findings = ["%s: content section %s not declared" % (name, section) for section in gaps]
    findings.extend(milestone_findings(name, entry["planned_milestone"]))
    findings.extend(dependency_findings(name, planned_dates))
    if slack < 0:
        findings.append("%s: planned to issue %d days after the %s it is owed at"
                        % (name, -slack, due))
    return {
        "key": name,
        "annex": DRD_SET[name]["annex"],
        "due_review": due,
        "slack_days": slack,
        "missing_sections": gaps,
        "complete": not findings,
        "findings": findings,
    }


def assess_deliverable_set(spec):
    """Run the full clause 4.9 and annex A-F deliverable assessment.

    spec keys: deliverables (sequence of declared deliverable entries),
    milestone_dates (mapping of review name to ISO date).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("deliverables", "milestone_dates"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    entries = spec["deliverables"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['deliverables'] must be a non-empty sequence")
    planned_dates = {}
    for entry in entries:
        if not isinstance(entry, dict) or "key" not in entry or "planned_issue_date" not in entry:
            raise ValueError("every deliverable entry needs a 'key' and a 'planned_issue_date'")
        name = validate_document_key(entry["key"])
        if name in planned_dates:
            raise ValueError("duplicate deliverable %r in the plan" % name)
        planned_dates[name] = validate_date(
            entry["planned_issue_date"], "planned issue date for %r" % name
        )
    records = [
        evaluate_deliverable(entry, spec["milestone_dates"], planned_dates)
        for entry in entries
    ]
    absent = missing_documents(planned_dates)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for name in absent:
        findings.append("%s: deliverable of annex %s is not in the plan"
                        % (name, DRD_SET[name]["annex"]))
    complete = [record["key"] for record in records if record["complete"]]
    tightest = min(records, key=lambda r: (r["slack_days"], r["key"]))["key"]
    return {
        "deliverables": records,
        "absent_deliverables": absent,
        "complete_deliverables": complete,
        "completeness_fraction": len(complete) / float(len(DRD_SET)),
        "tightest_slack_deliverable": tightest,
        "deliverable_set_complete": not findings,
        "findings": findings,
    }
