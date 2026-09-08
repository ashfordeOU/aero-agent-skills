"""Offline schedulability analysis for dual-criticality avionics task sets.

Pure Python stdlib, deterministic, no network. Implements the AMC-rtb
response-time bound of Baruah, Burns and Davis, "Response-Time Analysis
for Mixed Criticality Systems" (RTSS 2011), over the Vestal task model
of "Preemptive Scheduling of Multi-Criticality Systems with Varying
Degrees of Execution Time Assurance" (RTSS 2007). Public science,
summary-only; no standard text reproduced.

Each task is a dict {name, criticality, C_LO, C_HI, T, D}: criticality
is "LO" or "HI", C_LO and C_HI are low- and high-criticality execution
time estimates with C_HI at least C_LO (a LO task carries no high
estimate, so its C_HI must equal its C_LO), T is the period and D the
relative deadline with D no greater than T. The task list IS the
fixed-priority order: index 0 is the highest priority, and the
deadlines must be non-decreasing (deadline-monotonic order).

Two response-time phases:

- lo_response_time / lo_response_times: the classic fixed-point
  response-time analysis over the C_LO estimates for every task
  (before the criticality-mode change).
- hi_response_time / hi_response_times: the AMC-rtb fixed point for
  the HI-criticality tasks only (after the LO to HI criticality-mode
  change), charging higher-priority LO tasks at C_LO and
  higher-priority HI tasks at C_HI in the interference sum.

feasible(tasks) is the whole-set verdict: LO feasible and HI feasible.
A diverged solve (an iterate strictly past a task's own deadline, or a
solve that has not converged after MAX_RTA_ITERATIONS passes) reports
None and makes its mode infeasible.

Module constants: MAX_RTA_ITERATIONS (per-solve fixed-point safety cap)
and CONVERGENCE_TOL (the repeat tolerance that marks convergence).
"""

import math

# Per-solve fixed-point safety cap: a solve that still moves after this
# many passes reports None (divergence).
MAX_RTA_ITERATIONS = 100
# An iterate that repeats within this tolerance has converged.
CONVERGENCE_TOL = 1e-12

_REQUIRED_KEYS = ("criticality", "C_LO", "C_HI", "T", "D")


