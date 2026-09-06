"""Fixed-priority aperiodic server scheduling for avionics flight software.

Pure stdlib, closed form. Inserts a fixed-priority aperiodic server
(capacity C_s, period T_s) with polling-server, deferrable-server or
sporadic-server budget semantics into a periodic hard-real-time task set
so the aperiodic and event-driven jobs of an avionics task set get a
bounded worst-case service without breaking any periodic deadline.

The event load is given as (s, a) streams of worst-case execution s over
minimum inter-arrival a, reduced to the load utilization u_a = sum(s/a).
The server budget is sized from that load (U_s = u_a + margin,
C_s = U_s * T_s, U_s capped at 1) and folded into the fixed-priority
response-time analysis exactly as a periodic task (C_s, T_s) at its
priority slot. Mechanism comparison and aperiodic worst-case response
bounds use the published polling, deferrable and sporadic server
semantics (Sprunt, Sha and Lehoczky 1989; Lehoczky, Sha and Strosnider
1987), summary mathematics only.

Imports math only. Deterministic: no randomness, no network, no external
processes.
"""

import math

MAX_RTA_ITERATIONS = 100  # fixed-point safety cap for the RTA passes


def _is_real_number(value):
    """True for an int or float that is not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_pair(entry, what):
    """Return the (x, y) pair of a validated (execution, period)-style entry."""
    if not isinstance(entry, (tuple, list)) or len(entry) != 2:
        raise ValueError("each %s entry must be a two-value (x, y) pair" % what)
    x, y = entry
    if not _is_real_number(x) or not _is_real_number(y):
        raise ValueError("each %s entry must hold two real numbers" % what)
    if x <= 0 or y <= 0:
        raise ValueError("both values of a %s entry must be positive" % what)
    return x, y


def periodic_utilization(tasks):
    """Sum of C/T over the periodic (C, T) task list, RM order (index 0
    highest priority), implicit deadlines D = T."""
    if not tasks:
        raise ValueError("the periodic task list must not be empty")
    pairs = [_require_pair(task, "task") for task in tasks]
    return sum(c / t for c, t in pairs)


def aperiodic_utilization(streams):
    """Load utilization sum(s/a) over the (s, a) event streams; an empty
    stream list carries zero load."""
    if not streams:
        return 0.0
    pairs = [_require_pair(stream, "stream") for stream in streams]
    return sum(s / a for s, a in pairs)


def server_parameters(u_a, t_s, margin=0.0):
    """Size the aperiodic server: U_s = u_a + margin, C_s = U_s * T_s."""
    if u_a < 0 or margin < 0 or t_s <= 0:
        raise ValueError("u_a, margin and T_s must be non-negative with T_s > 0")
    u_s = u_a + margin
    if u_s > 1:
        raise ValueError("server utilization u_a + margin must not exceed 1")
    c_s = u_s * t_s
    if c_s == 0:
        raise ValueError("server capacity is zero (u_a and margin both zero)")
    return {"period": t_s, "capacity": c_s, "utilization": u_s}


def _validate_server_call(t_s, c_s, c_a, phase):
    """Shared ValueError checks of the single-job response functions."""
    if t_s <= 0 or c_s <= 0 or c_a <= 0:
        raise ValueError("T_s, C_s and C_a must all be positive")
    if c_a > c_s:
        raise ValueError("the job execution C_a must not exceed the capacity C_s")
    if phase < 0 or phase >= t_s:
        raise ValueError("phase must lie in [0, T_s)")


def polling_server_response(t_s, c_s, c_a, phase=0.0):
    """Single-job response under the polling server with an empty queue
    and an available budget: C_a exactly at a poll instant (phase 0.0),
    else (T_s - phase) + C_a waiting for the next poll."""
    _validate_server_call(t_s, c_s, c_a, phase)
    if phase == 0.0:
        return float(c_a)
    return (t_s - phase) + c_a


def deferrable_server_response(t_s, c_s, c_a, phase=0.0):
    """Single-job response under the deferrable server with an unspent
    budget: C_a at every phase (capacity preservation). The phase is
    validated for interface parity and does not change the result."""
    _validate_server_call(t_s, c_s, c_a, phase)
    return float(c_a)


def sporadic_server_response(t_s, c_s, c_a, phase=0.0):
    """Single-job response under the sporadic server with an available
    budget: C_a at every phase (the budget is never forfeited on
    idleness). Same ValueErrors as the polling response."""
    _validate_server_call(t_s, c_s, c_a, phase)
    return float(c_a)


def aperiodic_response_bound(t_s, c_s, demand):
    """Worst-case response bound of the final unit of service of a burst
    of total demand `demand` (each job at most C_s): k = ceil(d/C_s)
    windows are needed and the final unit completes at
    k * T_s + demand - (k - 1) * C_s after the arrival."""
    if t_s <= 0 or c_s <= 0 or demand <= 0:
        raise ValueError("T_s, C_s and demand must all be positive")
    k = math.ceil(demand / c_s)
    return k * t_s + demand - (k - 1) * c_s


def replenishment_wait(kind, t_s, start, end):
    """Wait from the end of a full-budget consumption [start, end] until
    the budget is next fully available: polling and deferrable wait for
    the next poll or period start, ceil(end/T_s) * T_s - end; sporadic
    replenishes T_s after the consumption started, T_s - (end - start)."""
    if kind not in ("polling", "deferrable", "sporadic"):
        raise ValueError("kind must be polling, deferrable or sporadic")
    if t_s <= 0 or start < 0 or end <= start:
        raise ValueError("need T_s > 0 and 0 <= start < end")
    if end - start > t_s:
        raise ValueError("the consumption must not be longer than T_s")
    if kind == "sporadic":
        return t_s - (end - start)
    return math.ceil(end / t_s) * t_s - end


def _validate_task_list(tasks):
    """Raise unless tasks is a non-empty list of valid (C, T) pairs."""
    if not tasks:
        raise ValueError("the periodic task list must not be empty")
    for task in tasks:
        _require_pair(task, "task")


def _validate_server_dict(server):
    """Return the (c_s, t_s) of a valid server dict (capacity <= period)."""
    try:
        c_s = server["capacity"]
        t_s = server["period"]
    except (KeyError, TypeError):
        raise ValueError("server must be a dict with capacity and period keys")
    if not _is_real_number(c_s) or not _is_real_number(t_s):
        raise ValueError("server capacity and period must be real numbers")
    if c_s <= 0 or t_s <= 0:
        raise ValueError("server capacity and period must be positive")
    if c_s > t_s:
        raise ValueError("server capacity must not exceed the server period")
    return c_s, t_s


def _rta(execution, period, higher):
    """Fixed-point response time of a task of (execution, period) under
    the higher-priority (C, T) tasks; monotone non-decreasing, converged
    when an iterate repeats within 1e-12. Returns None when an iterate
    exceeds the task's own period or the MAX_RTA_ITERATIONS pass cap."""
    r = float(execution)
    for _ in range(MAX_RTA_ITERATIONS):
        nxt = execution + sum(math.ceil(r / t) * c for c, t in higher)
        if nxt > period:
            return None
        if abs(nxt - r) < 1e-12:
            return nxt
        r = nxt
    return None


