"""ECSS-E-ST-10-02C clause 5.2.2.2 -- test method applicability and
E-ST-10-03 delegation logic.

Deterministic, offline, stdlib-only. Paraphrased procedure, not
verbatim standard text: the standard clause is cited as an anchor
only.
"""

from dataclasses import dataclass, replace
from typing import Optional

APPLICABILITY_CONDITIONS = (
    "physically_measurable",
    "test_article_available",
    "environment_reproducible",
    "pass_fail_criteria_defined",
)

TERMINAL_STATUSES = ("passed", "failed", "waived")
ALL_STATUSES = ("pending",) + TERMINAL_STATUSES


@dataclass(frozen=True)
class TestConditions:
    physically_measurable: bool
    test_article_available: bool
    environment_reproducible: bool
    pass_fail_criteria_defined: bool


@dataclass(frozen=True)
class TestVerificationRecord:
    requirement_id: str
    conditions: TestConditions
    test_specification_ref: Optional[str] = None
    procedure_embedded: bool = False
    status: str = "pending"
    evidence_ref: Optional[str] = None
    waiver_ref: Optional[str] = None

    def __post_init__(self):
        if not self.requirement_id or not self.requirement_id.strip():
            raise ValueError("requirement_id must be a non-empty string")
        if not isinstance(self.conditions, TestConditions):
            raise TypeError("conditions must be a TestConditions instance")
        if self.status not in ALL_STATUSES:
            raise ValueError(
                f"unknown status {self.status!r}; must be one of {ALL_STATUSES}"
            )


def evaluate_applicability(conditions: TestConditions) -> tuple[bool, list[str]]:
    """Check the four clause 5.2.2.2 conditions for test as a formal
    verification method. Returns (is_applicable, unmet_condition_names)."""
    unmet = [
        name
        for name in APPLICABILITY_CONDITIONS
        if not getattr(conditions, name)
    ]
    return (len(unmet) == 0, unmet)


def evaluate_delegation(record: TestVerificationRecord) -> list[str]:
    """Check that a test-method record delegates procedural detail to an
    E-ST-10-03 test specification instead of embedding it. Returns a list
    of violation descriptions (empty list means compliant)."""
    violations = []
    if not record.test_specification_ref or not record.test_specification_ref.strip():
        violations.append(
            f"{record.requirement_id}: missing E-ST-10-03 test specification reference"
        )
    if record.procedure_embedded:
        violations.append(
            f"{record.requirement_id}: detailed procedure embedded instead of "
            "delegated to an E-ST-10-03 test specification"
        )
    return violations


def close_out(
    record: TestVerificationRecord,
    new_status: str,
    evidence_ref: Optional[str] = None,
    waiver_ref: Optional[str] = None,
) -> TestVerificationRecord:
    """Return a new record with a terminal status applied, enforcing the
    evidence/waiver-reference and applicability gates. Raises ValueError
    on any violated precondition; never mutates the input record."""
    if new_status not in ALL_STATUSES:
        raise ValueError(f"unknown status {new_status!r}; must be one of {ALL_STATUSES}")

    is_applicable, unmet = evaluate_applicability(record.conditions)
    if new_status in TERMINAL_STATUSES and not is_applicable:
        raise ValueError(
            f"{record.requirement_id}: cannot close to {new_status!r}; "
            f"test method not applicable, unmet conditions: {unmet}"
        )

    if new_status in ("passed", "failed"):
        if not evidence_ref or not evidence_ref.strip():
            raise ValueError(
                f"{record.requirement_id}: {new_status} requires an evidence_ref"
            )
        return replace(record, status=new_status, evidence_ref=evidence_ref, waiver_ref=None)

    if new_status == "waived":
        if not waiver_ref or not waiver_ref.strip():
            raise ValueError(f"{record.requirement_id}: waived requires a waiver_ref")
        return replace(record, status=new_status, waiver_ref=waiver_ref, evidence_ref=None)

    return replace(record, status="pending", evidence_ref=None, waiver_ref=None)


def build_verification_summary(records: list[TestVerificationRecord]) -> dict:
    """Roll up a requirement set's test-applicability and delegation status.

    Returns a dict with counts and the sub-lists needed to explain them.
    Raises ValueError on an empty or duplicate-id record set.
    """
    if not records:
        raise ValueError("records must be a non-empty list")

    seen_ids = set()
    for record in records:
        if record.requirement_id in seen_ids:
            raise ValueError(f"duplicate requirement_id: {record.requirement_id}")
        seen_ids.add(record.requirement_id)

    not_applicable = []
    delegation_violations = []
    status_counts = {status: 0 for status in ALL_STATUSES}

    for record in records:
        is_applicable, unmet = evaluate_applicability(record.conditions)
        if not is_applicable:
            not_applicable.append((record.requirement_id, unmet))
        else:
            delegation_violations.extend(evaluate_delegation(record))
        status_counts[record.status] += 1

    applicable_count = len(records) - len(not_applicable)
    ready = (
        len(not_applicable) == 0
        and len(delegation_violations) == 0
        and status_counts["pending"] == 0
    )

    return {
        "total": len(records),
        "applicable_count": applicable_count,
        "not_applicable": not_applicable,
        "delegation_violations": delegation_violations,
        "status_counts": status_counts,
        "ready": ready,
    }
