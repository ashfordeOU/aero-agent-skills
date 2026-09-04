"""Offline schedulability analysis for periodic hard-real-time task sets.

Pure Python stdlib, deterministic, no network. Implements the standard
public mathematics of Liu and Layland (1973) plus exact iterative
response-time analysis:

- utilization(tasks): U = sum(C_i / T_i).
- liu_layland_bound(n): U_rm(n) = n * (2**(1/n) - 1), the sufficient
  utilization bound for n rate-monotonic tasks.
- rm_ub_feasible(tasks): True when U <= U_rm(n) (sufficient test).
- rm_response_times(tasks): exact fixed-point response times R_i via
  R_i = C_i + sum_{j in hp(i)} ceil(R_i / T_j) * C_j, or None when the
  analysis diverges / a task cannot converge within its period.
- rm_feasible(tasks): exact RM verdict, R_i <= T_i for every task.
- edf_feasible(tasks): implicit-deadline EDF is feasible iff U <= 1
  (necessary and sufficient).
- scheduling_summary(tasks): convenience dict with every result above
  plus a single verdict string.

Conventions: a task set is a list of (C, T) pairs: worst-case execution
time C and period T, implicit deadline D = T, all in the same time unit.
Shorter period means higher priority under RM; equal periods are broken
by list index (the earlier task in the list is the higher priority).
Module constants: DIVERGENCE_CAP_FACTOR (cap = factor * max period) and
MAX_RTA_ITERATIONS, both documented below.
"""

import math

# Divergence cap: response-time iteration is abandoned when R_i grows
# past DIVERGENCE_CAP_FACTOR * max(T) (spec model: 1000 * max T).
DIVERGENCE_CAP_FACTOR = 1000.0
# Hard guard on the fixed-point iteration count (never reached for
# sane inputs; protects against pathological float task parameters).
MAX_RTA_ITERATIONS = 10000
# Response times are compared to periods with this relative slack.
_EPS = 1e-9


def _validate_tasks(tasks):
    """Validate a task set and return it as a list of (C, T) float pairs.

    Raises ValueError on an empty set, on entries that are not (C, T)
    pairs, on non-numeric or non-finite values, and on C <= 0 or T <= 0.
    """
    if not isinstance(tasks, (list, tuple)):
        raise ValueError("task set must be a list or tuple of (C, T) pairs")
    if len(tasks) == 0:
        raise ValueError("task set must not be empty")
    validated = []
    for item in tasks:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(
                "each task must be a (C, T) pair of positive execution "
                "time and period"
            )
        c, t = item
        if isinstance(c, bool) or isinstance(t, bool):
            raise ValueError("C and T must be real numbers, not booleans")
        if not isinstance(c, (int, float)) or not isinstance(t, (int, float)):
            raise ValueError("C and T must be real numbers")
        c = float(c)
        t = float(t)
        if not math.isfinite(c) or not math.isfinite(t):
            raise ValueError("C and T must be finite numbers")
        if c <= 0.0 or t <= 0.0:
            raise ValueError("execution time C and period T must be positive")
        validated.append((c, t))
    return validated


def utilization(tasks):
    """Return the total processor utilization U = sum(C_i / T_i).

    Raises ValueError on an empty or invalid task set.
    """
    validated = _validate_tasks(tasks)
    return sum(c / t for c, t in validated)


def liu_layland_bound(n):
    """Return the Liu-Layland sufficient bound U_rm(n) = n(2^(1/n) - 1).

    n is the number of tasks: it must be a positive integer (integral
    floats such as 3.0 are accepted). Raises ValueError on n < 1 and on
    non-integral or non-numeric n. The anchor values are
    U_rm(2) = 0.828427, U_rm(3) = 0.779763, U_rm(4) = 0.756828.
    """
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        raise ValueError("n must be a positive integer number of tasks")
    if isinstance(n, float):
        if n.is_integer():
            n = int(n)
        else:
            raise ValueError("n must be an integer task count, got %r" % n)
    if n < 1:
        raise ValueError("n must be >= 1 (a task set has at least one task)")
    return n * (2.0 ** (1.0 / n) - 1.0)


def _higher_priority_indices(periods, i):
    """Indices of tasks with higher priority than task i under RM.

    Task j has higher priority than task i when T_j < T_i, or when
    T_j == T_i and j appears earlier in the list (tie-break by index).
    """
    hp = []
    for j in range(len(periods)):
        if j == i:
            continue
        if periods[j] < periods[i] or (periods[j] == periods[i] and j < i):
            hp.append(j)
    return hp


