"""Data unit identifier scheme assessment for a space link.

Anchor: ECSS-E-ST-50C clause 5.6.13.2 -- requirements on the identifier each
data unit carries. Paraphrased into an implementable procedure; no standard
text is reproduced.

One normative obligation is implemented: every data unit carries an identifier
that names it unambiguously for as long as that unit matters. A counter in a
fixed-width field satisfies that only while it has not wrapped inside the
window the system still cares about the unit -- retransmission, reordering,
gap filling or ground-side reconciliation. Once the wrap period is shorter than
that window, two live units share one identifier and every downstream decision
built on the identifier is built on a coin toss.

Field arithmetic is exact integer work. The one place a rate and a window meet
is compared with a relative tolerance, so a scheme sized exactly to its window
is decided the same way on every platform.
"""

import math

__all__ = [
    "UNAMBIGUOUS",
    "MARGIN_SHORT",
    "AMBIGUOUS",
    "MAX_WIDTH_BITS",
    "REL_TOL",
    "DEFAULT_MARGIN_FACTOR",
    "validate_width_bits",
    "validate_positive",
    "identifier_modulus",
    "wrap_period_s",
    "units_in_window",
    "minimum_width_bits",
    "assess_identifier_scheme",
    "analyse_observed_sequence",
]

UNAMBIGUOUS = "unambiguous"
MARGIN_SHORT = "margin-short"
AMBIGUOUS = "ambiguous"

# A counter field wider than this is not a counter, it is a mistyped constant.
MAX_WIDTH_BITS = 64

REL_TOL = 1e-9

# How many times over the field should cover the window before the scheme is
# called comfortable. A field that wraps exactly once per window has no room
# for a retransmission, a stretched pass or a slower ground turnaround.
DEFAULT_MARGIN_FACTOR = 2.0


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive magnitude."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_width_bits(value, name="width_bits"):
    """Return an identifier field width in bits."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer number of bits, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    if value > MAX_WIDTH_BITS:
        raise ValueError(
            "%s must not exceed %d, got %r" % (name, MAX_WIDTH_BITS, value)
        )
    return value


def identifier_modulus(width_bits):
    """Return how many distinct identifiers the field holds before it repeats."""
    return 2 ** validate_width_bits(width_bits)


def wrap_period_s(width_bits, production_rate_per_s):
    """Return how long the field takes to come back to the same identifier."""
    modulus = identifier_modulus(width_bits)
    rate = validate_positive(production_rate_per_s, "production_rate_per_s")
    return modulus / rate


def units_in_window(production_rate_per_s, window_s):
    """Return how many data units are live inside the window that matters."""
    rate = validate_positive(production_rate_per_s, "production_rate_per_s")
    window = validate_positive(window_s, "window_s")
    return rate * window


def minimum_width_bits(
    production_rate_per_s, window_s, margin_factor=DEFAULT_MARGIN_FACTOR
):
    """Return the narrowest field that covers the window with the margin asked for.

    The search doubles an integer capacity rather than taking a logarithm, so
    the answer is exact and identical on every platform instead of landing on
    either side of a power of two depending on how the library rounded.
    """
    needed = units_in_window(production_rate_per_s, window_s)
    factor = validate_positive(margin_factor, "margin_factor")
    if factor < 1.0:
        raise ValueError("margin_factor must be at least 1.0, got %r" % (margin_factor,))
    target = needed * factor
    capacity = 1
    width = 0
    while width < MAX_WIDTH_BITS:
        if capacity >= target * (1.0 - REL_TOL):
            return max(1, width)
        capacity *= 2
        width += 1
    raise ValueError(
        "no field up to %d bits covers %.6g units; the retention window or the "
        "production rate has to change" % (MAX_WIDTH_BITS, target)
    )


def assess_identifier_scheme(
    width_bits,
    production_rate_per_s,
    retention_window_s,
    margin_factor=DEFAULT_MARGIN_FACTOR,
):
    """Assess whether a counter field identifies its data units unambiguously.

    Three outcomes are separated: the field covers the retention window with
    the margin asked for; it covers the window but with less margin than that;
    or it wraps inside the window, at which point two live data units share one
    identifier.
    """
    modulus = identifier_modulus(width_bits)
    rate = validate_positive(production_rate_per_s, "production_rate_per_s")
    window = validate_positive(retention_window_s, "retention_window_s")
    factor = validate_positive(margin_factor, "margin_factor")
    if factor < 1.0:
        raise ValueError("margin_factor must be at least 1.0, got %r" % (margin_factor,))

    live = rate * window
    period = modulus / rate
    coverage = modulus / live
    tolerance = REL_TOL * max(1.0, coverage)

    if coverage < 1.0 - tolerance:
        verdict = AMBIGUOUS
    elif coverage < factor - tolerance:
        verdict = MARGIN_SHORT
    else:
        verdict = UNAMBIGUOUS

    findings = []
    if verdict == AMBIGUOUS:
        findings.append(
            "the field wraps every %.6g s inside a %.6g s window; %.6g live data "
            "units would share one identifier" % (period, window, live - modulus)
        )
    elif verdict == MARGIN_SHORT:
        findings.append(
            "the field covers the window only %.6g times over, short of the %.6g "
            "asked for" % (coverage, factor)
        )

    return {
        "width_bits": validate_width_bits(width_bits),
        "modulus": modulus,
        "production_rate_per_s": rate,
        "retention_window_s": window,
        "live_units": live,
        "wrap_period_s": period,
        "coverage": coverage,
        "unambiguous": coverage >= 1.0 - tolerance,
        "recommended_width_bits": minimum_width_bits(rate, window, factor),
        "verdict": verdict,
        "findings": findings,
    }


def analyse_observed_sequence(observed, width_bits):
    """Report what an observed run of identifiers says about the data units.

    Counts wraps, names the missing identifiers as gaps, names identifiers seen
    more than once, and rejects a value the field could never have carried --
    which is a decoding fault, not a lost unit, and must not be reported as a
    gap.
    """
    modulus = identifier_modulus(width_bits)
    if isinstance(observed, dict) or not isinstance(observed, (list, tuple)):
        raise ValueError("observed must be a list or tuple of identifiers")
    if not observed:
        raise ValueError("observed must not be empty")

    values = []
    for item in observed:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("observed identifiers must be integers, got %r" % (item,))
        if item < 0 or item >= modulus:
            raise ValueError(
                "observed identifier %r does not fit a %d-bit field"
                % (item, validate_width_bits(width_bits))
            )
        values.append(item)

    seen = {}
    duplicates = []
    for value in values:
        seen[value] = seen.get(value, 0) + 1
    for value in sorted(seen):
        if seen[value] > 1:
            duplicates.append(value)

    gaps = []
    wraps = 0
    for index in range(1, len(values)):
        previous = values[index - 1]
        current = values[index]
        step = (current - previous) % modulus
        if current < previous:
            # A counter that went backwards has come round the field. A repeat
            # of the same value has not -- that is a duplicate, and counting it
            # as a wrap would inflate how many units the run covers.
            wraps += 1
        if step == 0:
            continue
        for offset in range(1, step):
            gaps.append((previous + offset) % modulus)

    return {
        "width_bits": validate_width_bits(width_bits),
        "modulus": modulus,
        "observed_count": len(values),
        "distinct_count": len(seen),
        "wrap_count": wraps,
        "gaps": gaps,
        "missing_count": len(gaps),
        "duplicates": duplicates,
        "contiguous": not gaps and not duplicates,
        "expected_next": (values[-1] + 1) % modulus,
    }
