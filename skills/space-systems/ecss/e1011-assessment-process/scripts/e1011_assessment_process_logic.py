"""
ECSS-E-ST-10 §4.10.1 — Continuous assessment process logic.
Reference: ECSS-E-ST-10C clause 4.10.1 and Annex C (assessment report outline).
Stdlib only. No external dependencies.
"""

import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

VALID_FINDING_TYPES: frozenset = frozenset(
    {"observation", "action_item", "non_conformance"}
)
VALID_FINDING_STATUSES: frozenset = frozenset({"open", "closed", "waived"})
VALID_THRESHOLD_TYPES: frozenset = frozenset({"max", "min"})

MARGINAL_BAND_FRACTION = 0.10  # within 10 % of threshold => marginal


class AssessmentError(ValueError):
    """Raised when an input violates the assessment process rules."""


@dataclass
class Finding:
    finding_id: str
    finding_type: str          # observation | action_item | non_conformance
    description: str
    status: str                # open | closed | waived
    responsible: str
    waiver_rationale: Optional[str] = None


@dataclass
class TechnicalPerformanceMeasure:
    measure_id: str
    name: str
    current_value: float
    threshold_value: float
    threshold_type: str        # max | min
    unit: str


@dataclass
class AssessmentRecord:
    record_id: str
    phase: str
    event_name: str
    event_date: str            # ISO 8601 date string YYYY-MM-DD
    scope_description: str
    findings: List[Finding] = field(default_factory=list)
    measures: List[TechnicalPerformanceMeasure] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_finding_type(finding_type: str) -> str:
    """Return the normalised finding type or raise AssessmentError."""
    t = finding_type.lower().strip()
    if t not in VALID_FINDING_TYPES:
        raise AssessmentError(
            f"Unknown finding type '{finding_type}'. "
            f"Expected one of: {sorted(VALID_FINDING_TYPES)}."
        )
    return t


def validate_finding_status(status: str) -> str:
    """Return the normalised finding status or raise AssessmentError."""
    s = status.lower().strip()
    if s not in VALID_FINDING_STATUSES:
        raise AssessmentError(
            f"Unknown finding status '{status}'. "
            f"Expected one of: {sorted(VALID_FINDING_STATUSES)}."
        )
    return s


# ---------------------------------------------------------------------------
# Technical Performance Measure evaluation
# ---------------------------------------------------------------------------

def evaluate_measure_status(measure: TechnicalPerformanceMeasure) -> str:
    """
    Determine whether a TPM is nominal, marginal, or exceeded.

    For a max-type threshold the value must not exceed the threshold.
    For a min-type threshold the value must not fall below the threshold.
    A value within MARGINAL_BAND_FRACTION of the threshold boundary is
    marginal rather than nominal; beyond the boundary it is exceeded.
    """
    if measure.threshold_type not in VALID_THRESHOLD_TYPES:
        raise AssessmentError(
            f"threshold_type must be 'max' or 'min', "
            f"got '{measure.threshold_type}'."
        )
    v = measure.current_value
    t = measure.threshold_value
    band = abs(t) * MARGINAL_BAND_FRACTION if t != 0 else 0.0

    if measure.threshold_type == "max":
        if v > t:
            return "exceeded"
        if v > t - band:
            return "marginal"
        return "nominal"
    else:  # min
        if v < t:
            return "exceeded"
        if v < t + band:
            return "marginal"
        return "nominal"


# ---------------------------------------------------------------------------
# Finding closure validation
# ---------------------------------------------------------------------------

def check_finding_closure_valid(finding: Finding) -> Tuple[bool, List[str]]:
    """
    Return (True, []) when the finding record is structurally complete and
    any waiver is properly documented.  Return (False, [reasons]) otherwise.
    """
    issues: List[str] = []
    if not finding.finding_id.strip():
        issues.append("finding_id is empty")
    if not finding.description.strip():
        issues.append("description is empty")
    if not finding.responsible.strip():
        issues.append("responsible party is empty")
    if finding.status == "waived" and not finding.waiver_rationale:
        issues.append("waiver requires a rationale")
    return (len(issues) == 0, issues)


