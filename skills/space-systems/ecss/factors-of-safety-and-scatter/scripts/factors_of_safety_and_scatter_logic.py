"""
ECSS-E-ST-32C Rev.2 (2019) clauses 4.5.17–4.5.18: factor-of-safety application
and scatter-factor application for structural analysis.

Paraphrased from ECSS — no verbatim standard text reproduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# ── Material categories and their FOS values ─────────────────────────────────
#
# Ultimate and yield factors of safety per material category.
# Paraphrased from ECSS-E-ST-32C Rev.2 clause 4.5.17 (representative values;
# project tailoring may raise but must not lower these).
#
# Format: { category: (fos_ultimate, fos_yield) }

MATERIAL_CATEGORIES: dict[str, tuple[float, float]] = {
    "metallic_ductile": (1.25, 1.00),
    "metallic_brittle": (1.50, 1.10),
    "composite":        (1.40, 1.10),
    "bonded":           (1.50, 1.10),
}

# ── Scatter factors on fatigue life ──────────────────────────────────────────
#
# ECSS-E-ST-32C Rev.2 clause 4.5.18: divide the analysis fatigue life by the
# applicable scatter factor to obtain the allowable design life.
# Inspectable location: 2 | Uninspectable location: 4.

SCATTER_FACTOR_INSPECTABLE   = 2.0
SCATTER_FACTOR_UNINSPECTABLE = 4.0


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class FosResult:
    design_limit_load: float
    material_category: str
    fos_ultimate: float
    fos_yield: float
    design_ultimate_load: float
    design_yield_load: float
    errors: List[str] = field(default_factory=list)


@dataclass
class ScatterResult:
    analysis_life: float
    scatter_factor: float
    allowable_life: float
    errors: List[str] = field(default_factory=list)


@dataclass
class MosResult:
    allowable: float
    applied: float
    margin_of_safety: float
    passes: bool
    errors: List[str] = field(default_factory=list)


# ── Core functions ────────────────────────────────────────────────────────────

def apply_fos(design_limit_load: float, material_category: str) -> FosResult:
    """Apply ultimate and yield factors of safety to the design limit load.

    Returns a FosResult with derived design loads or populated errors on
    invalid input.
    """
    errors: List[str] = []

    if not isinstance(design_limit_load, (int, float)):
        errors.append("design_limit_load must be a numeric value")
        return FosResult(0.0, material_category, 0.0, 0.0, 0.0, 0.0, errors)
    if design_limit_load <= 0.0:
        errors.append(
            f"design_limit_load must be positive; got {design_limit_load}"
        )
        return FosResult(0.0, material_category, 0.0, 0.0, 0.0, 0.0, errors)
    if material_category not in MATERIAL_CATEGORIES:
        errors.append(
            f"unknown material_category '{material_category}'; "
            f"must be one of {sorted(MATERIAL_CATEGORIES)}"
        )
        return FosResult(0.0, material_category, 0.0, 0.0, 0.0, 0.0, errors)

    fos_ult, fos_yld = MATERIAL_CATEGORIES[material_category]
    dul = design_limit_load * fos_ult
    dyl = design_limit_load * fos_yld
    return FosResult(
        design_limit_load=design_limit_load,
        material_category=material_category,
        fos_ultimate=fos_ult,
        fos_yield=fos_yld,
        design_ultimate_load=dul,
        design_yield_load=dyl,
        errors=[],
    )


def apply_scatter_factor(analysis_life: float, inspectable: bool) -> ScatterResult:
    """Divide the analysis fatigue life by the scatter factor for the inspection regime.

    inspectable=True  → scatter factor 2 (accessible for in-service inspection)
    inspectable=False → scatter factor 4 (not accessible)
    """
    errors: List[str] = []

    if not isinstance(analysis_life, (int, float)):
        errors.append("analysis_life must be a numeric value")
        return ScatterResult(0.0, 0.0, 0.0, errors)
    if analysis_life <= 0.0:
        errors.append(
            f"analysis_life must be positive; got {analysis_life}"
        )
        return ScatterResult(0.0, 0.0, 0.0, errors)

    sf = SCATTER_FACTOR_INSPECTABLE if inspectable else SCATTER_FACTOR_UNINSPECTABLE
    allowable = analysis_life / sf
    return ScatterResult(
        analysis_life=analysis_life,
        scatter_factor=sf,
        allowable_life=allowable,
        errors=[],
    )


def compute_margin_of_safety(allowable: float, applied: float) -> MosResult:
    """Compute structural margin of safety: MS = allowable / applied − 1.

    MS ≥ 0 is a pass; MS < 0 is a structural finding.
    """
    errors: List[str] = []

    for name, val in (("allowable", allowable), ("applied", applied)):
        if not isinstance(val, (int, float)):
            errors.append(f"{name} must be a numeric value")
        elif val <= 0.0:
            errors.append(f"{name} must be positive; got {val}")

    if errors:
        return MosResult(0.0, 0.0, 0.0, False, errors)

    ms = allowable / applied - 1.0
    return MosResult(
        allowable=allowable,
        applied=applied,
        margin_of_safety=ms,
        passes=(ms >= 0.0),
        errors=[],
    )


def check_fatigue_compliance(
    analysis_life: float,
    mission_life: float,
    inspectable: bool,
) -> dict:
    """Check whether the allowable fatigue life covers the mission design life.

    Returns a dict with keys: allowable_life, mission_life, passes, deficit, errors.
    """
    errors: List[str] = []

    for name, val in (("analysis_life", analysis_life), ("mission_life", mission_life)):
        if not isinstance(val, (int, float)):
            errors.append(f"{name} must be a numeric value")
        elif val <= 0.0:
            errors.append(f"{name} must be positive; got {val}")

    if errors:
        return {"allowable_life": 0.0, "mission_life": 0.0, "passes": False,
                "deficit": 0.0, "errors": errors}

    scatter_result = apply_scatter_factor(analysis_life, inspectable)
    allowable = scatter_result.allowable_life
    passes = allowable >= mission_life
    deficit = max(0.0, mission_life - allowable)
    return {
        "allowable_life": allowable,
        "mission_life": mission_life,
        "passes": passes,
        "deficit": deficit,
        "errors": [],
    }
