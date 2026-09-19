#!/usr/bin/env python3
"""Downlink frame rejection rate, ECSS-E-ST-50C clause 5.6.11.8.

Paraphrased requirement, no standard text reproduced. The clause carries one
obligation: the rate at which the ground rejects downlink frames stays within
the stated bound, evaluated at the assumed downlink bit error rate.

The downlink is not the uplink with the arrow reversed. A rejected telecommand
costs a retransmission; a rejected telemetry frame is usually science or
housekeeping that is simply gone, because the spacecraft has moved on and in
many missions nothing asks for it again. The consequence of this rate is data
loss per pass, not link occupancy.

The coding is different too. Downlink telemetry is normally protected by a
block code working on multi-bit symbols, so the unit that fails is a symbol,
not a bit: one burst that corrupts eight consecutive bits costs one symbol,
and the decoder's strength is quoted in symbols it can correct. A frame then
carries several codewords, often interleaved, and is rejected when any one of
them cannot be corrected - so the frame rate is worse than the codeword rate
by roughly the interleaving depth.

Numerics. The symbol error probability and both compounding steps run through
expm1 and log1p, never one minus a product. The codeword tail starts from its
first term and walks upward with an exact integer recurrence on the binomial
coefficient, so no huge coefficient is ever built and no near-one head is ever
subtracted. The bound comparison is inclusive with a relative tolerance.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# A rate that lands on the bound is compliant; the factors reach the
# comparison through expm1 and log1p, which are not correctly rounded.
RELATIVE_TOLERANCE = 1e-12

# Terms below this fraction of the running tail stop the summation.
TERM_CUTOFF = 1e-18

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


def symbol_error_probability(ber, symbol_bits=8):
    """Chance a multi-bit symbol carries at least one wrong bit."""
    p = validate_probability(ber, "ber", allow_zero=False)
    bits = validate_count(symbol_bits, "symbol_bits")
    return -math.expm1(bits * math.log1p(-p))


def codeword_failure_probability(
    symbol_error_rate, codeword_symbols, correctable_symbols
):
    """Chance a block codeword carries more symbol errors than it can fix."""
    ps = validate_probability(symbol_error_rate, "symbol_error_rate")
    n = validate_count(codeword_symbols, "codeword_symbols")
    t = validate_count(correctable_symbols, "correctable_symbols", minimum=0)
    if t >= n:
        return 0.0
    if ps == 0.0:
        return 0.0
    if ps == 1.0:
        return 1.0

    log_q = math.log1p(-ps)
    log_p = math.log(ps)
    first = t + 1
    # First term of the tail, in the log domain so no huge coefficient and no
    # near-one head is ever formed.
    log_coefficient = 0.0
    for step in range(first):
        log_coefficient += math.log(n - step) - math.log(step + 1)
    term = math.exp(log_coefficient + first * log_p + (n - first) * log_q)

    tail = term
    ratio_base = ps / (1.0 - ps)
    for errors in range(first + 1, n + 1):
        term *= ((n - errors + 1) / errors) * ratio_base
        tail += term
        if term == 0.0 or (tail > 0.0 and term < tail * TERM_CUTOFF):
            break
    return tail if tail < 1.0 else 1.0


def frame_rejection_from_codewords(codeword_failure, codewords_per_frame):
    """Chance at least one codeword in an interleaved frame stays broken."""
    p = validate_probability(codeword_failure, "codeword_failure", allow_one=True)
    depth = validate_count(codewords_per_frame, "codewords_per_frame")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    return -math.expm1(depth * math.log1p(-p))


def downlink_frame_rejection_rate(
    ber,
    symbol_bits=8,
    codeword_symbols=255,
    correctable_symbols=16,
    codewords_per_frame=5,
):
    """Fraction of downlink frames the ground rejects at an assumed rate."""
    ps = symbol_error_probability(ber, symbol_bits)
    per_codeword = codeword_failure_probability(
        ps, codeword_symbols, correctable_symbols
    )
    return frame_rejection_from_codewords(per_codeword, codewords_per_frame)


def frames_lost_per_pass(rate, frames_per_pass):
    """How many downlink frames a pass is expected to lose outright."""
    r = validate_probability(rate, "rate", allow_one=True)
    frames = validate_count(frames_per_pass, "frames_per_pass")
    return r * frames


def information_bits_lost_per_pass(rate, frames_per_pass, information_bits_per_frame):
    """How much payload a pass loses, since telemetry is rarely resent."""
    lost = frames_lost_per_pass(rate, frames_per_pass)
    payload = validate_count(
        information_bits_per_frame, "information_bits_per_frame"
    )
    return lost * payload


def within_bound(rate, maximum_rate):
    """True when a rejection rate meets its bound, the bound itself included."""
    r = validate_probability(rate, "rate", allow_one=True)
    limit = validate_probability(maximum_rate, "maximum_rate", allow_one=True)
    return r <= limit + RELATIVE_TOLERANCE * max(limit, 1e-300)


def assess_downlink_frame_rejection(
    ber,
    maximum_rejection_rate,
    symbol_bits=8,
    codeword_symbols=255,
    correctable_symbols=16,
    codewords_per_frame=5,
    frames_per_pass=1,
    information_bits_per_frame=1,
):
    """Grade a downlink frame rejection rate against clause 5.6.11.8."""
    ps = symbol_error_probability(ber, symbol_bits)
    per_codeword = codeword_failure_probability(
        ps, codeword_symbols, correctable_symbols
    )
    rate = frame_rejection_from_codewords(per_codeword, codewords_per_frame)
    limit = validate_probability(
        maximum_rejection_rate, "maximum_rejection_rate", allow_one=True
    )
    frames = validate_count(frames_per_pass, "frames_per_pass")
    compliant = within_bound(rate, limit)
    return {
        "verdict": WITHIN if compliant else EXCEEDED,
        "compliant": compliant,
        "assumed_ber": validate_probability(ber, "ber", allow_zero=False),
        "symbol_error_probability": ps,
        "codeword_failure_probability": per_codeword,
        "codewords_per_frame": validate_count(
            codewords_per_frame, "codewords_per_frame"
        ),
        "rejection_rate": rate,
        "maximum_rejection_rate": limit,
        "frames_lost_per_pass": frames_lost_per_pass(rate, frames),
        "information_bits_lost_per_pass": information_bits_lost_per_pass(
            rate, frames, information_bits_per_frame
        ),
        "finding": (
            "the downlink frame rejection rate meets its bound at the assumed rate"
            if compliant
            else "the downlink frame rejection rate exceeds its bound, and the frames are not resent"
        ),
    }
