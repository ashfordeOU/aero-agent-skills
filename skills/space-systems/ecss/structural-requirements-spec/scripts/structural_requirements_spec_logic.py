"""
Structural requirements specification logic for spacecraft and launch vehicle structures.
Procedures per ECSS-E-ST-32C clause 4: requirement baseline capture, design load
derivation, margin-of-safety computation, and requirement-set validation.
"""

FUNCTIONAL_REQ_TYPES = frozenset({
    "stiffness",
    "strength",
    "stability",
    "fracture_control",
    "fatigue",
    "static_stiffness",
    "dynamic_stiffness",
    "buckling",
    "thermal_dimensional_stability",
})

PERFORMANCE_REQ_TYPES = frozenset({
    "margin_of_safety",
    "load_case",
    "mass_budget",
    "frequency",
    "deflection_limit",
    "design_load",
    "factor_of_safety",
    "deformation_allowable",
})

VALID_VERIFICATION_METHODS = frozenset({
    "analysis",
    "test",
    "inspection",
    "similarity",
    "review",
})


def categorize_requirement(req_type: str) -> str:
    """
    Categorize a structural requirement as 'functional' or 'performance'.
    Normalizes the input to lowercase with underscores before matching.
    Raises ValueError for unrecognized types.
    """
    key = req_type.strip().lower().replace(" ", "_").replace("-", "_")
    if key in FUNCTIONAL_REQ_TYPES:
        return "functional"
    if key in PERFORMANCE_REQ_TYPES:
        return "performance"
    recognized = sorted(FUNCTIONAL_REQ_TYPES | PERFORMANCE_REQ_TYPES)
    raise ValueError(
        f"Unrecognized requirement type: '{req_type}'. Must be one of {recognized}"
    )


def compute_design_limit_load(
    nominal_load: float,
    dynamic_factor: float = 1.0,
    quasi_static_factor: float = 1.0,
) -> float:
    """
    Compute the Design Limit Load (DLL) from a nominal mechanical environment load.

    DLL = nominal_load * dynamic_factor * quasi_static_factor

    Both amplification factors must be >= 1.0; they increase the environment load,
    never reduce it.  A negative nominal load is rejected because loads are expressed
    as non-negative magnitudes at this stage.
    """
    if nominal_load < 0:
        raise ValueError(f"nominal_load {nominal_load} must be >= 0")
    if dynamic_factor < 1.0:
        raise ValueError(
            f"dynamic_factor {dynamic_factor} must be >= 1.0 (load amplifier)"
        )
    if quasi_static_factor < 1.0:
        raise ValueError(
            f"quasi_static_factor {quasi_static_factor} must be >= 1.0 (load amplifier)"
        )
    return nominal_load * dynamic_factor * quasi_static_factor


def compute_design_loads(dll: float, yield_fs: float, ultimate_fs: float) -> dict:
    """
    Derive Design Yield Load (DYL) and Design Ultimate Load (DUL) from the DLL.

    DYL = dll * yield_fs
    DUL = dll * ultimate_fs

    Both factors of safety must be >= 1.0.  ultimate_fs must be >= yield_fs
    (the ultimate condition is always more severe than the yield condition).
    """
    if dll < 0:
        raise ValueError(f"dll {dll} must be >= 0")
    if yield_fs < 1.0:
        raise ValueError(f"yield_fs {yield_fs} must be >= 1.0")
    if ultimate_fs < 1.0:
        raise ValueError(f"ultimate_fs {ultimate_fs} must be >= 1.0")
    if ultimate_fs < yield_fs:
        raise ValueError(
            f"ultimate_fs {ultimate_fs} must be >= yield_fs {yield_fs}"
        )
    return {
        "dll": dll,
        "dyl": dll * yield_fs,
        "dul": dll * ultimate_fs,
        "yield_fs": yield_fs,
        "ultimate_fs": ultimate_fs,
    }


def compute_margin_of_safety(allowable: float, applied: float) -> float:
    """
    Compute the structural Margin of Safety (MoS).

    MoS = allowable / applied - 1

    A positive MoS is compliant.  MoS == 0 is the exact boundary (still compliant
    in ECSS-E-ST-32C — the requirement is MoS >= 0).  A negative MoS is a finding.
    Both allowable and applied must be strictly positive.
    """
    if applied <= 0:
        raise ValueError(f"applied {applied} must be > 0")
    if allowable <= 0:
        raise ValueError(f"allowable {allowable} must be > 0")
    return allowable / applied - 1.0


