#!/usr/bin/env python3
"""Deciding whether a limiter switch stuck in the on state is paid for by
the spacecraft power budget, in the case where nothing else can open the
channel.

Anchor: ECSS-E-ST-20-20C clause 5.2.13.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

When a limiter switch fails on and the channel carries no further
switching element, the load cannot be shed. Whatever it draws it keeps
drawing, and the only place that can absorb it is the power budget:

    provision    what the channel has downstream or upstream of the stuck
                 switch decides the question. An isolation switch or a
                 load switch can still open the channel, so the failure
                 costs nothing in the budget. A redundant limiter branch
                 is a second path into the same load, not a way out of
                 it, so it sheds nothing
    increment    the channel's nominal draw is already in the budget. The
                 cost of the failure is what the stuck channel adds on
                 top of that, and where the stuck draw is below the
                 nominal one it adds nothing rather than a credit
    worst case   the clause is answered against a single failure, so the
                 charge is the largest increment among the channels that
                 cannot be shed, not the sum of all of them

A channel with no declared stuck-on current is not a channel that costs
nothing; it is the channel nobody sized, and it outranks a budget that
came out short, because the two need different work.

The margin requirement and the number of simultaneous stuck channels
below are a declared policy, not physical constants: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NO_ADDITIONAL_SWITCHING = "no-additional-switching"
UPSTREAM_ISOLATION_SWITCH = "upstream-isolation-switch"
DOWNSTREAM_LOAD_SWITCH = "downstream-load-switch"
REDUNDANT_LIMITER_BRANCH = "redundant-limiter-branch"

SWITCHING_PROVISIONS = (
    NO_ADDITIONAL_SWITCHING,
    UPSTREAM_ISOLATION_SWITCH,
    DOWNSTREAM_LOAD_SWITCH,
    REDUNDANT_LIMITER_BRANCH,
)

PROVISION_SHEDS_LOAD = {
    NO_ADDITIONAL_SWITCHING: False,
    UPSTREAM_ISOLATION_SWITCH: True,
    DOWNSTREAM_LOAD_SWITCH: True,
    REDUNDANT_LIMITER_BRANCH: False,
}

BUDGET_NOT_ASSESSED = "stuck-on-channel-not-assessed"
BUDGET_EXCEEDED = "stuck-on-power-exceeds-available"
BUDGET_MARGIN_SHORTFALL = "stuck-on-power-margin-shortfall"
BUDGET_COVERED = "stuck-on-power-within-budget"

BUDGET_VERDICTS = (
    BUDGET_NOT_ASSESSED,
    BUDGET_EXCEEDED,
    BUDGET_MARGIN_SHORTFALL,
    BUDGET_COVERED,
)

DEFAULT_BUDGET_POLICY = {
    "required_margin_fraction": 0.10,
    "simultaneous_stuck_channels": 1,
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


def _require_count(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_budget_policy(policy):
    """Check a budget policy before any stuck channel is priced."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_non_negative(
        "required_margin_fraction", policy.get("required_margin_fraction")
    )
    if margin >= 1.0:
        raise ValueError(
            "required_margin_fraction %g leaves no power for the load it is "
            "meant to protect" % (margin,)
        )
    _require_count(
        "simultaneous_stuck_channels",
        policy.get("simultaneous_stuck_channels"),
        1,
    )
    return policy


def categorize_switching_provision(provision):
    """Name what else can open the channel, refusing anything unrecognised."""
    name = _require_identifier("switching provision", provision)
    if name not in SWITCHING_PROVISIONS:
        raise ValueError(
            "unrecognised switching provision %r; known provisions are %s"
            % (name, ", ".join(SWITCHING_PROVISIONS))
        )
    return name


def provision_sheds_load(provision):
    """Whether that provision can actually remove the stuck-on load."""
    return PROVISION_SHEDS_LOAD[categorize_switching_provision(provision)]


def stuck_on_power_w(bus_voltage_v, stuck_on_current_a):
    """Continuous power a channel draws once its switch is stuck closed."""
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_non_negative("stuck_on_current_a", stuck_on_current_a)
    return voltage * current


def stuck_on_increment_w(stuck_power_w, nominal_power_w):
    """What the failure adds on top of the draw already in the budget."""
    stuck = _require_non_negative("stuck_power_w", stuck_power_w)
    nominal = _require_non_negative("nominal_power_w", nominal_power_w)
    return max(0.0, stuck - nominal)


