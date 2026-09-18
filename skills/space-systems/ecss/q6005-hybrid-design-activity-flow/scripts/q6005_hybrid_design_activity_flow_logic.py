"""Design activity flow for a hybrid microcircuit.

Anchor: ECSS-Q-ST-60-05 clause 7.1.2 (the sequence of engineering tasks that
take a hybrid concept through to an approved design solution). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared activity: an identifier, the mandated stage it
   serves, a duration and the activities it waits on.
2. Build the flow graph, refusing a duplicate identifier, a self-dependency
   or a predecessor that was never declared.
3. Sequence the activities topologically, refusing a dependency cycle - a
   cycle is not a slow plan, it is a plan that never reaches approval.
4. Name the mandated stages the plan never declares, so a flow that simply
   omits design verification is caught before it is worked.
5. Report what may start now (every predecessor complete), and expose any
   activity signed off ahead of a predecessor that is not complete.
6. Derive the earliest finish of every activity and the critical path to the
   approved design solution.
"""

import math

__all__ = [
    "CANONICAL_STAGES",
    "ACTIVITY_STATES",
    "validate_activity",
    "build_flow",
    "topological_order",
    "missing_stages",
    "ready_activities",
    "out_of_order_signoffs",
    "earliest_finish_days",
    "critical_path",
    "completion_ratio",
    "assess_design_flow",
]

# The engineering tasks a hybrid design passes through on its way from a
# concept to a design solution somebody signs.
CANONICAL_STAGES = (
    "design-input-review",
    "preliminary-design",
    "materials-and-parts-selection",
    "detailed-design",
    "design-analysis",
    "design-verification",
    "design-review-and-approval",
)

ACTIVITY_STATES = ("not-started", "in-progress", "complete")

_APPROVAL_STAGE = "design-review-and-approval"


def _duration(value, label):
    """Return a validated non-negative finite duration in days."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, out))
    return out


def validate_activity(activity):
    """Return one declared activity as a validated record."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("id", "stage", "duration_days", "status"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    ident = activity["id"]
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("activity id must be a non-empty string, got %r" % (ident,))
    ident = ident.strip()
    stage = activity["stage"]
    if not isinstance(stage, str) or stage.strip().lower() not in CANONICAL_STAGES:
        raise ValueError(
            "activity '%s' names stage %r; expected one of %s"
            % (ident, stage, ", ".join(CANONICAL_STAGES))
        )
    status = activity["status"]
    if not isinstance(status, str) or status.strip().lower() not in ACTIVITY_STATES:
        raise ValueError(
            "activity '%s' has status %r; expected one of %s"
            % (ident, status, ", ".join(ACTIVITY_STATES))
        )
    raw_preds = activity.get("predecessors", ())
    if raw_preds is None:
        raw_preds = ()
    if not isinstance(raw_preds, (list, tuple)):
        raise ValueError("activity '%s' predecessors must be a sequence" % ident)
    preds = []
    for item in raw_preds:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("activity '%s' has a non-string predecessor %r" % (ident, item))
        name = item.strip()
        if name == ident:
            raise ValueError("activity '%s' depends on itself" % ident)
        if name in preds:
            raise ValueError("activity '%s' lists predecessor '%s' twice" % (ident, name))
        preds.append(name)
    return {
        "id": ident,
        "stage": stage.strip().lower(),
        "duration_days": _duration(activity["duration_days"], "activity '%s' duration_days" % ident),
        "status": status.strip().lower(),
        "predecessors": tuple(preds),
    }


def build_flow(activities):
    """Return the validated flow as an id -> activity mapping."""
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("activities must be a non-empty sequence of activity mappings")
    flow = {}
    for activity in activities:
        record = validate_activity(activity)
        if record["id"] in flow:
            raise ValueError("activity id '%s' declared twice" % record["id"])
        flow[record["id"]] = record
    for record in flow.values():
        for pred in record["predecessors"]:
            if pred not in flow:
                raise ValueError(
                    "activity '%s' waits on '%s', which is not declared" % (record["id"], pred)
                )
    return flow


