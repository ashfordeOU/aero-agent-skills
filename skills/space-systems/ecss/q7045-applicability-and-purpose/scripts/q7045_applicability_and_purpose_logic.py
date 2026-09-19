"""Scope and purpose of a metallic-material mechanical test campaign.

Anchor: ECSS-Q-ST-70-45C, framework/scope clause (mechanical test methods for
metallic materials, run to qualify a material or to generate design data).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the product is a metallic product form the standard covers.
2. Sort the requested properties into the mechanical set the standard covers
   and an explicit out-of-scope remainder.
3. Read the declared purpose of the campaign and take the minimum number of
   valid test pieces owed per matrix cell from it.
4. Expand the test matrix as property x orientation x temperature, count the
   valid test pieces assigned to each cell, and report empty and short cells
   separately.
5. For design-allowable generation, check heat coverage as well as count.
"""

import math

__all__ = [
    "MECHANICAL_PROPERTIES",
    "NON_MECHANICAL_PROPERTIES",
    "METALLIC_FAMILIES",
    "NON_METALLIC_FAMILIES",
    "PURPOSE_MINIMUM_PIECES",
    "DESIGN_ALLOWABLE_MINIMUM_HEATS",
    "in_scope_material",
    "partition_properties",
    "minimum_pieces_for_purpose",
    "expand_matrix",
    "valid_pieces",
    "cell_coverage",
    "heat_coverage",
    "assess_campaign",
]

# Mechanical behaviour of a metallic product form, covered by the standard.
MECHANICAL_PROPERTIES = frozenset(
    {
        "tensile",
        "compression",
        "shear",
        "bearing",
        "fracture-toughness",
        "fatigue",
        "creep",
        "stress-rupture",
    }
)

# Properties of a metallic product that are real but belong to other documents.
NON_MECHANICAL_PROPERTIES = frozenset(
    {
        "density",
        "thermal-expansion",
        "thermal-conductivity",
        "electrical-resistivity",
        "corrosion-resistance",
        "outgassing",
        "magnetic-permeability",
    }
)

METALLIC_FAMILIES = frozenset(
    {
        "aluminium-alloy",
        "titanium-alloy",
        "steel",
        "stainless-steel",
        "nickel-alloy",
        "copper-alloy",
        "magnesium-alloy",
        "beryllium-alloy",
        "refractory-alloy",
        "metal-matrix-composite",
    }
)

NON_METALLIC_FAMILIES = frozenset(
    {
        "polymer",
        "elastomer",
        "ceramic",
        "glass",
        "carbon-fibre-laminate",
        "glass-fibre-laminate",
        "bonded-assembly",
        "adhesive",
    }
)

# Minimum valid test pieces owed per matrix cell, by declared purpose. A lot
# decision closes on few pieces; a design allowable has to carry a basis.
PURPOSE_MINIMUM_PIECES = {
    "design-allowable": 9,
    "qualification": 5,
    "lot-acceptance": 3,
    "process-verification": 2,
}

# A multi-heat statistical basis cannot be drawn from a single melt.
DESIGN_ALLOWABLE_MINIMUM_HEATS = 3


