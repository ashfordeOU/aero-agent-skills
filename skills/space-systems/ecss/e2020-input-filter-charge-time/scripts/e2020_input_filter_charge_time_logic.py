#!/usr/bin/env python3
"""Input filter charge time of a protected load during limitation.

Anchor: ECSS-E-ST-20-20C clause 5.3.2.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A load unit presents a filter at its input: one or more capacitive
stages that the bus has to charge before the unit can run. Energising
that filter is a limitation event by construction. The protective switch
feeding the unit holds its output to a limiting current while the filter
charges, and it only tolerates that for a bounded charging window before
it opens. The clause asks for a demonstration that the filter is fully
charged before the window runs out.

Three things decide the answer, and two of them are routinely dropped:

    total capacitance    every stage the bus sees in parallel, not the
                         first stage alone
    net charging current the HELD limiting current minus whatever the
                         unit itself draws while it is charging; only
                         the remainder reaches the capacitance
    the window           the bounded time the protection allows before
                         it opens, taken at its SHORTEST declared value

While the switch is limiting, its output is a current source, so the
capacitance charges linearly and the time is C*V/I on the NET current.
A unit whose own draw during charging equals or exceeds the held
limiting current never charges at all: the bus voltage collapses onto
the load and the window expires. That case is reported, not divided by.

The stage weighting, the charge margin and the utilisation advisory
floor are declared project policy rather than physical constants; the
defaults are a starting point a project substitutes its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STAGE_FIELDS = ("name", "capacitance_f")

CONDITION_FIELDS = (
    "bus_voltage_v",
    "held_limiting_current_a",
    "load_draw_during_charge_a",
    "charging_window_s",
)

VERDICT_CHARGED = "filter-charges-inside-the-window"
VERDICT_NOT_CHARGED = "filter-does-not-charge-inside-the-window"
VERDICT_NO_CHARGING = "no-net-charging-current-reaches-the-filter"

FINDING_WINDOW = "charge-time-exceeds-the-charging-window"
FINDING_NO_CURRENT = "load-draw-leaves-no-net-charging-current"
FINDING_UTILISATION = "window-utilisation-above-advisory-ceiling"

# Placeholder filter: the shape a unit's own stage list takes.
DEFAULT_FILTER_STAGES = (
    {"name": "common-mode-stage", "capacitance_f": 10.0e-6},
    {"name": "differential-stage", "capacitance_f": 47.0e-6},
    {"name": "bulk-hold-up", "capacitance_f": 150.0e-6},
)

DEFAULT_CONDITIONS = {
    "bus_voltage_v": 28.0,
    "held_limiting_current_a": 2.40,
    "load_draw_during_charge_a": 0.15,
    "charging_window_s": 8.0e-3,
}

DEFAULT_CHARGE_POLICY = {
    "charge_time_margin": 1.25,
    "utilisation_advisory_ceiling": 0.90,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A charge time is built by division and a margin by multiplication, so
    a case meant to sit exactly on the window can land a few units in the
    last place above it. The window is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_charge_policy(policy):
    """Check the charge margin and the advisory ceiling are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive("charge_time_margin", policy.get("charge_time_margin"))
    if margin < 1.0:
        raise ValueError("charge_time_margin must be at least one, got %r" % (margin,))
    ceiling = _require_positive(
        "utilisation_advisory_ceiling", policy.get("utilisation_advisory_ceiling")
    )
    if ceiling > 1.0:
        raise ValueError(
            "utilisation_advisory_ceiling must not exceed one, got %r" % (ceiling,)
        )
    return policy


