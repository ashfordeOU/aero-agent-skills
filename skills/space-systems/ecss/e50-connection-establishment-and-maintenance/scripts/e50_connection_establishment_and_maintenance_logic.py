"""Connection establishment and maintenance on a space link service.

Anchor: ECSS-E-ST-50C clause 5.6.14.1 -- establishment and maintenance of a
connection for a connection-oriented service. Paraphrased into an implementable
procedure; no standard text is reproduced.

The single normative item is that the service both opens a connection and keeps
it open for as long as the exchange needs it. Two failure modes sit inside one
obligation, so the procedure grades both:

  establishment -- the handshake costs a round trip per exchange plus the time
                   the far end spends deciding, which sets a floor under the
                   timeout; the attempts allowed multiply that floor into a
                   worst case time to open;
  maintenance   -- the connection survives only while keepalives keep arriving,
                   so the interval times one more than the tolerated losses has
                   to stay inside the inactivity timeout;
  transitions   -- a recorded state trace is replayed against the transitions
                   the service allows, and the first step the machine does not
                   permit is named.

Stdlib only, offline, deterministic.
"""

import math

CLOSED = "closed"
ESTABLISHING = "establishing"
OPEN = "open"
MAINTAINING = "maintaining"
CLOSING = "closing"

VALID_STATES = (CLOSED, ESTABLISHING, OPEN, MAINTAINING, CLOSING)

# The transitions a connection-oriented service allows. Establishment may fail
# back to closed; an open connection may be maintained and return to open; and
# closing always ends at closed.
ALLOWED_TRANSITIONS = {
    CLOSED: (ESTABLISHING,),
    ESTABLISHING: (OPEN, CLOSED),
    OPEN: (MAINTAINING, CLOSING, CLOSED),
    MAINTAINING: (OPEN, CLOSING, CLOSED),
    CLOSING: (CLOSED,),
}

SUPPORTED = "supported"
UNSUPPORTED = "unsupported"

# Relative tolerance for the timeout and keepalive comparisons, so a setting
# placed exactly on its bound decides the same way on every platform.
REL_TOL = 1e-9

__all__ = [
    "CLOSED",
    "ESTABLISHING",
    "OPEN",
    "MAINTAINING",
    "CLOSING",
    "VALID_STATES",
    "ALLOWED_TRANSITIONS",
    "SUPPORTED",
    "UNSUPPORTED",
    "REL_TOL",
    "validate_state",
    "validate_count",
    "validate_time",
    "validate_positive_time",
    "transition_allowed",
    "replay_state_trace",
    "establishment_timeout_floor_s",
    "worst_case_time_to_open_s",
    "keepalive_budget_s",
    "recommended_keepalive_interval_s",
    "assess_connection",
]


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_state(value, name="state"):
    """Return a recognised connection state."""
    if value not in VALID_STATES:
        raise ValueError("%s must be one of %s, got %r" % (name, list(VALID_STATES), value))
    return value


