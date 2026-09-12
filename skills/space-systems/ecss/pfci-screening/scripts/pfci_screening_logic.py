"""
PFCI screening logic: Figure 6-1 decision-tree procedure per
ECSS-E-ST-32C clause 6.1.

Determines whether each structural item or GSE item must be treated as a
Potentially Fracture Critical Item (PFCI). Items are processed through a
sequential five-gate check; the first gate that fails produces a NON_PFCI
outcome and records the disqualifying gate name. Items that pass all five
gates are PFCI and require fracture control analysis.

Reference: ECSS-E-ST-32C, clause 6.1, Figure 6-1.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# Below this cross-sectional area the item is too small to sustain a
# fatigue-initiating flaw of consequence (programme default; may be tightened).
MIN_CROSS_SECTION_CM2: float = 1.27


class ScreeningOutcome(Enum):
    PFCI = "PFCI"
    NON_PFCI = "NON_PFCI"


class FailureEffect(Enum):
    """Worst-case consequence of item failure during its design service life."""
    CATASTROPHIC = "CATASTROPHIC"   # loss of mission or crew safety hazard
    CRITICAL = "CRITICAL"           # significant, unrecoverable mission degradation
    MARGINAL = "MARGINAL"           # minor, recoverable mission impact
    NEGLIGIBLE = "NEGLIGIBLE"       # no meaningful mission or safety impact


@dataclass
class StructuralItem:
    """Input record for a single PFCI screening candidate.

    Fields
    ------
    item_id
        Unique identifier (non-empty, no leading/trailing whitespace).
    name
        Human-readable label.
    is_structural
        True if the item performs a load-bearing structural function.
    failure_effect
        Worst-case FailureEffect of the item's failure.
    carries_tensile_load
        True if the item is subject to direct tensile, bending, or combined
        tensile loading that could drive crack growth.
    material_susceptible
        True if the material is susceptible to fracture (all metallic alloys,
        composites, ceramics, glass). False only when an approved
        fracture-toughness declaration establishes non-susceptibility.
    min_cross_section_cm2
        Minimum cross-sectional area in cm². Must be >= 0.
    is_gse
        True for Ground Support Equipment items.
    gse_critical_operation
        Relevant only when is_gse is True. True if the GSE item is engaged
        in a critical operation whose failure could cause loss of flight
        hardware or a crew safety hazard.
    notes
        Optional free-text rationale or reference.
    """
    item_id: str
    name: str
    is_structural: bool
    failure_effect: FailureEffect
    carries_tensile_load: bool
    material_susceptible: bool
    min_cross_section_cm2: float
    is_gse: bool = False
    gse_critical_operation: bool = False
    notes: str = ""


@dataclass
class ScreeningResult:
    """Output record for one screened item."""
    item_id: str
    outcome: ScreeningOutcome
    reasons: List[str] = field(default_factory=list)
    disqualifying_gate: Optional[str] = None   # populated only for NON_PFCI


def _validate_item(item: StructuralItem) -> None:
    """Raise ValueError for structurally invalid input records."""
    if not isinstance(item.item_id, str) or not item.item_id.strip():
        raise ValueError("item_id must be a non-empty, non-whitespace string")
    if not isinstance(item.failure_effect, FailureEffect):
        raise ValueError(
            f"failure_effect must be a FailureEffect member; got {item.failure_effect!r}"
        )
    if item.min_cross_section_cm2 < 0:
        raise ValueError(
            f"min_cross_section_cm2 must be >= 0; got {item.min_cross_section_cm2}"
        )


def screen_item(
    item: StructuralItem,
    min_cross_section_override_cm2: Optional[float] = None,
) -> ScreeningResult:
    """Apply the Figure 6-1 five-gate screening to a single item.

    Parameters
    ----------
    item
        Candidate item to screen.
    min_cross_section_override_cm2
        Programme-level override for the minimum cross-section threshold.
        When None, the module default (MIN_CROSS_SECTION_CM2) is used.

    Returns
    -------
    ScreeningResult
        outcome is PFCI or NON_PFCI; disqualifying_gate is set for NON_PFCI.
    """
    _validate_item(item)
    threshold = (
        min_cross_section_override_cm2
        if min_cross_section_override_cm2 is not None
        else MIN_CROSS_SECTION_CM2
    )
    if threshold < 0:
        raise ValueError(
            f"min_cross_section_override_cm2 must be >= 0; got {threshold}"
        )

    # GSE pre-check — excludes GSE not engaged in a critical operation.
    if item.is_gse and not item.gse_critical_operation:
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=[
                "GSE item is not engaged in a critical operation; "
                "excluded from fracture control scope before five-gate check."
            ],
            disqualifying_gate="GSE-CRITICAL-OPERATION",
        )

    # Gate 1 — Structural role
    if not item.is_structural:
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=["Item performs no structural (load-bearing) function."],
            disqualifying_gate="GATE-1-STRUCTURAL",
        )

    # Gate 2 — Failure effect: must be CATASTROPHIC or CRITICAL to proceed.
    if item.failure_effect in (FailureEffect.MARGINAL, FailureEffect.NEGLIGIBLE):
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=[
                f"Worst-case failure effect is {item.failure_effect.value}; "
                "not catastrophic or critical — fracture control not required."
            ],
            disqualifying_gate="GATE-2-FAILURE-EFFECT",
        )

    # Gate 3 — Tensile-load presence
    if not item.carries_tensile_load:
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=[
                "Item carries no tensile loading; crack propagation under "
                "sustained or cyclic tension is not applicable."
            ],
            disqualifying_gate="GATE-3-TENSILE-LOAD",
        )

    # Gate 4 — Material fracture susceptibility
    if not item.material_susceptible:
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=[
                "Material has an approved non-susceptibility declaration; "
                "fracture control is not required for this material."
            ],
            disqualifying_gate="GATE-4-MATERIAL",
        )

    # Gate 5 — Minimum dimension threshold
    if item.min_cross_section_cm2 < threshold:
        return ScreeningResult(
            item_id=item.item_id,
            outcome=ScreeningOutcome.NON_PFCI,
            reasons=[
                f"Minimum cross-section {item.min_cross_section_cm2:.4f} cm² is below "
                f"the threshold {threshold:.4f} cm²; item is too small to sustain a "
                "consequential fatigue-initiating flaw."
            ],
            disqualifying_gate="GATE-5-DIMENSION",
        )

    # All gates passed → PFCI
    pfci_reasons = [
        "Structural item (Gate 1 passed).",
        f"Failure effect is {item.failure_effect.value} (Gate 2 passed).",
        "Carries tensile loads susceptible to crack propagation (Gate 3 passed).",
        "Material is susceptible to fracture (Gate 4 passed).",
        f"Cross-section {item.min_cross_section_cm2:.4f} cm² meets or exceeds "
        f"threshold {threshold:.4f} cm² (Gate 5 passed).",
    ]
    if item.is_gse:
        pfci_reasons.insert(0, "GSE item engaged in a critical operation (GSE pre-check passed).")

    return ScreeningResult(
        item_id=item.item_id,
        outcome=ScreeningOutcome.PFCI,
        reasons=pfci_reasons,
    )


def screen_batch(
    items: List[StructuralItem],
    min_cross_section_override_cm2: Optional[float] = None,
) -> dict:
    """Screen a list of items and return a summary dictionary.

    Returns
    -------
    dict with keys:
        total           : int — number of items processed
        pfci_count      : int — number of PFCI outcomes
        non_pfci_count  : int — number of NON_PFCI outcomes
        pfci_ids        : list[str] — item_id values of PFCI items
        results         : list[ScreeningResult] — one entry per input item
    """
    results = [
        screen_item(item, min_cross_section_override_cm2) for item in items
    ]
    pfci_results = [r for r in results if r.outcome == ScreeningOutcome.PFCI]
    non_pfci_results = [r for r in results if r.outcome == ScreeningOutcome.NON_PFCI]
    return {
        "total": len(results),
        "pfci_count": len(pfci_results),
        "non_pfci_count": len(non_pfci_results),
        "pfci_ids": [r.item_id for r in pfci_results],
        "results": results,
    }
