#!/usr/bin/env python3
"""Deciding whether a latching or high power limiter honours the
recommended power-up state -- output off -- and, when it does not,
whether the departure was argued or merely declared.

Anchor: ECSS-E-ST-20-20C clause 5.2.7.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause recommends rather than mandates: a latching current limiter
and a high power limiter come up with the output off. A recommendation
has two conforming answers and one non-answer, and separating them is
most of the work:

    output off       the recommendation is met. Nothing further is owed
                     beyond showing the enable really is a positive
                     command and not a default that happens to be off
    output on, with
    an argument      a departure the project has taken deliberately: a
                     recorded rationale, an assessed criticality, and
                     compensating provisions that stand in for the state
                     the recommendation would have given
    output on, with
    nothing          the recommendation was not followed and not argued
                     either, which is the case the clause exists to make
                     visible

Coming up conducting is not free even when it is justified. Every
channel that defaults on charges the source at the same instant, so the
aggregate inrush of the defaulting set is compared against what the
source can actually deliver into a cold start. A departure that is
beautifully argued and still browns the bus out is a departure that
fails on arithmetic rather than on paperwork.

The margins, floors and criticality bands below are a declared policy,
not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LATCHING_CURRENT_LIMITER = "latching-current-limiter"
HIGH_POWER_LIMITER = "high-power-limiter"

GOVERNED_LIMITER_TYPES = (LATCHING_CURRENT_LIMITER, HIGH_POWER_LIMITER)

RETRIGGERABLE_LIMITER = "retriggerable-current-limiter"
FOLDBACK_LIMITER = "foldback-limiter"

OUT_OF_SCOPE_LIMITER_TYPES = (RETRIGGERABLE_LIMITER, FOLDBACK_LIMITER)

OUTPUT_OFF = "output-off"
OUTPUT_ON = "output-on"
OUTPUT_INDETERMINATE = "output-indeterminate"

DECLARED_OUTPUT_STATES = (OUTPUT_OFF, OUTPUT_ON, OUTPUT_INDETERMINATE)

CRITICALITY_MINOR = "minor"
CRITICALITY_MAJOR = "major"
CRITICALITY_CATASTROPHIC = "catastrophic"

CRITICALITY_BANDS = (
    CRITICALITY_MINOR,
    CRITICALITY_MAJOR,
    CRITICALITY_CATASTROPHIC,
)

CHANNEL_RECOMMENDATION_MET = "power-up-recommendation-met"
CHANNEL_ENABLE_NOT_POSITIVE = "power-up-enable-not-positive"
CHANNEL_DEPARTURE_JUSTIFIED = "power-up-departure-justified"
CHANNEL_DEPARTURE_UNJUSTIFIED = "power-up-departure-unjustified"
CHANNEL_STATE_UNDECLARED = "power-up-state-undeclared"

CHANNEL_STANDINGS = (
    CHANNEL_RECOMMENDATION_MET,
    CHANNEL_ENABLE_NOT_POSITIVE,
    CHANNEL_DEPARTURE_JUSTIFIED,
    CHANNEL_DEPARTURE_UNJUSTIFIED,
    CHANNEL_STATE_UNDECLARED,
)

_STANDING_SEVERITY = {
    CHANNEL_STATE_UNDECLARED: 4,
    CHANNEL_DEPARTURE_UNJUSTIFIED: 3,
    CHANNEL_ENABLE_NOT_POSITIVE: 2,
    CHANNEL_DEPARTURE_JUSTIFIED: 1,
    CHANNEL_RECOMMENDATION_MET: 0,
}

BUS_NOT_EVALUATED = "lcl-power-up-not-evaluated"
BUS_INRUSH_EXCEEDED = "lcl-power-up-inrush-exceeded"
BUS_DEPARTURES_UNJUSTIFIED = "lcl-power-up-departures-unjustified"
BUS_DEPARTURES_JUSTIFIED = "lcl-power-up-departures-justified"
BUS_RECOMMENDATION_MET = "lcl-power-up-recommendation-met"

BUS_VERDICTS = (
    BUS_NOT_EVALUATED,
    BUS_INRUSH_EXCEEDED,
    BUS_DEPARTURES_UNJUSTIFIED,
    BUS_DEPARTURES_JUSTIFIED,
    BUS_RECOMMENDATION_MET,
)

DEFAULT_LCL_POWER_UP_POLICY = {
    "inrush_margin_fraction": 0.20,
    "justified_criticality_ceiling": CRITICALITY_MAJOR,
    "min_compensating_provisions": 2,
    "require_positive_enable": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_unit_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number < 1.0:
        raise ValueError(
            "%s must be at least zero and below one, got %r" % (name, value)
        )
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_lcl_power_up_policy(policy):
    """Check a power-up policy is usable before any channel is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_unit_fraction(
        "inrush_margin_fraction", policy.get("inrush_margin_fraction")
    )
    ceiling = policy.get("justified_criticality_ceiling")
    if ceiling not in CRITICALITY_BANDS:
        raise ValueError(
            "justified_criticality_ceiling %r is not a known band; known "
            "bands are %s" % (ceiling, ", ".join(CRITICALITY_BANDS))
        )
    _require_count(
        "min_compensating_provisions",
        policy.get("min_compensating_provisions"),
    )
    if not isinstance(policy.get("require_positive_enable"), bool):
        raise ValueError(
            "require_positive_enable must be a boolean, got %r"
            % (policy.get("require_positive_enable"),)
        )
    return policy


