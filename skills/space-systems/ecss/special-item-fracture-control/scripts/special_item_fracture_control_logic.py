"""
Fracture control logic for special items per ECSS-E-ST-32C §8.5–8.9.
Covers non-metallics, rotating machinery, glass, fasteners, and EDM-treated alloys.
Stdlib only — offline, deterministic, no external dependencies.
"""

# --- Category registry ---

VALID_CATEGORIES = frozenset([
    "non_metallic",
    "rotating_machinery",
    "glass",
    "fastener",
    "edm_treated_alloy",
])

NON_METALLIC_METHODS = frozenset(["proof_test", "analysis", "similarity"])

# --- Acceptance thresholds (ECSS-E-ST-32C §8.5–8.9) ---

NON_METALLIC_MIN_PROOF_FACTOR = 1.5   # §8.5: proof load ≥ 1.5 × design load
BURST_SPEED_MARGIN = 1.25             # §8.6: burst speed ≥ 1.25 × operating speed
GLASS_MIN_PROOF_RATIO = 1.3           # §8.7: proof stress ≥ 1.3 × design stress
EDM_MIN_REMOVAL_DEPTH_MM = 0.1        # §8.9: recast-layer removal ≥ 0.1 mm

FASTENER_EXEMPT_GRADES = frozenset(["A", "B"])


# --- Category validation ---

