"""Execution observability level of an on-board control procedure.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

What an observability level is. An on-board control procedure runs
without the ground watching each move, so the only picture the ground
gets is whatever the engine was told to emit. The observability level
is that setting: how deep inside a running procedure the reporting
goes. It is a link-budget decision wearing an operations costume,
because every level below the coarsest one buys insight with downlink
octets that are not free.

The levels, coarsest first:

  none        -- nothing is emitted. The procedure runs blind: the
                 ground learns it ran only from whatever the procedure
                 itself changed in the spacecraft.
  procedure   -- the engine reports the procedure starting, completing
                 and aborting. Enough to know it ran and how it ended,
                 not enough to know where it went wrong.
  step        -- each step start and completion is reported too. Enough
                 to locate a failure to one step of the procedure.
  instruction -- every instruction the engine executes is reported.
                 Enough to reconstruct the run, and expensive enough
                 that it is a debugging posture, not an operating one.

The levels are ordered and cumulative. A level shows everything the
coarser levels show plus its own events, so asking "which level do I
need" is answerable: take the deepest event the operator must see and
read off the level that first makes it visible.

Two constraints meet here. An engine supports only some of the levels,
and a requested level above what the engine supports quietly becomes
the highest it does support -- the ground sees less than it asked for
and nothing reports the shortfall unless something computes it. And a
fleet of procedures reporting at once has to fit a downlink budget; the
honest answer when it does not is a graded downgrade, never a silent
one.

Stdlib only, offline, deterministic.
"""

LEVEL_NONE = "none"
LEVEL_PROCEDURE = "procedure"
LEVEL_STEP = "step"
LEVEL_INSTRUCTION = "instruction"

# Ordered coarsest to deepest. The index is the rank.
LEVEL_ORDER = (LEVEL_NONE, LEVEL_PROCEDURE, LEVEL_STEP, LEVEL_INSTRUCTION)

EVENT_PROCEDURE_STARTED = "procedure-started"
EVENT_PROCEDURE_COMPLETED = "procedure-completed"
EVENT_PROCEDURE_ABORTED = "procedure-aborted"
EVENT_STEP_STARTED = "step-started"
EVENT_STEP_COMPLETED = "step-completed"
EVENT_INSTRUCTION_EXECUTED = "instruction-executed"

# The level at which each event first becomes visible.
EVENT_FIRST_VISIBLE_AT = {
    EVENT_PROCEDURE_STARTED: LEVEL_PROCEDURE,
    EVENT_PROCEDURE_COMPLETED: LEVEL_PROCEDURE,
    EVENT_PROCEDURE_ABORTED: LEVEL_PROCEDURE,
    EVENT_STEP_STARTED: LEVEL_STEP,
    EVENT_STEP_COMPLETED: LEVEL_STEP,
    EVENT_INSTRUCTION_EXECUTED: LEVEL_INSTRUCTION,
}

PLAN_WITHIN_BUDGET = "within-budget"
PLAN_DOWNGRADED_TO_FIT = "downgraded-to-fit-budget"
PLAN_OVER_BUDGET_AT_FLOORS = "over-budget-with-every-procedure-at-its-floor"

# A downlink rate is a product of integer octet counts and a possibly
# fractional execution rate, so a plan that lands exactly on its budget
# can sit a few units in the last place either side of it. This relative
# tolerance absorbs that; the budget itself is never widened.
RATE_TOLERANCE = 1.0e-12


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return float(value)


def validate_level(level):
    """Validate an observability level name and return it."""
    if level not in LEVEL_ORDER:
        raise ValueError(
            "unknown observability level %r (expected one of %s)"
            % (level, ", ".join(LEVEL_ORDER))
        )
    return level


def level_rank(level):
    """Ordinal rank of a level, coarsest at zero."""
    return LEVEL_ORDER.index(validate_level(level))


def compare_levels(left, right):
    """Return -1, 0 or 1 as the left level is coarser, equal or deeper."""
    difference = level_rank(left) - level_rank(right)
    if difference < 0:
        return -1
    return 1 if difference > 0 else 0


