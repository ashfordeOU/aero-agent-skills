#!/usr/bin/env python3
"""Detonation distribution boxes and explosive delay elements.

Anchor: ECSS-E-ST-33-11C clauses 4.11.9 and 4.11.10. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

A distribution box takes one detonation input and divides it across
several output branches. It has no gain: the donor energy is split, then
reduced again by the loss of the transfer interface each branch uses, and
the branch that sizes the box is the weakest one.

Transfer media, lowest loss to highest
    detonating-cord            a continuous run, the cheapest crossing
    explosive-transfer-line    a confined line with an end fitting
    through-bulkhead-initiator a sealed wall crossing, the costliest

An explosive delay element is a burning column, so its output time moves
with unit-to-unit tolerance and with temperature. Both widen the window
before it is compared with the event the delay has to hit, and ordering
inside a delay train is a question about window edges, not nominal times.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TRANSFER_MEDIA = (
    "detonating-cord",
    "explosive-transfer-line",
    "through-bulkhead-initiator",
)

MARGIN_MET = "transfer-margin-met"
MARGIN_NOT_MET = "transfer-margin-not-met"
SPREAD_MET = "simultaneity-met"
SPREAD_NOT_MET = "simultaneity-not-met"
ORDER_MET = "delay-train-ordered"
ORDER_NOT_MET = "delay-train-overlapped"

DEFAULT_DISTRIBUTION_POLICY = {
    "min_transfer_margin": 2.0,
    "transfer_loss_fraction": {
        "detonating-cord": 0.10,
        "explosive-transfer-line": 0.20,
        "through-bulkhead-initiator": 0.35,
    },
    "max_simultaneity_spread_ms": 1.0,
    "min_event_separation_ms": 5.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


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


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value >= 1.0:
        raise ValueError("%s must be below one, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_branch_count(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("branch_count must be a whole number, got %r" % (value,))
    if value < 1:
        raise ValueError("branch_count must be at least one, got %r" % (value,))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Branch energies and window edges are sums of products, so a case that
    sits exactly on a limit can land a few units in the last place below
    it. The limit is never lowered; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit with the same representation-error tolerance."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_distribution_policy(policy):
    """Check a distribution policy covers every medium with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_transfer_margin", policy.get("min_transfer_margin"))
    _require_positive(
        "max_simultaneity_spread_ms", policy.get("max_simultaneity_spread_ms")
    )
    _require_non_negative(
        "min_event_separation_ms", policy.get("min_event_separation_ms")
    )
    table = policy.get("transfer_loss_fraction")
    if not isinstance(table, dict):
        raise ValueError("policy transfer_loss_fraction must be a mapping")
    missing = set(TRANSFER_MEDIA) - set(table)
    if missing:
        raise ValueError(
            "policy transfer_loss_fraction is missing entries: %s"
            % ", ".join(sorted(missing))
        )
    for medium in TRANSFER_MEDIA:
        _require_fraction("transfer_loss_fraction[%s]" % medium, table[medium])
    return policy


def branch_delivered_energy_j(
    input_energy_j, branch_count, medium, policy=DEFAULT_DISTRIBUTION_POLICY
):
    """Energy one branch acceptor sees after the split and the interface loss."""
    validate_distribution_policy(policy)
    energy = _require_positive("input_energy_j", input_energy_j)
    count = _require_branch_count(branch_count)
    _require_choice("medium", medium, TRANSFER_MEDIA)
    loss = policy["transfer_loss_fraction"][medium]
    return (energy / count) * (1.0 - loss)


def branch_transfer_margin(delivered_energy_j, threshold_energy_j):
    """Ratio of delivered branch energy to the acceptor initiation threshold."""
    delivered = _require_positive("delivered_energy_j", delivered_energy_j)
    threshold = _require_positive("threshold_energy_j", threshold_energy_j)
    return delivered / threshold


def simultaneity_spread_ms(function_times_ms):
    """Earliest-to-latest spread of the branch function times."""
    if not isinstance(function_times_ms, (list, tuple)):
        raise ValueError(
            "function_times_ms must be a list or tuple, got %r" % (function_times_ms,)
        )
    if len(function_times_ms) < 2:
        raise ValueError("a spread needs at least two branch function times")
    values = [
        _require_non_negative("function_time_ms", t) for t in function_times_ms
    ]
    return max(values) - min(values)


def delay_window_ms(
    nominal_delay_ms,
    unit_tolerance_ms,
    temperature_coefficient_per_k=0.0,
    temperature_excursion_k=0.0,
):
    """Earliest and latest output time of one delay element.

    The unit tolerance and the temperature drift both widen the window,
    and the drift is a fraction of the nominal delay, so it grows with
    the longest delays in a train.
    """
    nominal = _require_positive("nominal_delay_ms", nominal_delay_ms)
    tolerance = _require_non_negative("unit_tolerance_ms", unit_tolerance_ms)
    coefficient = _require_non_negative(
        "temperature_coefficient_per_k", temperature_coefficient_per_k
    )
    excursion = _require_non_negative(
        "temperature_excursion_k", temperature_excursion_k
    )
    drift = nominal * coefficient * excursion
    half_width = tolerance + drift
    earliest = nominal - half_width
    if earliest <= 0.0:
        raise ValueError(
            "the stacked window of a %g ms delay collapses to %g ms; the "
            "element cannot be sequenced" % (nominal, earliest)
        )
    return {
        "nominal_ms": nominal,
        "earliest_ms": earliest,
        "latest_ms": nominal + half_width,
        "half_width_ms": half_width,
        "drift_ms": drift,
    }