def categorize_limiter_type(kind):
    """Name a limiter type and say whether this clause governs it."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("limiter type must be a non-empty string, got %r" % (kind,))
    name = kind.strip()
    if name in GOVERNED_LIMITER_TYPES:
        return name
    if name in OUT_OF_SCOPE_LIMITER_TYPES:
        raise ValueError(
            "%r is not governed by this recommendation; a retriggerable or "
            "foldback limiter has its own power-up state" % (name,)
        )
    raise ValueError(
        "unrecognised limiter type %r; governed types are %s"
        % (name, ", ".join(GOVERNED_LIMITER_TYPES))
    )


def criticality_rank(band):
    """Order a criticality band so one ceiling can be compared to another."""
    if band not in CRITICALITY_BANDS:
        raise ValueError(
            "unrecognised criticality band %r; known bands are %s"
            % (band, ", ".join(CRITICALITY_BANDS))
        )
    return CRITICALITY_BANDS.index(band)


def departure_is_argued(channel, policy=DEFAULT_LCL_POWER_UP_POLICY):
    """Whether a come-up-conducting departure carries a real argument."""
    validate_lcl_power_up_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    gaps = []

    rationale = channel.get("rationale")
    if not isinstance(rationale, str) or len(rationale.strip()) < 12:
        gaps.append("no recorded rationale for coming up conducting")

    band = channel.get("criticality")
    if band is None:
        gaps.append("the criticality of coming up conducting was never assessed")
    else:
        rank = criticality_rank(band)
        ceiling = criticality_rank(policy["justified_criticality_ceiling"])
        if rank > ceiling:
            gaps.append(
                "the assessed criticality %r sits above the %r ceiling a "
                "departure may be argued at"
                % (band, policy["justified_criticality_ceiling"])
            )

    provisions = channel.get("compensating_provisions", ())
    if not isinstance(provisions, (list, tuple)):
        raise ValueError(
            "compensating_provisions must be a sequence, got %r" % (provisions,)
        )
    named = [p for p in provisions if isinstance(p, str) and p.strip()]
    if len(named) != len(provisions):
        raise ValueError(
            "every compensating provision must be a non-empty string, got %r"
            % (provisions,)
        )
    if len(set(named)) != len(named):
        raise ValueError(
            "a compensating provision was named twice: %r" % (provisions,)
        )
    required = int(policy["min_compensating_provisions"])
    if len(named) < required:
        gaps.append(
            "%d compensating provision(s) named against the %d a departure "
            "needs" % (len(named), required)
        )

    return {"argued": not gaps, "gaps": gaps, "provisions": tuple(named)}


def assess_channel_power_up(channel, policy=DEFAULT_LCL_POWER_UP_POLICY):
    """Judge one latching or high power limiter channel's power-up state."""
    validate_lcl_power_up_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))

    identifier = channel.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("channel is missing a non-empty id, got %r" % (identifier,))
    limiter_type = categorize_limiter_type(channel.get("limiter_type"))

    state = channel.get("power_up_state")
    if state not in DECLARED_OUTPUT_STATES:
        raise ValueError(
            "unrecognised power_up_state %r on channel %r; known states are %s"
            % (state, identifier, ", ".join(DECLARED_OUTPUT_STATES))
        )

    inrush = _require_non_negative(
        "inrush_peak_a", channel.get("inrush_peak_a", 0.0)
    )
    record = {
        "id": identifier.strip(),
        "limiter_type": limiter_type,
        "power_up_state": state,
        "inrush_peak_a": inrush,
        "defaults_on": state == OUTPUT_ON,
        "gaps": [],
        "provisions": (),
    }

    if state == OUTPUT_INDETERMINATE:
        record["standing"] = CHANNEL_STATE_UNDECLARED
        record["gaps"] = [
            "the power-up state is left indeterminate, so the channel has no "
            "state to grade rather than a wrong one"
        ]
        return record

    if state == OUTPUT_OFF:
        if policy["require_positive_enable"] and not bool(
            channel.get("positive_enable_command", False)
        ):
            record["standing"] = CHANNEL_ENABLE_NOT_POSITIVE
            record["gaps"] = [
                "the output is off at power-up but no positive enable command "
                "was declared, so the off state is an accident of the design "
                "rather than a commanded one"
            ]
        else:
            record["standing"] = CHANNEL_RECOMMENDATION_MET
        return record

    argument = departure_is_argued(channel, policy)
    record["gaps"] = list(argument["gaps"])
    record["provisions"] = argument["provisions"]
    record["standing"] = (
        CHANNEL_DEPARTURE_JUSTIFIED
        if argument["argued"]
        else CHANNEL_DEPARTURE_UNJUSTIFIED
    )
    return record


