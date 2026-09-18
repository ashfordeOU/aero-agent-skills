#!/usr/bin/env python3
"""Input undervoltage protection on every limiter's bus interface.

Anchor: ECSS-E-ST-20C clause 5.2.5.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The provision is stated over the whole population: each limiter carries
an input undervoltage protection function on the interface where it meets
the bus. The word that does the work is "each". A design where most
limiters carry the function and two do not has not met the clause, and
the two that do not are exactly the ones that will keep drawing their
full load while the bus is collapsing.

So the first half of the assessment is an inventory question, and it is
answered by counting, not by sampling. A limiter with no declared
function is a finding whatever the rest of the design looks like.

The second half is harder, because a protection that exists can still be
placed where it does nothing or where it does harm. Four placements go
wrong, and each has a different symptom.

A threshold set too high sits inside the voltage band the bus legitimately
occupies. The function then trips on normal operation, and a protection
that sheds load during a healthy day is worse than none: it turns a bus
excursion into a mission event. So the threshold has to sit a declared
margin below the lowest steady-state voltage the bus is specified to
hold.

A threshold set too low sits under the limiter's own minimum operating
input. The limiter has already left its specified behaviour by the time
the protection notices anything, so the function protects nothing that
was still working. The threshold has to sit above that floor.

A recovery level above the bus minimum latches the unit out. Recovery is
the threshold plus the hysteresis, and if that sum lands above the lowest
voltage the bus holds, the limiter switches off during a dip and never
sees a voltage high enough to come back -- a permanent loss from a
transient cause.

A hysteresis too narrow chatters. With no meaningful separation between
trip and recovery, ripple and source impedance alone will cycle the
function, so a floor on the hysteresis is part of the provision rather
than an implementation detail.

Finally the response time. If a bus dip the design is expected to survive
reaches below the threshold, the protection must be slow enough to let it
pass. A function that reacts inside the survivable dip converts a
transient the bus was built to absorb into a shed load.

The margins below are declared project policy, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROTECTION_ABSENT = "input-undervoltage-protection-absent"
THRESHOLD_INSIDE_STEADY_STATE_BAND = "threshold-inside-bus-steady-state-band"
THRESHOLD_BELOW_OPERATING_FLOOR = "threshold-below-limiter-operating-floor"
RECOVERY_ABOVE_BUS_MINIMUM = "recovery-level-above-bus-minimum"
HYSTERESIS_BELOW_CHATTER_FLOOR = "hysteresis-below-chatter-floor"
RESPONSE_INSIDE_SURVIVABLE_DIP = "response-time-inside-survivable-dip"

BUS_ENVELOPE_NOT_ESTABLISHED = "bus-envelope-not-established"
PROVISION_POLICY_NOT_ESTABLISHED = "provision-policy-not-established"
UNDERVOLTAGE_PROTECTION_MISSING = "undervoltage-protection-missing-on-a-limiter"
UNDERVOLTAGE_PROTECTION_MISPLACED = "undervoltage-protection-present-but-misplaced"
ALL_LIMITERS_PROTECTED = "all-limiters-carry-a-placed-undervoltage-protection"

DEFAULT_PROVISION_POLICY = {
    "policy_reference": "project power bus protection policy",
    "min_nuisance_margin_fraction": 0.05,
    "min_hysteresis_fraction": 0.02,
    "dip_ride_through_margin": 0.50,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_provision_policy(policy):
    """Check the placement margins are present and inside their sensible range."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    reference = _require_label("policy_reference", policy.get("policy_reference"))
    nuisance = _require_non_negative(
        "min_nuisance_margin_fraction", policy.get("min_nuisance_margin_fraction")
    )
    if nuisance >= 1.0:
        raise ValueError(
            "min_nuisance_margin_fraction %g leaves no admissible threshold at "
            "all" % nuisance
        )
    hysteresis = _require_non_negative(
        "min_hysteresis_fraction", policy.get("min_hysteresis_fraction")
    )
    if hysteresis >= 1.0:
        raise ValueError(
            "min_hysteresis_fraction %g would demand a recovery level at twice "
            "the trip threshold" % hysteresis
        )
    ride_through = _require_non_negative(
        "dip_ride_through_margin", policy.get("dip_ride_through_margin")
    )
    return {
        "policy_reference": reference,
        "min_nuisance_margin_fraction": nuisance,
        "min_hysteresis_fraction": hysteresis,
        "dip_ride_through_margin": ride_through,
    }


def validate_bus_envelope(bus):
    """Read the bus voltages and the dip the design is expected to survive."""
    if not isinstance(bus, dict):
        raise ValueError("bus envelope must be a mapping, got %r" % (bus,))
    minimum = _require_positive(
        "min_steady_state_v", bus.get("min_steady_state_v")
    )
    maximum = _require_positive(
        "max_steady_state_v", bus.get("max_steady_state_v")
    )
    if not _at_least(maximum, minimum):
        raise ValueError(
            "the bus maximum %g V is below its minimum %g V" % (maximum, minimum)
        )
    dip = _require_positive(
        "survivable_dip_floor_v", bus.get("survivable_dip_floor_v")
    )
    if not dip < minimum:
        raise ValueError(
            "the survivable dip floor %g V is not below the steady-state "
            "minimum %g V, so it is not a dip" % (dip, minimum)
        )
    duration = _require_positive(
        "survivable_dip_duration_ms", bus.get("survivable_dip_duration_ms")
    )
    return {
        "min_steady_state_v": minimum,
        "max_steady_state_v": maximum,
        "survivable_dip_floor_v": dip,
        "survivable_dip_duration_ms": duration,
    }


