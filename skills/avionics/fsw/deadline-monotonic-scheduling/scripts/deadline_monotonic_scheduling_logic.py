"""Deadline-monotonic fixed-priority scheduling for avionics flight software.

Pure stdlib, closed form (math.ceil only). Decides the offline
fixed-priority schedulability of a task set whose per-task relative
deadlines D_i are not the implicit D_i = T_i of the pack sibling
avionics/fsw/real-time-scheduling: priorities are assigned by
deadline-monotonic order (shorter deadline, higher priority; equal
deadlines keep input order, the assignment Leung and Whitehead 1982
proved optimal for constrained deadlines), and each task's exact
worst-case response time is computed by the jitter-aware fixed-point
iteration converged against its own deadline.

Tasks are dicts {name, C, T, D, J} in one time unit: worst-case
execution C, period T, relative deadline D and optional release
jitter J (default 0.0); name is optional.  The busy-window completion
of job q of task i is

    w_i(q) = (q + 1) * C_i + sum_{j in hp(i)} ceil((w + J_j)/T_j) * C_j

iterated from below until it repeats within CONVERGENCE_TOL (Audsley,
Burns, Richardson and Wellings 1993 convergence rules; Tindell and
Clark 1994 release-jitter term in the interference count).  Job q of
task i releases at q * T_i, so its response is w_i(q) - q * T_i and
it must satisfy w_i(q) <= q * T_i + D_i; the iteration is monotone
non-decreasing, so an iterate past that per-job bound can never
converge under the deadline and the task reports None (divergence).

Constrained deadlines (D_i <= T_i) need only the converged first-job
completion, which is exact and sufficient.  Arbitrary deadlines
(D_i > T_i) whose first-job completion exceeds T_i enter the queueing
regime and the exact response is the maximum of w_i(q) - q * T_i over
the busy-period job scan, stopped when a completion satisfies
w(q) <= (q + 1) * T_i; a job response past D_i, or a scan past
MAX_BUSY_PERIOD_JOBS, reports None.

Imports math only.  Deterministic: no randomness, no network, no
external processes.
"""

import math

# Module constants (pinned by the wave-45 spec).
MAX_RTA_ITERATIONS = 100    # fixed-point safety cap per completion solve
MAX_BUSY_PERIOD_JOBS = 1000  # cap on the arbitrary-deadline job scan
CONVERGENCE_TOL = 1e-12      # an iterate that repeats within this has converged


def _norm_task(t):
    """Validate one task dict and return {name, C, T, D, J} of floats."""
    if not isinstance(t, dict):
        raise ValueError("each task must be a dict {name, C, T, D, J}")
    missing = [k for k in ("C", "T", "D") if k not in t]
    if missing:
        raise ValueError("task missing key(s) %s" % ", ".join(missing))
    try:
        c = float(t["C"])
        tt = float(t["T"])
        d = float(t["D"])
        j = float(t.get("J", 0.0))
    except (TypeError, ValueError):
        raise ValueError("task C, T, D, J must be numeric")
    name = t.get("name", None)
    for label, val in (("C", c), ("T", tt), ("D", d)):
        if isinstance(t[label], bool) or not math.isfinite(val) or val <= 0:
            raise ValueError("%s must be a positive number, got %r"
                             % (label, t[label]))
    if isinstance(t.get("J", 0.0), bool) or not math.isfinite(j) or j < 0:
        raise ValueError("J must be a non-negative number, got %r"
                         % t.get("J", 0.0))
    return {"name": name, "C": c, "T": tt, "D": d, "J": j}


def _norm_tasks(tasks):
    """Validate a whole task list and return the normalized dicts."""
    if not isinstance(tasks, (list, tuple)) or len(tasks) == 0:
        raise ValueError("task list must be a non-empty list")
    return [_norm_task(t) for t in tasks]


def _check_dm_order(tasks):
    """Deadline-monotonic order is non-decreasing D, index 0 highest."""
    for i in range(len(tasks) - 1):
        if tasks[i]["D"] > tasks[i + 1]["D"]:
            raise ValueError(
                "tasks must be in deadline-monotonic priority order "
                "(non-decreasing D); sort with dm_priority_order first")


def _norm_one(tasks, index):
    """Validate the ordered list and one index into it."""
    ts = _norm_tasks(tasks)
    _check_dm_order(ts)
    if not isinstance(index, int) or index < 0 or index >= len(ts):
        raise ValueError("index out of range")
    return ts, index


def utilization(tasks):
    """Sum of C / T over the task list in one time unit, DM or any
    order; reported for context (deadlines differ from periods, so it
    is not a verdict, but U > 1 always ends in None)."""
    ts = _norm_tasks(tasks)
    return sum(t["C"] / t["T"] for t in ts)


