#!/usr/bin/env python3
"""ECSS-E-ST-10C per-phase system engineering task overview (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): E-ST-10C
lists, for each project lifecycle phase (0 through F), which system
engineering tasks are carried out and which generic outputs close the
phase. The concrete deliverable set for a given project is not fixed by
this task list alone -- the project's System Engineering Plan (SEP,
ECSS-E-ST-10C clause 5.1; see the sibling e10-sep leaf) tailors it. This
module tracks per-phase task completion against the generic task list; it
does not replace SEP tailoring and it does not track review-gate records
(see the sibling systems-engineering leaf for MDR/PRR/SRR/PDR/CDR/QR/AR/
FRR/CRR/ER gates).
"""

PHASE_TASKS = {
    "0": ("mission needs capture", "feasibility assessment", "top-level requirement drafting"),
    "A": ("system requirement definition", "concept trade-off", "preliminary specification tree"),
    "B": ("preliminary design definition", "requirement baseline freeze", "interface definition"),
    "C": ("detailed design definition", "verification planning", "requirement closure"),
    "D": ("qualification test execution", "acceptance test execution", "as-built documentation"),
    "E": ("in-orbit commissioning", "operational maintenance support", "anomaly resolution"),
    "F": ("disposal execution", "close-out reporting"),
}


def tasks_for(phase):
    """SE task tuple for a lifecycle phase (0 through F); unknown phases
    raise ValueError."""
    if phase not in PHASE_TASKS:
        raise ValueError("unknown ECSS lifecycle phase: %r" % (phase,))
    return PHASE_TASKS[phase]


def task_status(phase, task, done, waived):
    """Status of one task for a phase: 'done', 'waived', or 'open'. done
    and waived are iterables of task names for that phase. Raises
    ValueError if the task is not part of the phase's task list, or if a
    task is marked both done and waived."""
    if task not in tasks_for(phase):
        raise ValueError("task %r is not part of phase %r" % (task, phase))
    done_set = set(done)
    waived_set = set(waived)
    if task in done_set and task in waived_set:
        raise ValueError("task %r cannot be both done and waived" % (task,))
    if task in done_set:
        return "done"
    if task in waived_set:
        return "waived"
    return "open"


def phase_task_register(phase, done, waived):
    """(task, status) pairs for every task in the phase, in task-list
    order."""
    return [(t, task_status(phase, t, done, waived)) for t in tasks_for(phase)]


def phase_exit_ready(phase, done, waived):
    """Phase-exit readiness: (ready, open_tasks). ready is True only when
    no task is 'open' (every task is done or waived); open_tasks lists
    the outstanding ones in task-list order."""
    register = phase_task_register(phase, done, waived)
    open_tasks = [t for t, status in register if status == "open"]
    return (not open_tasks, open_tasks)
