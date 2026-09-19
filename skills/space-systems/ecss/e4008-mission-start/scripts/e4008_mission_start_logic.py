#!/usr/bin/env python3
"""Mission start and the mission time scale it defines.

Anchor: ECSS-E-ST-40-08C clause 5.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Mission start is one instant on the epoch scale. Declaring it creates
a third time scale for the schedule: mission time, measured from that
instant, which is the scale an operational timeline is actually
written on. The single normative item the clause places on it is that
the instant is declared and that a mission-time entry is resolved
through it.

    simulation time = mission time + (mission start - epoch at zero)

Everything below follows from that one line:

    * mission time before mission start is negative and entirely
      legal. Pre-launch and pre-separation activities live there and
      refusing a negative value deletes them
    * the mapping is exact in both directions, in integer
      nanoseconds, so an entry can be restated on whichever scale the
      reader works in
    * mission start is declared once. Moving it after entries have
      been resolved shifts every mission-time entry by the same
      amount, and that shift is reported rather than applied in
      silence
    * a move while the simulator is executing is refused: entries
      already dispatched cannot be un-dispatched

Standard library only, offline, deterministic.
"""

from __future__ import annotations

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807

SIMULATOR_STATES = ("building", "connecting", "initialising", "standby", "executing")
DECLARABLE_STATES = ("building", "connecting", "initialising", "standby")

DECISION_ACCEPTED = "mission-start-accepted"
DECISION_UNCHANGED = "mission-start-unchanged"
DECISION_RESTATED = "mission-start-restated"
DECISION_REFUSED = "mission-start-refused"

DECISIONS = (
    DECISION_ACCEPTED,
    DECISION_UNCHANGED,
    DECISION_RESTATED,
    DECISION_REFUSED,
)

REASON_STATE = "simulator-is-executing"


def require_nanoseconds(label, value):
    """Accept only an exact integer nanosecond count inside the int64 range."""
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


def _require_state(value):
    if value not in SIMULATOR_STATES:
        raise ValueError(
            "simulator state must be one of %s, got %r"
            % (", ".join(SIMULATOR_STATES), value)
        )
    return value


def mission_start_simulation_ns(mission_start_epoch_ns, epoch_at_simulation_zero_ns):
    """Simulation time at which mission time reads zero."""
    if mission_start_epoch_ns is None:
        raise ValueError("mission start has not been declared")
    if epoch_at_simulation_zero_ns is None:
        raise ValueError("the epoch at simulation time zero has not been declared")
    start = require_nanoseconds("mission_start_epoch_ns", mission_start_epoch_ns)
    zero = require_nanoseconds(
        "epoch_at_simulation_zero_ns", epoch_at_simulation_zero_ns
    )
    return _guard_int64("mission start on simulation time", start - zero)


def mission_to_simulation_ns(
    mission_time_ns, mission_start_epoch_ns, epoch_at_simulation_zero_ns
):
    """Simulation time of an entry written on the mission time scale."""
    mission_time = require_nanoseconds("mission_time_ns", mission_time_ns)
    offset = mission_start_simulation_ns(
        mission_start_epoch_ns, epoch_at_simulation_zero_ns
    )
    return _guard_int64("simulation time", mission_time + offset)


def simulation_to_mission_ns(
    simulation_time_ns, mission_start_epoch_ns, epoch_at_simulation_zero_ns
):
    """Mission time of a given simulation time; the exact inverse."""
    simulation_time = require_nanoseconds("simulation_time_ns", simulation_time_ns)
    offset = mission_start_simulation_ns(
        mission_start_epoch_ns, epoch_at_simulation_zero_ns
    )
    return _guard_int64("mission time", simulation_time - offset)


def mission_to_epoch_ns(mission_time_ns, mission_start_epoch_ns):
    """Epoch instant of a mission time, independent of the run."""
    mission_time = require_nanoseconds("mission_time_ns", mission_time_ns)
    if mission_start_epoch_ns is None:
        raise ValueError("mission start has not been declared")
    start = require_nanoseconds("mission_start_epoch_ns", mission_start_epoch_ns)
    return _guard_int64("epoch time", start + mission_time)


def is_before_mission_start(mission_time_ns):
    """Whether an entry sits on the pre-mission-start side of the scale."""
    return require_nanoseconds("mission_time_ns", mission_time_ns) < 0


