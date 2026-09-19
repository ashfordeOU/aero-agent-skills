"""Preliminary component detail specification at the end of layout.

Anchor: ECSS-E-ST-20-40C clause 5.6.7 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Decide whether the device owes an early component specification at
   all. The obligation follows the procurement route: a packaged
   device headed for formal evaluation owes one, an application-
   specific device or a core delivered as source does not.
2. Grade the draft against the content blocks a procurement-grade
   specification has to carry, each block present, drafted or absent.
3. Check every electrical characteristic carries a bound, a test
   condition and a temperature; any one missing makes the number
   unreproducible by the evaluation house.
4. Check the rating envelope: the recommended operating range has to
   sit inside the absolute maximum ratings, with a coincident bound
   reported rather than passed.
5. Report readiness as present blocks over required blocks with the
   open blocks named.

Stdlib only, offline, deterministic.
"""

import math

ROUTE_FORMAL_EVALUATION = "formal-part-evaluation"
ROUTE_APPLICATION_SPECIFIC = "application-specific-single-use"
ROUTE_SOURCE_DELIVERY = "source-delivery-no-package"
VALID_ROUTES = (
    ROUTE_FORMAL_EVALUATION,
    ROUTE_APPLICATION_SPECIFIC,
    ROUTE_SOURCE_DELIVERY,
)

DEVICE_KIND_ASIC = "asic"
DEVICE_KIND_FPGA = "fpga"
DEVICE_KIND_IP_CORE = "ip-core"
VALID_DEVICE_KINDS = (DEVICE_KIND_ASIC, DEVICE_KIND_FPGA, DEVICE_KIND_IP_CORE)

# A core delivered as source has no package, no terminals and no
# marking, so no component detail specification can describe it.
UNPACKAGED_DEVICE_KINDS = (DEVICE_KIND_IP_CORE,)

REQUIRED_BLOCKS = (
    "device-identification-and-variants",
    "terminal-identification",
    "absolute-maximum-ratings",
    "recommended-operating-conditions",
    "electrical-characteristics",
    "test-and-screening-list",
    "marking-and-traceability",
    "package-outline",
)

BLOCK_PRESENT = "present"
BLOCK_DRAFTED = "drafted"
BLOCK_ABSENT = "absent"
VALID_BLOCK_STATES = (BLOCK_PRESENT, BLOCK_DRAFTED, BLOCK_ABSENT)

DIRECTION_UPPER_BOUND = "upper-bound"
DIRECTION_LOWER_BOUND = "lower-bound"
VALID_DIRECTIONS = (DIRECTION_UPPER_BOUND, DIRECTION_LOWER_BOUND)

# A rating pair read off two documents can differ by a few units in
# the last place when it was meant to coincide; this relative
# tolerance reports that case as coincident instead of as clearance.
RELATIVE_TOLERANCE = 1.0e-9

OWED = "specification-owed"
NOT_OWED = "specification-not-owed"

FINDING_BLOCK_DRAFTED = "content-block-still-in-draft"
FINDING_BLOCK_ABSENT = "content-block-absent"
FINDING_NO_TEST_CONDITION = "characteristic-without-a-test-condition"
FINDING_NO_TEMPERATURE = "characteristic-without-a-stated-temperature"
FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE = (
    "recommended-operating-range-outside-the-absolute-maximum-ratings"
)
FINDING_OPERATING_RANGE_COINCIDENT = (
    "recommended-operating-bound-coincident-with-an-absolute-maximum"
)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _close(a, b):
    scale = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= RELATIVE_TOLERANCE * scale


