"""
HFE ground verification logic — ECSS-E-ST-10-11C §4.11.3, Annex D.

Paraphrased from public ECSS process guidelines; no verbatim ECSS text.
Stdlib only, offline, deterministic.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple


class VerificationMethod(Enum):
    TEST = "T"
    DEMONSTRATION = "D"
    ANALYSIS = "A"
    INSPECTION = "I"


class AnnexDEvent(Enum):
    FUNCTIONAL_TASK = "FUNCTIONAL_TASK"
    ERGONOMIC_ASSESSMENT = "ERGONOMIC_ASSESSMENT"
    COGNITIVE_WORKLOAD = "COGNITIVE_WORKLOAD"
    DISPLAY_CONTROL_INTERFACE = "DISPLAY_CONTROL_INTERFACE"
    LABEL_AND_CUE = "LABEL_AND_CUE"
    EMERGENCY_PROCEDURE = "EMERGENCY_PROCEDURE"
    MAINTENANCE_TASK = "MAINTENANCE_TASK"
    ENVIRONMENTAL_ERGONOMICS = "ENVIRONMENTAL_ERGONOMICS"


# Per §4.11.3 and Annex D: these five categories must each be covered by
# at least one T or D method before verification closure.
MANDATORY_ANNEX_D_EVENTS: frozenset = frozenset({
    AnnexDEvent.FUNCTIONAL_TASK,
    AnnexDEvent.ERGONOMIC_ASSESSMENT,
    AnnexDEvent.COGNITIVE_WORKLOAD,
    AnnexDEvent.DISPLAY_CONTROL_INTERFACE,
    AnnexDEvent.EMERGENCY_PROCEDURE,
})

# Only observable methods count toward covering an Annex D mandatory event.
OBSERVABLE_METHODS: frozenset = frozenset({
    VerificationMethod.TEST,
    VerificationMethod.DEMONSTRATION,
})

VALID_STATUSES: frozenset = frozenset({"PASS", "FAIL", "PENDING"})


class HFERequirementError(ValueError):
    """Raised when a requirement record is structurally invalid."""


def parse_verification_method(method_str: str) -> VerificationMethod:
    """Return VerificationMethod for a single-letter code; raise on unknown."""
    upper = method_str.strip().upper()
    for m in VerificationMethod:
        if m.value == upper:
            return m
    raise HFERequirementError(
        f"Unknown verification method '{method_str}'. "
        f"Valid codes: {sorted(m.value for m in VerificationMethod)}"
    )


def parse_annex_d_event(event_str: str) -> AnnexDEvent:
    """Return AnnexDEvent for an event name string; raise on unknown."""
    upper = event_str.strip().upper()
    for e in AnnexDEvent:
        if e.value == upper:
            return e
    raise HFERequirementError(
        f"Unknown Annex D event '{event_str}'. "
        f"Valid values: {sorted(e.value for e in AnnexDEvent)}"
    )


def validate_requirement(req: Dict) -> Tuple[bool, str]:
    """
    Check a single HFE requirement dict for structural validity.

    Required keys: req_id, description, method, status.
    Conditional: annex_d_event required when method is T or D.
    Returns (True, '') on success or (False, reason) on failure.
    """
    for key in ("req_id", "description", "method", "status"):
        if key not in req:
            return False, f"Missing required field '{key}'"
        if not str(req[key]).strip():
            return False, f"Field '{key}' must not be empty"

    try:
        method = parse_verification_method(req["method"])
    except HFERequirementError as exc:
        return False, str(exc)

    if method in OBSERVABLE_METHODS:
        event_str = str(req.get("annex_d_event", "")).strip()
        if not event_str:
            return False, (
                f"Requirement '{req['req_id']}': method '{req['method']}' "
                "requires an 'annex_d_event' mapping"
            )
        try:
            parse_annex_d_event(event_str)
        except HFERequirementError as exc:
            return False, str(exc)

    status_upper = str(req["status"]).strip().upper()
    if status_upper not in VALID_STATUSES:
        return False, (
            f"Invalid status '{req['status']}'. "
            f"Valid values: {sorted(VALID_STATUSES)}"
        )

    return True, ""


def check_mandatory_event_coverage(requirements: List[Dict]) -> List[str]:
    """
    Return sorted list of mandatory Annex D event names not covered.

    A requirement covers a mandatory event when its method is T or D
    and its annex_d_event matches that event's name.  A or I methods
    do not count as observable coverage.
    """
    covered: set = set()
    for req in requirements:
        method_str = str(req.get("method", "")).strip()
        event_str = str(req.get("annex_d_event", "")).strip()
        try:
            method = parse_verification_method(method_str)
        except HFERequirementError:
            continue
        if method not in OBSERVABLE_METHODS or not event_str:
            continue
        try:
            event = parse_annex_d_event(event_str)
            covered.add(event)
        except HFERequirementError:
            continue

    return sorted(
        e.value
        for e in MANDATORY_ANNEX_D_EVENTS
        if e not in covered
    )


def evaluate_test_readiness(
    readiness_criteria: List[Dict],
) -> Tuple[bool, List[str]]:
    """
    Check pre-event readiness criteria before an Annex D test event.

    Each criterion dict must have: criterion_id, description, met (bool).
    Returns (ready, list_of_unmet_criterion_ids).
    ready is True only when every criterion has met == True.
    """
    unmet: List[str] = []
    for criterion in readiness_criteria:
        if not criterion.get("met", False):
            unmet.append(str(criterion.get("criterion_id", "UNKNOWN")))
    return len(unmet) == 0, unmet


def compute_compliance_summary(requirements: List[Dict]) -> Dict:
    """
    Aggregate pass/fail/pending counts across all requirements.

    Returns dict with keys: total, pass, fail, pending, compliant.
    compliant is True only when total > 0, fail == 0, and pending == 0.
    """
    counts: Dict = {"total": 0, "pass": 0, "fail": 0, "pending": 0}
    for req in requirements:
        status = str(req.get("status", "PENDING")).strip().upper()
        counts["total"] += 1
        if status == "PASS":
            counts["pass"] += 1
        elif status == "FAIL":
            counts["fail"] += 1
        else:
            counts["pending"] += 1

    counts["compliant"] = (
        counts["total"] > 0
        and counts["fail"] == 0
        and counts["pending"] == 0
    )
    return counts


def aggregate_findings(requirements: List[Dict]) -> List[str]:
    """
    Collect structural, coverage, and status findings for a requirement list.

    Returns a list of human-readable finding strings; empty means no issues.
    """
    findings: List[str] = []

    for req in requirements:
        valid, reason = validate_requirement(req)
        if not valid:
            req_id = str(req.get("req_id", "<unknown>"))
            findings.append(f"[INVALID] {req_id}: {reason}")

    uncovered = check_mandatory_event_coverage(requirements)
    for event in uncovered:
        findings.append(
            f"[COVERAGE] Mandatory Annex D event not covered: {event}"
        )

    for req in requirements:
        status = str(req.get("status", "")).strip().upper()
        req_id = str(req.get("req_id", "<unknown>"))
        if status == "FAIL":
            findings.append(
                f"[FAIL] Requirement {req_id} did not pass ground verification"
            )
        elif status == "PENDING":
            findings.append(
                f"[PENDING] Requirement {req_id} not yet verified"
            )

    return findings
