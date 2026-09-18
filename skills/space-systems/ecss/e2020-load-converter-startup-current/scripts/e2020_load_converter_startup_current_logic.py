#!/usr/bin/env python3
"""Start-up current drawn by the converters inside a protected load.

Anchor: ECSS-E-ST-20-20C clause 5.3.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A load unit is fed through one protective switch of a declared class,
and that class comes with a current the load is not allowed to exceed.
Inside the unit sit one or more DC/DC converters. Each converter, when it
is energised, draws far more than its settled input current: it charges
its own input capacitance and it ramps its output up over a soft-start
window. The clause asks for a demonstration that the converters get
themselves started without the unit ever pulling more than the class
current, so the feeding switch never has to enter limitation at all.

Three figures per converter drive the demonstration:

    input_capacitance_f      the capacitance the converter presents to
                             the unit input while it is charging
    soft_start_ramp_s        the window over which it brings its output
                             up before it is regulating
    steady_input_current_a   what it draws once it is regulating
    start_delay_s            when the unit releases it, relative to the
                             instant the unit is powered

The aggregate is a TIMELINE question, not a sum. Converters released
together add their ramp currents; converters staggered so that one has
settled before the next is released do not. Summing every converter peak
over-states a staggered design and reports a finding that is not there;
taking the largest single peak under-states a simultaneous design and
misses the finding that is. The envelope below is built on one timeline
and read at its true maximum.

The current margin, the ramp loading fraction and the headroom advisory
floor are declared project policy rather than physical constants; the
defaults are a starting point a project substitutes its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import itertools
import math

CONVERTER_FIELDS = (
    "name",
    "input_capacitance_f",
    "soft_start_ramp_s",
    "steady_input_current_a",
    "start_delay_s",
)

VERDICT_WITHIN = "start-up-within-the-class-current"
VERDICT_EXCEEDS = "start-up-exceeds-the-class-current"

FINDING_AGGREGATE = "aggregate-start-up-peak-above-class-current"
FINDING_SETTLED = "settled-draw-above-class-current"
FINDING_SINGLE = "single-converter-peak-above-class-current"
FINDING_UNSTAGGERABLE = "no-release-order-fits-the-class-current"
FINDING_HEADROOM = "headroom-below-advisory-floor"

DEFAULT_STARTUP_POLICY = {
    "startup_current_margin": 1.20,
    "ramp_load_fraction": 1.0,
    "headroom_advisory_floor": 0.10,
}

# Placeholder converter set: the shape a unit's own converter list takes.
DEFAULT_CONVERTER_SET = (
    {
        "name": "core-3v3",
        "input_capacitance_f": 47.0e-6,
        "soft_start_ramp_s": 5.0e-3,
        "steady_input_current_a": 0.45,
        "start_delay_s": 0.0,
    },
    {
        "name": "payload-5v",
        "input_capacitance_f": 33.0e-6,
        "soft_start_ramp_s": 4.0e-3,
        "steady_input_current_a": 0.30,
        "start_delay_s": 10.0e-3,
    },
    {
        "name": "rf-12v",
        "input_capacitance_f": 22.0e-6,
        "soft_start_ramp_s": 6.0e-3,
        "steady_input_current_a": 0.25,
        "start_delay_s": 20.0e-3,
    },
)

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

    A ramp current is built by division and a margin by multiplication,
    so a case meant to sit exactly on the class current can land a few
    units in the last place above it. The limit is never widened; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_startup_policy(policy):
    """Check the current margin, ramp loading and advisory floor are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive(
        "startup_current_margin", policy.get("startup_current_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "startup_current_margin must be at least one, got %r" % (margin,)
        )
    fraction = _require_non_negative(
        "ramp_load_fraction", policy.get("ramp_load_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "ramp_load_fraction must not exceed one, got %r" % (fraction,)
        )
    floor = _require_non_negative(
        "headroom_advisory_floor", policy.get("headroom_advisory_floor")
    )
    if floor >= 1.0:
        raise ValueError(
            "headroom_advisory_floor must be below one, got %r" % (floor,)
        )
    return policy


def validate_converter(entry):
    """Check one converter row carries a usable start-up description."""
    if not isinstance(entry, dict):
        raise ValueError("converter entry must be a mapping, got %r" % (entry,))
    missing = [f for f in CONVERTER_FIELDS if f not in entry]
    if missing:
        raise ValueError(
            "converter entry is missing figures: %s" % ", ".join(sorted(missing))
        )
    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("converter name must be a non-empty string, got %r" % (name,))
    return {
        "name": name,
        "input_capacitance_f": _require_positive(
            "input_capacitance_f", entry["input_capacitance_f"]
        ),
        "soft_start_ramp_s": _require_positive(
            "soft_start_ramp_s", entry["soft_start_ramp_s"]
        ),
        "steady_input_current_a": _require_positive(
            "steady_input_current_a", entry["steady_input_current_a"]
        ),
        "start_delay_s": _require_non_negative(
            "start_delay_s", entry["start_delay_s"]
        ),
    }


def validate_converter_set(converters):
    """Normalise a converter list and require unique converter names."""
    if isinstance(converters, dict) or not hasattr(converters, "__iter__"):
        raise ValueError("converter set must be a sequence of entries")
    rows = [validate_converter(e) for e in converters]
    if not rows:
        raise ValueError("converter set is empty; there is no start-up to assess")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("converter set repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def converter_ramp_current_a(entry, bus_voltage_v, policy=DEFAULT_STARTUP_POLICY):
    """Input current one converter draws while it is soft-starting.

    Two contributions add: the constant current that charges the input
    capacitance over the ramp window, C*V/t, and the share of the settled
    input current the converter is already delivering during the ramp.
    """
    validate_startup_policy(policy)
    row = validate_converter(entry)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    charging = row["input_capacitance_f"] * voltage / row["soft_start_ramp_s"]
    loaded = row["steady_input_current_a"] * float(policy["ramp_load_fraction"])
    return charging + loaded


def converter_windows(converters, bus_voltage_v, policy=DEFAULT_STARTUP_POLICY):
    """Per-converter release window with the current drawn inside it."""
    rows = validate_converter_set(converters)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    windows = []
    for row in rows:
        windows.append(
            {
                "name": row["name"],
                "start_s": row["start_delay_s"],
                "settled_s": row["start_delay_s"] + row["soft_start_ramp_s"],
                "ramp_current_a": converter_ramp_current_a(row, voltage, policy),
                "steady_current_a": row["steady_input_current_a"],
            }
        )
    return tuple(windows)


def _close(a, b):
    return math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def startup_current_at_s(windows, time_s):
    """Unit input current at one instant of the start-up sequence.

    A converter contributes its ramp current from its release until it
    settles, and its settled current from then on. Before its release it
    contributes nothing. An instant sitting on a release or on a settling
    is taken at the later state, which is where the envelope steps.
    """
    instant = _require_non_negative("time_s", time_s)
    total = 0.0
    active = []
    for window in windows:
        released = instant > window["start_s"] or _close(instant, window["start_s"])
        if not released:
            continue
        settled = instant > window["settled_s"] or _close(
            instant, window["settled_s"]
        )
        if settled:
            total += window["steady_current_a"]
            active.append((window["name"], "settled"))
        else:
            total += window["ramp_current_a"]
            active.append((window["name"], "ramping"))
    return total, tuple(active)


def startup_current_profile(
    converters, bus_voltage_v, policy=DEFAULT_STARTUP_POLICY
):
    """Piecewise-constant unit input current over the start-up sequence.

    The envelope only changes where a converter is released or settles,
    so those instants are the whole profile.
    """
    windows = converter_windows(converters, bus_voltage_v, policy)
    instants = sorted({w["start_s"] for w in windows} | {w["settled_s"] for w in windows})
    profile = []
    for instant in instants:
        current, active = startup_current_at_s(windows, instant)
        profile.append(
            {"time_s": instant, "current_a": current, "active": active}
        )
    return tuple(profile)


def peak_startup_current_a(
    converters, bus_voltage_v, policy=DEFAULT_STARTUP_POLICY
):
    """Largest unit input current the release sequence ever produces."""
    profile = startup_current_profile(converters, bus_voltage_v, policy)
    peak = max(profile, key=lambda point: point["current_a"])
    return peak["current_a"], peak["time_s"]


def settled_current_a(converters):
    """Unit input current once every converter is regulating."""
    rows = validate_converter_set(converters)
    return sum(row["steady_input_current_a"] for row in rows)


EXACT_ORDER_LIMIT = 7


def staggered_release_peak_a(
    converters, bus_voltage_v, order, policy=DEFAULT_STARTUP_POLICY
):
    """Peak of a strictly one-at-a-time release in the order given.

    Each converter is released only once the previous one has settled, so
    while it ramps it sits on top of the settled draw of everything
    released before it and nothing else.
    """
    rows = {r["name"]: r for r in validate_converter_set(converters)}
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    if isinstance(order, (str, bytes)) or not hasattr(order, "__iter__"):
        raise ValueError("order must be a sequence of converter names")
    sequence = list(order)
    if sorted(sequence) != sorted(rows):
        raise ValueError(
            "order must name every converter exactly once, got %r" % (sequence,)
        )
    prefix = 0.0
    peak = 0.0
    for name in sequence:
        row = rows[name]
        moment = converter_ramp_current_a(row, voltage, policy) + prefix
        if moment > peak:
            peak = moment
        prefix += row["steady_input_current_a"]
    return peak


def minimum_achievable_peak(
    converters, bus_voltage_v, policy=DEFAULT_STARTUP_POLICY
):
    """Best peak any strictly staggered release order can reach.

    A unit whose aggregate peak is too high can sometimes be repaired by
    releasing its converters further apart. This is the floor that repair
    can reach: below it, the converter set itself has to change. Small
    sets are searched exactly; a set past EXACT_ORDER_LIMIT falls back to
    releasing the heaviest ramp first, which is reported as inexact so a
    reviewer knows the figure is an upper bound on the true floor.
    """
    rows = validate_converter_set(converters)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    names = [r["name"] for r in rows]
    if len(names) <= EXACT_ORDER_LIMIT:
        best_order = None
        best_peak = None
        for candidate in itertools.permutations(names):
            peak = staggered_release_peak_a(rows, voltage, candidate, policy)
            if best_peak is None or peak < best_peak:
                best_peak = peak
                best_order = candidate
        return {"peak_a": best_peak, "order": tuple(best_order), "exact": True}
    heaviest_first = tuple(
        sorted(
            names,
            key=lambda n: converter_ramp_current_a(
                next(r for r in rows if r["name"] == n), voltage, policy
            ),
            reverse=True,
        )
    )
    return {
        "peak_a": staggered_release_peak_a(rows, voltage, heaviest_first, policy),
        "order": heaviest_first,
        "exact": False,
    }


def class_startup_allowance_a(class_current_a, policy=DEFAULT_STARTUP_POLICY):
    """Current the unit may actually draw once the margin is taken out."""
    validate_startup_policy(policy)
    limit = _require_positive("class_current_a", class_current_a)
    return limit / float(policy["startup_current_margin"])


def assess_converter_startup(
    converters, bus_voltage_v, class_current_a, policy=DEFAULT_STARTUP_POLICY
):
    """Full clause 5.3.2.2.1 start-up demonstration with a verdict."""
    validate_startup_policy(policy)
    rows = validate_converter_set(converters)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    limit = _require_positive("class_current_a", class_current_a)
    allowance = class_startup_allowance_a(limit, policy)

    peak, peak_time = peak_startup_current_a(rows, voltage, policy)
    settled = settled_current_a(rows)
    stagger = minimum_achievable_peak(rows, voltage, policy)
    floor = stagger["peak_a"]

    findings = []
    advisories = []

    if not _at_most(settled, allowance):
        findings.append(
            "%s: settled draw %.4f A is above the allowed %.4f A, so the unit "
            "never leaves limitation" % (FINDING_SETTLED, settled, allowance)
        )

    worst_single = None
    for row in rows:
        single = converter_ramp_current_a(row, voltage, policy)
        if worst_single is None or single > worst_single[1]:
            worst_single = (row["name"], single)
        if not _at_most(single, allowance):
            findings.append(
                "%s: converter %s alone draws %.4f A against the allowed %.4f A"
                % (FINDING_SINGLE, row["name"], single, allowance)
            )

    if not _at_most(peak, allowance):
        findings.append(
            "%s: aggregate peak %.4f A at t=%.6f s is above the allowed %.4f A"
            % (FINDING_AGGREGATE, peak, peak_time, allowance)
        )
        if not _at_most(floor, allowance):
            findings.append(
                "%s: even a fully staggered release peaks at %.4f A against "
                "the allowed %.4f A" % (FINDING_UNSTAGGERABLE, floor, allowance)
            )

    headroom = (allowance - peak) / allowance
    if not findings and headroom < float(policy["headroom_advisory_floor"]):
        advisories.append(
            "%s: start-up headroom %.3f leaves little room for growth"
            % (FINDING_HEADROOM, headroom)
        )

    return {
        "verdict": VERDICT_WITHIN if not findings else VERDICT_EXCEEDS,
        "class_current_a": limit,
        "allowance_a": allowance,
        "peak_current_a": peak,
        "peak_time_s": peak_time,
        "settled_current_a": settled,
        "staggered_floor_a": floor,
        "staggered_floor_order": stagger["order"],
        "staggered_floor_exact": stagger["exact"],
        "worst_single_converter": worst_single[0],
        "worst_single_current_a": worst_single[1],
        "headroom": headroom,
        "restagger_would_help": (
            not _at_most(peak, allowance) and _at_most(floor, allowance)
        ),
        "profile": startup_current_profile(rows, voltage, policy),
        "findings": findings,
        "advisories": advisories,
    }
