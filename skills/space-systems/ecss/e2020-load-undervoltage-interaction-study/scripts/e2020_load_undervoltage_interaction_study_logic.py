#!/usr/bin/env python3
"""Repetitive overload patterns driven by a load-side undervoltage protection.

Anchor: ECSS-E-ST-20-20C clause 5.3.5.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An undervoltage protection placed inside the user equipment, rather than
in the power subsystem, closes a loop nobody drew. The load energises
and demands more than its branch limit. The limiter leaves switch mode,
holds the current at the limit value, and the branch output collapses
towards whatever the load is pulling at that current. The load's own
undervoltage protection sees the collapse, decides its supply has
failed, and switches the load off. The demand disappears, the branch
recovers to nominal, the undervoltage protection releases, the load
energises again -- and the same event repeats.

Why the pattern can run forever
-------------------------------
The limiter only latches off if the branch stays in limitation for the
whole trip-off delay. The load-side protection removes the demand well
before that, so each limitation window is shorter than the delay and
the limiter is denied the one condition that would end the sequence.
Whether the pattern terminates therefore depends on what the limiter
does with its timer between windows:

    full reset        each window starts the count from zero, the
                      accumulated time never reaches the delay, and the
                      cycle repeats for as long as the bus is powered
    partial retention the count decays between windows but does not
                      reach zero, so it creeps up and may or may not
                      reach the delay depending on the duty
    integrating       the count is never given back, and the branch
                      latches off after a predictable number of cycles

The study implemented here
--------------------------
1. Validate the supplying branch and the load, including the ordering of
   the undervoltage trip and recovery thresholds.
2. Decide whether the load provokes limitation at all.
3. Compute the branch output voltage held during limitation from the
   limited current and the effective load resistance, and decide whether
   the load-side protection sees it as an undervoltage.
4. Compute the cycle period from the protection's detection and recovery
   delays, and the limitation duty inside it.
5. Accumulate the limiter timer across cycles under the declared
   retention and find the cycle on which the branch latches off, if it
   ever does.
6. Categorise the interaction and report the findings a designer acts
   on: a branch that never latches, a load that never starts, and the
   thermal duty the pass element carries meanwhile.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Interaction categories, in order of how the sequence ends.
NO_LIMITATION = "no-limitation-demand-within-limit"
NO_UNDERVOLTAGE = "limitation-without-load-undervoltage-trip"
SINGLE_LATCH_OFF = "limiter-latches-off-in-first-window"
DELAYED_LATCH_OFF = "limiter-latches-off-after-repeated-cycles"
REPETITIVE_CYCLE = "repetitive-overload-cycle-without-latch-off"
LOAD_STAYS_OFF = "load-undervoltage-protection-never-releases"

CATEGORIES = (
    NO_LIMITATION,
    NO_UNDERVOLTAGE,
    SINGLE_LATCH_OFF,
    DELAYED_LATCH_OFF,
    REPETITIVE_CYCLE,
    LOAD_STAYS_OFF,
)

SUPPLY_KEYS = ("bus_voltage_v", "current_limit_a", "trip_off_delay_s", "timer_retention")
LOAD_KEYS = (
    "inrush_current_a",
    "load_resistance_ohm",
    "undervoltage_trip_v",
    "undervoltage_recovery_v",
    "detection_delay_s",
    "recovery_delay_s",
)

# A repetitive cycle has no natural end, so the accumulation walk needs a
# stated horizon before it declares the pattern unbounded.
MAX_CYCLES = 100000

# Voltages, delays and accumulated times are all products of floats; a value
# placed exactly on a threshold must decide the same way on every platform.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12

__all__ = [
    "NO_LIMITATION",
    "NO_UNDERVOLTAGE",
    "SINGLE_LATCH_OFF",
    "DELAYED_LATCH_OFF",
    "REPETITIVE_CYCLE",
    "LOAD_STAYS_OFF",
    "CATEGORIES",
    "MAX_CYCLES",
    "validate_supply",
    "validate_load",
    "limitation_entered",
    "limited_output_voltage",
    "undervoltage_trips",
    "protection_releases",
    "cycle_period_s",
    "limitation_duty",
    "accumulated_limitation_time",
    "steady_state_accumulation",
    "cycles_to_latch_off",
    "pass_element_cycle_energy_j",
    "study_interaction",
]


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _at_or_below(value, bound):
    """True when value is at or below bound, absorbing representation error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_or_above(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _require_number(container, key, label, minimum=None, strict=True):
    if key not in container:
        raise ValueError("%s is missing '%s'" % (label, key))
    value = container[key]
    if not _is_finite_number(value):
        raise ValueError("%s['%s'] must be a finite real number" % (label, key))
    value = float(value)
    if minimum is not None:
        if strict and value <= minimum:
            raise ValueError(
                "%s['%s'] must be above %g, got %g" % (label, key, minimum, value)
            )
        if not strict and value < minimum:
            raise ValueError(
                "%s['%s'] must not be below %g, got %g" % (label, key, minimum, value)
            )
    return value


def validate_supply(spec):
    """Return a validated description of the supplying limited branch."""
    if not isinstance(spec, dict):
        raise ValueError("supply must be a mapping")
    out = {
        "bus_voltage_v": _require_number(spec, "bus_voltage_v", "supply", 0.0),
        "current_limit_a": _require_number(spec, "current_limit_a", "supply", 0.0),
        "trip_off_delay_s": _require_number(spec, "trip_off_delay_s", "supply", 0.0),
    }
    retention = _require_number(spec, "timer_retention", "supply", 0.0, strict=False)
    if retention > 1.0:
        raise ValueError(
            "supply['timer_retention'] must lie between zero and one, got %g" % retention
        )
    out["timer_retention"] = retention
    return out


def validate_load(spec):
    """Return a validated description of the load and its undervoltage protection."""
    if not isinstance(spec, dict):
        raise ValueError("load must be a mapping")
    out = {
        "inrush_current_a": _require_number(spec, "inrush_current_a", "load", 0.0),
        "load_resistance_ohm": _require_number(spec, "load_resistance_ohm", "load", 0.0),
        "undervoltage_trip_v": _require_number(spec, "undervoltage_trip_v", "load", 0.0),
        "undervoltage_recovery_v": _require_number(
            spec, "undervoltage_recovery_v", "load", 0.0
        ),
        "detection_delay_s": _require_number(spec, "detection_delay_s", "load", 0.0),
        "recovery_delay_s": _require_number(
            spec, "recovery_delay_s", "load", 0.0, strict=False
        ),
    }
    if out["undervoltage_recovery_v"] < out["undervoltage_trip_v"]:
        raise ValueError(
            "load recovery threshold %g V sits below the trip threshold %g V; the "
            "hysteresis is inverted"
            % (out["undervoltage_recovery_v"], out["undervoltage_trip_v"])
        )
    return out


def limitation_entered(current_limit_a, inrush_current_a):
    """True when the load demand reaches the branch limit and provokes limitation."""
    if not _is_finite_number(current_limit_a) or float(current_limit_a) <= 0.0:
        raise ValueError("current_limit_a must be a positive finite number")
    if not _is_finite_number(inrush_current_a) or float(inrush_current_a) < 0.0:
        raise ValueError("inrush_current_a must be a non-negative finite number")
    return _at_or_above(float(inrush_current_a), float(current_limit_a))


def limited_output_voltage(bus_voltage_v, current_limit_a, load_resistance_ohm):
    """Return the branch output voltage held while the limiter limits the current."""
    for label, value in (
        ("bus_voltage_v", bus_voltage_v),
        ("current_limit_a", current_limit_a),
        ("load_resistance_ohm", load_resistance_ohm),
    ):
        if not _is_finite_number(value) or float(value) <= 0.0:
            raise ValueError("%s must be a positive finite number" % label)
    held = float(current_limit_a) * float(load_resistance_ohm)
    return min(held, float(bus_voltage_v))


def undervoltage_trips(held_voltage_v, undervoltage_trip_v):
    """True when the load-side protection reads the held voltage as an undervoltage."""
    for label, value in (
        ("held_voltage_v", held_voltage_v),
        ("undervoltage_trip_v", undervoltage_trip_v),
    ):
        if not _is_finite_number(value) or float(value) < 0.0:
            raise ValueError("%s must be a non-negative finite number" % label)
    return _at_or_below(float(held_voltage_v), float(undervoltage_trip_v))


def protection_releases(recovered_voltage_v, undervoltage_recovery_v):
    """True when the recovered bus clears the protection's release threshold."""
    for label, value in (
        ("recovered_voltage_v", recovered_voltage_v),
        ("undervoltage_recovery_v", undervoltage_recovery_v),
    ):
        if not _is_finite_number(value) or float(value) < 0.0:
            raise ValueError("%s must be a non-negative finite number" % label)
    return _at_or_above(float(recovered_voltage_v), float(undervoltage_recovery_v))


def cycle_period_s(detection_delay_s, recovery_delay_s):
    """Return the period of one overload-and-restart cycle."""
    if not _is_finite_number(detection_delay_s) or float(detection_delay_s) <= 0.0:
        raise ValueError("detection_delay_s must be a positive finite number")
    if not _is_finite_number(recovery_delay_s) or float(recovery_delay_s) < 0.0:
        raise ValueError("recovery_delay_s must be a non-negative finite number")
    return float(detection_delay_s) + float(recovery_delay_s)


def limitation_duty(detection_delay_s, recovery_delay_s):
    """Return the fraction of each cycle the pass element spends in limitation."""
    period = cycle_period_s(detection_delay_s, recovery_delay_s)
    return float(detection_delay_s) / period


def accumulated_limitation_time(cycles, limitation_per_cycle_s, retention):
    """Return the limiter timer reading after a whole number of cycles."""
    if not isinstance(cycles, int) or isinstance(cycles, bool):
        raise ValueError("cycles must be an integer")
    if cycles < 0:
        raise ValueError("cycles must not be negative")
    if not _is_finite_number(limitation_per_cycle_s) or float(limitation_per_cycle_s) <= 0.0:
        raise ValueError("limitation_per_cycle_s must be a positive finite number")
    if not _is_finite_number(retention) or not 0.0 <= float(retention) <= 1.0:
        raise ValueError("retention must lie between zero and one")
    window = float(limitation_per_cycle_s)
    retention = float(retention)
    total = 0.0
    for _ in range(cycles):
        total = total * retention + window
    return total


def steady_state_accumulation(limitation_per_cycle_s, retention):
    """Return the timer reading the accumulation converges on, or infinity."""
    if not _is_finite_number(limitation_per_cycle_s) or float(limitation_per_cycle_s) <= 0.0:
        raise ValueError("limitation_per_cycle_s must be a positive finite number")
    if not _is_finite_number(retention) or not 0.0 <= float(retention) <= 1.0:
        raise ValueError("retention must lie between zero and one")
    retention = float(retention)
    if math.isclose(retention, 1.0, rel_tol=0.0, abs_tol=_ABS_TOL):
        return float("inf")
    return float(limitation_per_cycle_s) / (1.0 - retention)


def cycles_to_latch_off(limitation_per_cycle_s, trip_off_delay_s, retention,
                        max_cycles=MAX_CYCLES):
    """Return the cycle number the branch latches off on, or None if it never does."""
    if not _is_finite_number(trip_off_delay_s) or float(trip_off_delay_s) <= 0.0:
        raise ValueError("trip_off_delay_s must be a positive finite number")
    if not isinstance(max_cycles, int) or isinstance(max_cycles, bool) or max_cycles <= 0:
        raise ValueError("max_cycles must be a positive integer")
    window = float(limitation_per_cycle_s)
    delay = float(trip_off_delay_s)
    ceiling = steady_state_accumulation(window, retention)
    if math.isfinite(ceiling) and ceiling < delay and not math.isclose(
        ceiling, delay, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return None
    retention = float(retention)
    total = 0.0
    for cycle in range(1, max_cycles + 1):
        total = total * retention + window
        if _at_or_above(total, delay):
            return cycle
    return None


def pass_element_cycle_energy_j(bus_voltage_v, held_voltage_v, current_limit_a,
                                detection_delay_s):
    """Return the energy the pass element absorbs in one limitation window."""
    for label, value in (
        ("bus_voltage_v", bus_voltage_v),
        ("current_limit_a", current_limit_a),
        ("detection_delay_s", detection_delay_s),
    ):
        if not _is_finite_number(value) or float(value) <= 0.0:
            raise ValueError("%s must be a positive finite number" % label)
    if not _is_finite_number(held_voltage_v) or float(held_voltage_v) < 0.0:
        raise ValueError("held_voltage_v must be a non-negative finite number")
    stood_off = float(bus_voltage_v) - float(held_voltage_v)
    if stood_off < 0.0:
        raise ValueError(
            "held voltage %g V exceeds the bus %g V" % (held_voltage_v, bus_voltage_v)
        )
    return stood_off * float(current_limit_a) * float(detection_delay_s)


def study_interaction(spec):
    """Run the full clause 5.3.5.1.1 load-undervoltage interaction study.

    spec keys: supply (mapping), load (mapping), optional max_cycles.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("supply", "load"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % (key,))
    supply = validate_supply(spec["supply"])
    load = validate_load(spec["load"])
    max_cycles = spec.get("max_cycles", MAX_CYCLES)
    if not isinstance(max_cycles, int) or isinstance(max_cycles, bool) or max_cycles <= 0:
        raise ValueError("max_cycles must be a positive integer")

    report = {
        "category": None,
        "limitation_entered": False,
        "held_voltage_v": None,
        "undervoltage_trips": False,
        "protection_releases": None,
        "cycle_period_s": None,
        "limitation_duty": None,
        "cycles_to_latch_off": None,
        "steady_state_timer_s": None,
        "cycle_energy_j": None,
        "findings": [],
    }

    if not limitation_entered(supply["current_limit_a"], load["inrush_current_a"]):
        report["category"] = NO_LIMITATION
        return report
    report["limitation_entered"] = True

    held = limited_output_voltage(
        supply["bus_voltage_v"], supply["current_limit_a"], load["load_resistance_ohm"]
    )
    report["held_voltage_v"] = held
    report["cycle_energy_j"] = pass_element_cycle_energy_j(
        supply["bus_voltage_v"], held, supply["current_limit_a"], load["detection_delay_s"]
    )

    if not undervoltage_trips(held, load["undervoltage_trip_v"]):
        report["category"] = NO_UNDERVOLTAGE
        report["findings"].append(
            "the branch limits at %.2f V, above the load trip threshold %.2f V, so the "
            "load rides the event through and the limiter runs its full delay"
            % (held, load["undervoltage_trip_v"])
        )
        return report
    report["undervoltage_trips"] = True

    window = load["detection_delay_s"]
    if _at_or_above(window, supply["trip_off_delay_s"]):
        report["category"] = SINGLE_LATCH_OFF
        report["cycles_to_latch_off"] = 1
        report["findings"].append(
            "the load detects the undervoltage after the branch has already latched "
            "off, so the failure shows once and stays shown"
        )
        return report

    releases = protection_releases(supply["bus_voltage_v"], load["undervoltage_recovery_v"])
    report["protection_releases"] = releases
    if not releases:
        report["category"] = LOAD_STAYS_OFF
        report["findings"].append(
            "the recovered bus at %.2f V never reaches the load release threshold "
            "%.2f V, so the load stays off after the first window"
            % (supply["bus_voltage_v"], load["undervoltage_recovery_v"])
        )
        return report

    report["cycle_period_s"] = cycle_period_s(window, load["recovery_delay_s"])
    report["limitation_duty"] = limitation_duty(window, load["recovery_delay_s"])
    report["steady_state_timer_s"] = steady_state_accumulation(
        window, supply["timer_retention"]
    )
    latch_cycle = cycles_to_latch_off(
        window, supply["trip_off_delay_s"], supply["timer_retention"], max_cycles
    )
    report["cycles_to_latch_off"] = latch_cycle
    if latch_cycle is None:
        report["category"] = REPETITIVE_CYCLE
        report["findings"].append(
            "each limitation window lasts %.4f s against a %.4f s trip-off delay and "
            "the timer never reaches it, so the load restarts indefinitely and the "
            "failure is never annunciated"
            % (window, supply["trip_off_delay_s"])
        )
        report["findings"].append(
            "the pass element absorbs %.3f J per cycle at a %.1f%% limitation duty, a "
            "thermal duty no single-event rating covers"
            % (report["cycle_energy_j"], 100.0 * report["limitation_duty"])
        )
    else:
        report["category"] = DELAYED_LATCH_OFF
        report["findings"].append(
            "the timer accumulates across windows and the branch latches off on cycle "
            "%d, after %.4f s of repeated overload"
            % (latch_cycle, latch_cycle * report["cycle_period_s"])
        )
    return report