def deeper_level(left, right):
    """The deeper of two levels -- how a mandated floor is applied."""
    return left if compare_levels(left, right) >= 0 else right


def coarser_level(left, right):
    """The coarser of two levels -- how an engine ceiling is applied."""
    return left if compare_levels(left, right) <= 0 else right


def observable_events(level):
    """Event kinds an engine emits at this level, in a stable order."""
    rank = level_rank(level)
    return tuple(
        event
        for event in EVENT_FIRST_VISIBLE_AT
        if level_rank(EVENT_FIRST_VISIBLE_AT[event]) <= rank
    )


def is_event_observable(level, event):
    """Is this event visible to the ground at this level?"""
    if event not in EVENT_FIRST_VISIBLE_AT:
        raise ValueError("unknown execution event %r" % (event,))
    return level_rank(EVENT_FIRST_VISIBLE_AT[event]) <= level_rank(level)


def minimum_level_for(events):
    """Coarsest level that makes every required event visible."""
    if not isinstance(events, (list, tuple, set)):
        raise ValueError("events must be a list, tuple or set")
    level = LEVEL_NONE
    for event in events:
        if event not in EVENT_FIRST_VISIBLE_AT:
            raise ValueError("unknown execution event %r" % (event,))
        level = deeper_level(level, EVENT_FIRST_VISIBLE_AT[event])
    return level


def validate_engine_support(supported_levels):
    """Validate the set of levels an engine supports; return its ceiling."""
    if not isinstance(supported_levels, (list, tuple)) or not supported_levels:
        raise ValueError("an engine must support at least one level")
    ceiling = LEVEL_NONE
    for level in supported_levels:
        ceiling = deeper_level(ceiling, validate_level(level))
    return ceiling


def effective_level(requested, supported_levels):
    """What the ground actually gets, and whether it is short of the ask."""
    wanted = validate_level(requested)
    ceiling = validate_engine_support(supported_levels)
    granted = coarser_level(wanted, ceiling)
    return {
        "requested": wanted,
        "engine_ceiling": ceiling,
        "granted": granted,
        "shortfall": compare_levels(granted, wanted) < 0,
        "lost_events": tuple(
            event
            for event in observable_events(wanted)
            if event not in observable_events(granted)
        ),
    }


def validate_profile(profile):
    """Validate one procedure's reporting profile and normalize it."""
    if not isinstance(profile, dict):
        raise ValueError("procedure profile must be a mapping")
    proc_id = profile.get("id")
    if not isinstance(proc_id, str) or not proc_id.strip():
        raise ValueError("procedure profile needs a non-empty string id")
    proc_id = proc_id.strip()
    step_count = _integer("procedure %s step_count" % proc_id,
                          profile.get("step_count"), 1)
    instruction_count = _integer(
        "procedure %s instruction_count" % proc_id,
        profile.get("instruction_count"), step_count,
    )
    event_octets = _integer("procedure %s event_octets" % proc_id,
                            profile.get("event_octets"), 1)
    executions = _positive_number(
        "procedure %s executions_per_hour" % proc_id,
        profile.get("executions_per_hour"),
    )
    requested = validate_level(profile.get("requested_level", LEVEL_PROCEDURE))
    floor = validate_level(profile.get("floor_level", LEVEL_NONE))
    if compare_levels(floor, requested) > 0:
        raise ValueError(
            "procedure %s asks for %s but declares a floor of %s, which is "
            "deeper" % (proc_id, requested, floor)
        )
    return {
        "id": proc_id,
        "step_count": step_count,
        "instruction_count": instruction_count,
        "event_octets": event_octets,
        "executions_per_hour": executions,
        "requested_level": requested,
        "floor_level": floor,
    }