def _require_text(value, label):
    """Return a stripped, lower-cased token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def in_scope_material(material_family, product_form=None):
    """Return the scope decision for a material family and product form."""
    family = _require_text(material_family, "material_family")
    reasons = []
    if family in NON_METALLIC_FAMILIES:
        reasons.append(
            "%s is not a metallic product form; it is tested under its own document"
            % family
        )
        return {"family": family, "in_scope": False, "reasons": reasons}
    if family not in METALLIC_FAMILIES:
        raise ValueError(
            "material_family %r is on neither the metallic nor the non-metallic "
            "list; place it on one before scoping the campaign" % family
        )
    if family == "metal-matrix-composite":
        form = _require_text(product_form or "", "product_form") if product_form else ""
        if not form:
            raise ValueError(
                "a metal-matrix-composite needs a declared product_form before "
                "its scope can be decided"
            )
        reasons.append(
            "metal-matrix-composite admitted on the declared metallic product form %s"
            % form
        )
    else:
        reasons.append("%s is a metallic product form covered by the standard" % family)
    return {"family": family, "in_scope": True, "reasons": reasons}


def partition_properties(requested):
    """Split requested properties into the covered set and the remainder."""
    if not isinstance(requested, (list, tuple)) or not requested:
        raise ValueError("requested properties must be a non-empty sequence")
    covered = []
    out_of_scope = []
    seen = set()
    for item in requested:
        token = _require_text(item, "requested property")
        if token in seen:
            continue
        seen.add(token)
        if token in MECHANICAL_PROPERTIES:
            covered.append(token)
        elif token in NON_MECHANICAL_PROPERTIES:
            out_of_scope.append(token)
        else:
            raise ValueError(
                "property %r is on neither the mechanical nor the "
                "non-mechanical list; place it on one" % token
            )
    return {"covered": sorted(covered), "out_of_scope": sorted(out_of_scope)}


def minimum_pieces_for_purpose(purpose):
    """Return the minimum valid test pieces owed per matrix cell."""
    token = _require_text(purpose, "purpose")
    if token not in PURPOSE_MINIMUM_PIECES:
        raise ValueError(
            "purpose %r is not one of %s"
            % (token, ", ".join(sorted(PURPOSE_MINIMUM_PIECES)))
        )
    return PURPOSE_MINIMUM_PIECES[token]


def _validate_temperature(value):
    """Return a validated test temperature in degrees Celsius."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("test temperature must be a real number, got %r" % (value,))
    temperature = float(value)
    if not math.isfinite(temperature):
        raise ValueError("test temperature must be finite")
    if temperature < -273.15:
        raise ValueError(
            "test temperature %g degC is below absolute zero" % temperature
        )
    return temperature


def expand_matrix(properties, orientations, temperatures_c):
    """Return the sorted property/orientation/temperature cells the plan owes."""
    if not isinstance(properties, (list, tuple)) or not properties:
        raise ValueError("properties must be a non-empty sequence")
    if not isinstance(orientations, (list, tuple)) or not orientations:
        raise ValueError("orientations must be a non-empty sequence")
    if not isinstance(temperatures_c, (list, tuple)) or not temperatures_c:
        raise ValueError("temperatures_c must be a non-empty sequence")
    props = sorted({_require_text(p, "property") for p in properties})
    orients = sorted({_require_text(o, "orientation") for o in orientations})
    temps = sorted({_validate_temperature(t) for t in temperatures_c})
    return [(p, o, t) for p in props for o in orients for t in temps]


def valid_pieces(pieces):
    """Return only the test-piece records marked valid, grouped by cell."""
    if not isinstance(pieces, (list, tuple)):
        raise ValueError("pieces must be a sequence of test-piece records")
    grouped = {}
    for index, piece in enumerate(pieces):
        if not isinstance(piece, dict):
            raise ValueError("piece[%d] must be a mapping" % index)
        for key in ("property", "orientation", "temperature_c"):
            if key not in piece:
                raise ValueError("piece[%d] missing required key '%s'" % (index, key))
        if "valid" in piece and not isinstance(piece["valid"], bool):
            raise ValueError("piece[%d] 'valid' must be a boolean" % index)
        if not piece.get("valid", True):
            continue
        cell = (
            _require_text(piece["property"], "piece property"),
            _require_text(piece["orientation"], "piece orientation"),
            _validate_temperature(piece["temperature_c"]),
        )
        grouped.setdefault(cell, []).append(piece)
    return grouped