def normalize_channel(channel, bus_voltage_v):
    """Read one limiter channel into the fields the budget question needs."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    identifier = _require_identifier("channel id", channel.get("id"))
    provision = categorize_switching_provision(channel.get("switching_provision"))
    nominal = _require_non_negative(
        "nominal_power_w", channel.get("nominal_power_w", 0.0)
    )
    raw_current = channel.get("stuck_on_current_a")
    if raw_current is None:
        stuck_power = None
        increment = None
        assessed = False
    else:
        stuck_power = stuck_on_power_w(bus_voltage_v, raw_current)
        increment = stuck_on_increment_w(stuck_power, nominal)
        assessed = True
    return {
        "id": identifier,
        "switching_provision": provision,
        "sheds_load": provision_sheds_load(provision),
        "nominal_power_w": nominal,
        "stuck_on_power_w": stuck_power,
        "stuck_on_increment_w": increment,
        "assessed": assessed,
    }


def normalize_channels(channels, bus_voltage_v):
    """Read every channel, refusing an empty or self-contradicting set."""
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("channels must be a non-empty sequence, got %r" % (channels,))
    normalized = [normalize_channel(channel, bus_voltage_v) for channel in channels]
    identifiers = [channel["id"] for channel in normalized]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("a channel id was declared twice: %r" % (identifiers,))
    return normalized


def channels_needing_budget(channels):
    """The channels whose stuck-on load nothing can shed."""
    if not isinstance(channels, (list, tuple)):
        raise ValueError("channels must be a sequence, got %r" % (channels,))
    needing = []
    for channel in channels:
        if not isinstance(channel, dict) or "sheds_load" not in channel:
            raise ValueError("channel must be normalized first, got %r" % (channel,))
        if not channel["sheds_load"]:
            needing.append(channel)
    return needing


def worst_case_increment_w(channels, simultaneous=1):
    """The charge the budget carries: the largest increments that can occur."""
    count = _require_count("simultaneous_stuck_channels", simultaneous, 1)
    if not isinstance(channels, (list, tuple)):
        raise ValueError("channels must be a sequence, got %r" % (channels,))
    increments = []
    for channel in channels:
        if not isinstance(channel, dict):
            raise ValueError("channel must be a mapping, got %r" % (channel,))
        increment = channel.get("stuck_on_increment_w")
        if increment is None:
            continue
        increments.append(
            _require_non_negative("stuck_on_increment_w", increment)
        )
    increments.sort(reverse=True)
    return sum(increments[:count])


def budget_margin_fraction(available_power_w, demand_power_w):
    """Share of the available power still unspent once the demand is met."""
    available = _require_positive("available_power_w", available_power_w)
    demand = _require_non_negative("demand_power_w", demand_power_w)
    return (available - demand) / available


def assess_switch_failure_budget(system, policy=DEFAULT_BUDGET_POLICY):
    """Full clause 5.2.13.1.1 judgement of one spacecraft's stuck-on case."""
    validate_budget_policy(policy)
    if not isinstance(system, dict):
        raise ValueError("system must be a mapping, got %r" % (system,))

    bus_voltage = _require_positive("bus_voltage_v", system.get("bus_voltage_v"))
    available = _require_positive(
        "available_power_w", system.get("available_power_w")
    )
    nominal_demand = _require_non_negative(
        "nominal_demand_w", system.get("nominal_demand_w")
    )
    channels = normalize_channels(system.get("channels"), bus_voltage)

    needing = channels_needing_budget(channels)
    unassessed = [
        channel["id"] for channel in needing if not channel["assessed"]
    ]
    shed = [channel["id"] for channel in channels if channel["sheds_load"]]

    simultaneous = int(policy["simultaneous_stuck_channels"])
    charge = worst_case_increment_w(needing, simultaneous)
    demand = nominal_demand + charge
    margin = budget_margin_fraction(available, demand)
    required = float(policy["required_margin_fraction"])
    margin_sufficient = _at_least(margin, required)
    within_available = _at_least(available, demand)

    charged = sorted(
        (channel for channel in needing if channel["assessed"]),
        key=lambda channel: (-channel["stuck_on_increment_w"], channel["id"]),
    )[:simultaneous]

    findings = []
    for identifier in unassessed:
        findings.append(
            "%s cannot shed a stuck-on load and has no declared stuck-on "
            "current, so it is a channel nobody sized rather than a channel "
            "that costs nothing" % (identifier,)
        )
    if not within_available:
        findings.append(
            "the worst stuck-on channel adds %.4f W to a %.4f W demand "
            "against %.4f W available, so the failure is not paid for"
            % (charge, nominal_demand, available)
        )
    elif not margin_sufficient:
        findings.append(
            "covering the stuck-on channel leaves %.4f of the available "
            "power unspent against a %.4f requirement, so the failure is "
            "paid for out of the margin" % (margin, required)
        )
    for channel in charged:
        findings.append(
            "%s is charged %.4f W: %.4f W stuck on against %.4f W already "
            "budgeted"
            % (
                channel["id"],
                channel["stuck_on_increment_w"],
                channel["stuck_on_power_w"],
                channel["nominal_power_w"],
            )
        )

    result = {
        "channels": channels,
        "channels_needing_budget": [channel["id"] for channel in needing],
        "sheddable_channels": shed,
        "unassessed_channels": unassessed,
        "charged_channels": [channel["id"] for channel in charged],
        "worst_case_increment_w": charge,
        "demand_power_w": demand,
        "margin_fraction": margin,
        "findings": findings,
    }

    if unassessed:
        result["verdict"] = BUDGET_NOT_ASSESSED
    elif not within_available:
        result["verdict"] = BUDGET_EXCEEDED
    elif not margin_sufficient:
        result["verdict"] = BUDGET_MARGIN_SHORTFALL
    else:
        result["verdict"] = BUDGET_COVERED
    return result