def topological_order(activities):
    """Return the activity ids in a runnable order; refuse a dependency cycle."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    remaining = {k: set(v["predecessors"]) for k, v in flow.items()}
    order = []
    while remaining:
        ready = sorted(k for k, preds in remaining.items() if not preds)
        if not ready:
            raise ValueError(
                "dependency cycle among activities: %s" % ", ".join(sorted(remaining))
            )
        for ident in ready:
            order.append(ident)
            del remaining[ident]
        for preds in remaining.values():
            preds.difference_update(ready)
    return order


def missing_stages(activities):
    """Return the mandated stages the declared flow never covers."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    declared = {record["stage"] for record in flow.values()}
    return tuple(stage for stage in CANONICAL_STAGES if stage not in declared)


def ready_activities(activities):
    """Return the ids that can start now: not complete, all predecessors complete."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    out = []
    for ident in sorted(flow):
        record = flow[ident]
        if record["status"] == "complete":
            continue
        if all(flow[p]["status"] == "complete" for p in record["predecessors"]):
            out.append(ident)
    return out


def out_of_order_signoffs(activities):
    """Return (activity, predecessor) pairs signed off ahead of their input."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    violations = []
    for ident in sorted(flow):
        record = flow[ident]
        if record["status"] != "complete":
            continue
        for pred in record["predecessors"]:
            if flow[pred]["status"] != "complete":
                violations.append((ident, pred))
    return violations


def earliest_finish_days(activities):
    """Return the earliest finish day of every activity, in flow order."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    finish = {}
    for ident in topological_order(flow):
        record = flow[ident]
        start = 0.0
        for pred in record["predecessors"]:
            if finish[pred] > start:
                start = finish[pred]
        finish[ident] = start + record["duration_days"]
    return finish


def critical_path(activities):
    """Return (path, total_days): the longest chain through the flow."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    finish = earliest_finish_days(flow)
    if not finish:
        raise ValueError("flow carries no activities")
    total = max(finish.values())
    # Break a tie on the lowest id so the reported path is reproducible.
    tail = sorted(k for k, v in finish.items() if math.isclose(v, total, rel_tol=0.0, abs_tol=1e-12))[0]
    path = [tail]
    while flow[path[-1]]["predecessors"]:
        record = flow[path[-1]]
        driver = sorted(record["predecessors"], key=lambda p: (-finish[p], p))[0]
        path.append(driver)
    path.reverse()
    return (path, total)


def completion_ratio(activities):
    """Return the fraction of declared activities already complete."""
    flow = activities if isinstance(activities, dict) else build_flow(activities)
    done = sum(1 for record in flow.values() if record["status"] == "complete")
    return done / float(len(flow))


def assess_design_flow(spec):
    """Run the full clause 7.1.2 design-activity-flow assessment.

    spec keys: activities (sequence of activity mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "activities" not in spec:
        raise ValueError("spec missing required key 'activities'")
    flow = build_flow(spec["activities"])
    order = topological_order(flow)
    gaps = missing_stages(flow)
    ready = ready_activities(flow)
    violations = out_of_order_signoffs(flow)
    finish = earliest_finish_days(flow)
    path, total = critical_path(flow)
    ratio = completion_ratio(flow)

    approval_ids = [i for i in order if flow[i]["stage"] == _APPROVAL_STAGE]
    successors = {i: [] for i in flow}
    for ident, record in flow.items():
        for pred in record["predecessors"]:
            successors[pred].append(ident)
    terminal_approval = [i for i in approval_ids if not successors[i]]

    findings = []
    if gaps:
        findings.append("mandated design stages never declared: %s" % ", ".join(gaps))
    if violations:
        findings.append(
            "activities signed off ahead of an open predecessor: %s"
            % ", ".join("%s before %s" % pair for pair in violations)
        )
    if not terminal_approval:
        findings.append(
            "no design-review-and-approval activity closes the flow; the design "
            "solution cannot be approved from this plan"
        )
    open_ids = [i for i in order if flow[i]["status"] != "complete"]
    if open_ids:
        findings.append("design activities still open: %s" % ", ".join(open_ids))

    return {
        "order": order,
        "missing_stages": gaps,
        "ready": ready,
        "out_of_order": violations,
        "earliest_finish_days": finish,
        "critical_path": path,
        "duration_days": total,
        "completion_ratio": ratio,
        "open_activities": tuple(open_ids),
        "findings": findings,
        "design_solution_approved": not findings,
    }
