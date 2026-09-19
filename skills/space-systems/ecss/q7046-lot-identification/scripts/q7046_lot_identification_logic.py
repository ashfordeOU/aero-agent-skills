"""Lot identification for threaded fasteners: marking, traceability, packaging.

Anchor: ECSS-Q-ST-70-46, manufacturing clause, identification and
packaging (paraphrased into an implementable procedure; no standard
text is reproduced).

Procedure implemented here:

1. A lot identifier is composed, not written. It carries the
   manufacturer code, the part code, the material heat, the
   heat-treatment charge and the date code, each drawn from a
   restricted character set, so two lots can never collide and an
   identifier can be taken apart again by whoever reads it.
2. Marking is bounded by the part, not by the wish list. A hexagon
   head offers an area that follows from its width across flats, only
   part of it is usable once the edges and any recess are allowed
   for, and the number of characters that area holds follows from the
   character height. Where the required marking does not fit, it
   moves to the package and that move is recorded.
3. Marking is also bounded by depth and by location. A stamp deeper
   than a fraction of the head height is a notch, and marking placed
   on the shank or the thread run-out of a fatigue-critical part puts
   that notch exactly where the part is worked hardest.
4. Traceability is a chain, and a chain is only as good as its
   weakest link. Every required link from the melt to the delivered
   package has to be present and non-empty; one gap makes the lot
   untraceable, whatever the other links prove.
5. A package holds one production lot. Two lot codes in one package
   is a segregation failure that no downstream inspection can undo,
   because the evidence for each part has already been mixed.

Stdlib only, offline, deterministic.
"""

ACCEPTED = "accepted"
ACCEPTED_WITH_ACTIONS = "accepted-with-actions"
REJECTED = "rejected"

_RANK = {ACCEPTED: 0, ACCEPTED_WITH_ACTIONS: 1, REJECTED: 2}

# Fields a lot identifier is composed from, in order.
IDENTIFIER_FIELDS = (
    "manufacturer_code",
    "part_code",
    "heat_number",
    "heat_treatment_charge",
    "date_code",
)

IDENTIFIER_SEPARATOR = "-"

# Character set an identifier field may use.
ALLOWED_FIELD_CHARACTERS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)

MAX_FIELD_LENGTH = 12

# Links the traceability chain must carry from melt to package.
REQUIRED_TRACEABILITY_LINKS = (
    "melt-certificate",
    "bar-lot",
    "production-lot",
    "heat-treatment-charge",
    "surface-treatment-batch",
    "package-record",
)

# Fields the package label must carry.
REQUIRED_LABEL_FIELDS = (
    "lot_identifier",
    "part_code",
    "property_class",
    "quantity",
    "date_code",
)

# Marking geometry. A regular hexagon of width across flats s has area
# sqrt(3)/2 * s squared; only part of that face is markable once the
# drive recess, the chamfer and the edge distance are allowed for.
HEXAGON_AREA_FACTOR = 0.8660254037844386
USABLE_HEAD_FRACTION = 0.35
CHARACTER_ASPECT_RATIO = 0.60

# A character occupies more than its own body: the pitch factor spaces
# it from its neighbours in both directions.
CHARACTER_PITCH_FACTOR = 1.40

# A stamp deeper than this fraction of the head height is a notch.
MARKING_DEPTH_FRACTION = 0.05

# Locations a marking may occupy.
PERMITTED_MARKING_LOCATIONS = ("head-top", "head-side", "end-face")
FATIGUE_BARRED_LOCATIONS = ("shank", "thread-run-out", "thread-flank")

