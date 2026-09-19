"""Identification and marking of delivered mechanism hardware and its parts.

Anchor: ECSS-E-ST-33-01 clause 4.2.4.1 -- delivered mechanism hardware, its
parts and its subassemblies are identified and marked. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each hardware item: part number, serial number where the item is
   delivered, surface finish, the marking field available on it, and the wall
   the marking would be applied to.
2. Build the identity string every delivered item has to carry and detect a
   repeated identity across the delivery.
3. Size the character height the marking field can actually support for the
   identity that has to fit on it.
4. Decide which marking methods the item permits: a finish the method does not
   suit, or a penetration deep relative to the wall, rules a method out.
5. Route the item to the most durable permitted method that fits, or to an
   attached tag when nothing direct does, and report the items that cannot be
   identified at all.
6. Check subassembly traceability: every declared parent exists and is itself
   an identified item.
"""

import math

__all__ = [
    "MARKING_METHODS",
    "METHOD_PREFERENCE",
    "SURFACE_FINISHES",
    "MAX_PENETRATION_FRACTION",
    "DEFAULT_ASPECT_RATIO",
    "HEIGHT_TOLERANCE",
    "validate_item",
    "identity_string",
    "achievable_character_height_mm",
    "method_is_permitted",
    "select_marking_route",
    "duplicate_identities",
    "traceability_findings",
    "assess_marking_plan",
]

# Surface finishes the marking decision distinguishes.
SURFACE_FINISHES = (
    "bare-metal",
    "anodized",
    "painted",
    "composite",
    "polymer",
)

# Marking methods, with the smallest character each reliably produces, the
# depth it drives into the surface, the finishes it suits, and whether it
# consumes the part's own marking field.
MARKING_METHODS = {
    "laser-engraving": {
        "min_character_height_mm": 0.8,
        "penetration_mm": 0.05,
        "allowed_finishes": frozenset({"bare-metal", "anodized"}),
        "uses_part_surface": True,
    },
    "electrochemical-etch": {
        "min_character_height_mm": 1.0,
        "penetration_mm": 0.03,
        "allowed_finishes": frozenset({"bare-metal"}),
        "uses_part_surface": True,
    },
    "impact-stamping": {
        "min_character_height_mm": 2.0,
        "penetration_mm": 0.15,
        "allowed_finishes": frozenset({"bare-metal"}),
        "uses_part_surface": True,
    },
    "ink-marking": {
        "min_character_height_mm": 1.5,
        "penetration_mm": 0.0,
        "allowed_finishes": frozenset(SURFACE_FINISHES),
        "uses_part_surface": True,
    },
    "adhesive-label": {
        "min_character_height_mm": 2.5,
        "penetration_mm": 0.0,
        "allowed_finishes": frozenset(SURFACE_FINISHES),
        "uses_part_surface": False,
    },
    "attached-tag": {
        "min_character_height_mm": 3.0,
        "penetration_mm": 0.0,
        "allowed_finishes": frozenset(SURFACE_FINISHES),
        "uses_part_surface": False,
    },
}

# Most durable first: a method earlier in this order is chosen whenever it is
# permitted and the identity fits in the field at its minimum character height.
METHOD_PREFERENCE = (
    "laser-engraving",
    "electrochemical-etch",
    "impact-stamping",
    "ink-marking",
    "adhesive-label",
    "attached-tag",
)

# A marking may not eat more than this fraction of the wall it sits on.
MAX_PENETRATION_FRACTION = 0.10

# Character width as a fraction of character height, for field sizing.
DEFAULT_ASPECT_RATIO = 0.6

# Heights that should land exactly on a minimum land a few ULPs off it.
HEIGHT_TOLERANCE = 1.0e-9


