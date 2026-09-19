"""Sequence identifier sizing for a space data transfer protocol.

Anchor: ECSS-E-ST-50C clause 5.6.13.3 -- sequence identifier on the transferred
data units. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that each transferred data unit carries a sequence
identifier the receiver can use to tell loss, duplication and reordering apart.
That obligation only holds if the identifier space is wide enough for the units
the link keeps outstanding, so the procedure here is a sizing calculation plus
the trace replay the identifier exists to make possible:

  space        -- the number of distinct identifiers a field width gives,
                  computed as an integer count;
  window       -- the largest outstanding window that space keeps unambiguous,
                  which depends on the retransmission scheme;
  width        -- the smallest field width that makes a wanted window safe;
  wrap         -- how long the link runs before an identifier is reused;
  replay       -- the gaps, repeats and reorderings in a received trace.

Stdlib only, offline, deterministic. Integer arithmetic is used wherever the
quantity is a count, so no logarithm decides a counting question.
"""

import math

GO_BACK_N = "go-back-n"
SELECTIVE_REPEAT = "selective-repeat"
VALID_SCHEMES = (GO_BACK_N, SELECTIVE_REPEAT)

UNAMBIGUOUS = "unambiguous"
AMBIGUOUS = "ambiguous"

# Relative tolerance for the wrap-time comparison, so a link whose wrap time
# lands exactly on the accepted delivery latency decides the same way on every
# platform instead of by the last bit of a division.
REL_TOL = 1e-9

__all__ = [
    "GO_BACK_N",
    "SELECTIVE_REPEAT",
    "VALID_SCHEMES",
    "UNAMBIGUOUS",
    "AMBIGUOUS",
    "REL_TOL",
    "validate_bits",
    "validate_count",
    "validate_positive_number",
    "validate_scheme",
    "identifier_space",
    "unambiguous_window",
    "required_identifier_bits",
    "bandwidth_delay_window",
    "wrap_time_s",
    "replay_identifier_trace",
    "assess_sequence_identifier",
]


