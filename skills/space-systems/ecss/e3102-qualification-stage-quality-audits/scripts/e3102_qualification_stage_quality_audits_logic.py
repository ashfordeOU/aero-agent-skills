"""Qualification stage structure and supplier-process quality audits.

Anchor: ECSS-E-ST-31-02C clauses 5.5.1 and 5.5.2 (the qualification stage and
the quality audits of the supplier processes the stage depends on).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Order the stage activities and confirm the planned sequence keeps the
   precedences that make the stage meaningful: the plan is approved before
   anything is built, the supplier process audit closes before the
   qualification model is manufactured, and the test campaign precedes the
   qualification review.
2. Work out which of the supplier's declared processes are special processes
   whose result cannot be verified by inspecting the finished article, and so
   owe a quality audit.
3. Grade each audit record: inside its validity window at the reference month,
   run by an auditor independent of the audited organisation, and with no
   major finding still open.
4. Reduce that to a coverage picture per process, a coverage fraction, and the
   blocking findings that hold the stage at its entry gate.

Dates are handled as integer month indices on a project calendar so the logic
stays deterministic, offline and free of locale or timezone behaviour.
"""

import math

__all__ = [
    "AUDIT_VALIDITY_MONTHS",
    "COVERAGE_TOLERANCE",
    "STAGE_ACTIVITIES",
    "STAGE_PRECEDENCES",
    "SPECIAL_PROCESSES",
    "validate_audit",
    "audit_age_months",
    "audit_status",
    "special_processes_required",
    "process_coverage",
    "coverage_fraction",
    "sequence_findings",
    "stage_readiness",
    "assess_qualification_stage",
]

# An audit older than this at the reference month no longer speaks for the
# process as it is run today.
AUDIT_VALIDITY_MONTHS = 24

# Coverage is a quotient of two counts; absorb only its representation error.
COVERAGE_TOLERANCE = 1e-12

STAGE_ACTIVITIES = (
    "qualification-plan-approval",
    "supplier-process-quality-audit",
    "qualification-model-manufacture",
    "qualification-test-campaign",
    "qualification-review",
)

# (earlier, later) pairs that the planned sequence must preserve.
STAGE_PRECEDENCES = (
    ("qualification-plan-approval", "supplier-process-quality-audit"),
    ("supplier-process-quality-audit", "qualification-model-manufacture"),
    ("qualification-model-manufacture", "qualification-test-campaign"),
    ("qualification-test-campaign", "qualification-review"),
)

# Processes whose conformity cannot be established by inspecting the delivered
# item, so the evidence has to come from auditing how the supplier runs them.
SPECIAL_PROCESSES = frozenset(
    {
        "closure-welding",
        "brazing",
        "wick-sintering",
        "groove-extrusion",
        "cleaning-and-passivation",
        "fluid-purity-and-charging",
        "heat-treatment",
        "non-destructive-inspection",
        "leak-testing",
    }
)