def _response_time_single(c_i, t_i, hp_tasks):
    """Fixed-point response time of one task given its higher-priority set.

    Iterates R = C_i + sum_{j in hp} ceil(R / T_j) * C_j from R = C_i
    until a fixed point. Returns the converged R as a float, or None
    when the iteration grows past the divergence cap, exceeds the task
    period (the monotone iteration can then never return to a feasible
    value), or fails to settle within MAX_RTA_ITERATIONS steps.
    """
    cap = DIVERGENCE_CAP_FACTOR * t_i
    r = c_i
    for _ in range(MAX_RTA_ITERATIONS):
        r_next = c_i + sum(
            math.ceil(r / t_j) * c_j for c_j, t_j in hp_tasks
        )
        if r_next > t_i + _EPS or r_next > cap:
            # Crossing the deadline or the cap means the monotone
            # iteration cannot converge to a schedulable fixed point.
            return None
        if abs(r_next - r) <= _EPS:
            return float(r_next)
        r = r_next
    return None


def rm_response_times(tasks):
    """Return exact RM response times R_i for every task, or None.

    R_i = C_i + sum_{j in hp(i)} ceil(R_i / T_j) * C_j, iterated from
    R_i = C_i to a fixed point for each task in list order. Returns the
    list of converged R_i (floats; integral for integer (C, T) input)
    when every task converges within its period, and None when any task
    diverges (R exceeds 1000 * max period) or cannot converge within
    its own period, which makes the task set RM-infeasible.
    """
    validated = _validate_tasks(tasks)
    periods = [t for _, t in validated]
    result = []
    for i, (c_i, t_i) in enumerate(validated):
        hp = [(validated[j][0], validated[j][1])
              for j in _higher_priority_indices(periods, i)]
        r_i = _response_time_single(c_i, t_i, hp)
        if r_i is None:
            return None
        result.append(r_i)
    return result


def rm_ub_feasible(tasks):
    """Return True when U <= U_rm(n): the Liu-Layland sufficient test.

    A True verdict guarantees RM feasibility; a False verdict is
    inconclusive (use rm_feasible for the exact answer).
    """
    validated = _validate_tasks(tasks)
    return utilization(validated) <= liu_layland_bound(len(validated))


def rm_feasible(tasks):
    """Return the exact RM feasibility verdict from response-time analysis.

    True iff every task's converged response time satisfies R_i <= T_i.
    Divergence (rm_response_times returning None) means infeasible.
    """
    response_times = rm_response_times(tasks)
    if response_times is None:
        return False
    validated = _validate_tasks(tasks)
    return all(
        r <= t + _EPS for r, (_, t) in zip(response_times, validated)
    )


def edf_feasible(tasks):
    """Return True when the task set is feasible under EDF (U <= 1).

    For implicit-deadline periodic tasks EDF is optimal, so U <= 1 is
    both necessary and sufficient.
    """
    validated = _validate_tasks(tasks)
    return utilization(validated) <= 1.0 + _EPS


def scheduling_summary(tasks):
    """Return the convenience verdict dict for a task set.

    Keys (exact and documented): utilization, n_tasks,
    liu_layland_bound, rm_ub_verdict, rm_exact_response_times,
    rm_exact_feasible, edf_feasible, verdict.

    verdict is one of:
    - "RM-guaranteed-by-UB": U <= U_rm(n), RM feasible by the bound.
    - "RM-exact-feasible (UB inconclusive)": RTA converges within every
      period although the utilization bound was not met.
    - "EDF-feasible-only": RM is infeasible but EDF can schedule U <= 1.
    - "RM-infeasible": neither RM (exact) nor EDF can schedule the set.
    """
    validated = _validate_tasks(tasks)
    u = utilization(validated)
    n = len(validated)
    ll_bound = liu_layland_bound(n)
    ub_verdict = u <= ll_bound
    response_times = rm_response_times(validated)
    exact_feasible = (
        response_times is not None
        and all(r <= t + _EPS for r, (_, t) in zip(response_times, validated))
    )
    edf_ok = u <= 1.0 + _EPS
    if exact_feasible:
        if ub_verdict:
            verdict = "RM-guaranteed-by-UB"
        else:
            verdict = "RM-exact-feasible (UB inconclusive)"
    elif edf_ok:
        verdict = "EDF-feasible-only"
    else:
        verdict = "RM-infeasible"
    return {
        "utilization": u,
        "n_tasks": n,
        "liu_layland_bound": ll_bound,
        "rm_ub_verdict": ub_verdict,
        "rm_exact_response_times": response_times,
        "rm_exact_feasible": exact_feasible,
        "edf_feasible": edf_ok,
        "verdict": verdict,
    }
