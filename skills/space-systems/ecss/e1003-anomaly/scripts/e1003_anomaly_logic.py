#!/usr/bin/env python3
"""ECSS-E-ST-10C §4.3.4 anomaly handling during testing (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the AIT
standard's anomaly clause requires that every unexpected event or failure
detected during testing be immediately contained to preserve the as-found
state, formally recorded in an anomaly report with a defined minimum set of
fields, assigned a disposition (accept as-is, repair and retest, waiver
required, reject, or pending analysis), and that a retest scope be derived
stating which previously executed test cases must be repeated following any
corrective action. This module implements anomaly categorization by failure
domain, containment-action derivation from severity level, anomaly-record
field validation, disposition validation, and retest-scope derivation. It
does not implement the configuration-control authority routing or the
waiver-approval workflow.
"""

ANOMALY_CATEGORIES = frozenset({
    "hardware_failure",
    "software_failure",
    "environmental_exceedance",
    "electrical_anomaly",
    "mechanical_anomaly",
})

SEVERITY_LEVELS = ("critical", "major", "minor")

DISPOSITION_CODES = frozenset({
    "accept_as_is",
    "repair_and_retest",
    "waiver_required",
    "reject",
    "pending_analysis",
})

REQUIRED_RECORD_FIELDS = frozenset({
    "anomaly_id",
    "description",
    "detected_at",
    "affected_item",
    "test_procedure_ref",
    "detected_by",
    "initial_findings",
})

_CONTAINMENT_ACTIONS = {
    "critical": [
        "halt_test_immediately",
        "preserve_test_configuration",
        "isolate_affected_unit",
        "notify_responsible_engineer",
        "secure_test_data",
    ],
    "major": [
        "suspend_test_activity",
        "document_current_state",
        "assess_risk_to_hardware",
        "notify_test_conductor",
    ],
    "minor": [
        "continue_with_enhanced_monitoring",
        "document_anomaly_in_test_log",
    ],
}


def categorize_anomaly(anomaly_type):
    """Returns the failure-domain category string for anomaly_type.
    Raises ValueError for any type outside the known set."""
    if anomaly_type in ANOMALY_CATEGORIES:
        return anomaly_type
    raise ValueError(
        "unrecognized anomaly type %r under E-ST-10C §4.3.4" % (anomaly_type,)
    )


def containment_actions(severity):
    """Returns an ordered list of required containment actions for the
    given severity level. Raises ValueError for an unrecognized severity."""
    if severity in _CONTAINMENT_ACTIONS:
        return list(_CONTAINMENT_ACTIONS[severity])
    raise ValueError(
        "unrecognized severity %r; expected one of %r" % (severity, SEVERITY_LEVELS)
    )


def validate_record(record):
    """Returns a sorted list of field names missing from the anomaly record.
    An empty list means the record satisfies the minimum documentation
    requirement under E-ST-10C §4.3.4. Does not mutate record."""
    return sorted(REQUIRED_RECORD_FIELDS - set(record.keys()))


def validate_disposition(disposition):
    """Returns True when disposition is a recognized code.
    Raises ValueError for an unrecognized disposition code."""
    if disposition in DISPOSITION_CODES:
        return True
    raise ValueError(
        "unrecognized disposition %r under E-ST-10C §4.3.4" % (disposition,)
    )


def disposition_requires_retest(disposition):
    """Returns True when the disposition mandates an explicit retest.
    Only 'repair_and_retest' mandates retesting; other dispositions may still
    overlap previously executed tests but that is handled by retest_scope.
    Raises ValueError for an unrecognized disposition code."""
    validate_disposition(disposition)
    return disposition == "repair_and_retest"


def retest_scope(disposition, affected_test_ids, repair_touches_test_ids=None):
    """Derives the set of test IDs that must be repeated under §4.3.4.

    For 'repair_and_retest': returns the union of affected_test_ids and any
    tests whose scope overlaps the repair action (repair_touches_test_ids).
    For all other dispositions: returns an empty set (no mandatory retest from
    disposition alone).

    Does not mutate the input iterables. Raises ValueError for an unrecognized
    disposition."""
    validate_disposition(disposition)
    if disposition != "repair_and_retest":
        return set()
    base = set(affected_test_ids)
    if repair_touches_test_ids:
        base = base | set(repair_touches_test_ids)
    return base


def anomaly_review(anomaly):
    """Full §4.3.4 anomaly review for one anomaly dict.

    anomaly keys:
      anomaly_type: str — failure domain key
      severity: str — "critical" | "major" | "minor"
      record: dict — documentation fields captured at detection time
      disposition: str | None — disposition code, or None if not yet assigned
      affected_test_ids: list[str] — test IDs whose results may be invalidated
      repair_touches_test_ids: list[str] | None — additional tests overlapping
          the repair scope

    Returns a new dict with:
      category: str — failure domain (from categorize_anomaly)
      containment: list[str] — ordered containment actions for the severity
      record_gaps: list[str] — sorted list of missing required record fields
      disposition_valid: bool — True when disposition is a recognized code
      retest_required: bool — True when disposition mandates retesting
      retest_scope: set[str] — test IDs that must be repeated
      findings: list[str] — aggregated finding strings (empty means no issues)

    Raises ValueError for an unrecognized anomaly_type or severity.
    Does not mutate the input dict.
    """
    findings = []

    category = categorize_anomaly(anomaly["anomaly_type"])
    actions = containment_actions(anomaly["severity"])

    record_gaps = validate_record(anomaly.get("record", {}))
    if record_gaps:
        findings.append("missing_record_fields:" + ",".join(record_gaps))

    disposition = anomaly.get("disposition")
    disp_valid = False
    requires_retest = False
    scope = set()

    if disposition is None:
        findings.append("missing_disposition")
    else:
        disp_valid = validate_disposition(disposition)
        if disposition == "pending_analysis":
            findings.append("disposition_pending_analysis")
        requires_retest = disposition_requires_retest(disposition)
        scope = retest_scope(
            disposition,
            anomaly.get("affected_test_ids", []),
            anomaly.get("repair_touches_test_ids"),
        )

    return {
        "category": category,
        "containment": actions,
        "record_gaps": record_gaps,
        "disposition_valid": disp_valid,
        "retest_required": requires_retest,
        "retest_scope": scope,
        "findings": findings,
    }
