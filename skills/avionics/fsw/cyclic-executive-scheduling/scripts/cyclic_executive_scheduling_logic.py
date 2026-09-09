"""Cyclic executive frame-table scheduling: hyperperiod, admissible frame
lengths, per-frame capacity check and the constructive frame table for a
periodic avionics flight software task set with implicit deadlines.

Pure stdlib (math only), deterministic, no randomness.
"""

import math

TOL = 1e-12


def _validate_tasks(tasks):
    """Validate the task list shape shared by every public function."""
    if not isinstance(tasks, list) or len(tasks) == 0:
        raise ValueError("task list must be a non-empty list")
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError("task %d must be a dict" % idx)
        missing = [k for k in ("C", "T") if k not in task]
        if missing:
            raise ValueError("task %d missing key(s) %s" % (idx, ", ".join(missing)))
        for key in ("C", "T"):
            value = task[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("%s must be a positive integer, got %r" % (key, value))
            if value <= 0:
                raise ValueError("%s must be a positive integer, got %r" % (key, value))


def _task_name(task, idx):
    """Return the task label: its "name" key, or "task%d" % idx."""
    return task.get("name", "task%d" % idx)


def _validate_frame_length(tasks, f):
    """Validate a candidate frame length against the task period set."""
    if isinstance(f, bool) or not isinstance(f, int) or f <= 0:
        raise ValueError("frame length f must be a positive integer, got %r" % (f,))
    periods = [task["T"] for task in tasks]
    bad = [p for p in periods if p % f != 0]
    if bad:
        raise ValueError(
            "frame length f must divide every task period, got f=%d, periods %s"
            % (f, periods)
        )


def hyperperiod(tasks):
    """H = lcm over all task periods, the major cycle the frame table repeats over."""
    _validate_tasks(tasks)
    h = 1
    for task in tasks:
        h = h * task["T"] // math.gcd(h, task["T"])
    return h


def period_gcd(tasks):
    """g = gcd over all task periods; frame lengths must divide g."""
    _validate_tasks(tasks)
    g = tasks[0]["T"]
    for task in tasks[1:]:
        g = math.gcd(g, task["T"])
    return g


def utilization(tasks):
    """U = sum of C_i / T_i, the necessary-condition processor utilization."""
    _validate_tasks(tasks)
    return sum(task["C"] / task["T"] for task in tasks)


def admissible_frame_lengths(tasks):
    """Ascending divisors f of the period gcd with f >= max C_i (frame-fit rule)."""
    _validate_tasks(tasks)
    g = period_gcd(tasks)
    max_c = max(task["C"] for task in tasks)
    return [f for f in range(1, g + 1) if g % f == 0 and f >= max_c]


def frame_loads(tasks, f):
    """Per-frame loads load(j) for j = 0..H/f - 1 at frame length f."""
    _validate_tasks(tasks)
    _validate_frame_length(tasks, f)
    h = hyperperiod(tasks)
    n_frames = h // f
    loads = [0] * n_frames
    for task in tasks:
        for j in range(n_frames):
            if (j * f) % task["T"] == 0:
                loads[j] += task["C"]
    return loads


def max_frame_load(tasks, f):
    """The worst-case single-frame load at frame length f."""
    return max(frame_loads(tasks, f))


def feasible_frame_lengths(tasks):
    """Admissible frame lengths that are also capacity-feasible, ascending."""
    _validate_tasks(tasks)
    return [f for f in admissible_frame_lengths(tasks) if max_frame_load(tasks, f) <= f]


def frame_table(tasks, f):
    """Constructive frame table: one dict per frame with jobs, load and slack."""
    _validate_tasks(tasks)
    loads = frame_loads(tasks, f)
    n_frames = len(loads)
    table = []
    for j in range(n_frames):
        jobs = [
            _task_name(task, idx)
            for idx, task in enumerate(tasks)
            if (j * f) % task["T"] == 0
        ]
        table.append(
            {
                "frame": j,
                "start_ms": j * f,
                "end_ms": (j + 1) * f,
                "jobs": jobs,
                "load": loads[j],
                "slack": f - loads[j],
            }
        )
    return table


def cyclic_executive_report(tasks):
    """Full feasibility report: hyperperiod, gcd, utilization, verdict and frame table."""
    _validate_tasks(tasks)
    h = hyperperiod(tasks)
    g = period_gcd(tasks)
    max_c = max(task["C"] for task in tasks)
    u = utilization(tasks)
    admissible = admissible_frame_lengths(tasks)
    feasible = feasible_frame_lengths(tasks)

    report = {
        "hyperperiod": h,
        "period_gcd": g,
        "max_execution_time": max_c,
        "utilization": u,
        "admissible_frame_lengths": admissible,
        "feasible_frame_lengths": feasible,
        "verdict": None,
        "reject_reason": None,
        "frame_length": None,
        "frame_count": None,
        "max_frame_load": None,
        "min_slack": None,
        "frame_table": None,
    }

    if feasible:
        f = feasible[0]
        table = frame_table(tasks, f)
        loads = [row["load"] for row in table]
        report["verdict"] = "FITS"
        report["frame_length"] = f
        report["frame_count"] = h // f
        report["max_frame_load"] = max(loads)
        report["min_slack"] = f - max(loads)
        report["frame_table"] = table
    else:
        report["verdict"] = "no-admissible-frame"
        report["reject_reason"] = "frame-fit" if not admissible else "capacity"

    return report


def feasible(tasks):
    """Convenience: True iff cyclic_executive_report(tasks)["verdict"] == "FITS"."""
    return cyclic_executive_report(tasks)["verdict"] == "FITS"
