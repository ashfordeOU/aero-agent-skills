#!/usr/bin/env python3
"""Getting back to conducting after a switch-off nobody asked for.

Anchor: ECSS-E-ST-20-20C clause 5.2.18.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable limiter that trips on a disturbance rather than on a real
load fault is expected to put itself back into the conducting state. The
whole point of the retrigger function is that nobody has to be in the
loop: the limiter cycles, the disturbance passes, conduction resumes.

Three things decide whether that promise is real, and each of them is a
way a design ends up meeting the clause on paper only.

Recovery has to be the limiter's own. A return to conduction that waits
on a ground telecommand, an onboard reconfiguration or an operator
procedure is not this function at all -- it is a latching limiter with a
recovery procedure attached, and the load is off for as long as the
procedure takes.

Recovery has to be bounded in time, and the bound has to be compared
with something. A limiter that resumes conduction eventually is not
useful to a load whose hold-up runs out first: the load has already
dropped, the unit downstream has already reset, and the fact that power
came back afterwards is a separate story. The latency is built from the
declared timing -- how long the limiter takes to recognise the overload,
how long it stays open between attempts, how many attempts the
disturbance forces, and how long the output takes to ramp back up.

Recovery has to survive the disturbance, not just outlast one cycle. A
disturbance lasting longer than one off interval forces another retrigger
cycle, and a limiter with a finite retrigger budget can run out of
attempts before the disturbance passes. Counting the cycles is what turns
a qualitative "it retriggers" into a number a reviewer can check.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECOVERY_NOT_AUTONOMOUS = "rlcl-recovery-not-autonomous"
RETRIGGER_BUDGET_EXHAUSTED = "rlcl-retrigger-budget-exhausted"
RECOVERY_SLOWER_THAN_HOLD_UP = "rlcl-recovery-slower-than-load-hold-up"
SPURIOUS_TRIP_RECOVERY_DEMONSTRATED = "rlcl-spurious-trip-recovery-demonstrated"

UNLIMITED_ATTEMPTS = None

DEFAULT_RECOVERY_POLICY = {
    "require_autonomous_recovery": True,
    "min_hold_up_margin": 1.5,
    "thin_margin_advisory": 2.0,
    "attempt_headroom_advisory": 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _tolerant_ceil(value):
    """math.ceil that does not round a representation error up a whole step.

    A duration divided by an interval it is an exact multiple of can land a
    hair above the integer on one platform and a hair below it on another.
    Rounding that hair up costs a whole retrigger cycle, so the nearest
    integer wins whenever the quotient is indistinguishable from it.
    """
    if not _is_finite_number(value):
        raise ValueError("cycle quotient must be a finite number, got %r" % (value,))
    nearest = math.floor(value + 0.5)
    if math.isclose(value, nearest, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return int(nearest)
    return int(math.ceil(value))


def validate_recovery_policy(policy):
    """Check the declared recovery policy can be assessed against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag(
        "require_autonomous_recovery", policy.get("require_autonomous_recovery")
    )
    minimum = _require_positive("min_hold_up_margin", policy.get("min_hold_up_margin"))
    if minimum < 1.0:
        raise ValueError(
            "min_hold_up_margin below one asks the load to drop before power "
            "returns and still calls it recovery, got %r" % (minimum,)
        )
    thin = _require_positive("thin_margin_advisory", policy.get("thin_margin_advisory"))
    if thin < minimum:
        raise ValueError(
            "thin_margin_advisory %r sits below min_hold_up_margin %r, so the "
            "advisory could never fire on a passing case" % (thin, minimum)
        )
    headroom = _require_count(
        "attempt_headroom_advisory", policy.get("attempt_headroom_advisory")
    )
    if headroom < 1:
        raise ValueError(
            "attempt_headroom_advisory must be at least one; an advisory that "
            "fires on zero spare attempts says nothing"
        )
    return policy


