"""Assessment of a component manufacturer against the Class 1 baseline.

Anchor: ECSS-Q-ST-60C clause 4.2.3.2 (the assessment a part manufacturer is
put through, against the European space component baseline criteria, as part
of evaluating a part for the highest assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The assessment is a set of criteria, each carrying a weight that says how
  much of the manufacturer's standing it supplies. A few of them are baseline
  criteria: the quality system, process control, traceability and change
  notification. Nothing else in the assessment compensates for them, so a
  weak rating on one of those blocks approval outright.
* Each criterion carries a rating and the evidence source the rating rests on.
  The rating says what was found; the source says how much the finding is
  worth. A statement on a questionnaire and a finding from an on-site audit
  are not the same observation, so the source derates the rating rather than
  being recorded beside it.
* Evidence older than the audit validity period is derated to the weakest
  source, because an audit describes a factory on the day it was run.
* The capability index is weighted effective rating over total weight. It is a
  ranking number, not a pass mark: a blocking non-conformance on a baseline
  criterion fails the assessment at any index.
* A criterion nobody assessed is not assessed, not excused. Every assessment
  is graded against the full criteria set, so a short report cannot shrink the
  baseline it is measured against.
"""

from __future__ import annotations

import math

# Assessment criteria and the share of the manufacturer's standing each holds.
CRITERION_WEIGHTS = {
    "quality-management-system-certification": 1.0,
    "process-control-and-statistical-monitoring": 0.9,
    "traceability-and-lot-identification": 0.9,
    "change-notification-procedure": 0.8,
    "space-product-assurance-experience": 0.8,
    "lot-acceptance-and-screening-capability": 0.8,
    "wafer-source-and-subcontractor-control": 0.7,
    "failure-analysis-capability": 0.7,
    "electrostatic-discharge-control-programme": 0.6,
}

# Criteria nothing else in the assessment compensates for.
BASELINE_CRITERIA = (
    "quality-management-system-certification",
    "process-control-and-statistical-monitoring",
    "traceability-and-lot-identification",
    "change-notification-procedure",
)

# What the assessor found.
RATING_VALUE = {
    "fully-compliant": 1.0,
    "compliant-with-observation": 0.85,
    "partially-compliant": 0.5,
    "non-compliant": 0.0,
    "not-assessed": 0.0,
}

# How much the finding is worth, given how it was obtained.
EVIDENCE_SOURCE_FACTOR = {
    "on-site-audit": 1.0,
    "remote-audit": 0.9,
    "third-party-audit-report": 0.8,
    "questionnaire-response-only": 0.6,
    "no-evidence-supplied": 0.0,
}

WEAKEST_SUPPORTED_SOURCE = "questionnaire-response-only"

# An audit describes a factory on the day it was run.
AUDIT_VALIDITY_MONTHS = 36

# Effective rating a baseline criterion has to reach before it stops blocking.
BASELINE_MIN_EFFECTIVE = 0.85

# Capability index an approvable manufacturer has to reach.
APPROVAL_INDEX = 0.90

# The index is a ratio of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
ASSESSMENT_TOLERANCE = 1e-9

