"""Telecommand delivery confirmation across an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.7 -- confirmation that a telecommand has
been delivered to its destination. Paraphrased into an implementable
procedure; no standard text is reproduced.

The single normative item is that delivery is confirmed, which means the
sender learns, within a bounded time, that the destination has it. Grading a
real dispatch log against a real confirmation log is therefore a matching
problem with a deadline on each match, not a count of confirmations received.

The deadline for a command is its dispatch time plus the transit bound across
the network plus the bound on the confirmation coming back. A confirmation
after that is evidence of delivery but not of the service: by then the sender
has already had to decide what to do without it.

Three things go wrong in the matching itself and each is reported by name. A
confirmation for a command nobody dispatched is a stray, and it usually means
two senders share an identifier space. A second confirmation for the same
command is a duplicate, and the earliest is the one that counts. A
confirmation dated before its own dispatch is impossible and is refused rather
than averaged in.
"""

import math

__all__ = [
    "CONFIRMED",
    "LATE",
    "UNCONFIRMED",
    "REL_TOL",
    "validate_identifier",
    "validate_time",
    "validate_bound",
    "normalise_command",
    "normalise_confirmation",
    "confirmation_deadline",
    "match_confirmations",
    "assess_delivery_confirmation",
]

CONFIRMED = "confirmed"
LATE = "late"
UNCONFIRMED = "unconfirmed"

