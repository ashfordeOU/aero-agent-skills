"""Radiographic screening inspection of sealed hybrid packages.

Anchor: ECSS-Q-ST-60-05C clause 10.3.10 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Take enough views. A radiograph is a projection, so a void, a strand
   of debris or a displaced element hidden behind something else in one
   direction is visible from another. A single view of a stacked
   assembly is a sample of the interior, not a survey of it.
2. Show the image can resolve what it is looking for. Image quality is
   stated as the smallest detail the system distinguishes as a fraction
   of the thickness it is looking through; an image that cannot resolve
   the smallest rejectable feature returns clean views that carry no
   information.
3. Get the beam through the package without washing it out. Attenuation
   is exponential in thickness and depends on what the lid and
   substrate are made of, so the same setting that images an epoxy body
   is opaque through a kovar lid and transparent through nothing at
   all. A usable radiograph sits inside a band at both ends.
4. Grade voids three ways. The total voided fraction of a bond, the
   largest single void in it, and a void sitting under an active area
   are three different objections, and a bond can satisfy two of them
   while failing the third.
5. Grade debris by what it can reach. A particle matters when its
   largest dimension can span the smallest conductor spacing in the
   cavity; below that it is dirt and above it is a short waiting for a
   shock.
6. Grade a displaced element by the clearance it leaves, not by how far
   it moved. An offset that would be trivial in a roomy cavity closes
   the last of the clearance in a crowded one.

Stdlib only, offline, deterministic.
"""

import math

# Views a package interior owes, from how it is built up.
VIEW_REQUIREMENTS = {
    "single-layer-substrate": 2,
    "stacked-assembly": 3,
    "multi-cavity-assembly": 3,
}

# Linear attenuation per millimetre for the materials the beam passes.
MATERIAL_ATTENUATION_PER_MM = {
    "kovar-lid": 2.60,
    "aluminium-lid": 0.45,
    "alumina-substrate": 0.55,
    "gold-plated-copper": 5.00,
    "moulding-epoxy": 0.12,
}

# Transmitted fraction a usable radiograph sits between. Below the floor
# the image is starved; above the ceiling there is no contrast left.
USABLE_TRANSMISSION_BAND = (0.02, 0.60)

# Smallest detail the system must distinguish, as a percentage of the
# thickness it is looking through.
MAX_IMAGE_QUALITY_PERCENT = 2.0

# Void limits, as fractions of the bonded area.
MAX_TOTAL_VOID_FRACTION = 0.50
MAX_SINGLE_VOID_FRACTION = 0.15
MAX_ACTIVE_AREA_VOID_FRACTION = 0.10

# Indication groups this leaf reports against.
INDICATION_GROUPS = (
    "attachment-void",
    "foreign-material",
    "displaced-element",
    "no-indication",
)

COMPARISON_TOLERANCE = 1.0e-12

PASS = "radiograph-accepted"
FAIL = "radiograph-rejected"


