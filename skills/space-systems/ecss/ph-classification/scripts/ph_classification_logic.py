"""
ph_classification_logic.py

Pressure hardware category determination per ECSS-E-ST-32 clause 4.1.
(Paraphrased procedure; no verbatim ECSS text reproduced. Cite the
standard and clause as the anchor.)

Four categories:
  PV  — Pressure Vessel: single closed item whose primary function is
        pressure retention only; no concurrent primary structural loads.
  PS  — Pressure System: interconnected assembly of pressure-retaining
        components forming a functional unit; constituent items are each
        categorized individually.
  PC  — Pressure Container: item that retains pressure AND concurrently
        carries primary structural loads.
  SPE — Simple Pressure Equipment: item satisfying all five simplicity
        criteria simultaneously (shape, MEOP threshold, volume threshold,
        standard material, no internal heat source).
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# SPE simplicity thresholds (values paraphrased from clause 4.1 criteria)
# ---------------------------------------------------------------------------

SPE_MAX_MEOP_BAR: float = 30.0    # Maximum MEOP for SPE eligibility, bar
SPE_MAX_VOLUME_LITRES: float = 50.0  # Maximum internal volume for SPE eligibility, L


# ---------------------------------------------------------------------------
# Input data type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HardwareItem:
    """Input descriptor for a single hardware item to be categorized."""

    item_id: str
    is_assembly: bool              # True → item is a multi-component pressure assembly
    carries_structural_loads: bool # True → item concurrently carries primary structural loads
    shape_simple: bool             # True → geometry is sphere, plain cylinder, or flat-ended cylinder
    meop_bar: float                # Maximum expected operating pressure, bar (≥ 0)
    volume_litres: float           # Internal volume, litres (≥ 0)
    uses_common_material: bool     # True → material is standard/recognized for pressure service
    no_heat_source: bool           # True → no internal heat generation
    sub_items: tuple = ()          # Constituent HardwareItem objects when is_assembly=True


# ---------------------------------------------------------------------------
# Output data type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CategoryResult:
    """Result of a single hardware item category determination."""

    item_id: str
    category: str         # "PV", "PS", "PC", or "SPE"
    rationale: str        # Plain-text rationale for traceability
    sub_item_results: tuple = ()  # CategoryResult objects for PS sub-items


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CategoryError(ValueError):
    """Raised when input data is invalid or category determination cannot proceed."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(item: HardwareItem) -> None:
    """Raise CategoryError if input data is incomplete or out of range."""
    if not isinstance(item.item_id, str) or not item.item_id.strip():
        raise CategoryError(
            "item_id must be a non-empty string."
        )
    if item.meop_bar < 0.0:
        raise CategoryError(
            f"meop_bar must be non-negative; got {item.meop_bar!r}."
        )
    if item.volume_litres < 0.0:
        raise CategoryError(
            f"volume_litres must be non-negative; got {item.volume_litres!r}."
        )
    if item.is_assembly and not item.sub_items:
        raise CategoryError(
            "An assembly item (is_assembly=True) must provide at least one "
            "sub-item in sub_items."
        )


# ---------------------------------------------------------------------------
# SPE criteria gate (figure 4-2 logic, paraphrased)
# ---------------------------------------------------------------------------

def meets_spe_criteria(item: HardwareItem) -> bool:
    """
    Return True only when all five SPE simplicity criteria are satisfied
    simultaneously.  A single failure is enough to route the item to PV.
    """
    return (
        item.shape_simple
        and item.meop_bar <= SPE_MAX_MEOP_BAR
        and item.volume_litres <= SPE_MAX_VOLUME_LITRES
        and item.uses_common_material
        and item.no_heat_source
    )


def spe_failing_criteria(item: HardwareItem) -> List[str]:
    """Return a list of SPE criterion labels that the item fails."""
    failures = []
    if not item.shape_simple:
        failures.append("non-simple geometry")
    if item.meop_bar > SPE_MAX_MEOP_BAR:
        failures.append(
            f"MEOP {item.meop_bar} bar exceeds SPE threshold {SPE_MAX_MEOP_BAR} bar"
        )
    if item.volume_litres > SPE_MAX_VOLUME_LITRES:
        failures.append(
            f"volume {item.volume_litres} L exceeds SPE threshold "
            f"{SPE_MAX_VOLUME_LITRES} L"
        )
    if not item.uses_common_material:
        failures.append("non-standard material")
    if not item.no_heat_source:
        failures.append("internal heat source present")
    return failures


# ---------------------------------------------------------------------------
# Single-item category determination (figure 4-1 decision tree, paraphrased)
# ---------------------------------------------------------------------------

def determine_category(item: HardwareItem) -> CategoryResult:
    """
    Determine the pressure hardware category for one item.

    Decision path per clause 4.1 figure 4-1 (paraphrased):
      1. Assembly of connected pressure-retaining items  → PS
      2. Concurrently carries primary structural loads   → PC
      3. All five SPE simplicity criteria satisfied      → SPE
      4. Otherwise                                       → PV
    """
    _validate(item)

    # Branch 1 — Pressure System (assembly)
    if item.is_assembly:
        sub_results = tuple(determine_category(si) for si in item.sub_items)
        return CategoryResult(
            item_id=item.item_id,
            category="PS",
            rationale=(
                "Item is an interconnected assembly of pressure-retaining "
                "components forming a functional unit; it is a Pressure "
                "System (PS) per ECSS-E-ST-32 clause 4.1."
            ),
            sub_item_results=sub_results,
        )

    # Branch 2 — Pressure Container (structural loads concurrent)
    if item.carries_structural_loads:
        return CategoryResult(
            item_id=item.item_id,
            category="PC",
            rationale=(
                "Item retains pressure and concurrently carries primary "
                "structural loads; it is a Pressure Container (PC) per "
                "ECSS-E-ST-32 clause 4.1."
            ),
        )

    # Branch 3 — Simple Pressure Equipment (all simplicity criteria met)
    if meets_spe_criteria(item):
        return CategoryResult(
            item_id=item.item_id,
            category="SPE",
            rationale=(
                f"Item satisfies all five SPE simplicity criteria "
                f"(simple shape, MEOP {item.meop_bar} bar "
                f"≤ {SPE_MAX_MEOP_BAR} bar, "
                f"volume {item.volume_litres} L "
                f"≤ {SPE_MAX_VOLUME_LITRES} L, "
                f"standard material, no heat source); it is Simple "
                f"Pressure Equipment (SPE) per ECSS-E-ST-32 clause 4.1."
            ),
        )

    # Branch 4 — Pressure Vessel (default)
    failures = spe_failing_criteria(item)
    failure_str = "; ".join(failures) if failures else "no SPE criteria met"
    return CategoryResult(
        item_id=item.item_id,
        category="PV",
        rationale=(
            f"Item retains pressure as its primary function and does not "
            f"satisfy SPE criteria ({failure_str}); it is a Pressure "
            f"Vessel (PV) per ECSS-E-ST-32 clause 4.1."
        ),
    )


# ---------------------------------------------------------------------------
# Composite / batch determination (figures 4-2 / 4-3 scope)
# ---------------------------------------------------------------------------

def determine_composite_category(items: List[HardwareItem]) -> List[CategoryResult]:
    """
    Determine pressure categories for a list of hardware items.

    Returns one CategoryResult per item in input order.
    Raises CategoryError if the list is empty or any item fails validation.
    """
    if not items:
        raise CategoryError(
            "Item list must contain at least one HardwareItem."
        )
    return [determine_category(item) for item in items]
