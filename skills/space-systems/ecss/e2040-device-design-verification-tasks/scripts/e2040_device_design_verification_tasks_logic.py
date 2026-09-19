#!/usr/bin/env python3
"""Design and verification phase tasks (ECSS-E-ST-20-40C clause 5.4.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause puts two kinds of activity on the supplier during the design
and verification phase, and the useful checks run between them rather
than inside either one:

* an engineering task produces exactly one named design item;
* a checking task examines one or more items that some engineering task
  produced. A task doing both at once is a description of work rather
  than a task, and it hides which half slipped;
* prerequisites order the set. A prerequisite loop leaves nothing to
  schedule, so it is refused as an input defect;
* a task is complete only when its prerequisites are complete and it
  carries evidence. Either one alone records an opinion;
* verification coverage is the fraction of produced items that at least
  one checking task examines. A threshold met exactly is met, so the
  comparison absorbs representation error rather than failing on the
  last bit of a division.
"""

import math

ENGINEERING = "engineering"
CHECKING = "checking"
TASK_KINDS = (ENGINEERING, CHECKING)
_KIND_ALIASES = {
    "engineering": ENGINEERING,
    "design": ENGINEERING,
    "design task": ENGINEERING,
    "develop": ENGINEERING,
    "e": ENGINEERING,
    "checking": CHECKING,
    "check": CHECKING,
    "verification": CHECKING,
    "verification task": CHECKING,
    "v": CHECKING,
}