def aggregate_default_on_inrush(records):
    """Peak the source is asked for by every channel that defaults on."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    total = 0.0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        if record.get("defaults_on"):
            total += _require_non_negative(
                "inrush_peak_a", record.get("inrush_peak_a")
            )
    return total


def usable_source_inrush_a(source_inrush_capability_a, margin_fraction):
    """Source inrush capability after the declared margin is held back."""
    capability = _require_positive(
        "source_inrush_capability_a", source_inrush_capability_a
    )
    margin = _require_unit_fraction("margin_fraction", margin_fraction)
    return capability * (1.0 - margin)


def assess_lcl_power_up(design, policy=DEFAULT_LCL_POWER_UP_POLICY):
    """Full clause 5.2.7.2.1 judgement of a set of limiter channels."""
    validate_lcl_power_up_policy(policy)
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))

    channels = design.get("channels")
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("design is missing a non-empty channels sequence")

    records = [assess_channel_power_up(channel, policy) for channel in channels]
    identifiers = [record["id"] for record in records]
    duplicates = sorted(
        {name for name in identifiers if identifiers.count(name) > 1}
    )
    if duplicates:
        raise ValueError(
            "channel declared twice: %s" % (", ".join(duplicates),)
        )

    grouped = {standing: [] for standing in CHANNEL_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])

    demanded = aggregate_default_on_inrush(records)
    usable = usable_source_inrush_a(
        design.get("source_inrush_capability_a"),
        float(policy["inrush_margin_fraction"]),
    )
    inrush_fits = _at_most(demanded, usable)

    findings = []
    for record in records:
        for gap in record["gaps"]:
            findings.append("%s: %s" % (record["id"], gap))
    if not inrush_fits:
        findings.append(
            "the channels that default on ask the source for %.4f A against "
            "the %.4f A usable after margin, so a simultaneous power-up "
            "browns the bus out however well the departure is argued"
            % (demanded, usable)
        )

    result = {
        "channels": records,
        "standings": grouped,
        "default_on_inrush_a": demanded,
        "usable_source_inrush_a": usable,
        "inrush_fits": inrush_fits,
        "findings": findings,
    }

    if grouped[CHANNEL_STATE_UNDECLARED]:
        result["verdict"] = BUS_NOT_EVALUATED
    elif not inrush_fits:
        result["verdict"] = BUS_INRUSH_EXCEEDED
    elif grouped[CHANNEL_DEPARTURE_UNJUSTIFIED] or grouped[
        CHANNEL_ENABLE_NOT_POSITIVE
    ]:
        result["verdict"] = BUS_DEPARTURES_UNJUSTIFIED
    elif grouped[CHANNEL_DEPARTURE_JUSTIFIED]:
        result["verdict"] = BUS_DEPARTURES_JUSTIFIED
    else:
        result["verdict"] = BUS_RECOMMENDATION_MET
    return result


def worst_standing(records):
    """The standing a set of channels is reported at: the worst one present."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict) or record.get("standing") not in (
            _STANDING_SEVERITY
        ):
            raise ValueError("record carries no known standing: %r" % (record,))
        if worst is None or (
            _STANDING_SEVERITY[record["standing"]] > _STANDING_SEVERITY[worst]
        ):
            worst = record["standing"]
    return worst
