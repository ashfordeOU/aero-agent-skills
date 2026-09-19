"""Controlling the OBCP engine as a whole, and what that does to its procedures.

Anchor: ECSS-E-ST-70-41C clause 6.18.5.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause is about the engine, not about any one procedure: starting
it, stopping it, holding it and resuming it. Every one of those acts
on the procedures the engine is hosting, and the whole difficulty of
the clause is that the effect is not the same in each direction.

Stopping is destructive. An engine that stops does not leave
procedures suspended in mid-step waiting for it to come back; the
procedures it was running are terminated, and terminated procedures do
not resume when the engine starts again. A stop is therefore a
different act from a hold, even though from the ground both look like
"the procedures are no longer stepping".

Holding is reversible, and reversible only for what it held. An engine
hold suspends the procedures that were running; an engine resume
releases exactly those. A procedure that was already suspended by its
own command was not suspended by the engine, and it stays suspended
across the engine's hold and resume. Releasing it too is the common
defect: the engine resume silently restarts a procedure somebody
deliberately stopped.

Activation follows the engine. A procedure cannot be activated into an
engine that is stopped or held, and the engine hosts a bounded number
of simultaneously running procedures, so an activation past that bound
is refused rather than queued.

Stdlib only, offline, deterministic.
"""

ENGINE_STOPPED = "stopped"
ENGINE_RUNNING = "running"
ENGINE_HELD = "held"
ENGINE_STATES = (ENGINE_STOPPED, ENGINE_RUNNING, ENGINE_HELD)

PROCEDURE_LOADED = "loaded"
PROCEDURE_RUNNING = "running"
PROCEDURE_HELD = "held"
PROCEDURE_TERMINATED = "terminated"
PROCEDURE_STATES = (
    PROCEDURE_LOADED,
    PROCEDURE_RUNNING,
    PROCEDURE_HELD,
    PROCEDURE_TERMINATED,
)

HELD_BY_ENGINE = "engine"
HELD_BY_COMMAND = "own-command"

COMMAND_START_ENGINE = "start-engine"
COMMAND_STOP_ENGINE = "stop-engine"
COMMAND_HOLD_ENGINE = "hold-engine"
COMMAND_RESUME_ENGINE = "resume-engine"
COMMAND_LOAD = "load-procedure"
COMMAND_ACTIVATE = "activate-procedure"
COMMAND_HOLD_PROCEDURE = "hold-procedure"
COMMAND_RESUME_PROCEDURE = "resume-procedure"
COMMAND_TERMINATE = "terminate-procedure"
ENGINE_COMMANDS = (
    COMMAND_START_ENGINE,
    COMMAND_STOP_ENGINE,
    COMMAND_HOLD_ENGINE,
    COMMAND_RESUME_ENGINE,
)
PROCEDURE_COMMANDS = (
    COMMAND_LOAD,
    COMMAND_ACTIVATE,
    COMMAND_HOLD_PROCEDURE,
    COMMAND_RESUME_PROCEDURE,
    COMMAND_TERMINATE,
)
COMMANDS = ENGINE_COMMANDS + PROCEDURE_COMMANDS

FINDING_ILLEGAL_ENGINE_TRANSITION = "engine-command-rejected-in-the-current-engine-state"
FINDING_STOP_TERMINATED_PROCEDURES = "stopping-the-engine-terminated-live-procedures"
FINDING_HOLD_SUSPENDED_PROCEDURES = "holding-the-engine-suspended-running-procedures"
FINDING_RESUME_LEFT_OWN_HOLDS = "engine-resume-left-individually-held-procedures-held"
FINDING_ACTIVATION_WHILE_NOT_RUNNING = "activation-refused-because-the-engine-is-not-running"
FINDING_UNKNOWN_PROCEDURE = "command-named-a-procedure-the-engine-has-not-loaded"
FINDING_ALREADY_ACTIVE = "activation-refused-because-the-procedure-is-already-live"
FINDING_CAPACITY_REACHED = "activation-refused-because-the-engine-is-at-its-procedure-limit"
FINDING_TERMINATED_CANNOT_RESUME = "a-terminated-procedure-cannot-be-resumed-by-the-engine"
FINDING_NOTHING_TO_RESUME = "resume-refused-because-the-procedure-is-not-held"
FINDING_NOTHING_TO_HOLD = "hold-refused-because-the-procedure-is-not-running"

