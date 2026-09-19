#!/usr/bin/env python3
"""Accepting a corrupted uplink frame, ECSS-E-ST-50C clause 5.6.11.7.

Paraphrased requirement, no standard text reproduced. The clause carries one
obligation: the probability that the spacecraft accepts a corrupted uplink
frame as if it were sound stays inside its stated bound.

This is the dangerous half of the pair. A rejected frame is a detected fault
and costs a retransmission; an accepted corrupted frame is an undetected
fault and is executed. The two are bounded separately for that reason, and
the bound here is always the tighter one.

The probability has two independent factors and they are usually confused:

  * how often a frame arrives corrupted at the detector - the residual
    figure the rejection analysis already produced, after any correction;
  * how often the detector misses a corruption that reached it - the escape
    probability of the error detection code, which for a well-behaved code
    of k check bits is two to the minus k and does not depend on the channel.

Multiplying them gives the per-frame figure. The number that matters
operationally is the mission one: the chance of at least one such acceptance
across every frame the mission uplinks.

Numerics. Two to the minus k is built by dividing one by an exact integer
power of two, never by raising two to a negative power in floating point, so
it is bit-exact everywhere. The mission-level figure uses expm1 and log1p
rather than one minus a product. The smallest sufficient check length is
found by an integer search, not by a logarithm, so it is the same integer on
every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# A per-frame figure that lands on the bound is compliant. Its factors reach
# the comparison through expm1 and log1p, which are not correctly rounded, so
# the comparison carries a relative tolerance rather than a strict inequality.
RELATIVE_TOLERANCE = 1e-12

# A detection code longer than this is not a frame check field; it is almost
# always a unit mistake, and the exact power of two would stop being useful.
MAX_CHECK_BITS = 512

# Upper limit on the integer search for a sufficient check length.
CHECK_BITS_SEARCH_GUARD = MAX_CHECK_BITS

WITHIN = "within-bound"
EXCEEDED = "bound-exceeded"


def validate_probability(value, name, allow_zero=True, allow_one=False):
    """Return value as a probability, with the endpoints controlled."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a probability, got %r" % (name, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if result < 0.0 or result > 1.0:
        raise ValueError("%s must lie in 0..1, got %r" % (name, value))
    if result == 0.0 and not allow_zero:
        raise ValueError("%s must not be zero" % name)
    if result == 1.0 and not allow_one:
        raise ValueError("%s must not be one" % name)
    return result


def validate_count(value, name, minimum=1):
    """Return value as a whole count at or above a floor."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return int(value)


def escape_probability(check_bits):
    """Chance a corruption slips past a detection code of this many bits."""
    bits = validate_count(check_bits, "check_bits", minimum=1)
    if bits > MAX_CHECK_BITS:
        raise ValueError(
            "check_bits of %d exceeds the %d bit ceiling; check the units"
            % (bits, MAX_CHECK_BITS)
        )
    # An exact integer power of two converts to a float without rounding, so
    # the reciprocal is bit-identical on every host.
    return 1.0 / float(1 << bits)


def combine_detection_layers(escapes):
    """Chance a corruption slips past every independent detection layer."""
    if not isinstance(escapes, (list, tuple)):
        raise ValueError("escapes must be a sequence of escape probabilities")
    if not escapes:
        raise ValueError("at least one detection layer must be declared")
    combined = 1.0
    for index, escape in enumerate(escapes):
        combined *= validate_probability(
            escape, "escapes[%d]" % index, allow_one=True
        )
    return combined


def acceptance_probability_per_frame(residual_corruption_probability, escape):
    """Chance one uplink frame is both corrupted and accepted as sound."""
    corrupted = validate_probability(
        residual_corruption_probability, "residual_corruption_probability"
    )
    missed = validate_probability(escape, "escape", allow_one=True)
    return corrupted * missed


def mission_acceptance_probability(per_frame_probability, frames):
    """Chance of at least one accepted corrupted frame across the mission."""
    p = validate_probability(per_frame_probability, "per_frame_probability")
    count = validate_count(frames, "frames")
    if p == 0.0:
        return 0.0
    return -math.expm1(count * math.log1p(-p))


def frames_between_acceptances(per_frame_probability):
    """Mean number of uplink frames between two accepted corrupted frames."""
    p = validate_probability(
        per_frame_probability, "per_frame_probability", allow_zero=False
    )
    return 1.0 / p


def within_bound(probability, maximum_probability):
    """True when a figure meets its bound, the bound itself included."""
    p = validate_probability(probability, "probability", allow_one=True)
    limit = validate_probability(
        maximum_probability, "maximum_probability", allow_one=True
    )
    return p <= limit + RELATIVE_TOLERANCE * max(limit, 1e-300)


def sufficient_check_bits(residual_corruption_probability, maximum_probability):
    """Shortest detection code that brings the per-frame figure inside bound."""
    corrupted = validate_probability(
        residual_corruption_probability, "residual_corruption_probability"
    )
    limit = validate_probability(
        maximum_probability, "maximum_probability", allow_one=True
    )
    for bits in range(1, CHECK_BITS_SEARCH_GUARD + 1):
        figure = acceptance_probability_per_frame(
            corrupted, escape_probability(bits)
        )
        if within_bound(figure, limit):
            return bits
    raise ValueError(
        "no detection code up to %d bits brings %r inside %r"
        % (CHECK_BITS_SEARCH_GUARD, corrupted, limit)
    )


def assess_corrupted_uplink_frame_acceptance(
    residual_corruption_probability,
    check_bits,
    maximum_probability,
    extra_detection_layers=(),
    uplink_frames=1,
):
    """Grade the corrupted uplink frame acceptance figure per clause 5.6.11.7."""
    corrupted = validate_probability(
        residual_corruption_probability, "residual_corruption_probability"
    )
    layers = [escape_probability(check_bits)]
    for extra in extra_detection_layers:
        layers.append(validate_probability(extra, "extra_detection_layer"))
    escape = combine_detection_layers(layers)
    per_frame = acceptance_probability_per_frame(corrupted, escape)
    limit = validate_probability(
        maximum_probability, "maximum_probability", allow_one=True
    )
    frames = validate_count(uplink_frames, "uplink_frames")
    compliant = within_bound(per_frame, limit)

    return {
        "verdict": WITHIN if compliant else EXCEEDED,
        "compliant": compliant,
        "residual_corruption_probability": corrupted,
        "check_bits": validate_count(check_bits, "check_bits"),
        "detection_layers": len(layers),
        "combined_escape_probability": escape,
        "per_frame_probability": per_frame,
        "maximum_probability": limit,
        "mission_probability": mission_acceptance_probability(per_frame, frames),
        "uplink_frames": frames,
        "shortest_sufficient_check_bits": (
            None if corrupted == 0.0 else sufficient_check_bits(corrupted, limit)
        ),
        "finding": (
            "an undetected corrupted uplink frame stays inside its bound"
            if compliant
            else "an undetected corrupted uplink frame is more likely than the bound allows"
        ),
    }