def _number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _positive_number(label, value):
    value = _number(label, value)
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_number(label, value):
    value = _number(label, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _positive_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def required_views(build_style):
    """Views the interior of this build style owes."""
    if build_style not in VIEW_REQUIREMENTS:
        raise ValueError(
            "unknown build_style %r (expected one of %s)"
            % (build_style, ", ".join(sorted(VIEW_REQUIREMENTS)))
        )
    return VIEW_REQUIREMENTS[build_style]


def attenuation_coefficient(material):
    """Linear attenuation per millimetre carried by a material."""
    if material not in MATERIAL_ATTENUATION_PER_MM:
        raise ValueError(
            "unknown material %r (expected one of %s)"
            % (material, ", ".join(sorted(MATERIAL_ATTENUATION_PER_MM)))
        )
    return MATERIAL_ATTENUATION_PER_MM[material]


def transmitted_fraction(layers):
    """Fraction of the beam that survives a stack of material layers."""
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("layers must be a non-empty sequence")
    total = 0.0
    for index, layer in enumerate(layers):
        if not isinstance(layer, (list, tuple)) or len(layer) != 2:
            raise ValueError(
                "layer %d must be a (material, thickness_mm) pair" % index
            )
        material, thickness = layer
        total += attenuation_coefficient(material) * _positive_number(
            "layer %d thickness_mm" % index, thickness
        )
    return math.exp(-total)


def stack_thickness_mm(layers):
    """Total thickness the beam has to look through."""
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("layers must be a non-empty sequence")
    total = 0.0
    for index, layer in enumerate(layers):
        if not isinstance(layer, (list, tuple)) or len(layer) != 2:
            raise ValueError(
                "layer %d must be a (material, thickness_mm) pair" % index
            )
        attenuation_coefficient(layer[0])
        total += _positive_number("layer %d thickness_mm" % index, layer[1])
    return total


def image_quality_percent(smallest_detail_mm, total_thickness_mm):
    """Smallest resolved detail as a percentage of the thickness."""
    detail = _positive_number("smallest_detail_mm", smallest_detail_mm)
    thickness = _positive_number("total_thickness_mm", total_thickness_mm)
    return 100.0 * detail / thickness


def void_area_fraction(void_areas_mm2, bond_area_mm2):
    """Fraction of a bonded area the voids together occupy."""
    if not isinstance(void_areas_mm2, (list, tuple)):
        raise ValueError("void_areas_mm2 must be a sequence")
    bond = _positive_number("bond_area_mm2", bond_area_mm2)
    total = 0.0
    for index, area in enumerate(void_areas_mm2):
        total += _non_negative_number("void %d area" % index, area)
    if total > bond * (1.0 + COMPARISON_TOLERANCE):
        raise ValueError(
            "voids total %g mm2 in a bond of %g mm2" % (total, bond)
        )
    return total / bond


def largest_void_fraction(void_areas_mm2, bond_area_mm2):
    """Fraction of the bonded area the single worst void occupies."""
    void_area_fraction(void_areas_mm2, bond_area_mm2)
    bond = _positive_number("bond_area_mm2", bond_area_mm2)
    if not void_areas_mm2:
        return 0.0
    return max(float(area) for area in void_areas_mm2) / bond


def particle_can_bridge(particle_dimension_mm, conductor_spacing_mm):
    """True when a loose particle is long enough to span two conductors."""
    dimension = _positive_number("particle_dimension_mm", particle_dimension_mm)
    spacing = _positive_number("conductor_spacing_mm", conductor_spacing_mm)
    return dimension >= spacing * (1.0 - COMPARISON_TOLERANCE)


def clearance_after_offset(nominal_clearance_mm, offset_mm):
    """Clearance left once an element has moved off its intended place."""
    nominal = _positive_number("nominal_clearance_mm", nominal_clearance_mm)
    offset = _non_negative_number("offset_mm", offset_mm)
    return nominal - offset


def categorize_indication(indication):
    """Group one radiographic indication into the family it belongs to."""
    if indication is None:
        return "no-indication"
    if not isinstance(indication, str) or not indication.strip():
        raise ValueError("indication must be a non-empty string or None")
    if indication not in INDICATION_GROUPS:
        raise ValueError(
            "unknown indication %r (expected one of %s)"
            % (indication, ", ".join(INDICATION_GROUPS))
        )
    return indication


def validate_radiograph(record):
    """Validate one radiographic record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    build_style = record.get("build_style")
    required_views(build_style)
    layers = record.get("layers")
    stack_thickness_mm(layers)
    voids = record.get("void_areas_mm2", [])
    if not isinstance(voids, (list, tuple)):
        raise ValueError("unit %s void_areas_mm2 must be a sequence" % unit_id)
    return {
        "id": unit_id,
        "build_style": build_style,
        "layers": [(material, float(thickness)) for material, thickness in layers],
        "views_taken": _positive_integer(
            "unit %s views_taken" % unit_id, record.get("views_taken")
        ),
        "smallest_detail_mm": _positive_number(
            "unit %s smallest_detail_mm" % unit_id,
            record.get("smallest_detail_mm"),
        ),
        "bond_area_mm2": _positive_number(
            "unit %s bond_area_mm2" % unit_id, record.get("bond_area_mm2")
        ),
        "void_areas_mm2": [float(area) for area in voids],
        "void_under_active_area_mm2": _non_negative_number(
            "unit %s void_under_active_area_mm2" % unit_id,
            record.get("void_under_active_area_mm2", 0.0),
        ),
        "particle_dimension_mm": _non_negative_number(
            "unit %s particle_dimension_mm" % unit_id,
            record.get("particle_dimension_mm", 0.0),
        ),
        "conductor_spacing_mm": _positive_number(
            "unit %s conductor_spacing_mm" % unit_id,
            record.get("conductor_spacing_mm"),
        ),
        "nominal_clearance_mm": _positive_number(
            "unit %s nominal_clearance_mm" % unit_id,
            record.get("nominal_clearance_mm"),
        ),
        "element_offset_mm": _non_negative_number(
            "unit %s element_offset_mm" % unit_id,
            record.get("element_offset_mm", 0.0),
        ),
        "minimum_clearance_mm": _positive_number(
            "unit %s minimum_clearance_mm" % unit_id,
            record.get("minimum_clearance_mm"),
        ),
    }


def check_coverage(record):
    """Findings about how much of the interior the views actually saw."""
    norm = validate_radiograph(record)
    if norm["views_taken"] < required_views(norm["build_style"]):
        return ["fewer-views-than-the-build-style-requires"]
    return []


def check_image_quality(record):
    """Findings about whether the image could resolve anything useful."""
    norm = validate_radiograph(record)
    findings = []
    thickness = stack_thickness_mm(norm["layers"])
    quality = image_quality_percent(norm["smallest_detail_mm"], thickness)
    if quality > MAX_IMAGE_QUALITY_PERCENT + COMPARISON_TOLERANCE:
        findings.append("image-quality-coarser-than-the-requirement")
    low, high = USABLE_TRANSMISSION_BAND
    transmission = transmitted_fraction(norm["layers"])
    if not (
        low * (1.0 - COMPARISON_TOLERANCE)
        <= transmission
        <= high * (1.0 + COMPARISON_TOLERANCE)
    ):
        findings.append("beam-transmission-outside-the-usable-band")
    return findings


def check_voids(record):
    """Findings about the voiding seen in the attachment."""
    norm = validate_radiograph(record)
    findings = []
    total = void_area_fraction(norm["void_areas_mm2"], norm["bond_area_mm2"])
    if total > MAX_TOTAL_VOID_FRACTION + COMPARISON_TOLERANCE:
        findings.append("total-void-area-above-the-limit")
    largest = largest_void_fraction(norm["void_areas_mm2"], norm["bond_area_mm2"])
    if largest > MAX_SINGLE_VOID_FRACTION + COMPARISON_TOLERANCE:
        findings.append("single-void-above-the-limit")
    active = norm["void_under_active_area_mm2"] / norm["bond_area_mm2"]
    if active > MAX_ACTIVE_AREA_VOID_FRACTION + COMPARISON_TOLERANCE:
        findings.append("void-under-the-active-area-above-the-limit")
    return findings


def check_foreign_material(record):
    """Findings about loose material seen inside the cavity."""
    norm = validate_radiograph(record)
    if norm["particle_dimension_mm"] == 0.0:
        return []
    if particle_can_bridge(
        norm["particle_dimension_mm"], norm["conductor_spacing_mm"]
    ):
        return ["foreign-material-can-bridge-the-conductor-spacing"]
    return []


def check_element_placement(record):
    """Findings about an element sitting away from its intended place."""
    norm = validate_radiograph(record)
    remaining = clearance_after_offset(
        norm["nominal_clearance_mm"], norm["element_offset_mm"]
    )
    if remaining < norm["minimum_clearance_mm"] * (1.0 - COMPARISON_TOLERANCE):
        return ["element-offset-closes-the-minimum-clearance"]
    return []


def assess_radiograph(record):
    """Assess one radiographic screening record against clause 10.3.10."""
    norm = validate_radiograph(record)
    findings = list(check_coverage(norm))
    findings.extend(check_image_quality(norm))
    findings.extend(check_voids(norm))
    findings.extend(check_foreign_material(norm))
    findings.extend(check_element_placement(norm))
    thickness = stack_thickness_mm(norm["layers"])
    return {
        "id": norm["id"],
        "build_style": norm["build_style"],
        "required_views": required_views(norm["build_style"]),
        "views_taken": norm["views_taken"],
        "stack_thickness_mm": thickness,
        "transmitted_fraction": transmitted_fraction(norm["layers"]),
        "image_quality_percent": image_quality_percent(
            norm["smallest_detail_mm"], thickness
        ),
        "total_void_fraction": void_area_fraction(
            norm["void_areas_mm2"], norm["bond_area_mm2"]
        ),
        "largest_void_fraction": largest_void_fraction(
            norm["void_areas_mm2"], norm["bond_area_mm2"]
        ),
        "remaining_clearance_mm": clearance_after_offset(
            norm["nominal_clearance_mm"], norm["element_offset_mm"]
        ),
        "findings": findings,
        "disposition": FAIL if findings else PASS,
    }


def assess_radiographic_lot(records):
    """Run the clause 10.3.10 inspection over a lot of packages."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_radiograph(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if r["disposition"] == FAIL]
    return {
        "units": results,
        "accepted_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "rejected_ids": rejected,
        "worst_void_fraction": max(r["total_void_fraction"] for r in results),
        "reject_fraction": len(rejected) / len(results),
        "lot_accepted": not rejected,
    }


def grouped_findings(records):
    """Findings across a lot, grouped by the unit that carried them."""
    report = assess_radiographic_lot(records)
    grouped = {}
    for unit in report["units"]:
        if unit["findings"]:
            grouped[unit["id"]] = list(unit["findings"])
    return grouped
