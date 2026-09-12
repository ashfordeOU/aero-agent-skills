"""
DRD Allowables logic — ECSS-E-ST-32C Annex H (MMPA).
Material and mechanical-part allowables document verification.
Stdlib only. Offline. Deterministic.
"""

# Allowable basis types
# A-basis: 99th-percentile lower bound at 95% confidence
# B-basis: 90th-percentile lower bound at 95% confidence
# S-basis: published specification minimum
# TYPICAL: mean value (non-critical stiffness estimates only)
VALID_BASES = {"A", "B", "S", "TYPICAL"}

# Recognised material families
MATERIAL_FAMILIES = {"metallic", "composite", "adhesive", "fastener", "other"}

# Required properties per material family (minimum set for structural use)
REQUIRED_PROPERTIES = {
    "metallic":  {"Ftu", "Fty", "Fcy", "Fsu", "E", "density"},
    "composite": {"F1tu", "F1cu", "F2tu", "F2cu", "F12su", "E11", "E22", "G12", "nu12"},
    "adhesive":  {"shear_strength", "peel_strength", "E"},
    "fastener":  {"Fstu", "Fsbru", "diameter"},
    "other":     {"strength", "E"},
}

# Approved allowables source references
APPROVED_SOURCES = {
    "MMPDS",
    "CMH-17",
    "MIL-HDBK-5",
    "ESA-PSS",
    "test_data",
    "manufacturer_data",
}

# Valid temperature units
VALID_TEMP_UNITS = {"K", "degC", "degF"}

# Absolute-zero floors per unit
_ABS_ZERO = {"K": 0.0, "degC": -273.15, "degF": -459.67}


def validate_basis(basis: str) -> bool:
    """Return True if basis is a recognised allowable basis."""
    return str(basis).upper() in VALID_BASES


def categorize_material(material_family: str) -> str:
    """
    Return the normalised material-family string.
    Raises ValueError for unrecognised families.
    """
    normalized = str(material_family).lower().strip()
    if normalized not in MATERIAL_FAMILIES:
        raise ValueError(
            f"Unrecognised material family: '{material_family}'. "
            f"Must be one of {sorted(MATERIAL_FAMILIES)}."
        )
    return normalized


def check_property_completeness(material_family: str, provided_props: set) -> dict:
    """
    Check whether all required properties for the material family are present.
    Returns dict with keys 'required', 'present', 'missing', 'complete'.
    Raises ValueError for unrecognised material family.
    """
    family = categorize_material(material_family)
    required = REQUIRED_PROPERTIES[family]
    present = required & provided_props
    missing = required - provided_props
    return {
        "required": sorted(required),
        "present":  sorted(present),
        "missing":  sorted(missing),
        "complete": len(missing) == 0,
    }


def validate_allowable_values_metallic(properties: dict) -> list:
    """
    Check physical plausibility of metallic allowable values.
    Returns list of finding strings (empty list means no issues).
    """
    findings = []
    ftu = properties.get("Ftu")
    fty = properties.get("Fty")
    fcy = properties.get("Fcy")
    fsu = properties.get("Fsu")
    mod = properties.get("E")

    if ftu is not None and ftu <= 0:
        findings.append("Ftu must be positive")
    if fty is not None and fty <= 0:
        findings.append("Fty must be positive")
    if ftu is not None and fty is not None and fty > ftu:
        findings.append("Fty (yield) must not exceed Ftu (ultimate)")
    if ftu is not None and fsu is not None and fsu > ftu:
        findings.append("Fsu (shear ultimate) must not exceed Ftu")
    if fcy is not None and fcy <= 0:
        findings.append("Fcy must be positive")
    if mod is not None and mod <= 0:
        findings.append("Young's modulus E must be positive")
    return findings


def validate_allowable_values_composite(properties: dict) -> list:
    """
    Check physical plausibility of composite allowable values.
    Returns list of finding strings (empty list means no issues).
    """
    findings = []
    for key in ["F1tu", "F1cu", "F2tu", "F2cu", "F12su", "E11", "E22", "G12"]:
        val = properties.get(key)
        if val is not None and val <= 0:
            findings.append(f"{key} must be positive")
    nu12 = properties.get("nu12")
    if nu12 is not None and not (-1.0 < nu12 < 1.0):
        findings.append("nu12 (Poisson ratio) must be in the open range (-1, 1)")
    return findings


