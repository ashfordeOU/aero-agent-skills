"""
Fracture control summary report logic — ECSS-E-ST-32C clause 6.4.4.

Determines per-item compliance and compiles the programme-level summary
for every flight item in the fracture control programme.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# Thresholds per ECSS-E-ST-32C clause 6.4.4
MIN_LIFE_RATIO_INSPECTABLE = 1.0
MIN_LIFE_RATIO_SAFE_LIFE = 4.0

VALID_INSPECTION_CATEGORIES = {"inspectable", "safe_life"}


@dataclass
class FlightItemRecord:
    """Input record for one flight item in the fracture control programme."""

    item_id: str
    name: str
    fracture_critical: bool
    basis_documented: bool
    # Fields below are only relevant for fracture-critical items.
    analysis_complete: bool = False
    life_ratio: float = 0.0          # computed life / required life (scatter applied)
    safety_factor_met: bool = False
    inspection_category: str = ""    # "inspectable" or "safe_life"
    inspection_method: str = ""      # e.g. "NDE", "visual", "proof_test"
    inspection_interval_met: bool = False
    test_verified: bool = False


@dataclass
class ItemStatus:
    """Compliance status for a single flight item."""

    item_id: str
    fracture_critical: bool
    findings: List[str] = field(default_factory=list)
    compliant: bool = False


@dataclass
class SummaryReport:
    """Programme-level fracture control summary across all flight items."""

    total_items: int
    fracture_critical_count: int
    non_fracture_critical_count: int
    compliant_count: int
    non_compliant_count: int
    item_statuses: List[ItemStatus]
    overall_compliant: bool


def _validate_record(record: FlightItemRecord) -> None:
    """Raise ValueError for structurally invalid input before any checks."""
    if not record.item_id or not record.item_id.strip():
        raise ValueError("item_id must be a non-empty string")
    if not record.name or not record.name.strip():
        raise ValueError(f"name must be non-empty for item '{record.item_id}'")
    if record.fracture_critical and record.inspection_category not in ("", *VALID_INSPECTION_CATEGORIES):
        raise ValueError(
            f"Item '{record.item_id}': inspection_category must be one of "
            f"{sorted(VALID_INSPECTION_CATEGORIES)} or empty string, "
            f"got '{record.inspection_category}'"
        )


def assess_item(record: FlightItemRecord) -> ItemStatus:
    """
    Assess compliance for a single flight item and return its ItemStatus.

    Raises ValueError for invalid input (missing id/name, unknown category).
    """
    _validate_record(record)

    findings: List[str] = []

    if not record.basis_documented:
        findings.append(
            f"Item '{record.item_id}': designation basis not documented"
        )

    if record.fracture_critical:
        if not record.analysis_complete:
            findings.append(
                f"Item '{record.item_id}': crack growth analysis not complete"
            )
        else:
            # Life ratio check — threshold depends on inspection category.
            if record.inspection_category == "safe_life":
                if record.life_ratio < MIN_LIFE_RATIO_SAFE_LIFE:
                    findings.append(
                        f"Item '{record.item_id}': safe-life ratio {record.life_ratio:.3f} "
                        f"< required {MIN_LIFE_RATIO_SAFE_LIFE}"
                    )
            elif record.inspection_category == "inspectable":
                if record.life_ratio < MIN_LIFE_RATIO_INSPECTABLE:
                    findings.append(
                        f"Item '{record.item_id}': life ratio {record.life_ratio:.3f} "
                        f"< required {MIN_LIFE_RATIO_INSPECTABLE}"
                    )
            else:
                findings.append(
                    f"Item '{record.item_id}': inspection category not set; "
                    "must be 'inspectable' or 'safe_life'"
                )

            if not record.safety_factor_met:
                findings.append(
                    f"Item '{record.item_id}': fracture safety factor not satisfied"
                )

        if record.inspection_category == "inspectable":
            if not record.inspection_method or not record.inspection_method.strip():
                findings.append(
                    f"Item '{record.item_id}': inspection method not recorded"
                )
            if not record.inspection_interval_met:
                findings.append(
                    f"Item '{record.item_id}': inspection interval requirement not met"
                )

        if not record.test_verified:
            findings.append(
                f"Item '{record.item_id}': test verification not complete"
            )

    return ItemStatus(
        item_id=record.item_id,
        fracture_critical=record.fracture_critical,
        findings=findings,
        compliant=len(findings) == 0,
    )


def compile_summary(records: List[FlightItemRecord]) -> SummaryReport:
    """
    Assess all flight items and compile the programme-level summary report.

    Raises ValueError if any record is structurally invalid.
    """
    statuses: List[ItemStatus] = [assess_item(r) for r in records]

    fracture_critical_count = sum(1 for s in statuses if s.fracture_critical)
    non_fracture_critical_count = len(statuses) - fracture_critical_count
    compliant_count = sum(1 for s in statuses if s.compliant)
    non_compliant_count = len(statuses) - compliant_count

    return SummaryReport(
        total_items=len(statuses),
        fracture_critical_count=fracture_critical_count,
        non_fracture_critical_count=non_fracture_critical_count,
        compliant_count=compliant_count,
        non_compliant_count=non_compliant_count,
        item_statuses=statuses,
        overall_compliant=(non_compliant_count == 0),
    )