# Areas and depths are products of measured floats, so a case exactly
# on a bound can land a few units in the last place outside it. These
# absorb that without moving a bound.
LENGTH_TOLERANCE_MM = 1.0e-9
AREA_TOLERANCE_MM2 = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def validate_identifier_field(name, value):
    """Validate one identifier field and return it normalized."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    normalized = value.strip().upper()
    if len(normalized) > MAX_FIELD_LENGTH:
        raise ValueError(
            "%s must be at most %d characters" % (name, MAX_FIELD_LENGTH)
        )
    bad = sorted(set(normalized) - ALLOWED_FIELD_CHARACTERS)
    if bad:
        raise ValueError(
            "%s carries characters outside the allowed set: %s" % (name, "".join(bad))
        )
    return normalized


def compose_lot_identifier(fields):
    """Compose a lot identifier from its five fields."""
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping")
    missing = [name for name in IDENTIFIER_FIELDS if name not in fields]
    if missing:
        raise ValueError("identifier is missing %s" % ", ".join(missing))
    parts = [
        validate_identifier_field(name, fields[name]) for name in IDENTIFIER_FIELDS
    ]
    return IDENTIFIER_SEPARATOR.join(parts)


def parse_lot_identifier(identifier):
    """Take a composed lot identifier apart into its five fields."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("identifier must be a non-empty string")
    parts = identifier.strip().split(IDENTIFIER_SEPARATOR)
    if len(parts) != len(IDENTIFIER_FIELDS):
        raise ValueError(
            "identifier must carry %d fields, got %d"
            % (len(IDENTIFIER_FIELDS), len(parts))
        )
    return {
        name: validate_identifier_field(name, value)
        for name, value in zip(IDENTIFIER_FIELDS, parts)
    }


def hex_head_markable_area_mm2(
    width_across_flats_mm, usable_fraction=USABLE_HEAD_FRACTION
):
    """Markable area on a hexagon head, in square millimetres."""
    width = _numeric("width_across_flats_mm", width_across_flats_mm, 0.0)
    if width <= 0.0:
        raise ValueError("width_across_flats_mm must be positive")
    fraction = _numeric("usable_fraction", usable_fraction, 0.0)
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError("usable_fraction must lie in (0, 1]")
    return HEXAGON_AREA_FACTOR * width * width * fraction


def character_cell_area_mm2(character_height_mm, aspect_ratio=CHARACTER_ASPECT_RATIO):
    """Area one character occupies including its spacing, in mm squared."""
    height = _numeric("character_height_mm", character_height_mm, 0.0)
    if height <= 0.0:
        raise ValueError("character_height_mm must be positive")
    ratio = _numeric("aspect_ratio", aspect_ratio, 0.0)
    if ratio <= 0.0:
        raise ValueError("aspect_ratio must be positive")
    pitch = CHARACTER_PITCH_FACTOR * CHARACTER_PITCH_FACTOR
    return pitch * ratio * height * height