def _month(value, label):
    """Return an integer project month index or raise ValueError."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer project month index, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _count(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_audit(record):
    """Return a validated supplier-process audit record."""
    if not isinstance(record, dict):
        raise ValueError("audit record must be a mapping")
    for key in ("process", "audit_month", "independent_auditor", "major_findings_open"):
        if key not in record:
            raise ValueError("audit record missing required key '%s'" % key)
    process = record["process"]
    if not isinstance(process, str) or not process.strip():
        raise ValueError("audit record 'process' must be a non-empty string")
    if not isinstance(record["independent_auditor"], bool):
        raise ValueError("audit record 'independent_auditor' must be a boolean")
    return {
        "process": process.strip().lower(),
        "audit_month": _month(record["audit_month"], "audit_month"),
        "independent_auditor": record["independent_auditor"],
        "major_findings_open": _count(record["major_findings_open"], "major_findings_open"),
        "minor_findings_open": _count(
            record.get("minor_findings_open", 0), "minor_findings_open"
        ),
    }


def audit_age_months(audit, reference_month):
    """Return the audit age in months at the reference month."""
    record = validate_audit(audit)
    ref = _month(reference_month, "reference_month")
    if ref < record["audit_month"]:
        raise ValueError(
            "reference_month %d precedes the audit month %d" % (ref, record["audit_month"])
        )
    return ref - record["audit_month"]


def audit_status(audit, reference_month, validity_months=AUDIT_VALIDITY_MONTHS):
    """Return the status of one audit: covered, expired, not-independent or open-major."""
    record = validate_audit(audit)
    if not isinstance(validity_months, int) or isinstance(validity_months, bool):
        raise ValueError("validity_months must be an integer")
    if validity_months <= 0:
        raise ValueError("validity_months must be positive, got %d" % validity_months)
    age = audit_age_months(record, reference_month)
    if age > validity_months:
        status = "expired"
    elif not record["independent_auditor"]:
        status = "not-independent"
    elif record["major_findings_open"] > 0:
        status = "open-major-finding"
    else:
        status = "covered"
    return {
        "process": record["process"],
        "status": status,
        "age_months": age,
        "validity_months": validity_months,
        "major_findings_open": record["major_findings_open"],
        "minor_findings_open": record["minor_findings_open"],
    }


def special_processes_required(declared_processes):
    """Return the sorted declared processes that owe a quality audit."""
    if not isinstance(declared_processes, (list, tuple)) or not declared_processes:
        raise ValueError("declared_processes must be a non-empty sequence")
    required = set()
    for item in declared_processes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("declared process must be a non-empty string, got %r" % (item,))
        key = item.strip().lower()
        if key in SPECIAL_PROCESSES:
            required.add(key)
    return sorted(required)


def process_coverage(declared_processes, audits, reference_month,
                     validity_months=AUDIT_VALIDITY_MONTHS):
    """Return {process: status} for every declared special process.

    Where a process carries several audit records the most recent one governs;
    an older clean audit does not rescue a recent one with an open major
    finding.
    """
    required = special_processes_required(declared_processes)
    if audits is None:
        audits = []
    if not isinstance(audits, (list, tuple)):
        raise ValueError("audits must be a sequence of audit records")
    latest = {}
    for item in audits:
        record = validate_audit(item)
        current = latest.get(record["process"])
        if current is None or record["audit_month"] > current["audit_month"]:
            latest[record["process"]] = record
    coverage = {}
    for process in required:
        record = latest.get(process)
        if record is None:
            coverage[process] = {
                "process": process,
                "status": "missing",
                "age_months": None,
                "validity_months": validity_months,
                "major_findings_open": 0,
                "minor_findings_open": 0,
            }
        else:
            coverage[process] = audit_status(record, reference_month, validity_months)
    return coverage


def coverage_fraction(coverage):
    """Return the fraction of required processes whose audit is covered."""
    if not isinstance(coverage, dict) or not coverage:
        raise ValueError("coverage must be a non-empty mapping")
    good = 0
    for entry in coverage.values():
        if not isinstance(entry, dict) or "status" not in entry:
            raise ValueError("each coverage entry must carry a 'status'")
        if entry["status"] == "covered":
            good += 1
    return good / len(coverage)


def sequence_findings(planned_sequence):
    """Return the precedence violations in a planned stage sequence."""
    if not isinstance(planned_sequence, (list, tuple)) or not planned_sequence:
        raise ValueError("planned_sequence must be a non-empty sequence of activity names")
    position = {}
    for index, item in enumerate(planned_sequence):
        if not isinstance(item, str) or not item.strip():
            raise ValueError("activity name must be a non-empty string, got %r" % (item,))
        key = item.strip().lower()
        if key not in STAGE_ACTIVITIES:
            raise ValueError(
                "unknown stage activity '%s'; known activities: %s"
                % (item, ", ".join(STAGE_ACTIVITIES))
            )
        if key in position:
            raise ValueError("stage activity '%s' appears twice in the sequence" % key)
        position[key] = index
    findings = []
    for activity in STAGE_ACTIVITIES:
        if activity not in position:
            findings.append("stage activity '%s' is absent from the plan" % activity)
    for earlier, later in STAGE_PRECEDENCES:
        if earlier in position and later in position and position[earlier] > position[later]:
            findings.append("'%s' is planned after '%s'" % (earlier, later))
    return findings


def stage_readiness(coverage, findings):
    """Return the blocking reasons that hold the stage at its entry gate."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    blocking = list(findings)
    for process in sorted(coverage):
        entry = coverage[process]
        if entry["status"] == "missing":
            blocking.append("special process '%s' has no quality audit" % process)
        elif entry["status"] == "expired":
            blocking.append(
                "audit of '%s' is %d months old against a %d month validity"
                % (process, entry["age_months"], entry["validity_months"])
            )
        elif entry["status"] == "not-independent":
            blocking.append("audit of '%s' was not run by an independent auditor" % process)
        elif entry["status"] == "open-major-finding":
            blocking.append(
                "audit of '%s' still carries %d open major finding(s)"
                % (process, entry["major_findings_open"])
            )
    return blocking


def assess_qualification_stage(spec):
    """Run the full clause 5.5.1/5.5.2 stage-and-audit assessment.

    spec keys: planned_sequence, declared_processes, audits, reference_month,
    optional validity_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("planned_sequence", "declared_processes", "reference_month"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    validity = spec.get("validity_months", AUDIT_VALIDITY_MONTHS)
    findings = sequence_findings(spec["planned_sequence"])
    coverage = process_coverage(
        spec["declared_processes"], spec.get("audits"), spec["reference_month"], validity
    )
    fraction = coverage_fraction(coverage)
    blocking = stage_readiness(coverage, findings)
    complete = math.isclose(fraction, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE)
    return {
        "coverage": coverage,
        "coverage_fraction": fraction,
        "audits_complete": complete,
        "sequence_findings": findings,
        "blocking_findings": blocking,
        "ready_for_test_campaign": not blocking,
        "minor_findings_open": sum(e["minor_findings_open"] for e in coverage.values()),
    }
