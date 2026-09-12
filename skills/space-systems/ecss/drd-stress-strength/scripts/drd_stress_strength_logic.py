"""
ECSS-E-ST-32C Annex K — Stress and Strength Analysis DRD logic.
Paraphrased procedures; ECSS-E-ST-32C + Annex K cited as anchor only.
stdlib only — no external dependencies.
"""

VALID_ELEMENT_TYPES = frozenset({
    "metallic",
    "composite",
    "bonded_joint",
    "welded_joint",
    "fastener",
})

VALID_LOAD_TYPES = frozenset({"limit", "yield", "ultimate"})

# Default factors of safety (paraphrased from ECSS-E-ST-32C Table 5 defaults).
# These are starting-point values; the program FoS document takes precedence.
DEFAULT_FOS = {
    "limit": 1.0,
    "yield": 1.0,
    "ultimate": 1.25,
}

REQUIRED_DRD_SECTIONS = (
    "scope",
    "applicable_documents",
    "load_cases",
    "material_allowables",
    "analysis_methods",
    "structural_element_list",
    "margins_of_safety",
    "conclusions",
)


def categorize_element(element_type: str) -> str:
    """
    Return element_type if it is a recognized construction type.
    Raises ValueError for any unrecognized type — uncategorized elements
    must not silently enter the margin calculation.
    """
    if element_type not in VALID_ELEMENT_TYPES:
        raise ValueError(
            f"Unrecognized element type '{element_type}'. "
            f"Accepted types: {sorted(VALID_ELEMENT_TYPES)}"
        )
    return element_type


def categorize_load_case(load_type: str) -> str:
    """
    Return load_type if it is a recognized load case category.
    Raises ValueError for any unrecognized type.
    """
    if load_type not in VALID_LOAD_TYPES:
        raise ValueError(
            f"Unrecognized load type '{load_type}'. "
            f"Accepted types: {sorted(VALID_LOAD_TYPES)}"
        )
    return load_type


def apply_factor_of_safety(limit_load: float, fos: float) -> float:
    """
    Compute design load = limit_load × fos.
    Both arguments must be strictly positive; a zero or negative limit load
    has no physical meaning in the context of a stress check.
    """
    if fos <= 0:
        raise ValueError(f"Factor of safety must be positive; got {fos}")
    if limit_load < 0:
        raise ValueError(f"Limit load must be non-negative; got {limit_load}")
    return limit_load * fos


def compute_margin_of_safety(allowable: float, design_load: float) -> float:
    """
    MoS = (allowable / design_load) − 1.
    Positive MoS → element has reserve. Negative MoS → finding.
    design_load must be strictly positive (a zero design load is a degenerate case
    that cannot produce a meaningful margin).
    """
    if design_load <= 0:
        raise ValueError(
            f"Design load must be strictly positive; got {design_load}"
        )
    if allowable <= 0:
        raise ValueError(
            f"Allowable must be strictly positive; got {allowable}"
        )
    return (allowable / design_load) - 1.0


def validate_allowable(
    allowable_stress: float, element_type: str, load_type: str
) -> float:
    """
    Validate that an allowable stress value is physically reasonable for the
    given element type and load case category.
    Returns the validated value or raises ValueError.
    """
    categorize_element(element_type)
    categorize_load_case(load_type)
    if allowable_stress <= 0:
        raise ValueError(
            f"Allowable stress must be positive for {element_type}/{load_type}; "
            f"got {allowable_stress}"
        )
    return allowable_stress


def check_negative_margins(margin_table: dict) -> list:
    """
    Given {element_id: MoS}, return the list of element IDs whose MoS < 0.
    Each entry in the returned list is a finding requiring resolution.
    """
    return [eid for eid, mos in margin_table.items() if mos < 0.0]


def check_drd_completeness(sections_present) -> list:
    """
    Return the list of required DRD section names absent from sections_present.
    An empty return list means the document satisfies the Annex K content check.
    """
    present = set(sections_present)
    return [s for s in REQUIRED_DRD_SECTIONS if s not in present]


def analyse_element(element_id: str, element_type: str, load_cases: list) -> dict:
    """
    Perform the stress/strength margin check for one structural element.

    load_cases — list of dicts, each with:
        load_type       : str   — "limit" | "yield" | "ultimate"
        applied_stress  : float — limit stress (MPa or consistent unit)
        allowable_stress: float — material allowable (same unit)
        fos             : float — factor of safety (optional; default from DEFAULT_FOS)

    Returns a result dict:
        element_id   : str
        element_type : str
        results      : list of per-load-case result dicts
        overall      : "pass" | "fail"
    """
    categorize_element(element_type)
    results = []
    for lc in load_cases:
        load_type = categorize_load_case(lc["load_type"])
        fos = lc.get("fos", DEFAULT_FOS[load_type])
        design_stress = apply_factor_of_safety(lc["applied_stress"], fos)
        mos = compute_margin_of_safety(lc["allowable_stress"], design_stress)
        results.append({
            "load_type": load_type,
            "design_stress": round(design_stress, 6),
            "allowable_stress": lc["allowable_stress"],
            "mos": round(mos, 6),
            "status": "pass" if mos >= 0.0 else "fail",
        })
    overall = "pass" if all(r["status"] == "pass" for r in results) else "fail"
    return {
        "element_id": element_id,
        "element_type": element_type,
        "results": results,
        "overall": overall,
    }


def build_margin_summary(analyses: list) -> tuple:
    """
    Aggregate a list of analyse_element outputs into a summary margin table.

    Returns:
        summary : dict {element_id: minimum MoS across all load cases}
        failing : list of element IDs whose overall status is "fail"
    """
    summary = {}
    failing = []
    for analysis in analyses:
        if not analysis["results"]:
            continue
        min_mos = min(r["mos"] for r in analysis["results"])
        summary[analysis["element_id"]] = min_mos
        if analysis["overall"] == "fail":
            failing.append(analysis["element_id"])
    return summary, failing
