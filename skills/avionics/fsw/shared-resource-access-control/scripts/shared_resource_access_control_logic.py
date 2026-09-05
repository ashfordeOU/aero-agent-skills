"""Shared-resource access control for fixed-priority avionics task sets.

Pure Python stdlib, deterministic, no network. Implements the classic
priority ceiling protocol (PCP) blocking model and the response-time
analysis extended with the blocking term:

- priority_ceiling(tasks, locks): per-resource ceiling, the highest
  priority among the tasks that lock the resource.
- resource_ceiling(tasks, locks, resource): single-resource ceiling.
- worst_case_blocking(task, tasks, locks): the longest critical section
  of any lower-priority task that locks a resource whose ceiling is at
  least the task's priority (the ceiling rule: at most one such
  lower-priority critical section can block the task under PCP).
- blocking_times(tasks, locks): per-task worst-case blocking map.
- response_time_with_blocking(task, tasks, locks): fixed-point
  R_i = C_i + B_i + sum over higher-priority j of
  ceil(R_i / T_j) * C_j, iterated from C_i + B_i until convergence or
  the 100-iteration cap.
- rta_with_blocking_feasibility(tasks, locks): dict with keys
  blocking, response_times and feasible (feasible iff every response
  time is at most its task period).

Conventions: a task is a dict {name, C, T, priority} with implicit
deadline D = T (C and T in one time unit; higher number = higher
priority). The task set is a dict {name: {C, T, priority}} or a list of
task dicts (names must be unique). A resource lock is a dict
{resource, task, cs} where cs is the task's longest critical-section
time on that resource, in the same time unit as C. The priority ceiling
of a resource is the highest priority among the tasks that lock it.

API note: the two ceiling helpers and the per-task helpers take the
task registry alongside the lock list, because ceilings and the
lower-priority test need task priorities; outputs match the spec
anchors exactly. Equal-priority tasks are incomparable (strictly
higher / strictly lower only), so ties neither preempt nor block.
Module constants: MAX_RTA_ITERATIONS = 100 (spec cap) and _EPS for the
feasibility comparison.
"""

import math

# Fixed-point cap from the leaf spec: iterate at most 100 times.
MAX_RTA_ITERATIONS = 100
# Feasibility slack: a response time must not exceed its period by more
# than this relative amount to count as within the period.
_EPS = 1e-9


def _task_registry(tasks):
    """Validate a task set and return {name: task} preserving order.

    Accepts a dict {name: {C, T, priority}} or a list of task dicts.
    Raises ValueError on an empty set, a malformed or duplicate task
    name, non-numeric or non-finite C, T or priority, C <= 0, T <= 0,
    C > T, or a boolean where a number is required.
    """
    if isinstance(tasks, dict):
        items = list(tasks.items())
    elif isinstance(tasks, (list, tuple)):
        items = []
        for entry in tasks:
            if not isinstance(entry, dict) or "name" not in entry:
                raise ValueError(
                    "each task in a list must be a dict with a name key"
                )
            items.append((entry["name"], entry))
    else:
        raise ValueError("task set must be a dict or a list of task dicts")
    if len(items) == 0:
        raise ValueError("task set must not be empty")
    registry = {}
    for name, record in items:
        if not isinstance(name, str) or name == "":
            raise ValueError("task name must be a non-empty string")
        if name in registry:
            raise ValueError("duplicate task name: %s" % name)
        if not isinstance(record, dict):
            raise ValueError("task %s must be a dict" % name)
        missing = set(("C", "T", "priority")) - set(record)
        if missing:
            raise ValueError("task %s lacks keys %s" % (name, sorted(missing)))
        c = record["C"]
        t = record["T"]
        p = record["priority"]
        for label, value in (("C", c), ("T", t), ("priority", p)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    "%s of task %s must be a real number" % (label, name)
                )
            if not math.isfinite(float(value)):
                raise ValueError("%s of task %s must be finite" % (label, name))
        if c <= 0.0 or t <= 0.0:
            raise ValueError(
                "execution time C and period T of task %s must be "
                "positive" % name
            )
        if c > t:
            raise ValueError(
                "execution time C of task %s exceeds its period T" % name
            )
        registry[name] = {
            "C": float(c),
            "T": float(t),
            "priority": float(p),
        }
    return registry


def _validate_locks(tasks, locks, allow_empty):
    """Validate a lock list against a task registry.

    Returns a normalized list of (resource, task, cs) tuples. Raises
    ValueError on a non-list, on an empty list when allow_empty is
    False, on a malformed lock, on a lock referencing an unknown task,
    on a non-finite or negative cs, and on a boolean cs.
    """
    if not isinstance(locks, (list, tuple)):
        raise ValueError("locks must be a list of lock dicts")
    if len(locks) == 0:
        if not allow_empty:
            raise ValueError("lock list must not be empty")
        return []
    normalized = []
    for lock in locks:
        if not isinstance(lock, dict):
            raise ValueError("each lock must be a dict")
        missing = set(("resource", "task", "cs")) - set(lock)
        if missing:
            raise ValueError("lock lacks keys %s" % sorted(missing))
        resource = lock["resource"]
        task = lock["task"]
        cs = lock["cs"]
        if not isinstance(resource, str) or resource == "":
            raise ValueError("resource name must be a non-empty string")
        if task not in tasks:
            raise ValueError("lock references unknown task %r" % (task,))
        if isinstance(cs, bool) or not isinstance(cs, (int, float)):
            raise ValueError("cs of a lock must be a real number")
        if not math.isfinite(float(cs)):
            raise ValueError("cs of a lock must be finite")
        if cs < 0.0:
            raise ValueError("critical section cs must not be negative")
        normalized.append((resource, task, float(cs)))
    return normalized


