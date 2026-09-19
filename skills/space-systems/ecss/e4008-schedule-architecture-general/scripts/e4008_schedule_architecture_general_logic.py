#!/usr/bin/env python3
"""General requirements on a simulator schedule architecture.

Anchor: ECSS-E-ST-40-08C clause 4.2.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A schedule is a list of items, each of which asks the simulator to call
one entry point of one instance, either once or on a repeating cycle.
The clause carries five general normative items:

    1 every scheduled item resolves onto an entry point that the
      assembly actually provides
    2 a cyclic item declares a positive cycle time; a single-shot item
      is released exactly once
    3 every offset is non-negative and lands strictly inside its own
      cycle
    4 the summed worst-case execution time over the cycle times stays
      inside the declared utilisation budget
    5 the release order is determined: no two items may share a release
      instant and a priority

Item five is the one that is invisible until it bites. Two items
released at the same instant with the same priority run in whatever
order the platform enumerates them, so the run is reproducible on one
build and not on the next.

Times are carried internally as whole microseconds so the hyperperiod is
an exact integer least common multiple rather than a float accumulation.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
import re

NORMATIVE_ITEMS = (
    "scheduled-entry-points-resolve",
    "cycle-time-declared-for-every-item",
    "offsets-inside-their-own-cycle",
    "schedule-utilisation-inside-the-budget",
    "release-order-determined",
)

ITEM_KINDS = ("cyclic", "single-shot")
SCHEDULE_VERDICTS = ("schedule-acceptable", "schedule-not-acceptable")

MICROSECONDS_PER_SECOND = 1000000
DEFAULT_UTILISATION_BUDGET = 1.0
MAX_ENUMERATED_RELEASES = 200000

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_SEPARATOR = "/"
ENTRY_POINT_SEPARATOR = "."

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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def to_microseconds(name, seconds):
    """Convert a duration in seconds to whole microseconds, or refuse it."""
    value = _require_number(name, seconds)
    scaled = value * MICROSECONDS_PER_SECOND
    rounded = round(scaled)
    if abs(scaled - rounded) > 1e-6:
        raise ValueError(
            "%s = %r s is finer than the one-microsecond schedule resolution"
            % (name, seconds)
        )
    return int(rounded)


def parse_entry_point(reference):
    """Split an instance-path.entry-point reference into its two parts."""
    if not isinstance(reference, str) or ENTRY_POINT_SEPARATOR not in reference:
        raise ValueError(
            "entry point reference %r must be written <instance path>%s<entry point>"
            % (reference, ENTRY_POINT_SEPARATOR)
        )
    path, _sep, entry = reference.rpartition(ENTRY_POINT_SEPARATOR)
    if not path.startswith(PATH_SEPARATOR):
        raise ValueError(
            "entry point reference %r must name an absolute instance path" % reference
        )
    if IDENTIFIER_PATTERN.match(entry) is None:
        raise ValueError(
            "entry point name %r in %r is not a legal identifier" % (entry, reference)
        )
    for segment in path.strip(PATH_SEPARATOR).split(PATH_SEPARATOR):
        if IDENTIFIER_PATTERN.match(segment) is None:
            raise ValueError(
                "instance path segment %r in %r is not a legal identifier"
                % (segment, reference)
            )
    return (path, entry)


def validate_schedule_item(item):
    """Normalize one schedule item into whole microseconds, or refuse it."""
    _require_mapping("schedule item", item)
    name = item.get("name")
    if not isinstance(name, str) or IDENTIFIER_PATTERN.match(name) is None:
        raise ValueError("schedule item name %r is not a legal identifier" % (name,))
    kind = item.get("kind", "cyclic")
    if kind not in ITEM_KINDS:
        raise ValueError(
            "schedule item %r declares kind %r, expected one of %s"
            % (name, kind, ", ".join(ITEM_KINDS))
        )
    priority = item.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValueError(
            "schedule item %r priority must be an integer, got %r" % (name, priority)
        )
    wcet_us = to_microseconds("%s worst_case_execution_s" % name, item.get("worst_case_execution_s", 0.0))
    if wcet_us < 0:
        raise ValueError("schedule item %r declares a negative execution time" % name)
    offset_us = to_microseconds("%s offset_s" % name, item.get("offset_s", 0.0))
    cycle_us = None
    if kind == "cyclic":
        if item.get("cycle_s") is None:
            raise ValueError("cyclic schedule item %r declares no cycle_s" % name)
        cycle_us = to_microseconds("%s cycle_s" % name, item["cycle_s"])
    return {
        "name": name,
        "kind": kind,
        "entry_point": item.get("entry_point"),
        "priority": priority,
        "cycle_us": cycle_us,
        "offset_us": offset_us,
        "wcet_us": wcet_us,
    }


def normalize_schedule(items):
    """Validate every item and refuse a repeated item name."""
    _require_sequence("schedule items", items)
    if not items:
        raise ValueError("a schedule needs at least one item")
    normalized = [validate_schedule_item(item) for item in items]
    names = [item["name"] for item in normalized]
    if len(set(names)) != len(names):
        raise ValueError("schedule repeats an item name")
    return normalized


def schedule_utilisation(normalized_items):
    """Summed execution time over cycle time across the cyclic items."""
    total = 0.0
    for item in normalized_items:
        if item["kind"] != "cyclic":
            continue
        if not item["cycle_us"]:
            raise ValueError("cyclic item %r has no cycle to divide by" % item["name"])
        total += item["wcet_us"] / item["cycle_us"]
    return total


def hyperperiod_us(normalized_items):
    """Least common multiple of the cyclic periods, in whole microseconds."""
    periods = [item["cycle_us"] for item in normalized_items if item["kind"] == "cyclic"]
    if not periods:
        return 0
    period = periods[0]
    for other in periods[1:]:
        period = period * other // math.gcd(period, other)
    return period


def release_instants(item, horizon_us):
    """Every instant inside the horizon at which one item is released."""
    if not isinstance(horizon_us, int) or horizon_us <= 0:
        raise ValueError("horizon_us must be a positive whole number of microseconds")
    if item["kind"] == "single-shot":
        return [item["offset_us"]] if item["offset_us"] < horizon_us else []
    cycle = item["cycle_us"]
    if not cycle:
        raise ValueError("cyclic item %r has no cycle" % item["name"])
    count = (horizon_us - item["offset_us"] + cycle - 1) // cycle
    if count <= 0:
        return []
    if count > MAX_ENUMERATED_RELEASES:
        raise ValueError(
            "item %r releases %d times in the hyperperiod, beyond the %d the "
            "determinism check enumerates" % (item["name"], count, MAX_ENUMERATED_RELEASES)
        )
    return [item["offset_us"] + index * cycle for index in range(count)]


def find_order_ambiguities(normalized_items, horizon_us=None):
    """Instants where two items share a release time and a priority."""
    horizon = horizon_us if horizon_us is not None else hyperperiod_us(normalized_items)
    if not horizon:
        horizon = max(
            (item["offset_us"] + 1 for item in normalized_items), default=1
        )
    buckets = {}
    total = 0
    for item in normalized_items:
        for instant in release_instants(item, horizon):
            total += 1
            if total > MAX_ENUMERATED_RELEASES:
                raise ValueError(
                    "the hyperperiod holds more than %d releases; the determinism "
                    "check refuses to enumerate it" % MAX_ENUMERATED_RELEASES
                )
            buckets.setdefault((instant, item["priority"]), []).append(item["name"])
    ambiguities = []
    for (instant, priority), names in sorted(buckets.items()):
        if len(names) > 1:
            ambiguities.append(
                {
                    "instant_us": instant,
                    "priority": priority,
                    "items": sorted(names),
                }
            )
    return ambiguities


def _item_result(identifier, satisfied, finding=None):
    return {"item": identifier, "satisfied": satisfied, "finding": finding}


def evaluate_schedule_architecture(
    schedule, available_entry_points=(), utilisation_budget=DEFAULT_UTILISATION_BUDGET
):
    """Grade a schedule against the five general items of 4.2.4.1."""
    _require_mapping("schedule", schedule)
    budget = _require_number("utilisation_budget", utilisation_budget)
    if budget <= 0.0:
        raise ValueError("utilisation_budget must be greater than zero")
    normalized = normalize_schedule(schedule.get("items"))
    available = set(available_entry_points)
    items = []
    findings = []

    unresolved = []
    for item in normalized:
        path, entry = parse_entry_point(item["entry_point"])
        reference = "%s%s%s" % (path, ENTRY_POINT_SEPARATOR, entry)
        if available and reference not in available:
            unresolved.append("%s -> %s" % (item["name"], reference))
    items.append(
        _item_result(NORMATIVE_ITEMS[0], True)
        if not unresolved
        else _item_result(
            NORMATIVE_ITEMS[0],
            False,
            "entry points the assembly does not provide: %s" % ", ".join(unresolved),
        )
    )

    bad_cycles = [
        item["name"]
        for item in normalized
        if item["kind"] == "cyclic" and (not item["cycle_us"] or item["cycle_us"] <= 0)
    ]
    items.append(
        _item_result(NORMATIVE_ITEMS[1], True)
        if not bad_cycles
        else _item_result(
            NORMATIVE_ITEMS[1],
            False,
            "cyclic items without a positive cycle: %s" % ", ".join(bad_cycles),
        )
    )

    bad_offsets = []
    for item in normalized:
        if item["offset_us"] < 0:
            bad_offsets.append("%s offset is negative" % item["name"])
        elif item["kind"] == "cyclic" and item["cycle_us"] and item["offset_us"] >= item["cycle_us"]:
            bad_offsets.append(
                "%s offset %d us is not inside its %d us cycle"
                % (item["name"], item["offset_us"], item["cycle_us"])
            )
    items.append(
        _item_result(NORMATIVE_ITEMS[2], True)
        if not bad_offsets
        else _item_result(NORMATIVE_ITEMS[2], False, "; ".join(bad_offsets))
    )

    utilisation = schedule_utilisation(normalized)
    inside = _at_most(utilisation, budget)
    items.append(
        _item_result(NORMATIVE_ITEMS[3], True)
        if inside
        else _item_result(
            NORMATIVE_ITEMS[3],
            False,
            "utilisation %.6f exceeds the budget %.6f" % (utilisation, budget),
        )
    )

    ambiguities = find_order_ambiguities(normalized)
    items.append(
        _item_result(NORMATIVE_ITEMS[4], True)
        if not ambiguities
        else _item_result(
            NORMATIVE_ITEMS[4],
            False,
            "; ".join(
                "%s share priority %d at %d us"
                % (" and ".join(entry["items"]), entry["priority"], entry["instant_us"])
                for entry in ambiguities
            ),
        )
    )

    findings = [entry["finding"] for entry in items if entry["finding"]]
    satisfied = sum(1 for entry in items if entry["satisfied"])
    acceptable = satisfied == len(NORMATIVE_ITEMS)
    return {
        "items": items,
        "satisfied": satisfied,
        "required": len(NORMATIVE_ITEMS),
        "utilisation": utilisation,
        "utilisation_budget": budget,
        "hyperperiod_us": hyperperiod_us(normalized),
        "ambiguities": ambiguities,
        "acceptable": acceptable,
        "verdict": "schedule-acceptable" if acceptable else "schedule-not-acceptable",
        "findings": findings,
    }
