"""Encoding and decoding of the boolean parameter field type.

Anchor: ECSS-E-ST-70-41C clause 7.3.2 (the boolean packet field type).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Accept exactly one type pair for a boolean parameter field: the boolean
   type code with its single defined format code. Any other pair is a
   different field type wearing a boolean name.
2. Encode a boolean field into one bit, set for true and clear for false.
   Accept only genuine truth values: the strings "true" and "1", the integers
   0 and 1 used as flags, and every other truthy-looking value are refused,
   because a field that silently reads a non-empty string as true is the
   defect this type exists to prevent.
3. Decode one bit back to a truth value, refusing a bit that is not 0 or 1.
4. Pack a run of boolean fields into octets most significant bit first, so
   the first field of the definition is the first bit on the wire, and report
   the pad bits the last octet needed.
5. Unpack the same run from octets, taking the count of fields from the
   definition rather than from the octet length, because the padding carries
   no field and must never be decoded as one.
6. Assess a structure of boolean fields: the bits used, the pad bits wasted
   and the finding that a single boolean given a whole octet has spent seven
   bits on nothing.
"""

__all__ = [
    "BOOLEAN_TYPE_CODE",
    "BOOLEAN_FORMAT_CODE",
    "BOOLEAN_WIDTH_BITS",
    "BITS_PER_OCTET",
    "validate_boolean_type_pair",
    "encode_boolean",
    "decode_boolean",
    "boolean_width_bits",
    "pack_booleans",
    "unpack_booleans",
    "padding_bits",
    "assess_boolean_structure",
]

BOOLEAN_TYPE_CODE = 1
BOOLEAN_FORMAT_CODE = 0
BOOLEAN_WIDTH_BITS = 1
BITS_PER_OCTET = 8


def validate_boolean_type_pair(type_code, format_code):
    """Return the validated boolean type and format code pair."""
    for label, value in (("type code", type_code), ("format code", format_code)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be a whole number, got %r" % (label, value))
    if type_code != BOOLEAN_TYPE_CODE:
        raise ValueError(
            "type code %d is not the boolean field type code %d" % (type_code, BOOLEAN_TYPE_CODE)
        )
    if format_code != BOOLEAN_FORMAT_CODE:
        raise ValueError(
            "the boolean field type defines only format code %d, got %d"
            % (BOOLEAN_FORMAT_CODE, format_code)
        )
    return (BOOLEAN_TYPE_CODE, BOOLEAN_FORMAT_CODE)


def boolean_width_bits(type_code=BOOLEAN_TYPE_CODE, format_code=BOOLEAN_FORMAT_CODE):
    """Return the width in bits of a boolean parameter field."""
    validate_boolean_type_pair(type_code, format_code)
    return BOOLEAN_WIDTH_BITS


def encode_boolean(value):
    """Return the single bit that carries this truth value: 1 for true, 0 for false."""
    if not isinstance(value, bool):
        raise ValueError(
            "a boolean field takes a genuine truth value, not %r of type %s"
            % (value, type(value).__name__)
        )
    return 1 if value else 0


def decode_boolean(bit):
    """Return the truth value carried by a single bit."""
    if isinstance(bit, bool) or not isinstance(bit, int):
        raise ValueError("a boolean field decodes from the integer 0 or 1, got %r" % (bit,))
    if bit not in (0, 1):
        raise ValueError("a one-bit field holds 0 or 1, got %d" % bit)
    return bit == 1


def padding_bits(bit_count):
    """Return the pad bits needed to reach the next octet boundary."""
    if isinstance(bit_count, bool) or not isinstance(bit_count, int):
        raise ValueError("bit count must be a whole number, got %r" % (bit_count,))
    if bit_count < 0:
        raise ValueError("bit count must not be negative, got %d" % bit_count)
    remainder = bit_count % BITS_PER_OCTET
    return 0 if remainder == 0 else BITS_PER_OCTET - remainder


def pack_booleans(values):
    """Pack a run of boolean fields into octets, most significant bit first."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of truth values")
    if not values:
        raise ValueError("a boolean structure must carry at least one field")
    bits = [encode_boolean(value) for value in values]
    pad = padding_bits(len(bits))
    padded = bits + [0] * pad
    octets = []
    for start in range(0, len(padded), BITS_PER_OCTET):
        octet = 0
        for offset in range(BITS_PER_OCTET):
            octet = (octet << 1) | padded[start + offset]
        octets.append(octet)
    return {
        "octets": octets,
        "field_count": len(bits),
        "bits_used": len(bits),
        "padding_bits": pad,
    }


def unpack_booleans(octets, field_count):
    """Unpack a run of boolean fields from octets, most significant bit first."""
    if not isinstance(octets, (list, tuple)):
        raise ValueError("octets must be a sequence of whole numbers")
    for index, octet in enumerate(octets):
        if isinstance(octet, bool) or not isinstance(octet, int):
            raise ValueError("octet %d must be a whole number, got %r" % (index, octet))
        if octet < 0 or octet > 255:
            raise ValueError("octet %d must be in 0 to 255, got %d" % (index, octet))
    if isinstance(field_count, bool) or not isinstance(field_count, int):
        raise ValueError("field_count must be a whole number, got %r" % (field_count,))
    if field_count < 1:
        raise ValueError("field_count must be at least one, got %d" % field_count)
    available = len(octets) * BITS_PER_OCTET
    if field_count > available:
        raise ValueError(
            "%d boolean fields need more than the %d bits these octets carry"
            % (field_count, available)
        )
    values = []
    for index in range(field_count):
        octet = octets[index // BITS_PER_OCTET]
        shift = BITS_PER_OCTET - 1 - (index % BITS_PER_OCTET)
        values.append(decode_boolean((octet >> shift) & 1))
    return values


def assess_boolean_structure(fields):
    """Assess a structure of boolean parameter fields and report its packing.

    fields: a sequence of mappings with 'name' and 'value', optionally
    'type_code' and 'format_code' to be checked against the boolean pair.
    """
    if not isinstance(fields, (list, tuple)) or not fields:
        raise ValueError("fields must be a non-empty sequence of boolean field definitions")
    names = []
    values = []
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError("field %d must be a mapping" % index)
        for required in ("name", "value"):
            if required not in field:
                raise ValueError("field %d missing required key '%s'" % (index, required))
        name = field["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("field %d must carry a non-blank name" % index)
        validate_boolean_type_pair(
            field.get("type_code", BOOLEAN_TYPE_CODE),
            field.get("format_code", BOOLEAN_FORMAT_CODE),
        )
        names.append(name)
        values.append(field["value"])
    packed = pack_booleans(values)
    round_trip = unpack_booleans(packed["octets"], packed["field_count"])
    findings = []
    if packed["padding_bits"]:
        findings.append(
            "%d of the %d bit(s) transmitted carry no field"
            % (packed["padding_bits"], packed["field_count"] + packed["padding_bits"])
        )
    if packed["field_count"] == 1:
        findings.append(
            "a single boolean field occupies a whole octet on the wire; "
            "grouping it with the neighbouring flags recovers the other bits"
        )
    duplicates = sorted(set(name for name in names if names.count(name) > 1))
    if duplicates:
        findings.append("duplicate field name(s): %s" % ", ".join(duplicates))
    return {
        "names": names,
        "values": [bool(value) for value in values],
        "octets": packed["octets"],
        "octet_count": len(packed["octets"]),
        "bits_used": packed["bits_used"],
        "padding_bits": packed["padding_bits"],
        "round_trip_matches": round_trip == [bool(value) for value in values],
        "findings": findings,
    }
