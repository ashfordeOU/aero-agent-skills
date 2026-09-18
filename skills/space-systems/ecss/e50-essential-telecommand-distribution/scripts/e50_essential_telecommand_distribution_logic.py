#!/usr/bin/env python3
"""Distribution of essential telecommands, ECSS-E-ST-50C clause 5.4.4.

Paraphrased requirement, no standard text reproduced. The clause carries four
obligations on the way an essential telecommand reaches the unit it acts on.
Each is a separate property of the route, each fails for a different reason,
and each has a different fix, so this module keeps them apart end to end:

  1. the route is decoded in hardware, not by flight software
  2. the route shares no single failure point with the nominal command path
  3. the route exists in every mission configuration the command is needed in
  4. the route delivers inside the latency the command was specified against

An essential command is assessed against all four, the findings are named per
obligation, and a distribution architecture is then summarized by how many of
its essential commands satisfy all four at once.

Latency comparisons carry an explicit tolerance, so a route budgeted exactly
on its bound is read the same way on every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Seconds of slack allowed when a route's budget lands on its bound.
TIME_TOLERANCE_S = 1e-9

# Obligation tokens, in clause order.
HARDWARE_DECODED = "hardware-decoded-route"
SEGREGATED = "segregated-from-nominal-path"
AVAILABLE_IN_ALL_MODES = "available-in-every-required-mode"
WITHIN_LATENCY = "within-specified-latency"
OBLIGATIONS = (
    HARDWARE_DECODED,
    SEGREGATED,
    AVAILABLE_IN_ALL_MODES,
    WITHIN_LATENCY,
)

# Verdict tokens for a whole architecture.
FULLY_DISTRIBUTED = "every-essential-command-distributed"
PARTIALLY_DISTRIBUTED = "some-essential-commands-not-distributed"
NOT_DISTRIBUTED = "no-essential-command-distributed"
VERDICTS = (FULLY_DISTRIBUTED, PARTIALLY_DISTRIBUTED, NOT_DISTRIBUTED)

_COMMAND_KEYS = (
    "id",
    "decoded_in_hardware",
    "shared_failure_points",
    "available_modes",
    "delivery_latency_s",
    "specified_latency_s",
)


def _number(value, name):
    """Return value as a finite float, refusing bools, text and NaN."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def _non_negative(value, name):
    """Return value as a finite float at or above zero."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _flag(value, name):
    """Return value as a bool, refusing integers and text standing in for one."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def _token_set(value, name):
    """Return a collection of non-empty name tokens as a frozen set."""
    if isinstance(value, str) or not isinstance(
        value, (list, tuple, set, frozenset)
    ):
        raise ValueError("%s must be a collection of names, got %r" % (name, value))
    tokens = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s entries must be non-empty strings" % name)
        tokens.add(item.strip())
    return frozenset(tokens)


def validate_required_modes(modes):
    """Validate the mission configurations an essential command is needed in."""
    tokens = _token_set(modes, "required_modes")
    if not tokens:
        raise ValueError("required_modes must name at least one configuration")
    return tokens