_ENGINE_TRANSITIONS = {
    (ENGINE_STOPPED, COMMAND_START_ENGINE): ENGINE_RUNNING,
    (ENGINE_RUNNING, COMMAND_STOP_ENGINE): ENGINE_STOPPED,
    (ENGINE_HELD, COMMAND_STOP_ENGINE): ENGINE_STOPPED,
    (ENGINE_RUNNING, COMMAND_HOLD_ENGINE): ENGINE_HELD,
    (ENGINE_HELD, COMMAND_RESUME_ENGINE): ENGINE_RUNNING,
}


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def new_engine(capacity=4, state=ENGINE_STOPPED):
    """An engine with no procedures loaded and a bounded procedure limit."""
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be an integer, got %r" % (capacity,))
    if capacity < 1:
        raise ValueError("an engine must host at least one procedure, got %d" % capacity)
    if state not in ENGINE_STATES:
        raise ValueError(
            "engine state must be one of %s, got %r" % (", ".join(ENGINE_STATES), state)
        )
    return {"state": state, "capacity": capacity, "procedures": {}}


def live_procedures(engine):
    """Identifiers of the procedures the engine currently counts against capacity."""
    return sorted(
        name
        for name, p in engine["procedures"].items()
        if p["state"] in (PROCEDURE_RUNNING, PROCEDURE_HELD)
    )


def _normalise_command(raw, index):
    if not isinstance(raw, dict):
        raise ValueError("command %d must be a mapping, got %r" % (index, raw))
    name = raw.get("command")
    if name not in COMMANDS:
        raise ValueError(
            "command %d is %r, expected one of %s" % (index, name, ", ".join(COMMANDS))
        )
    procedure_id = raw.get("procedure_id")
    if name in PROCEDURE_COMMANDS:
        procedure_id = _identifier("command %d procedure id" % index, procedure_id)
    elif procedure_id is not None:
        raise ValueError("engine command %d must not name a procedure" % index)
    return {"command": name, "procedure_id": procedure_id}


def _apply_engine_command(engine, name, findings):
    target = _ENGINE_TRANSITIONS.get((engine["state"], name))
    if target is None:
        findings.append(
            {
                "finding": FINDING_ILLEGAL_ENGINE_TRANSITION,
                "command": name,
                "engine_state": engine["state"],
            }
        )
        return
    if name == COMMAND_STOP_ENGINE:
        terminated = []
        for procedure_id in live_procedures(engine):
            engine["procedures"][procedure_id]["state"] = PROCEDURE_TERMINATED
            engine["procedures"][procedure_id]["held_by"] = None
            terminated.append(procedure_id)
        if terminated:
            findings.append(
                {
                    "finding": FINDING_STOP_TERMINATED_PROCEDURES,
                    "procedures": terminated,
                }
            )
    elif name == COMMAND_HOLD_ENGINE:
        suspended = []
        for procedure_id, procedure in sorted(engine["procedures"].items()):
            if procedure["state"] == PROCEDURE_RUNNING:
                procedure["state"] = PROCEDURE_HELD
                procedure["held_by"] = HELD_BY_ENGINE
                suspended.append(procedure_id)
        if suspended:
            findings.append(
                {
                    "finding": FINDING_HOLD_SUSPENDED_PROCEDURES,
                    "procedures": suspended,
                }
            )
    elif name == COMMAND_RESUME_ENGINE:
        left_held = []
        for procedure_id, procedure in sorted(engine["procedures"].items()):
            if procedure["state"] != PROCEDURE_HELD:
                continue
            if procedure["held_by"] == HELD_BY_ENGINE:
                procedure["state"] = PROCEDURE_RUNNING
                procedure["held_by"] = None
            else:
                left_held.append(procedure_id)
        if left_held:
            findings.append(
                {"finding": FINDING_RESUME_LEFT_OWN_HOLDS, "procedures": left_held}
            )
    engine["state"] = target


