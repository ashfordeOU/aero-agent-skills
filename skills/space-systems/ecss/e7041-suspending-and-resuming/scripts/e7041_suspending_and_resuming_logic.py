"""Suspending and resuming an on-board control procedure.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

What a suspension is. A running on-board control procedure can be told
to hold: stop where it is, keep everything it has, and wait to be
released. It is the operator's way of buying time without throwing away
a run -- a deployment paused while a telemetry anomaly is understood, a
calibration held while a ground station hands over.

A hold is not a stop. Stopping ends the run and the procedure would
have to start again from its first step. Holding keeps the step
pointer, the bound arguments and the engine slot, so releasing it
carries on from exactly where it paused. Every rule below exists to
protect that distinction.

Where a suspension takes effect. Not immediately -- at a step
boundary. A step is the unit the procedure was written in, and halting
half way through one leaves the spacecraft in a configuration the
procedure's author never described: a valve driven and not confirmed, a
heater commanded and not verified. So a suspend arriving mid-step is
pending, and lands when the current step completes.

The late suspend. If that step was the procedure's last, the run ends
before the hold can take effect. There is then nothing to release. The
honest report is that the procedure terminated and the suspend arrived
too late, never that it is suspended -- a ground waiting to resume
something that finished waits forever.

The cost of holding. A held procedure still owns its engine slot and
its store space. A hold with no bound on it is an engine slot lost
quietly, so a maximum hold is graded here and an over-run is a finding
the operator has to answer: release it or abort it.

Stdlib only, offline, deterministic.
"""

STATE_RUNNING = "running"
STATE_SUSPEND_PENDING = "suspend-pending-at-step-boundary"
STATE_SUSPENDED = "suspended"
STATE_TERMINATED = "terminated"
VALID_STATES = (
    STATE_RUNNING,
    STATE_SUSPEND_PENDING,
    STATE_SUSPENDED,
    STATE_TERMINATED,
)

OUTCOME_SUSPENDED = "suspended"
OUTCOME_SUSPEND_PENDING = "suspend-pending-until-step-completes"
OUTCOME_REFUSED_NOT_RUNNING = "refused-procedure-is-not-running"
OUTCOME_REFUSED_ALREADY_SUSPENDED = "refused-already-suspended"
OUTCOME_REFUSED_SUSPEND_ALREADY_PENDING = "refused-suspend-already-pending"

OUTCOME_RESUMED = "resumed-at-held-step"
OUTCOME_REFUSED_NOT_SUSPENDED = "refused-procedure-is-not-suspended"

OUTCOME_STEP_STARTED = "step-started"
OUTCOME_STEP_COMPLETED = "step-completed"
OUTCOME_SUSPEND_TOOK_EFFECT = "suspend-took-effect-at-step-boundary"
OUTCOME_TERMINATED_BEFORE_SUSPEND = "terminated-before-the-suspend-landed"
OUTCOME_TERMINATED = "terminated-on-its-last-step"
OUTCOME_REFUSED_NO_STEP_IN_PROGRESS = "refused-no-step-in-progress"
OUTCOME_REFUSED_STEP_ALREADY_IN_PROGRESS = "refused-step-already-in-progress"

HOLD_WITHIN_LIMIT = "hold-within-limit"
HOLD_OVER_LIMIT = "hold-over-limit-release-or-abort"
HOLD_NOT_HELD = "not-held"

EVENT_SUSPEND = "suspend"
EVENT_RESUME = "resume"
EVENT_COMPLETE_STEP = "complete-step"
EVENT_START_STEP = "start-step"
VALID_EVENTS = (
    EVENT_SUSPEND,
    EVENT_RESUME,
    EVENT_COMPLETE_STEP,
    EVENT_START_STEP,
)

ACCEPTING_OUTCOMES = (
    OUTCOME_STEP_STARTED,
    OUTCOME_SUSPENDED,
    OUTCOME_SUSPEND_PENDING,
    OUTCOME_RESUMED,
    OUTCOME_STEP_COMPLETED,
    OUTCOME_SUSPEND_TOOK_EFFECT,
    OUTCOME_TERMINATED_BEFORE_SUSPEND,
    OUTCOME_TERMINATED,
)


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_state(state):
    """Validate an instance state name and return it."""
    if state not in VALID_STATES:
        raise ValueError(
            "unknown execution state %r (expected one of %s)"
            % (state, ", ".join(VALID_STATES))
        )
    return state


def create_instance(proc_id, step_count, started_at=0):
    """Create a freshly started procedure instance sitting before step one."""
    name = _text("procedure id", proc_id)
    steps = _integer("procedure %s step_count" % name, step_count, 1)
    _integer("started_at", started_at, 0)
    return {
        "id": name,
        "step_count": steps,
        "state": STATE_RUNNING,
        "current_step": 1,
        "step_in_progress": False,
        "held_since": None,
        "held_at_step": None,
        "total_held_seconds": 0,
        "resume_count": 0,
        "started_at": started_at,
    }