def validate_limiter_record(limiter):
    """Read one limiter and whatever undervoltage function it declares."""
    if not isinstance(limiter, dict):
        raise ValueError("limiter must be a mapping, got %r" % (limiter,))
    identifier = _require_label("limiter id", limiter.get("id"))
    if not identifier:
        raise ValueError("limiter id must not be blank")
    present = limiter.get("undervoltage_protection_present")
    if not isinstance(present, bool):
        raise ValueError(
            "undervoltage_protection_present on %s must be true or false, got "
            "%r" % (identifier, present)
        )
    floor = _require_positive(
        "min_operating_input_v on %s" % identifier,
        limiter.get("min_operating_input_v"),
    )
    record = {
        "id": identifier,
        "undervoltage_protection_present": present,
        "min_operating_input_v": floor,
        "trip_threshold_v": None,
        "hysteresis_v": None,
        "response_time_ms": None,
    }
    if not present:
        return record
    record["trip_threshold_v"] = _require_positive(
        "trip_threshold_v on %s" % identifier, limiter.get("trip_threshold_v")
    )
    record["hysteresis_v"] = _require_non_negative(
        "hysteresis_v on %s" % identifier, limiter.get("hysteresis_v")
    )
    record["response_time_ms"] = _require_positive(
        "response_time_ms on %s" % identifier, limiter.get("response_time_ms")
    )
    return record


def admissible_threshold_window(limiter, bus, policy=DEFAULT_PROVISION_POLICY):
    """The band a trip threshold has to sit inside to be worth anything."""
    record = validate_limiter_record(limiter)
    envelope = validate_bus_envelope(bus)
    rules = validate_provision_policy(policy)
    ceiling = envelope["min_steady_state_v"] * (
        1.0 - rules["min_nuisance_margin_fraction"]
    )
    floor = record["min_operating_input_v"]
    if not floor < ceiling:
        raise ValueError(
            "limiter %s has an operating floor of %g V and an admissible "
            "ceiling of %g V, leaving no threshold that both protects and "
            "avoids nuisance trips" % (record["id"], floor, ceiling)
        )
    return {"floor_v": floor, "ceiling_v": ceiling}


def recovery_level_v(limiter):
    """Voltage the bus has to reach again before the limiter re-arms."""
    record = validate_limiter_record(limiter)
    if not record["undervoltage_protection_present"]:
        raise ValueError(
            "limiter %s declares no undervoltage function, so it has no "
            "recovery level" % record["id"]
        )
    return record["trip_threshold_v"] + record["hysteresis_v"]


def required_response_time_ms(limiter, bus, policy=DEFAULT_PROVISION_POLICY):
    """Delay the function needs so a survivable dip is not treated as a fault.

    Returns None when the dip floor never reaches the threshold, because
    then the function is not exercised by the dip at all.
    """
    record = validate_limiter_record(limiter)
    envelope = validate_bus_envelope(bus)
    rules = validate_provision_policy(policy)
    if not record["undervoltage_protection_present"]:
        raise ValueError(
            "limiter %s declares no undervoltage function, so no response time "
            "is required of it" % record["id"]
        )
    if _at_least(envelope["survivable_dip_floor_v"], record["trip_threshold_v"]):
        return None
    return envelope["survivable_dip_duration_ms"] * (
        1.0 + rules["dip_ride_through_margin"]
    )


def limiter_provision_verdict(limiter, bus, policy=DEFAULT_PROVISION_POLICY):
    """Judge one limiter: is the function there, and is it placed usefully."""
    record = validate_limiter_record(limiter)
    envelope = validate_bus_envelope(bus)
    rules = validate_provision_policy(policy)

    verdict = {
        "id": record["id"],
        "undervoltage_protection_present": record["undervoltage_protection_present"],
        "trip_threshold_v": record["trip_threshold_v"],
        "recovery_level_v": None,
        "required_response_time_ms": None,
        "threshold_window": None,
        "threshold_headroom_fraction": None,
        "shortfalls": (PROTECTION_ABSENT,),
        "compliant": False,
    }
    if not record["undervoltage_protection_present"]:
        return verdict

    window = admissible_threshold_window(limiter, bus, policy)
    verdict["threshold_window"] = window
    threshold = record["trip_threshold_v"]
    verdict["threshold_headroom_fraction"] = (
        window["ceiling_v"] - threshold
    ) / window["ceiling_v"]
    recovery = recovery_level_v(limiter)
    verdict["recovery_level_v"] = recovery

    shortfalls = []
    if not _at_most(threshold, window["ceiling_v"]):
        shortfalls.append(THRESHOLD_INSIDE_STEADY_STATE_BAND)
    if not _at_least(threshold, window["floor_v"]):
        shortfalls.append(THRESHOLD_BELOW_OPERATING_FLOOR)
    if not _at_most(recovery, envelope["min_steady_state_v"]):
        shortfalls.append(RECOVERY_ABOVE_BUS_MINIMUM)
    if not _at_least(
        record["hysteresis_v"], threshold * rules["min_hysteresis_fraction"]
    ):
        shortfalls.append(HYSTERESIS_BELOW_CHATTER_FLOOR)

    required = required_response_time_ms(limiter, bus, policy)
    verdict["required_response_time_ms"] = required
    if required is not None and not _at_least(record["response_time_ms"], required):
        shortfalls.append(RESPONSE_INSIDE_SURVIVABLE_DIP)

    verdict["shortfalls"] = tuple(shortfalls)
    verdict["compliant"] = not shortfalls
    return verdict