def validate_bits(value, name="identifier_bits"):
    """Return a sequence identifier field width in bits, at least one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer number of bits" % name)
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    if value > 64:
        raise ValueError("%s above 64 is not a transfer-layer field, got %r" % (name, value))
    return value


def validate_count(value, name="window_units"):
    """Return a positive integer count of data units."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def validate_positive_number(value, name="value"):
    """Return a strictly positive finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_scheme(value, name="scheme"):
    """Return a recognised retransmission scheme."""
    if value not in VALID_SCHEMES:
        raise ValueError("%s must be one of %s, got %r" % (name, list(VALID_SCHEMES), value))
    return value


def identifier_space(identifier_bits):
    """Return the number of distinct identifiers a field width gives."""
    bits = validate_bits(identifier_bits)
    return 1 << bits


def unambiguous_window(identifier_bits, scheme):
    """Return the largest outstanding window the identifier space keeps distinct.

    Go-back-N leaves one identifier spare so an acknowledged unit cannot be
    confused with the unit a full turn later. Selective repeat leaves half the
    space spare, because the receiver has to separate a retransmission of an old
    unit from a fresh unit that landed on the same identifier.
    """
    space = identifier_space(identifier_bits)
    validate_scheme(scheme)
    if scheme == GO_BACK_N:
        return space - 1
    return space // 2


def required_identifier_bits(window_units, scheme):
    """Return the smallest field width that keeps this window unambiguous.

    Found by widening one bit at a time rather than by inverting a logarithm,
    which would answer a counting question with a rounded float.
    """
    window = validate_count(window_units)
    validate_scheme(scheme)
    bits = 1
    while bits <= 64:
        if unambiguous_window(bits, scheme) >= window:
            return bits
        bits += 1
    raise ValueError("window of %d units needs a field wider than 64 bits" % window)


def bandwidth_delay_window(rate_bps, unit_bits, round_trip_s):
    """Return the outstanding units needed to keep the link busy over a round trip.

    Rounded up: a partial unit still has to be in flight, and a window rounded
    down leaves the transmitter idle waiting for an acknowledgement.
    """
    rate = validate_positive_number(rate_bps, "rate_bps")
    size = validate_positive_number(unit_bits, "unit_bits")
    trip = validate_positive_number(round_trip_s, "round_trip_s")
    units = (rate * trip) / size
    return int(math.ceil(units))


def wrap_time_s(identifier_bits, rate_bps, unit_bits):
    """Return the seconds the link runs before an identifier is reused."""
    space = identifier_space(identifier_bits)
    rate = validate_positive_number(rate_bps, "rate_bps")
    size = validate_positive_number(unit_bits, "unit_bits")
    units_per_second = rate / size
    return space / units_per_second


def replay_identifier_trace(received, identifier_bits, first_expected=0):
    """Walk a received identifier trace and name what the identifiers reveal.

    Returns the missing, repeated and out-of-order identifiers. Ordering is
    judged against the running expectation: an identifier that arrives before
    one already expected is out of order, and the expectation only advances past
    identifiers that have actually been seen, so a late arrival is not counted
    as a loss twice.
    """
    space = identifier_space(identifier_bits)
    if not isinstance(received, (list, tuple)):
        raise ValueError("received must be a list or tuple of identifiers")
    if isinstance(first_expected, bool) or not isinstance(first_expected, int):
        raise ValueError("first_expected must be an integer identifier")
    if not 0 <= first_expected < space:
        raise ValueError(
            "first_expected %r is outside the identifier space of %d" % (first_expected, space)
        )
    seen = set()
    repeated = []
    out_of_order = []
    for item in received:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("identifier %r is not an integer" % (item,))
        if not 0 <= item < space:
            raise ValueError(
                "identifier %r is outside the identifier space of %d" % (item, space)
            )
    expected = first_expected
    for item in received:
        if item in seen:
            repeated.append(item)
            continue
        seen.add(item)
        if item != expected:
            out_of_order.append(item)
        while expected in seen:
            expected = (expected + 1) % space
    missing = _gap_span(seen, first_expected, space)
    return {
        "delivered": sorted(seen),
        "missing": missing,
        "repeated": repeated,
        "out_of_order": out_of_order,
        "next_expected": expected,
        "identifier_space": space,
        "complete": not missing and not repeated,
    }


def _gap_span(seen, first_expected, space):
    """Return the identifiers never seen between the first and the last delivered."""
    if not seen:
        return []
    offsets = sorted((identifier - first_expected) % space for identifier in seen)
    highest = offsets[-1]
    present = set(offsets)
    return [
        (first_expected + offset) % space
        for offset in range(0, highest)
        if offset not in present
    ]


def assess_sequence_identifier(
    identifier_bits,
    scheme,
    window_units,
    rate_bps,
    unit_bits,
    round_trip_s,
    accepted_latency_s,
):
    """Assess one sequence identifier design against the link it has to serve."""
    bits = validate_bits(identifier_bits)
    validate_scheme(scheme)
    window = validate_count(window_units)
    rate = validate_positive_number(rate_bps, "rate_bps")
    size = validate_positive_number(unit_bits, "unit_bits")
    trip = validate_positive_number(round_trip_s, "round_trip_s")
    latency = validate_positive_number(accepted_latency_s, "accepted_latency_s")

    space = identifier_space(bits)
    allowed = unambiguous_window(bits, scheme)
    needed_bits = required_identifier_bits(window, scheme)
    needed_window = bandwidth_delay_window(rate, size, trip)
    wrap = wrap_time_s(bits, rate, size)

    findings = []
    window_fits = window <= allowed
    if not window_fits:
        findings.append(
            "window of %d units exceeds the %d that %d identifiers keep distinct under "
            "%s; %d identifier bits carry it" % (window, allowed, space, scheme, needed_bits)
        )
    if window < needed_window:
        findings.append(
            "window of %d units is below the %d the bandwidth-delay product asks for; "
            "the transmitter idles waiting for acknowledgements" % (window, needed_window)
        )
    wrap_clear = wrap >= latency - REL_TOL * latency
    if not wrap_clear:
        findings.append(
            "identifier space wraps after %.6g s, inside the %.6g s delivery latency the "
            "protocol still accepts; a reused identifier is ambiguous" % (wrap, latency)
        )
    verdict = UNAMBIGUOUS if (window_fits and wrap_clear) else AMBIGUOUS
    return {
        "identifier_bits": bits,
        "scheme": scheme,
        "identifier_space": space,
        "window_units": window,
        "unambiguous_window": allowed,
        "window_fits": window_fits,
        "required_identifier_bits": needed_bits,
        "bandwidth_delay_window": needed_window,
        "wrap_time_s": wrap,
        "accepted_latency_s": latency,
        "wrap_clear_of_latency": wrap_clear,
        "verdict": verdict,
        "findings": findings,
    }