# ---------------------------------------------------------------------------
# Overall assessment status
# ---------------------------------------------------------------------------

def compute_overall_status(
    findings: List[Finding],
    measure_statuses: List[str],
) -> str:
    """
    Derive the single overall status for an assessment event.

    Rules (in descending priority):
    - non_compliant : any open non_conformance finding exists
    - at_risk       : any measure is exceeded, or any action_item is open
    - marginal      : any measure is marginal (no open AIs, no open NCs,
                      no exceeded measures)
    - compliant     : all findings closed/waived, all measures nominal
    """
    open_nc = any(
        f.status == "open" and f.finding_type == "non_conformance"
        for f in findings
    )
    if open_nc:
        return "non_compliant"

    any_exceeded = any(s == "exceeded" for s in measure_statuses)
    open_ai = any(
        f.status == "open" and f.finding_type == "action_item"
        for f in findings
    )
    if any_exceeded or open_ai:
        return "at_risk"

    any_marginal = any(s == "marginal" for s in measure_statuses)
    if any_marginal:
        return "marginal"

    return "compliant"


# ---------------------------------------------------------------------------
# Annex C report field generation
# ---------------------------------------------------------------------------

def generate_annex_c_fields(
    record: AssessmentRecord,
    measure_statuses: List[str],
) -> dict:
    """
    Produce the structured fields required by the Annex C assessment report
    outline (ECSS-E-ST-10C Annex C).  Returns a plain dict; all values are
    stdlib-safe types.
    """
    if len(measure_statuses) != len(record.measures):
        raise AssessmentError(
            f"measure_statuses length ({len(measure_statuses)}) does not match "
            f"record.measures length ({len(record.measures)})."
        )

    open_f = [f for f in record.findings if f.status == "open"]
    closed_f = [f for f in record.findings if f.status == "closed"]
    waived_f = [f for f in record.findings if f.status == "waived"]
    overall = compute_overall_status(record.findings, measure_statuses)

    return {
        "record_id": record.record_id,
        "event_name": record.event_name,
        "event_date": record.event_date,
        "phase": record.phase,
        "scope": record.scope_description,
        "total_findings": len(record.findings),
        "open_count": len(open_f),
        "closed_count": len(closed_f),
        "waived_count": len(waived_f),
        "open_finding_ids": [f.finding_id for f in open_f],
        "measure_statuses": {
            m.measure_id: s
            for m, s in zip(record.measures, measure_statuses)
        },
        "overall_status": overall,
    }


# ---------------------------------------------------------------------------
# Record-level validation
# ---------------------------------------------------------------------------

def validate_assessment_record(record: AssessmentRecord) -> List[str]:
    """
    Check an AssessmentRecord for structural completeness.
    Returns a list of issue strings; an empty list means the record is valid.
    """
    issues: List[str] = []

    if not record.record_id.strip():
        issues.append("record_id is empty")
    if not record.event_name.strip():
        issues.append("event_name is empty")
    if not record.scope_description.strip():
        issues.append("scope_description is empty")

    try:
        datetime.date.fromisoformat(record.event_date)
    except ValueError:
        issues.append(
            f"event_date '{record.event_date}' is not a valid ISO 8601 date (YYYY-MM-DD)"
        )

    for f in record.findings:
        try:
            validate_finding_type(f.finding_type)
        except AssessmentError as exc:
            issues.append(str(exc))
        try:
            validate_finding_status(f.status)
        except AssessmentError as exc:
            issues.append(str(exc))
        if f.status in ("closed", "waived"):
            ok, errs = check_finding_closure_valid(f)
            if not ok:
                issues.extend(errs)

    for m in record.measures:
        if m.threshold_type not in VALID_THRESHOLD_TYPES:
            issues.append(
                f"measure '{m.measure_id}': threshold_type must be 'max' or 'min', "
                f"got '{m.threshold_type}'"
            )

    return issues
