"""
Safe-life compliance logic — ECSS-E-ST-32C clause 6.3.2.

Structural items are categorized as safe-life or fail-safe. Safe-life items
must demonstrate by analysis or test that an assumed initial crack does not
grow to critical size within the design life (with scatter factor applied) and
that residual strength at end-of-life crack size meets the limit-load
requirement.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

VALID_CATEGORIES: Tuple[str, ...] = ("safe-life", "fail-safe")
VALID_EVIDENCE_TYPES: Tuple[str, ...] = ("analysis", "test")

# Minimum ratio of residual_strength / limit_load for compliance.
RESIDUAL_STRENGTH_RATIO_MINIMUM: float = 1.0

# Default scatter factor applied to design life (project value overrides).
DEFAULT_SCATTER_FACTOR: float = 4.0


@dataclass
class SafeLifeItem:
    """Represents one structural item under safe-life compliance assessment."""
    item_id: str
    category: str                            # "safe-life" or "fail-safe"
    crack_growth_life: Optional[float] = None  # cycles or hours to critical crack
    design_life: Optional[float] = None        # required service life (same unit)
    scatter_factor: float = DEFAULT_SCATTER_FACTOR
    residual_strength: Optional[float] = None  # load capacity at end-of-life crack size
    limit_load: Optional[float] = None         # design limit load (same unit)
    evidence: List[str] = field(default_factory=list)  # subset of VALID_EVIDENCE_TYPES


@dataclass
class ItemResult:
    """Compliance outcome for a single structural item."""
    item_id: str
    category: str
    category_valid: bool
    crack_growth_check: str      # "PASS" | "FAIL" | "MISSING_DATA" | "N/A"
    residual_strength_check: str # "PASS" | "FAIL" | "MISSING_DATA" | "N/A"
    evidence_check: str          # "PASS" | "FAIL" | "N/A"
    compliant: bool
    notes: List[str] = field(default_factory=list)


def categorize_item(item: SafeLifeItem) -> Tuple[bool, List[str]]:
    """Return (valid, notes) for item category."""
    if item.category not in VALID_CATEGORIES:
        return False, [
            f"Unknown category '{item.category}'; expected one of {VALID_CATEGORIES}"
        ]
    return True, []


def check_evidence(item: SafeLifeItem) -> Tuple[str, List[str]]:
    """
    Confirm at least one valid evidence type is on record.
    Returns (status, notes); status is N/A for fail-safe items.
    """
    if item.category != "safe-life":
        return "N/A", []

    valid = [e for e in item.evidence if e in VALID_EVIDENCE_TYPES]
    if not valid:
        return "FAIL", [
            f"Item '{item.item_id}': no valid evidence on record "
            f"(expected 'analysis' and/or 'test'); found {item.evidence!r}"
        ]
    return "PASS", [f"Item '{item.item_id}': evidence on record: {valid}"]


def check_crack_growth_life(item: SafeLifeItem) -> Tuple[str, List[str]]:
    """
    Compare crack-growth life against design_life * scatter_factor.
    Returns (status, notes); status is N/A for fail-safe items.
    """
    if item.category != "safe-life":
        return "N/A", []

    if item.crack_growth_life is None or item.design_life is None:
        return "MISSING_DATA", [
            f"Item '{item.item_id}': crack_growth_life or design_life not provided"
        ]

    if item.crack_growth_life <= 0 or item.design_life <= 0:
        return "FAIL", [
            f"Item '{item.item_id}': crack_growth_life and design_life must be positive; "
            f"got crack_growth_life={item.crack_growth_life}, design_life={item.design_life}"
        ]

    required = item.design_life * item.scatter_factor
    margin = item.crack_growth_life / required - 1.0

    if item.crack_growth_life >= required:
        return "PASS", [
            f"Item '{item.item_id}': crack-growth life {item.crack_growth_life} "
            f">= required {required} "
            f"(design_life {item.design_life} x scatter {item.scatter_factor}); "
            f"margin {margin:.4f}"
        ]
    return "FAIL", [
        f"Item '{item.item_id}': crack-growth life {item.crack_growth_life} "
        f"< required {required} "
        f"(design_life {item.design_life} x scatter {item.scatter_factor}); "
        f"shortfall {-margin:.4f}"
    ]


def check_residual_strength(item: SafeLifeItem) -> Tuple[str, List[str]]:
    """
    Confirm residual_strength / limit_load >= RESIDUAL_STRENGTH_RATIO_MINIMUM.
    Returns (status, notes); status is N/A for fail-safe items.
    """
    if item.category != "safe-life":
        return "N/A", []

    if item.residual_strength is None or item.limit_load is None:
        return "MISSING_DATA", [
            f"Item '{item.item_id}': residual_strength or limit_load not provided"
        ]

    if item.limit_load <= 0:
        return "FAIL", [
            f"Item '{item.item_id}': limit_load must be positive; got {item.limit_load}"
        ]

    ratio = item.residual_strength / item.limit_load
    margin = ratio - RESIDUAL_STRENGTH_RATIO_MINIMUM

    if ratio >= RESIDUAL_STRENGTH_RATIO_MINIMUM:
        return "PASS", [
            f"Item '{item.item_id}': residual-strength ratio {ratio:.4f} "
            f">= {RESIDUAL_STRENGTH_RATIO_MINIMUM}; margin {margin:.4f}"
        ]
    return "FAIL", [
        f"Item '{item.item_id}': residual-strength ratio {ratio:.4f} "
        f"< {RESIDUAL_STRENGTH_RATIO_MINIMUM}; deficit {-margin:.4f}"
    ]


def assess_item(item: SafeLifeItem) -> ItemResult:
    """Run all compliance checks on one item and return an ItemResult."""
    all_notes: List[str] = []

    category_valid, cat_notes = categorize_item(item)
    all_notes.extend(cat_notes)

    if not category_valid:
        return ItemResult(
            item_id=item.item_id,
            category=item.category,
            category_valid=False,
            crack_growth_check="N/A",
            residual_strength_check="N/A",
            evidence_check="N/A",
            compliant=False,
            notes=all_notes,
        )

    ev_status, ev_notes = check_evidence(item)
    cg_status, cg_notes = check_crack_growth_life(item)
    rs_status, rs_notes = check_residual_strength(item)

    all_notes.extend(ev_notes)
    all_notes.extend(cg_notes)
    all_notes.extend(rs_notes)

    if item.category == "safe-life":
        compliant = (
            ev_status == "PASS"
            and cg_status == "PASS"
            and rs_status == "PASS"
        )
    else:
        compliant = True  # fail-safe: category valid is sufficient for this leaf

    return ItemResult(
        item_id=item.item_id,
        category=item.category,
        category_valid=category_valid,
        crack_growth_check=cg_status,
        residual_strength_check=rs_status,
        evidence_check=ev_status,
        compliant=compliant,
        notes=all_notes,
    )


def assess_items(items: List[SafeLifeItem]) -> dict:
    """
    Assess a list of items and return a summary:
      results         — list of ItemResult
      total           — total item count
      compliant       — count of compliant items
      non_compliant   — count of non-compliant items
      all_compliant   — True only when every item is compliant
      findings        — list of item_ids that are non-compliant
    """
    results = [assess_item(i) for i in items]
    findings = [r.item_id for r in results if not r.compliant]
    compliant_count = len(results) - len(findings)

    return {
        "results": results,
        "total": len(results),
        "compliant": compliant_count,
        "non_compliant": len(findings),
        "all_compliant": len(findings) == 0,
        "findings": findings,
    }
