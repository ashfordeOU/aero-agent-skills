"""Design task set of a microwave monolithic integrated circuit development.

Anchor: ECSS-Q-ST-60-12 clause 7.2 (the collected engineering activities that
make up the microwave circuit development effort). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared task: a unique identifier, one of the mandated
   design activities or a declared project extra, a state from the closed
   vocabulary, a strictly positive declared effort, an owner and a deliverable.
2. Compare the declared activities with the mandated set, so an activity no
   task serves is reported as a coverage gap and an activity outside the
   mandated set is reported separately as a project extra rather than a gap.
3. Report the tasks that carry no responsible owner and the tasks that produce
   no named deliverable; both make a declared task unauditable.
4. Distribute the declared effort over the activities and expose the share held
   by the single largest activity, because one activity holding most of the
   effort is a planning-granularity finding, not a plan.
5. Derive the completion ratio by effort rather than by task count, so a set of
   small finished tasks cannot report a development as nearly done.
6. Return the authorisation verdict for the task set.
"""

import math

__all__ = [
    "MANDATED_ACTIVITIES",
    "TASK_STATES",
    "EFFORT_CONCENTRATION_LIMIT",
    "RATIO_TOLERANCE",
    "normalise_activity",
    "validate_task",
    "build_task_set",
    "activity_coverage",
    "effort_by_activity",
    "effort_concentration",
    "ownership_gaps",
    "deliverable_gaps",
    "completion_ratio_by_effort",
    "completion_ratio_by_count",
    "assess_design_task_set",
]

# The engineering activities a microwave circuit development effort has to
# contain. A project may split one of these across several tasks, and may add
# tasks of its own, but an activity nothing serves is a gap in the effort.
MANDATED_ACTIVITIES = (
    "electrical-design-specification",
    "circuit-design",
    "layout-design",
    "electromagnetic-simulation",
    "thermal-design",
    "reliability-and-lifetime-design",
    "process-design-rule-verification",
    "design-review",
)

# Closed state vocabulary. Anything else is an input error, because a free-text
# state cannot be counted towards a completion ratio.
TASK_STATES = ("planned", "in-progress", "complete")

# One activity holding more than this share of the declared effort means the
# effort has not been broken down far enough to be tracked.
EFFORT_CONCENTRATION_LIMIT = 0.5