VERDICTS = (
    "manufacturer-approved-for-class-1",
    "manufacturer-approved-with-open-actions",
    "manufacturer-not-approved-for-class-1",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def criterion_weight(name):
    """Weight of one assessment criterion; unknown names are rejected."""
    if name not in CRITERION_WEIGHTS:
        raise ValueError(
            "unknown assessment criterion %r (known: %s)"
            % (name, ", ".join(sorted(CRITERION_WEIGHTS)))
        )
    return CRITERION_WEIGHTS[name]


def rating_value(rating):
    """Value of an assessor rating before the evidence source derates it."""
    if rating not in RATING_VALUE:
        raise ValueError(
            "unknown rating %r (known: %s)" % (rating, ", ".join(sorted(RATING_VALUE)))
        )
    return RATING_VALUE[rating]


def source_factor(source, age_months):
    """Worth of the evidence source, derated once it is out of validity.

    Returns ``(factor, findings)``.
    """
    if source not in EVIDENCE_SOURCE_FACTOR:
        raise ValueError(
            "unknown evidence source %r (known: %s)"
            % (source, ", ".join(sorted(EVIDENCE_SOURCE_FACTOR)))
        )
    age = _real(age_months, "evidence_age_months")
    if age < 0.0:
        raise ValueError("evidence_age_months must not be negative, got %r" % (age,))
    factor = EVIDENCE_SOURCE_FACTOR[source]
    findings = []
    if age > float(AUDIT_VALIDITY_MONTHS):
        weakest = EVIDENCE_SOURCE_FACTOR[WEAKEST_SUPPORTED_SOURCE]
        if factor > weakest:
            factor = weakest
            findings.append("assessment-evidence-out-of-validity")
    return (factor, findings)


def normalize_criterion(raw):
    """Validate one criterion record and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("criterion must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("criterion")
    criterion_weight(name)  # validation only
    rating = raw.get("rating", "not-assessed")
    rating_value(rating)  # validation only
    source = raw.get("evidence_source", "no-evidence-supplied")
    if source not in EVIDENCE_SOURCE_FACTOR:
        raise ValueError(
            "unknown evidence source %r (known: %s)"
            % (source, ", ".join(sorted(EVIDENCE_SOURCE_FACTOR)))
        )
    if rating != "not-assessed" and source == "no-evidence-supplied":
        raise ValueError(
            "criterion %r carries a rating but no evidence source" % (name,)
        )
    age = _real(raw.get("evidence_age_months", 0.0), "evidence_age_months")
    return {
        "criterion": name,
        "rating": rating,
        "evidence_source": source,
        "evidence_age_months": age,
    }


def assess_criterion(raw):
    """Grade one criterion into an effective rating and its findings."""
    record = normalize_criterion(raw)
    name = record["criterion"]
    weight = criterion_weight(name)
    value = rating_value(record["rating"])
    factor, findings = source_factor(record["evidence_source"], record["evidence_age_months"])
    effective = value * factor
    if record["rating"] == "not-assessed":
        findings.append("criterion-not-assessed")
    elif record["rating"] == "non-compliant":
        findings.append("criterion-non-compliant")
    elif record["rating"] == "partially-compliant":
        findings.append("criterion-partially-compliant")
    elif record["rating"] == "compliant-with-observation":
        findings.append("criterion-observation-open")
    if record["evidence_source"] == "questionnaire-response-only":
        findings.append("rating-rests-on-questionnaire-only")
    blocking = (
        name in BASELINE_CRITERIA
        and effective < BASELINE_MIN_EFFECTIVE - ASSESSMENT_TOLERANCE
    )
    if blocking:
        findings.append("baseline-criterion-blocking")
    return {
        "criterion": name,
        "rating": record["rating"],
        "evidence_source": record["evidence_source"],
        "evidence_age_months": record["evidence_age_months"],
        "weight": weight,
        "rating_value": value,
        "source_factor": factor,
        "effective_rating": effective,
        "weighted_rating": weight * effective,
        "blocking": blocking,
        "findings": findings,
    }


def capability_index(records):
    """Weighted effective rating of a set of graded criteria over the weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("an assessment must carry at least one criterion")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_rating"], "weighted_rating")
    if total_weight <= 0.0:
        raise ValueError("total assessment weight must be positive")
    return earned / total_weight


def blocking_criteria(records):
    """Baseline criteria that block approval, heaviest first, then by name."""
    blocked = [r for r in records if r["blocking"]]
    return sorted(blocked, key=lambda r: (-r["weight"], r["criterion"]))


def assess_manufacturer(manufacturer_id, criteria):
    """Grade a part manufacturer against the whole Class 1 baseline.

    Every criterion the baseline owes is graded, including the ones the report
    left out entirely -- a criterion nobody assessed is not assessed, not
    excused.
    """
    if not isinstance(manufacturer_id, str) or not manufacturer_id.strip():
        raise ValueError(
            "manufacturer_id must be a non-empty string, got %r" % (manufacturer_id,)
        )
    if not isinstance(criteria, (list, tuple)):
        raise ValueError(
            "criteria must be a list or tuple, got %r" % (type(criteria).__name__,)
        )
    declared = {}
    for raw in criteria:
        record = normalize_criterion(raw)
        if record["criterion"] in declared:
            raise ValueError("duplicate assessment criterion %r" % (record["criterion"],))
        declared[record["criterion"]] = record
    records = []
    for name in sorted(CRITERION_WEIGHTS):
        records.append(assess_criterion(declared.get(name, {"criterion": name})))
    index = capability_index(records)
    blocked = blocking_criteria(records)
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"criterion": record["criterion"], "finding": finding})
    if blocked or index < APPROVAL_INDEX - ASSESSMENT_TOLERANCE:
        verdict = "manufacturer-not-approved-for-class-1"
    elif findings:
        verdict = "manufacturer-approved-with-open-actions"
    else:
        verdict = "manufacturer-approved-for-class-1"
    reassessment_due = any(
        "assessment-evidence-out-of-validity" in r["findings"] for r in records
    )
    return {
        "manufacturer_id": manufacturer_id,
        "records": records,
        "capability_index": index,
        "blocking_criteria": [r["criterion"] for r in blocked],
        "findings": findings,
        "verdict": verdict,
        "reassessment_due": reassessment_due,
        "approved_for_class_1": verdict != "manufacturer-not-approved-for-class-1",
    }