def validate_limiter_record(limiter):
    """Read one retriggerable limiter and the timing of its retrigger cycle."""
    if not isinstance(limiter, dict):
        raise ValueError("limiter must be a mapping, got %r" % (limiter,))
    identifier = _require_label("limiter id", limiter.get("id"))
    if not identifier:
        raise ValueError("limiter id must not be blank")
    retrigger_enabled = _require_flag(
        "retrigger_enabled on %s" % identifier, limiter.get("retrigger_enabled")
    )
    autonomous = _require_flag(
        "autonomous_retrigger on %s" % identifier,
        limiter.get("autonomous_retrigger"),
    )
    detection = _require_positive(
        "trip_detection_s on %s" % identifier, limiter.get("trip_detection_s")
    )
    off_interval = _require_positive(
        "off_interval_s on %s" % identifier, limiter.get("off_interval_s")
    )
    ramp = _require_non_negative(
        "turn_on_ramp_s on %s" % identifier, limiter.get("turn_on_ramp_s")
    )
    attempts = limiter.get("retrigger_attempts", UNLIMITED_ATTEMPTS)
    if attempts is not UNLIMITED_ATTEMPTS:
        attempts = _require_count("retrigger_attempts on %s" % identifier, attempts)
        if attempts < 1:
            raise ValueError(
                "retrigger_attempts on %s is zero, which is a latching limiter "
                "rather than a retriggerable one" % identifier
            )
    return {
        "id": identifier,
        "retrigger_enabled": retrigger_enabled,
        "autonomous_retrigger": autonomous,
        "trip_detection_s": detection,
        "off_interval_s": off_interval,
        "turn_on_ramp_s": ramp,
        "retrigger_attempts": attempts,
    }


def validate_load_record(load):
    """Read the load and how long it survives with its input open."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    identifier = _require_label("load id", load.get("id"))
    if not identifier:
        raise ValueError("load id must not be blank")
    hold_up = _require_positive(
        "hold_up_s on %s" % identifier, load.get("hold_up_s")
    )
    return {"id": identifier, "hold_up_s": hold_up}


def validate_disturbance(disturbance):
    """Read one disturbance the limiter is expected to ride through."""
    if not isinstance(disturbance, dict):
        raise ValueError("disturbance must be a mapping, got %r" % (disturbance,))
    name = _require_label("disturbance name", disturbance.get("name"))
    if not name:
        raise ValueError("disturbance name must not be blank")
    duration = _require_non_negative(
        "duration_s on %s" % name, disturbance.get("duration_s")
    )
    return {"name": name, "duration_s": duration}


def disturbance_records(disturbances):
    """Read every disturbance on the table, in record order."""
    if not isinstance(disturbances, (list, tuple)) or not disturbances:
        raise ValueError(
            "disturbances must be a non-empty sequence; recovery cannot be "
            "timed against an event nobody described"
        )
    records = []
    seen = set()
    for disturbance in disturbances:
        record = validate_disturbance(disturbance)
        if record["name"] in seen:
            raise ValueError("duplicate disturbance %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    return tuple(records)


def retrigger_cycle_period(limiter):
    """One recognise-and-wait cycle: detection plus the open interval."""
    record = validate_limiter_record(limiter)
    return record["trip_detection_s"] + record["off_interval_s"]


def retrigger_cycles_required(limiter, duration_s):
    """How many retrigger cycles a disturbance of this length forces.

    A disturbance still present when the limiter retries trips it again, so
    the count is the disturbance measured in whole cycles -- never fewer
    than the one cycle the trip itself costs.
    """
    period = retrigger_cycle_period(limiter)
    duration = _require_non_negative("disturbance duration", duration_s)
    return max(1, _tolerant_ceil(duration / period))


def recovery_latency(limiter, duration_s):
    """Seconds from the unintended trip to conduction restored."""
    record = validate_limiter_record(limiter)
    cycles = retrigger_cycles_required(record, duration_s)
    return cycles * retrigger_cycle_period(record) + record["turn_on_ramp_s"]


def hold_up_margin(load, latency_s):
    """How much of the load's hold-up the recovery leaves unused."""
    record = validate_load_record(load)
    latency = _require_positive("recovery latency", latency_s)
    return record["hold_up_s"] / latency


def recovery_is_autonomous(limiter):
    """True only when the limiter returns to conducting with nobody helping."""
    record = validate_limiter_record(limiter)
    return record["retrigger_enabled"] and record["autonomous_retrigger"]


def attempts_remaining(limiter, cycles):
    """Spare retrigger attempts after the worst disturbance, or None."""
    record = validate_limiter_record(limiter)
    used = _require_count("cycles", cycles)
    if record["retrigger_attempts"] is UNLIMITED_ATTEMPTS:
        return None
    return record["retrigger_attempts"] - used


def worst_disturbance(limiter, disturbances):
    """The disturbance costing the longest recovery, ties broken by name."""
    records = disturbance_records(disturbances)
    scored = [
        (recovery_latency(limiter, record["duration_s"]), record["name"], record)
        for record in records
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2], scored[0][0]


