"""
FEM Modelling Requirements Logic — ECSS-E-ST-32C section 4.3
Deterministic, offline, stdlib only. No third-party dependencies.

Covers: idealization selection, element-type compatibility,
mesh density criterion, material model assignment, coordinate/unit
system consistency, and boundary-condition justification checks.
"""

VALID_IDEALIZATIONS = {"STICK", "SHELL", "SOLID"}

# Element families permitted for each idealization
ELEMENT_FAMILIES = {
    "STICK": {"BEAM", "TRUSS", "BAR"},
    "SHELL": {"SHELL", "MEMBRANE", "PLATE"},
    "SOLID": {"HEX", "TET", "WEDGE", "SOLID"},
}

VALID_MATERIAL_MODELS = {"LINEAR_ELASTIC", "ISOTROPIC", "ORTHOTROPIC", "LAMINATE"}
COMPOSITE_MODELS = {"ORTHOTROPIC", "LAMINATE"}

VALID_UNIT_SYSTEMS = {"SI_N_M", "SI_N_MM"}
VALID_COORD_SYSTEMS = {"CARTESIAN", "CYLINDRICAL", "SPHERICAL"}

# Minimum number of elements across the characteristic dimension
_MIN_ELEMENTS_STRESS = 4   # stress gradient criterion: element_size <= ref / 4
_MIN_ELEMENTS_MODAL = 6    # modal criterion: element_size <= half-wavelength / 6

# Temperature excursion threshold above which LINEAR_ELASTIC must be flagged
_TEMP_DELTA_THRESHOLD_K = 200


def check_idealization(idealization, aspect_ratio):
    """
    Validate the chosen idealization against the component aspect ratio.

    Rules (ECSS-E-ST-32C §4.3):
      STICK  — aspect_ratio >= 10 (slender member, beam/truss behaviour)
      SHELL  — no aspect-ratio gate (thin-walled; shell behaviour)
      SOLID  — aspect_ratio <= 5 (bulky; volumetric behaviour)

    Returns (ok: bool, reason: str).
    """
    if idealization not in VALID_IDEALIZATIONS:
        return False, (
            f"Unknown idealization '{idealization}'. "
            f"Choose from {sorted(VALID_IDEALIZATIONS)}."
        )
    if not isinstance(aspect_ratio, (int, float)):
        return False, "aspect_ratio must be a positive number."
    if aspect_ratio <= 0:
        return False, "aspect_ratio must be > 0."

    if idealization == "STICK" and aspect_ratio < 10:
        return False, (
            f"STICK idealization requires aspect_ratio >= 10; got {aspect_ratio}. "
            "Use SHELL or SOLID for less slender components."
        )
    if idealization == "SOLID" and aspect_ratio > 5:
        return False, (
            f"SOLID idealization not appropriate for aspect_ratio > 5; got {aspect_ratio}. "
            "Consider SHELL idealization for this component."
        )
    return True, "OK"


def check_element_type(idealization, element_type):
    """
    Validate that the element type is compatible with the chosen idealization.

    Returns (ok: bool, reason: str).
    """
    if idealization not in VALID_IDEALIZATIONS:
        return False, f"Unknown idealization '{idealization}'."
    allowed = ELEMENT_FAMILIES.get(idealization, set())
    if element_type not in allowed:
        return False, (
            f"Element type '{element_type}' is incompatible with "
            f"'{idealization}' idealization. Allowed: {sorted(allowed)}."
        )
    return True, "OK"


def check_mesh_density(element_size, reference_size, mode="stress"):
    """
    Validate element size against the spatial resolution criterion.

    mode='stress': element_size <= reference_size / _MIN_ELEMENTS_STRESS
    mode='modal':  element_size <= reference_size / _MIN_ELEMENTS_MODAL

    reference_size is the characteristic length (stress-gradient length
    for stress mode; modal half-wavelength for modal mode).

    Returns (ok: bool, reason: str).
    """
    if mode not in ("stress", "modal"):
        return False, (
            f"Unknown mode '{mode}'. Use 'stress' or 'modal'."
        )
    if not isinstance(element_size, (int, float)) or element_size <= 0:
        return False, "element_size must be a positive number."
    if not isinstance(reference_size, (int, float)) or reference_size <= 0:
        return False, "reference_size must be a positive number."

    divisor = _MIN_ELEMENTS_STRESS if mode == "stress" else _MIN_ELEMENTS_MODAL
    limit = reference_size / divisor
    if element_size > limit:
        return False, (
            f"Element size {element_size} exceeds the {mode} limit "
            f"{limit:.4f} (reference_size {reference_size} / {divisor})."
        )
    return True, "OK"


