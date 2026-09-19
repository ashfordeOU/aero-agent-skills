#!/usr/bin/env python3
"""Unsigned integer parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An unsigned integer parameter carries a whole number with no sign, in
a field whose width the parameter's format code fixes. Three things
follow, and together they are the clause's job:

    the field width fixes the representable range, zero up to one
    below two-to-the-width, and nothing outside it can be carried;
    the value is laid down most significant bit first, so a field that
    is a whole number of octets packs directly into big-endian octets;
    a value that does not fit is a rejected value, not a wrapped one.

Everything here is exact integer arithmetic on bit widths, so the same
answer comes back on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

UNSIGNED_PTC = 3

MIN_FIELD_WIDTH_BITS = 1
MAX_FIELD_WIDTH_BITS = 64
OCTET_BITS = 8

VERDICT_IN_RANGE = "unsigned-value-in-range"
VERDICT_OVER_RANGE = "unsigned-value-over-range"
VERDICT_NEGATIVE = "unsigned-value-negative"


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_integer(name, value):
    if not _is_integer(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def validate_field_width(width_bits):
    """Width of the unsigned field, as the format code fixes it."""
    _require_integer("width_bits", width_bits)
    if width_bits < MIN_FIELD_WIDTH_BITS or width_bits > MAX_FIELD_WIDTH_BITS:
        raise ValueError(
            "width_bits must be between %d and %d, got %d"
            % (MIN_FIELD_WIDTH_BITS, MAX_FIELD_WIDTH_BITS, width_bits)
        )
    return width_bits


def value_range(width_bits):
    """Lowest and highest value the field can carry."""
    validate_field_width(width_bits)
    return (0, (1 << width_bits) - 1)


def is_octet_aligned(width_bits):
    """True when the field is a whole number of octets."""
    validate_field_width(width_bits)
    return width_bits % OCTET_BITS == 0


def octet_count(width_bits):
    """Octets the field occupies once it is padded out to a boundary."""
    validate_field_width(width_bits)
    return (width_bits + OCTET_BITS - 1) // OCTET_BITS


def minimum_width_for(max_value):
    """Narrowest field that still carries this value.

    Exact integer arithmetic: the answer is the bit length of the
    value, never a rounded logarithm.
    """
    _require_integer("max_value", max_value)
    if max_value < 0:
        raise ValueError("max_value must not be negative, got %d" % max_value)
    if max_value == 0:
        return MIN_FIELD_WIDTH_BITS
    return max_value.bit_length()


def fits(value, width_bits):
    """True when the value is inside the field's range."""
    _require_integer("value", value)
    low, high = value_range(width_bits)
    return low <= value <= high


def encode_unsigned(value, width_bits):
    """Bit pattern for the value, most significant bit first.

    A value outside the range is refused. Wrapping it to fit would
    report a plausible number that the spacecraft never held.
    """
    _require_integer("value", value)
    low, high = value_range(width_bits)
    if value < low:
        raise ValueError(
            "an unsigned field cannot carry the negative value %d" % value
        )
    if value > high:
        raise ValueError(
            "value %d does not fit a %d bit unsigned field whose top is %d"
            % (value, width_bits, high)
        )
    return format(value, "0%db" % width_bits)


def decode_unsigned(bits, width_bits):
    """Value carried by a bit pattern read most significant bit first."""
    validate_field_width(width_bits)
    if not isinstance(bits, str):
        raise ValueError("bits must be a string of 0 and 1, got %r" % (bits,))
    if len(bits) != width_bits:
        raise ValueError(
            "expected %d bits, got %d" % (width_bits, len(bits))
        )
    if any(character not in "01" for character in bits):
        raise ValueError("bits must contain only 0 and 1, got %r" % bits)
    return int(bits, 2)


def pack_octets(value, width_bits):
    """Octets for an octet-aligned field, most significant octet first."""
    if not is_octet_aligned(width_bits):
        raise ValueError(
            "a %d bit field is not a whole number of octets and cannot be "
            "packed on its own" % width_bits
        )
    encode_unsigned(value, width_bits)
    return value.to_bytes(width_bits // OCTET_BITS, "big")


def unpack_octets(octets):
    """Value carried by a big-endian octet run."""
    if not isinstance(octets, (bytes, bytearray)):
        raise ValueError("octets must be bytes, got %r" % (octets,))
    if not octets:
        raise ValueError("octets must not be empty")
    return int.from_bytes(bytes(octets), "big")


def narrowing_is_lossless(from_width_bits, to_width_bits, observed_max):
    """Whether moving a parameter to a narrower field can still carry it."""
    validate_field_width(from_width_bits)
    validate_field_width(to_width_bits)
    _require_integer("observed_max", observed_max)
    if observed_max < 0:
        raise ValueError("observed_max must not be negative, got %d" % observed_max)
    if observed_max > value_range(from_width_bits)[1]:
        raise ValueError(
            "observed_max %d already exceeds the %d bit source field"
            % (observed_max, from_width_bits)
        )
    return observed_max <= value_range(to_width_bits)[1]


def assess_unsigned_field(spec):
    """Full clause 7.3.4 assessment of one unsigned integer parameter."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    width_bits = validate_field_width(spec.get("width_bits"))
    value = _require_integer("value", spec.get("value"))
    low, high = value_range(width_bits)
    findings = []
    if value < low:
        verdict = VERDICT_NEGATIVE
        findings.append(
            "value %d is negative; an unsigned field carries no sign, so a "
            "signed parameter type is needed rather than a wider field" % value
        )
        encoded = None
    elif value > high:
        verdict = VERDICT_OVER_RANGE
        findings.append(
            "value %d is above the %d bit ceiling %d; it needs %d bits"
            % (value, width_bits, high, minimum_width_for(value))
        )
        encoded = None
    else:
        verdict = VERDICT_IN_RANGE
        encoded = encode_unsigned(value, width_bits)
    if not is_octet_aligned(width_bits):
        findings.append(
            "a %d bit field is not octet aligned; it only packs beside its "
            "neighbours, and occupies %d octets alone"
            % (width_bits, octet_count(width_bits))
        )
    return {
        "ptc": UNSIGNED_PTC,
        "width_bits": width_bits,
        "value": value,
        "low": low,
        "high": high,
        "minimum_width_bits": minimum_width_for(value) if value >= 0 else None,
        "octet_aligned": is_octet_aligned(width_bits),
        "encoded_bits": encoded,
        "verdict": verdict,
        "findings": findings,
    }
