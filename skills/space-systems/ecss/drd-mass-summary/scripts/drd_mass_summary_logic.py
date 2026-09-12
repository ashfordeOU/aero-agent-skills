"""
ECSS-E-ST-32C Annex N — Structure Mass Summary (SMS) Document logic.
Paraphrased procedure; ECSS-E-ST-32C cited as anchor only (not reproduced).
stdlib only — no external dependencies.
"""

from typing import Dict, List, Optional

# Design maturity codes recognized per ECSS-E-ST-32C Annex N and the
# minimum margin fraction required at each level.
MATURITY_CODE_MIN_MARGINS: Dict[str, float] = {
    "A": 0.02,   # actual measured or weighed mass
    "B": 0.05,   # mass from detailed design drawing
    "C": 0.10,   # mass from preliminary design
    "D": 0.15,   # mass estimated from analysis
    "E": 0.20,   # mass estimated from similarity or analogy
}

RECOGNIZED_MATURITY_CODES = frozenset(MATURITY_CODE_MIN_MARGINS.keys())


def categorize_maturity_code(code: str) -> str:
    """
    Return the normalized design maturity code for a given input string.
    Raises ValueError if the code is not in the recognized set.
    """
    if not isinstance(code, str):
        raise ValueError(
            f"Maturity code must be a string, got {type(code).__name__!r}."
        )
    normalized = code.strip().upper()
    if normalized not in RECOGNIZED_MATURITY_CODES:
        raise ValueError(
            f"Maturity code {code!r} is not recognized. "
            f"Accepted codes: {sorted(RECOGNIZED_MATURITY_CODES)}."
        )
    return normalized


def compute_mass_with_margin(dry_mass: float, margin_fraction: float) -> float:
    """
    Compute the component mass-with-margin.
    mass_with_margin = dry_mass × (1 + margin_fraction).
    Raises ValueError for a negative dry mass or a negative margin fraction.
    """
    if dry_mass < 0:
        raise ValueError(
            f"Dry mass must be non-negative, got {dry_mass}."
        )
    if margin_fraction < 0:
        raise ValueError(
            f"Margin fraction must be non-negative, got {margin_fraction}."
        )
    return dry_mass * (1.0 + margin_fraction)


def process_component(component: dict) -> dict:
    """
    Process a single SMS component entry and return computed values with findings.

    Required keys:
        id             (str)   — unique component identifier
        maturity_code  (str)   — design maturity code (A–E)
        dry_mass       (float) — dry mass in kg (must be > 0)

    Optional keys:
        margin_fraction (float) — override margin; must be >= minimum for the
                                  assigned maturity code. When omitted, the
                                  minimum margin for the code is used.

    Returns:
        {
            "id":               str,
            "maturity_code":    str | None,
            "dry_mass":         float | None,
            "margin_fraction":  float | None,
            "mass_with_margin": float | None,
            "findings":         list[str],
        }
    """
    findings: List[str] = []
    result: Dict = {
        "id": component.get("id", ""),
        "maturity_code": None,
        "dry_mass": None,
        "margin_fraction": None,
        "mass_with_margin": None,
        "findings": findings,
    }

    comp_id = component.get("id", "")
    if not comp_id:
        findings.append("Component is missing an 'id' field.")

    # Validate maturity code
    raw_code = component.get("maturity_code", "")
    code: Optional[str] = None
    try:
        code = categorize_maturity_code(raw_code)
        result["maturity_code"] = code
    except (ValueError, AttributeError) as exc:
        findings.append(str(exc))

    # Validate dry mass
    dry_mass = component.get("dry_mass")
    if dry_mass is None:
        findings.append(
            f"Component {comp_id!r}: 'dry_mass' is missing — "
            "component cannot be assessed without a dry mass value."
        )
        return result

    try:
        dry_mass = float(dry_mass)
    except (TypeError, ValueError):
        findings.append(
            f"Component {comp_id!r}: 'dry_mass' must be a numeric value."
        )
        return result

    if dry_mass <= 0:
        findings.append(
            f"Component {comp_id!r}: 'dry_mass' must be positive, got {dry_mass}."
        )
        return result

    result["dry_mass"] = dry_mass

    # Resolve and validate margin fraction
    if code is not None:
        min_margin = MATURITY_CODE_MIN_MARGINS[code]
        raw_margin = component.get("margin_fraction")

        if raw_margin is None:
            margin_fraction = min_margin
        else:
            try:
                margin_fraction = float(raw_margin)
            except (TypeError, ValueError):
                findings.append(
                    f"Component {comp_id!r}: 'margin_fraction' must be a numeric value."
                )
                return result
            if margin_fraction < min_margin:
                findings.append(
                    f"Component {comp_id!r}: margin_fraction {margin_fraction} is below "
                    f"the minimum {min_margin} for maturity code {code!r}."
                )
                return result

        result["margin_fraction"] = margin_fraction

        try:
            result["mass_with_margin"] = compute_mass_with_margin(dry_mass, margin_fraction)
        except ValueError as exc:
            findings.append(str(exc))

    return result


def process_mass_summary_document(components: list,
                                  mass_budget: Optional[float] = None) -> dict:
    """
    Process a full SMS component list.

    Args:
        components:  list of component dicts (see process_component).
        mass_budget: allocated total mass-with-margin budget in kg, or None
                     when the budget has not yet been set.

    Returns:
        {
            "component_results":      list[dict],
            "total_dry_mass":         float,
            "total_mass_with_margin": float,
            "mass_budget":            float | None,
            "budget_exceedance":      float | None,  positive = over budget
            "findings":               list[str],
            "compliant":              bool,
        }
    """
    if not components:
        return {
            "component_results": [],
            "total_dry_mass": 0.0,
            "total_mass_with_margin": 0.0,
            "mass_budget": mass_budget,
            "budget_exceedance": None,
            "findings": [
                "Mass summary document contains no components; "
                "at least one component is required."
            ],
            "compliant": False,
        }

    results = [process_component(c) for c in components]

    all_findings: List[str] = []
    for r in results:
        all_findings.extend(r["findings"])

    # Check for duplicate component IDs
    seen_ids: set = set()
    for r in results:
        cid = r["id"]
        if cid:
            if cid in seen_ids:
                all_findings.append(
                    f"Duplicate component ID {cid!r}: each component must have "
                    "a unique identifier in the SMS document."
                )
            seen_ids.add(cid)

    # Compute totals from entries that produced valid values
    total_dry_mass = sum(
        r["dry_mass"] for r in results if r["dry_mass"] is not None
    )
    total_mass_with_margin = sum(
        r["mass_with_margin"] for r in results if r["mass_with_margin"] is not None
    )

    budget_exceedance: Optional[float] = None
    if mass_budget is None:
        all_findings.append(
            "No allocated mass budget has been set; the mass requirement has "
            "not been captured and the budget check cannot be performed."
        )
    else:
        if mass_budget <= 0:
            all_findings.append(
                f"Allocated mass budget must be positive, got {mass_budget}."
            )
        else:
            exceedance = total_mass_with_margin - mass_budget
            budget_exceedance = exceedance
            if exceedance > 0:
                all_findings.append(
                    f"Total mass-with-margin {total_mass_with_margin:.4f} kg exceeds "
                    f"the allocated budget {mass_budget:.4f} kg by {exceedance:.4f} kg."
                )

    return {
        "component_results": results,
        "total_dry_mass": total_dry_mass,
        "total_mass_with_margin": total_mass_with_margin,
        "mass_budget": mass_budget,
        "budget_exceedance": budget_exceedance,
        "findings": all_findings,
        "compliant": len(all_findings) == 0,
    }
