#!/usr/bin/env python3
"""Accepting a corrupted downlink frame, ECSS-E-ST-50C clause 5.6.11.9.

Paraphrased requirement, no standard text reproduced. The clause carries three
obligations, and a downlink case routinely satisfies one while quietly failing
the other two:

  1. the probability of accepting a corrupted downlink frame as sound stays
     inside its stated bound;
  2. that probability is derived from the declared configuration - the assumed
     bit error rate, the block code and the frame check field - rather than
     from whatever numbers were convenient;
  3. the bound is demonstrated across the frames the mission actually
     downlinks, not only for one frame in isolation.

They are graded separately here because they fail separately. A figure inside
its bound that was computed from an undeclared rate proves nothing, and a
per-frame figure inside its bound can still make an undetected corruption
likely over a mission.

The escape path on a coded downlink has two gates, not one. A codeword beyond
the decoder's correction radius can still land inside the radius of some other
codeword, in which case the decoder reports success and hands up a wrong but
structurally valid block. That miscorrected block then has to get past the
frame check field. Only when both happen is a corrupted frame accepted.

Numerics. The miscorrection probability is an exact rational built from integer
binomials and integer powers of the symbol alphabet, converted to a float once
at the end, so it is the same number on every host. Two to the minus k comes
from an exact integer power of two. The frame and mission compounding use
expm1 and log1p. No result is reached by subtracting a near-one number from
one, and every bound comparison is inclusive with a relative tolerance.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import fractions
import math

RELATIVE_TOLERANCE = 1e-12
MAX_CHECK_BITS = 512

MET = "met"
NOT_MET = "not-met"

BOUND_OBLIGATION = "per-frame-bound"
DERIVATION_OBLIGATION = "declared-derivation"
MISSION_OBLIGATION = "mission-exposure"
OBLIGATIONS = (BOUND_OBLIGATION, DERIVATION_OBLIGATION, MISSION_OBLIGATION)

# The inputs a derivation has to declare before its result means anything.
REQUIRED_DECLARATIONS = ("assumed_ber", "codeword_symbols", "correctable_symbols",
                         "symbol_bits", "check_bits")


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
    """Chance a corruption slips past a frame check field of this many bits."""
    bits = validate_count(check_bits, "check_bits", minimum=1)
    if bits > MAX_CHECK_BITS:
        raise ValueError(
            "check_bits of %d exceeds the %d bit ceiling; check the units"
            % (bits, MAX_CHECK_BITS)
        )
    return 1.0 / float(1 << bits)


def miscorrection_probability(codeword_symbols, correctable_symbols, symbol_bits=8):
    """Chance a bounded-distance decoder reports success on a wrong block.

    The decoding spheres of radius t around every codeword cover a fixed
    fraction of the symbol space. An error pattern beyond correction lands in
    somebody else's sphere with about that probability, and the decoder then
    hands up a structurally valid block that is wrong.
    """
    n = validate_count(codeword_symbols, "codeword_symbols")
    t = validate_count(correctable_symbols, "correctable_symbols", minimum=0)
    bits = validate_count(symbol_bits, "symbol_bits")
    if bits > 64:
        raise ValueError("symbol_bits of %d is not a symbol alphabet" % bits)
    if 2 * t > n:
        raise ValueError(
            "a code of %d symbols cannot correct %d of them" % (n, t)
        )
    alphabet = 1 << bits
    sphere = 0
    for errors in range(t + 1):
        sphere += math.comb(n, errors) * (alphabet - 1) ** errors
    # The parity symbols of a bounded-distance code number twice its
    # correction radius, so the space the spheres sit in is that many
    # symbols wide.
    space = alphabet ** (2 * t)
    ratio = fractions.Fraction(sphere, space)
    if ratio >= 1:
        return 1.0
    return float(ratio)


def undeclared_inputs(declaration, used):
    """Name every derivation input that is missing or disagrees with use."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping of input to value")
    if not isinstance(used, dict):
        raise ValueError("used must be a mapping of input to value")
    offenders = []
    for key in REQUIRED_DECLARATIONS:
        if key not in declaration or declaration[key] is None:
            offenders.append(key)
            continue
        if key not in used:
            offenders.append(key)
            continue
        stated, applied = declaration[key], used[key]
        if isinstance(stated, bool) or isinstance(applied, bool):
            offenders.append(key)
            continue
        if isinstance(stated, int) and isinstance(applied, int):
            if stated != applied:
                offenders.append(key)
            continue
        try:
            stated_value = float(stated)
            applied_value = float(applied)
        except (TypeError, ValueError):
            offenders.append(key)
            continue
        scale = max(abs(stated_value), abs(applied_value), 1e-300)
        if abs(stated_value - applied_value) > RELATIVE_TOLERANCE * scale:
            offenders.append(key)
    return tuple(offenders)


