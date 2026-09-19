#!/usr/bin/env python3
"""Bit-string parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bit-string parameter carries an ordered run of bits that has no
numeric meaning: it is a pattern, and the receiver hands it on
unchanged. The clause's eight normative items reduce to these
obligations:

    the length is either fixed by the parameter's format code or
    carried in a count field ahead of the bits;
    a fixed field is exactly its declared length -- neither padded
    into meaning nor truncated to fit;
    a variable field's count field has a width, and a pattern longer
    than that width can express cannot be carried;
    bits are laid down in declaration order, first declared bit
    first, so the order is never reversed by the encoding;
    a run that is not a whole number of octets is padded at the
    trailing end to reach the boundary;
    the pad bits are not part of the value and are set to a fixed
    value so two encodings of the same pattern compare equal;
    decoding takes the declared length and discards the pad, so a
    reader that keeps the pad reads a longer pattern than was sent;
    a zero-length pattern is legitimate for a variable field and
    meaningless for a fixed one.

Everything here is exact integer and string work, so the same answer
comes back on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

BIT_STRING_PTC = 6

VARIABLE_FORMAT_CODE = 0
OCTET_BITS = 8
PAD_BIT = "0"

MAX_FIXED_LENGTH_BITS = 1 << 16
MIN_COUNT_WIDTH_BITS = 1
MAX_COUNT_WIDTH_BITS = 32

VERDICT_VALID = "bit-string-valid"
VERDICT_LENGTH_MISMATCH = "bit-string-length-mismatch"
VERDICT_COUNT_FIELD_TOO_NARROW = "bit-string-count-field-too-narrow"
VERDICT_EMPTY_FIXED = "bit-string-empty-fixed-field"


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_integer(name, value):
    if not _is_integer(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def validate_bits(bits):
    """Check a pattern is an ordered run of zeros and ones."""
    if not isinstance(bits, str):
        raise ValueError("bits must be a string of 0 and 1, got %r" % (bits,))
    for character in bits:
        if character not in "01":
            raise ValueError(
                "bits must contain only 0 and 1; found %r" % character
            )
    return bits


def validate_fixed_length(length_bits):
    """Check a fixed declared length is usable."""
    _require_integer("length_bits", length_bits)
    if length_bits < 1:
        raise ValueError(
            "a fixed bit-string field must declare at least one bit, got %d"
            % length_bits
        )
    if length_bits > MAX_FIXED_LENGTH_BITS:
        raise ValueError(
            "length_bits must not exceed %d, got %d"
            % (MAX_FIXED_LENGTH_BITS, length_bits)
        )
    return length_bits


def validate_count_width(count_width_bits):
    """Check the width of the count field that precedes a variable run."""
    _require_integer("count_width_bits", count_width_bits)
    if (
        count_width_bits < MIN_COUNT_WIDTH_BITS
        or count_width_bits > MAX_COUNT_WIDTH_BITS
    ):
        raise ValueError(
            "count_width_bits must be between %d and %d, got %d"
            % (MIN_COUNT_WIDTH_BITS, MAX_COUNT_WIDTH_BITS, count_width_bits)
        )
    return count_width_bits


def max_length_for_count_width(count_width_bits):
    """Longest pattern a count field of this width can announce."""
    validate_count_width(count_width_bits)
    return (1 << count_width_bits) - 1


def padding_bits(length_bits):
    """Pad bits needed to reach the next octet boundary."""
    _require_integer("length_bits", length_bits)
    if length_bits < 0:
        raise ValueError("length_bits must not be negative, got %d" % length_bits)
    return (-length_bits) % OCTET_BITS


def octet_count(length_bits):
    """Octets a pattern of this length occupies once padded."""
    _require_integer("length_bits", length_bits)
    if length_bits < 0:
        raise ValueError("length_bits must not be negative, got %d" % length_bits)
    return (length_bits + OCTET_BITS - 1) // OCTET_BITS


def pad_to_octet(bits):
    """Pad a pattern at the trailing end with the fixed pad value.

    The pad is appended after the last declared bit, never inserted
    ahead of the first, so the declaration order is preserved.
    """
    validate_bits(bits)
    pad = padding_bits(len(bits))
    return {"padded_bits": bits + PAD_BIT * pad, "pad_count": pad}


def strip_pad(padded_bits, length_bits):
    """Recover the declared pattern, discarding the pad."""
    validate_bits(padded_bits)
    _require_integer("length_bits", length_bits)
    if length_bits < 0:
        raise ValueError("length_bits must not be negative, got %d" % length_bits)
    if length_bits > len(padded_bits):
        raise ValueError(
            "declared length %d exceeds the %d bits available"
            % (length_bits, len(padded_bits))
        )
    if len(padded_bits) - length_bits >= OCTET_BITS:
        raise ValueError(
            "%d bits follow a declared length of %d; that is more than one "
            "octet of pad and the field boundaries do not line up"
            % (len(padded_bits) - length_bits, length_bits)
        )
    return padded_bits[:length_bits]


def pack_bit_string(bits):
    """Octets for a pattern, first declared bit in the leading octet."""
    validate_bits(bits)
    padded = pad_to_octet(bits)
    if not padded["padded_bits"]:
        return {"octets": b"", "pad_count": 0, "length_bits": 0}
    value = int(padded["padded_bits"], 2)
    octets = value.to_bytes(octet_count(len(bits)), "big")
    return {
        "octets": octets,
        "pad_count": padded["pad_count"],
        "length_bits": len(bits),
    }


def unpack_bit_string(octets, length_bits):
    """Pattern carried by an octet run, cut back to the declared length."""
    if not isinstance(octets, (bytes, bytearray)):
        raise ValueError("octets must be bytes, got %r" % (octets,))
    _require_integer("length_bits", length_bits)
    if length_bits < 0:
        raise ValueError("length_bits must not be negative, got %d" % length_bits)
    available = len(octets) * OCTET_BITS
    if length_bits > available:
        raise ValueError(
            "declared length %d exceeds the %d bits the octet run carries"
            % (length_bits, available)
        )
    if length_bits == 0:
        return ""
    bits = "".join(format(octet, "08b") for octet in bytes(octets))
    return strip_pad(bits, length_bits)


def check_fixed_field(bits, declared_length_bits):
    """A fixed field is exactly its declared length, either way."""
    validate_bits(bits)
    validate_fixed_length(declared_length_bits)
    if len(bits) < declared_length_bits:
        raise ValueError(
            "pattern is %d bits against a declared %d; padding it out would "
            "add bits the sender never set"
            % (len(bits), declared_length_bits)
        )
    if len(bits) > declared_length_bits:
        raise ValueError(
            "pattern is %d bits against a declared %d; truncating it would "
            "drop bits the sender did set"
            % (len(bits), declared_length_bits)
        )
    return bits


def encode_variable(bits, count_width_bits):
    """Count field followed by the pattern, padded to a boundary."""
    validate_bits(bits)
    validate_count_width(count_width_bits)
    ceiling = max_length_for_count_width(count_width_bits)
    if len(bits) > ceiling:
        raise ValueError(
            "a %d bit pattern cannot be announced by a %d bit count field, "
            "whose ceiling is %d bits"
            % (len(bits), count_width_bits, ceiling)
        )
    packed = pack_bit_string(bits)
    return {
        "count_bits": format(len(bits), "0%db" % count_width_bits),
        "length_bits": len(bits),
        "octets": packed["octets"],
        "pad_count": packed["pad_count"],
    }


def decode_variable(count_bits, octets, count_width_bits):
    """Pattern announced by a count field and carried by the octets."""
    validate_bits(count_bits)
    validate_count_width(count_width_bits)
    if len(count_bits) != count_width_bits:
        raise ValueError(
            "count field is %d bits against a declared width of %d"
            % (len(count_bits), count_width_bits)
        )
    return unpack_bit_string(octets, int(count_bits, 2))


def patterns_are_equal(left, right):
    """Two patterns match only when their lengths and bits both match.

    A pattern is not a number: leading zeros are part of it, and a
    shorter run is never equal to a longer one that starts the same.
    """
    validate_bits(left)
    validate_bits(right)
    return len(left) == len(right) and left == right


def assess_bit_string_field(spec):
    """Full clause 7.3.7 assessment of one bit-string parameter."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    bits = validate_bits(spec.get("bits"))
    format_code = _require_integer("format_code", spec.get("format_code"))
    if format_code < 0:
        raise ValueError("format_code must not be negative, got %d" % format_code)
    findings = []
    variable = format_code == VARIABLE_FORMAT_CODE
    pad = padding_bits(len(bits))
    octets = octet_count(len(bits))
    if variable:
        count_width_bits = validate_count_width(spec.get("count_width_bits"))
        ceiling = max_length_for_count_width(count_width_bits)
        if len(bits) > ceiling:
            verdict = VERDICT_COUNT_FIELD_TOO_NARROW
            findings.append(
                "a %d bit count field announces at most %d bits; the pattern "
                "is %d" % (count_width_bits, ceiling, len(bits))
            )
        else:
            verdict = VERDICT_VALID
        if len(bits) == 0:
            findings.append(
                "a zero-length pattern is legitimate for a variable field; the "
                "count field carries zero and no payload octet follows"
            )
        total_octets = octets
    else:
        count_width_bits = None
        declared = validate_fixed_length(format_code)
        total_octets = octet_count(declared)
        if len(bits) == 0:
            verdict = VERDICT_EMPTY_FIXED
            findings.append(
                "a fixed field of %d bits cannot carry an empty pattern" % declared
            )
        elif len(bits) != declared:
            verdict = VERDICT_LENGTH_MISMATCH
            findings.append(
                "pattern is %d bits against a fixed field of %d; a fixed field "
                "is neither padded into meaning nor truncated to fit"
                % (len(bits), declared)
            )
        else:
            verdict = VERDICT_VALID
        pad = padding_bits(declared)
    if pad:
        findings.append(
            "%d pad bit(s) follow the pattern to reach the octet boundary; "
            "they carry the fixed pad value and are not part of the value"
            % pad
        )
    return {
        "ptc": BIT_STRING_PTC,
        "format_code": format_code,
        "variable_length": variable,
        "length_bits": len(bits),
        "count_width_bits": count_width_bits,
        "pad_bits": pad,
        "payload_octets": total_octets,
        "verdict": verdict,
        "findings": findings,
    }
