#!/usr/bin/env python3
"""ARINC 429 digital information transfer word logic (paraphrase, summary only).

Common-knowledge summary (standards-map.yaml, arinc-429: proprietary
ARINC/SAE ITC, summary-only): ARINC 429 (Mark 33 DITS) transfers 32-bit
words point-to-point over a twisted shielded pair at 12.5 or 100 kbps,
with one transmitter and up to 20 receivers on a bus. Each word is sent
least-significant bit first. In ARINC bit numbering (1 = first bit
transmitted), bits 1-8 hold the octal label, bits 9-10 the SDI
(source/destination identifier), bits 11-29 the 19-bit data field,
bits 30-31 the SSM (sign/status matrix), and bit 32 the odd parity bit.
The full word-format tables, label assignments, and equipment
identification tables are standard data in the current revision and are
NOT reproduced here; this module implements the bit layout, odd parity,
and BNR (binary) and BCD coding helpers used for typical parameters.

Integer convention: bit 0 of the integer is the least significant bit
and the first bit transmitted (ARINC bit 1). So label occupies integer
bits 0-7, SDI bits 8-9, data bits 10-28, SSM bits 29-30, parity bit 31.

Worked anchors (verified by test_arinc429_logic.py):
- parse_label("010") -> 8
- build_word(0o10, 1, 1234, 3) -> 1611876616 (0x60134908), odd parity
- decode_word(1611876616) round-trips label 8, sdi 1, data 1234, ssm 3
- bnr_encode(123.4, 0.1) -> 1234; bnr_decode(1234, 0.1) -> 123.4
- bnr_encode(-12.3, 0.1) -> 524165; decodes back to -12.3
- bcd_encode(1234) -> 4660; bcd_decode(4660) -> 1234
"""

import re

LABEL_MASK = 0xFF          # bits 0-7   (ARINC bits 1-8)
SDI_MASK = 0b11            # bits 8-9   (ARINC bits 9-10)
DATA_MASK = 0x7FFFF        # bits 10-28 (ARINC bits 11-29)
SSM_MASK = 0b11            # bits 29-30 (ARINC bits 30-31)
PARITY_BIT = 31            # bit 31     (ARINC bit 32)
DATA_MAX = DATA_MASK
BNR_SIGN_BIT = 1 << 18     # data bit 18 (MSB of the 19-bit field)
BNR_POS_MAX = (1 << 18) - 1
BNR_NEG_MIN = -(1 << 18)

OCTAL_LABEL_RE = re.compile(r"^[0-7]+$")


def _number(value, name):
    """Return float(value) for real numbers; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def _require_int(value, name, lo, hi):
    """Return value when it is an int in [lo, hi]; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if not (lo <= value <= hi):
        raise ValueError(
            "%s %d out of range [%d, %d]" % (name, value, lo, hi)
        )
    return value


def parse_label(label):
    """Normalize a label to its 8-bit value.

    Accepts an int (0-255) or an octal string such as "010" or "377".
    Raises ValueError when the label is not 8-bit or not valid octal.
    """
    if isinstance(label, str):
        text = label.strip()
        if not OCTAL_LABEL_RE.match(text):
            raise ValueError(
                "label %r is not octal digits (0-7)" % (label,)
            )
        label = int(text, 8)
    return _require_int(label, "label", 0, LABEL_MASK)


def odd_parity_bit(payload):
    """Parity bit (0 or 1) that makes the 31-bit payload odd-parity.

    The payload holds integer bits 0-30 (label, SDI, data, SSM); the
    returned bit goes in bit 31 so the full 32-bit word has an odd
    number of 1 bits.
    """
    return 0 if (bin(payload & 0x7FFFFFFF).count("1") % 2) else 1


def build_word(label, sdi, data, ssm, parity=None):
    """Pack label, SDI, data field, SSM, and parity into a 32-bit word.

    All bounds are validated (label 0-255 octal, SDI 0-3, data 0-524287,
    SSM 0-3); ValueError is raised for out-of-range fields. When parity
    is None the odd parity bit is computed; otherwise the given parity
    bit (0 or 1) is validated and placed in bit 31.
    """
    label = parse_label(label)
    sdi = _require_int(sdi, "sdi", 0, SDI_MASK)
    data = _require_int(data, "data", 0, DATA_MAX)
    ssm = _require_int(ssm, "ssm", 0, SSM_MASK)
    payload = label | (sdi << 8) | (data << 10) | (ssm << 29)
    if parity is None:
        parity = odd_parity_bit(payload)
    else:
        parity = _require_int(parity, "parity", 0, 1)
    return payload | (parity << PARITY_BIT)