def dm_priority_order(tasks):
    """Deadline-monotonic priority assignment: stable sort by D
    ascending, shorter deadline higher priority (index 0), equal
    deadlines keep their input order.  Returns copies with all five
    keys present."""
    ts = _norm_tasks(tasks)
    return sorted(ts, key=lambda t: t["D"])  # stable: ties keep order


def _interference_count(w, hp_task):
    """Releases of a jittered higher-priority task whose executions can
    fall inside a busy window of length w (Tindell and Clark 1994
    release-jitter treatment in the interference count)."""
    return math.ceil((w + hp_task["J"]) / hp_task["T"])


def _completion(tasks, index, q):
    """Fixed-point completion w_i(q) of job q of task `index` in the
    critical-instant busy period, or None when a job response crosses
    D_i or the pass cap is hit.

    w = (q + 1) * C_i + sum over hp of ceil((w + J_j) / T_j) * C_j,
    iterated from w = (q + 1) * C_i.  Job q releases at q * T_i, so its
    response w - q * T_i must stay within D_i: the bound is
    w <= q * T_i + D_i.  The sequence is monotone non-decreasing, so an
    iterate past the bound can never converge under it (None).
    """
    task = tasks[index]
    own = (q + 1) * task["C"]
    bound = q * task["T"] + task["D"]
    hp = tasks[:index]
    w = own
    if w > bound:
        return None
    for _ in range(MAX_RTA_ITERATIONS):
        nxt = own + sum(_interference_count(w, t) * t["C"] for t in hp)
        if nxt > bound:
            return None          # crossed D_i: cannot converge under it
        if abs(nxt - w) <= CONVERGENCE_TOL:
            return nxt
        w = nxt
    return None                  # pass cap: divergence


def response_time(tasks, index):
    """Exact worst-case response time of task `index` of a
    deadline-monotonic-ordered list, or None when it is unschedulable.

    Constrained deadline (D <= T): the first-job completion w(0) is
    exact and sufficient, every later job starts a clean busy period.
    Arbitrary deadline (D > T): a first-job completion past T_i makes
    later jobs queue, and the exact response is the maximum of the
    busy-period job responses w(q) - q * T_i, scanned until
    w(q) <= (q + 1) * T_i ends the busy period.  Any job response past
    D_i, or a scan past MAX_BUSY_PERIOD_JOBS, returns None.
    """
    ts, index = _norm_one(tasks, index)
    task = ts[index]
    if task["D"] <= task["T"]:
        w0 = _completion(ts, index, 0)
        return None if w0 is None else w0
    # Arbitrary deadline: first-job completion, then the q-scan if
    # later jobs queue behind it.
    w0 = _completion(ts, index, 0)
    if w0 is None:
        return None
    if w0 <= task["T"]:
        return w0                # no queueing: first-job analysis exact
    worst = w0
    q = 1
    while q <= MAX_BUSY_PERIOD_JOBS:
        wq = _completion(ts, index, q)
        if wq is None:
            return None          # some queued job crossed D_i or diverged
        worst = max(worst, wq - q * task["T"])
        if wq <= (q + 1) * task["T"]:
            return worst         # busy period ended after job q
        q += 1
    return None                  # busy period never ends: over-subscribed


def dm_response_times(tasks):
    """Per-task worst-case responses over a deadline-monotonic-ordered
    list, with the feasible verdict (every response converged and at
    most its own deadline) and the total utilization."""
    ts = _norm_tasks(tasks)
    _check_dm_order(ts)
    names = [t["name"] for t in ts]
    resp = [response_time(ts, i) for i in range(len(ts))]
    feasible = all(
        r is not None and r <= ts[i]["D"] + CONVERGENCE_TOL
        for i, r in enumerate(resp))
    return {
        "names": names,
        "response_times": resp,
        "feasible": bool(feasible),
        "utilization": sum(t["C"] / t["T"] for t in ts),
    }


def feasible(tasks):
    """True when every converged response time is at most its own
    deadline; the whole-set feasible verdict of the DM-ordered list."""
    return dm_response_times(tasks)["feasible"]


def _busy_period_table(tasks, index):
    """Diagnostic rows (q, w(q), response w(q) - q * T_i) of the
    busy-period scan of one arbitrary-deadline task; module-internal,
    not part of the public API."""
    ts, index = _norm_one(tasks, index)
    task = ts[index]
    rows = []
    w0 = _completion(ts, index, 0)
    if w0 is None:
        return rows
    rows.append((0, w0, w0))
    if w0 <= task["T"]:
        return rows
    q = 1
    while q <= MAX_BUSY_PERIOD_JOBS:
        wq = _completion(ts, index, q)
        if wq is None:
            break
        rows.append((q, wq, wq - q * task["T"]))
        if wq <= (q + 1) * task["T"]:
            break
        q += 1
    return rows