def check_material_model(material_model, is_composite, temp_delta_k=None):
    """
    Validate the constitutive model against material class and thermal loading.

    Composite materials (is_composite=True) must use ORTHOTROPIC or LAMINATE.
    Non-composite materials must not use composite-specific models.
    A temperature excursion above _TEMP_DELTA_THRESHOLD_K with a
    LINEAR_ELASTIC model is flagged for property-variation verification.

    Returns (ok: bool, reason: str).
    """
    if material_model not in VALID_MATERIAL_MODELS:
        return False, (
            f"Unknown material model '{material_model}'. "
            f"Choose from {sorted(VALID_MATERIAL_MODELS)}."
        )
    if is_composite and material_model not in COMPOSITE_MODELS:
        return False, (
            f"Composite material requires a model in "
            f"{sorted(COMPOSITE_MODELS)}; got '{material_model}'."
        )
    if not is_composite and material_model in COMPOSITE_MODELS:
        return False, (
            f"Non-composite material must not use '{material_model}'. "
            "Use LINEAR_ELASTIC or ISOTROPIC."
        )
    if (
        temp_delta_k is not None
        and abs(temp_delta_k) > _TEMP_DELTA_THRESHOLD_K
        and material_model == "LINEAR_ELASTIC"
    ):
        return False, (
            f"Temperature excursion of {temp_delta_k} K exceeds "
            f"{_TEMP_DELTA_THRESHOLD_K} K; verify material property "
            "variation before using LINEAR_ELASTIC."
        )
    return True, "OK"


def check_unit_system(unit_system, coord_system):
    """
    Validate that both the unit system and coordinate system are recognised.

    Returns (ok: bool, reason: str).
    """
    if unit_system not in VALID_UNIT_SYSTEMS:
        return False, (
            f"Unknown unit system '{unit_system}'. "
            f"Choose from {sorted(VALID_UNIT_SYSTEMS)}."
        )
    if coord_system not in VALID_COORD_SYSTEMS:
        return False, (
            f"Unknown coordinate system '{coord_system}'. "
            f"Choose from {sorted(VALID_COORD_SYSTEMS)}."
        )
    return True, "OK"


def check_boundary_conditions(bcs):
    """
    Verify every boundary condition carries a written mechanical justification.

    bcs: list of dicts, each with at least 'dof', 'constraint', 'justification'.

    Returns (ok: bool, issues: list[str]).
    """
    if not isinstance(bcs, list):
        return False, ["bcs must be a list of boundary-condition dicts."]
    issues = []
    for i, bc in enumerate(bcs):
        if not isinstance(bc, dict):
            issues.append(f"BC[{i}] is not a dict.")
            continue
        justification = bc.get("justification", "")
        if not isinstance(justification, str) or not justification.strip():
            issues.append(
                f"BC[{i}] (dof={bc.get('dof', '?')}) has no mechanical justification."
            )
    return len(issues) == 0, issues


def evaluate_model(model):
    """
    Evaluate a complete FEM model specification and return a compliance report.

    model dict keys:
      unit_system        — str
      coord_system       — str
      components         — list of component dicts (see below)
      boundary_conditions — list of BC dicts

    Component dict keys:
      name           — str
      idealization   — str ("STICK" | "SHELL" | "SOLID")
      aspect_ratio   — float
      element_type   — str
      element_size   — float
      reference_size — float
      mesh_mode      — str ("stress" | "modal"), default "stress"
      material_model — str
      is_composite   — bool
      temp_delta_k   — float or None

    Returns {'findings': list[str], 'compliant': bool}.
    """
    findings = []

    ok, reason = check_unit_system(
        model.get("unit_system", ""),
        model.get("coord_system", ""),
    )
    if not ok:
        findings.append(f"UNIT/COORD: {reason}")

    for comp in model.get("components", []):
        name = comp.get("name", "?")

        ok, reason = check_idealization(
            comp.get("idealization", ""),
            comp.get("aspect_ratio"),
        )
        if not ok:
            findings.append(f"IDEALIZATION [{name}]: {reason}")

        ok, reason = check_element_type(
            comp.get("idealization", ""),
            comp.get("element_type", ""),
        )
        if not ok:
            findings.append(f"ELEMENT_TYPE [{name}]: {reason}")

        ok, reason = check_mesh_density(
            comp.get("element_size", 0),
            comp.get("reference_size", 0),
            comp.get("mesh_mode", "stress"),
        )
        if not ok:
            findings.append(f"MESH_DENSITY [{name}]: {reason}")

        ok, reason = check_material_model(
            comp.get("material_model", ""),
            comp.get("is_composite", False),
            comp.get("temp_delta_k"),
        )
        if not ok:
            findings.append(f"MATERIAL [{name}]: {reason}")

    ok, issues = check_boundary_conditions(model.get("boundary_conditions", []))
    for issue in issues:
        findings.append(f"BC: {issue}")

    return {"findings": findings, "compliant": len(findings) == 0}
