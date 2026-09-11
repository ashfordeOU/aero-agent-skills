#!/usr/bin/env python3
"""ECSS-E-ST-10C §5 Technical Specification establishment process
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
systems-engineering standard's TS establishment process runs in two
phases — phase-0 produces a preliminary Technical Specification through
four tasks (F1.1–F1.4): establish mission context, derive initial system
requirements, perform first-pass decomposition and requirement allocation,
and issue the preliminary TS; phase-A produces the phase-A Technical
Specification through six tasks (F1.5–F1.10): refine the functional
architecture, allocate performance budgets, define interface requirements,
conduct feasibility trade studies, iterate requirements at every
decomposition level until all open changes are resolved, then issue the
phase-A TS. Each task has explicit prerequisites; F1.6, F1.7, and F1.8
may run concurrently after F1.5 but all three must complete before F1.9
may start. Iteration at each decomposition level is not complete until
the open requirement change count at that level reaches zero. This module
implements task metadata, prerequisite checking, iteration convergence
tracking, phase completeness checking, and overall TS establishment
readiness assessment; it does not define the content of individual
requirements or the internal structure of the decomposition hierarchy.
"""

PHASE_0 = "phase_0"
PHASE_A = "phase_a"

# Task registry: id → (phase, short_description, list_of_prerequisite_ids)
_TASK_DEFS = {
    "F1.1": (
        PHASE_0,
        "establish mission context and top-level constraints",
        [],
    ),
    "F1.2": (
        PHASE_0,
        "derive initial system requirements from mission context",
        ["F1.1"],
    ),
    "F1.3": (
        PHASE_0,
        "perform first-pass system decomposition and allocate requirements to elements",
        ["F1.2"],
    ),
    "F1.4": (
        PHASE_0,
        "issue preliminary Technical Specification",
        ["F1.3"],
    ),
    "F1.5": (
        PHASE_A,
        "refine functional architecture and establish functional baseline",
        ["F1.4"],
    ),
    "F1.6": (
        PHASE_A,
        "allocate performance budgets to system elements",
        ["F1.5"],
    ),
    "F1.7": (
        PHASE_A,
        "define interface requirements at element boundaries",
        ["F1.5"],
    ),
    "F1.8": (
        PHASE_A,
        "conduct feasibility trade studies and record selected approach",
        ["F1.5"],
    ),
    "F1.9": (
        PHASE_A,
        "iterate requirements at each decomposition level until stable",
        ["F1.6", "F1.7", "F1.8"],
    ),
    "F1.10": (
        PHASE_A,
        "issue phase-A Technical Specification",
        ["F1.9"],
    ),
}

PHASE_0_TASKS = [tid for tid, (ph, _, _) in _TASK_DEFS.items() if ph == PHASE_0]
PHASE_A_TASKS = [tid for tid, (ph, _, _) in _TASK_DEFS.items() if ph == PHASE_A]
ALL_TASKS = list(_TASK_DEFS.keys())


def validate_task_id(task_id):
    """Raise ValueError if task_id is not a known TS establishment task."""
    if task_id not in _TASK_DEFS:
        raise ValueError(
            "unrecognized TS establishment task %r; known tasks: %s"
            % (task_id, sorted(_TASK_DEFS.keys()))
        )


def task_phase(task_id):
    """Phase of a task: PHASE_0 or PHASE_A.
    Raises ValueError for an unknown task_id."""
    validate_task_id(task_id)
    return _TASK_DEFS[task_id][0]


def task_prerequisites(task_id):
    """Prerequisite task IDs for a task (list, may be empty).
    Raises ValueError for an unknown task_id."""
    validate_task_id(task_id)
    return list(_TASK_DEFS[task_id][2])


def prerequisites_met(task_id, completed_task_ids):
    """True when every prerequisite of task_id appears in
    completed_task_ids. Raises ValueError for an unknown task_id."""
    validate_task_id(task_id)
    completed = set(completed_task_ids)
    return all(prereq in completed for prereq in _TASK_DEFS[task_id][2])


def blocking_tasks(task_id, completed_task_ids):
    """Prerequisite task IDs that are NOT yet in completed_task_ids,
    blocking the start of task_id. Returns an empty list when the task
    is ready to start. Raises ValueError for an unknown task_id."""
    validate_task_id(task_id)
    completed = set(completed_task_ids)
    return [p for p in _TASK_DEFS[task_id][2] if p not in completed]


def phase_complete(phase, completed_task_ids):
    """True when every task in the given phase is in completed_task_ids.
    Raises ValueError for an unrecognized phase name."""
    if phase == PHASE_0:
        tasks = PHASE_0_TASKS
    elif phase == PHASE_A:
        tasks = PHASE_A_TASKS
    else:
        raise ValueError(
            "unrecognized phase %r; expected %r or %r" % (phase, PHASE_0, PHASE_A)
        )
    completed = set(completed_task_ids)
    return all(t in completed for t in tasks)


def iteration_complete(open_change_count):
    """True when the open requirement change count at a decomposition
    level is zero (iteration has converged at that level).
    Raises ValueError for a negative count."""
    if open_change_count < 0:
        raise ValueError(
            "open_change_count must be >= 0; got %d" % (open_change_count,)
        )
    return open_change_count == 0


def ts_establishment_status(completed_task_ids, decomp_level_open_changes):
    """Overall TS establishment status.

    completed_task_ids: iterable of task ID strings that have been marked
        complete.
    decomp_level_open_changes: dict mapping decomposition level label
        (str) to its open requirement change count (int >= 0). An empty
        dict is treated as vacuously converged — the caller must register
        every level in use.

    Returns:
      {
        "phase_0_complete": bool,
        "phase_a_complete": bool,
        "all_levels_converged": bool,
        "unconverged_levels": [level, ...],   # levels with > 0 open changes
        "overall_ready": bool,                # True when all phases done and all levels converged
        "missing_tasks": [task_id, ...],      # tasks not yet in completed_task_ids
      }
    Raises ValueError for any open_change_count < 0.
    """
    completed = set(completed_task_ids)
    p0_done = phase_complete(PHASE_0, completed)
    pa_done = phase_complete(PHASE_A, completed)

    unconverged = []
    for level, count in decomp_level_open_changes.items():
        if count < 0:
            raise ValueError(
                "open_change_count for level %r must be >= 0; got %d" % (level, count)
            )
        if count > 0:
            unconverged.append(level)

    all_converged = len(unconverged) == 0
    missing = [t for t in ALL_TASKS if t not in completed]

    return {
        "phase_0_complete": p0_done,
        "phase_a_complete": pa_done,
        "all_levels_converged": all_converged,
        "unconverged_levels": sorted(unconverged),
        "overall_ready": p0_done and pa_done and all_converged,
        "missing_tasks": missing,
    }
