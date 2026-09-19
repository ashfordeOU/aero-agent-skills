"""General rules for packet field type codes and the bit layout they produce.

Anchor: ECSS-E-ST-70-41C clause 7.3.1 (packet field type code, general).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold a field type as an ordered pair: a type code that says what kind of
   value the field carries, and a format code that says which member of that
   kind it is. Neither half means anything alone.
2. Resolve the pair to a width in bits through a per-type rule. Some types
   have a fixed set of tabulated formats; some derive their width from the
   format code itself; one type has no width until a containing definition
   supplies it.
3. Refuse an unknown type code, a format code the type does not define, and
   a format code outside the span the type derives its width from. A pair
   that resolves to a plausible width by accident is worse than a refusal.
4. Lay a sequence of fields out in order, computing the bit offset of each
   from the widths of those before it, and the total width of the structure.
5. Assess the layout: whether it closes on an octet boundary, how many pad
   bits the next boundary needs, and which fields straddle one. A field that
   crosses an octet boundary is legal but is the usual source of an
   extraction defect, so it is named.
6. Report the resolved fields, the total width, the padding and the findings.
"""

__all__ = [
    "BITS_PER_OCTET",
    "TYPE_NAMES",
    "DEDUCED_TYPE_CODE",
    "validate_type_code",
    "validate_format_code",
    "field_width_bits",
    "describe_field_type",
    "is_octet_aligned",
    "padding_bits",
    "lay_out_fields",
    "straddling_fields",
    "assess_structure",
]

BITS_PER_OCTET = 8

# The type code names the kind of value; the format code selects within it.
TYPE_NAMES = {
    1: "boolean",
    2: "enumerated",
    3: "unsigned-integer",
    4: "signed-integer",
    5: "real",
    7: "octet-string",
    8: "character-string",
    9: "absolute-time",
    10: "relative-time",
    11: "deduced",
}

# A deduced field takes its width from the definition that contains it, so it
# has no width of its own and must never be given a default.
DEDUCED_TYPE_CODE = 11

# Types whose format code selects a tabulated width in bits.
_TABULATED_WIDTHS = {
    1: {0: 1},
    3: {4: 4, 8: 8, 12: 12, 13: 16, 14: 24, 16: 32, 17: 48, 18: 64},
    4: {4: 4, 8: 8, 12: 12, 13: 16, 14: 24, 16: 32, 17: 48, 18: 64},
    5: {1: 32, 2: 64},
    9: {1: 32, 2: 40, 3: 48, 4: 56},
    10: {1: 32, 2: 40, 3: 48, 4: 56},
}

# Types whose format code is itself the size, in the unit named here.
_DERIVED_WIDTHS = {
    2: ("bits", 1, 1, 64),
    7: ("octets", BITS_PER_OCTET, 1, 65535),
    8: ("characters", BITS_PER_OCTET, 1, 65535),
}


def validate_type_code(type_code):
    """Return a validated packet field type code."""
    if isinstance(type_code, bool) or not isinstance(type_code, int):
        raise ValueError("type code must be a whole number, got %r" % (type_code,))
    if type_code not in TYPE_NAMES:
        raise ValueError(
            "type code %d is not a defined packet field type code" % type_code
        )
    return type_code


def validate_format_code(format_code):
    """Return a validated packet field format code."""
    if isinstance(format_code, bool) or not isinstance(format_code, int):
        raise ValueError("format code must be a whole number, got %r" % (format_code,))
    if format_code < 0:
        raise ValueError("format code must not be negative, got %d" % format_code)
    return format_code


def field_width_bits(type_code, format_code):
    """Return the width in bits of the field named by this type and format pair."""
    type_code = validate_type_code(type_code)
    format_code = validate_format_code(format_code)
    if type_code == DEDUCED_TYPE_CODE:
        raise ValueError(
            "a deduced field has no width of its own; the containing definition supplies it"
        )
    if type_code in _TABULATED_WIDTHS:
        table = _TABULATED_WIDTHS[type_code]
        if format_code not in table:
            raise ValueError(
                "format code %d is not defined for type %d (%s); defined codes are %s"
                % (
                    format_code,
                    type_code,
                    TYPE_NAMES[type_code],
                    ", ".join(str(code) for code in sorted(table)),
                )
            )
        return table[format_code]
    unit, multiplier, lowest, highest = _DERIVED_WIDTHS[type_code]
    if format_code < lowest or format_code > highest:
        raise ValueError(
            "type %d (%s) derives its width from a format code of %d to %d %s, got %d"
            % (type_code, TYPE_NAMES[type_code], lowest, highest, unit, format_code)
        )
    return format_code * multiplier