PLANNED = "planned"
IN_PROGRESS = "in-progress"
COMPLETE = "complete"
TASK_STATUSES = (PLANNED, IN_PROGRESS, COMPLETE)
_STATUS_ALIASES = {
    "planned": PLANNED,
    "open": PLANNED,
    "not started": PLANNED,
    "in-progress": IN_PROGRESS,
    "in progress": IN_PROGRESS,
    "running": IN_PROGRESS,
    "ongoing": IN_PROGRESS,
    "complete": COMPLETE,
    "completed": COMPLETE,
    "closed": COMPLETE,
    "done": COMPLETE,
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_TASK_KEYS = ("id", "kind", "produces", "examines", "prerequisites", "evidence", "status")
_PHASE_REQUIRED_KEYS = ("tasks",)
_PHASE_OPTIONAL_KEYS = ("coverage_threshold",)


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_coverage_threshold(achieved, threshold):
    """True when achieved coverage reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_task_kind(value):
    """Fold a task kind spelling onto engineering or checking."""
    key = " ".join(_text("kind", value).lower().replace("_", " ").split())
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    raise ValueError(
        "unknown task kind %r; use one of %s" % (value, ", ".join(TASK_KINDS))
    )


def normalize_status(value):
    """Fold a task status spelling onto the three recognised states."""
    key = " ".join(_text("status", value).lower().replace("_", " ").split())
    key = key.replace("in progress", "in-progress")
    if key in _STATUS_ALIASES:
        return _STATUS_ALIASES[key]
    raise ValueError(
        "unknown task status %r; use one of %s" % (value, ", ".join(TASK_STATUSES))
    )


def _string_list(name, value):
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of strings" % name)
    out = []
    for index, item in enumerate(value):
        text = _text("%s[%d]" % (name, index), item)
        if text not in out:
            out.append(text)
    return out


def validate_tasks(entries):
    """Check the task list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("tasks must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("tasks[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_TASK_KEYS))
        if unknown:
            raise ValueError(
                "tasks[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind"):
            if key not in entry:
                raise ValueError("tasks[%d] missing key: %s" % (index, key))
        task_id = _text("tasks[%d].id" % index, entry["id"])
        if task_id in seen:
            raise ValueError("duplicate task id %r" % task_id)
        seen.add(task_id)
        kind = normalize_task_kind(entry["kind"])
        produces = _text(
            "tasks[%d].produces" % index, entry.get("produces", ""), allow_empty=True
        )
        examines = _string_list("tasks[%d].examines" % index, entry.get("examines"))
        if produces and examines:
            raise ValueError(
                "task %r both produces %r and examines %s; split it into an "
                "engineering task and a checking task"
                % (task_id, produces, ", ".join(examines))
            )
        resolved.append(
            {
                "id": task_id,
                "kind": kind,
                "produces": produces,
                "examines": examines,
                "prerequisites": _string_list(
                    "tasks[%d].prerequisites" % index, entry.get("prerequisites")
                ),
                "evidence": _text(
                    "tasks[%d].evidence" % index,
                    entry.get("evidence", ""),
                    allow_empty=True,
                ),
                "status": normalize_status(entry.get("status", PLANNED)),
            }
        )
    return resolved


def order_tasks(tasks):
    """Task ids in an order every prerequisite respects.

    Raises on a prerequisite naming no task and on a prerequisite cycle:
    neither leaves anything to schedule.
    """
    known = {task["id"] for task in tasks}
    remaining = {task["id"]: list(task["prerequisites"]) for task in tasks}
    for task in tasks:
        for prerequisite in task["prerequisites"]:
            if prerequisite == task["id"]:
                raise ValueError("task %r is its own prerequisite" % task["id"])
            if prerequisite not in known:
                raise ValueError(
                    "task %r names prerequisite %r, which is not a task"
                    % (task["id"], prerequisite)
                )
    order = []
    declared = [task["id"] for task in tasks]
    while remaining:
        ready = [tid for tid in declared if tid in remaining and not remaining[tid]]
        if not ready:
            raise ValueError(
                "prerequisite cycle among tasks: %s" % ", ".join(sorted(remaining))
            )
        for tid in ready:
            order.append(tid)
            del remaining[tid]
        for pending in remaining.values():
            for tid in ready:
                if tid in pending:
                    pending.remove(tid)
    return order


def produced_items(tasks):
    """Design items the engineering tasks produce, in declared order."""
    out = []
    for task in tasks:
        if task["kind"] == ENGINEERING and task["produces"] and task["produces"] not in out:
            out.append(task["produces"])
    return out


def examined_items(tasks):
    """Design items at least one checking task examines."""
    out = set()
    for task in tasks:
        if task["kind"] == CHECKING:
            out.update(task["examines"])
    return out


def unexamined_items(tasks):
    """Produced design items no checking task examines."""
    examined = examined_items(tasks)
    return sorted(item for item in produced_items(tasks) if item not in examined)


def verification_coverage(tasks):
    """Fraction of produced design items at least one checking task examines."""
    produced = produced_items(tasks)
    if not produced:
        raise ValueError("verification_coverage needs at least one produced design item")
    examined = examined_items(tasks)
    return sum(1 for item in produced if item in examined) / len(produced)


def evaluate_task_set(phase):
    """Full clause 5.4.3 assessment of one design and verification task set.

    Returns the resolved order, the coverage reached, the findings and the
    verdict.
    """
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping of tasks and an optional threshold")
    known = set(_PHASE_REQUIRED_KEYS) | set(_PHASE_OPTIONAL_KEYS)
    unknown = sorted(set(phase) - known)
    if unknown:
        raise ValueError("unknown phase keys: %s" % ", ".join(unknown))
    missing = [key for key in _PHASE_REQUIRED_KEYS if key not in phase]
    if missing:
        raise ValueError("phase missing required keys: %s" % ", ".join(missing))

    tasks = validate_tasks(phase["tasks"])
    if not tasks:
        raise ValueError("phase must carry at least one task")
    order = order_tasks(tasks)
    by_id = {task["id"]: task for task in tasks}

    findings = []
    for task in tasks:
        if task["kind"] == ENGINEERING and not task["produces"]:
            findings.append(
                {
                    "code": "engineering-task-without-design-item",
                    "task": task["id"],
                    "detail": "engineering task %s names no design item it produces"
                    % task["id"],
                }
            )
        if task["kind"] == CHECKING and not task["examines"]:
            findings.append(
                {
                    "code": "checking-task-without-target",
                    "task": task["id"],
                    "detail": "checking task %s names no design item it examines"
                    % task["id"],
                }
            )

    produced = set(produced_items(tasks))
    for task in tasks:
        if task["kind"] != CHECKING:
            continue
        for item in task["examines"]:
            if item not in produced:
                findings.append(
                    {
                        "code": "checking-target-not-produced",
                        "task": task["id"],
                        "item": item,
                        "detail": "checking task %s examines %r, which no "
                        "engineering task produces" % (task["id"], item),
                    }
                )

    for item in unexamined_items(tasks):
        findings.append(
            {
                "code": "design-item-not-examined",
                "item": item,
                "detail": "design item %r is produced and no checking task "
                "examines it" % item,
            }
        )

    for task in tasks:
        if task["status"] != COMPLETE:
            continue
        if not task["evidence"]:
            findings.append(
                {
                    "code": "complete-task-without-evidence",
                    "task": task["id"],
                    "detail": "task %s is reported complete and carries no evidence"
                    % task["id"],
                }
            )
        for prerequisite in task["prerequisites"]:
            if by_id[prerequisite]["status"] != COMPLETE:
                findings.append(
                    {
                        "code": "complete-ahead-of-prerequisite",
                        "task": task["id"],
                        "prerequisite": prerequisite,
                        "detail": "task %s is reported complete while its "
                        "prerequisite %s is %s"
                        % (task["id"], prerequisite, by_id[prerequisite]["status"]),
                    }
                )

    coverage = verification_coverage(tasks) if produced else 0.0
    threshold = phase.get("coverage_threshold")
    if threshold is not None:
        threshold_value = _fraction("coverage_threshold", threshold)
        if not meets_coverage_threshold(coverage, threshold_value):
            findings.append(
                {
                    "code": "verification-coverage-below-threshold",
                    "achieved": coverage,
                    "threshold": threshold_value,
                    "detail": "verification coverage reaches %.1f %% against a "
                    "%.1f %% threshold" % (100.0 * coverage, 100.0 * threshold_value),
                }
            )

    return {
        "order": order,
        "task_count": len(tasks),
        "produced_items": produced_items(tasks),
        "unexamined_items": unexamined_items(tasks),
        "verification_coverage": coverage,
        "findings": findings,
        "acceptable": not findings,
    }
