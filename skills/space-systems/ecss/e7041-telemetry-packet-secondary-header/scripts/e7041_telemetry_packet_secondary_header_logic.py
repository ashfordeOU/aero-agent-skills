"""Telemetry packet secondary header resolution for a PUS service.

Anchor: ECSS-E-ST-70-41C clause 7.4.3.1 (requirements on the telemetry packet
secondary header). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the mission-configured secondary header layout: the always-present
   fields, the optional fields the mission switched on, and the bit width of
   each, in the fixed field order.
2. Check the resolved layout lands on an octet boundary, because the user data
   field starts where the secondary header ends.
3. Validate each field value against the range its own width allows, and
   against the range the service model allows (a service type or a message
   subtype identifier of zero is not a usable identifier).
4. Pack the validated values into the layout and unpack them again, so a
   layout that cannot carry the values it was given is caught at build time.
5. Follow the message type counter per report source: a counter is a modulo
   counter, so a wrap is normal, a repeat is a duplicated report and a jump is
   a lost one, and the three are told apart rather than averaged together.
"""

__all__ = [
    "FIELD_ORDER",
    "MANDATORY_FIELDS",
    "OPTIONAL_FIELDS",
    "DEFAULT_WIDTHS_BITS",
    "PUS_C_VERSION_NUMBER",
    "MAX_FIELD_WIDTH_BITS",
    "validate_field_width",
    "resolve_layout",
    "layout_length_bits",
    "layout_length_octets",
    "is_octet_aligned",
    "validate_identifier",
    "validate_unsigned_field",
    "validate_pus_version_number",
    "pack_header",
    "unpack_header",
    "counter_step",
    "assess_counter_sequence",
    "assess_secondary_header",
]

# The secondary header fields in the order they appear on the wire. The first
# three are always present; the rest are switched on per mission.
FIELD_ORDER = (
    "pus-version-number",
    "spacecraft-time-reference-status",
    "service-type-id",
    "message-subtype-id",
    "message-type-counter",
    "destination-id",
    "time-field",
)

MANDATORY_FIELDS = (
    "pus-version-number",
    "service-type-id",
    "message-subtype-id",
)

OPTIONAL_FIELDS = tuple(f for f in FIELD_ORDER if f not in MANDATORY_FIELDS)

# Widths a mission usually starts from, in bits. Every one of them is
# overridable, which is exactly why the octet-alignment check is needed.
DEFAULT_WIDTHS_BITS = {
    "pus-version-number": 4,
    "spacecraft-time-reference-status": 4,
    "service-type-id": 8,
    "message-subtype-id": 8,
    "message-type-counter": 16,
    "destination-id": 16,
    "time-field": 48,
}

# The version number a PUS-C secondary header carries.
PUS_C_VERSION_NUMBER = 2

# A single secondary header field wider than this is a layout error, not a
# wide field; the time field is the widest realistic case.
MAX_FIELD_WIDTH_BITS = 128

_OCTET_BITS = 8


