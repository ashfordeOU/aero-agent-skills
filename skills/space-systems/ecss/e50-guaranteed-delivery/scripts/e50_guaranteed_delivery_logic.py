"""Guaranteed delivery on a space data transfer service.

Anchor: ECSS-E-ST-50C clause 5.6.14.2 -- guaranteed delivery of the data units
handed to the service. Paraphrased into an implementable procedure; no standard
text is reproduced.

The single normative item is that each data unit handed to the service reaches
the far end once and in order, or the sender is told that it did not. Three
obligations and one honest get-out, all of which a recorded delivery can be
checked against:

  completeness -- every unit handed over was delivered, or its absence was
                  notified to the sender;
  exactly once -- no unit was delivered twice;
  order        -- units arrived in the order they were handed over, with an
                  arrival ahead of an outstanding unit counted as a reordering
                  rather than as a loss.

Alongside the trace, the design side of the same obligation: the per-attempt
loss compounded over the retransmissions allowed, the attempt count a residual
target needs, and the residual scaled by the units in the transfer.

Stdlib only, offline, deterministic. The compounding is done by repeated
multiplication rather than by a power function, so the same attempt count gives
the same product on every platform.
"""

import math

GUARANTEED = "guaranteed"
BOUNDED = "bounded"
BROKEN = "broken"

# Relative tolerance for the residual comparison, so a design landing exactly on
# its target decides the same way on every platform.
REL_TOL = 1e-9

__all__ = [
    "GUARANTEED",
    "BOUNDED",
    "BROKEN",
    "REL_TOL",
    "validate_identifiers",
    "validate_probability",
    "validate_count",
    "replay_delivery",
    "residual_loss_probability",
    "attempts_for_residual_target",
    "expected_undelivered_units",
    "assess_guaranteed_delivery",
]


def validate_identifiers(values, name="identifiers", allow_repeats=False):
    """Return a list of integer data unit identifiers.

    The handed-over list may not repeat an identifier: the service is asked to
    deliver each unit once, so handing the same identifier over twice is an
    input error rather than a duplicate delivery.
    """
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple of identifiers" % name)
    result = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("%s carries a non-integer identifier %r" % (name, item))
        if item < 0:
            raise ValueError("%s carries a negative identifier %r" % (name, item))
        result.append(item)
    if not allow_repeats and len(set(result)) != len(result):
        raise ValueError("%s repeats an identifier" % name)
    return result


def validate_probability(value, name="probability"):
    """Return a probability in the closed interval zero to one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def validate_count(value, name="count", minimum=1):
    """Return an integer count at or above the minimum."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def replay_delivery(handed_over, delivered):
    """Replay one delivery and separate loss, duplication and reordering.

    An identifier that arrives ahead of one still outstanding is a reordering,
    not a loss: the outstanding unit stays outstanding and is only reported
    missing if it never turns up.
    """
    sent = validate_identifiers(handed_over, "handed_over")
    arrived = validate_identifiers(delivered, "delivered", allow_repeats=True)
    expected_order = {identifier: index for index, identifier in enumerate(sent)}
    unknown = [item for item in arrived if item not in expected_order]
    if unknown:
        raise ValueError("delivered carries identifiers never handed over: %s" % unknown)

    seen = set()
    duplicates = []
    out_of_order = []
    highest_index_seen = -1
    for item in arrived:
        if item in seen:
            duplicates.append(item)
            continue
        seen.add(item)
        index = expected_order[item]
        if index < highest_index_seen:
            out_of_order.append(item)
        if index > highest_index_seen:
            highest_index_seen = index
    missing = [identifier for identifier in sent if identifier not in seen]
    return {
        "handed_over": len(sent),
        "delivered": len(seen),
        "missing": missing,
        "duplicates": duplicates,
        "out_of_order": out_of_order,
        "complete": not missing,
        "exactly_once": not duplicates,
        "in_order": not out_of_order,
    }


def residual_loss_probability(per_attempt_loss, attempts):
    """Return the probability a unit is still undelivered after every attempt."""
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    tries = validate_count(attempts, "attempts")
    residual = 1.0
    for _ in range(tries):
        residual *= loss
    return residual


def attempts_for_residual_target(per_attempt_loss, target, ceiling=1000):
    """Return the attempts needed to bring the residual inside a target.

    None means no attempt count reaches it: a link that loses every attempt
    never delivers, however many times it tries.
    """
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    limit = validate_probability(target, "target")
    cap = validate_count(ceiling, "ceiling")
    if loss >= 1.0:
        return None
    residual = 1.0
    attempts = 0
    while attempts < cap:
        residual *= loss
        attempts += 1
        if residual <= limit + REL_TOL * limit:
            return attempts
    return None


def expected_undelivered_units(per_attempt_loss, attempts, units_in_transfer):
    """Return the units expected to remain undelivered across a whole transfer."""
    count = validate_count(units_in_transfer, "units_in_transfer")
    return residual_loss_probability(per_attempt_loss, attempts) * float(count)


def assess_guaranteed_delivery(
    handed_over,
    delivered,
    sender_notified,
    per_attempt_loss,
    attempts,
    residual_target,
):
    """Assess one guaranteed delivery service against the clause."""
    if not isinstance(sender_notified, bool):
        raise ValueError("sender_notified must be a boolean")
    loss = validate_probability(per_attempt_loss, "per_attempt_loss")
    tries = validate_count(attempts, "attempts")
    target = validate_probability(residual_target, "residual_target")
    replay = replay_delivery(handed_over, delivered)

    residual = residual_loss_probability(loss, tries)
    needed_attempts = attempts_for_residual_target(loss, target)
    expected_undelivered = expected_undelivered_units(loss, tries, replay["handed_over"])

    findings = []
    if replay["missing"]:
        if sender_notified:
            findings.append(
                "%d unit(s) were not delivered and the sender was notified; the service "
                "is bounded rather than guaranteed" % len(replay["missing"])
            )
        else:
            findings.append(
                "%d unit(s) were not delivered and the sender was not notified; the "
                "guarantee is broken" % len(replay["missing"])
            )
    if replay["duplicates"]:
        findings.append(
            "%d unit(s) were delivered more than once; exactly-once delivery is not met"
            % len(replay["duplicates"])
        )
    if replay["out_of_order"]:
        findings.append(
            "%d unit(s) arrived ahead of units still outstanding; ordered delivery is "
            "not met" % len(replay["out_of_order"])
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

    if replay["duplicates"] or replay["out_of_order"]:
        verdict = BROKEN
    elif replay["missing"]:
        verdict = BOUNDED if sender_notified else BROKEN
    else:
        verdict = GUARANTEED
    return {
        "handed_over": replay["handed_over"],
        "delivered": replay["delivered"],
        "missing": replay["missing"],
        "duplicates": replay["duplicates"],
        "out_of_order": replay["out_of_order"],
        "sender_notified": sender_notified,
        "complete": replay["complete"],
        "exactly_once": replay["exactly_once"],
        "in_order": replay["in_order"],
        "per_attempt_loss": loss,
        "attempts": tries,
        "residual_loss": residual,
        "residual_target": target,
        "residual_ok": residual_ok,
        "attempts_for_target": needed_attempts,
        "expected_undelivered_units": expected_undelivered,
        "verdict": verdict,
        "findings": findings,
    }
