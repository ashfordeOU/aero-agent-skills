"""Error detection on the data units of a space transfer protocol.

Anchor: ECSS-E-ST-50C clause 5.6.13.4 -- error detection on transferred data
units. Paraphrased into an implementable procedure; no standard text is
reproduced.

Three normative items sit in the clause and they fail independently:

  presence  -- every transferred data unit carries an error detection code;
  coverage  -- the code is computed over the whole unit, header included, not
               over the payload alone;
  strength  -- the units the code lets through undetected stay inside the bound
               the mission has set.

The procedure here grades all three, and where strength fails it names the
weakest catalogue code that would meet the bound on the same channel.

Numerics: the probability that a unit arrives corrupted is one minus the chance
every bit survives. At the bit error rates a space link runs at, evaluating that
as a direct subtraction cancels nearly every significant digit, so it is
computed through log1p and expm1 instead.

Stdlib only, offline, deterministic.
"""

import math

# Escape fraction of each catalogue code: the share of corrupted units whose
# error pattern the code fails to notice, taken as two to the minus width for
# budget work. This is a budget figure, not a burst-length guarantee; a burst
# analysis of the actual polynomial belongs alongside it.
CODE_WIDTH_BITS = {
    "none": 0,
    "parity": 1,
    "checksum-8": 8,
    "checksum-16": 16,
    "crc-16": 16,
    "crc-24": 24,
    "crc-32": 32,
}

# Catalogue order from weakest to strongest, used to name a sufficient code.
CODE_STRENGTH_ORDER = (
    "parity",
    "checksum-8",
    "checksum-16",
    "crc-16",
    "crc-24",
    "crc-32",
)

COVER_NONE = "none"
COVER_PAYLOAD = "payload"
COVER_WHOLE_UNIT = "whole-unit"
VALID_COVERAGE = (COVER_NONE, COVER_PAYLOAD, COVER_WHOLE_UNIT)

COMPLIANT = "compliant"
NON_COMPLIANT = "non-compliant"

# Relative tolerance for the bound comparison, so a design landing exactly on
# the bound decides the same way on every platform.
REL_TOL = 1e-9

__all__ = [
    "CODE_WIDTH_BITS",
    "CODE_STRENGTH_ORDER",
    "COVER_NONE",
    "COVER_PAYLOAD",
    "COVER_WHOLE_UNIT",
    "VALID_COVERAGE",
    "COMPLIANT",
    "NON_COMPLIANT",
    "REL_TOL",
    "validate_code",
    "validate_coverage",
    "validate_length_bits",
    "validate_probability",
    "escape_fraction",
    "corruption_probability",
    "undetected_probability",
    "undetected_units_per_pass",
    "weakest_sufficient_code",
    "assess_error_detection",
]


def validate_code(value, name="code"):
    """Return a recognised error detection code name."""
    if value not in CODE_WIDTH_BITS:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, sorted(CODE_WIDTH_BITS), value)
        )
    return value


def validate_coverage(value, name="coverage"):
    """Return a recognised statement of what the code is computed over."""
    if value not in VALID_COVERAGE:
        raise ValueError("%s must be one of %s, got %r" % (name, list(VALID_COVERAGE), value))
    return value


def validate_length_bits(value, name="unit_bits"):
    """Return a strictly positive integer length in bits."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer number of bits" % name)
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def validate_probability(value, name="bit_error_rate"):
    """Return a probability in the closed interval zero to one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def escape_fraction(code):
    """Return the share of corrupted units this code fails to notice.

    A unit with no code notices nothing, so every corruption escapes.
    """
    name = validate_code(code)
    width = CODE_WIDTH_BITS[name]
    if width == 0:
        return 1.0
    return 1.0 / float(1 << width)