def _require_int(value, label, allow_zero=True):
    """Return value as an int, refusing bools and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must not be zero" % label)
    return value


def validate_field_width(name, width_bits):
    """Return the validated bit width of one secondary header field."""
    if not isinstance(name, str) or not name:
        raise ValueError("field name must be a non-empty string, got %r" % (name,))
    if name not in FIELD_ORDER:
        raise ValueError("unknown secondary header field %r" % (name,))
    width = _require_int(width_bits, "width of %s" % name)
    if width <= 0:
        raise ValueError("width of %s must be positive, got %d" % (name, width))
    if width > MAX_FIELD_WIDTH_BITS:
        raise ValueError(
            "width of %s is %d bits, above the %d-bit layout limit"
            % (name, width, MAX_FIELD_WIDTH_BITS)
        )
    return width


def resolve_layout(present_optional_fields=None, width_overrides=None):
    """Return the ordered layout as a list of (name, offset_bits, width_bits)."""
    if present_optional_fields is None:
        present = set()
    else:
        if isinstance(present_optional_fields, str):
            raise ValueError("present_optional_fields must be a sequence of names")
        present = []
        for name in present_optional_fields:
            if name not in OPTIONAL_FIELDS:
                raise ValueError(
                    "%r is not an optional secondary header field" % (name,)
                )
            if name in present:
                raise ValueError("optional field %r listed twice" % (name,))
            present.append(name)
        present = set(present)

    overrides = {}
    if width_overrides is not None:
        if not isinstance(width_overrides, dict):
            raise ValueError("width_overrides must be a mapping")
        for name, width in width_overrides.items():
            overrides[name] = validate_field_width(name, width)

    layout = []
    offset = 0
    for name in FIELD_ORDER:
        if name not in MANDATORY_FIELDS and name not in present:
            if name in overrides:
                raise ValueError(
                    "width override given for %r, which the mission did not switch on"
                    % (name,)
                )
            continue
        width = overrides.get(name, DEFAULT_WIDTHS_BITS[name])
        layout.append((name, offset, width))
        offset += width
    return layout


def layout_length_bits(layout):
    """Return the total width of a resolved layout in bits."""
    if not isinstance(layout, (list, tuple)) or not layout:
        raise ValueError("layout must be a non-empty sequence of field entries")
    total = 0
    expected_offset = 0
    for entry in layout:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise ValueError("layout entry must be (name, offset_bits, width_bits)")
        name, offset, width = entry
        validate_field_width(name, width)
        _require_int(offset, "offset of %s" % name)
        if offset != expected_offset:
            raise ValueError(
                "layout entry %s starts at bit %d, expected %d (gap or overlap)"
                % (name, offset, expected_offset)
            )
        expected_offset += width
        total += width
    return total


def layout_length_octets(layout):
    """Return the layout length in whole octets, refusing a misaligned layout."""
    bits = layout_length_bits(layout)
    if bits % _OCTET_BITS != 0:
        raise ValueError(
            "layout is %d bits, which is not a whole number of octets" % bits
        )
    return bits // _OCTET_BITS


def is_octet_aligned(layout):
    """Return True when the resolved layout ends on an octet boundary."""
    return layout_length_bits(layout) % _OCTET_BITS == 0


def validate_unsigned_field(name, value, width_bits):
    """Return the value, refusing anything the field width cannot carry."""
    width = validate_field_width(name, width_bits)
    number = _require_int(value, "value of %s" % name)
    if number < 0:
        raise ValueError("value of %s must not be negative, got %d" % (name, number))
    limit = 1 << width
    if number >= limit:
        raise ValueError(
            "value %d of %s does not fit its %d-bit field" % (number, name, width)
        )
    return number


def validate_identifier(name, value, width_bits):
    """Validate a service type or message subtype identifier field."""
    number = validate_unsigned_field(name, value, width_bits)
    if number == 0:
        raise ValueError("%s must not be zero; zero is not an allocated identifier" % name)
    return number


def validate_pus_version_number(value, width_bits=None):
    """Return (value, is_pus_c) for the version number field."""
    width = DEFAULT_WIDTHS_BITS["pus-version-number"] if width_bits is None else width_bits
    number = validate_unsigned_field("pus-version-number", value, width)
    return (number, number == PUS_C_VERSION_NUMBER)


def pack_header(layout, values):
    """Pack the field values into one integer, most significant field first."""
    if not isinstance(values, dict):
        raise ValueError("values must be a mapping of field name to integer")
    total_bits = layout_length_bits(layout)
    names = [entry[0] for entry in layout]
    for name in values:
        if name not in names:
            raise ValueError("value given for %r, which the layout does not carry" % (name,))
    packed = 0
    for name, _offset, width in layout:
        if name not in values:
            raise ValueError("no value given for layout field %r" % (name,))
        number = validate_unsigned_field(name, values[name], width)
        packed = (packed << width) | number
    if packed >> total_bits:
        raise ValueError("packed header overflowed its own layout")
    return packed


def unpack_header(layout, packed):
    """Unpack an integer back into a field-name to value mapping."""
    total_bits = layout_length_bits(layout)
    number = _require_int(packed, "packed header")
    if number < 0:
        raise ValueError("packed header must not be negative")
    if number >> total_bits:
        raise ValueError(
            "packed header is wider than the %d-bit layout it was read with" % total_bits
        )
    out = {}
    for name, offset, width in layout:
        shift = total_bits - offset - width
        out[name] = (number >> shift) & ((1 << width) - 1)
    return out


def counter_step(previous, current, width_bits):
    """Return the forward distance from previous to current, modulo the width."""
    width = validate_field_width("message-type-counter", width_bits)
    modulus = 1 << width
    prev = validate_unsigned_field("message-type-counter", previous, width)
    curr = validate_unsigned_field("message-type-counter", current, width)
    return (curr - prev) % modulus


def assess_counter_sequence(values, width_bits=None):
    """Follow a message type counter and report wraps, repeats and gaps."""
    width = (
        DEFAULT_WIDTHS_BITS["message-type-counter"] if width_bits is None else width_bits
    )
    width = validate_field_width("message-type-counter", width)
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of counter readings")
    if len(values) < 2:
        raise ValueError("a counter sequence needs at least two readings")
    readings = [validate_unsigned_field("message-type-counter", v, width) for v in values]
    wraps = 0
    repeats = []
    gaps = []
    for index in range(1, len(readings)):
        prev = readings[index - 1]
        curr = readings[index]
        step = counter_step(prev, curr, width)
        if curr < prev:
            wraps += 1
        if step == 0:
            repeats.append(index)
        elif step > 1:
            gaps.append({"index": index, "missing": step - 1})
    return {
        "width_bits": width,
        "readings": readings,
        "wraps": wraps,
        "repeats": repeats,
        "gaps": gaps,
        "missing_total": sum(gap["missing"] for gap in gaps),
        "continuous": not repeats and not gaps,
    }


def assess_secondary_header(spec):
    """Run the full clause 7.4.3.1 secondary header assessment.

    spec keys: optional_fields (sequence), width_overrides (mapping),
    values (mapping of field name to integer), optional counter_readings.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "values" not in spec:
        raise ValueError("spec missing required key 'values'")
    layout = resolve_layout(spec.get("optional_fields"), spec.get("width_overrides"))
    values = spec["values"]
    if not isinstance(values, dict):
        raise ValueError("spec['values'] must be a mapping")

    findings = []
    aligned = is_octet_aligned(layout)
    if not aligned:
        findings.append(
            "secondary header is %d bits, so the user data field would not start "
            "on an octet boundary" % layout_length_bits(layout)
        )

    widths = {name: width for name, _offset, width in layout}
    version, is_pus_c = validate_pus_version_number(
        values.get("pus-version-number"), widths["pus-version-number"]
    )
    if not is_pus_c:
        findings.append(
            "version number field reads %d, not the %d a PUS-C secondary header "
            "carries" % (version, PUS_C_VERSION_NUMBER)
        )
    service_type = validate_identifier(
        "service-type-id", values.get("service-type-id"), widths["service-type-id"]
    )
    subtype = validate_identifier(
        "message-subtype-id", values.get("message-subtype-id"), widths["message-subtype-id"]
    )

    packed = pack_header(layout, values)
    restored = unpack_header(layout, packed)
    if restored != {name: validate_unsigned_field(name, values[name], widths[name])
                    for name in widths}:
        raise ValueError("pack/unpack round trip did not preserve the field values")

    counters = None
    if "counter_readings" in spec:
        if "message-type-counter" not in widths:
            raise ValueError(
                "counter readings given but the mission did not switch the "
                "message type counter on"
            )
        counters = assess_counter_sequence(
            spec["counter_readings"], widths["message-type-counter"]
        )
        if counters["repeats"]:
            findings.append(
                "message type counter repeated %d time(s); duplicated reports"
                % len(counters["repeats"])
            )
        if counters["gaps"]:
            findings.append(
                "message type counter skipped %d report(s) across %d gap(s)"
                % (counters["missing_total"], len(counters["gaps"]))
            )

    return {
        "layout": layout,
        "length_bits": layout_length_bits(layout),
        "length_octets": layout_length_octets(layout) if aligned else None,
        "octet_aligned": aligned,
        "packed": packed,
        "fields": restored,
        "apid_message_key": (service_type, subtype),
        "counter_assessment": counters,
        "findings": findings,
        "compliant": aligned and not findings,
    }
