"""
Fracture-critical item (FCI) determination logic.
Reference: ECSS-E-ST-32-01C §6.2.2 (paraphrased procedure, not verbatim text).
"""

VALID_ITEM_TYPES = frozenset({
    "pressure_vessel",
    "pressurized_line",
    "pressurized_fitting",
    "composite_primary",
    "composite_secondary",
    "metallic_primary",
    "metallic_secondary",
    "weld",
    "fastener",
    "other",
})

VALID_CONSEQUENCE_LEVELS = frozenset({
    "catastrophic",
    "critical",
    "non_critical",
})

_PRESSURIZED_TYPES = frozenset({
    "pressure_vessel",
    "pressurized_line",
    "pressurized_fitting",
})

_CRITICAL_OR_ABOVE = frozenset({"catastrophic", "critical"})


class FCIInputError(ValueError):
    """Raised when required item fields are missing or invalid."""


def _validate_item(item: dict) -> None:
    for field in ("name", "item_type", "failure_consequence"):
        if field not in item:
            raise FCIInputError(f"Missing required field: {field!r}")
    if item["item_type"] not in VALID_ITEM_TYPES:
        raise FCIInputError(
            f"Unknown item_type {item['item_type']!r}. "
            f"Must be one of {sorted(VALID_ITEM_TYPES)}"
        )
    if item["failure_consequence"] not in VALID_CONSEQUENCE_LEVELS:
        raise FCIInputError(
            f"Unknown failure_consequence {item['failure_consequence']!r}. "
            f"Must be one of {sorted(VALID_CONSEQUENCE_LEVELS)}"
        )


def determine_fci_status(item: dict) -> dict:
    """
    Determine whether a structural item is an FCI per ECSS-E-ST-32-01C §6.2.2.

    Parameters
    ----------
    item : dict
        Required keys:
          name                (str)  — item identifier
          item_type           (str)  — one of VALID_ITEM_TYPES
          failure_consequence (str)  — "catastrophic" | "critical" | "non_critical"
        Optional keys:
          ndt_accessible          (bool) — conventional NDT can reliably bound
                                           flaw size; default True
          life_limited_by_fracture (bool) — design life is controlled by crack
                                            growth; default False

    Returns
    -------
    dict with keys:
      name           — echoed from input
      fci_status     — "FCI" or "NON_FCI"
      fci_categories — list of applicable category strings
      rationale      — list of explanation strings (one per evaluated criterion)
    """
    _validate_item(item)

    consequence = item["failure_consequence"]
    ndt_accessible = item.get("ndt_accessible", True)
    life_limited_by_fracture = item.get("life_limited_by_fracture", False)

    categories = []
    rationale = []

    # Criterion 1 — Pressurized system
    if item["item_type"] in _PRESSURIZED_TYPES:
        if consequence in _CRITICAL_OR_ABOVE:
            categories.append("PRESSURE_VESSEL_OR_LINE")
            rationale.append(
                f"Pressurized component ({item['item_type']}) with "
                f"{consequence} failure consequence: PRESSURE_VESSEL_OR_LINE criterion met."
            )
        else:
            rationale.append(
                f"Pressurized component ({item['item_type']}) but failure "
                "consequence is non_critical: PRESSURE_VESSEL_OR_LINE criterion not triggered."
            )

    # Criterion 2 — Fracture-limited life item (FLLI)
    if life_limited_by_fracture:
        if consequence in _CRITICAL_OR_ABOVE:
            categories.append("FLLI")
            rationale.append(
                f"Life controlled by crack growth (FLLI) with {consequence} "
                "failure consequence: FLLI criterion met."
            )
        else:
            rationale.append(
                "Life controlled by crack growth (FLLI) but failure consequence "
                "is non_critical: FLLI criterion not triggered."
            )

    # Criterion 3 — NDT-limited item
    if not ndt_accessible:
        if consequence in _CRITICAL_OR_ABOVE:
            categories.append("NDT_LIMITED")
            rationale.append(
                f"Item not accessible to conventional NDT with {consequence} "
                "failure consequence: NDT_LIMITED criterion met."
            )
        else:
            rationale.append(
                "Item not accessible to conventional NDT but failure consequence "
                "is non_critical: NDT_LIMITED criterion not triggered."
            )

    # Criterion 4 — Composite primary structure
    if item["item_type"] == "composite_primary":
        if consequence in _CRITICAL_OR_ABOVE:
            categories.append("COMPOSITE_PRIMARY")
            rationale.append(
                f"Composite primary structure with {consequence} failure "
                "consequence: COMPOSITE_PRIMARY criterion met."
            )
        else:
            rationale.append(
                "Composite primary structure but failure consequence is "
                "non_critical: COMPOSITE_PRIMARY criterion not triggered."
            )

    if not categories:
        rationale.append(
            "No FCI criterion met under ECSS-E-ST-32-01C §6.2.2; "
            "item is not fracture-critical."
        )

    return {
        "name": item["name"],
        "fci_status": "FCI" if categories else "NON_FCI",
        "fci_categories": categories,
        "rationale": rationale,
    }


def batch_determine_fci(items: list) -> list:
    """Apply determine_fci_status to each item dict in a list."""
    if not isinstance(items, list):
        raise FCIInputError("Input must be a list of item dicts.")
    return [determine_fci_status(item) for item in items]


def summary_counts(results: list) -> dict:
    """Return FCI/NON_FCI counts from a batch result list."""
    fci = sum(1 for r in results if r.get("fci_status") == "FCI")
    non_fci = sum(1 for r in results if r.get("fci_status") == "NON_FCI")
    return {"FCI": fci, "NON_FCI": non_fci, "total": len(results)}
