"""
NDT/NDI structural verification logic — ECSS-E-ST-32C clause 4.6.3.13.
Procedure paraphrased; no verbatim ECSS text.
"""

VALID_MATERIAL_FAMILIES = {"metallic", "composite", "bond", "weld"}
VALID_DEFECT_FAMILIES = {"surface", "subsurface", "volumetric", "delamination"}
VALID_CRITICALITY_LEVELS = {"primary", "secondary", "tertiary"}

# Fraction of inspectable area that must be examined, indexed by criticality.
COVERAGE_MINIMUMS = {
    "primary":   1.00,
    "secondary": 0.50,
    "tertiary":  0.20,
}

# Human-readable labels for the supported NDT method codes.
NDT_METHODS = {
    "PT":  "Penetrant Testing",
    "MT":  "Magnetic Particle Testing",
    "UT":  "Ultrasonic Testing",
    "RT":  "Radiographic Testing",
    "ET":  "Eddy Current Testing",
    "VT":  "Visual Testing",
}

# (material_family, defect_family) -> sorted list of applicable method codes.
# MT excluded from composites (non-ferromagnetic); ET limited to conductive materials.
_METHOD_MATRIX = {
    ("metallic",   "surface"):      ["ET", "MT", "PT", "VT"],
    ("metallic",   "subsurface"):   ["ET", "RT", "UT"],
    ("metallic",   "volumetric"):   ["RT", "UT"],
    ("metallic",   "delamination"): ["UT"],
    ("composite",  "surface"):      ["ET", "PT", "VT"],
    ("composite",  "subsurface"):   ["RT", "UT"],
    ("composite",  "volumetric"):   ["RT", "UT"],
    ("composite",  "delamination"): ["RT", "UT"],
    ("bond",       "surface"):      ["PT", "VT"],
    ("bond",       "subsurface"):   ["UT"],
    ("bond",       "delamination"): ["UT"],
    ("weld",       "surface"):      ["MT", "PT", "VT"],
    ("weld",       "subsurface"):   ["RT", "UT"],
    ("weld",       "volumetric"):   ["RT", "UT"],
}


def get_applicable_methods(material_family, defect_family):
    """
    Return the list of applicable NDT method codes for a material/defect pair.

    Raises ValueError for unrecognized inputs or undefined matrix entries.
    """
    if material_family not in VALID_MATERIAL_FAMILIES:
        raise ValueError(
            f"Unrecognized material family '{material_family}'. "
            f"Expected one of: {sorted(VALID_MATERIAL_FAMILIES)}"
        )
    if defect_family not in VALID_DEFECT_FAMILIES:
        raise ValueError(
            f"Unrecognized defect family '{defect_family}'. "
            f"Expected one of: {sorted(VALID_DEFECT_FAMILIES)}"
        )
    key = (material_family, defect_family)
    if key not in _METHOD_MATRIX:
        raise ValueError(
            f"No NDT method mapping defined for "
            f"({material_family}, {defect_family})."
        )
    return list(_METHOD_MATRIX[key])


def check_coverage(criticality, inspected_fraction):
    """
    Verify that *inspected_fraction* meets the minimum for *criticality*.

    Returns a dict:
        criticality, required (float), actual (float),
        adequate (bool), shortfall (float).

    Raises ValueError for invalid inputs.
    """
    if criticality not in VALID_CRITICALITY_LEVELS:
        raise ValueError(
            f"Unrecognized criticality level '{criticality}'. "
            f"Expected one of: {sorted(VALID_CRITICALITY_LEVELS)}"
        )
    if not (0.0 <= inspected_fraction <= 1.0):
        raise ValueError(
            f"inspected_fraction must be in [0.0, 1.0], "
            f"got {inspected_fraction}."
        )
    required = COVERAGE_MINIMUMS[criticality]
    adequate = inspected_fraction >= required
    shortfall = max(0.0, required - inspected_fraction)
    return {
        "criticality": criticality,
        "required": required,
        "actual": inspected_fraction,
        "adequate": adequate,
        "shortfall": round(shortfall, 9),
    }