def corruption_probability(unit_bits, bit_error_rate):
    """Return the probability that a unit of this length arrives corrupted.

    Computed through log1p and expm1 so the result keeps its significant digits
    at the small bit error rates a real space link runs at.
    """
    length = validate_length_bits(unit_bits)
    ber = validate_probability(bit_error_rate)
    if ber == 0.0:
        return 0.0
    if ber == 1.0:
        return 1.0
    return -math.expm1(length * math.log1p(-ber))


def undetected_probability(unit_bits, bit_error_rate, code):
    """Return the probability that a unit arrives corrupted and is accepted."""
    return corruption_probability(unit_bits, bit_error_rate) * escape_fraction(code)


def undetected_units_per_pass(unit_bits, bit_error_rate, code, units_in_pass):
    """Return the units expected to be accepted corrupted across one pass."""
    count = validate_length_bits(units_in_pass, "units_in_pass")
    return undetected_probability(unit_bits, bit_error_rate, code) * float(count)


def weakest_sufficient_code(unit_bits, bit_error_rate, bound_per_unit):
    """Return the weakest catalogue code meeting the per-unit bound.

    None means no catalogue code is strong enough on this channel, which is a
    real answer: the fix is then a shorter unit or a better channel, not a wider
    code word.
    """
    limit = validate_probability(bound_per_unit, "bound_per_unit")
    for candidate in CODE_STRENGTH_ORDER:
        value = undetected_probability(unit_bits, bit_error_rate, candidate)
        if value <= limit + REL_TOL * limit:
            return candidate
    return None


def assess_error_detection(
    unit_bits,
    header_bits,
    code,
    coverage,
    bit_error_rate,
    bound_per_unit,
    units_in_pass=1,
):
    """Assess one data unit design against the three obligations of the clause."""
    length = validate_length_bits(unit_bits)
    header = validate_length_bits(header_bits, "header_bits")
    name = validate_code(code)
    extent = validate_coverage(coverage)
    ber = validate_probability(bit_error_rate)
    limit = validate_probability(bound_per_unit, "bound_per_unit")
    count = validate_length_bits(units_in_pass, "units_in_pass")
    if header >= length:
        raise ValueError(
            "header_bits %d must be smaller than unit_bits %d" % (header, length)
        )

    findings = []
    code_present = name != "none" and extent != COVER_NONE
    if not code_present:
        findings.append(
            "no error detection code is applied to the data unit; corrupted units are "
            "accepted as sound"
        )
    covers_header = extent == COVER_WHOLE_UNIT
    if code_present and not covers_header:
        findings.append(
            "the code covers the payload only; the %d header bits are unprotected and a "
            "corrupted destination or length field is acted on as sound" % header
        )

    corrupted = corruption_probability(length, ber)
    escaped = escape_fraction(name if code_present else "none")
    per_unit = corrupted * escaped
    per_pass = per_unit * float(count)
    within_bound = per_unit <= limit + REL_TOL * limit
    sufficient = weakest_sufficient_code(length, ber, limit)
    if not within_bound:
        if sufficient is None:
            findings.append(
                "undetected probability %.6g per unit exceeds the bound %.6g and no "
                "catalogue code closes it; shorten the unit or improve the channel"
                % (per_unit, limit)
            )
        else:
            findings.append(
                "undetected probability %.6g per unit exceeds the bound %.6g; %s meets it "
                "on this channel" % (per_unit, limit, sufficient)
            )

    obligations = {
        "code_present": code_present,
        "covers_whole_unit": covers_header,
        "within_bound": within_bound,
    }
    verdict = COMPLIANT if all(obligations.values()) else NON_COMPLIANT
    return {
        "unit_bits": length,
        "header_bits": header,
        "payload_bits": length - header,
        "code": name,
        "coverage": extent,
        "bit_error_rate": ber,
        "corruption_probability": corrupted,
        "escape_fraction": escaped,
        "undetected_per_unit": per_unit,
        "undetected_per_pass": per_pass,
        "bound_per_unit": limit,
        "units_in_pass": count,
        "obligations": obligations,
        "weakest_sufficient_code": sufficient,
        "verdict": verdict,
        "findings": findings,
    }
