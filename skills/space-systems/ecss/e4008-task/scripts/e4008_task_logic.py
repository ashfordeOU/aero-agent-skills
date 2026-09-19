#!/usr/bin/env python3
"""Tasks in an SMP schedule artefact.

Anchor: ECSS-E-ST-40-08C clause 5.4.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A task is the unit a schedule entry actually triggers. It carries an
ordered list of steps -- activities, and invocations of other tasks --
and it runs all of them at one scheduling point.

The clause's normative items reduce to three implementable checks:

    1  a task is named, the name is unique in the schedule, the task
       holds at least one step, and the steps run in declared order
    2  a task runs as one unit at a single point on the time line: no
       step advances simulated time and no step blocks, so nothing
       can interleave between two steps of the same task
    3  every task invocation and every schedule entry resolves to a
       declared task, and no chain of invocations reaches back to a
       task already on the chain

The third check is the one that needs real work. Task invocation is
transitive, so a schedule can be built entirely out of individually
sensible tasks and still contain a cycle that no single task reveals.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

STEP_ACTIVITY = "activity"
STEP_TASK = "task"
STEP_KINDS = (STEP_ACTIVITY, STEP_TASK)

VERDICT_SCHEDULABLE = "task-set-schedulable"
VERDICT_REJECTED = "task-set-rejected"

FINDING_TASK_UNNAMED = "task-name-missing"
FINDING_TASK_DUPLICATE = "task-name-duplicate"
FINDING_TASK_EMPTY = "task-has-no-steps"
FINDING_STEP_KIND = "step-kind-unknown"
FINDING_STEP_UNNAMED = "step-name-missing"
FINDING_ACTIVITY_DUPLICATE = "activity-name-duplicate-in-task"
FINDING_TASK_UNRESOLVED = "task-invocation-unresolved"
FINDING_TASK_CYCLE = "task-invocation-cycle"
FINDING_ADVANCES_TIME = "step-advances-simulated-time"
FINDING_BLOCKING = "step-blocks-the-scheduler"
FINDING_ENTRY_UNRESOLVED = "entry-names-an-undeclared-task"

# Findings that make a flattened execution order undefined rather than
# merely wrong: the expansion cannot be produced at all while one stands.
UNSAFE_FOR_EXPANSION = (
    FINDING_TASK_UNNAMED,
    FINDING_TASK_CYCLE,
    FINDING_TASK_UNRESOLVED,
    FINDING_STEP_KIND,
    FINDING_STEP_UNNAMED,
)


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (name, value))
    return list(value)


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _text_or_none(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _finding(code, detail):
    return {"code": code, "detail": detail}


def index_tasks(tasks):
    """Build a name to task index, reporting unnamed and repeated names."""
    entries = _require_sequence("tasks", tasks)
    if not entries:
        raise ValueError("a schedule with no tasks has nothing to trigger")
    index = {}
    findings = []
    for position, raw in enumerate(entries):
        _require_mapping("task", raw)
        name = _text_or_none(raw.get("name"))
        if name is None:
            findings.append(_finding(FINDING_TASK_UNNAMED, "task at position %d" % position))
            continue
        if name in index:
            findings.append(_finding(FINDING_TASK_DUPLICATE, name))
            continue
        index[name] = raw
    return index, findings


def task_steps(task):
    """The declared step list of one task, in order."""
    _require_mapping("task", task)
    return _require_sequence("task steps", task.get("steps", []))


def invoked_tasks(task):
    """Names of the tasks one task invokes, in declared order."""
    names = []
    for step in task_steps(task):
        _require_mapping("step", step)
        if step.get("kind") == STEP_TASK:
            name = _text_or_none(step.get("target"))
            if name is not None:
                names.append(name)
    return names


def execution_order(task_name, index, _chain=None):
    """Flattened activity order a task produces when it is triggered.

    Nested task invocations are expanded in place, which is what makes
    the order a single sequence. A chain that reaches a task already
    being expanded raises: the expansion would not terminate, and a
    truncated answer would look like a valid order.
    """
    chain = list(_chain or [])
    if task_name in chain:
        raise ValueError(
            "task invocation cycle: %s" % " -> ".join(chain + [task_name])
        )
    task = index.get(task_name)
    if task is None:
        raise ValueError("task %r is not declared in this schedule" % (task_name,))
    chain.append(task_name)
    order = []
    for step in task_steps(task):
        _require_mapping("step", step)
        kind = step.get("kind")
        if kind == STEP_ACTIVITY:
            label = _text_or_none(step.get("name"))
            if label is None:
                raise ValueError("an activity step in task %r has no name" % task_name)
            order.append("%s/%s" % (task_name, label))
        elif kind == STEP_TASK:
            target = _text_or_none(step.get("target"))
            if target is None:
                raise ValueError("a task step in task %r names no target" % task_name)
            order.extend(execution_order(target, index, chain))
        else:
            raise ValueError(
                "step kind must be one of %s, got %r" % (", ".join(STEP_KINDS), kind)
            )
    return order


def find_invocation_cycles(index):
    """Every task invocation cycle reachable in the schedule, deduplicated."""
    cycles = []
    seen = set()

    def walk(name, chain):
        if name in chain:
            start = chain.index(name)
            cycle = chain[start:] + [name]
            key = tuple(sorted(set(cycle)))
            if key not in seen:
                seen.add(key)
                cycles.append(cycle)
            return
        task = index.get(name)
        if task is None:
            return
        for target in invoked_tasks(task):
            walk(target, chain + [name])

    for name in sorted(index):
        walk(name, [])
    return cycles


def evaluate_task_set(tasks, entries=None):
    """Full clause 5.4.4 check over a schedule's tasks, with a verdict."""
    index, findings = index_tasks(tasks)
    findings = list(findings)

    for name in sorted(index):
        task = index[name]
        steps = task_steps(task)
        if not steps:
            findings.append(_finding(FINDING_TASK_EMPTY, name))
            continue
        activity_names = set()
        for position, step in enumerate(steps):
            _require_mapping("step", step)
            label = "%s[%d]" % (name, position)
            kind = step.get("kind")
            if kind not in STEP_KINDS:
                findings.append(_finding(FINDING_STEP_KIND, "%s -> %r" % (label, kind)))
                continue
            duration = step.get("duration_ns", 0)
            if isinstance(duration, bool) or not isinstance(duration, int):
                raise ValueError("%s duration_ns must be an integer" % label)
            if duration != 0:
                findings.append(_finding(FINDING_ADVANCES_TIME, "%s by %d ns" % (label, duration)))
            if step.get("blocking", False):
                findings.append(_finding(FINDING_BLOCKING, label))
            if kind == STEP_ACTIVITY:
                activity = _text_or_none(step.get("name"))
                if activity is None:
                    findings.append(_finding(FINDING_STEP_UNNAMED, label))
                    continue
                if activity in activity_names:
                    findings.append(
                        _finding(FINDING_ACTIVITY_DUPLICATE, "%s/%s" % (name, activity))
                    )
                activity_names.add(activity)
            else:
                target = _text_or_none(step.get("target"))
                if target is None:
                    findings.append(_finding(FINDING_STEP_UNNAMED, label))
                elif target not in index:
                    findings.append(
                        _finding(FINDING_TASK_UNRESOLVED, "%s -> %s" % (label, target))
                    )

    for cycle in find_invocation_cycles(index):
        findings.append(_finding(FINDING_TASK_CYCLE, " -> ".join(cycle)))

    triggered = []
    for position, entry in enumerate(_require_sequence("entries", entries or [])):
        _require_mapping("entry", entry)
        target = _text_or_none(entry.get("task"))
        label = _text_or_none(entry.get("name")) or "entry at position %d" % position
        if target is None or target not in index:
            findings.append(_finding(FINDING_ENTRY_UNRESOLVED, "%s -> %s" % (label, target)))
            continue
        triggered.append(target)

    reached = set()
    if not any(item["code"] == FINDING_TASK_CYCLE for item in findings):
        stack = list(triggered)
        while stack:
            name = stack.pop()
            task = index.get(name)
            if name in reached or task is None:
                continue
            reached.add(name)
            stack.extend(invoked_tasks(task))

    orders = {}
    if not any(item["code"] in UNSAFE_FOR_EXPANSION for item in findings):
        for name in sorted(index):
            if index[name].get("steps"):
                orders[name] = execution_order(name, index)

    return {
        "verdict": VERDICT_SCHEDULABLE if not findings else VERDICT_REJECTED,
        "schedulable": not findings,
        "task_names": sorted(index),
        "execution_orders": orders,
        "triggered_tasks": sorted(set(triggered)),
        "unreachable_tasks": sorted(set(index) - reached),
        "findings": findings,
        "finding_codes": sorted({item["code"] for item in findings}),
    }