def validate_essential_command(command):
    """Validate one essential command route record and return it normalized."""
    if not isinstance(command, dict):
        raise ValueError("essential command must be a mapping, got %r" % (command,))
    missing = [key for key in _COMMAND_KEYS if key not in command]
    if missing:
        raise ValueError("essential command is missing keys: %s" % ", ".join(missing))
    identifier = command["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("essential command id must be a non-empty string")
    return {
        "id": identifier.strip(),
        "decoded_in_hardware": _flag(
            command["decoded_in_hardware"], "decoded_in_hardware"
        ),
        "shared_failure_points": _token_set(
            command["shared_failure_points"], "shared_failure_points"
        ),
        "available_modes": _token_set(command["available_modes"], "available_modes"),
        "delivery_latency_s": _non_negative(
            command["delivery_latency_s"], "delivery_latency_s"
        ),
        "specified_latency_s": _non_negative(
            command["specified_latency_s"], "specified_latency_s"
        ),
    }


def within_latency(delivery_s, specified_s):
    """True when a delivery budget is at or inside the specified latency."""
    delivery = _non_negative(delivery_s, "delivery_latency_s")
    specified = _non_negative(specified_s, "specified_latency_s")
    return delivery <= specified + TIME_TOLERANCE_S


def check_hardware_decoded(command):
    """Obligation 1: the route does not depend on flight software to decode."""
    return validate_essential_command(command)["decoded_in_hardware"]


def check_segregation(command):
    """Obligation 2: the route shares no failure point with the nominal path."""
    return not validate_essential_command(command)["shared_failure_points"]


def check_mode_availability(command, required_modes):
    """Obligation 3: the route exists in every configuration that needs it."""
    record = validate_essential_command(command)
    return validate_required_modes(required_modes).issubset(record["available_modes"])


def check_latency(command):
    """Obligation 4: the route delivers inside the latency it was specified to."""
    record = validate_essential_command(command)
    return within_latency(record["delivery_latency_s"], record["specified_latency_s"])


def missing_modes(command, required_modes):
    """The configurations in which this essential command has no route."""
    record = validate_essential_command(command)
    wanted = validate_required_modes(required_modes)
    return tuple(sorted(wanted - record["available_modes"]))


def assess_essential_command(command, required_modes):
    """Assess one essential command against all four clause 5.4.4 obligations."""
    record = validate_essential_command(command)
    wanted = validate_required_modes(required_modes)

    results = {
        HARDWARE_DECODED: check_hardware_decoded(record),
        SEGREGATED: check_segregation(record),
        AVAILABLE_IN_ALL_MODES: check_mode_availability(record, wanted),
        WITHIN_LATENCY: check_latency(record),
    }

    findings = []
    if not results[HARDWARE_DECODED]:
        findings.append(
            "%s is decoded by flight software, so it is lost with the processor"
            % record["id"]
        )
    if not results[SEGREGATED]:
        findings.append(
            "%s shares %s with the nominal command path"
            % (record["id"], ", ".join(sorted(record["shared_failure_points"])))
        )
    absent = missing_modes(record, wanted)
    if absent:
        findings.append(
            "%s has no route in %s" % (record["id"], ", ".join(absent))
        )
    if not results[WITHIN_LATENCY]:
        findings.append(
            "%s delivers in %.6f s against a specified %.6f s"
            % (
                record["id"],
                record["delivery_latency_s"],
                record["specified_latency_s"],
            )
        )

    satisfied = tuple(token for token in OBLIGATIONS if results[token])
    return {
        "id": record["id"],
        "obligations": results,
        "satisfied": satisfied,
        "failed": tuple(token for token in OBLIGATIONS if not results[token]),
        "missing_modes": absent,
        "findings": findings,
        "distributed": len(satisfied) == len(OBLIGATIONS),
    }


def assess_distribution(commands, required_modes):
    """Assess a whole essential-telecommand distribution architecture."""
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence of command records")
    wanted = validate_required_modes(required_modes)

    seen = set()
    reports = []
    for command in commands:
        report = assess_essential_command(command, wanted)
        if report["id"] in seen:
            raise ValueError("duplicate essential command id %r" % report["id"])
        seen.add(report["id"])
        reports.append(report)

    distributed = [report for report in reports if report["distributed"]]
    findings = []
    for report in reports:
        findings.extend(report["findings"])

    if len(distributed) == len(reports):
        verdict = FULLY_DISTRIBUTED
    elif distributed:
        verdict = PARTIALLY_DISTRIBUTED
    else:
        verdict = NOT_DISTRIBUTED

    failures_by_obligation = {
        token: tuple(
            report["id"] for report in reports if token in report["failed"]
        )
        for token in OBLIGATIONS
    }

    return {
        "required_modes": tuple(sorted(wanted)),
        "command_count": len(reports),
        "distributed_count": len(distributed),
        "coverage_fraction": len(distributed) / len(reports),
        "commands": tuple(reports),
        "failures_by_obligation": failures_by_obligation,
        "findings": findings,
        "verdict": verdict,
        "compliant": verdict == FULLY_DISTRIBUTED,
    }