def validate_category(category):
    """
    Confirm the item category is one of the five defined special-item types.
    Raises ValueError for any unrecognized category.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown item category '{category}'. "
            f"Must be one of: {sorted(VALID_CATEGORIES)}"
        )
    return category


# --- Per-category acceptance checks ---

def check_non_metallic(method, proof_factor=None):
    """
    Evaluate fracture control compliance for a non-metallic item (§8.5).

    method      : str  — one of 'proof_test', 'analysis', 'similarity'
    proof_factor: float — required when method is 'proof_test';
                  ratio of applied proof load to design load

    Returns dict:
      compliant (bool), findings (list[str])
    """
    if method not in NON_METALLIC_METHODS:
        raise ValueError(
            f"Invalid compliance method '{method}'. "
            f"Must be one of: {sorted(NON_METALLIC_METHODS)}"
        )
    findings = []
    if method == "proof_test":
        if proof_factor is None:
            raise ValueError(
                "proof_factor is required when method='proof_test'"
            )
        if proof_factor < NON_METALLIC_MIN_PROOF_FACTOR:
            findings.append(
                f"Proof factor {proof_factor:.4f} is below minimum "
                f"{NON_METALLIC_MIN_PROOF_FACTOR} (§8.5)"
            )
    return {"compliant": len(findings) == 0, "findings": findings}


def check_rotating_machinery(operating_speed_rpm, burst_speed_rpm):
    """
    Evaluate burst-speed margin for a rotating machinery item (§8.6).

    operating_speed_rpm: float — maximum operating speed in RPM (must be > 0)
    burst_speed_rpm    : float — demonstrated or design burst speed in RPM (must be > 0)

    Returns dict:
      compliant (bool), margin (float), findings (list[str])
    """
    if operating_speed_rpm <= 0:
        raise ValueError("operating_speed_rpm must be positive")
    if burst_speed_rpm <= 0:
        raise ValueError("burst_speed_rpm must be positive")

    margin = burst_speed_rpm / operating_speed_rpm
    findings = []
    if margin < BURST_SPEED_MARGIN:
        findings.append(
            f"Burst margin {margin:.4f} is below minimum {BURST_SPEED_MARGIN} "
            f"(burst_speed / operating_speed < 1.25) (§8.6)"
        )
    return {"compliant": len(findings) == 0, "margin": margin, "findings": findings}


def check_glass(design_stress_mpa, proof_stress_mpa):
    """
    Evaluate the proof-stress ratio for a glass item (§8.7).

    design_stress_mpa: float — maximum design stress in MPa (must be > 0)
    proof_stress_mpa : float — applied proof stress in MPa (must be > 0)

    Returns dict:
      compliant (bool), ratio (float), findings (list[str])
    """
    if design_stress_mpa <= 0:
        raise ValueError("design_stress_mpa must be positive")
    if proof_stress_mpa <= 0:
        raise ValueError("proof_stress_mpa must be positive")

    ratio = proof_stress_mpa / design_stress_mpa
    findings = []
    if ratio < GLASS_MIN_PROOF_RATIO:
        findings.append(
            f"Proof stress ratio {ratio:.4f} is below minimum "
            f"{GLASS_MIN_PROOF_RATIO} (§8.7)"
        )
    return {"compliant": len(findings) == 0, "ratio": ratio, "findings": findings}


def check_fastener(grade, torque_controlled, tension_critical):
    """
    Evaluate whether a fastener qualifies for a fracture-control exemption (§8.8).

    grade           : str  — fastener material grade ('A' or 'B' for exempt grades)
    torque_controlled: bool — True if installation is torque-controlled
    tension_critical : bool — True if the fastener is in a tension-critical joint

    Exemption requires all three: standard grade, torque-controlled installation,
    and not in a tension-critical joint.

    Returns dict:
      exempt (bool), findings (list[str])
    """
    findings = []
    if grade not in FASTENER_EXEMPT_GRADES:
        findings.append(
            f"Fastener grade '{grade}' is not a standard exempt grade "
            f"({sorted(FASTENER_EXEMPT_GRADES)}) — full fracture analysis required (§8.8)"
        )
    if not torque_controlled:
        findings.append(
            "Fastener installation is not torque-controlled — "
            "exemption not applicable (§8.8)"
        )
    if tension_critical:
        findings.append(
            "Fastener is in a tension-critical joint — "
            "fracture analysis required (§8.8)"
        )
    return {"exempt": len(findings) == 0, "findings": findings}


def check_edm_alloy(removal_depth_mm, removal_process=None):
    """
    Evaluate EDM recast-layer removal compliance for an EDM-treated alloy (§8.9).

    removal_depth_mm: float — confirmed removal depth in mm (must be ≥ 0)
    removal_process : str or None — name of the documented removal process

    Returns dict:
      compliant (bool), findings (list[str])
    """
    if removal_depth_mm < 0:
        raise ValueError("removal_depth_mm must be non-negative")

    findings = []
    if removal_depth_mm < EDM_MIN_REMOVAL_DEPTH_MM:
        findings.append(
            f"EDM recast-layer removal depth {removal_depth_mm:.4f} mm is below "
            f"minimum {EDM_MIN_REMOVAL_DEPTH_MM} mm (§8.9)"
        )
    if not removal_process:
        findings.append(
            "No approved removal process documented — required for §8.9 compliance"
        )
    return {"compliant": len(findings) == 0, "findings": findings}


# --- Full item assessment ---

def assess_item(item):
    """
    Run the full fracture control assessment for a single special item.

    item: dict with keys:
      'name'     (str)  — item identifier
      'category' (str)  — one of VALID_CATEGORIES
      plus category-specific keys (see individual check functions above)

    Returns dict:
      name (str), category (str), compliant (bool), findings (list[str])
    """
    name = item.get("name", "unnamed")
    category = validate_category(item["category"])

    if category == "non_metallic":
        result = check_non_metallic(
            method=item["method"],
            proof_factor=item.get("proof_factor"),
        )
        compliant = result["compliant"]
        findings = result["findings"]

    elif category == "rotating_machinery":
        result = check_rotating_machinery(
            operating_speed_rpm=item["operating_speed_rpm"],
            burst_speed_rpm=item["burst_speed_rpm"],
        )
        compliant = result["compliant"]
        findings = result["findings"]

    elif category == "glass":
        result = check_glass(
            design_stress_mpa=item["design_stress_mpa"],
            proof_stress_mpa=item["proof_stress_mpa"],
        )
        compliant = result["compliant"]
        findings = result["findings"]

    elif category == "fastener":
        result = check_fastener(
            grade=item["grade"],
            torque_controlled=item["torque_controlled"],
            tension_critical=item.get("tension_critical", False),
        )
        compliant = result["exempt"]
        findings = result["findings"]

    elif category == "edm_treated_alloy":
        result = check_edm_alloy(
            removal_depth_mm=item["removal_depth_mm"],
            removal_process=item.get("removal_process"),
        )
        compliant = result["compliant"]
        findings = result["findings"]

    return {
        "name": name,
        "category": category,
        "compliant": compliant,
        "findings": findings,
    }
