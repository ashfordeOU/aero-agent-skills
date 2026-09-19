#!/usr/bin/env python3
"""Resolve schedule entries expressed on the epoch time scale.

Anchor: ECSS-E-ST-40-08C clause 5.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A schedule entry may be triggered on the epoch time scale -- an
absolute instant -- rather than on simulation time, which counts from
the start of the run. The single normative item the clause places on
such an entry is that it carries the epoch instant it is due at, and
the simulator turns that instant into a simulation time using the
epoch value that corresponds to simulation time zero.

The conversion itself is a subtraction, and that is exactly why it is
worth writing down: everything that goes wrong around it is a
representation or a declaration problem rather than arithmetic.

    * both scales are integer nanoseconds. A floating point
      nanosecond cannot represent a mission-length interval exactly,
      so a float is refused rather than rounded
    * the epoch at simulation time zero has to be declared. Without
      it the entry has no simulation time at all, and defaulting it
      to zero silently moves every entry by the mission epoch
    * the conversion is exact and reversible, so a resolved entry can
      always be restated on the scale it was written on
    * an instant that has already passed is reported, not discarded.
      It is the single most common symptom of a schedule written
      against the wrong epoch
    * a repeating entry resolves to its first occurrence at or after
      the instant the schedule is being resolved for

Standard library only, offline, deterministic.
"""

from __future__ import annotations

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807

DISPOSITION_FUTURE = "due-in-future"
DISPOSITION_NOW = "due-now"
DISPOSITION_PAST = "already-past"
DISPOSITION_NEVER = "no-occurrence-remaining"

DISPOSITIONS = (
    DISPOSITION_FUTURE,
    DISPOSITION_NOW,
    DISPOSITION_PAST,
    DISPOSITION_NEVER,
)


def require_nanoseconds(label, value):
    """Accept only an exact integer nanosecond count inside the int64 range.

    A float is refused outright. A mission-length interval in
    nanoseconds is far past the point where a double holds every
    integer, so accepting one would make the conversion lossy in a way
    no later check could detect.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            "%s must be an integer nanosecond count, got %r" % (label, value)
        )
    if value < INT64_MIN or value > INT64_MAX:
        raise ValueError("%s does not fit the 64-bit nanosecond range" % label)
    return value


def _guard_int64(label, value):
    if value < INT64_MIN or value > INT64_MAX:
        raise ValueError("%s overflows the 64-bit nanosecond range" % label)
    return value


def epoch_to_simulation_ns(epoch_time_ns, epoch_at_simulation_zero_ns):
    """Simulation time at which a given epoch instant occurs."""
    epoch_time = require_nanoseconds("epoch_time_ns", epoch_time_ns)
    if epoch_at_simulation_zero_ns is None:
        raise ValueError(
            "the epoch at simulation time zero is not declared; an epoch "
            "entry cannot be resolved without it"
        )
    zero = require_nanoseconds(
        "epoch_at_simulation_zero_ns", epoch_at_simulation_zero_ns
    )
    return _guard_int64("simulation time", epoch_time - zero)


def simulation_to_epoch_ns(simulation_time_ns, epoch_at_simulation_zero_ns):
    """Epoch instant of a given simulation time; the exact inverse."""
    simulation_time = require_nanoseconds("simulation_time_ns", simulation_time_ns)
    if epoch_at_simulation_zero_ns is None:
        raise ValueError(
            "the epoch at simulation time zero is not declared; a simulation "
            "time cannot be restated on the epoch scale without it"
        )
    zero = require_nanoseconds(
        "epoch_at_simulation_zero_ns", epoch_at_simulation_zero_ns
    )
    return _guard_int64("epoch time", simulation_time + zero)


def first_occurrence_ns(base_simulation_ns, period_ns, not_before_ns):
    """First occurrence of an entry at or after a given simulation time.

    A single-shot entry occurs once, at its base time. A repeating
    entry occurs at base + k*period for whole k >= 0, and the answer is
    the smallest such time that is not before the resolution instant.
    The arithmetic stays in integers so the result is exact.
    """
    base = require_nanoseconds("base_simulation_ns", base_simulation_ns)
    floor = require_nanoseconds("not_before_ns", not_before_ns)
    if period_ns is None:
        return base if base >= floor else None
    period = require_nanoseconds("period_ns", period_ns)
    if period <= 0:
        raise ValueError("a repeat period must be greater than zero, got %d" % period)
    if base >= floor:
        return base
    gap = floor - base
    steps = -(-gap // period)
    return _guard_int64("occurrence", base + steps * period)


def disposition_of(simulation_time_ns, current_simulation_ns):
    """Where a resolved simulation time sits relative to the clock now."""
    resolved = require_nanoseconds("simulation_time_ns", simulation_time_ns)
    now = require_nanoseconds("current_simulation_ns", current_simulation_ns)
    if resolved > now:
        return DISPOSITION_FUTURE
    if resolved == now:
        return DISPOSITION_NOW
    return DISPOSITION_PAST


def resolve_epoch_entry(entry, epoch_at_simulation_zero_ns, current_simulation_ns=0):
    """Resolve one epoch-scale schedule entry onto simulation time."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("entry name must be a non-empty string, got %r" % (name,))
    name = name.strip()
    base = epoch_to_simulation_ns(
        entry.get("epoch_time_ns"), epoch_at_simulation_zero_ns
    )
    now = require_nanoseconds("current_simulation_ns", current_simulation_ns)
    period = entry.get("period_ns")
    declared_disposition = disposition_of(base, now)
    occurrence = first_occurrence_ns(base, period, now)
    findings = []
    if declared_disposition == DISPOSITION_PAST:
        findings.append(
            "%s is written at an epoch instant that simulation time %d has "
            "already passed" % (name, now)
        )
    if occurrence is None:
        disposition = DISPOSITION_NEVER
    else:
        disposition = disposition_of(occurrence, now)
    return {
        "name": name,
        "base_simulation_ns": base,
        "occurrence_simulation_ns": occurrence,
        "epoch_time_ns": require_nanoseconds("epoch_time_ns", entry.get("epoch_time_ns")),
        "repeating": period is not None,
        "disposition": disposition,
        "declared_disposition": declared_disposition,
        "findings": findings,
    }


def resolve_epoch_schedule(entries, epoch_at_simulation_zero_ns, current_simulation_ns=0):
    """Resolve a set of epoch-scale entries into execution order."""
    if isinstance(entries, (str, bytes)) or not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list, got %r" % (entries,))
    if not entries:
        raise ValueError("an epoch schedule with no entries has nothing to resolve")
    resolved = []
    findings = []
    seen = set()
    for index, entry in enumerate(entries):
        item = resolve_epoch_entry(
            entry, epoch_at_simulation_zero_ns, current_simulation_ns
        )
        if item["name"] in seen:
            raise ValueError("entry name %r appears twice in one schedule" % item["name"])
        seen.add(item["name"])
        item["declared_index"] = index
        findings.extend(item["findings"])
        resolved.append(item)
    runnable = [item for item in resolved if item["occurrence_simulation_ns"] is not None]
    runnable.sort(key=lambda item: (item["occurrence_simulation_ns"], item["declared_index"]))
    dropped = [item["name"] for item in resolved if item["occurrence_simulation_ns"] is None]
    return {
        "order": [item["name"] for item in runnable],
        "entries": resolved,
        "runnable": runnable,
        "no_occurrence": dropped,
        "findings": findings,
        "clean": not findings and not dropped,
    }