def _require_text(value, label):
    """Return a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_positive(value, label):
    """Return a strictly positive finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def validate_item(item):
    """Return a validated hardware item record.

    item keys: id, part_number, surface_finish, marking_area_mm2,
    wall_thickness_mm, delivered; serial_number required when delivered;
    optional parent_id and fracture_critical.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("id", "part_number", "surface_finish", "marking_area_mm2",
                "wall_thickness_mm", "delivered"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    delivered = item["delivered"]
    if not isinstance(delivered, bool):
        raise ValueError("'delivered' must be a boolean")
    finish = _require_text(item["surface_finish"], "surface_finish")
    if finish not in SURFACE_FINISHES:
        raise ValueError(
            "surface_finish %r is not one of %s" % (finish, ", ".join(SURFACE_FINISHES))
        )
    fracture_critical = item.get("fracture_critical", False)
    if not isinstance(fracture_critical, bool):
        raise ValueError("'fracture_critical' must be a boolean")
    serial = item.get("serial_number")
    if delivered:
        serial = _require_text(serial, "serial_number of a delivered item")
    elif serial is not None:
        serial = _require_text(serial, "serial_number")
    parent = item.get("parent_id")
    if parent is not None:
        parent = _require_text(parent, "parent_id")
    return {
        "id": _require_text(item["id"], "item id"),
        "part_number": _require_text(item["part_number"], "part_number"),
        "serial_number": serial,
        "surface_finish": finish,
        "marking_area_mm2": _require_positive(item["marking_area_mm2"], "marking_area_mm2"),
        "wall_thickness_mm": _require_positive(item["wall_thickness_mm"], "wall_thickness_mm"),
        "delivered": delivered,
        "fracture_critical": fracture_critical,
        "parent_id": parent,
    }


def identity_string(item):
    """Return the identity a delivered item has to carry."""
    record = validate_item(item)
    if record["serial_number"] is None:
        return record["part_number"]
    return "%s/%s" % (record["part_number"], record["serial_number"])


def achievable_character_height_mm(marking_area_mm2, character_count,
                                   aspect_ratio=DEFAULT_ASPECT_RATIO, rows=1):
    """Return the character height a marking field supports for an identity.

    The field is taken as a rectangle whose area is shared by the characters,
    each of width aspect_ratio times its height, laid out in the given rows.
    """
    area = _require_positive(marking_area_mm2, "marking_area_mm2")
    if isinstance(character_count, bool) or not isinstance(character_count, int):
        raise ValueError("character_count must be an integer")
    if character_count <= 0:
        raise ValueError("character_count must be positive, got %d" % character_count)
    if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
        raise ValueError("rows must be a positive integer, got %r" % (rows,))
    aspect = _require_positive(aspect_ratio, "aspect_ratio")
    per_row = math.ceil(character_count / float(rows))
    return math.sqrt(area / (per_row * rows * aspect))


def method_is_permitted(method, item):
    """Return (permitted, reason) for a marking method on a hardware item."""
    if method not in MARKING_METHODS:
        raise ValueError(
            "unknown marking method %r; known methods are %s"
            % (method, ", ".join(sorted(MARKING_METHODS)))
        )
    record = validate_item(item)
    spec = MARKING_METHODS[method]
    if record["surface_finish"] not in spec["allowed_finishes"]:
        return (False, "%s does not suit a %s surface" % (method, record["surface_finish"]))
    penetration = spec["penetration_mm"]
    if penetration > 0.0:
        if record["fracture_critical"]:
            return (False, "%s raises a stress concentration on a fracture-critical item"
                    % method)
        allowance = MAX_PENETRATION_FRACTION * record["wall_thickness_mm"]
        if penetration > allowance and not math.isclose(
            penetration, allowance, rel_tol=0.0, abs_tol=HEIGHT_TOLERANCE
        ):
            return (False, "%s drives %.3f mm into a %.3f mm wall"
                    % (method, penetration, record["wall_thickness_mm"]))
    return (True, "%s is permitted" % method)


def select_marking_route(item, rows=1):
    """Return the marking route for one item: method, height and reasons."""
    record = validate_item(item)
    identity = identity_string(item)
    achievable = achievable_character_height_mm(
        record["marking_area_mm2"], len(identity), rows=rows
    )
    rejected = []
    for method in METHOD_PREFERENCE:
        permitted, reason = method_is_permitted(method, item)
        if not permitted:
            rejected.append(reason)
            continue
        spec = MARKING_METHODS[method]
        minimum = spec["min_character_height_mm"]
        if spec["uses_part_surface"]:
            fits = achievable > minimum or math.isclose(
                achievable, minimum, rel_tol=0.0, abs_tol=HEIGHT_TOLERANCE
            )
            if not fits:
                rejected.append(
                    "%s needs %.2f mm characters; the field supports %.2f mm"
                    % (method, minimum, achievable)
                )
                continue
        return {
            "id": record["id"],
            "identity": identity,
            "method": method,
            "direct": spec["uses_part_surface"],
            "achievable_character_height_mm": achievable,
            "required_character_height_mm": minimum,
            "rejected": rejected,
        }
    return {
        "id": record["id"],
        "identity": identity,
        "method": None,
        "direct": False,
        "achievable_character_height_mm": achievable,
        "required_character_height_mm": None,
        "rejected": rejected,
    }


def duplicate_identities(items):
    """Return the identities carried by more than one delivered item."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    seen = {}
    for item in items:
        record = validate_item(item)
        if not record["delivered"]:
            continue
        identity = identity_string(item)
        seen[identity] = seen.get(identity, 0) + 1
    return sorted(identity for identity, count in seen.items() if count > 1)


def traceability_findings(items):
    """Return findings about parents that are missing or not themselves identified."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    records = [validate_item(item) for item in items]
    by_id = {record["id"]: record for record in records}
    if len(by_id) != len(records):
        raise ValueError("the item list repeats an identifier")
    findings = []
    for record in records:
        parent = record["parent_id"]
        if parent is None:
            continue
        if parent == record["id"]:
            findings.append("item %s is declared its own parent" % record["id"])
            continue
        if parent not in by_id:
            findings.append(
                "item %s names parent %s, which is not in the delivery"
                % (record["id"], parent)
            )
            continue
        if by_id[parent]["serial_number"] is None:
            findings.append(
                "item %s hangs off parent %s, which carries no serial number"
                % (record["id"], parent)
            )
    return findings


def assess_marking_plan(items, rows=1):
    """Assess the identification and marking plan for a delivery."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    routes = [select_marking_route(item, rows) for item in items]
    findings = []
    for identity in duplicate_identities(items):
        findings.append("identity %s is carried by more than one delivered item" % identity)
    findings.extend(traceability_findings(items))
    for route in routes:
        if route["method"] is None:
            findings.append(
                "item %s cannot be identified by any permitted method" % route["id"]
            )
        elif not route["direct"]:
            findings.append(
                "item %s falls back to %s; direct marking is not available on it"
                % (route["id"], route["method"])
            )
    direct_count = sum(1 for route in routes if route["direct"])
    return {
        "routes": routes,
        "item_count": len(routes),
        "direct_marked_count": direct_count,
        "direct_fraction": direct_count / float(len(routes)),
        "findings": findings,
        "compliant": not findings,
    }