def check_temperature_range(temp_min, temp_max, unit: str) -> dict:
    """
    Validate a temperature-range definition for allowables applicability.
    Returns dict with 'valid' bool and 'issues' list.
    """
    issues = []
    if unit not in VALID_TEMP_UNITS:
        issues.append(
            f"Unrecognised temperature unit '{unit}'. "
            f"Must be one of {sorted(VALID_TEMP_UNITS)}."
        )
    else:
        floor = _ABS_ZERO[unit]
        if temp_min is not None and temp_min < floor:
            issues.append(
                f"temp_min {temp_min} {unit} is below absolute zero ({floor} {unit})"
            )
        if temp_min is not None and temp_max is not None and temp_min >= temp_max:
            issues.append("temp_min must be strictly less than temp_max")
    return {"valid": len(issues) == 0, "issues": issues}


def check_source_traceability(source: str) -> bool:
    """Return True if source is in the approved reference list."""
    return source in APPROVED_SOURCES


def apply_environmental_knockdown(allowable: float, kdf: float) -> float:
    """
    Apply an environmental knockdown factor kdf in (0, 1] to an allowable value.
    Raises ValueError for out-of-range kdf or negative allowable.
    """
    if not (0.0 < kdf <= 1.0):
        raise ValueError(
            f"Knockdown factor must be in the range (0, 1]; got {kdf}"
        )
    if allowable < 0:
        raise ValueError(
            f"Allowable value must be non-negative; got {allowable}"
        )
    return allowable * kdf


def assess_drd_sections(sections_present: set) -> dict:
    """
    Verify that all mandatory DRD sections for ECSS-E-ST-32C Annex H MMPA are present.
    Returns dict with 'mandatory', 'present', 'missing', 'complete'.
    """
    mandatory = {
        "scope",
        "applicable_documents",
        "material_identification",
        "allowable_basis",
        "property_tables",
        "source_traceability",
        "environmental_conditions",
        "statistical_derivation",
        "limitations_and_applicability",
    }
    present = mandatory & sections_present
    missing = mandatory - sections_present
    return {
        "mandatory": sorted(mandatory),
        "present":   sorted(present),
        "missing":   sorted(missing),
        "complete":  len(missing) == 0,
    }


def summarize_material_record(record: dict) -> dict:
    """
    Validate and summarize a single allowables record.

    Expected record keys:
        id        - unique material identifier string
        family    - material family string
        basis     - allowable basis string (A/B/S/TYPICAL)
        properties - dict of property name -> numeric value
        source    - reference source string
        temp_min  - lower temperature bound (numeric)
        temp_max  - upper temperature bound (numeric)
        temp_unit - temperature unit string (K / degC / degF)

    Returns dict with 'id', 'family', 'findings' (list of str), 'valid' (bool).
    """
    findings = []

    mat_id = record.get("id", "UNKNOWN")

    basis = record.get("basis", "")
    if not validate_basis(basis):
        findings.append(f"Unrecognised allowable basis '{basis}'")

    try:
        family = categorize_material(record.get("family", ""))
    except ValueError as exc:
        findings.append(str(exc))
        family = "other"

    props = record.get("properties", {})
    completeness = check_property_completeness(family, set(props.keys()))
    if not completeness["complete"]:
        findings.append(f"Missing required properties: {completeness['missing']}")

    if family == "metallic":
        findings.extend(validate_allowable_values_metallic(props))
    elif family == "composite":
        findings.extend(validate_allowable_values_composite(props))

    source = record.get("source", "")
    if not check_source_traceability(source):
        findings.append(f"Source '{source}' not in approved reference list")

    temp_check = check_temperature_range(
        record.get("temp_min"),
        record.get("temp_max"),
        record.get("temp_unit", ""),
    )
    if not temp_check["valid"]:
        findings.extend(temp_check["issues"])

    return {
        "id":       mat_id,
        "family":   family,
        "findings": findings,
        "valid":    len(findings) == 0,
    }
