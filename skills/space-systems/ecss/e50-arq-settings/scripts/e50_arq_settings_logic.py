"""Automatic repeat request settings for a space data transfer protocol.

Anchor: ECSS-E-ST-50C clause 5.6.13.5 -- settings of the retransmission
mechanism. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that the retransmission settings are adjustable
and consistent with the link they run over. Two halves, and designs drop the
first one: a timer compiled into the flight software cannot be corrected when
the link turns out different from the analysis.

The consistency half is arithmetic a designer can act on:

  timeout floor   -- round trip plus the far-end acknowledgement delay plus the
                     path jitter; below it the sender retransmits units that
                     were never lost;
  window          -- the bandwidth-delay product in units, rounded up, or the
                     transmitter stalls waiting for acknowledgements;
  worst case      -- attempts times the timeout plus the final round trip;
  residual loss   -- the per-attempt loss compounded over the attempts, with
                     the attempt count that would reach a target.

Stdlib only, offline, deterministic.
"""

import math

CONSISTENT = "consistent"
INCONSISTENT = "inconsistent"

# Relative tolerance for the timeout and window comparisons, so a setting placed
# exactly at its floor is accepted on every platform rather than on some.
REL_TOL = 1e-9

# Parameters the clause expects an operator to be able to change in flight.
COMMANDABLE_PARAMETERS = ("timeout_s", "window_units", "retry_limit")