# Relative tolerance for the deadline comparison, so a confirmation arriving
# exactly on its deadline counts as confirmed on every platform.
REL_TOL = 1e-9


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_identifier(value, name="command_id"):
    """Return a non-empty command identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_time(value, name="time_s"):
    """Return a finite epoch time in seconds. Negative times are allowed."""
    return _number(value, name)


def validate_bound(value, name="bound_s"):
    """Return a non-negative time bound in seconds."""
    bound = _number(value, name)
    if bound < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return bound


def normalise_command(command):
    """Return a validated copy of one dispatched telecommand."""
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping, got %r" % type(command).__name__)
    return {
        "id": validate_identifier(command.get("id"), "command id"),
        "dispatch_s": validate_time(command.get("dispatch_s"), "dispatch_s"),
        "destination": validate_identifier(
            command.get("destination", "unspecified"), "destination"
        ),
    }


def normalise_confirmation(confirmation):
    """Return a validated copy of one delivery confirmation."""
    if not isinstance(confirmation, dict):
        raise ValueError(
            "confirmation must be a mapping, got %r" % type(confirmation).__name__
        )
    return {
        "command_id": validate_identifier(
            confirmation.get("command_id"), "confirmation command_id"
        ),
        "time_s": validate_time(confirmation.get("time_s"), "confirmation time_s"),
    }


def confirmation_deadline(dispatch_s, transit_bound_s, confirmation_bound_s):
    """Return the epoch time by which a confirmation has to be back."""
    return (
        validate_time(dispatch_s, "dispatch_s")
        + validate_bound(transit_bound_s, "transit_bound_s")
        + validate_bound(confirmation_bound_s, "confirmation_bound_s")
    )


def match_confirmations(commands, confirmations):
    """Return (earliest per command, strays, duplicates) from a confirmation log.

    The earliest confirmation for a command is the one that counts; later ones
    are duplicates and are named rather than discarded quietly. A confirmation
    dated before its own dispatch is impossible and is refused outright.
    """
    by_id = dict((c["id"], c) for c in commands)
    earliest = {}
    strays = []
    duplicates = []
    for confirmation in confirmations:
        cid = confirmation["command_id"]
        command = by_id.get(cid)
        if command is None:
            strays.append(confirmation)
            continue
        if confirmation["time_s"] < command["dispatch_s"]:
            raise ValueError(
                "confirmation for %r is dated before the command was dispatched" % cid
            )
        if cid in earliest:
            duplicates.append(confirmation)
            if confirmation["time_s"] < earliest[cid]["time_s"]:
                duplicates[-1] = earliest[cid]
                earliest[cid] = confirmation
        else:
            earliest[cid] = confirmation
    return earliest, strays, duplicates


def assess_delivery_confirmation(
    commands, confirmations, transit_bound_s, confirmation_bound_s
):
    """Assess a telecommand dispatch log against its delivery confirmations."""
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list")
    if not isinstance(confirmations, (list, tuple)):
        raise ValueError("confirmations must be a list")
    if not commands:
        raise ValueError("at least one dispatched telecommand must be declared")
    norm_commands = [normalise_command(c) for c in commands]
    ids = [c["id"] for c in norm_commands]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate command id in the dispatch log")
    norm_confirmations = [normalise_confirmation(c) for c in confirmations]
    transit = validate_bound(transit_bound_s, "transit_bound_s")
    confirm = validate_bound(confirmation_bound_s, "confirmation_bound_s")
    earliest, strays, duplicates = match_confirmations(norm_commands, norm_confirmations)
    per_command = []
    observed = []
    for command in norm_commands:
        deadline = confirmation_deadline(command["dispatch_s"], transit, confirm)
        confirmation = earliest.get(command["id"])
        if confirmation is None:
            per_command.append(
                {
                    "id": command["id"],
                    "destination": command["destination"],
                    "deadline_s": deadline,
                    "confirmed_at_s": None,
                    "latency_s": None,
                    "margin_s": None,
                    "verdict": UNCONFIRMED,
                    "reason": "no delivery confirmation returned for %s" % command["id"],
                }
            )
            continue
        latency = confirmation["time_s"] - command["dispatch_s"]
        observed.append(latency)
        tolerance = REL_TOL * max(abs(confirmation["time_s"]), abs(deadline), 1.0)
        in_time = confirmation["time_s"] <= deadline + tolerance
        per_command.append(
            {
                "id": command["id"],
                "destination": command["destination"],
                "deadline_s": deadline,
                "confirmed_at_s": confirmation["time_s"],
                "latency_s": latency,
                "margin_s": deadline - confirmation["time_s"],
                "verdict": CONFIRMED if in_time else LATE,
                "reason": None
                if in_time
                else "%s was confirmed %.6g s after its deadline"
                % (command["id"], confirmation["time_s"] - deadline),
            }
        )
    unconfirmed = [r["id"] for r in per_command if r["verdict"] == UNCONFIRMED]
    late = [r["id"] for r in per_command if r["verdict"] == LATE]
    findings = []
    if unconfirmed:
        findings.append(
            "delivery is not confirmed for %s" % ", ".join(sorted(unconfirmed))
        )
    if late:
        findings.append(
            "confirmation for %s arrived after the sender had to act without it"
            % ", ".join(sorted(late))
        )
    if strays:
        findings.append(
            "confirmation received for %s, which was never dispatched"
            % ", ".join(sorted(set(s["command_id"] for s in strays)))
        )
    if duplicates:
        findings.append(
            "more than one confirmation received for %s"
            % ", ".join(sorted(set(d["command_id"] for d in duplicates)))
        )
    required_bound = None
    if observed:
        required_bound = max(observed)
    return {
        "commands": ids,
        "transit_bound_s": transit,
        "confirmation_bound_s": confirm,
        "per_command": per_command,
        "confirmed": [r["id"] for r in per_command if r["verdict"] == CONFIRMED],
        "late": late,
        "unconfirmed": unconfirmed,
        "strays": [s["command_id"] for s in strays],
        "duplicates": [d["command_id"] for d in duplicates],
        "worst_observed_latency_s": required_bound,
        "confirmation_ratio": (len(norm_commands) - len(unconfirmed))
        / float(len(norm_commands)),
        "log_clean": not strays and not duplicates,
        "service_confirmed": not unconfirmed and not late,
        "compliant": not unconfirmed and not late and not strays and not duplicates,
        "findings": findings,
    }
