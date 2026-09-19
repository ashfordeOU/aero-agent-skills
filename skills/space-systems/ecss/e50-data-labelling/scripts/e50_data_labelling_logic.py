"""Labelling of the data units a space communication system carries.

Anchor: ECSS-E-ST-50C clause 5.8.2 -- data labelling.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that data carried by the communication system is
labelled so that a receiver can tell one unit from another and say where it
came from, where it is going, what it is and when it was made. A label either
does that or it does not, and the difference is arithmetic:

  coverage  -- the label fields declared against the fields a receiver needs;
  width     -- whether each identifier field is wide enough for the number of
               distinct values it has to carry, which is a bit count, not an
               opinion;
  ambiguity -- whether the sequence field wraps inside the window over which
               two units still have to be distinguishable;
  cost      -- what the label takes from the payload, as a share of the link.

Widths are computed with integer bit arithmetic rather than logarithms, so a
field sitting exactly on a power of two comes out the same on every host.
"""

import math

__all__ = [
    "SUFFICIENT",
    "DEFICIENT",
    "REQUIRED_FIELDS",
    "REL_TOL",
    "validate_positive",
    "validate_nonnegative",
    "validate_count",
    "validate_width",
    "validate_fields",
    "field_coverage",
    "required_identifier_bits",
    "addressable_values",
    "label_bits",
    "label_overhead_fraction",
    "effective_payload_bps",
    "wrap_period_s",
    "min_sequence_bits",
    "assess_labelling",
]

SUFFICIENT = "labelling-sufficient"
DEFICIENT = "labelling-deficient"

# What a receiver has to be able to read off a data unit without being told.
REQUIRED_FIELDS = frozenset(
    [
        "source-identifier",
        "destination-identifier",
        "data-type",
        "sequence-count",
        "generation-time",
    ]
)

REL_TOL = 1e-9


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_nonnegative(value, name="value"):
    """Return a non-negative float."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive float."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_count(value, name="count"):
    """Return a strictly positive whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def validate_width(value, name="width_bits"):
    """Return a field width in whole bits."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of bits" % name)
    if value <= 0:
        raise ValueError("%s must be at least one bit, got %r" % (name, value))
    return value


def validate_fields(fields):
    """Return the declared label as a name to width map."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields must be a non-empty mapping of name to width")
    normalized = {}
    for name, width in fields.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each field name must be a non-empty string")
        key = name.strip().lower()
        if key in normalized:
            raise ValueError("field %s declared twice" % key)
        normalized[key] = validate_width(width, "width of %s" % key)
    return normalized


def field_coverage(fields):
    """Compare the declared label fields against the required set."""
    declared = validate_fields(fields)
    names = set(declared)
    return {
        "present": sorted(names & REQUIRED_FIELDS),
        "missing": sorted(REQUIRED_FIELDS - names),
        "unrecognised": sorted(names - REQUIRED_FIELDS),
        "complete": not (REQUIRED_FIELDS - names),
    }


def required_identifier_bits(distinct_values):
    """Return the bits needed to name this many distinct things.

    Integer arithmetic on purpose: a count sitting exactly on a power of two is
    the case a floating-point logarithm gets wrong, and it is also the case a
    designer is most likely to have chosen.
    """
    count = validate_count(distinct_values, "distinct_values")
    if count == 1:
        return 1
    return (count - 1).bit_length()


def addressable_values(width_bits):
    """Return how many distinct values a field of this width can carry."""
    return 1 << validate_width(width_bits)


def label_bits(fields):
    """Return the total width of the declared label."""
    return sum(validate_fields(fields).values())


def label_overhead_fraction(fields, payload_bits):
    """Return the share of each data unit spent on its label."""
    label = label_bits(fields)
    payload = validate_positive(payload_bits, "payload_bits")
    return label / (label + payload)


def effective_payload_bps(capacity_bps, fields, payload_bits):
    """Return the payload rate a link of this capacity actually delivers."""
    capacity = validate_positive(capacity_bps, "capacity_bps")
    return capacity * (1.0 - label_overhead_fraction(fields, payload_bits))


def wrap_period_s(width_bits, rate_per_s):
    """Return how long a counter of this width runs before it repeats."""
    width = validate_width(width_bits)
    rate = validate_positive(rate_per_s, "rate_per_s")
    return addressable_values(width) / rate


