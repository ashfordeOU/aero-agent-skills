"""
Margin of Safety (MOS) computation for structural elements.
Aligned with ECSS-E-ST-32C clause 4.5.16 — MOS computation rules.
Stdlib only — no external dependencies.
"""

from __future__ import annotations

FAILURE_MODES = ("yield", "ultimate", "buckling", "fatigue")


def compute_mos(allowable: float, applied_load: float) -> float:
    """
    MOS = (allowable / applied_load) - 1.

    Raises ValueError for non-positive inputs; those represent
    invalid structural data and must not silently yield a number.
    """
    if applied_load <= 0.0:
        raise ValueError(
            f"Applied load must be positive; received {applied_load}."
        )
    if allowable <= 0.0:
        raise ValueError(
            f"Allowable must be positive; received {allowable}."
        )
    return (allowable / applied_load) - 1.0


def is_adequate(mos: float) -> bool:
    """True when MOS >= 0 (applied load does not exceed allowable)."""
    return mos >= 0.0


def assess_failure_mode(
    mode: str,
    applied_load: float,
    allowable: float,
) -> dict:
    """
    Assess a single failure mode at a single load level.

    Returns a result dict with keys:
        mode, applied_load, allowable, mos, adequate.

    Raises ValueError for an unrecognized mode or invalid numeric inputs.
    """
    if mode not in FAILURE_MODES:
        raise ValueError(
            f"Unrecognized failure mode '{mode}'. "
            f"Expected one of {FAILURE_MODES}."
        )
    mos = compute_mos(allowable, applied_load)
    return {
        "mode": mode,
        "applied_load": applied_load,
        "allowable": allowable,
        "mos": mos,
        "adequate": is_adequate(mos),
    }


def govern_assessments(assessments: list) -> dict:
    """
    Return the assessment with the minimum MOS (governing case).
    Raises ValueError for an empty list.
    """
    if not assessments:
        raise ValueError(
            "Cannot determine governing assessment from an empty list."
        )
    return min(assessments, key=lambda a: a["mos"])


def assess_element(element_id: str, mode_assessments: list) -> dict:
    """
    Aggregate failure-mode assessments for a structural element.

    Returns a summary dict with keys:
        element_id, mode_assessments, all_adequate,
        governing_mode, governing_mos, failed_modes.

    Raises ValueError for a blank element_id or empty assessment list.
    """
    if not element_id:
        raise ValueError("element_id must be a non-empty string.")
    if not mode_assessments:
        raise ValueError("mode_assessments list must not be empty.")
    all_adequate = all(a["adequate"] for a in mode_assessments)
    governing = govern_assessments(mode_assessments)
    failed = [a["mode"] for a in mode_assessments if not a["adequate"]]
    return {
        "element_id": element_id,
        "mode_assessments": mode_assessments,
        "all_adequate": all_adequate,
        "governing_mode": governing["mode"],
        "governing_mos": governing["mos"],
        "failed_modes": failed,
    }


def compute_design_loads(
    limit_load: float,
    yield_factor: float,
    ultimate_factor: float,
) -> dict:
    """
    Derive Design Yield Load and Design Ultimate Load from a Limit Load.

    Returns a dict with keys:
        limit_load, design_yield_load, design_ultimate_load.

    Raises ValueError for non-positive inputs.
    """
    if limit_load <= 0.0:
        raise ValueError(
            f"Limit load must be positive; received {limit_load}."
        )
    if yield_factor <= 0.0:
        raise ValueError(
            f"Yield safety factor must be positive; received {yield_factor}."
        )
    if ultimate_factor <= 0.0:
        raise ValueError(
            f"Ultimate safety factor must be positive; received {ultimate_factor}."
        )
    return {
        "limit_load": limit_load,
        "design_yield_load": limit_load * yield_factor,
        "design_ultimate_load": limit_load * ultimate_factor,
    }


def full_assessment(
    element_id: str,
    limit_load: float,
    yield_factor: float,
    ultimate_factor: float,
    yield_allowable: float,
    ultimate_allowable: float,
    buckling_applied: float = None,
    buckling_allowable: float = None,
) -> dict:
    """
    Full multi-load-level, multi-failure-mode MOS assessment.

    Always assesses yield at DYL and ultimate at DUL.
    Adds a buckling assessment when both buckling_applied and
    buckling_allowable are supplied.

    Returns the element assessment dict from assess_element().
    """
    design = compute_design_loads(limit_load, yield_factor, ultimate_factor)
    assessments = [
        assess_failure_mode(
            "yield", design["design_yield_load"], yield_allowable
        ),
        assess_failure_mode(
            "ultimate", design["design_ultimate_load"], ultimate_allowable
        ),
    ]
    if buckling_applied is not None and buckling_allowable is not None:
        assessments.append(
            assess_failure_mode("buckling", buckling_applied, buckling_allowable)
        )
    return assess_element(element_id, assessments)