def validate_requirement(req: dict) -> list:
    """
    Validate a single requirement dict for completeness.

    Required keys: 'id', 'type', 'threshold', 'verification_method'.
    Returns a list of finding strings.  An empty list means the requirement is
    complete.  Does not raise; all findings are collected and returned.
    """
    findings = []
    for field in ("id", "type", "threshold", "verification_method"):
        if field not in req or req[field] is None or str(req[field]).strip() == "":
            findings.append(f"missing field '{field}'")

    if "type" in req and req["type"] and str(req["type"]).strip():
        try:
            categorize_requirement(str(req["type"]))
        except ValueError as exc:
            findings.append(str(exc))

    if "verification_method" in req and req["verification_method"] and \
            str(req["verification_method"]).strip():
        vm = str(req["verification_method"]).strip().lower()
        if vm not in VALID_VERIFICATION_METHODS:
            findings.append(
                f"unrecognized verification_method '{req['verification_method']}'; "
                f"must be one of {sorted(VALID_VERIFICATION_METHODS)}"
            )

    return findings


def validate_requirement_set(requirements: list) -> dict:
    """
    Validate a list of requirement dicts for completeness and internal consistency.

    Checks performed:
    - The list must not be empty.
    - Every requirement must pass validate_requirement.
    - No two requirements may share the same 'id'.

    Returns {'compliant': bool, 'findings': list[str]}.
    """
    if not requirements:
        return {"compliant": False, "findings": ["Requirement set is empty"]}

    all_findings = []
    ids_seen: set = set()

    for req in requirements:
        req_id = req.get("id") or "<no-id>"
        if req_id in ids_seen:
            all_findings.append(f"Duplicate requirement id '{req_id}'")
        ids_seen.add(req_id)
        for finding in validate_requirement(req):
            all_findings.append(f"[{req_id}] {finding}")

    return {
        "compliant": len(all_findings) == 0,
        "findings": all_findings,
    }


def assess_requirement_baseline(
    requirements: list,
    load_cases: list,
    allowables: dict,
) -> dict:
    """
    Full structural requirement baseline assessment.

    requirements : list of dicts, each with keys id/type/threshold/verification_method
    load_cases   : list of dicts, each with keys id/dll/yield_fs/ultimate_fs
    allowables   : dict mapping load_case id -> allowable value (float)

    Steps executed:
    1. Validate the requirement set for completeness.
    2. For each load case, derive the DYL and DUL.
    3. Compare the DUL against the allowable and compute MoS; flag exceedances and
       missing allowables.

    Returns {
        'compliant'     : bool,
        'req_validation': {compliant, findings},
        'load_findings' : list[str],
        'mos_findings'  : list[str],
    }.
    """
    result: dict = {
        "compliant": True,
        "req_validation": None,
        "load_findings": [],
        "mos_findings": [],
    }

    req_check = validate_requirement_set(requirements)
    result["req_validation"] = req_check
    if not req_check["compliant"]:
        result["compliant"] = False

    for lc in load_cases:
        lc_id = lc.get("id") or "<no-id>"
        try:
            design = compute_design_loads(
                float(lc["dll"]),
                float(lc["yield_fs"]),
                float(lc["ultimate_fs"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            result["load_findings"].append(
                f"[{lc_id}] load computation error: {exc}"
            )
            result["compliant"] = False
            continue

        if lc_id in allowables:
            try:
                mos = compute_margin_of_safety(
                    float(allowables[lc_id]), design["dul"]
                )
                if mos < 0:
                    result["mos_findings"].append(
                        f"[{lc_id}] MoS = {mos:.4f} (FAIL): "
                        f"allowable {allowables[lc_id]}, DUL {design['dul']:.4f}"
                    )
                    result["compliant"] = False
            except (ValueError, TypeError) as exc:
                result["mos_findings"].append(f"[{lc_id}] MoS error: {exc}")
                result["compliant"] = False
        else:
            result["mos_findings"].append(
                f"[{lc_id}] no allowable on record — requirement baseline incomplete"
            )
            result["compliant"] = False

    return result