def assess_delay_train(events, policy=DEFAULT_DISTRIBUTION_POLICY):
    """Open every delay window and check the worst-case corners stay ordered."""
    validate_distribution_policy(policy)
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events must be a non-empty list of delay elements")
    windows = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("event %d must be a mapping, got %r" % (index, event))
        identifier = event.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("event %d needs a non-empty string id" % index)
        window = delay_window_ms(
            event.get("nominal_delay_ms"),
            event.get("unit_tolerance_ms", 0.0),
            event.get("temperature_coefficient_per_k", 0.0),
            event.get("temperature_excursion_k", 0.0),
        )
        window["id"] = identifier
        windows.append(window)
    ordered = sorted(windows, key=lambda w: w["nominal_ms"])
    separation = policy["min_event_separation_ms"]
    overlaps = []
    for earlier, later in zip(ordered, ordered[1:]):
        gap = later["earliest_ms"] - earlier["latest_ms"]
        if not _at_least(gap, separation):
            overlaps.append(
                {
                    "earlier_id": earlier["id"],
                    "later_id": later["id"],
                    "gap_ms": gap,
                    "required_gap_ms": separation,
                }
            )
    return {
        "windows": ordered,
        "overlaps": overlaps,
        "verdict": ORDER_MET if not overlaps else ORDER_NOT_MET,
    }


def assess_distribution_box(case, policy=DEFAULT_DISTRIBUTION_POLICY):
    """Apportion the input across the branches and grade the weakest one."""
    validate_distribution_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    branches = case.get("branches")
    if not isinstance(branches, (list, tuple)) or not branches:
        raise ValueError("case needs a non-empty branches list")
    count = _require_branch_count(len(branches))
    input_energy = _require_positive("input_energy_j", case.get("input_energy_j"))
    required = policy["min_transfer_margin"]
    graded = []
    findings = []
    for index, branch in enumerate(branches):
        if not isinstance(branch, dict):
            raise ValueError("branch %d must be a mapping, got %r" % (index, branch))
        identifier = branch.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("branch %d needs a non-empty string id" % index)
        medium = _require_choice("medium", branch.get("medium"), TRANSFER_MEDIA)
        delivered = branch_delivered_energy_j(input_energy, count, medium, policy)
        threshold = _require_positive(
            "threshold_energy_j", branch.get("threshold_energy_j")
        )
        margin = branch_transfer_margin(delivered, threshold)
        met = _at_least(margin, required)
        if not met:
            findings.append(
                "branch %s transfers %.4f J against a %.4f J threshold, a margin "
                "of %.3f below the required %.3f"
                % (identifier, delivered, threshold, margin, required)
            )
        graded.append(
            {
                "id": identifier,
                "medium": medium,
                "delivered_energy_j": delivered,
                "threshold_energy_j": threshold,
                "transfer_margin": margin,
                "margin_met": met,
            }
        )
    weakest = min(graded, key=lambda b: b["transfer_margin"])
    return {
        "branch_count": count,
        "branches": graded,
        "weakest_branch_id": weakest["id"],
        "weakest_transfer_margin": weakest["transfer_margin"],
        "required_transfer_margin": required,
        "verdict": MARGIN_MET if not findings else MARGIN_NOT_MET,
        "findings": findings,
    }


def plan_distribution_and_delays(case, policy=DEFAULT_DISTRIBUTION_POLICY):
    """Full clause 4.11.9 and 4.11.10 assessment with a combined verdict."""
    box = assess_distribution_box(case, policy)
    findings = list(box["findings"])
    result = {
        "box": box,
        "simultaneity_spread_ms": None,
        "simultaneity_verdict": "simultaneity-not-evaluated",
        "delay_train": None,
        "delay_verdict": "delay-train-not-evaluated",
        "findings": findings,
    }
    times = case.get("branch_function_times_ms")
    if times is not None:
        spread = simultaneity_spread_ms(times)
        allowance = policy["max_simultaneity_spread_ms"]
        met = _at_most(spread, allowance)
        result["simultaneity_spread_ms"] = spread
        result["simultaneity_verdict"] = SPREAD_MET if met else SPREAD_NOT_MET
        if not met:
            findings.append(
                "branch function times spread %.4f ms against a %.4f ms allowance"
                % (spread, allowance)
            )
    else:
        findings.append(
            "no branch function times supplied; the simultaneity of the box is "
            "not yet demonstrated"
        )
    events = case.get("delay_elements")
    if events:
        train = assess_delay_train(events, policy)
        result["delay_train"] = train
        result["delay_verdict"] = train["verdict"]
        for overlap in train["overlaps"]:
            findings.append(
                "delay %s closes %.4f ms before %s opens, against a required "
                "%.4f ms separation"
                % (
                    overlap["earlier_id"],
                    overlap["gap_ms"],
                    overlap["later_id"],
                    overlap["required_gap_ms"],
                )
            )
    compliant = (
        box["verdict"] == MARGIN_MET
        and result["simultaneity_verdict"] == SPREAD_MET
        and result["delay_verdict"] in (ORDER_MET, "delay-train-not-evaluated")
    )
    result["compliant"] = compliant
    result["verdict"] = "distribution-acceptable" if compliant else "distribution-rework"
    return result