def server_response_times(tasks, server, above_index):
    """Response-time analysis with the server budget inserted at the
    priority slot above_index in [0, len(tasks)]: tasks above it are
    untouched, the server sits between task above_index - 1 and task
    above_index, and tasks below it gain ceil(R_i / T_s) * C_s."""
    _validate_task_list(tasks)
    c_s, t_s = _validate_server_dict(server)
    if not isinstance(above_index, int) or isinstance(above_index, bool):
        raise ValueError("above_index must be an integer")
    if above_index < 0 or above_index > len(tasks):
        raise ValueError("above_index must lie in [0, len(tasks)]")

    def _higher_for(i):
        """Higher-priority interference list of task i with the server
        folded in below slot above_index."""
        higher = []
        for j in range(i):
            c_j, t_j = tasks[j]
            higher.append((c_j, t_j))
        if i >= above_index:
            higher.append((c_s, t_s))
        return higher

    server_r = _rta(c_s, t_s, list(tasks[0:above_index]))
    task_rs = []
    for i in range(len(tasks)):
        c_i, t_i = _require_pair(tasks[i], "task")
        task_rs.append(_rta(c_i, t_i, _higher_for(i)))
    feasible = server_r is not None and all(r is not None for r in task_rs)
    total_util = periodic_utilization(tasks) + c_s / t_s
    return {
        "above_index": above_index,
        "server_response_time": server_r,
        "task_response_times": task_rs,
        "feasible": feasible,
        "total_utilization": total_util,
    }


def place_server(tasks, server):
    """Scan the n + 1 priority slots from the highest (above_index 0,
    best aperiodic responsiveness) to the lowest (above_index n) and
    return the first feasible placement."""
    _validate_task_list(tasks)
    _validate_server_dict(server)
    for idx in range(len(tasks) + 1):
        result = server_response_times(tasks, server, idx)
        if result["feasible"]:
            return {
                "insertion_index": idx,
                "server_response_time": result["server_response_time"],
                "task_response_times": result["task_response_times"],
                "total_utilization": result["total_utilization"],
                "feasible": True,
            }
    raise ValueError(
        "no feasible insertion point for the server in the %d priority slots"
        % (len(tasks) + 1)
    )
