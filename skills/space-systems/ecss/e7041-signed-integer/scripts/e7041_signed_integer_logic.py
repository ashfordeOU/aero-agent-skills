#!/usr/bin/env python3
"""Signed integer parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A signed integer parameter carries a whole number that may be
negative, in a field whose width the parameter's format code fixes.
Three things follow, and together they are the clause's job:

    the sign lives in the leading bit and negatives are held in two's
    complement, not as a sign bit beside a magnitude;
    the range is asymmetric -- it reaches one further below zero than
    above it, because zero occupies a positive-side code;
    decoding sign-extends from the field width, so reading the field
    at the wrong width turns a small negative into a large positive.

Everything here is exact integer arithmetic on bit widths, so the same
answer comes back on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

SIGNED_PTC = 4

MIN_FIELD_WIDTH_BITS = 2
MAX_FIELD_WIDTH_BITS = 64
OCTET_BITS = 8

VERDICT_IN_RANGE = "signed-value-in-range"
VERDICT_ABOVE_RANGE = "signed-value-above-range"
VERDICT_BELOW_RANGE = "signed-value-below-range"


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_integer(name, value):
    if not _is_integer(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def validate_field_width(width_bits):
    """Width of the signed field, as the format code fixes it.

    A one bit field has no room for a sign and a magnitude together,
    so two bits is the narrowest meaningful signed field.
    """
    _require_integer("width_bits", width_bits)
    if width_bits < MIN_FIELD_WIDTH_BITS or width_bits > MAX_FIELD_WIDTH_BITS:
        raise ValueError(
            "width_bits must be between %d and %d, got %d"
            % (MIN_FIELD_WIDTH_BITS, MAX_FIELD_WIDTH_BITS, width_bits)
        )
    return width_bits


def value_range(width_bits):
    """Lowest and highest value the field can carry, two's complement."""
    validate_field_width(width_bits)
    half = 1 << (width_bits - 1)
    return (-half, half - 1)


def range_is_asymmetric(width_bits):
    """True when the negative end reaches further than the positive end."""
    low, high = value_range(width_bits)
    return -low != high


def most_negative_value(width_bits):
    """The value with no positive counterpart in the same field."""
    return value_range(width_bits)[0]


def minimum_width_for_range(low, high):
    """Narrowest signed field covering an inclusive value range.

    Exact integer search over widths, so the asymmetry at the bottom
    of the range is honoured rather than approximated by a magnitude.
    """
    _require_integer("low", low)
    _require_integer("high", high)
    if low > high:
        raise ValueError("low %d must not exceed high %d" % (low, high))
    for width_bits in range(MIN_FIELD_WIDTH_BITS, MAX_FIELD_WIDTH_BITS + 1):
        field_low, field_high = value_range(width_bits)
        if field_low <= low and high <= field_high:
            return width_bits
    raise ValueError(
        "range %d..%d does not fit any field up to %d bits"
        % (low, high, MAX_FIELD_WIDTH_BITS)
    )


def fits(value, width_bits):
    """True when the value is inside the field's signed range."""
    _require_integer("value", value)
    low, high = value_range(width_bits)
    return low <= value <= high


def encode_signed(value, width_bits):
    """Two's complement code for the value, refusing anything outside."""
    _require_integer("value", value)
    low, high = value_range(width_bits)
    if value < low or value > high:
        raise ValueError(
            "value %d does not fit a %d bit signed field spanning %d..%d"
            % (value, width_bits, low, high)
        )
    code = value & ((1 << width_bits) - 1)
    return code


def decode_signed(code, width_bits):
    """Value carried by a two's complement code, sign extended."""
    validate_field_width(width_bits)
    _require_integer("code", code)
    capacity = 1 << width_bits
    if code < 0 or code >= capacity:
        raise ValueError(
            "code %d is not a %d bit pattern" % (code, width_bits)
        )
    if code >= capacity >> 1:
        return code - capacity
    return code


def encode_bits(value, width_bits):
    """Two's complement bit pattern, most significant bit first."""
    code = encode_signed(value, width_bits)
    return format(code, "0%db" % width_bits)


def sign_bit(value, width_bits):
    """Leading bit of the encoded field: 1 for a negative value."""
    return 1 if encode_signed(value, width_bits) >> (width_bits - 1) else 0


def misread_at_width(value, true_width_bits, read_width_bits):
    """What a negative value becomes when read at the wrong width.

    Reading a narrower field as a wider one drops the sign extension,
    so a small negative reads as a large positive. This is the single
    most common signed-parameter defect and is worth naming.
    """
    code = encode_signed(value, true_width_bits)
    validate_field_width(read_width_bits)
    if read_width_bits < true_width_bits:
        raise ValueError(
            "read_width_bits %d is narrower than the field %d; that is a "
            "truncation, not a sign-extension fault"
            % (read_width_bits, true_width_bits)
        )
    return decode_signed(code, read_width_bits)


def assess_signed_field(spec):
    """Full clause 7.3.5 assessment of one signed integer parameter."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    width_bits = validate_field_width(spec.get("width_bits"))
    value = _require_integer("value", spec.get("value"))
    low, high = value_range(width_bits)
    findings = []
    if value < low:
        verdict = VERDICT_BELOW_RANGE
        encoded = None
        findings.append(
            "value %d is below the %d bit floor %d" % (value, width_bits, low)
        )
    elif value > high:
        verdict = VERDICT_ABOVE_RANGE
        encoded = None
        findings.append(
            "value %d is above the %d bit ceiling %d; note the ceiling is one "
            "short of the magnitude of the floor" % (value, width_bits, high)
        )
    else:
        verdict = VERDICT_IN_RANGE
        encoded = encode_bits(value, width_bits)
    if value == low:
        findings.append(
            "value %d is the most negative code; it has no positive "
            "counterpart in this field, so negating it overflows" % low
        )
    if width_bits % OCTET_BITS != 0:
        findings.append(
            "a %d bit signed field is not octet aligned; sign extension has to "
            "be applied from bit %d, not from an octet boundary"
            % (width_bits, width_bits)
        )
    return {
        "ptc": SIGNED_PTC,
        "width_bits": width_bits,
        "value": value,
        "low": low,
        "high": high,
        "asymmetric": range_is_asymmetric(width_bits),
        "minimum_width_bits": (
            minimum_width_for_range(min(value, 0), max(value, 0))
        ),
        "encoded_bits": encoded,
        "verdict": verdict,
        "findings": findings,
    }