def decode_word(word):
    """Split a 32-bit word into its fields.

    Returns a dict with label, sdi, data, ssm, parity, and parity_ok
    (True when the word has odd parity). Raises ValueError when the word
    is not a 32-bit integer.
    """
    word = _require_int(word, "word", 0, 0xFFFFFFFF)
    return {
        "label": word & LABEL_MASK,
        "sdi": (word >> 8) & SDI_MASK,
        "data": (word >> 10) & DATA_MASK,
        "ssm": (word >> 29) & SSM_MASK,
        "parity": (word >> PARITY_BIT) & 1,
        "parity_ok": (bin(word).count("1") % 2) == 1,
    }


def bnr_encode(value, scale_factor):
    """Encode a signed BNR value into the 19-bit data field.

    ARINC 429 BNR data is two's complement with the data MSB (bit 18 of
    the field) as the sign bit; the least significant bit weight is the
    scale factor (for example 0.1 for a 0.1-unit LSB). Worked anchor:
    123.4 at scale 0.1 -> field 1234. Raises ValueError when the value
    does not fit the 19-bit signed range [-2^18, 2^18 - 1] times the
    scale, or when inputs are invalid.
    """
    value = _number(value, "value")
    scale = _number(scale_factor, "scale_factor")
    if scale <= 0.0:
        raise ValueError("scale_factor must be positive, got %r" % (scale,))
    raw = int(round(value / scale))
    if not (BNR_NEG_MIN <= raw <= BNR_POS_MAX):
        raise ValueError(
            "value %.6f does not fit BNR range [%.6f, %.6f] at scale %.6f"
            % (value, BNR_NEG_MIN * scale, BNR_POS_MAX * scale, scale)
        )
    if raw < 0:
        raw += 1 << 19
    return raw


def bnr_decode(data_field, scale_factor):
    """Decode a 19-bit BNR data field to its signed value.

    Worked anchor: field 1234 at scale 0.1 -> 123.4; field 524165 at
    scale 0.1 -> -12.3 (two's complement). Raises ValueError on invalid
    field or scale.
    """
    data_field = _require_int(data_field, "data_field", 0, DATA_MAX)
    scale = _number(scale_factor, "scale_factor")
    if scale <= 0.0:
        raise ValueError("scale_factor must be positive, got %r" % (scale,))
    raw = data_field - (1 << 19) if data_field & BNR_SIGN_BIT else data_field
    return raw * scale


def bcd_encode(value, digits=5):
    """Encode a non-negative integer into BCD digits in the data field.

    Four digits occupy the low 16 field bits; the optional fifth digit
    (most significant, 0-7) uses the top 3 bits of the 19-bit field.
    Worked anchor: 1234 with digits=5 -> field 4660. Raises ValueError
    when the value has a non-decimal digit (values above 9999 for 4
    digits, above 79999 for 5 digits) or inputs are invalid.
    """
    digits = _require_int(digits, "digits", 4, 5)
    value = _require_int(value, "value", 0, 10 ** digits - 1)
    max_value = 79999 if digits == 5 else 9999
    if value > max_value:
        raise ValueError(
            "value %d exceeds %d-digit BCD capacity %d" % (value, digits, max_value)
        )
    field = 0
    remaining = value
    for i in range(digits):
        field |= (remaining % 10) << (4 * i)
        remaining //= 10
    return field


def bcd_decode(data_field, digits=5):
    """Decode BCD digits from the data field back to an integer.

    Worked anchor: field 4660 with digits=5 -> 1234. Raises ValueError
    when a digit is not 0-9 (or the fifth digit is not 0-7) or when the
    field or digits are invalid.
    """
    data_field = _require_int(data_field, "data_field", 0, DATA_MAX)
    digits = _require_int(digits, "digits", 4, 5)
    value = 0
    for i in range(digits):
        digit = (data_field >> (4 * i)) & 0xF
        if digit > 9:
            raise ValueError(
                "digit %d of the BCD field is %d, not 0-9" % (i + 1, digit)
            )
        if digits == 5 and i == 4 and digit > 7:
            raise ValueError(
                "fifth BCD digit %d exceeds the 3-bit capacity 7" % digit
            )
        value += digit * (10 ** i)
    return value