def _ceil_div(a, b):
    """Ceiling of a / b: exact integer floor-division when both are ints."""
    if isinstance(a, int) and isinstance(b, int):
        return -(-a // b)
    return math.ceil(a / b)


def _validate_positive(value, key):
    """Return value if it is a positive, non-boolean real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a positive number, got %r" % (key, value))
    if value <= 0:
        raise ValueError("%s must be a positive number, got %s" % (key, value))
    return value


def _validate_task(task, index):
    """Validate one task dict and return a normalized copy.

    Raises ValueError on a non-dict entry, a missing required key, an
    unknown criticality word, a boolean or non-positive C_LO/C_HI/T/D,
    C_HI below C_LO, a LO task whose C_HI differs from C_LO, and a
    deadline D above T.
    """
    if not isinstance(task, dict):
        raise ValueError("task at index %d must be a dict" % index)
    missing = [k for k in _REQUIRED_KEYS if k not in task]
    if missing:
        raise ValueError(
            "task at index %d missing key(s) %s" % (index, ", ".join(missing))
        )
    criticality = task["criticality"]
    if criticality not in ("LO", "HI"):
        raise ValueError("criticality must be 'LO' or 'HI', got %r" % criticality)
    c_lo = _validate_positive(task["C_LO"], "C_LO")
    c_hi = _validate_positive(task["C_HI"], "C_HI")
    t = _validate_positive(task["T"], "T")
    d = _validate_positive(task["D"], "D")
    if c_hi < c_lo:
        raise ValueError(
            "C_HI must be at least C_LO, got C_HI %s with C_LO %s" % (c_hi, c_lo)
        )
    if criticality == "LO" and c_hi != c_lo:
        raise ValueError(
            "a LO-criticality task carries no high estimate: C_HI must "
            "equal C_LO, got C_HI %s with C_LO %s" % (c_hi, c_lo)
        )
    if d > t:
        raise ValueError("D must be no greater than T, got D %s with T %s" % (d, t))
    return {
        "name": task.get("name", "task%d" % index),
        "criticality": criticality,
        "C_LO": c_lo,
        "C_HI": c_hi,
        "T": t,
        "D": d,
    }


def _validate_tasks(tasks):
    """Validate a task list and return the normalized list.

    Raises ValueError on an empty list and on a list whose deadlines
    are not non-decreasing (not in deadline-monotonic priority order,
    step 1 of the SKILL.md workflow).
    """
    if not isinstance(tasks, (list, tuple)) or len(tasks) == 0:
        raise ValueError("task list must be a non-empty list")
    validated = [_validate_task(task, i) for i, task in enumerate(tasks)]
    for i in range(1, len(validated)):
        if validated[i]["D"] < validated[i - 1]["D"]:
            raise ValueError(
                "tasks must be in deadline-monotonic priority order "
                "(non-decreasing D); higher priority is the lower list index"
            )
    return validated


def _validate_index(n_tasks, index):
    """Raise ValueError when index is outside [0, n_tasks)."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("index out of range")
    if index < 0 or index >= n_tasks:
        raise ValueError("index out of range")


def _solve_fixed_point(c_own, d_own, interference):
    """Iterate R = c_own + interference(R) to a fixed point, or None.

    Starts at R = c_own (step 2/3 of the SKILL.md workflow). Returns
    None the moment an iterate exceeds d_own (the monotone iteration
    can then never return to a feasible value) or when no fixed point
    is reached within MAX_RTA_ITERATIONS passes. Returns the converged
    R (a float) when two consecutive iterates agree within
    CONVERGENCE_TOL.
    """
    r = c_own
    for _ in range(MAX_RTA_ITERATIONS):
        r_next = c_own + interference(r)
        if r_next > d_own + CONVERGENCE_TOL:
            return None
        if abs(r_next - r) <= CONVERGENCE_TOL:
            return float(r_next)
        r = r_next
    return None


def _lo_interference(hp_tasks):
    """Interference function for the LO-mode phase over hp_tasks."""
    def interference(r):
        return sum(_ceil_div(r, j["T"]) * j["C_LO"] for j in hp_tasks)
    return interference


def _hi_interference(hp_tasks):
    """Interference function for the AMC-rtb HI-mode phase over hp_tasks.

    Higher-priority LO tasks are charged at C_LO (dropped only after
    the mode change); higher-priority HI tasks are charged at C_HI
    (overrun possible). Both arms feed the same sum, step 5 of the
    SKILL.md workflow.
    """
    def interference(r):
        total = 0.0
        for j in hp_tasks:
            rate = j["C_LO"] if j["criticality"] == "LO" else j["C_HI"]
            total += _ceil_div(r, j["T"]) * rate
        return total
    return interference


def lo_response_time(tasks, index):
    """LO-mode response time of task `index`, or None on divergence.

    The converged fixed point over the C_LO estimates (step 2 of the
    SKILL.md workflow). ValueErrors of the task shape and of an index
    outside [0, len(tasks)).
    """
    validated = _validate_tasks(tasks)
    _validate_index(len(validated), index)
    task = validated[index]
    hp_tasks = validated[:index]
    return _solve_fixed_point(task["C_LO"], task["D"], _lo_interference(hp_tasks))


def hi_response_time(tasks, index):
    """HI-mode (AMC-rtb) response time of task `index`, or None.

    The converged AMC-rtb fixed point after the criticality-mode
    change (steps 3 and 5 of the SKILL.md workflow). ValueError when
    task `index` is LO-criticality: HI-mode analysis guarantees HI
    tasks only. ValueErrors of the task shape and index as above.
    """
    validated = _validate_tasks(tasks)
    _validate_index(len(validated), index)
    task = validated[index]
    if task["criticality"] != "HI":
        raise ValueError(
            "task %d is LO-criticality; HI-mode analysis guarantees HI "
            "tasks only" % index
        )
    hp_tasks = validated[:index]
    return _solve_fixed_point(task["C_HI"], task["D"], _hi_interference(hp_tasks))


def lo_response_times(tasks):
    """LO-mode response times, feasibility and utilization for every task.

    Step 2 of the SKILL.md workflow, run once per task in priority
    order. Returns {"names", "response_times", "feasible", "utilization"}
    with feasible True only when every LO-mode response converged at
    or under its own deadline. ValueErrors of the task shape and of a
    non-deadline-monotonic order.
    """
    validated = _validate_tasks(tasks)
    responses = []
    for i, task in enumerate(validated):
        hp_tasks = validated[:i]
        responses.append(
            _solve_fixed_point(task["C_LO"], task["D"], _lo_interference(hp_tasks))
        )
    return {
        "names": [t["name"] for t in validated],
        "response_times": responses,
        "feasible": all(r is not None for r in responses),
        "utilization": sum(t["C_LO"] / t["T"] for t in validated),
    }


def hi_response_times(tasks):
    """HI-mode (AMC-rtb) response times, feasibility and utilization.

    Step 3 of the SKILL.md workflow, restricted to the HI-criticality
    tasks after the criticality-mode change (LO tasks are dropped).
    Returns {"names" (HI tasks only), "response_times", "feasible",
    "utilization" (U_HI)}. An all-LO set returns empty names and
    responses with feasible True. ValueErrors of the task shape and
    order.
    """
    validated = _validate_tasks(tasks)
    hi_indices = [i for i, t in enumerate(validated) if t["criticality"] == "HI"]
    responses = []
    for i in hi_indices:
        task = validated[i]
        hp_tasks = validated[:i]
        responses.append(
            _solve_fixed_point(task["C_HI"], task["D"], _hi_interference(hp_tasks))
        )
    return {
        "names": [validated[i]["name"] for i in hi_indices],
        "response_times": responses,
        "feasible": all(r is not None for r in responses),
        "utilization": sum(validated[i]["C_HI"] / validated[i]["T"] for i in hi_indices),
    }


def feasible(tasks):
    """Whole-set verdict: LO-mode feasible and HI-mode feasible.

    Step 6 of the SKILL.md workflow. Same ValueErrors as
    lo_response_times / hi_response_times.
    """
    return lo_response_times(tasks)["feasible"] and hi_response_times(tasks)["feasible"]
