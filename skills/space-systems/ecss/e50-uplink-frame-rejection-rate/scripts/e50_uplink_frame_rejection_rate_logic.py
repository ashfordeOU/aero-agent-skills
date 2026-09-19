#!/usr/bin/env python3
"""Uplink frame rejection rate, ECSS-E-ST-50C clause 5.6.11.6.

Paraphrased requirement, no standard text reproduced. The clause carries one
obligation: the rate at which the receiving end rejects uplink frames stays
within the stated bound, evaluated at the assumed uplink bit error rate.

A rejected frame is a detected fault, which is the good outcome; the clause
bounds how often it happens because every rejection costs a retransmission
and a rejection rate that looks small per frame becomes a lost pass once it
is multiplied by the frames in that pass.

The rejection rate for an uncoded uplink frame is the probability that at
least one of its bits is wrong. With a decoder that corrects up to a fixed
number of bit errors, it is instead the probability of more errors than the
decoder can correct, which is a binomial tail, not a scaled version of the
uncoded figure - halving the raw rate does not halve the coded one.

Numerics. The uncoded tail is evaluated as -expm1(n * log1p(-p)) rather than
as 1 - (1-p)**n, because at the rates this clause deals with the direct form
subtracts two numbers that agree to fifteen digits and returns noise. The
binomial tail is summed from the exact integer binomial coefficients upward,
smallest term first, so the sum is reproducible. The compliance comparison
uses a relative tolerance so a design that lands on its bound is graded the
same way on every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# A rate that lands on the bound is compliant. Tail probabilities are reached
# through expm1, log1p and integer binomials, none of which is guaranteed
# correctly rounded, so the comparison carries a relative tolerance rather
# than a strict inequality.
RELATIVE_TOLERANCE = 1e-12

# Upper limit on how many binomial terms a single tail evaluation may sum, so
# a decoder strength nobody meant to type cannot turn into an unbounded run.
SUMMATION_GUARD = 4096

WITHIN = "within-bound"
EXCEEDED = "bound-exceeded"

UNCODED = "uncoded"
ERROR_CORRECTING = "error-correcting"


def validate_probability(value, name):
    """Return value as a probability strictly inside zero and one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a probability, got %r" % (name, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if result <= 0.0 or result >= 1.0:
        raise ValueError(
            "%s must lie strictly between 0 and 1, got %r" % (name, value)
        )
    return result


def validate_bound(value, name):
    """Return a requirement bound, which may sit at zero or one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a probability, got %r" % (name, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if result < 0.0 or result > 1.0:
        raise ValueError("%s must lie in 0..1, got %r" % (name, value))
    return result


def validate_count(value, name, minimum=1):
    """Return value as a whole count at or above a floor."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return int(value)


def frame_bits(information_bits, overhead_bits):
    """Total bits exposed to the channel: information plus every overhead bit."""
    information = validate_count(information_bits, "information_bits")
    overhead = validate_count(overhead_bits, "overhead_bits", minimum=0)
    return information + overhead


def uncoded_frame_error_probability(ber, total_bits):
    """Probability at least one bit of an uncoded frame arrives wrong."""
    p = validate_probability(ber, "ber")
    n = validate_count(total_bits, "total_bits")
    return -math.expm1(n * math.log1p(-p))


def _log_binomial_term(n, errors, log_p, log_q):
    """Log probability of exactly this many bit errors in a frame."""
    return math.log(math.comb(n, errors)) + errors * log_p + (n - errors) * log_q


def binomial_tail_probability(ber, total_bits, correctable_bits):
    """Probability of more bit errors in a frame than the decoder corrects."""
    p = validate_probability(ber, "ber")
    n = validate_count(total_bits, "total_bits")
    t = validate_count(correctable_bits, "correctable_bits", minimum=0)
    if t >= n:
        return 0.0
    log_q = math.log1p(-p)
    log_p = math.log(p)
    mean_errors = n * p

    if t + 1 > mean_errors:
        # The tail is the small side. Summing it directly keeps every digit;
        # reaching it as one minus the head would subtract two numbers that
        # agree to fifteen places and return noise.
        total = 0.0
        for errors in range(t + 1, n + 1):
            term = math.exp(_log_binomial_term(n, errors, log_p, log_q))
            total += term
            if errors > mean_errors and (
                term == 0.0 or (total > 0.0 and term < total * 1e-18)
            ):
                break
        return total if total < 1.0 else 1.0

    # The tail is the large side, so the head is the small one; sum the head
    # from its largest index downward and subtract that instead.
    if t + 1 > SUMMATION_GUARD:
        raise ValueError(
            "correctable_bits of %d needs more than %d summation terms"
            % (t, SUMMATION_GUARD)
        )
    head = 0.0
    for errors in range(t, -1, -1):
        head += math.exp(_log_binomial_term(n, errors, log_p, log_q))
    tail = 1.0 - head
    return tail if tail > 0.0 else 0.0


def frame_rejection_rate(ber, total_bits, correctable_bits=0):
    """Fraction of uplink frames the receiving end rejects."""
    t = validate_count(correctable_bits, "correctable_bits", minimum=0)
    if t == 0:
        return uncoded_frame_error_probability(ber, total_bits)
    return binomial_tail_probability(ber, total_bits, t)


def coding_scheme(correctable_bits):
    """Name the scheme a correctable-bit count describes."""
    t = validate_count(correctable_bits, "correctable_bits", minimum=0)
    return UNCODED if t == 0 else ERROR_CORRECTING


def expected_rejections(rate, frames_per_pass):
    """How many frames a pass is expected to lose at a given rejection rate."""
    r = validate_bound(rate, "rate")
    frames = validate_count(frames_per_pass, "frames_per_pass")
    return r * frames


def retransmission_overhead(rate):
    """Mean transmissions needed per frame delivered, retransmitting on reject."""
    r = validate_bound(rate, "rate")
    if r >= 1.0:
        raise ValueError("a rejection rate of one never delivers a frame")
    return 1.0 / (1.0 - r)


def within_bound(rate, maximum_rate):
    """True when a rejection rate meets its bound, the bound itself included."""
    r = validate_bound(rate, "rate")
    limit = validate_bound(maximum_rate, "maximum_rate")
    return r <= limit + RELATIVE_TOLERANCE * max(limit, 1e-300)


def assess_uplink_frame_rejection(
    ber,
    information_bits,
    overhead_bits,
    maximum_rejection_rate,
    correctable_bits=0,
    frames_per_pass=1,
):
    """Grade an uplink frame rejection rate against clause 5.6.11.6."""
    total = frame_bits(information_bits, overhead_bits)
    rate = frame_rejection_rate(ber, total, correctable_bits)
    limit = validate_bound(maximum_rejection_rate, "maximum_rejection_rate")
    frames = validate_count(frames_per_pass, "frames_per_pass")
    compliant = within_bound(rate, limit)
    return {
        "verdict": WITHIN if compliant else EXCEEDED,
        "compliant": compliant,
        "assumed_ber": validate_probability(ber, "ber"),
        "frame_bits": total,
        "coding": coding_scheme(correctable_bits),
        "correctable_bits": validate_count(
            correctable_bits, "correctable_bits", minimum=0
        ),
        "rejection_rate": rate,
        "maximum_rejection_rate": limit,
        "expected_rejections_per_pass": expected_rejections(rate, frames),
        "mean_transmissions_per_delivered_frame": retransmission_overhead(rate),
        "finding": (
            "the uplink frame rejection rate meets its bound at the assumed rate"
            if compliant
            else "the uplink frame rejection rate exceeds its bound at the assumed rate"
        ),
    }