def recovery_advisories(limiter, load, disturbances, policy=DEFAULT_RECOVERY_POLICY):
    """Things worth saying about a chain that already meets the clause."""
    validate_recovery_policy(policy)
    record = validate_limiter_record(limiter)
    advisories = []
    worst, latency = worst_disturbance(record, disturbances)
    margin = hold_up_margin(load, latency)
    cycles = retrigger_cycles_required(record, worst["duration_s"])
    if _at_least(margin, policy["min_hold_up_margin"]) and not _at_least(
        margin, policy["thin_margin_advisory"]
    ):
        advisories.append(
            "recovery from %s leaves a hold-up margin of %.3f, above the "
            "declared minimum but below the point at which timing growth "
            "during development would stay harmless" % (worst["name"], margin)
        )
    if record["retrigger_attempts"] is UNLIMITED_ATTEMPTS:
        advisories.append(
            "limiter %s declares an unlimited retrigger budget; that is a "
            "property of the design record rather than a tested bound and is "
            "worth confirming against the qualification evidence" % record["id"]
        )
    else:
        spare = record["retrigger_attempts"] - cycles
        if spare >= 0 and spare < int(policy["attempt_headroom_advisory"]):
            advisories.append(
                "limiter %s has %d retrigger attempts left after riding out "
                "%s; a disturbance only slightly longer exhausts the budget"
                % (record["id"], spare, worst["name"])
            )
    if record["turn_on_ramp_s"] <= 0.0:
        advisories.append(
            "limiter %s declares a zero turn-on ramp; an instantaneous "
            "restoration is a modelling convenience and understates the "
            "latency the load actually sees" % record["id"]
        )
    return tuple(advisories)


def assess_spurious_switch_off_recovery(case, policy=DEFAULT_RECOVERY_POLICY):
    """Full clause 5.2.18.1.1 verdict for one limiter and its load."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_recovery_policy(policy)

    findings = []
    advisories = []
    result = {
        "limiter_id": None,
        "load_id": None,
        "worst_disturbance": None,
        "retrigger_cycles": None,
        "recovery_latency_s": None,
        "hold_up_margin": None,
        "attempts_remaining": None,
        "findings": findings,
        "advisories": advisories,
    }

    limiter = validate_limiter_record(case.get("limiter"))
    load = validate_load_record(case.get("load"))
    records = disturbance_records(case.get("disturbances"))
    result["limiter_id"] = limiter["id"]
    result["load_id"] = load["id"]

    if policy["require_autonomous_recovery"] and not recovery_is_autonomous(limiter):
        if not limiter["retrigger_enabled"]:
            findings.append(
                "limiter %s has retrigger switched off, so an unintended trip "
                "leaves load %s open until somebody acts"
                % (limiter["id"], load["id"])
            )
        else:
            findings.append(
                "limiter %s returns to conducting only on an external command, "
                "so load %s is off for the length of a procedure rather than "
                "the length of a retrigger cycle" % (limiter["id"], load["id"])
            )
        result["verdict"] = RECOVERY_NOT_AUTONOMOUS
        return result

    worst, latency = worst_disturbance(limiter, records)
    cycles = retrigger_cycles_required(limiter, worst["duration_s"])
    result["worst_disturbance"] = worst["name"]
    result["retrigger_cycles"] = cycles
    result["recovery_latency_s"] = latency
    result["hold_up_margin"] = hold_up_margin(load, latency)
    result["attempts_remaining"] = attempts_remaining(limiter, cycles)

    if limiter["retrigger_attempts"] is not UNLIMITED_ATTEMPTS and cycles > limiter[
        "retrigger_attempts"
    ]:
        findings.append(
            "%s forces %d retrigger cycles on limiter %s, which allows %d; the "
            "limiter stops trying while the disturbance is still there and "
            "load %s stays off"
            % (
                worst["name"],
                cycles,
                limiter["id"],
                limiter["retrigger_attempts"],
                load["id"],
            )
        )
        result["verdict"] = RETRIGGER_BUDGET_EXHAUSTED
        return result

    advisories.extend(recovery_advisories(limiter, load, records, policy))

    if not _at_least(result["hold_up_margin"], policy["min_hold_up_margin"]):
        findings.append(
            "recovery from %s takes %.6f s against a hold-up of %.6f s on load "
            "%s, a margin of %.3f below the declared %.3f; power returns after "
            "the load has already dropped"
            % (
                worst["name"],
                latency,
                load["hold_up_s"],
                load["id"],
                result["hold_up_margin"],
                policy["min_hold_up_margin"],
            )
        )
        result["verdict"] = RECOVERY_SLOWER_THAN_HOLD_UP
        return result

    result["verdict"] = SPURIOUS_TRIP_RECOVERY_DEMONSTRATED
    return result
