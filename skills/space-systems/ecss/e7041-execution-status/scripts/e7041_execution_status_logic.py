"""Execution status of an on-board control procedure.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

What an execution status is. Every on-board control procedure the
spacecraft holds is in exactly one execution status at any moment, and
that single value is what the ground reasons with: whether the
procedure is aboard at all, whether it is running now, whether it is
holding, and if it is finished whether it finished the way it meant to.

This module does not move a procedure between statuses -- loading and
activation belong to the load-and-activate job, holding and releasing
to the suspend-and-resume job. What it does is the one thing clause
6.18.4.3 actually asks: settle what the status IS, from the facts the
engine can observe, and refuse to name a status for a combination of
facts that cannot happen.

The statuses:

  not-loaded          -- the procedure is not in the on-board store.
                         Nothing about it is executing and nothing can
                         be, whatever a stale ground model says.
  loaded-inactive     -- aboard and idle. It has either never been
                         started, or it was started, finished, and the
                         instance was cleared.
  active-running      -- the engine is executing it now.
  active-suspended    -- started, not finished, and holding. It still
                         owns its engine slot and its step pointer.
  terminated-completed -- it reached its end on its own terms.
  terminated-aborted  -- it stopped before its end, by command or by
                         fault.

Why derivation matters. A ground system that stores the status as a
free-standing field will, sooner or later, hold a status that
contradicts its own facts: suspended but never started, terminated with
no reason, running while not loaded. Deriving the status from the facts
turns every one of those into a raised error at the moment the
contradiction enters, instead of a decision made later on a value that
was never true.

Stdlib only, offline, deterministic.
"""

STATUS_NOT_LOADED = "not-loaded"
STATUS_LOADED_INACTIVE = "loaded-inactive"
STATUS_ACTIVE_RUNNING = "active-running"
STATUS_ACTIVE_SUSPENDED = "active-suspended"
STATUS_TERMINATED_COMPLETED = "terminated-completed"
STATUS_TERMINATED_ABORTED = "terminated-aborted"

VALID_STATUSES = (
    STATUS_NOT_LOADED,
    STATUS_LOADED_INACTIVE,
    STATUS_ACTIVE_RUNNING,
    STATUS_ACTIVE_SUSPENDED,
    STATUS_TERMINATED_COMPLETED,
    STATUS_TERMINATED_ABORTED,
)

TERMINATION_COMPLETED = "completed"
TERMINATION_ABORTED = "aborted"
VALID_TERMINATION_REASONS = (TERMINATION_COMPLETED, TERMINATION_ABORTED)

CATEGORY_ABSENT = "absent"
CATEGORY_IDLE = "idle"
CATEGORY_EXECUTING = "executing"
CATEGORY_TERMINAL = "terminal"

STATUS_CATEGORY = {
    STATUS_NOT_LOADED: CATEGORY_ABSENT,
    STATUS_LOADED_INACTIVE: CATEGORY_IDLE,
    STATUS_ACTIVE_RUNNING: CATEGORY_EXECUTING,
    STATUS_ACTIVE_SUSPENDED: CATEGORY_EXECUTING,
    STATUS_TERMINATED_COMPLETED: CATEGORY_TERMINAL,
    STATUS_TERMINATED_ABORTED: CATEGORY_TERMINAL,
}

# A running or holding procedure owns an engine slot; a finished or idle
# one does not. Suspended still counts -- that is the whole cost of a
# hold.
SLOT_OWNING_STATUSES = (STATUS_ACTIVE_RUNNING, STATUS_ACTIVE_SUSPENDED)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_status(status):
    """Validate an execution status name and return it."""
    if status not in VALID_STATUSES:
        raise ValueError(
            "unknown execution status %r (expected one of %s)"
            % (status, ", ".join(VALID_STATUSES))
        )
    return status


def status_category(status):
    """Group a status into absent, idle, executing or terminal."""
    return STATUS_CATEGORY[validate_status(status)]


def is_terminal(status):
    """Has this procedure finished, either way?"""
    return status_category(status) == CATEGORY_TERMINAL


def is_executing(status):
    """Is this procedure started and not yet finished?"""
    return status_category(status) == CATEGORY_EXECUTING


def owns_engine_slot(status):
    """Does this status hold an engine slot against the concurrency limit?"""
    return validate_status(status) in SLOT_OWNING_STATUSES


def validate_facts(facts):
    """Validate the observable facts about one procedure and normalize them."""
    if not isinstance(facts, dict):
        raise ValueError("execution facts must be a mapping")
    proc_id = facts.get("id")
    if not isinstance(proc_id, str) or not proc_id.strip():
        raise ValueError("execution facts need a non-empty string id")
    normalized = {
        "id": proc_id.strip(),
        "loaded": _boolean("procedure %s loaded" % proc_id,
                           facts.get("loaded", False)),
        "started": _boolean("procedure %s started" % proc_id,
                            facts.get("started", False)),
        "suspended": _boolean("procedure %s suspended" % proc_id,
                              facts.get("suspended", False)),
        "terminated": _boolean("procedure %s terminated" % proc_id,
                               facts.get("terminated", False)),
    }
    reason = facts.get("termination_reason")
    if reason is not None and reason not in VALID_TERMINATION_REASONS:
        raise ValueError(
            "procedure %s has unknown termination reason %r"
            % (normalized["id"], reason)
        )
    normalized["termination_reason"] = reason
    return normalized


