"""Telecommand receipt confirmation on a space link.

Anchor: ECSS-E-ST-50C clause 5.6.14.8 -- telecommand receipt confirmation.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that receipt of a telecommand is confirmed to the
sender. A confirmation is only useful against a deadline, and the deadline is
not a free parameter: it is bounded below by the geometry of the link. A
deadline shorter than the round trip plus onboard processing declares timeouts
that no spacecraft could ever avoid, and the ground then retransmits commands
that were received perfectly well the first time.

Each outstanding command is graded into one of four states -- confirmed,
confirmed after the deadline had already expired, still pending inside it, or
timed out -- and each state carries the action the ground should take. The
third state is the one usually missed: a confirmation that arrives late is not
a success, because the retransmission has already gone out and the spacecraft
may act on the command twice.

Confirmations arriving from the spacecraft are graded too, since one naming a
command nobody sent, or a command already confirmed, is itself a finding.
"""

import math

__all__ = [
    "CONFIRMED",
    "CONFIRMED_LATE",
    "PENDING",
    "TIMED_OUT",
    "ACTION_NONE",
    "ACTION_RETRANSMIT",
    "ACTION_ESCALATE",
    "ACCEPTED",
    "DUPLICATE",
    "UNSOLICITED",
    "HEALTHY",
    "RETRANSMISSION_REQUIRED",
    "ESCALATION_REQUIRED",
    "DEADLINE_UNACHIEVABLE",
    "REL_TOL",
    "validate_instant",
    "validate_span",
    "validate_attempts",
    "validate_commands",
    "minimum_confirmation_deadline_s",
    "deadline_is_achievable",
    "confirmation_latency_s",
    "grade_command",
    "next_action",
    "grade_confirmation",
    "assess_confirmation_window",
]

CONFIRMED = "confirmed"
CONFIRMED_LATE = "confirmed-late"
PENDING = "pending"
TIMED_OUT = "timed-out"

ACTION_NONE = "none"
ACTION_RETRANSMIT = "retransmit"
ACTION_ESCALATE = "escalate"

ACCEPTED = "accepted"
DUPLICATE = "duplicate"
UNSOLICITED = "unsolicited"

HEALTHY = "healthy"
RETRANSMISSION_REQUIRED = "retransmission-required"
ESCALATION_REQUIRED = "escalation-required"
DEADLINE_UNACHIEVABLE = "deadline-unachievable"

# Relative tolerance for every deadline comparison, so a confirmation landing
# exactly on the deadline counts as on time on every platform, not on some.
REL_TOL = 1e-9


def _slack(*values):
    return REL_TOL * max([abs(value) for value in values] + [1.0])


def validate_instant(value, name="instant_s"):
    """Return a finite instant on the ground timeline, in seconds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    instant = float(value)
    if math.isnan(instant) or math.isinf(instant):
        raise ValueError("%s must be finite" % name)
    return instant


def validate_span(value, name="span_s"):
    """Return a non-negative interval in seconds."""
    span = validate_instant(value, name)
    if span < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return span


def validate_attempts(value, name="attempts"):
    """Return the number of times a command has been sent, at least once."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer" % name)
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def validate_commands(commands, name="commands"):
    """Return the outstanding command records, checked and with unique ids."""
    if isinstance(commands, (str, bytes)) or not isinstance(commands, (list, tuple)):
        raise ValueError("%s must be a list or tuple of command records" % name)
    checked = []
    seen = set()
    for index, record in enumerate(commands):
        if not isinstance(record, dict):
            raise ValueError("%s[%d] must be a mapping" % (name, index))
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("%s[%d] must carry a non-empty string id" % (name, index))
        if identifier in seen:
            raise ValueError("%s holds more than one command with id %r" % (name, identifier))
        seen.add(identifier)
        sent_at = validate_instant(record.get("sent_at_s"), "%s[%d].sent_at_s" % (name, index))
        confirmed_at = record.get("confirmed_at_s")
        if confirmed_at is not None:
            confirmed_at = validate_instant(
                confirmed_at, "%s[%d].confirmed_at_s" % (name, index)
            )
            if confirmed_at < sent_at:
                raise ValueError(
                    "%s[%d] was confirmed before it was sent" % (name, index)
                )
        attempts = validate_attempts(
            record.get("attempts", 1), "%s[%d].attempts" % (name, index)
        )
        checked.append(
            {
                "id": identifier,
                "sent_at_s": sent_at,
                "confirmed_at_s": confirmed_at,
                "attempts": attempts,
            }
        )
    return checked


def minimum_confirmation_deadline_s(round_trip_light_time_s, onboard_processing_s, margin_s):
    """Return the shortest deadline the link geometry can possibly meet."""
    return (
        validate_span(round_trip_light_time_s, "round_trip_light_time_s")
        + validate_span(onboard_processing_s, "onboard_processing_s")
        + validate_span(margin_s, "margin_s")
    )


def deadline_is_achievable(configured_deadline_s, minimum_deadline_s):
    """Return whether a configured deadline is long enough to ever be met."""
    configured = validate_span(configured_deadline_s, "configured_deadline_s")
    minimum = validate_span(minimum_deadline_s, "minimum_deadline_s")
    return configured >= minimum - _slack(configured, minimum)