def events_per_execution(profile, level):
    """How many execution events one run emits at a given level."""
    working = validate_profile(profile)
    rank = level_rank(level)
    count = 0
    if rank >= level_rank(LEVEL_PROCEDURE):
        # One start and one termination event per run.
        count += 2
    if rank >= level_rank(LEVEL_STEP):
        count += 2 * working["step_count"]
    if rank >= level_rank(LEVEL_INSTRUCTION):
        count += working["instruction_count"]
    return count


def octets_per_execution(profile, level):
    """Downlink octets one run costs at a given level."""
    working = validate_profile(profile)
    return events_per_execution(working, level) * working["event_octets"]


def rate_octets_per_hour(profile, level):
    """Downlink octets per hour one procedure costs at a given level."""
    working = validate_profile(profile)
    return octets_per_execution(working, level) * working["executions_per_hour"]


def _within(rate, budget):
    return rate - budget <= abs(budget) * RATE_TOLERANCE


def assess_observability_plan(profiles, budget_octets_per_hour,
                              supported_levels=None):
    """Grade a fleet of procedures against a downlink budget, downgrading."""
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("profiles must be a non-empty list")
    budget = _positive_number("budget_octets_per_hour", budget_octets_per_hour)
    ceiling = (
        validate_engine_support(supported_levels)
        if supported_levels is not None
        else LEVEL_INSTRUCTION
    )
    working = []
    seen = set()
    for profile in profiles:
        normalized = validate_profile(profile)
        if normalized["id"] in seen:
            raise ValueError("duplicate procedure id %r" % (normalized["id"],))
        seen.add(normalized["id"])
        granted = coarser_level(normalized["requested_level"], ceiling)
        if compare_levels(normalized["floor_level"], granted) > 0:
            raise ValueError(
                "procedure %s needs at least %s but the engine ceiling is %s"
                % (normalized["id"], normalized["floor_level"], ceiling)
            )
        normalized["assigned_level"] = granted
        normalized["engine_shortfall"] = compare_levels(
            granted, normalized["requested_level"]
        ) < 0
        working.append(normalized)

    downgrades = []
    while True:
        total = sum(rate_octets_per_hour(p, p["assigned_level"])
                    for p in working)
        if _within(total, budget):
            break
        candidates = [
            p for p in working
            if compare_levels(p["assigned_level"], p["floor_level"]) > 0
        ]
        if not candidates:
            break
        # Downgrade the costliest procedure first; ties break on id so the
        # same fleet always produces the same plan.
        candidates.sort(
            key=lambda p: (-rate_octets_per_hour(p, p["assigned_level"]),
                           p["id"])
        )
        victim = candidates[0]
        previous = victim["assigned_level"]
        victim["assigned_level"] = LEVEL_ORDER[level_rank(previous) - 1]
        downgrades.append({
            "id": victim["id"],
            "from_level": previous,
            "to_level": victim["assigned_level"],
        })

    total = sum(rate_octets_per_hour(p, p["assigned_level"]) for p in working)
    if not _within(total, budget):
        disposition = PLAN_OVER_BUDGET_AT_FLOORS
    elif downgrades:
        disposition = PLAN_DOWNGRADED_TO_FIT
    else:
        disposition = PLAN_WITHIN_BUDGET
    return {
        "disposition": disposition,
        "budget_octets_per_hour": budget,
        "total_octets_per_hour": total,
        "margin_octets_per_hour": budget - total,
        "engine_ceiling": ceiling,
        "downgrades": downgrades,
        "assignments": [
            {
                "id": p["id"],
                "requested_level": p["requested_level"],
                "assigned_level": p["assigned_level"],
                "floor_level": p["floor_level"],
                "engine_shortfall": p["engine_shortfall"],
                "octets_per_hour": rate_octets_per_hour(p,
                                                        p["assigned_level"]),
                "observable_events": observable_events(p["assigned_level"]),
            }
            for p in working
        ],
        "grouped_by_assigned_level": {
            level: [p["id"] for p in working if p["assigned_level"] == level]
            for level in LEVEL_ORDER
            if any(p["assigned_level"] == level for p in working)
        },
    }