def marking_character_capacity(
    area_mm2, character_height_mm, aspect_ratio=CHARACTER_ASPECT_RATIO
):
    """Whole characters a markable area holds at a character height."""
    area = _numeric("area_mm2", area_mm2, 0.0)
    per_character = character_cell_area_mm2(character_height_mm, aspect_ratio)
    return int((area + AREA_TOLERANCE_MM2) // per_character)


def marking_depth_limit_mm(head_height_mm, fraction=MARKING_DEPTH_FRACTION):
    """Deepest stamp a head height admits before the mark is a notch."""
    height = _numeric("head_height_mm", head_height_mm, 0.0)
    if height <= 0.0:
        raise ValueError("head_height_mm must be positive")
    limit_fraction = _numeric("fraction", fraction, 0.0)
    if limit_fraction <= 0.0:
        raise ValueError("fraction must be positive")
    return height * limit_fraction


def marking_location_admissible(location, fatigue_critical=False):
    """Whether a marking location is admissible for this duty."""
    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")
    location = location.strip()
    if location in PERMITTED_MARKING_LOCATIONS:
        return True
    if location in FATIGUE_BARRED_LOCATIONS:
        return not fatigue_critical
    raise ValueError(
        "unknown marking location %r (expected one of %s)"
        % (location, ", ".join(PERMITTED_MARKING_LOCATIONS + FATIGUE_BARRED_LOCATIONS))
    )


def traceability_gaps(chain):
    """Required traceability links a chain leaves empty or absent."""
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping")
    gaps = []
    for link in REQUIRED_TRACEABILITY_LINKS:
        value = chain.get(link)
        if not isinstance(value, str) or not value.strip():
            gaps.append(link)
    return gaps


def mixed_lot_codes(items):
    """Distinct production-lot codes found in one package."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    codes = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("every item needs a non-empty lot code")
        code = item.strip().upper()
        if code not in codes:
            codes.append(code)
    return codes


def label_gaps(label):
    """Required package-label fields a label leaves empty or absent."""
    if not isinstance(label, dict):
        raise ValueError("label must be a mapping")
    gaps = []
    for field in REQUIRED_LABEL_FIELDS:
        value = label.get(field)
        if value is None:
            gaps.append(field)
        elif isinstance(value, str) and not value.strip():
            gaps.append(field)
    return gaps


def validate_consignment(record):
    """Validate one consignment record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("consignment must be a mapping")
    identifier = compose_lot_identifier(record.get("identifier_fields", {}))
    return {
        "identifier": identifier,
        "width_across_flats_mm": _numeric(
            "width_across_flats_mm", record.get("width_across_flats_mm", 16.0), 0.0
        ),
        "head_height_mm": _numeric(
            "head_height_mm", record.get("head_height_mm", 6.4), 0.0
        ),
        "character_height_mm": _numeric(
            "character_height_mm", record.get("character_height_mm", 1.6), 0.0
        ),
        "required_marking": str(record.get("required_marking", "")).strip(),
        "marking_depth_mm": _numeric(
            "marking_depth_mm", record.get("marking_depth_mm", 0.1), 0.0
        ),
        "marking_location": record.get("marking_location", "head-top"),
        "fatigue_critical": bool(record.get("fatigue_critical", False)),
        "traceability_chain": record.get("traceability_chain", {}),
        "package_items": record.get("package_items", []),
        "package_label": record.get("package_label", {}),
    }


def assess_consignment(record):
    """Assess one consignment's identification end to end."""
    norm = validate_consignment(record)
    findings = []
    actions = []
    disposition = ACCEPTED

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    area = hex_head_markable_area_mm2(norm["width_across_flats_mm"])
    capacity = marking_character_capacity(area, norm["character_height_mm"])
    required_characters = len(norm["required_marking"].replace(" ", ""))
    marking_fits = required_characters <= capacity
    if not marking_fits:
        actions.append("move-the-surplus-marking-to-the-package")
        disposition = escalate(ACCEPTED_WITH_ACTIONS)

    depth_limit = marking_depth_limit_mm(norm["head_height_mm"])
    depth_ok = norm["marking_depth_mm"] <= depth_limit + LENGTH_TOLERANCE_MM
    if not depth_ok:
        findings.append("marking-stamped-deeper-than-the-head-admits")
        disposition = escalate(REJECTED)

    location_ok = marking_location_admissible(
        norm["marking_location"], norm["fatigue_critical"]
    )
    if not location_ok:
        findings.append("marking-placed-where-the-part-is-worked-hardest")
        disposition = escalate(REJECTED)

    gaps = traceability_gaps(norm["traceability_chain"])
    if gaps:
        findings.append("traceability-chain-broken-at-%s" % gaps[0])
        disposition = escalate(REJECTED)

    codes = mixed_lot_codes(norm["package_items"])
    if len(codes) > 1:
        findings.append("package-holds-more-than-one-production-lot")
        disposition = escalate(REJECTED)

    missing_label = label_gaps(norm["package_label"])
    if missing_label:
        findings.append("package-label-missing-%s" % missing_label[0])
        disposition = escalate(ACCEPTED_WITH_ACTIONS)
        actions.append("complete-the-package-label-before-issue")

    return {
        "identifier": norm["identifier"],
        "markable_area_mm2": area,
        "marking_capacity_characters": capacity,
        "required_marking_characters": required_characters,
        "marking_fits_on_the_head": marking_fits,
        "marking_depth_limit_mm": depth_limit,
        "marking_depth_admissible": depth_ok,
        "marking_location_admissible": location_ok,
        "traceability_gaps": gaps,
        "lot_codes_in_package": codes,
        "label_gaps": missing_label,
        "actions": actions,
        "findings": findings,
        "disposition": disposition,
    }


def assess_delivery(records):
    """Assess every consignment in a delivery and roll them up."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_consignment(record)
        if result["identifier"] in seen:
            raise ValueError("duplicate lot identifier %r" % (result["identifier"],))
        seen.add(result["identifier"])
        results.append(result)
    delivery = ACCEPTED
    for result in results:
        if _RANK[result["disposition"]] > _RANK[delivery]:
            delivery = result["disposition"]
    return {
        "consignments": results,
        "delivery_disposition": delivery,
        "rejected_lots": [
            r["identifier"] for r in results if r["disposition"] == REJECTED
        ],
        "untraceable_lots": [
            r["identifier"] for r in results if r["traceability_gaps"]
        ],
    }