def confirmation_latency_s(sent_at_s, confirmed_at_s):
    """Return how long a confirmation took to come back, in seconds."""
    sent = validate_instant(sent_at_s, "sent_at_s")
    confirmed = validate_instant(confirmed_at_s, "confirmed_at_s")
    if confirmed < sent:
        raise ValueError("confirmed_at_s must not precede sent_at_s")
    return confirmed - sent


def grade_command(record, now_s, deadline_s):
    """Return the state of one outstanding command against the deadline."""
    now = validate_instant(now_s, "now_s")
    deadline = validate_span(deadline_s, "deadline_s")
    sent = validate_instant(record.get("sent_at_s"), "sent_at_s")
    confirmed_at = record.get("confirmed_at_s")
    if confirmed_at is not None:
        latency = confirmation_latency_s(sent, confirmed_at)
        if latency <= deadline + _slack(latency, deadline):
            return CONFIRMED
        return CONFIRMED_LATE
    if now < sent:
        raise ValueError("now_s must not precede the time the command was sent")
    if now - sent <= deadline + _slack(now - sent, deadline):
        return PENDING
    return TIMED_OUT


def next_action(status, attempts, retransmission_limit):
    """Return what the ground should do about a command in this state."""
    tries = validate_attempts(attempts)
    if isinstance(retransmission_limit, bool) or not isinstance(retransmission_limit, int):
        raise ValueError("retransmission_limit must be an integer")
    if retransmission_limit < 0:
        raise ValueError(
            "retransmission_limit must not be negative, got %r" % (retransmission_limit,)
        )
    if status != TIMED_OUT:
        return ACTION_NONE
    if tries <= retransmission_limit:
        return ACTION_RETRANSMIT
    return ACTION_ESCALATE


def grade_confirmation(confirmation_id, sent_ids, already_confirmed_ids):
    """Return whether an arriving confirmation is expected, repeated or unknown."""
    if not isinstance(confirmation_id, str) or not confirmation_id:
        raise ValueError("confirmation_id must be a non-empty string")
    if confirmation_id not in set(sent_ids):
        return UNSOLICITED
    if confirmation_id in set(already_confirmed_ids):
        return DUPLICATE
    return ACCEPTED


def assess_confirmation_window(
    commands,
    now_s,
    round_trip_light_time_s,
    onboard_processing_s,
    margin_s,
    configured_deadline_s=None,
    retransmission_limit=3,
):
    """Grade a window of outstanding telecommands and their confirmations."""
    checked = validate_commands(commands)
    now = validate_instant(now_s, "now_s")
    minimum = minimum_confirmation_deadline_s(
        round_trip_light_time_s, onboard_processing_s, margin_s
    )
    if configured_deadline_s is None:
        deadline = minimum
    else:
        deadline = validate_span(configured_deadline_s, "configured_deadline_s")
    achievable = deadline_is_achievable(deadline, minimum)
    outcomes = []
    counts = {CONFIRMED: 0, CONFIRMED_LATE: 0, PENDING: 0, TIMED_OUT: 0}
    for record in checked:
        status = grade_command(record, now, deadline)
        action = next_action(status, record["attempts"], retransmission_limit)
        latency = None
        if record["confirmed_at_s"] is not None:
            latency = confirmation_latency_s(record["sent_at_s"], record["confirmed_at_s"])
        counts[status] = counts[status] + 1
        outcomes.append(
            {
                "id": record["id"],
                "status": status,
                "action": action,
                "attempts": record["attempts"],
                "latency_s": latency,
                "age_s": now - record["sent_at_s"],
            }
        )
    latencies = [o["latency_s"] for o in outcomes if o["latency_s"] is not None]
    worst_latency = max(latencies) if latencies else None
    findings = []
    if not achievable:
        findings.append(
            "confirmation deadline of %.9g s is below the %.9g s the round trip, "
            "onboard processing and margin already consume; every command times "
            "out before a confirmation could arrive" % (deadline, minimum)
        )
        findings.append(
            "a deadline of at least %.9g s is the shortest this geometry can meet"
            % (minimum,)
        )
    late = [o["id"] for o in outcomes if o["status"] == CONFIRMED_LATE]
    if late:
        findings.append(
            "confirmation for %s arrived after the deadline had expired, so a "
            "retransmission was already sent and the command may be acted on "
            "twice unless it is idempotent" % (", ".join(late),)
        )
    escalating = [o["id"] for o in outcomes if o["action"] == ACTION_ESCALATE]
    if escalating:
        findings.append(
            "%s reached the retransmission limit of %d; the link rather than the "
            "command is the fault to report" % (", ".join(escalating), retransmission_limit)
        )
    retransmitting = [o["id"] for o in outcomes if o["action"] == ACTION_RETRANSMIT]
    if not achievable:
        verdict = DEADLINE_UNACHIEVABLE
    elif escalating:
        verdict = ESCALATION_REQUIRED
    elif retransmitting:
        verdict = RETRANSMISSION_REQUIRED
    else:
        verdict = HEALTHY
    return {
        "now_s": now,
        "minimum_deadline_s": minimum,
        "deadline_s": deadline,
        "deadline_achievable": achievable,
        "retransmission_limit": retransmission_limit,
        "outcomes": outcomes,
        "counts": counts,
        "worst_latency_s": worst_latency,
        "retransmit_ids": retransmitting,
        "escalate_ids": escalating,
        "late_confirmation_ids": late,
        "verdict": verdict,
        "findings": findings,
    }