def cell_coverage(cells, pieces, minimum):
    """Return per-cell counts plus the empty and short cell lists."""
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("minimum must be a positive integer, got %r" % (minimum,))
    grouped = valid_pieces(pieces)
    counts = {}
    empty = []
    short = []
    for cell in cells:
        count = len(grouped.get(cell, ()))
        counts[cell] = count
        if count == 0:
            empty.append(cell)
        elif count < minimum:
            short.append(cell)
    unplanned = sorted(set(grouped) - set(cells))
    return {
        "counts": counts,
        "empty_cells": empty,
        "short_cells": short,
        "unplanned_cells": unplanned,
    }


def heat_coverage(pieces):
    """Return the distinct heat identifiers behind the valid test pieces."""
    grouped = valid_pieces(pieces)
    heats = set()
    missing = 0
    for records in grouped.values():
        for record in records:
            heat = record.get("heat_id")
            if heat is None or (isinstance(heat, str) and not heat.strip()):
                missing += 1
                continue
            heats.add(_require_text(heat, "heat_id"))
    return {"heats": sorted(heats), "pieces_without_heat": missing}


def assess_campaign(spec):
    """Run the full scope-and-completeness assessment of a test campaign.

    spec keys: material_family, optional product_form, requested_properties,
    purpose, orientations, temperatures_c, pieces.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "material_family",
        "requested_properties",
        "purpose",
        "orientations",
        "temperatures_c",
        "pieces",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    material = in_scope_material(spec["material_family"], spec.get("product_form"))
    findings = []
    if not material["in_scope"]:
        return {
            "material": material,
            "in_scope": False,
            "status": "out-of-scope",
            "findings": list(material["reasons"]),
        }

    split = partition_properties(spec["requested_properties"])
    if split["out_of_scope"]:
        findings.append(
            "requested properties outside this standard: %s"
            % ", ".join(split["out_of_scope"])
        )
    if not split["covered"]:
        return {
            "material": material,
            "in_scope": False,
            "status": "out-of-scope",
            "properties": split,
            "findings": findings
            + ["no requested property is a mechanical property of the product"],
        }

    purpose = _require_text(spec["purpose"], "purpose")
    minimum = minimum_pieces_for_purpose(purpose)
    cells = expand_matrix(
        split["covered"], spec["orientations"], spec["temperatures_c"]
    )
    coverage = cell_coverage(cells, spec["pieces"], minimum)
    if coverage["empty_cells"]:
        findings.append(
            "%d matrix cell(s) have no valid test piece" % len(coverage["empty_cells"])
        )
    if coverage["short_cells"]:
        findings.append(
            "%d matrix cell(s) hold fewer than the %d valid pieces the %s purpose owes"
            % (len(coverage["short_cells"]), minimum, purpose)
        )
    if coverage["unplanned_cells"]:
        findings.append(
            "%d valid piece group(s) sit outside the declared matrix"
            % len(coverage["unplanned_cells"])
        )

    heats = heat_coverage(spec["pieces"])
    if purpose == "design-allowable":
        if heats["pieces_without_heat"]:
            findings.append(
                "%d valid piece(s) carry no heat identifier, so the multi-heat "
                "basis cannot be demonstrated" % heats["pieces_without_heat"]
            )
        if len(heats["heats"]) < DESIGN_ALLOWABLE_MINIMUM_HEATS:
            findings.append(
                "design-allowable generation draws on %d heat(s); at least %d are "
                "needed for a multi-heat basis"
                % (len(heats["heats"]), DESIGN_ALLOWABLE_MINIMUM_HEATS)
            )

    complete = not (
        coverage["empty_cells"]
        or coverage["short_cells"]
        or (
            purpose == "design-allowable"
            and (
                len(heats["heats"]) < DESIGN_ALLOWABLE_MINIMUM_HEATS
                or heats["pieces_without_heat"]
            )
        )
    )
    status = "in-scope-complete" if complete else "in-scope-incomplete"
    return {
        "material": material,
        "in_scope": True,
        "properties": split,
        "purpose": purpose,
        "minimum_pieces_per_cell": minimum,
        "cells": cells,
        "coverage": coverage,
        "heat_coverage": heats,
        "complete": complete,
        "status": status,
        "findings": findings,
    }
