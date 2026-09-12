"""
Damage-tolerance design principle selection for Potentially Fracture Critical Items (PFCIs).
Implements the ECSS-E-ST-32C clause 6.2.1 procedure (paraphrased — no verbatim ECSS text).

Three permitted principles:
  SAFE_LIFE         — single-path, non-inspectable; requires fracture life demonstration.
  FAIL_SAFE         — redundant load paths or inspectable in service.
  LOW_RISK_FRACTURE — both net stress and cross-section thickness below specified thresholds;
                      item is exempt from detailed fracture analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# Principle identifiers
SAFE_LIFE = "SAFE_LIFE"
FAIL_SAFE = "FAIL_SAFE"
LOW_RISK_FRACTURE = "LOW_RISK_FRACTURE"

VALID_PRINCIPLES = frozenset({SAFE_LIFE, FAIL_SAFE, LOW_RISK_FRACTURE})

# Low-risk fracture eligibility thresholds (ECSS-E-ST-32C cl.6.2.1, paraphrased).
# Both must be satisfied simultaneously for the low-risk designation.
LOW_RISK_STRESS_THRESHOLD_MPA = 55.0      # net section stress at limit load, MPa
LOW_RISK_THICKNESS_THRESHOLD_MM = 2.5    # governing cross-section thickness, mm


@dataclass
class PfciItem:
    """Descriptor for a single Potentially Fracture Critical Item."""
    item_id: str
    redundant_load_paths: bool
    inspectable_in_service: bool
    net_stress_mpa: float
    cross_section_thickness_mm: float
    material_fracture_toughness_kic: Optional[float] = None


@dataclass
class PrincipleSelection:
    """Result of applying the clause 6.2.1 selection procedure to one PFCI."""
    item_id: str
    principle: str
    rationale: str
    findings: List[str] = field(default_factory=list)


def _validate_item(item: PfciItem) -> None:
    """Raise ValueError for inputs that would make the selection undefined."""
    if not isinstance(item.item_id, str) or not item.item_id.strip():
        raise ValueError("item_id must be a non-empty string.")
    if item.net_stress_mpa < 0.0:
        raise ValueError(
            f"net_stress_mpa must be non-negative; got {item.net_stress_mpa}."
        )
    if item.cross_section_thickness_mm <= 0.0:
        raise ValueError(
            f"cross_section_thickness_mm must be positive; got "
            f"{item.cross_section_thickness_mm}."
        )
    if (
        item.material_fracture_toughness_kic is not None
        and item.material_fracture_toughness_kic <= 0.0
    ):
        raise ValueError(
            f"material_fracture_toughness_kic must be positive when provided; "
            f"got {item.material_fracture_toughness_kic}."
        )


def select_principle(item: PfciItem) -> PrincipleSelection:
    """
    Select the damage-tolerance design principle for a single PFCI.

    Selection order per ECSS-E-ST-32C cl.6.2.1 (paraphrased):
      1. Low-risk fracture — if BOTH stress and thickness are at or below thresholds.
      2. Fail-safe — if redundant load paths exist OR item is inspectable in service.
      3. Safe life — default for single-path, non-inspectable items.
    """
    _validate_item(item)

    findings: List[str] = []

    stress_ok = item.net_stress_mpa <= LOW_RISK_STRESS_THRESHOLD_MPA
    thickness_ok = item.cross_section_thickness_mm <= LOW_RISK_THICKNESS_THRESHOLD_MM

    # Step 1 — low-risk fracture eligibility
    if stress_ok and thickness_ok:
        return PrincipleSelection(
            item_id=item.item_id,
            principle=LOW_RISK_FRACTURE,
            rationale=(
                f"Net section stress {item.net_stress_mpa} MPa is at or below "
                f"{LOW_RISK_STRESS_THRESHOLD_MPA} MPa and cross-section thickness "
                f"{item.cross_section_thickness_mm} mm is at or below "
                f"{LOW_RISK_THICKNESS_THRESHOLD_MM} mm: item meets the low-risk "
                f"fracture criteria of ECSS-E-ST-32C cl.6.2.1."
            ),
            findings=findings,
        )

    # Record threshold exceedances as findings before continuing.
    if not stress_ok:
        findings.append(
            f"Net section stress {item.net_stress_mpa} MPa exceeds the low-risk "
            f"threshold {LOW_RISK_STRESS_THRESHOLD_MPA} MPa — low-risk fracture "
            f"designation not applicable."
        )
    if not thickness_ok:
        findings.append(
            f"Cross-section thickness {item.cross_section_thickness_mm} mm exceeds "
            f"the low-risk threshold {LOW_RISK_THICKNESS_THRESHOLD_MM} mm — low-risk "
            f"fracture designation not applicable."
        )

    # Step 2 — fail-safe
    if item.redundant_load_paths or item.inspectable_in_service:
        conditions = []
        if item.redundant_load_paths:
            conditions.append("redundant load paths present")
        if item.inspectable_in_service:
            conditions.append("item is inspectable in service")
        return PrincipleSelection(
            item_id=item.item_id,
            principle=FAIL_SAFE,
            rationale=(
                "Fail-safe applies: "
                + "; ".join(conditions)
                + " (ECSS-E-ST-32C cl.6.2.1). An inspection plan with defined "
                "intervals is required."
            ),
            findings=findings,
        )

    # Step 3 — safe life (default)
    return PrincipleSelection(
        item_id=item.item_id,
        principle=SAFE_LIFE,
        rationale=(
            "Safe life applies: single load path and not inspectable in service "
            "(ECSS-E-ST-32C cl.6.2.1). A fracture life demonstration by analysis "
            "and/or test is required."
        ),
        findings=findings,
    )


def evaluate_pfci_set(items: List[PfciItem]) -> dict:
    """
    Evaluate a list of PfciItem objects and return an aggregated summary.

    Returns:
      {
        "selections": list[PrincipleSelection],
        "counts": {SAFE_LIFE: int, FAIL_SAFE: int, LOW_RISK_FRACTURE: int},
        "items_with_findings": int,
      }
    """
    if not items:
        raise ValueError("Item list must not be empty.")

    selections = [select_principle(item) for item in items]

    counts = {SAFE_LIFE: 0, FAIL_SAFE: 0, LOW_RISK_FRACTURE: 0}
    items_with_findings = 0
    for sel in selections:
        counts[sel.principle] += 1
        if sel.findings:
            items_with_findings += 1

    return {
        "selections": selections,
        "counts": counts,
        "items_with_findings": items_with_findings,
    }