def per_frame_acceptance_probability(
    codeword_failure_probability,
    miscorrection,
    escape,
    codewords_per_frame,
):
    """Chance one downlink frame is corrupted, miscorrected and accepted."""
    failure = validate_probability(
        codeword_failure_probability, "codeword_failure_probability", allow_one=True
    )
    miss = validate_probability(miscorrection, "miscorrection", allow_one=True)
    slip = validate_probability(escape, "escape", allow_one=True)
    depth = validate_count(codewords_per_frame, "codewords_per_frame")
    per_codeword = failure * miss
    if per_codeword <= 0.0:
        return 0.0
    if per_codeword >= 1.0:
        return slip
    frame_level = -math.expm1(depth * math.log1p(-per_codeword))
    return frame_level * slip


def mission_acceptance_probability(per_frame_probability, frames):
    """Chance of at least one accepted corrupted frame across the mission."""
    p = validate_probability(per_frame_probability, "per_frame_probability")
    count = validate_count(frames, "frames")
    if p == 0.0:
        return 0.0
    return -math.expm1(count * math.log1p(-p))


def within_bound(probability, maximum_probability):
    """True when a figure meets its bound, the bound itself included."""
    p = validate_probability(probability, "probability", allow_one=True)
    limit = validate_probability(
        maximum_probability, "maximum_probability", allow_one=True
    )
    return p <= limit + RELATIVE_TOLERANCE * max(limit, 1e-300)


def assess_corrupted_downlink_frame_acceptance(
    codeword_failure_probability,
    codeword_symbols,
    correctable_symbols,
    check_bits,
    maximum_per_frame_probability,
    maximum_mission_probability,
    declaration,
    used,
    symbol_bits=8,
    codewords_per_frame=5,
    downlink_frames=1,
):
    """Grade all three obligations of clause 5.6.11.9 separately."""
    miss = miscorrection_probability(
        codeword_symbols, correctable_symbols, symbol_bits
    )
    slip = escape_probability(check_bits)
    per_frame = per_frame_acceptance_probability(
        codeword_failure_probability, miss, slip, codewords_per_frame
    )
    frames = validate_count(downlink_frames, "downlink_frames")
    mission = mission_acceptance_probability(per_frame, frames)

    frame_limit = validate_probability(
        maximum_per_frame_probability, "maximum_per_frame_probability", allow_one=True
    )
    mission_limit = validate_probability(
        maximum_mission_probability, "maximum_mission_probability", allow_one=True
    )
    missing = undeclared_inputs(declaration, used)

    graded = (
        {
            "obligation": BOUND_OBLIGATION,
            "grade": MET if within_bound(per_frame, frame_limit) else NOT_MET,
            "value": per_frame,
            "bound": frame_limit,
            "finding": "the per-frame figure is compared with its own bound",
        },
        {
            "obligation": DERIVATION_OBLIGATION,
            "grade": MET if not missing else NOT_MET,
            "value": len(missing),
            "bound": 0,
            "finding": (
                "every derivation input is declared and was the one used"
                if not missing
                else "a derivation input is undeclared or disagrees with the one used"
            ),
        },
        {
            "obligation": MISSION_OBLIGATION,
            "grade": MET if within_bound(mission, mission_limit) else NOT_MET,
            "value": mission,
            "bound": mission_limit,
            "finding": "the figure is demonstrated across the mission's frames",
        },
    )

    failed = tuple(g["obligation"] for g in graded if g["grade"] == NOT_MET)
    return {
        "verdict": MET if not failed else NOT_MET,
        "compliant": not failed,
        "obligations": graded,
        "failed_obligations": failed,
        "miscorrection_probability": miss,
        "escape_probability": slip,
        "per_frame_probability": per_frame,
        "mission_probability": mission,
        "downlink_frames": frames,
        "undeclared_inputs": missing,
        "finding": (
            "all three obligations of the clause are met"
            if not failed
            else "obligations not met: " + ", ".join(failed)
        ),
    }