def limiter_verdicts(limiters, bus, policy=DEFAULT_PROVISION_POLICY):
    """Judge every limiter on the bus, in record order."""
    if not isinstance(limiters, (list, tuple)):
        raise ValueError("limiters must be a sequence of limiter records")
    if not limiters:
        raise ValueError(
            "no limiter is declared on this bus, so the provision cannot be "
            "shown to hold over a population that is empty"
        )
    verdicts = []
    seen = set()
    for limiter in limiters:
        verdict = limiter_provision_verdict(limiter, bus, policy)
        if verdict["id"] in seen:
            raise ValueError("duplicate limiter id %r" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def provision_coverage_fraction(verdicts):
    """Share of the declared limiters that carry the function at all."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    carried = sum(
        1 for verdict in verdicts if verdict["undervoltage_protection_present"]
    )
    return carried / len(verdicts)


def weakest_placement(verdicts):
    """The protected limiter whose threshold sits closest to the bus band."""
    placed = [
        verdict
        for verdict in verdicts
        if verdict["threshold_headroom_fraction"] is not None
    ]
    if not placed:
        raise ValueError("no limiter declares a placed undervoltage threshold")
    return min(placed, key=lambda verdict: verdict["threshold_headroom_fraction"])


def assess_undervoltage_protection_provision(case, policy=DEFAULT_PROVISION_POLICY):
    """Full clause 5.2.5.1.1 provision decision for one power bus."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "policy_reference": None,
        "limiter_verdicts": (),
        "provision_coverage_fraction": None,
        "unprotected_limiters": (),
        "weakest_placement_id": None,
        "weakest_threshold_headroom_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    bus = case.get("bus_envelope")
    if bus is None:
        findings.append(
            "no bus envelope is declared, so no threshold can be shown to sit "
            "below the operating band or above the limiter floor"
        )
        result["verdict"] = BUS_ENVELOPE_NOT_ESTABLISHED
        return result

    rules = validate_provision_policy(policy)
    result["policy_reference"] = rules["policy_reference"]
    if not rules["policy_reference"]:
        findings.append(
            "the placement margins carry no policy reference; margins with no "
            "policy behind them are not a provision requirement"
        )
        result["verdict"] = PROVISION_POLICY_NOT_ESTABLISHED
        return result

    envelope = validate_bus_envelope(bus)
    verdicts = limiter_verdicts(case.get("limiters"), bus, policy)
    result["limiter_verdicts"] = verdicts
    result["provision_coverage_fraction"] = provision_coverage_fraction(verdicts)
    result["unprotected_limiters"] = tuple(
        verdict["id"]
        for verdict in verdicts
        if not verdict["undervoltage_protection_present"]
    )

    if result["unprotected_limiters"]:
        for identifier in result["unprotected_limiters"]:
            findings.append(
                "limiter %s declares no input undervoltage protection on its "
                "bus interface; the provision is stated over every limiter, so "
                "one omission fails it" % identifier
            )
        result["verdict"] = UNDERVOLTAGE_PROTECTION_MISSING
        return result

    weakest = weakest_placement(verdicts)
    result["weakest_placement_id"] = weakest["id"]
    result["weakest_threshold_headroom_fraction"] = weakest[
        "threshold_headroom_fraction"
    ]

    for verdict in verdicts:
        if verdict["required_response_time_ms"] is None:
            advisories.append(
                "limiter %s trips at %.4g V, above the %.4g V survivable dip "
                "floor, so the dip never exercises its protection"
                % (
                    verdict["id"],
                    verdict["trip_threshold_v"],
                    envelope["survivable_dip_floor_v"],
                )
            )
        if verdict["compliant"]:
            continue
        findings.append(
            "limiter %s carries the function but places it badly: %s"
            % (verdict["id"], " and ".join(verdict["shortfalls"]))
        )

    if findings:
        result["verdict"] = UNDERVOLTAGE_PROTECTION_MISPLACED
        return result

    result["verdict"] = ALL_LIMITERS_PROTECTED
    return result
