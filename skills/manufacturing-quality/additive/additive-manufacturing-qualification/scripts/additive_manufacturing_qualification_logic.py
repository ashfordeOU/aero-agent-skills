"""Additive manufacturing (AM) process qualification for aerospace parts.

An AM build (powder bed fusion, directed energy deposition) is qualified
through its parameter set: layer height, laser power, scan speed, and
hatch spacing. The volumetric energy density (VED) ties the four
parameters together: VED = laser power / (scan speed x hatch spacing x
layer height), in J/mm^3 with W, mm/s, mm, mm. Qualification evidence
comes from witness coupons built with the same parameter set and
machine, material property verification from those coupons, and first
article checks for the AM part.

This module implements the qualification model exercised by
scripts/test_additive_manufacturing_qualification.py (stdlib unittest,
offline): the AM parameter set record with volumetric energy density
computation, witness coupon count determination from the material
property sample plan, and the qualification record completeness check.
"""

# The additive manufacturing qualification record checklist fields.
REQUIRED_FIELDS = (
    "parameter_set",
    "witness_coupon_plan",
    "material_property_verification",
    "first_article_inspection",
)


def volumetric_energy_density(laser_power, scan_speed, hatch_spacing, layer_height):
    """Volumetric energy density of the AM process, in J/mm^3.

    VED = laser_power / (scan_speed x hatch_spacing x layer_height).
    Units: laser_power in W, scan_speed in mm/s, hatch_spacing in mm,
    layer_height in mm. Raises ValueError when a value is missing,
    non-numeric, or not positive.
    """
    try:
        power = float(laser_power)
        speed = float(scan_speed)
        hatch = float(hatch_spacing)
        layer = float(layer_height)
    except (TypeError, ValueError):
        raise ValueError(
            "laser power, scan speed, hatch spacing, layer height must be numeric"
        )
    for name, value in (
        ("laser power", power),
        ("scan speed", speed),
        ("hatch spacing", hatch),
        ("layer height", layer),
    ):
        if value <= 0:
            raise ValueError("%s must be > 0" % name)
    return power / (speed * hatch * layer)


def build_parameter_set(
    process_id, material, laser_power, scan_speed, hatch_spacing, layer_height
):
    """Build and validate the AM parameter set record.

    Returns a dict with the four build parameters, the computed
    volumetric energy density (key 'volumetric_energy_density'), the
    process id, and the material. Raises ValueError on a malformed
    process id or material, or a non-positive build parameter.
    """
    if not isinstance(process_id, str) or not process_id.strip():
        raise ValueError("process_id must be a non-empty string")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty string")
    ved = volumetric_energy_density(
        laser_power, scan_speed, hatch_spacing, layer_height
    )
    return {
        "process_id": process_id,
        "material": material,
        "laser_power": float(laser_power),
        "scan_speed": float(scan_speed),
        "hatch_spacing": float(hatch_spacing),
        "layer_height": float(layer_height),
        "volumetric_energy_density": ved,
    }


def witness_coupon_count(sample_plan):
    """Coupon count from the material property sample plan.

    sample_plan: non-empty list of {'test', 'samples'} mappings, one
    per material property test (tensile, fatigue, hardness, ...).

    Rule: coupon count = total samples across all tests + one spare
    coupon per test type. The spare covers a re-test without a new
    build. Raises ValueError on a malformed plan.
    """
    if not isinstance(sample_plan, list) or not sample_plan:
        raise ValueError("sample_plan must be a non-empty list")
    total = 0
    for entry in sample_plan:
        if not isinstance(entry, dict):
            raise ValueError("each sample plan entry must be a mapping")
        test = entry.get("test")
        if not isinstance(test, str) or not test.strip():
            raise ValueError("each sample plan entry needs a non-empty 'test'")
        samples = entry.get("samples")
        if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
            raise ValueError(
                "sample plan entry %r 'samples' must be a positive int" % test
            )
        total += samples
    return total + len(sample_plan)


def build_qualification_record(
    parameter_set,
    witness_coupon_plan,
    material_property_verification,
    first_article_inspection,
):
    """Build and validate the AM qualification record.

    parameter_set: dict from build_parameter_set(). witness_coupon_plan:
    list of {'test', 'samples'} mappings. material_property_verification:
    list of {'test', 'result', 'status'} mappings, non-empty once coupon
    results are recorded. first_article_inspection: list of {'check',
    'status'} mappings for the AM first article checks.

    Returns the record plus 'missing' (absent REQUIRED_FIELDS),
    'complete' (boolean), and 'checklist' (one {'field', 'present',
    'detail'} item per required field). Raises ValueError when a field
    has the wrong type or an empty value.
    """
    if not isinstance(parameter_set, dict) or not parameter_set:
        raise ValueError("parameter_set must be a non-empty mapping")
    if not isinstance(witness_coupon_plan, list) or not witness_coupon_plan:
        raise ValueError("witness_coupon_plan must be a non-empty list")
    if (
        not isinstance(material_property_verification, list)
        or not material_property_verification
    ):
        raise ValueError("material_property_verification must be a non-empty list")
    if not isinstance(first_article_inspection, list) or not first_article_inspection:
        raise ValueError("first_article_inspection must be a non-empty list")

    record = {
        "parameter_set": parameter_set,
        "witness_coupon_plan": witness_coupon_plan,
        "material_property_verification": material_property_verification,
        "first_article_inspection": first_article_inspection,
    }
    missing = validate_record(record)
    record["missing"] = missing
    record["complete"] = not missing
    record["checklist"] = [
        {
            "field": field,
            "present": field not in missing,
            "detail": record.get(field, ""),
        }
        for field in REQUIRED_FIELDS
    ]
    return record


def validate_record(record):
    """Return the list of missing REQUIRED_FIELDS in a record.

    Empty list means the record is complete. A field is missing when
    absent, None, an empty string, or an empty mapping or list. Raises
    ValueError when record is not a mapping.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or value == "" or value == {} or value == []:
            missing.append(field)
    return missing
