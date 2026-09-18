#!/usr/bin/env python3
"""Telecommand delivery service, ECSS-E-ST-50C clause 5.4.2.

Paraphrased requirement, no standard text reproduced. The clause places one
obligation on the telecommand chain: it has to offer a delivery service, and
a delivery service is a promise about a stream rather than about a frame.
The promise has three parts a receiver can actually enforce — every accepted
frame is delivered once, frames are delivered in the order they were sent,
and a frame that would break that order is refused rather than delivered out
of turn.

This module implements the receiving end of that service as a sliding
acceptance window over a modular sequence counter:

  frame sequence number + window -> accepted, duplicate, gap, or out of window
  accepted                       -> delivered, and the expected value advances
  gap                            -> refused, and the expected value is the ask
  duplicate                      -> discarded, already delivered once
  out of window                  -> discarded, the sender is out of step

The whole stream is then judged: contiguous, in order, delivered once each,
and whether any retransmission is still owed.

Every quantity is an integer sequence number, so the comparisons are exact
integer comparisons with no floating-point behaviour to differ between hosts.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

# Sequence numbers wrap; this is the default modulus of the counter.
DEFAULT_SEQUENCE_MODULUS = 256

# Frames the service will accept ahead of the expected one before it decides
# the sender is out of step rather than merely early.
DEFAULT_WINDOW_WIDTH = 10

# Disposition tokens.
ACCEPTED = "accepted-and-delivered"
GAP_REFUSED = "refused-out-of-sequence"
DUPLICATE = "duplicate-discarded"
OUT_OF_WINDOW = "outside-window-discarded"
DISPOSITIONS = (ACCEPTED, GAP_REFUSED, DUPLICATE, OUT_OF_WINDOW)

# Verdict tokens for a whole stream.
GUARANTEE_MET = "delivery-guarantee-met"
RETRANSMISSION_OWED = "retransmission-owed"
SENDER_OUT_OF_STEP = "sender-out-of-step"
VERDICTS = (GUARANTEE_MET, RETRANSMISSION_OWED, SENDER_OUT_OF_STEP)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and text."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return int(value)


def validate_modulus(modulus=DEFAULT_SEQUENCE_MODULUS):
    """Validate the modulus of the sequence counter."""
    value = _integer(modulus, "modulus")
    if value < 4:
        raise ValueError("modulus must be at least 4, got %d" % value)
    if value % 2 != 0:
        raise ValueError("modulus must be even so the window can be centred, got %d" % value)
    return value


def validate_window_width(width=DEFAULT_WINDOW_WIDTH, modulus=DEFAULT_SEQUENCE_MODULUS):
    """Validate the acceptance window against the counter it slides over."""
    limit = validate_modulus(modulus)
    value = _integer(width, "window_width")
    if value < 1:
        raise ValueError("window_width must be at least 1, got %d" % value)
    if value > limit // 2:
        raise ValueError(
            "window_width %d exceeds half the modulus %d; ahead and behind "
            "would overlap and a duplicate would read as a gap" % (value, limit)
        )
    return value


def validate_sequence_number(value, modulus=DEFAULT_SEQUENCE_MODULUS):
    """Validate one sequence number against the counter range."""
    limit = validate_modulus(modulus)
    number = _integer(value, "sequence_number")
    if number < 0 or number >= limit:
        raise ValueError(
            "sequence_number must lie in 0..%d, got %d" % (limit - 1, number)
        )
    return number


def signed_offset(sequence_number, expected, modulus=DEFAULT_SEQUENCE_MODULUS):
    """How far a frame sits ahead of or behind the expected sequence number."""
    limit = validate_modulus(modulus)
    number = validate_sequence_number(sequence_number, limit)
    want = validate_sequence_number(expected, limit)
    ahead = (number - want) % limit
    if ahead > limit // 2:
        return ahead - limit
    return ahead


def categorize_frame(
    sequence_number,
    expected,
    window_width=DEFAULT_WINDOW_WIDTH,
    modulus=DEFAULT_SEQUENCE_MODULUS,
):
    """Group one received frame into a disposition of the delivery service."""
    limit = validate_modulus(modulus)
    width = validate_window_width(window_width, limit)
    offset = signed_offset(sequence_number, expected, limit)
    if offset == 0:
        return ACCEPTED
    if 0 < offset < width:
        return GAP_REFUSED
    if -width <= offset < 0:
        return DUPLICATE
    return OUT_OF_WINDOW


def advance_expected(expected, modulus=DEFAULT_SEQUENCE_MODULUS):
    """The sequence number the service wants next, wrapped."""
    limit = validate_modulus(modulus)
    return (validate_sequence_number(expected, limit) + 1) % limit


def deliver_stream(
    frames,
    expected=0,
    window_width=DEFAULT_WINDOW_WIDTH,
    modulus=DEFAULT_SEQUENCE_MODULUS,
):
    """Run a received frame stream through the delivery service."""
    if not isinstance(frames, (list, tuple)):
        raise ValueError("frames must be a sequence of sequence numbers")
    limit = validate_modulus(modulus)
    width = validate_window_width(window_width, limit)
    want = validate_sequence_number(expected, limit)

    delivered = []
    dispositions = []
    retransmission_requests = []
    counts = {token: 0 for token in DISPOSITIONS}

    for frame in frames:
        number = validate_sequence_number(frame, limit)
        disposition = categorize_frame(number, want, width, limit)
        counts[disposition] += 1
        dispositions.append((number, disposition))
        if disposition == ACCEPTED:
            delivered.append(number)
            want = advance_expected(want, limit)
        elif disposition == GAP_REFUSED:
            retransmission_requests.append(want)

    return {
        "modulus": limit,
        "window_width": width,
        "first_expected": validate_sequence_number(expected, limit),
        "next_expected": want,
        "delivered": tuple(delivered),
        "dispositions": tuple(dispositions),
        "retransmission_requests": tuple(retransmission_requests),
        "counts": counts,
    }


def delivery_is_ordered(delivered, modulus=DEFAULT_SEQUENCE_MODULUS):
    """True when every delivered frame follows the one before it exactly."""
    limit = validate_modulus(modulus)
    previous = None
    for number in delivered:
        current = validate_sequence_number(number, limit)
        if previous is not None and current != (previous + 1) % limit:
            return False
        previous = current
    return True


def delivery_is_unique(delivered):
    """True when no frame was handed upward more than once."""
    seen = set()
    for number in delivered:
        if number in seen:
            return False
        seen.add(number)
    return True


def assess_delivery_service(
    frames,
    expected=0,
    window_width=DEFAULT_WINDOW_WIDTH,
    modulus=DEFAULT_SEQUENCE_MODULUS,
):
    """Assess a received stream against the clause 5.4.2 delivery promise."""
    report = deliver_stream(frames, expected, window_width, modulus)
    delivered = report["delivered"]
    limit = report["modulus"]

    ordered = delivery_is_ordered(delivered, limit)
    unique = delivery_is_unique(delivered)

    findings = []
    limitations = []
    if report["counts"][OUT_OF_WINDOW]:
        findings.append(
            "%d frame(s) arrived outside the acceptance window; the sender is "
            "not tracking the receiver" % report["counts"][OUT_OF_WINDOW]
        )
    if report["counts"][GAP_REFUSED]:
        limitations.append(
            "%d frame(s) refused out of sequence; retransmission from %s is owed"
            % (
                report["counts"][GAP_REFUSED],
                ", ".join(str(n) for n in report["retransmission_requests"]),
            )
        )
    if report["counts"][DUPLICATE]:
        limitations.append(
            "%d duplicate frame(s) discarded without a second delivery"
            % report["counts"][DUPLICATE]
        )
    if not ordered:
        findings.append("delivered frames are not contiguous and in order")
    if not unique:
        findings.append("a frame was delivered more than once")

    if findings:
        verdict = SENDER_OUT_OF_STEP
    elif report["counts"][GAP_REFUSED]:
        verdict = RETRANSMISSION_OWED
    else:
        verdict = GUARANTEE_MET

    result = dict(report)
    result.update(
        {
            "in_order": ordered,
            "delivered_once": unique,
            "findings": findings,
            "limitations": limitations,
            "verdict": verdict,
            "guarantee_held": verdict == GUARANTEE_MET,
        }
    )
    return result