__all__ = [
    "CONSISTENT",
    "INCONSISTENT",
    "REL_TOL",
    "COMMANDABLE_PARAMETERS",
    "validate_time",
    "validate_positive_time",
    "validate_positive_number",
    "validate_count",
    "validate_probability",
    "validate_commandability",
    "retransmission_timeout_floor",
    "required_window_units",
    "worst_case_delivery_s",
    "residual_loss_probability",
    "attempts_for_residual_target",
    "assess_arq_settings",
]


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_time(value, name="time_s"):
    """Return a non-negative time in seconds."""
    seconds = _number(value, name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return seconds


def validate_positive_time(value, name="time_s"):
    """Return a strictly positive time in seconds."""
    seconds = _number(value, name)
    if seconds <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return seconds


def validate_positive_number(value, name="value"):
    """Return a strictly positive finite number."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_count(value, name="count"):
    """Return a positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def validate_probability(value, name="loss_probability"):
    """Return a probability in the closed interval zero to one."""
    number = _number(value, name)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def validate_commandability(mapping, name="commandable"):
    """Return a mapping saying which parameters an operator can change in flight."""
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping of parameter name to boolean" % name)
    result = {}
    for parameter in COMMANDABLE_PARAMETERS:
        if parameter not in mapping:
            raise ValueError("%s is missing an entry for %r" % (name, parameter))
        value = mapping[parameter]
        if not isinstance(value, bool):
            raise ValueError("%s[%r] must be a boolean, got %r" % (name, parameter, value))
        result[parameter] = value
    unknown = sorted(set(mapping) - set(COMMANDABLE_PARAMETERS))
    if unknown:
        raise ValueError("%s carries parameters the clause does not name: %s" % (name, unknown))
    return result


def retransmission_timeout_floor(round_trip_s, ack_delay_s, jitter_s):
    """Return the shortest timeout that does not retransmit a healthy unit."""
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    ack = validate_time(ack_delay_s, "ack_delay_s")
    jitter = validate_time(jitter_s, "jitter_s")
    return trip + ack + jitter


def required_window_units(rate_bps, unit_bits, round_trip_s, ack_delay_s=0.0):
    """Return the outstanding units needed to keep the transmitter busy.

    Rounded up: a partial unit still occupies the link, and a window rounded
    down leaves the transmitter idle waiting for an acknowledgement.
    """
    rate = validate_positive_number(rate_bps, "rate_bps")
    size = validate_positive_number(unit_bits, "unit_bits")
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    ack = validate_time(ack_delay_s, "ack_delay_s")
    return int(math.ceil((rate * (trip + ack)) / size))


def worst_case_delivery_s(timeout_s, retry_limit, round_trip_s):
    """Return the longest a single unit can take to arrive within the retry limit.

    Every attempt but the last costs a full timeout; the successful attempt
    costs one round trip.
    """
    timeout = validate_positive_time(timeout_s, "timeout_s")
    retries = validate_count(retry_limit, "retry_limit")
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    return (retries - 1) * timeout + trip


def residual_loss_probability(per_attempt_loss, retry_limit):
    """Return the probability a unit is still undelivered after every attempt.

    Compounded by repeated multiplication rather than by raising to a power, so
    the same attempt count gives the same product on every platform.
    """
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    attempts = validate_count(retry_limit, "retry_limit")
    residual = 1.0
    for _ in range(attempts):
        residual *= loss
    return residual


def attempts_for_residual_target(per_attempt_loss, target):
    """Return the attempts needed to bring the residual loss inside a target.

    None means no attempt count reaches it: a link that loses every attempt
    never delivers, however many times it tries.
    """
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    limit = validate_probability(target, "target")
    if loss >= 1.0:
        return None
    residual = 1.0
    attempts = 0
    while attempts < 1000:
        residual *= loss
        attempts += 1
        if residual <= limit + REL_TOL * limit:
            return attempts
    return None


def assess_arq_settings(
    timeout_s,
    window_units,
    retry_limit,
    per_attempt_loss,
    commandable,
    round_trip_s,
    ack_delay_s,
    jitter_s,
    rate_bps,
    unit_bits,
    residual_target,
    delivery_deadline_s=None,
):
    """Assess one ARQ configuration against the link and the clause."""
    timeout = validate_positive_time(timeout_s, "timeout_s")
    window = validate_count(window_units, "window_units")
    retries = validate_count(retry_limit, "retry_limit")
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    flags = validate_commandability(commandable)
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    ack = validate_time(ack_delay_s, "ack_delay_s")
    jitter = validate_time(jitter_s, "jitter_s")
    rate = validate_positive_number(rate_bps, "rate_bps")
    size = validate_positive_number(unit_bits, "unit_bits")
    target = validate_probability(residual_target, "residual_target")
    deadline = None
    if delivery_deadline_s is not None:
        deadline = validate_positive_time(delivery_deadline_s, "delivery_deadline_s")

    floor = retransmission_timeout_floor(trip, ack, jitter)
    needed_window = required_window_units(rate, size, trip, ack)
    worst_case = worst_case_delivery_s(timeout, retries, trip)
    residual = residual_loss_probability(loss, retries)
    needed_attempts = attempts_for_residual_target(loss, target)

    findings = []
    timeout_ok = timeout >= floor - REL_TOL * floor
    if not timeout_ok:
        findings.append(
            "timeout of %.6g s is below the %.6g s floor set by the round trip, the "
            "acknowledgement delay and the jitter; healthy units are retransmitted"
            % (timeout, floor)
        )
    window_ok = window >= needed_window
    if not window_ok:
        findings.append(
            "window of %d units is below the %d the bandwidth-delay product asks for; "
            "the transmitter stalls waiting for acknowledgements" % (window, needed_window)
        )
    residual_ok = residual <= target + REL_TOL * target
    if not residual_ok:
        if needed_attempts is None:
            findings.append(
                "residual loss %.6g exceeds the target %.6g and no attempt count reaches "
                "it at a per-attempt loss of %.6g" % (residual, target, loss)
            )
        else:
            findings.append(
                "residual loss %.6g exceeds the target %.6g; %d attempts reach it"
                % (residual, target, needed_attempts)
            )
    deadline_ok = True
    if deadline is not None:
        deadline_ok = worst_case <= deadline + REL_TOL * deadline
        if not deadline_ok:
            findings.append(
                "worst case delivery of %.6g s exceeds the %.6g s deadline; the retry "
                "limit or the timeout has to come down" % (worst_case, deadline)
            )
    fixed = sorted(name for name, settable in flags.items() if not settable)
    for name in fixed:
        findings.append(
            "%s is fixed in the build and cannot be changed in flight" % name
        )

    consistent = timeout_ok and window_ok and residual_ok and deadline_ok
    adjustable = not fixed
    verdict = CONSISTENT if (consistent and adjustable) else INCONSISTENT
    return {
        "timeout_s": timeout,
        "timeout_floor_s": floor,
        "timeout_ok": timeout_ok,
        "window_units": window,
        "required_window_units": needed_window,
        "window_ok": window_ok,
        "retry_limit": retries,
        "worst_case_delivery_s": worst_case,
        "delivery_deadline_s": deadline,
        "deadline_ok": deadline_ok,
        "per_attempt_loss": loss,
        "residual_loss": residual,
        "residual_target": target,
        "residual_ok": residual_ok,
        "attempts_for_target": needed_attempts,
        "commandable": flags,
        "fixed_parameters": fixed,
        "adjustable": adjustable,
        "consistent": consistent,
        "recommended": {
            "timeout_s": max(timeout, floor),
            "window_units": max(window, needed_window),
            "retry_limit": max(retries, needed_attempts or retries),
        },
        "verdict": verdict,
        "findings": findings,
    }
