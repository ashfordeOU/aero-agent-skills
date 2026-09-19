"""Expedited transfer services on an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.3 -- expedited transfer services.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the network offers an expedited transfer
service for traffic that cannot wait its turn. Two things have to be true for
that service to exist in fact rather than on paper.

The first is precedence: expedited traffic goes ahead of ordinary traffic
already queued. Where it does not, the whole ordinary backlog sits in front of
the urgent message and there is no expedited service, however it is labelled.

The second is a bounded worst case. Even with precedence, an urgent message
waits for whatever is already on the wire, because a transfer unit in progress
cannot be taken back, and it waits behind any other expedited traffic that may
be queued at the same moment. Worst-case delivery is therefore

    (blocking + interference + own) bits / link rate

where blocking is the largest non-preemptable unit the link can be carrying.
That expression inverts two useful ways: the largest non-preemptable unit a
deadline can tolerate, and the link rate a deadline needs.
"""

import math

__all__ = [
    "MET",
    "MISSED",
    "NOT_EXPEDITED",
    "REL_TOL",
    "validate_bits",
    "validate_rate",
    "validate_deadline",
    "transmission_time",
    "interference_bits",
    "ahead_bits",
    "worst_case_latency",
    "max_non_preemptable_bits",
    "required_link_rate",
    "assess_expedited_transfer",
]

MET = "met"
MISSED = "missed"
NOT_EXPEDITED = "not-expedited"

# Relative tolerance for the deadline comparison, so a message whose worst case
# lands exactly on its deadline is met on every platform rather than on the one
# that happened to round down.
REL_TOL = 1e-9


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_bits(value, name="bits"):
    """Return a non-negative size in bits."""
    bits = _number(value, name)
    if bits < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return bits


def validate_rate(value, name="link_rate_bps"):
    """Return a strictly positive link rate in bits per second."""
    rate = _number(value, name)
    if rate <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return rate


def validate_deadline(value, name="deadline_s"):
    """Return a strictly positive deadline in seconds."""
    deadline = _number(value, name)
    if deadline <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return deadline


def transmission_time(bits, link_rate_bps):
    """Return the seconds a given number of bits occupies the link."""
    return validate_bits(bits) / validate_rate(link_rate_bps)


def interference_bits(peer_message_bits):
    """Return the bits of other expedited traffic that may queue ahead.

    A peer list that is not a list is an input error rather than an empty
    contention set: the caller meant something by it.
    """
    if peer_message_bits is None:
        return 0.0
    if not isinstance(peer_message_bits, (list, tuple)):
        raise ValueError("peer_message_bits must be a list of sizes in bits")
    total = 0.0
    for index, bits in enumerate(peer_message_bits):
        total += validate_bits(bits, "peer_message_bits[%d]" % index)
    return total


def ahead_bits(
    message_bits,
    non_preemptable_bits,
    peer_message_bits=None,
    ordinary_backlog_bits=0.0,
    precedence=True,
):
    """Return the bits that must go out before this message is delivered.

    Without precedence the ordinary backlog joins the queue in front of the
    urgent message, which is exactly what having no expedited service means.
    """
    own = validate_bits(message_bits, "message_bits")
    blocking = validate_bits(non_preemptable_bits, "non_preemptable_bits")
    peers = interference_bits(peer_message_bits)
    backlog = validate_bits(ordinary_backlog_bits, "ordinary_backlog_bits")
    if not isinstance(precedence, bool):
        raise ValueError("precedence must be a boolean, got %r" % (precedence,))
    total = own + blocking + peers
    if not precedence:
        total += backlog
    return total


def worst_case_latency(
    message_bits,
    non_preemptable_bits,
    link_rate_bps,
    peer_message_bits=None,
    ordinary_backlog_bits=0.0,
    precedence=True,
):
    """Return the worst-case seconds to deliver one expedited message."""
    total = ahead_bits(
        message_bits,
        non_preemptable_bits,
        peer_message_bits,
        ordinary_backlog_bits,
        precedence,
    )
    return total / validate_rate(link_rate_bps)