def evaluate_indication(indication_size, acceptance_limit):
    """
    Evaluate a single NDT indication against an acceptance limit.

    Severity scale:
        acceptable  — indication_size < acceptance_limit  (passes)
        marginal    — indication_size == acceptance_limit (does not pass)
        rejectable  — indication_size > acceptance_limit  (does not pass)

    Returns a dict:
        indication_size, acceptance_limit, severity (str), passes (bool).

    Raises ValueError for non-physical inputs.
    """
    if indication_size < 0:
        raise ValueError(
            f"indication_size must be >= 0, got {indication_size}."
        )
    if acceptance_limit <= 0:
        raise ValueError(
            f"acceptance_limit must be > 0, got {acceptance_limit}."
        )
    if indication_size < acceptance_limit:
        severity = "acceptable"
    elif indication_size == acceptance_limit:
        severity = "marginal"
    else:
        severity = "rejectable"
    return {
        "indication_size": indication_size,
        "acceptance_limit": acceptance_limit,
        "severity": severity,
        "passes": severity == "acceptable",
    }


def assess_component(component):
    """
    Full NDT assessment for a single structural component.

    Expected keys in *component*:
        element_id         : str
        material_family    : str  (metallic | composite | bond | weld)
        defect_families    : list[str]
        criticality        : str  (primary | secondary | tertiary)
        inspected_fraction : float
        ndt_method         : str  (code to validate against applicable methods)
        indications        : list[dict] each with indication_size, acceptance_limit

    Returns a dict:
        element_id, applicable_methods (list), method_applicable (bool),
        coverage (dict), indications_summary (list), passes (bool),
        findings (list[str]).
    """
    element_id = component.get("element_id", "unknown")
    findings = []

    # Step 1 — collect applicable methods across all targeted defect families.
    material_family = component.get("material_family", "")
    defect_families = component.get("defect_families") or []
    ndt_method = component.get("ndt_method", "")

    applicable_set = set()
    for df in defect_families:
        try:
            applicable_set.update(get_applicable_methods(material_family, df))
        except ValueError as exc:
            findings.append(str(exc))

    # Step 2 — confirm the applied method is in the applicable set.
    method_applicable = bool(applicable_set) and (ndt_method in applicable_set)
    if ndt_method and not method_applicable:
        findings.append(
            f"Method '{ndt_method}' is not applicable for material "
            f"'{material_family}' with defect families {defect_families}."
        )

    # Step 3 — coverage adequacy.
    criticality = component.get("criticality", "")
    inspected_fraction = component.get("inspected_fraction", 0.0)
    try:
        coverage = check_coverage(criticality, inspected_fraction)
        if not coverage["adequate"]:
            pct_short = coverage["shortfall"] * 100
            pct_req = coverage["required"] * 100
            findings.append(
                f"Coverage shortfall: {pct_short:.1f}% below the "
                f"{pct_req:.0f}% minimum for {criticality} structure."
            )
    except ValueError as exc:
        coverage = {}
        findings.append(str(exc))

    # Step 4 — indication evaluation.
    indications_summary = []
    for ind in component.get("indications") or []:
        try:
            result = evaluate_indication(
                ind["indication_size"], ind["acceptance_limit"]
            )
            indications_summary.append(result)
            if not result["passes"]:
                findings.append(
                    f"Indication {result['indication_size']} mm is "
                    f"{result['severity']} (limit {result['acceptance_limit']} mm)."
                )
        except (KeyError, ValueError) as exc:
            findings.append(f"Indication evaluation error: {exc}")

    return {
        "element_id": element_id,
        "applicable_methods": sorted(applicable_set),
        "method_applicable": method_applicable,
        "coverage": coverage,
        "indications_summary": indications_summary,
        "passes": len(findings) == 0,
        "findings": findings,
    }
