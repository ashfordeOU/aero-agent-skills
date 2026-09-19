#!/usr/bin/env python3
"""Octet-string parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An octet-string parameter carries an opaque run of whole octets. The
ground segment moves it, stores it and hands it back unchanged; it
does not interpret it. The clause's six normative items reduce to
these obligations:

    the length is either fixed by the parameter's format code or
    carried in a count field ahead of the octets;
    a fixed field is exactly its declared octet count -- neither
    padded out nor truncated to fit;
    a variable field's count field has a width, and a run longer
    than that width can express cannot be carried;
    the field is inherently octet aligned, so there is no pad and no
    partial octet anywhere in it;
    the content is opaque -- no character set, byte order or numeric
    reading is imposed on it by the parameter type;
    a zero-length run is legitimate for a variable field and
    meaningless for a fixed one.

Everything here is exact integer and byte work, so the same answer
comes back on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_STRING_PTC = 7

VARIABLE_FORMAT_CODE = 0
OCTET_BITS = 8

MAX_FIXED_LENGTH_OCTETS = 1 << 16
MIN_COUNT_WIDTH_BITS = 1
MAX_COUNT_WIDTH_BITS = 32

VERDICT_VALID = "octet-string-valid"
VERDICT_LENGTH_MISMATCH = "octet-string-length-mismatch"
VERDICT_COUNT_FIELD_TOO_NARROW = "octet-string-count-field-too-narrow"
VERDICT_EMPTY_FIXED = "octet-string-empty-fixed-field"


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_integer(name, value):
    if not _is_integer(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def validate_octets(value):
    """Check the payload is a run of whole octets and nothing else.

    Text is refused on purpose. The parameter type imposes no
    character set, so accepting a string here would mean guessing an
    encoding the standard never named.
    """
    if isinstance(value, str):
        raise ValueError(
            "an octet-string payload is opaque and carries no character set; "
            "supply bytes rather than text"
        )
    if not isinstance(value, (bytes, bytearray)):
        raise ValueError("payload must be bytes, got %r" % (value,))
    return bytes(value)


def validate_fixed_length(length_octets):
    """Check a fixed declared octet count is usable."""
    _require_integer("length_octets", length_octets)
    if length_octets < 1:
        raise ValueError(
            "a fixed octet-string field must declare at least one octet, got %d"
            % length_octets
        )
    if length_octets > MAX_FIXED_LENGTH_OCTETS:
        raise ValueError(
            "length_octets must not exceed %d, got %d"
            % (MAX_FIXED_LENGTH_OCTETS, length_octets)
        )
    return length_octets


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
    """Longest run a count field of this width can announce, in octets."""
    validate_count_width(count_width_bits)
    return (1 << count_width_bits) - 1


def field_size_bits(length_octets):
    """Bits the payload occupies. Always a whole number of octets."""
    _require_integer("length_octets", length_octets)
    if length_octets < 0:
        raise ValueError("length_octets must not be negative, got %d" % length_octets)
    return length_octets * OCTET_BITS


def padding_octets(length_octets):
    """Pad an octet-string needs to reach a boundary: none, ever."""
    _require_integer("length_octets", length_octets)
    if length_octets < 0:
        raise ValueError("length_octets must not be negative, got %d" % length_octets)
    return 0


def check_fixed_field(payload, declared_length_octets):
    """A fixed field is exactly its declared octet count, either way."""
    payload = validate_octets(payload)
    validate_fixed_length(declared_length_octets)
    if len(payload) < declared_length_octets:
        raise ValueError(
            "payload is %d octets against a declared %d; padding it out would "
            "add octets the sender never set"
            % (len(payload), declared_length_octets)
        )
    if len(payload) > declared_length_octets:
        raise ValueError(
            "payload is %d octets against a declared %d; truncating it would "
            "drop octets the sender did set"
            % (len(payload), declared_length_octets)
        )
    return payload


def encode_variable(payload, count_width_bits):
    """Count field followed by the opaque octets."""
    payload = validate_octets(payload)
    validate_count_width(count_width_bits)
    ceiling = max_length_for_count_width(count_width_bits)
    if len(payload) > ceiling:
        raise ValueError(
            "a %d octet payload cannot be announced by a %d bit count field, "
            "whose ceiling is %d octets"
            % (len(payload), count_width_bits, ceiling)
        )
    if count_width_bits % OCTET_BITS:
        raise ValueError(
            "a %d bit count field is not a whole number of octets and cannot "
            "precede an octet-aligned payload on its own" % count_width_bits
        )
    count = len(payload).to_bytes(count_width_bits // OCTET_BITS, "big")
    return {
        "count_octets": count,
        "length_octets": len(payload),
        "payload": payload,
        "buffer": count + payload,
    }


def decode_variable(buffer, count_width_bits):
    """Payload announced by a leading count field, and what it consumed."""
    buffer = validate_octets(buffer)
    validate_count_width(count_width_bits)
    if count_width_bits % OCTET_BITS:
        raise ValueError(
            "a %d bit count field is not a whole number of octets" % count_width_bits
        )
    count_size = count_width_bits // OCTET_BITS
    if len(buffer) < count_size:
        raise ValueError(
            "buffer of %d octets is too short for a %d octet count field"
            % (len(buffer), count_size)
        )
    announced = int.from_bytes(buffer[:count_size], "big")
    available = len(buffer) - count_size
    if announced > available:
        raise ValueError(
            "the count field announces %d octets and only %d follow; the "
            "payload is truncated" % (announced, available)
        )
    return {
        "payload": buffer[count_size : count_size + announced],
        "length_octets": announced,
        "consumed_octets": count_size + announced,
        "trailing_octets": available - announced,
    }


def payloads_are_equal(left, right):
    """Two payloads match only when their lengths and octets both match.

    An octet-string is opaque, so no normalisation, trimming or case
    folding is applied before the comparison.
    """
    return validate_octets(left) == validate_octets(right)


def assess_octet_string_field(spec):
    """Full clause 7.3.8 assessment of one octet-string parameter."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    payload = validate_octets(spec.get("payload"))
    format_code = _require_integer("format_code", spec.get("format_code"))
    if format_code < 0:
        raise ValueError("format_code must not be negative, got %d" % format_code)
    findings = []
    variable = format_code == VARIABLE_FORMAT_CODE
    if variable:
        count_width_bits = validate_count_width(spec.get("count_width_bits"))
        ceiling = max_length_for_count_width(count_width_bits)
        overhead = (count_width_bits + OCTET_BITS - 1) // OCTET_BITS
        if len(payload) > ceiling:
            verdict = VERDICT_COUNT_FIELD_TOO_NARROW
            findings.append(
                "a %d bit count field announces at most %d octets; the payload "
                "is %d" % (count_width_bits, ceiling, len(payload))
            )
        else:
            verdict = VERDICT_VALID
        if len(payload) == 0:
            findings.append(
                "a zero-length payload is legitimate for a variable field; the "
                "count field carries zero and no payload octet follows"
            )
        field_octets = overhead + len(payload)
    else:
        count_width_bits = None
        declared = validate_fixed_length(format_code)
        field_octets = declared
        if len(payload) == 0:
            verdict = VERDICT_EMPTY_FIXED
            findings.append(
                "a fixed field of %d octets cannot carry an empty payload"
                % declared
            )
        elif len(payload) != declared:
            verdict = VERDICT_LENGTH_MISMATCH
            findings.append(
                "payload is %d octets against a fixed field of %d; a fixed "
                "field is neither padded out nor truncated to fit"
                % (len(payload), declared)
            )
        else:
            verdict = VERDICT_VALID
    findings.append(
        "the payload is opaque: no character set, byte order or numeric "
        "reading is imposed on its %d octet(s) by this parameter type"
        % len(payload)
    )
    return {
        "ptc": OCTET_STRING_PTC,
        "format_code": format_code,
        "variable_length": variable,
        "length_octets": len(payload),
        "count_width_bits": count_width_bits,
        "pad_octets": padding_octets(len(payload)),
        "field_octets": field_octets,
        "payload_bits": field_size_bits(len(payload)),
        "verdict": verdict,
        "findings": findings,
    }