def validate_filter_stage(stage):
    """Check one filter stage carries a usable capacitance."""
    if not isinstance(stage, dict):
        raise ValueError("filter stage must be a mapping, got %r" % (stage,))
    missing = [f for f in STAGE_FIELDS if f not in stage]
    if missing:
        raise ValueError(
            "filter stage is missing figures: %s" % ", ".join(sorted(missing))
        )
    name = stage["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("stage name must be a non-empty string, got %r" % (name,))
    return {
        "name": name,
        "capacitance_f": _require_positive("capacitance_f", stage["capacitance_f"]),
    }


def validate_filter(stages):
    """Normalise a stage list and require unique stage names."""
    if isinstance(stages, dict) or not hasattr(stages, "__iter__"):
        raise ValueError("filter must be a sequence of stages")
    rows = [validate_filter_stage(s) for s in stages]
    if not rows:
        raise ValueError("filter has no stages; there is nothing to charge")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("filter repeats the stage name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def validate_conditions(conditions):
    """Check the charging conditions carry every figure the check needs."""
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping, got %r" % (conditions,))
    missing = [f for f in CONDITION_FIELDS if f not in conditions]
    if missing:
        raise ValueError(
            "conditions are missing figures: %s" % ", ".join(sorted(missing))
        )
    return {
        "bus_voltage_v": _require_positive(
            "bus_voltage_v", conditions["bus_voltage_v"]
        ),
        "held_limiting_current_a": _require_positive(
            "held_limiting_current_a", conditions["held_limiting_current_a"]
        ),
        "load_draw_during_charge_a": _require_non_negative(
            "load_draw_during_charge_a", conditions["load_draw_during_charge_a"]
        ),
        "charging_window_s": _require_positive(
            "charging_window_s", conditions["charging_window_s"]
        ),
    }


def total_filter_capacitance_f(stages):
    """Capacitance the bus actually sees: every stage, in parallel."""
    rows = validate_filter(stages)
    return sum(row["capacitance_f"] for row in rows)


def net_charging_current_a(held_limiting_current_a, load_draw_during_charge_a):
    """Share of the held limiting current that reaches the capacitance.

    The unit draws its own current while the filter is charging, and only
    the remainder charges the capacitance. The result may be zero or
    negative; that is a reportable condition, not an error, so the caller
    decides what to do with it.
    """
    held = _require_positive("held_limiting_current_a", held_limiting_current_a)
    drawn = _require_non_negative(
        "load_draw_during_charge_a", load_draw_during_charge_a
    )
    return held - drawn


def filter_charge_time_s(capacitance_f, bus_voltage_v, charging_current_a):
    """Time to charge the filter at a held current: t = C*V/I."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_positive("charging_current_a", charging_current_a)
    return capacitance * voltage / current


def largest_supportable_capacitance_f(conditions, policy=DEFAULT_CHARGE_POLICY):
    """Biggest total filter the window would still carry, in farads.

    Inverting the charge time at the margin answers the design question
    directly: a unit over this figure has to shed capacitance, slow its
    own draw during charging, or be fed by a higher class.
    """
    validate_charge_policy(policy)
    case = validate_conditions(conditions)
    net = net_charging_current_a(
        case["held_limiting_current_a"], case["load_draw_during_charge_a"]
    )
    if net <= 0.0:
        return 0.0
    margin = float(policy["charge_time_margin"])
    return case["charging_window_s"] * net / (case["bus_voltage_v"] * margin)


def window_utilisation(charge_time_s, charging_window_s):
    """Share of the allowed window the charge actually consumes."""
    time_taken = _require_positive("charge_time_s", charge_time_s)
    window = _require_positive("charging_window_s", charging_window_s)
    return time_taken / window


def assess_filter_charge(stages, conditions, policy=DEFAULT_CHARGE_POLICY):
    """Full clause 5.3.2.3.1 charging demonstration with a verdict."""
    validate_charge_policy(policy)
    rows = validate_filter(stages)
    case = validate_conditions(conditions)

    total_c = sum(row["capacitance_f"] for row in rows)
    net = net_charging_current_a(
        case["held_limiting_current_a"], case["load_draw_during_charge_a"]
    )

    if net <= 0.0 or math.isclose(net, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return {
            "verdict": VERDICT_NO_CHARGING,
            "total_capacitance_f": total_c,
            "net_charging_current_a": net,
            "charge_time_s": None,
            "required_time_s": None,
            "charging_window_s": case["charging_window_s"],
            "window_slack_s": None,
            "window_utilisation": None,
            "largest_supportable_capacitance_f": 0.0,
            "stage_shares": _stage_shares(rows, total_c),
            "findings": [
                "%s: the unit draws %.4f A of a held %.4f A, leaving %.4f A to "
                "charge the filter"
                % (
                    FINDING_NO_CURRENT,
                    case["load_draw_during_charge_a"],
                    case["held_limiting_current_a"],
                    net,
                )
            ],
            "advisories": [],
        }

    charge_time = filter_charge_time_s(total_c, case["bus_voltage_v"], net)
    margin = float(policy["charge_time_margin"])
    required = charge_time * margin
    fits = _at_most(required, case["charging_window_s"])
    utilisation = required / case["charging_window_s"]

    findings = []
    advisories = []
    if not fits:
        findings.append(
            "%s: charging %.4g F to %.4g V at a net %.4f A needs %.6f s with "
            "margin, against a window of %.6f s"
            % (
                FINDING_WINDOW,
                total_c,
                case["bus_voltage_v"],
                net,
                required,
                case["charging_window_s"],
            )
        )
    elif utilisation > float(policy["utilisation_advisory_ceiling"]):
        advisories.append(
            "%s: the charge consumes %.3f of the window, leaving little room "
            "for capacitance growth" % (FINDING_UTILISATION, utilisation)
        )

    return {
        "verdict": VERDICT_CHARGED if fits else VERDICT_NOT_CHARGED,
        "total_capacitance_f": total_c,
        "net_charging_current_a": net,
        "charge_time_s": charge_time,
        "required_time_s": required,
        "charging_window_s": case["charging_window_s"],
        "window_slack_s": case["charging_window_s"] - required,
        "window_utilisation": utilisation,
        "largest_supportable_capacitance_f": largest_supportable_capacitance_f(
            case, policy
        ),
        "stage_shares": _stage_shares(rows, total_c),
        "findings": findings,
        "advisories": advisories,
    }


def _stage_shares(rows, total_c):
    """Share of the total capacitance each stage contributes."""
    return tuple(
        {
            "name": row["name"],
            "capacitance_f": row["capacitance_f"],
            "share": row["capacitance_f"] / total_c,
        }
        for row in rows
    )