def _ceiling_map(tasks, locks):
    """Return {resource: ceiling priority} for a validated lock list."""
    ceiling = {}
    for resource, task, _cs in locks:
        priority = tasks[task]["priority"]
        if resource not in ceiling or priority > ceiling[resource]:
            ceiling[resource] = priority
    return ceiling


def priority_ceiling(tasks, locks):
    """Return {resource: ceiling priority} over the tasks that lock it.

    The ceiling of a resource is the highest priority among the tasks
    that lock it. Raises ValueError on an invalid task set, an empty
    lock list, or a lock referencing an unknown task.
    """
    registry = _task_registry(tasks)
    normalized = _validate_locks(registry, locks, allow_empty=False)
    return _ceiling_map(registry, normalized)


def resource_ceiling(tasks, locks, resource):
    """Return the ceiling priority of one resource.

    Raises ValueError when the resource is not locked by any task.
    """
    registry = _task_registry(tasks)
    normalized = _validate_locks(registry, locks, allow_empty=False)
    if not isinstance(resource, str) or resource == "":
        raise ValueError("resource name must be a non-empty string")
    ceiling = _ceiling_map(registry, normalized)
    if resource not in ceiling:
        raise ValueError("resource %r is not locked by any task" % resource)
    return ceiling[resource]


def _hp_names(registry, priority):
    """Names of tasks with strictly higher priority than the given one."""
    return [
        name
        for name, record in registry.items()
        if record["priority"] > priority
    ]


def worst_case_blocking(task, tasks, locks):
    """Return the worst-case blocking time of one task under PCP.

    The task can be blocked by at most one lower-priority task's
    critical section: the result is the longest cs of any lower-priority
    task that locks a resource whose ceiling is at least the task's
    priority (the ceiling rule). Zero when no such section exists.
    """
    registry = _task_registry(tasks)
    normalized = _validate_locks(registry, locks, allow_empty=True)
    if task not in registry:
        raise ValueError("unknown task %r" % (task,))
    priority = registry[task]["priority"]
    ceiling = _ceiling_map(registry, normalized)
    best = 0.0
    for lock_task in registry:
        if registry[lock_task]["priority"] >= priority:
            continue  # only strictly lower-priority tasks can block
        for resource, lock_task_name, cs in normalized:
            if lock_task_name != lock_task:
                continue
            if ceiling.get(resource, -math.inf) >= priority:
                best = max(best, cs)
    return best


def blocking_times(tasks, locks):
    """Return {task name: worst-case blocking time} for every task."""
    registry = _task_registry(tasks)
    _validate_locks(registry, locks, allow_empty=True)
    return {name: worst_case_blocking(name, registry, locks)
            for name in registry}


def response_time_with_blocking(task, tasks, locks):
    """Return the response time of one task including the blocking term.

    Fixed point of R_i = C_i + B_i + sum over higher-priority tasks j of
    ceil(R_i / T_j) * C_j, iterated from C_i + B_i until the value stops
    changing or the MAX_RTA_ITERATIONS cap (100) is reached. The
    iteration is monotone non-decreasing, so on an overloaded set the
    capped value grows far past the period and feasibility fails.
    """
    registry = _task_registry(tasks)
    _validate_locks(registry, locks, allow_empty=True)
    if task not in registry:
        raise ValueError("unknown task %r" % (task,))
    record = registry[task]
    c = record["C"]
    t = record["T"]
    priority = record["priority"]
    hp = [
        (registry[name]["C"], registry[name]["T"])
        for name in _hp_names(registry, priority)
    ]
    blocking = worst_case_blocking(task, registry, locks)
    response = c + blocking
    for _ in range(MAX_RTA_ITERATIONS):
        total = blocking + sum(
            math.ceil(response / period) * exec_time
            for exec_time, period in hp
        )
        updated = c + total
        if updated == response:
            break
        response = updated
    return response


def rta_with_blocking_feasibility(tasks, locks):
    """Return blocking, response times and the schedulability verdict.

    Dict keys are exactly blocking, response_times and feasible;
    feasible is True iff every response time is at most its task
    period (within _EPS). An empty lock list gives zero blocking, so
    the response times then equal the plain response-time analysis.
    """
    registry = _task_registry(tasks)
    _validate_locks(registry, locks, allow_empty=True)
    blocking = {name: worst_case_blocking(name, registry, locks)
                for name in registry}
    response_times = {
        name: response_time_with_blocking(name, registry, locks)
        for name in registry
    }
    feasible = all(
        response_times[name] <= registry[name]["T"] * (1.0 + _EPS)
        for name in registry
    )
    return {
        "blocking": blocking,
        "response_times": response_times,
        "feasible": feasible,
    }