def validate_count(value, name="count", minimum=1):
    """Return an integer count at or above the minimum."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


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


def transition_allowed(from_state, to_state):
    """Return whether the service allows this state change."""
    source = validate_state(from_state, "from_state")
    target = validate_state(to_state, "to_state")
    return target in ALLOWED_TRANSITIONS[source]


def replay_state_trace(trace):
    """Replay a recorded connection state trace against the allowed transitions.

    Returns every step the machine does not permit, each as the index in the
    trace and the two states involved, so an implementer can see which step
    broke rather than only that one did.
    """
    if not isinstance(trace, (list, tuple)):
        raise ValueError("trace must be a list or tuple of states")
    if len(trace) < 1:
        raise ValueError("trace must carry at least one state")
    for state in trace:
        validate_state(state)
    violations = []
    for index in range(1, len(trace)):
        source = trace[index - 1]
        target = trace[index]
        if not transition_allowed(source, target):
            violations.append({"index": index, "from": source, "to": target})
    reached_open = OPEN in trace or MAINTAINING in trace
    return {
        "steps": max(len(trace) - 1, 0),
        "violations": violations,
        "valid": not violations,
        "reached_open": reached_open,
        "final_state": trace[-1],
    }


def establishment_timeout_floor_s(handshake_exchanges, round_trip_s, far_end_processing_s=0.0):
    """Return the shortest establishment timeout that does not abandon a healthy open.

    Each exchange in the handshake costs a round trip, and the far end spends
    its processing time once per exchange before it answers.
    """
    exchanges = validate_count(handshake_exchanges, "handshake_exchanges")
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    processing = validate_time(far_end_processing_s, "far_end_processing_s")
    return exchanges * (trip + processing)


def worst_case_time_to_open_s(timeout_s, attempts, round_trip_s, handshake_exchanges,
                              far_end_processing_s=0.0):
    """Return the longest a connection can take to open within the attempts allowed.

    Every attempt but the last is abandoned at the full timeout; the successful
    attempt costs the handshake itself.
    """
    timeout = validate_positive_time(timeout_s, "timeout_s")
    tries = validate_count(attempts, "attempts")
    floor = establishment_timeout_floor_s(
        handshake_exchanges, round_trip_s, far_end_processing_s
    )
    return (tries - 1) * timeout + floor


def keepalive_budget_s(keepalive_interval_s, tolerated_losses):
    """Return the silence the connection has to survive before it is declared down.

    One more interval than the tolerated losses: the losses plus the keepalive
    that finally has to arrive.
    """
    interval = validate_positive_time(keepalive_interval_s, "keepalive_interval_s")
    losses = validate_count(tolerated_losses, "tolerated_losses", minimum=0)
    return interval * (losses + 1)


def recommended_keepalive_interval_s(inactivity_timeout_s, tolerated_losses):
    """Return the longest interval that still survives the tolerated losses."""
    timeout = validate_positive_time(inactivity_timeout_s, "inactivity_timeout_s")
    losses = validate_count(tolerated_losses, "tolerated_losses", minimum=0)
    return timeout / float(losses + 1)


def assess_connection(
    handshake_exchanges,
    round_trip_s,
    far_end_processing_s,
    establishment_timeout_s,
    attempts,
    contact_time_s,
    keepalive_interval_s,
    inactivity_timeout_s,
    tolerated_losses,
    state_trace=None,
):
    """Assess one connection-oriented service against both halves of the clause."""
    exchanges = validate_count(handshake_exchanges, "handshake_exchanges")
    trip = validate_positive_time(round_trip_s, "round_trip_s")
    processing = validate_time(far_end_processing_s, "far_end_processing_s")
    timeout = validate_positive_time(establishment_timeout_s, "establishment_timeout_s")
    tries = validate_count(attempts, "attempts")
    contact = validate_positive_time(contact_time_s, "contact_time_s")
    interval = validate_positive_time(keepalive_interval_s, "keepalive_interval_s")
    inactivity = validate_positive_time(inactivity_timeout_s, "inactivity_timeout_s")
    losses = validate_count(tolerated_losses, "tolerated_losses", minimum=0)

    floor = establishment_timeout_floor_s(exchanges, trip, processing)
    worst_case = worst_case_time_to_open_s(timeout, tries, trip, exchanges, processing)
    budget = keepalive_budget_s(interval, losses)
    recommended_interval = recommended_keepalive_interval_s(inactivity, losses)

    findings = []
    timeout_ok = timeout >= floor - REL_TOL * floor
    if not timeout_ok:
        findings.append(
            "establishment timeout of %.6g s is below the %.6g s the handshake costs; "
            "connections that were about to open are abandoned" % (timeout, floor)
        )
    contact_ok = worst_case <= contact + REL_TOL * contact
    if not contact_ok:
        findings.append(
            "worst case time to open of %.6g s exceeds the %.6g s contact; the attempts "
            "or the timeout has to come down" % (worst_case, contact)
        )
    maintenance_ok = budget <= inactivity + REL_TOL * inactivity
    if not maintenance_ok:
        findings.append(
            "keepalive interval of %.6g s does not survive %d lost keepalives inside the "
            "%.6g s inactivity timeout; %.6g s does"
            % (interval, losses, inactivity, recommended_interval)
        )
    wasteful = interval < recommended_interval / 10.0
    if wasteful:
        findings.append(
            "keepalive interval of %.6g s is far shorter than the %.6g s the timeout "
            "allows; the supervision traffic competes with the data"
            % (interval, recommended_interval)
        )
    replay = None
    if state_trace is not None:
        replay = replay_state_trace(state_trace)
        for violation in replay["violations"]:
            findings.append(
                "state trace step %d moves from %s to %s, which the service does not allow"
                % (violation["index"], violation["from"], violation["to"])
            )

    trace_ok = replay is None or replay["valid"]
    verdict = SUPPORTED if (timeout_ok and contact_ok and maintenance_ok and trace_ok) else UNSUPPORTED
    return {
        "handshake_exchanges": exchanges,
        "round_trip_s": trip,
        "establishment_timeout_s": timeout,
        "establishment_timeout_floor_s": floor,
        "timeout_ok": timeout_ok,
        "attempts": tries,
        "worst_case_time_to_open_s": worst_case,
        "contact_time_s": contact,
        "contact_ok": contact_ok,
        "keepalive_interval_s": interval,
        "keepalive_budget_s": budget,
        "inactivity_timeout_s": inactivity,
        "tolerated_losses": losses,
        "maintenance_ok": maintenance_ok,
        "keepalive_is_wasteful": wasteful,
        "recommended_keepalive_interval_s": recommended_interval,
        "state_replay": replay,
        "trace_ok": trace_ok,
        "verdict": verdict,
        "findings": findings,
    }