def declare_mission_start(proposed_epoch_ns, current_epoch_ns=None, state="building"):
    """Decide whether a mission start declaration may be taken.

    A first declaration is taken in any state before the run starts.
    Repeating the same instant is a no-op worth naming. A different
    instant is a restatement that shifts every mission-time entry, and
    once the simulator is executing it is refused outright.
    """
    _require_state(state)
    proposed = require_nanoseconds("proposed_epoch_ns", proposed_epoch_ns)
    current = (
        None
        if current_epoch_ns is None
        else require_nanoseconds("current_epoch_ns", current_epoch_ns)
    )
    if state not in DECLARABLE_STATES:
        return {
            "decision": DECISION_REFUSED,
            "reason": REASON_STATE,
            "shift_ns": 0,
            "effective_epoch_ns": current,
        }
    if current is None:
        return {
            "decision": DECISION_ACCEPTED,
            "reason": None,
            "shift_ns": 0,
            "effective_epoch_ns": proposed,
        }
    if current == proposed:
        return {
            "decision": DECISION_UNCHANGED,
            "reason": None,
            "shift_ns": 0,
            "effective_epoch_ns": current,
        }
    return {
        "decision": DECISION_RESTATED,
        "reason": None,
        "shift_ns": _guard_int64("shift", proposed - current),
        "effective_epoch_ns": proposed,
    }


def resolve_mission_entries(
    entries, mission_start_epoch_ns, epoch_at_simulation_zero_ns
):
    """Resolve mission-time schedule entries onto simulation time."""
    if isinstance(entries, (str, bytes)) or not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list, got %r" % (entries,))
    if not entries:
        raise ValueError("a mission-time schedule with no entries resolves to nothing")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entry must be a mapping, got %r" % (entry,))
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("entry name must be a non-empty string, got %r" % (name,))
        name = name.strip()
        if name in seen:
            raise ValueError("entry name %r appears twice in one schedule" % name)
        seen.add(name)
        mission_time = require_nanoseconds(
            "entry %s mission_time_ns" % name, entry.get("mission_time_ns")
        )
        resolved.append(
            {
                "name": name,
                "declared_index": index,
                "mission_time_ns": mission_time,
                "simulation_time_ns": mission_to_simulation_ns(
                    mission_time, mission_start_epoch_ns, epoch_at_simulation_zero_ns
                ),
                "epoch_time_ns": mission_to_epoch_ns(mission_time, mission_start_epoch_ns),
                "before_mission_start": is_before_mission_start(mission_time),
            }
        )
    resolved.sort(key=lambda item: (item["simulation_time_ns"], item["declared_index"]))
    return {
        "order": [item["name"] for item in resolved],
        "entries": resolved,
        "pre_mission_start": [item["name"] for item in resolved if item["before_mission_start"]],
        "mission_start_simulation_ns": mission_start_simulation_ns(
            mission_start_epoch_ns, epoch_at_simulation_zero_ns
        ),
    }


def restate_on_new_mission_start(
    entries,
    current_mission_start_ns,
    proposed_mission_start_ns,
    epoch_at_simulation_zero_ns,
    state="standby",
    current_simulation_ns=0,
):
    """Report what moving mission start would do to a resolved schedule."""
    decision = declare_mission_start(
        proposed_mission_start_ns, current_mission_start_ns, state
    )
    before = resolve_mission_entries(
        entries, current_mission_start_ns, epoch_at_simulation_zero_ns
    )
    if decision["decision"] == DECISION_REFUSED:
        return {
            "decision": decision["decision"],
            "reason": decision["reason"],
            "shift_ns": 0,
            "moved_into_past": [],
            "order_before": before["order"],
            "order_after": before["order"],
            "applied": False,
        }
    after = resolve_mission_entries(
        entries, decision["effective_epoch_ns"], epoch_at_simulation_zero_ns
    )
    now = require_nanoseconds("current_simulation_ns", current_simulation_ns)
    lookup = {item["name"]: item for item in before["entries"]}
    moved = [
        item["name"]
        for item in after["entries"]
        if item["simulation_time_ns"] < now
        and lookup[item["name"]]["simulation_time_ns"] >= now
    ]
    return {
        "decision": decision["decision"],
        "reason": decision["reason"],
        "shift_ns": decision["shift_ns"],
        "moved_into_past": moved,
        "order_before": before["order"],
        "order_after": after["order"],
        "applied": decision["decision"] in (DECISION_ACCEPTED, DECISION_RESTATED, DECISION_UNCHANGED),
    }