def _apply_procedure_command(engine, name, procedure_id, findings):
    procedures = engine["procedures"]
    if name == COMMAND_LOAD:
        procedures.setdefault(
            procedure_id, {"state": PROCEDURE_LOADED, "held_by": None}
        )
        return
    procedure = procedures.get(procedure_id)
    if procedure is None:
        findings.append(
            {"finding": FINDING_UNKNOWN_PROCEDURE, "procedure_id": procedure_id}
        )
        return
    if name == COMMAND_ACTIVATE:
        if engine["state"] != ENGINE_RUNNING:
            findings.append(
                {
                    "finding": FINDING_ACTIVATION_WHILE_NOT_RUNNING,
                    "procedure_id": procedure_id,
                    "engine_state": engine["state"],
                }
            )
            return
        if procedure["state"] in (PROCEDURE_RUNNING, PROCEDURE_HELD):
            findings.append(
                {"finding": FINDING_ALREADY_ACTIVE, "procedure_id": procedure_id}
            )
            return
        if len(live_procedures(engine)) >= engine["capacity"]:
            findings.append(
                {"finding": FINDING_CAPACITY_REACHED, "procedure_id": procedure_id}
            )
            return
        procedure["state"] = PROCEDURE_RUNNING
        procedure["held_by"] = None
    elif name == COMMAND_HOLD_PROCEDURE:
        if procedure["state"] != PROCEDURE_RUNNING:
            findings.append(
                {"finding": FINDING_NOTHING_TO_HOLD, "procedure_id": procedure_id}
            )
            return
        procedure["state"] = PROCEDURE_HELD
        procedure["held_by"] = HELD_BY_COMMAND
    elif name == COMMAND_RESUME_PROCEDURE:
        if procedure["state"] == PROCEDURE_TERMINATED:
            findings.append(
                {
                    "finding": FINDING_TERMINATED_CANNOT_RESUME,
                    "procedure_id": procedure_id,
                }
            )
            return
        if procedure["state"] != PROCEDURE_HELD:
            findings.append(
                {"finding": FINDING_NOTHING_TO_RESUME, "procedure_id": procedure_id}
            )
            return
        if engine["state"] != ENGINE_RUNNING:
            findings.append(
                {
                    "finding": FINDING_ACTIVATION_WHILE_NOT_RUNNING,
                    "procedure_id": procedure_id,
                    "engine_state": engine["state"],
                }
            )
            return
        procedure["state"] = PROCEDURE_RUNNING
        procedure["held_by"] = None
    else:
        procedure["state"] = PROCEDURE_TERMINATED
        procedure["held_by"] = None


def apply_command(engine, raw, index=0):
    """Apply one engine or procedure command and report what it did."""
    if not isinstance(engine, dict) or "procedures" not in engine:
        raise ValueError("engine must be a new_engine result")
    command = _normalise_command(raw, index)
    findings = []
    if command["command"] in ENGINE_COMMANDS:
        _apply_engine_command(engine, command["command"], findings)
    else:
        _apply_procedure_command(
            engine, command["command"], command["procedure_id"], findings
        )
    return findings


def run_commands(engine, commands):
    """Apply a sequence of commands, collecting every finding in order."""
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list")
    findings = []
    for index, raw in enumerate(commands):
        for finding in apply_command(engine, raw, index):
            entry = dict(finding)
            entry["index"] = index
            findings.append(entry)
    return findings


def procedure_states(engine):
    """A name-to-state view of every procedure the engine knows about."""
    return {name: p["state"] for name, p in sorted(engine["procedures"].items())}


def assess_engine_control(commands, capacity=4, initial_state=ENGINE_STOPPED):
    """Replay a control sequence and grade what it did to the engine."""
    engine = new_engine(capacity=capacity, state=initial_state)
    findings = run_commands(engine, commands)
    states = procedure_states(engine)
    running = [n for n, s in states.items() if s == PROCEDURE_RUNNING]
    held = [n for n, s in states.items() if s == PROCEDURE_HELD]
    terminated = [n for n, s in states.items() if s == PROCEDURE_TERMINATED]
    return {
        "engine_state": engine["state"],
        "procedure_states": states,
        "running": sorted(running),
        "held": sorted(held),
        "terminated": sorted(terminated),
        "spare_capacity": engine["capacity"] - len(live_procedures(engine)),
        "findings": findings,
        "sequence_clean": not findings,
    }
