"""
FOS tables application logic — ECSS-E-ST-32C clause 4.2.5.

Paraphrased procedure; no verbatim ECSS text.  All numeric values are
public minimums from the standard's tabulated FOS requirements.

Mission categories
------------------
- "unmanned"          spacecraft with no crew on board
- "human_spaceflight" human-rated missions (crew on board or shared manifest)

Factor types
------------
- "yield"    — prevents permanent deformation (jY)
- "ultimate" — prevents fracture / collapse (jU)
- "proof"    — pressure-vessel retention verification (jP)
"""

from __future__ import annotations

MISSION_CATEGORIES: frozenset[str] = frozenset({"unmanned", "human_spaceflight"})
FACTOR_TYPES: frozenset[str] = frozenset({"yield", "ultimate", "proof"})

# Tabulated minimum FOS per ECSS-E-ST-32C clause 4.2.5 (paraphrased).
# Key: (mission_category, factor_type)  →  minimum factor of safety
_FOS_TABLE: dict[tuple[str, str], float] = {
    ("unmanned",          "yield"):    1.10,
    ("unmanned",          "ultimate"): 1.25,
    ("unmanned",          "proof"):    1.10,
    ("human_spaceflight", "yield"):    1.25,
    ("human_spaceflight", "ultimate"): 1.40,
    ("human_spaceflight", "proof"):    1.50,
}

_HUMAN_KEYWORDS: frozenset[str] = frozenset({
    "human", "crew", "crewed", "astronaut", "cosmonaut",
    "human-rated", "human rated", "manned",
})


def lookup_fos(mission_category: str, factor_type: str) -> float:
    """Return the minimum FOS for the given mission category and factor type.

    Raises ValueError for unrecognized inputs.
    """
    mc = mission_category.lower().strip()
    ft = factor_type.lower().strip()

    if mc not in MISSION_CATEGORIES:
        raise ValueError(
            f"Unknown mission category {mission_category!r}. "
            f"Must be one of: {sorted(MISSION_CATEGORIES)}"
        )
    if ft not in FACTOR_TYPES:
        raise ValueError(
            f"Unknown factor type {factor_type!r}. "
            f"Must be one of: {sorted(FACTOR_TYPES)}"
        )

    return _FOS_TABLE[(mc, ft)]


def apply_fos(
    mission_category: str,
    factor_type: str,
    limit_load: float,
) -> dict:
    """Multiply *limit_load* by the applicable FOS to obtain the design load.

    Returns a result dict with all intermediate values.

    Raises ValueError if *limit_load* ≤ 0 or inputs are unrecognized.
    """
    if limit_load <= 0.0:
        raise ValueError(
            f"limit_load must be positive; got {limit_load!r}"
        )

    fos = lookup_fos(mission_category, factor_type)
    design_load = round(limit_load * fos, 10)

    return {
        "mission_category": mission_category.lower().strip(),
        "factor_type": factor_type.lower().strip(),
        "fos": fos,
        "limit_load": limit_load,
        "design_load": design_load,
    }


def compute_margin(
    mission_category: str,
    factor_type: str,
    limit_load: float,
    allowable: float,
) -> dict:
    """Compute margin of safety: MS = (allowable / (FOS × limit_load)) − 1.

    A non-negative MS means the component meets the requirement.

    Raises ValueError for non-positive loads or unrecognized inputs.
    """
    if limit_load <= 0.0:
        raise ValueError(
            f"limit_load must be positive; got {limit_load!r}"
        )
    if allowable <= 0.0:
        raise ValueError(
            f"allowable must be positive; got {allowable!r}"
        )

    fos = lookup_fos(mission_category, factor_type)
    design_load = limit_load * fos
    ms = (allowable / design_load) - 1.0

    return {
        "mission_category": mission_category.lower().strip(),
        "factor_type": factor_type.lower().strip(),
        "fos": fos,
        "limit_load": limit_load,
        "design_load": round(design_load, 10),
        "allowable": allowable,
        "margin_of_safety": round(ms, 10),
        "pass": ms >= 0.0,
    }


def infer_mission_category(description: str) -> str:
    """Infer mission category from a free-text description.

    Returns "human_spaceflight" if any human keyword is found,
    otherwise "unmanned".
    """
    lower = description.lower()
    for kw in _HUMAN_KEYWORDS:
        if kw in lower:
            return "human_spaceflight"
    return "unmanned"


def summarise_load_cases(cases: list[dict]) -> dict:
    """Evaluate a list of load-case dicts and return an aggregate summary.

    Each dict in *cases* must have keys:
      mission_category, factor_type, limit_load, allowable

    Returns:
      {
        "results": [<compute_margin result>, ...],
        "governing_margin": <minimum MS>,
        "all_pass": <bool>,
        "failing_cases": [<indices of failing cases>],
      }

    Raises ValueError if *cases* is empty or any case dict is malformed.
    """
    if not cases:
        raise ValueError("cases must be a non-empty list")

    results = []
    for i, case in enumerate(cases):
        for key in ("mission_category", "factor_type", "limit_load", "allowable"):
            if key not in case:
                raise ValueError(f"Case {i} is missing required key {key!r}")
        results.append(
            compute_margin(
                case["mission_category"],
                case["factor_type"],
                case["limit_load"],
                case["allowable"],
            )
        )

    margins = [r["margin_of_safety"] for r in results]
    governing = min(margins)
    failing = [i for i, r in enumerate(results) if not r["pass"]]

    return {
        "results": results,
        "governing_margin": governing,
        "all_pass": len(failing) == 0,
        "failing_cases": failing,
    }