def describe_field_type(type_code, format_code):
    """Return the resolved description of one field type pair."""
    type_code = validate_type_code(type_code)
    format_code = validate_format_code(format_code)
    deduced = type_code == DEDUCED_TYPE_CODE
    return {
        "type_code": type_code,
        "format_code": format_code,
        "type_name": TYPE_NAMES[type_code],
        "deduced": deduced,
        "width_bits": None if deduced else field_width_bits(type_code, format_code),
    }


def is_octet_aligned(bit_count):
    """Return whether a bit count closes on an octet boundary."""
    if isinstance(bit_count, bool) or not isinstance(bit_count, int):
        raise ValueError("bit count must be a whole number, got %r" % (bit_count,))
    if bit_count < 0:
        raise ValueError("bit count must not be negative, got %d" % bit_count)
    return bit_count % BITS_PER_OCTET == 0


def padding_bits(bit_count):
    """Return the pad bits needed to reach the next octet boundary."""
    if is_octet_aligned(bit_count):
        return 0
    return BITS_PER_OCTET - (bit_count % BITS_PER_OCTET)


def lay_out_fields(fields):
    """Return each field with its bit offset, plus the total width of the structure."""
    if not isinstance(fields, (list, tuple)) or not fields:
        raise ValueError("fields must be a non-empty sequence of field definitions")
    placed = []
    offset = 0
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError("field %d must be a mapping" % index)
        for required in ("name", "type_code", "format_code"):
            if required not in field:
                raise ValueError("field %d missing required key '%s'" % (index, required))
        name = field["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("field %d must carry a non-blank name" % index)
        described = describe_field_type(field["type_code"], field["format_code"])
        if described["deduced"]:
            if "width_bits" not in field:
                raise ValueError(
                    "field '%s' is deduced; the containing definition must supply width_bits"
                    % name
                )
            supplied = field["width_bits"]
            if isinstance(supplied, bool) or not isinstance(supplied, int) or supplied < 1:
                raise ValueError(
                    "field '%s' width_bits must be a positive whole number, got %r"
                    % (name, supplied)
                )
            described["width_bits"] = supplied
        described["name"] = name
        described["bit_offset"] = offset
        described["octet_offset"] = offset // BITS_PER_OCTET
        offset += described["width_bits"]
        placed.append(described)
    return {"fields": placed, "total_bits": offset}


def straddling_fields(placed_fields):
    """Return the names of fields that start mid-octet and run past that octet.

    A field that begins on an octet boundary is read whole octets at a time
    however wide it is. The awkward field is the one that begins part way into
    an octet and does not finish inside it, because extracting it needs a mask
    and a shift across two octets.
    """
    if not isinstance(placed_fields, (list, tuple)):
        raise ValueError("placed_fields must be a sequence of laid-out fields")
    names = []
    for field in placed_fields:
        for required in ("name", "bit_offset", "width_bits"):
            if required not in field:
                raise ValueError("laid-out field missing required key '%s'" % required)
        start = field["bit_offset"]
        into_octet = start % BITS_PER_OCTET
        if into_octet and into_octet + field["width_bits"] > BITS_PER_OCTET:
            names.append(field["name"])
    return names


def assess_structure(fields):
    """Lay out a field structure and report its width, padding and findings."""
    layout = lay_out_fields(fields)
    total = layout["total_bits"]
    pad = padding_bits(total)
    straddling = straddling_fields(layout["fields"])
    findings = []
    if pad:
        findings.append(
            "the structure is %d bits and needs %d pad bit(s) to close on an octet boundary"
            % (total, pad)
        )
    if straddling:
        findings.append(
            "field(s) crossing an octet boundary: %s" % ", ".join(straddling)
        )
    names = [field["name"] for field in layout["fields"]]
    duplicates = sorted(set(name for name in names if names.count(name) > 1))
    if duplicates:
        findings.append("duplicate field name(s): %s" % ", ".join(duplicates))
    return {
        "fields": layout["fields"],
        "total_bits": total,
        "total_octets": (total + pad) // BITS_PER_OCTET,
        "padding_bits": pad,
        "octet_aligned": pad == 0,
        "straddling_fields": straddling,
        "findings": findings,
    }