def min_sequence_bits(rate_per_s, window_s):
    """Return the narrowest counter that stays unique across the window."""
    rate = validate_positive(rate_per_s, "rate_per_s")
    window = validate_positive(window_s, "window_s")
    exact = rate * window
    needed = int(math.ceil(exact - REL_TOL * exact))
    if needed < 1:
        needed = 1
    if needed == 1:
        return 1
    return (needed - 1).bit_length()


def assess_labelling(
    fields,
    distinct_sources,
    distinct_destinations,
    rate_per_s,
    ambiguity_window_s,
    payload_bits,
    capacity_bps,
    overhead_allowance,
):
    """Grade one declared data label against the job a receiver needs it to do."""
    declared = validate_fields(fields)
    coverage = field_coverage(declared)
    allowance = validate_positive(overhead_allowance, "overhead_allowance")
    if allowance > 1.0:
        raise ValueError("overhead_allowance must be a fraction of the data unit")
    rate = validate_positive(rate_per_s, "rate_per_s")
    window = validate_positive(ambiguity_window_s, "ambiguity_window_s")

    findings = []
    widths = []
    for field, distinct in (
        ("source-identifier", distinct_sources),
        ("destination-identifier", distinct_destinations),
    ):
        needed = required_identifier_bits(distinct)
        declared_width = declared.get(field)
        wide_enough = declared_width is not None and declared_width >= needed
        widths.append(
            {
                "field": field,
                "declared_bits": declared_width,
                "required_bits": needed,
                "addressable": addressable_values(declared_width)
                if declared_width
                else 0,
                "distinct_values": validate_count(distinct, "distinct_values"),
                "wide_enough": wide_enough,
            }
        )
        if declared_width is not None and not wide_enough:
            findings.append(
                "%s is %d bit and names %d of %d things; %d bit is the narrowest "
                "field that carries them all"
                % (
                    field,
                    declared_width,
                    addressable_values(declared_width),
                    validate_count(distinct, "distinct_values"),
                    needed,
                )
            )

    sequence_width = declared.get("sequence-count")
    needed_sequence = min_sequence_bits(rate, window)
    if sequence_width is None:
        sequence_ok = False
        wrap = None
    else:
        wrap = wrap_period_s(sequence_width, rate)
        sequence_ok = sequence_width >= needed_sequence
        if not sequence_ok:
            findings.append(
                "sequence-count repeats every %.6g s inside a %.6g s window in "
                "which two units still have to be told apart; %d bit closes it"
                % (wrap, window, needed_sequence)
            )

    overhead = label_overhead_fraction(declared, payload_bits)
    overhead_ok = overhead <= allowance + REL_TOL * allowance
    if not overhead_ok:
        findings.append(
            "the label takes %.6g of each data unit against a %.6g allowance; "
            "at this label size the data unit has to carry at least %.6g bit "
            "of payload"
            % (
                overhead,
                allowance,
                label_bits(declared) * (1.0 - allowance) / allowance,
            )
        )

    if coverage["missing"]:
        findings.append(
            "the label carries no %s, so a receiver cannot recover it from the "
            "unit alone" % ", ".join(coverage["missing"])
        )
    if coverage["unrecognised"]:
        findings.append(
            "unrecognised label field: %s; confirm it is not a required field "
            "under another name" % ", ".join(coverage["unrecognised"])
        )

    widths_ok = all(w["wide_enough"] for w in widths)
    return {
        "coverage": coverage,
        "identifier_widths": widths,
        "sequence_bits": sequence_width,
        "required_sequence_bits": needed_sequence,
        "wrap_period_s": wrap,
        "ambiguity_window_s": window,
        "sequence_unambiguous": sequence_ok,
        "label_bits": label_bits(declared),
        "overhead_fraction": overhead,
        "overhead_allowance": allowance,
        "overhead_within_allowance": overhead_ok,
        "effective_payload_bps": effective_payload_bps(
            capacity_bps, declared, payload_bits
        ),
        "verdict": SUFFICIENT
        if (coverage["complete"] and widths_ok and sequence_ok and overhead_ok)
        else DEFICIENT,
        "findings": findings,
    }