def max_non_preemptable_bits(
    message_bits,
    link_rate_bps,
    deadline_s,
    peer_message_bits=None,
    ordinary_backlog_bits=0.0,
    precedence=True,
):
    """Return the largest non-preemptable unit this deadline can tolerate.

    Zero means the deadline is already unreachable with instantaneous
    preemption, which is a rate or a queueing problem and not a unit-size one.
    """
    own = validate_bits(message_bits, "message_bits")
    rate = validate_rate(link_rate_bps)
    deadline = validate_deadline(deadline_s)
    peers = interference_bits(peer_message_bits)
    backlog = validate_bits(ordinary_backlog_bits, "ordinary_backlog_bits")
    if not isinstance(precedence, bool):
        raise ValueError("precedence must be a boolean, got %r" % (precedence,))
    budget = deadline * rate - own - peers
    if not precedence:
        budget -= backlog
    if budget < 0.0:
        return 0.0
    return budget


def required_link_rate(
    message_bits,
    non_preemptable_bits,
    deadline_s,
    peer_message_bits=None,
    ordinary_backlog_bits=0.0,
    precedence=True,
):
    """Return the link rate this deadline needs at the stated queueing."""
    total = ahead_bits(
        message_bits,
        non_preemptable_bits,
        peer_message_bits,
        ordinary_backlog_bits,
        precedence,
    )
    return total / validate_deadline(deadline_s)


def assess_expedited_transfer(
    message_bits,
    non_preemptable_bits,
    link_rate_bps,
    deadline_s,
    peer_message_bits=None,
    ordinary_backlog_bits=0.0,
    precedence=True,
):
    """Judge one urgent message against the expedited service it is offered."""
    own = validate_bits(message_bits, "message_bits")
    blocking = validate_bits(non_preemptable_bits, "non_preemptable_bits")
    rate = validate_rate(link_rate_bps)
    deadline = validate_deadline(deadline_s)
    peers = interference_bits(peer_message_bits)
    backlog = validate_bits(ordinary_backlog_bits, "ordinary_backlog_bits")
    if not isinstance(precedence, bool):
        raise ValueError("precedence must be a boolean, got %r" % (precedence,))
    latency = worst_case_latency(
        own, blocking, rate, peer_message_bits, backlog, precedence
    )
    tolerance = REL_TOL * max(latency, deadline, 1.0)
    on_time = latency <= deadline + tolerance
    if not precedence:
        verdict = NOT_EXPEDITED
    elif on_time:
        verdict = MET
    else:
        verdict = MISSED
    findings = []
    if not precedence:
        findings.append(
            "ordinary traffic is not stood aside, so %.6g bit of backlog is "
            "delivered before the urgent message" % backlog
        )
    if not on_time:
        findings.append(
            "worst case %.6g s exceeds the %.6g s deadline" % (latency, deadline)
        )
        findings.append(
            "a non-preemptable unit of at most %.6g bit, or a link rate of at "
            "least %.6g bit/s, meets this deadline"
            % (
                max_non_preemptable_bits(
                    own, rate, deadline, peer_message_bits, backlog, precedence
                ),
                required_link_rate(
                    own, blocking, deadline, peer_message_bits, backlog, precedence
                ),
            )
        )
    return {
        "message_bits": own,
        "non_preemptable_bits": blocking,
        "link_rate_bps": rate,
        "deadline_s": deadline,
        "peer_bits": peers,
        "ordinary_backlog_bits": backlog,
        "precedence": precedence,
        "blocking_time_s": transmission_time(blocking, rate),
        "interference_time_s": transmission_time(peers, rate),
        "own_time_s": transmission_time(own, rate),
        "worst_case_latency_s": latency,
        "margin_s": deadline - latency,
        "on_time": on_time,
        "max_non_preemptable_bits": max_non_preemptable_bits(
            own, rate, deadline, peer_message_bits, backlog, precedence
        ),
        "required_link_rate_bps": required_link_rate(
            own, blocking, deadline, peer_message_bits, backlog, precedence
        ),
        "verdict": verdict,
        "findings": findings,
    }