def validate_instance(instance):
    """Validate a procedure instance and return an independent copy."""
    if not isinstance(instance, dict):
        raise ValueError("procedure instance must be a mapping")
    name = _text("procedure id", instance.get("id"))
    steps = _integer("procedure %s step_count" % name,
                     instance.get("step_count"), 1)
    state = validate_state(instance.get("state"))
    current = _integer("procedure %s current_step" % name,
                       instance.get("current_step"), 1)
    if current > steps + 1:
        raise ValueError(
            "procedure %s sits at step %d of %d" % (name, current, steps)
        )
    in_progress = _boolean("procedure %s step_in_progress" % name,
                           instance.get("step_in_progress", False))
    if state == STATE_SUSPENDED and in_progress:
        raise ValueError(
            "procedure %s is held with a step still in progress; a hold only "
            "ever lands on a step boundary" % name
        )
    if state == STATE_TERMINATED and in_progress:
        raise ValueError(
            "procedure %s has finished with a step still in progress" % name
        )
    held_since = instance.get("held_since")
    if held_since is not None:
        _integer("procedure %s held_since" % name, held_since, 0)
    if (state == STATE_SUSPENDED) != (held_since is not None):
        raise ValueError(
            "procedure %s records a hold start that does not match its state "
            "%s" % (name, state)
        )
    held_at_step = instance.get("held_at_step")
    if held_at_step is not None:
        _integer("procedure %s held_at_step" % name, held_at_step, 1)
    return {
        "id": name,
        "step_count": steps,
        "state": state,
        "current_step": current,
        "step_in_progress": in_progress,
        "held_since": held_since,
        "held_at_step": held_at_step,
        "total_held_seconds": _integer(
            "procedure %s total_held_seconds" % name,
            instance.get("total_held_seconds", 0), 0,
        ),
        "resume_count": _integer("procedure %s resume_count" % name,
                                 instance.get("resume_count", 0), 0),
        "started_at": _integer("procedure %s started_at" % name,
                               instance.get("started_at", 0), 0),
    }


def is_held(instance):
    """Is this procedure holding right now?"""
    return validate_instance(instance)["state"] == STATE_SUSPENDED


def owns_engine_slot(instance):
    """Does it still hold its engine slot? A hold does not give it back."""
    return validate_instance(instance)["state"] in (
        STATE_RUNNING, STATE_SUSPEND_PENDING, STATE_SUSPENDED
    )


def start_step(instance):
    """The engine begins the current step."""
    working = validate_instance(instance)
    if working["state"] != STATE_RUNNING:
        return working, OUTCOME_REFUSED_NOT_RUNNING
    if working["step_in_progress"]:
        return working, OUTCOME_REFUSED_STEP_ALREADY_IN_PROGRESS
    working["step_in_progress"] = True
    return working, OUTCOME_STEP_STARTED


def request_suspend(instance, now):
    """Ask a running procedure to hold; return the instance and the outcome."""
    working = validate_instance(instance)
    _integer("now", now, 0)
    if working["state"] == STATE_SUSPENDED:
        return working, OUTCOME_REFUSED_ALREADY_SUSPENDED
    if working["state"] == STATE_SUSPEND_PENDING:
        return working, OUTCOME_REFUSED_SUSPEND_ALREADY_PENDING
    if working["state"] != STATE_RUNNING:
        return working, OUTCOME_REFUSED_NOT_RUNNING
    if working["step_in_progress"]:
        # Halting mid-step would leave the spacecraft in a configuration
        # the procedure's author never described. The hold waits for the
        # boundary.
        working["state"] = STATE_SUSPEND_PENDING
        return working, OUTCOME_SUSPEND_PENDING
    working["state"] = STATE_SUSPENDED
    working["held_since"] = now
    working["held_at_step"] = working["current_step"]
    return working, OUTCOME_SUSPENDED


def complete_step(instance, now):
    """The engine finishes the current step, landing any pending hold."""
    working = validate_instance(instance)
    _integer("now", now, 0)
    if not working["step_in_progress"]:
        return working, OUTCOME_REFUSED_NO_STEP_IN_PROGRESS
    if working["state"] not in (STATE_RUNNING, STATE_SUSPEND_PENDING):
        return working, OUTCOME_REFUSED_NOT_RUNNING
    pending = working["state"] == STATE_SUSPEND_PENDING
    working["step_in_progress"] = False
    working["current_step"] += 1
    if working["current_step"] > working["step_count"]:
        working["state"] = STATE_TERMINATED
        # The run ended before the hold could land. There is nothing left
        # to release, and reporting it as suspended strands the ground.
        return working, (
            OUTCOME_TERMINATED_BEFORE_SUSPEND if pending else OUTCOME_TERMINATED
        )
    if pending:
        working["state"] = STATE_SUSPENDED
        working["held_since"] = now
        working["held_at_step"] = working["current_step"]
        return working, OUTCOME_SUSPEND_TOOK_EFFECT
    return working, OUTCOME_STEP_COMPLETED


