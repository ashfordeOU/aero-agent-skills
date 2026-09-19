#!/usr/bin/env python3
"""Real parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A real parameter carries a floating point value in one of the defined
floating encodings, and the parameter's format code says which. Two
things follow, and together they are the clause's job:

    the encoding is chosen, not assumed -- the width it occupies and
    the relative precision it can hold are properties of the chosen
    encoding, and the parameter's required range and resolution have
    to fit inside both; and
    a value the chosen encoding cannot hold is reported rather than
    silently rounded, overflowed to infinity or underflowed to zero.

Numerics here go through struct and math.ldexp only. Both are exact
binary operations, so the same bit pattern and the same reported error
come back on every platform. Nothing is computed through a power of
ten or a logarithm.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
import struct

REAL_PTC = 5

SINGLE = "ieee754-single"
DOUBLE = "ieee754-double"

REAL_ENCODINGS = {
    SINGLE: {"format": ">f", "octets": 4, "mantissa_bits": 24},
    DOUBLE: {"format": ">d", "octets": 8, "mantissa_bits": 53},
}

# Encodings ordered narrowest first: the selection walks this order and
# takes the first that can carry the parameter.
ENCODING_ORDER = (SINGLE, DOUBLE)

VERDICT_REPRESENTABLE = "real-value-representable"
VERDICT_ROUNDED = "real-value-rounded"
VERDICT_OVERFLOWS = "real-value-overflows-encoding"
VERDICT_UNDERFLOWS = "real-value-underflows-to-zero"

_REL_TOL = 1e-9
_ABS_TOL = 1e-300


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_finite(name, value):
    if not _is_number(value):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(
            "%s must be finite; a real parameter field carries no infinity or "
            "not-a-number code, got %r" % (name, value)
        )
    return value


def _require_positive(name, value):
    value = _require_finite(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def validate_encoding(encoding):
    """Check the named floating encoding is one this clause offers."""
    if encoding not in REAL_ENCODINGS:
        raise ValueError(
            "encoding must be one of %s, got %r"
            % (", ".join(sorted(REAL_ENCODINGS)), encoding)
        )
    return encoding


def encoding_octets(encoding):
    """Field width of the encoding, in octets."""
    validate_encoding(encoding)
    return REAL_ENCODINGS[encoding]["octets"]


def relative_resolution(encoding):
    """Smallest relative step the encoding can resolve.

    Computed with math.ldexp, which is an exact binary scaling, so the
    value is bit-identical on every platform.
    """
    validate_encoding(encoding)
    return math.ldexp(1.0, -(REAL_ENCODINGS[encoding]["mantissa_bits"] - 1))


def largest_finite(encoding):
    """Largest finite magnitude the encoding can carry."""
    validate_encoding(encoding)
    if encoding == DOUBLE:
        return struct.unpack(">d", b"\x7f\xef\xff\xff\xff\xff\xff\xff")[0]
    return struct.unpack(">f", b"\x7f\x7f\xff\xff")[0]


def smallest_normal(encoding):
    """Smallest magnitude the encoding holds at full precision."""
    validate_encoding(encoding)
    if encoding == DOUBLE:
        return struct.unpack(">d", b"\x00\x10\x00\x00\x00\x00\x00\x00")[0]
    return struct.unpack(">f", b"\x00\x80\x00\x00")[0]


def encode_real(value, encoding):
    """Octets for the value in the chosen encoding, big endian.

    A magnitude the encoding cannot hold is refused rather than
    written out as an infinity code.
    """
    value = _require_finite("value", value)
    validate_encoding(encoding)
    try:
        return struct.pack(REAL_ENCODINGS[encoding]["format"], value)
    except OverflowError as error:
        raise ValueError(
            "value %r overflows %s, whose largest finite magnitude is %r (%s)"
            % (value, encoding, largest_finite(encoding), error)
        )


def decode_real(octets, encoding):
    """Value carried by a big-endian octet run in the chosen encoding."""
    validate_encoding(encoding)
    if not isinstance(octets, (bytes, bytearray)):
        raise ValueError("octets must be bytes, got %r" % (octets,))
    expected = encoding_octets(encoding)
    if len(octets) != expected:
        raise ValueError(
            "%s occupies %d octets, got %d" % (encoding, expected, len(octets))
        )
    return struct.unpack(REAL_ENCODINGS[encoding]["format"], bytes(octets))[0]


def round_trip(value, encoding):
    """Value that comes back after a trip through the encoding."""
    return decode_real(encode_real(value, encoding), encoding)


def is_exactly_representable(value, encoding):
    """True when the encoding stores the value with no rounding at all."""
    value = _require_finite("value", value)
    return round_trip(value, encoding) == value


def round_trip_error(value, encoding):
    """Absolute and relative error the encoding introduces."""
    value = _require_finite("value", value)
    stored = round_trip(value, encoding)
    absolute = abs(stored - value)
    if value == 0.0:
        relative = 0.0
    else:
        relative = absolute / abs(value)
    return {
        "stored": stored,
        "absolute_error": absolute,
        "relative_error": relative,
        "exact": stored == value,
    }


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def select_real_encoding(max_abs_value, required_relative_precision):
    """Narrowest encoding that carries the range and the precision.

    Both tests are inequalities against exactly representable binary
    bounds, and the comparison absorbs representation error so a
    parameter that sits exactly on an encoding's resolution selects
    that encoding rather than the next one up.
    """
    max_abs_value = _require_finite("max_abs_value", max_abs_value)
    if max_abs_value < 0.0:
        raise ValueError(
            "max_abs_value is a magnitude and must not be negative, got %r"
            % max_abs_value
        )
    required = _require_positive(
        "required_relative_precision", required_relative_precision
    )
    for encoding in ENCODING_ORDER:
        range_ok = max_abs_value <= largest_finite(encoding) or math.isclose(
            max_abs_value, largest_finite(encoding), rel_tol=_REL_TOL
        )
        precision_ok = _at_least(required, relative_resolution(encoding))
        if range_ok and precision_ok:
            return encoding
    raise ValueError(
        "no offered real encoding carries a magnitude of %r at a relative "
        "precision of %r" % (max_abs_value, required)
    )


def assess_real_field(spec):
    """Full clause 7.3.6 assessment of one real parameter value."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    encoding = validate_encoding(spec.get("encoding"))
    value = _require_finite("value", spec.get("value"))
    findings = []
    if abs(value) > largest_finite(encoding):
        return {
            "ptc": REAL_PTC,
            "encoding": encoding,
            "octets": encoding_octets(encoding),
            "value": value,
            "stored": None,
            "absolute_error": None,
            "relative_error": None,
            "verdict": VERDICT_OVERFLOWS,
            "findings": [
                "magnitude %r is past the largest finite value %s holds (%r); "
                "packing it would write an infinity code"
                % (abs(value), encoding, largest_finite(encoding))
            ],
        }
    error = round_trip_error(value, encoding)
    if value != 0.0 and error["stored"] == 0.0:
        verdict = VERDICT_UNDERFLOWS
        findings.append(
            "magnitude %r is below what %s can hold and stores as zero; the "
            "smallest value it holds at full precision is %r"
            % (abs(value), encoding, smallest_normal(encoding))
        )
    elif error["exact"]:
        verdict = VERDICT_REPRESENTABLE
    else:
        verdict = VERDICT_ROUNDED
        findings.append(
            "the value is stored as %r, a relative error of %r against a "
            "resolution of %r"
            % (error["stored"], error["relative_error"], relative_resolution(encoding))
        )
    if value != 0.0 and abs(value) < smallest_normal(encoding):
        findings.append(
            "magnitude %r is below the smallest value %s holds at full "
            "precision, so the resolution figure no longer applies"
            % (abs(value), encoding)
        )
    return {
        "ptc": REAL_PTC,
        "encoding": encoding,
        "octets": encoding_octets(encoding),
        "value": value,
        "stored": error["stored"],
        "absolute_error": error["absolute_error"],
        "relative_error": error["relative_error"],
        "verdict": verdict,
        "findings": findings,
    }
