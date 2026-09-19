#!/usr/bin/env python3
"""Enumerated parameter type for a packet utilisation data field.

Anchor: ECSS-E-ST-70-41C clause 7.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An enumerated parameter carries one symbol out of a declared set. The
symbol is not transmitted; an unsigned binary code standing for it is,
in a field whose width the parameter's format code fixes. Two things
follow, and they are the whole of the clause's job:

    the declared symbol set has to fit in the coded field, and
    a received code outside the declared set is undefined -- it is
    reported as undefined, never quietly resolved to a default symbol.

Everything here is exact integer arithmetic on bit widths, so the same
answer comes back on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

ENUMERATED_PTC = 2

MIN_FIELD_WIDTH_BITS = 1
MAX_FIELD_WIDTH_BITS = 64

VERDICT_VALID = "enumeration-valid"
VERDICT_OVERFLOWS_FIELD = "enumeration-overflows-field"
VERDICT_NO_HEADROOM = "enumeration-has-no-spare-codes"


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_integer(name, value):
    if not _is_integer(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def validate_field_width(width_bits):
    """Width of the coded field, as the format code fixes it."""
    _require_integer("width_bits", width_bits)
    if width_bits < MIN_FIELD_WIDTH_BITS or width_bits > MAX_FIELD_WIDTH_BITS:
        raise ValueError(
            "width_bits must be between %d and %d, got %d"
            % (MIN_FIELD_WIDTH_BITS, MAX_FIELD_WIDTH_BITS, width_bits)
        )
    return width_bits


def code_capacity(width_bits):
    """How many distinct codes a field of this width can carry."""
    validate_field_width(width_bits)
    return 1 << width_bits


def minimum_width_bits(symbol_count):
    """Narrowest field that still holds this many distinct symbols.

    Exact integer arithmetic: the answer is the bit length of the
    largest code needed, never a rounded logarithm.
    """
    _require_integer("symbol_count", symbol_count)
    if symbol_count < 1:
        raise ValueError("symbol_count must be at least 1, got %d" % symbol_count)
    if symbol_count == 1:
        return MIN_FIELD_WIDTH_BITS
    return (symbol_count - 1).bit_length()


def validate_symbol_table(symbols):
    """Check a code-to-symbol mapping is usable before anything is coded."""
    if not isinstance(symbols, dict):
        raise ValueError("symbols must be a mapping of code to name, got %r" % (symbols,))
    if not symbols:
        raise ValueError("symbols must declare at least one entry")
    names = set()
    for code, name in symbols.items():
        _require_integer("symbol code", code)
        if code < 0:
            raise ValueError("symbol code must not be negative, got %d" % code)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("symbol name for code %d must be a non-empty string" % code)
        if name in names:
            raise ValueError("symbol name %r is declared against two codes" % name)
        names.add(name)
    return symbols


def table_fits_field(symbols, width_bits):
    """True when every declared code is representable in the field."""
    validate_symbol_table(symbols)
    validate_field_width(width_bits)
    return max(symbols) < code_capacity(width_bits)


def encode_symbol(symbols, width_bits, name):
    """Code that carries this symbol, or a refusal."""
    validate_symbol_table(symbols)
    validate_field_width(width_bits)
    if not isinstance(name, str):
        raise ValueError("name must be a string, got %r" % (name,))
    for code, declared in symbols.items():
        if declared == name:
            if code >= code_capacity(width_bits):
                raise ValueError(
                    "symbol %r sits at code %d, outside a %d bit field"
                    % (name, code, width_bits)
                )
            return code
    raise ValueError("symbol %r is not in the declared set" % name)


def decode_code(symbols, width_bits, code):
    """Resolve a received code, reporting an undefined one as undefined.

    The undefined case is the point of the clause: a code that is not
    in the declared set carries no symbol, and substituting a default
    would invent a spacecraft state that was never reported.
    """
    validate_symbol_table(symbols)
    validate_field_width(width_bits)
    _require_integer("code", code)
    if code < 0:
        raise ValueError("code must not be negative, got %d" % code)
    if code >= code_capacity(width_bits):
        raise ValueError(
            "code %d does not fit a %d bit field" % (code, width_bits)
        )
    if code in symbols:
        return {"code": code, "symbol": symbols[code], "defined": True, "findings": []}
    return {
        "code": code,
        "symbol": None,
        "defined": False,
        "findings": [
            "code %d is not in the declared symbol set; the value is undefined "
            "and is not resolved to a default symbol" % code
        ],
    }


def spare_codes(symbols, width_bits):
    """Codes the field can carry that no symbol has claimed yet."""
    validate_symbol_table(symbols)
    validate_field_width(width_bits)
    used = set(symbols)
    return [code for code in range(code_capacity(width_bits)) if code not in used]


def round_trip_symbol(symbols, width_bits, name):
    """Encode then decode a symbol; the name must survive unchanged."""
    code = encode_symbol(symbols, width_bits, name)
    return decode_code(symbols, width_bits, code)


def assess_enumerated_field(spec):
    """Full clause 7.3.3 assessment of one enumerated parameter."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    symbols = validate_symbol_table(spec.get("symbols"))
    width_bits = validate_field_width(spec.get("width_bits"))
    findings = []
    fits = table_fits_field(symbols, width_bits)
    needed = minimum_width_bits(max(symbols) + 1)
    spares = spare_codes(symbols, width_bits)
    if not fits:
        findings.append(
            "the declared set reaches code %d, which needs a %d bit field "
            "rather than the declared %d" % (max(symbols), needed, width_bits)
        )
        verdict = VERDICT_OVERFLOWS_FIELD
    elif not spares:
        findings.append(
            "every code in the %d bit field is claimed; a new state cannot be "
            "added without widening the field" % width_bits
        )
        verdict = VERDICT_NO_HEADROOM
    else:
        verdict = VERDICT_VALID
    if fits and width_bits > needed:
        findings.append(
            "a %d bit field would hold the declared set; %d bits are declared"
            % (needed, width_bits)
        )
    return {
        "ptc": ENUMERATED_PTC,
        "width_bits": width_bits,
        "symbol_count": len(symbols),
        "capacity": code_capacity(width_bits),
        "minimum_width_bits": needed,
        "fits": fits,
        "spare_code_count": len(spares),
        "verdict": verdict,
        "findings": findings,
    }