def request_resume(instance, now):
    """Release a held procedure; it carries on from the step it held at."""
    working = validate_instance(instance)
    moment = _integer("now", now, 0)
    if working["state"] != STATE_SUSPENDED:
        return working, OUTCOME_REFUSED_NOT_SUSPENDED
    if moment < working["held_since"]:
        raise ValueError(
            "procedure %s cannot be released at %d, before it held at %d"
            % (working["id"], moment, working["held_since"])
        )
    working["total_held_seconds"] += moment - working["held_since"]
    working["state"] = STATE_RUNNING
    working["held_since"] = None
    working["held_at_step"] = None
    working["step_in_progress"] = False
    working["resume_count"] += 1
    return working, OUTCOME_RESUMED


def hold_duration(instance, now):
    """How long this procedure has been holding, right now."""
    working = validate_instance(instance)
    moment = _integer("now", now, 0)
    if working["state"] != STATE_SUSPENDED:
        return 0
    if moment < working["held_since"]:
        raise ValueError(
            "procedure %s cannot be inspected at %d, before it held at %d"
            % (working["id"], moment, working["held_since"])
        )
    return moment - working["held_since"]


def assess_hold(instance, now, max_hold_seconds):
    """Grade an open hold against the longest the mission allows."""
    working = validate_instance(instance)
    limit = _integer("max_hold_seconds", max_hold_seconds, 1)
    if working["state"] != STATE_SUSPENDED:
        return {
            "id": working["id"],
            "disposition": HOLD_NOT_HELD,
            "held_seconds": 0,
            "max_hold_seconds": limit,
            "remaining_seconds": limit,
            "held_at_step": None,
            "owns_engine_slot": owns_engine_slot(working),
        }
    held = hold_duration(working, now)
    return {
        "id": working["id"],
        "disposition": HOLD_OVER_LIMIT if held > limit else HOLD_WITHIN_LIMIT,
        "held_seconds": held,
        "max_hold_seconds": limit,
        "remaining_seconds": limit - held,
        "held_at_step": working["held_at_step"],
        "owns_engine_slot": True,
    }


def apply_events(instance, events):
    """Drive an instance through a timed event sequence."""
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    working = validate_instance(instance)
    results = []
    last_time = None
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be a mapping")
        kind = event.get("event")
        if kind not in VALID_EVENTS:
            raise ValueError(
                "unknown event %r (expected one of %s)"
                % (kind, ", ".join(VALID_EVENTS))
            )
        moment = _integer("event time", event.get("at", 0), 0)
        if last_time is not None and moment < last_time:
            raise ValueError(
                "event sequence for procedure %s goes backwards in time, "
                "from %d to %d" % (working["id"], last_time, moment)
            )
        last_time = moment
        if kind == EVENT_SUSPEND:
            working, outcome = request_suspend(working, moment)
        elif kind == EVENT_RESUME:
            working, outcome = request_resume(working, moment)
        elif kind == EVENT_START_STEP:
            working, outcome = start_step(working)
        else:
            working, outcome = complete_step(working, moment)
        results.append({
            "at": moment,
            "event": kind,
            "outcome": outcome,
            "state": working["state"],
            "current_step": working["current_step"],
            "accepted": outcome in ACCEPTING_OUTCOMES,
        })
    return working, results


def report_instance(instance, now=None):
    """Deterministic report of where one instance stands."""
    working = validate_instance(instance)
    held = hold_duration(working, now) if (
        now is not None and working["state"] == STATE_SUSPENDED
    ) else 0
    return {
        "id": working["id"],
        "state": working["state"],
        "current_step": working["current_step"],
        "step_count": working["step_count"],
        "steps_remaining": max(0, working["step_count"]
                               - working["current_step"] + 1),
        "step_in_progress": working["step_in_progress"],
        "held": working["state"] == STATE_SUSPENDED,
        "held_at_step": working["held_at_step"],
        "current_hold_seconds": held,
        "total_held_seconds": working["total_held_seconds"] + held,
        "resume_count": working["resume_count"],
        "owns_engine_slot": owns_engine_slot(working),
        "progress_fraction": (working["current_step"] - 1)
        / float(working["step_count"]),
    }
