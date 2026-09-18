"""Congestion containment for a space communication link.

Anchor: ECSS-E-ST-50C clause 5.3.2 -- congestion on the communication system.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the system is designed so congestion is
contained rather than resolved by loss: when the offered load runs above the
service rate, the excess is held and drained, and the design shows it can be.
That turns into a deterministic fluid model with four numbers a designer can
act on:

  backlog     -- bits the burst leaves behind, offered minus served over its
                 duration;
  overflow    -- how long the overload can run before the provided buffer is
                 full, which is None when there is no overload;
  containment -- whether the backlog fits the buffer at all;
  drain       -- how long the backlog takes to clear once the burst ends.

Sizing is the inverse of the same model: the buffer a burst needs, and the
service rate that would hold a burst inside a buffer that already exists.
"""

import math

__all__ = [
    "NO_CONGESTION",
    "CONTAINED",
    "OVERFLOW",
    "REL_TOL",
    "validate_rate",
    "validate_duration",
    "validate_buffer",
    "backlog_bits",
    "time_to_overflow",
    "drain_time",
    "required_buffer_bits",
    "required_service_rate",
    "assess_congestion",
]

NO_CONGESTION = "no-congestion"
CONTAINED = "contained"
OVERFLOW = "overflow"

# Relative tolerance for the containment comparison, so a burst sized to exactly
# fill the buffer is contained on every platform rather than on some of them.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_rate(value, name="rate_bps"):
    """Return a non-negative rate in bits per second."""
    rate = _validate_number(value, name)
    if rate < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return rate


def validate_duration(value, name="duration_s"):
    """Return a strictly positive duration in seconds."""
    duration = _validate_number(value, name)
    if duration <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return duration


def validate_buffer(value, name="buffer_bits"):
    """Return a non-negative buffer size in bits."""
    size = _validate_number(value, name)
    if size < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return size


def backlog_bits(offered_bps, service_bps, duration_s):
    """Return the bits a burst leaves behind over its duration."""
    offered = validate_rate(offered_bps, "offered_bps")
    service = validate_rate(service_bps, "service_bps")
    duration = validate_duration(duration_s)
    excess = offered - service
    if excess <= 0.0:
        return 0.0
    return excess * duration


def time_to_overflow(offered_bps, service_bps, buffer_bits_provided):
    """Return the seconds an overload runs before the buffer fills.

    None means the buffer never fills: the service rate keeps up, so there is no
    excess to accumulate.
    """
    offered = validate_rate(offered_bps, "offered_bps")
    service = validate_rate(service_bps, "service_bps")
    size = validate_buffer(buffer_bits_provided)
    excess = offered - service
    if excess <= 0.0:
        return None
    return size / excess


def drain_time(backlog, service_bps, offered_after_bps=0.0):
    """Return the seconds a backlog takes to clear once the burst ends.

    None means it never clears: the load that follows the burst is itself at or
    above the service rate, so there is no spare capacity to drain with.
    """
    held = validate_buffer(backlog, "backlog")
    service = validate_rate(service_bps, "service_bps")
    after = validate_rate(offered_after_bps, "offered_after_bps")
    spare = service - after
    if spare <= 0.0:
        return None
    if held == 0.0:
        return 0.0
    return held / spare


def required_buffer_bits(offered_bps, service_bps, duration_s):
    """Return the buffer a burst of this shape needs to be contained."""
    return backlog_bits(offered_bps, service_bps, duration_s)


def required_service_rate(offered_bps, duration_s, buffer_bits_provided):
    """Return the service rate that holds this burst inside the buffer given.

    Never returns a negative rate: a buffer large enough to swallow the whole
    burst asks nothing of the service rate, and the answer there is zero.
    """
    offered = validate_rate(offered_bps, "offered_bps")
    duration = validate_duration(duration_s)
    size = validate_buffer(buffer_bits_provided)
    needed = offered - (size / duration)
    if needed < 0.0:
        return 0.0
    return needed


def assess_congestion(offered_bps, service_bps, duration_s, buffer_bits_provided):
    """Grade one burst against the link and the buffer behind it."""
    offered = validate_rate(offered_bps, "offered_bps")
    service = validate_rate(service_bps, "service_bps")
    duration = validate_duration(duration_s)
    size = validate_buffer(buffer_bits_provided)
    backlog = backlog_bits(offered, service, duration)
    overflow_at = time_to_overflow(offered, service, size)
    tolerance = REL_TOL * (size if size > 0.0 else max(backlog, 1.0))
    contained = backlog <= size + tolerance
    if backlog == 0.0:
        verdict = NO_CONGESTION
    elif contained:
        verdict = CONTAINED
    else:
        verdict = OVERFLOW
    findings = []
    if verdict == OVERFLOW:
        findings.append(
            "burst leaves %.6g bit against a %.6g bit buffer; the excess is lost "
            "rather than held" % (backlog, size)
        )
        findings.append(
            "buffer of at least %.6g bit, or a service rate of at least %.6g "
            "bit/s, contains this burst"
            % (backlog, required_service_rate(offered, duration, size))
        )
    return {
        "offered_bps": offered,
        "service_bps": service,
        "duration_s": duration,
        "buffer_bits": size,
        "backlog_bits": backlog,
        "congested": backlog > 0.0,
        "contained": contained,
        "time_to_overflow_s": overflow_at,
        "drain_time_s": drain_time(min(backlog, size), service),
        "required_buffer_bits": backlog,
        "required_service_bps": required_service_rate(offered, duration, size),
        "verdict": verdict,
        "findings": findings,
    }
