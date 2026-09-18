#!/usr/bin/env python3
"""Cessation of emission on command, ECSS-E-ST-50C clause 5.3.3.

Paraphrased requirement, no standard text reproduced. The clause places one
obligation on a spacecraft radio system: it has to be possible to stop the
space-to-ground emission by command. This module turns that obligation into a
deterministic assessment of a real inhibit architecture:

  inhibit path record        -> validated, with its impairments named
  impairments                -> credible path or not a path at all
  credible paths + timings   -> worst-case time from ground request to carrier off
  credible path count        -> does cessation survive one failure
  time vs. required deadline -> comply or report what is missing

Every comparison against a deadline is made with an explicit tolerance rather
than a bare strict inequality, so a path whose budget lands exactly on the
deadline is read the same way on every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Seconds of slack allowed when a computed budget lands on its bound. Time
# budgets are sums of floats; an exact landing must not flip on rounding.
TIME_TOLERANCE_S = 1e-9

# Default deadline, in seconds, from the ground issuing the request to the
# carrier being off, when a project states none.
DEFAULT_CESSATION_DEADLINE_S = 300.0

# Impairment tokens a path can carry.
ROUTED_THROUGH_EMITTING_CHAIN = "routed-through-emitting-chain"
UNAVAILABLE_IN_SAFE_MODE = "unavailable-in-safe-mode"
SOFTWARE_DEPENDENT = "software-dependent"
IMPAIRMENTS = (
    ROUTED_THROUGH_EMITTING_CHAIN,
    UNAVAILABLE_IN_SAFE_MODE,
    SOFTWARE_DEPENDENT,
)

# Impairments that remove a path from the credible set outright: a path that
# runs through the unit which is stuck on cannot switch that unit off, and a
# path that disappears in safe mode is absent exactly when it is wanted.
DISQUALIFYING_IMPAIRMENTS = (
    ROUTED_THROUGH_EMITTING_CHAIN,
    UNAVAILABLE_IN_SAFE_MODE,
)

# Verdict tokens.
COMPLIANT = "cessation-demonstrated"
SINGLE_PATH = "cessation-not-single-failure-tolerant"
TOO_SLOW = "cessation-too-slow"
NOT_COMMANDABLE = "cessation-not-commandable"
VERDICTS = (COMPLIANT, SINGLE_PATH, TOO_SLOW, NOT_COMMANDABLE)

_PATH_KEYS = (
    "id",
    "latency_s",
    "routed_through_emitting_chain",
    "available_in_safe_mode",
    "requires_onboard_software",
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
    """Return value as a finite, non-negative float."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _flag(value, name):
    """Return value as a bool, refusing integers and text standing in for one."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def meets_deadline(elapsed_s, deadline_s):
    """True when an elapsed time is at or inside a deadline, tolerance included."""
    elapsed = _non_negative(elapsed_s, "elapsed_s")
    deadline = _non_negative(deadline_s, "deadline_s")
    return elapsed <= deadline + TIME_TOLERANCE_S


def validate_inhibit_path(path):
    """Validate one inhibit path record and return it normalized."""
    if not isinstance(path, dict):
        raise ValueError("inhibit path must be a mapping, got %r" % (path,))
    missing = [key for key in _PATH_KEYS if key not in path]
    if missing:
        raise ValueError("inhibit path is missing keys: %s" % ", ".join(missing))
    identifier = path["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("inhibit path id must be a non-empty string")
    return {
        "id": identifier.strip(),
        "latency_s": _non_negative(path["latency_s"], "latency_s"),
        "routed_through_emitting_chain": _flag(
            path["routed_through_emitting_chain"], "routed_through_emitting_chain"
        ),
        "available_in_safe_mode": _flag(
            path["available_in_safe_mode"], "available_in_safe_mode"
        ),
        "requires_onboard_software": _flag(
            path["requires_onboard_software"], "requires_onboard_software"
        ),
    }


def path_impairments(path):
    """Name every impairment carried by one inhibit path, in a fixed order."""
    record = validate_inhibit_path(path)
    found = []
    if record["routed_through_emitting_chain"]:
        found.append(ROUTED_THROUGH_EMITTING_CHAIN)
    if not record["available_in_safe_mode"]:
        found.append(UNAVAILABLE_IN_SAFE_MODE)
    if record["requires_onboard_software"]:
        found.append(SOFTWARE_DEPENDENT)
    return tuple(found)


def path_is_credible(path):
    """True when a path can still command cessation with the radio stuck on."""
    return not any(
        token in DISQUALIFYING_IMPAIRMENTS for token in path_impairments(path)
    )


def path_response_time_s(path, uplink_delay_s=0.0, ground_reaction_s=0.0):
    """Time from the ground deciding to stop the emission to the carrier off."""
    record = validate_inhibit_path(path)
    uplink = _non_negative(uplink_delay_s, "uplink_delay_s")
    reaction = _non_negative(ground_reaction_s, "ground_reaction_s")
    return reaction + uplink + record["latency_s"]


def credible_response_times(paths, uplink_delay_s=0.0, ground_reaction_s=0.0):
    """Ascending response times of the credible paths only."""
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty sequence of path records")
    seen = set()
    times = []
    for path in paths:
        record = validate_inhibit_path(path)
        if record["id"] in seen:
            raise ValueError("duplicate inhibit path id %r" % record["id"])
        seen.add(record["id"])
        if path_is_credible(record):
            times.append(
                path_response_time_s(record, uplink_delay_s, ground_reaction_s)
            )
    return tuple(sorted(times))


def response_time_after_single_failure(
    paths, uplink_delay_s=0.0, ground_reaction_s=0.0
):
    """Worst-case cessation time once the fastest credible path has failed.

    Returns None when fewer than two credible paths exist, because there is
    then no time to quote: one failure removes the capability altogether.
    """
    times = credible_response_times(paths, uplink_delay_s, ground_reaction_s)
    if len(times) < 2:
        return None
    return times[1]


def assess_cessation_of_emission(
    paths,
    deadline_s=DEFAULT_CESSATION_DEADLINE_S,
    uplink_delay_s=0.0,
    ground_reaction_s=0.0,
):
    """Assess a cessation-of-emission architecture against clause 5.3.3."""
    deadline = _non_negative(deadline_s, "deadline_s")
    times = credible_response_times(paths, uplink_delay_s, ground_reaction_s)
    degraded = response_time_after_single_failure(
        paths, uplink_delay_s, ground_reaction_s
    )

    findings = []
    limitations = []
    for path in paths:
        record = validate_inhibit_path(path)
        impairments = path_impairments(record)
        for token in impairments:
            if token in DISQUALIFYING_IMPAIRMENTS:
                findings.append(
                    "inhibit path %s cannot be relied on: %s"
                    % (record["id"], token)
                )
            else:
                limitations.append(
                    "inhibit path %s is %s" % (record["id"], token)
                )

    nominal = times[0] if times else None
    if not times:
        verdict = NOT_COMMANDABLE
        findings.append("no credible inhibit path; emission cannot be commanded off")
    elif not meets_deadline(nominal, deadline):
        verdict = TOO_SLOW
        findings.append(
            "fastest credible path needs %.6f s against a %.6f s deadline"
            % (nominal, deadline)
        )
    elif degraded is None:
        verdict = SINGLE_PATH
        findings.append(
            "only one credible inhibit path; a single failure removes cessation"
        )
    elif not meets_deadline(degraded, deadline):
        verdict = TOO_SLOW
        findings.append(
            "after one failure cessation needs %.6f s against a %.6f s deadline"
            % (degraded, deadline)
        )
    else:
        verdict = COMPLIANT

    return {
        "deadline_s": deadline,
        "credible_path_count": len(times),
        "nominal_response_s": nominal,
        "degraded_response_s": degraded,
        "single_failure_tolerant": degraded is not None,
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
        "compliant": verdict == COMPLIANT,
    }