def contradictions(facts):
    """Every way this set of facts fails to describe a real procedure."""
    working = validate_facts(facts)
    found = []
    if not working["loaded"] and (
        working["started"] or working["suspended"] or working["terminated"]
    ):
        found.append(
            "procedure %s is not loaded yet carries execution history; "
            "nothing that is not aboard can have run" % working["id"]
        )
    if working["suspended"] and not working["started"]:
        found.append(
            "procedure %s is held but was never started; a hold needs "
            "something to hold" % working["id"]
        )
    if working["suspended"] and working["terminated"]:
        found.append(
            "procedure %s is both holding and finished; a finished "
            "procedure has nothing left to release" % working["id"]
        )
    if working["terminated"] and not working["started"]:
        found.append(
            "procedure %s finished without ever starting" % working["id"]
        )
    if working["terminated"] and working["termination_reason"] is None:
        found.append(
            "procedure %s is finished with no reason recorded; completed and "
            "aborted are different outcomes and the difference is the report"
            % working["id"]
        )
    if not working["terminated"] and working["termination_reason"] is not None:
        found.append(
            "procedure %s records a termination reason while still running"
            % working["id"]
        )
    return found


def derive_execution_status(facts):
    """Settle the one execution status these facts describe."""
    working = validate_facts(facts)
    found = contradictions(working)
    if found:
        raise ValueError(
            "procedure %s has contradictory execution facts: %s"
            % (working["id"], "; ".join(found))
        )
    if not working["loaded"]:
        return STATUS_NOT_LOADED
    if working["terminated"]:
        if working["termination_reason"] == TERMINATION_COMPLETED:
            return STATUS_TERMINATED_COMPLETED
        return STATUS_TERMINATED_ABORTED
    if working["suspended"]:
        return STATUS_ACTIVE_SUSPENDED
    if working["started"]:
        return STATUS_ACTIVE_RUNNING
    return STATUS_LOADED_INACTIVE


def facts_are_consistent(facts):
    """Do these facts describe a procedure that could exist?"""
    return not contradictions(facts)


def reconcile_reported_status(reported, facts):
    """Compare a status the ground holds against the facts aboard."""
    working = validate_facts(facts)
    declared = validate_status(reported)
    derived = derive_execution_status(working)
    return {
        "id": working["id"],
        "reported_status": declared,
        "derived_status": derived,
        "agrees": declared == derived,
        "reported_category": status_category(declared),
        "derived_category": status_category(derived),
        "category_agrees": status_category(declared) == status_category(derived),
        "note": (
            "agreed"
            if declared == derived
            else "ground holds %s, the facts aboard say %s"
            % (declared, derived)
        ),
    }


def summarize_status_set(records):
    """Derive, group and count the execution status of a set of procedures."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    seen = set()
    derived = []
    for record in records:
        working = validate_facts(record)
        if working["id"] in seen:
            raise ValueError("duplicate procedure id %r" % (working["id"],))
        seen.add(working["id"])
        status = derive_execution_status(working)
        derived.append({"id": working["id"], "status": status,
                        "category": status_category(status)})
    grouped_by_status = {}
    grouped_by_category = {}
    for entry in derived:
        grouped_by_status.setdefault(entry["status"], []).append(entry["id"])
        grouped_by_category.setdefault(entry["category"], []).append(
            entry["id"]
        )
    return {
        "entries": derived,
        "grouped_by_status": grouped_by_status,
        "grouped_by_category": grouped_by_category,
        "counts_by_status": {
            status: len(grouped_by_status.get(status, []))
            for status in VALID_STATUSES
        },
        "executing_count": len(grouped_by_category.get(CATEGORY_EXECUTING, [])),
        "terminal_count": len(grouped_by_category.get(CATEGORY_TERMINAL, [])),
        "slot_owning_count": sum(
            1 for entry in derived if owns_engine_slot(entry["status"])
        ),
        "aborted_count": len(
            grouped_by_status.get(STATUS_TERMINATED_ABORTED, [])
        ),
    }


def assess_engine_slot_demand(records, max_concurrent):
    """Check derived statuses against the engine's concurrency limit."""
    limit = _integer("max_concurrent", max_concurrent, 1)
    summary = summarize_status_set(records)
    demand = summary["slot_owning_count"]
    return {
        "max_concurrent": limit,
        "slot_owning_count": demand,
        "free_slots": limit - demand,
        "over_limit": demand > limit,
        "slot_owners": [
            entry["id"] for entry in summary["entries"]
            if owns_engine_slot(entry["status"])
        ],
        "summary": summary,
    }