# Ratio comparisons are divisions of sums; absorb representation error here
# instead of moving the planning limit.
RATIO_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a stripped non-empty string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _optional_text(value, label):
    """Return a stripped string, or None when the field is absent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("%s must be a string or None, got %r" % (label, value))
    text = value.strip()
    return text or None


def normalise_activity(name):
    """Return the canonical spelling of an activity name."""
    text = _require_text(name, "activity")
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_task(task):
    """Return one validated task record, or raise on a malformed declaration."""
    if not isinstance(task, dict):
        raise ValueError("each task must be a mapping, got %r" % (task,))
    for key in ("id", "activity", "state", "effort_hours"):
        if key not in task:
            raise ValueError("task missing required key '%s'" % key)
    identifier = _require_text(task["id"], "task id")
    activity = normalise_activity(task["activity"])
    state = _require_text(task["state"], "task state").lower()
    if state not in TASK_STATES:
        raise ValueError(
            "task %s has state %r, must be one of %s"
            % (identifier, state, ", ".join(TASK_STATES))
        )
    effort = task["effort_hours"]
    if not isinstance(effort, (int, float)) or isinstance(effort, bool):
        raise ValueError("task %s effort_hours must be a real number" % identifier)
    effort = float(effort)
    if not math.isfinite(effort):
        raise ValueError("task %s effort_hours must be finite" % identifier)
    if effort <= 0.0:
        raise ValueError(
            "task %s effort_hours must be positive, got %g" % (identifier, effort)
        )
    return {
        "id": identifier,
        "activity": activity,
        "state": state,
        "effort_hours": effort,
        "owner": _optional_text(task.get("owner"), "task owner"),
        "deliverable": _optional_text(task.get("deliverable"), "task deliverable"),
    }


def build_task_set(tasks):
    """Return the validated task set, refusing a duplicate identifier."""
    if not isinstance(tasks, (list, tuple)) or not tasks:
        raise ValueError("tasks must be a non-empty sequence of task mappings")
    records = []
    seen = set()
    for task in tasks:
        record = validate_task(task)
        if record["id"] in seen:
            raise ValueError("duplicate task id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def activity_coverage(records):
    """Return the covered, missing and extra activities of a task set."""
    declared = {record["activity"] for record in records}
    covered = [name for name in MANDATED_ACTIVITIES if name in declared]
    missing = [name for name in MANDATED_ACTIVITIES if name not in declared]
    extra = sorted(name for name in declared if name not in MANDATED_ACTIVITIES)
    return {"covered": covered, "missing": missing, "extra": extra}


def effort_by_activity(records):
    """Return the declared effort in hours summed per activity."""
    totals = {}
    for record in records:
        totals[record["activity"]] = totals.get(record["activity"], 0.0) + record["effort_hours"]
    return totals


def effort_concentration(records):
    """Return the share of the total effort held by the largest activity."""
    totals = effort_by_activity(records)
    grand = sum(totals.values())
    if grand <= 0.0:
        raise ValueError("total declared effort must be positive")
    return max(totals.values()) / grand


def ownership_gaps(records):
    """Return the identifiers of tasks declared without a responsible owner."""
    return [record["id"] for record in records if record["owner"] is None]


def deliverable_gaps(records):
    """Return the identifiers of tasks declared without a named deliverable."""
    return [record["id"] for record in records if record["deliverable"] is None]


def completion_ratio_by_effort(records):
    """Return the completed share of the declared effort."""
    grand = sum(record["effort_hours"] for record in records)
    if grand <= 0.0:
        raise ValueError("total declared effort must be positive")
    done = sum(r["effort_hours"] for r in records if r["state"] == "complete")
    return done / grand


def completion_ratio_by_count(records):
    """Return the completed share of the task count."""
    if not records:
        raise ValueError("task set must not be empty")
    done = sum(1 for record in records if record["state"] == "complete")
    return done / float(len(records))


def assess_design_task_set(spec):
    """Run the full clause 7.2 design-task-set assessment.

    spec keys: tasks (sequence of task mappings), optional
    concentration_limit (default EFFORT_CONCENTRATION_LIMIT).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "tasks" not in spec:
        raise ValueError("spec missing required key 'tasks'")
    limit = spec.get("concentration_limit", EFFORT_CONCENTRATION_LIMIT)
    if not isinstance(limit, (int, float)) or isinstance(limit, bool):
        raise ValueError("concentration_limit must be a real number")
    limit = float(limit)
    if not math.isfinite(limit) or not (0.0 < limit <= 1.0):
        raise ValueError("concentration_limit must lie in (0, 1], got %g" % limit)

    records = build_task_set(spec["tasks"])
    coverage = activity_coverage(records)
    owners = ownership_gaps(records)
    deliverables = deliverable_gaps(records)
    concentration = effort_concentration(records)
    over_concentrated = concentration > limit and not math.isclose(
        concentration, limit, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )

    findings = []
    if coverage["missing"]:
        findings.append(
            "no task serves %d mandated design activity/activities: %s"
            % (len(coverage["missing"]), ", ".join(coverage["missing"]))
        )
    if owners:
        findings.append(
            "%d task(s) carry no responsible owner: %s" % (len(owners), ", ".join(owners))
        )
    if deliverables:
        findings.append(
            "%d task(s) produce no named deliverable: %s"
            % (len(deliverables), ", ".join(deliverables))
        )
    if over_concentrated:
        findings.append(
            "a single activity holds %.1f%% of the declared effort, above the %.1f%% "
            "breakdown limit" % (concentration * 100.0, limit * 100.0)
        )

    return {
        "tasks": records,
        "covered_activities": coverage["covered"],
        "missing_activities": coverage["missing"],
        "extra_activities": coverage["extra"],
        "effort_by_activity": effort_by_activity(records),
        "total_effort_hours": sum(r["effort_hours"] for r in records),
        "effort_concentration": concentration,
        "concentration_limit": limit,
        "ownership_gaps": owners,
        "deliverable_gaps": deliverables,
        "completion_ratio_by_effort": completion_ratio_by_effort(records),
        "completion_ratio_by_count": completion_ratio_by_count(records),
        "coverage_ratio": len(coverage["covered"]) / float(len(MANDATED_ACTIVITIES)),
        "findings": findings,
        "authorised": not findings,
    }