def validate_device(device):
    """Validate the device record and return a normalized copy."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    device_id = _text("device id", device.get("id"))
    kind = device.get("kind")
    if kind not in VALID_DEVICE_KINDS:
        raise ValueError(
            "device %s has unknown kind %r (expected one of %s)"
            % (device_id, kind, ", ".join(VALID_DEVICE_KINDS))
        )
    route = device.get("route")
    if route not in VALID_ROUTES:
        raise ValueError(
            "device %s has unknown route %r (expected one of %s)"
            % (device_id, route, ", ".join(VALID_ROUTES))
        )
    return {"id": device_id, "kind": kind, "route": route}


def specification_owed(device):
    """Return (status, reason) for the clause 5.6.7 obligation."""
    norm = validate_device(device)
    if norm["kind"] in UNPACKAGED_DEVICE_KINDS:
        return NOT_OWED, "delivered-as-source-with-no-package"
    if norm["route"] != ROUTE_FORMAL_EVALUATION:
        return NOT_OWED, "not-routed-to-formal-part-evaluation"
    return OWED, "packaged-device-routed-to-formal-part-evaluation"


def validate_block_map(blocks):
    """Validate the content-block state map and normalize it."""
    if not isinstance(blocks, dict) or not blocks:
        raise ValueError("blocks must be a non-empty mapping")
    normalized = {}
    for name, state in blocks.items():
        block = _text("block name", name)
        if block not in REQUIRED_BLOCKS:
            raise ValueError(
                "unknown content block %r (expected one of %s)"
                % (block, ", ".join(REQUIRED_BLOCKS))
            )
        if state not in VALID_BLOCK_STATES:
            raise ValueError(
                "block %s has unknown state %r (expected one of %s)"
                % (block, state, ", ".join(VALID_BLOCK_STATES))
            )
        normalized[block] = state
    return normalized


def block_findings(blocks):
    """Findings for every required block that is not present."""
    normalized = validate_block_map(blocks)
    findings = []
    for block in REQUIRED_BLOCKS:
        state = normalized.get(block, BLOCK_ABSENT)
        if state == BLOCK_DRAFTED:
            findings.append((block, FINDING_BLOCK_DRAFTED))
        elif state == BLOCK_ABSENT:
            findings.append((block, FINDING_BLOCK_ABSENT))
    return findings


def readiness_fraction(blocks):
    """Fraction of the required content blocks that are present."""
    normalized = validate_block_map(blocks)
    present = sum(
        1 for block in REQUIRED_BLOCKS if normalized.get(block) == BLOCK_PRESENT
    )
    return present / len(REQUIRED_BLOCKS)


def validate_characteristic(characteristic):
    """Validate one electrical characteristic entry and normalize it."""
    if not isinstance(characteristic, dict):
        raise ValueError("characteristic must be a mapping")
    name = _text("characteristic id", characteristic.get("id"))
    direction = characteristic.get("direction")
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            "characteristic %s has unknown direction %r" % (name, direction)
        )
    limit = _finite("characteristic %s limit" % name, characteristic.get("limit"))
    unit = _text("characteristic %s unit" % name, characteristic.get("unit"))
    condition = characteristic.get("test_condition")
    if condition is not None:
        condition = _text("characteristic %s test_condition" % name, condition)
    temperature = characteristic.get("temperature_c")
    if temperature is not None:
        temperature = _finite("characteristic %s temperature_c" % name, temperature)
    return {
        "id": name,
        "direction": direction,
        "limit": limit,
        "unit": unit,
        "test_condition": condition,
        "temperature_c": temperature,
    }


def characteristic_findings(characteristic):
    """Findings about the reproducibility of one characteristic."""
    norm = validate_characteristic(characteristic)
    findings = []
    if norm["test_condition"] is None:
        findings.append(FINDING_NO_TEST_CONDITION)
    if norm["temperature_c"] is None:
        findings.append(FINDING_NO_TEMPERATURE)
    return findings


def validate_rating(rating):
    """Validate one absolute-maximum / recommended-operating pair."""
    if not isinstance(rating, dict):
        raise ValueError("rating must be a mapping")
    name = _text("rating id", rating.get("id"))
    absolute_min = _finite("rating %s absolute_min" % name, rating.get("absolute_min"))
    absolute_max = _finite("rating %s absolute_max" % name, rating.get("absolute_max"))
    if absolute_max <= absolute_min:
        raise ValueError(
            "rating %s has absolute_max %r not above absolute_min %r"
            % (name, absolute_max, absolute_min)
        )
    operating_min = _finite(
        "rating %s operating_min" % name, rating.get("operating_min")
    )
    operating_max = _finite(
        "rating %s operating_max" % name, rating.get("operating_max")
    )
    if operating_max < operating_min:
        raise ValueError(
            "rating %s has operating_max %r below operating_min %r"
            % (name, operating_max, operating_min)
        )
    return {
        "id": name,
        "absolute_min": absolute_min,
        "absolute_max": absolute_max,
        "operating_min": operating_min,
        "operating_max": operating_max,
    }


def rating_findings(rating):
    """Findings about one recommended-operating / absolute-maximum pair."""
    norm = validate_rating(rating)
    findings = []
    for operating, absolute, outside in (
        (norm["operating_min"], norm["absolute_min"], norm["operating_min"] < norm["absolute_min"]),
        (norm["operating_max"], norm["absolute_max"], norm["operating_max"] > norm["absolute_max"]),
    ):
        if _close(operating, absolute):
            findings.append(FINDING_OPERATING_RANGE_COINCIDENT)
        elif outside:
            findings.append(FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE)
    return findings


def assess_preliminary_escc_detail_specification(
    device, blocks=None, characteristics=None, ratings=None
):
    """Assess the clause 5.6.7 draft for one device."""
    norm_device = validate_device(device)
    status, reason = specification_owed(norm_device)
    if status == NOT_OWED:
        return {
            "device_id": norm_device["id"],
            "status": status,
            "status_reason": reason,
            "readiness": None,
            "open_blocks": [],
            "findings": [],
            "review_ready": True,
        }
    if blocks is None:
        raise ValueError(
            "device %s owes a specification, so a block map is required"
            % norm_device["id"]
        )
    characteristics = [] if characteristics is None else characteristics
    ratings = [] if ratings is None else ratings
    if not isinstance(characteristics, list):
        raise ValueError("characteristics must be a list")
    if not isinstance(ratings, list):
        raise ValueError("ratings must be a list")
    findings = list(block_findings(blocks))
    seen = set()
    for characteristic in characteristics:
        norm = validate_characteristic(characteristic)
        if norm["id"] in seen:
            raise ValueError("duplicate characteristic id %r" % (norm["id"],))
        seen.add(norm["id"])
        for name in characteristic_findings(norm):
            findings.append((norm["id"], name))
    seen_ratings = set()
    for rating in ratings:
        norm = validate_rating(rating)
        if norm["id"] in seen_ratings:
            raise ValueError("duplicate rating id %r" % (norm["id"],))
        seen_ratings.add(norm["id"])
        for name in rating_findings(norm):
            findings.append((norm["id"], name))
    normalized_blocks = validate_block_map(blocks)
    open_blocks = [
        block
        for block in REQUIRED_BLOCKS
        if normalized_blocks.get(block, BLOCK_ABSENT) != BLOCK_PRESENT
    ]
    return {
        "device_id": norm_device["id"],
        "status": status,
        "status_reason": reason,
        "readiness": readiness_fraction(blocks),
        "open_blocks": open_blocks,
        "findings": findings,
        "review_ready": not findings,
    }
