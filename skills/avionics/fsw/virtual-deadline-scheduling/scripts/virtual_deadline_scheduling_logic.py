"""Offline dual-criticality EDF-VD schedulability for avionics task sets.

Pure Python stdlib, deterministic, no network. Implements the closed-form
utilization test of Baruah, Bonifaci, D'Angelo, Li, Marchetti-Spaccamela,
Megow and Stougie, "Scheduling Real-Time Mixed-Criticality Jobs", IEEE
Transactions on Computers 61(8):1140-1152, 2012 (the edf-vd / virtual-
deadline scheduling algorithm for the dual-criticality task model). Public
science, summary-only; no standard text reproduced.

Each task is a dict {name, criticality, C_LO, C_HI, T}: criticality is "LO"
or "HI", C_LO and C_HI are low- and high-criticality execution-time
estimates with C_HI at least C_LO (a LO task carries no high estimate, so
its C_HI must equal its C_LO), and T is the period with the implicit
deadline D = T. EDF is priority-free: there is no deadline key and no task
list order requirement.

Three per-mode demand sums drive the whole model:

  a = u_lo_lo = sum over LO tasks of C_LO / T
  b = u_hi_lo = sum over HI tasks of C_LO / T
  c = u_hi_hi = sum over HI tasks of C_HI / T

The common virtual-deadline factor x = b / (1 - a) shortens every HI
task's LO-mode deadline to x * T. The set is edf-vd feasible when both the
LO-mode condition (a + b / x <= 1) and the HI-mode condition
(c + a * x <= 1) hold at that factor.

Module constant TOL is the comparison tolerance used by every verdict: a
condition holds when its left side is at most its right side plus TOL.
"""

TOL = 1e-12

_REQUIRED_KEYS = ("criticality", "C_LO", "C_HI", "T")


def _validate_positive(value, key):
    """Return value if it is a positive, non-boolean real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a positive number, got %r" % (key, value))
    if value <= 0:
        raise ValueError("%s must be a positive number, got %s" % (key, float(value)))
    return float(value)


def _validate_task(task, index):
    """Validate one task dict and return a normalized copy.

    Raises ValueError on a non-dict entry, a missing required key, an
    unknown criticality word, a boolean or non-positive C_LO/C_HI/T,
    C_HI below C_LO, and a LO task whose C_HI differs from C_LO.
    """
    if not isinstance(task, dict):
        raise ValueError("task at index %d must be a dict" % index)
    missing = [k for k in _REQUIRED_KEYS if k not in task]
    if missing:
        raise ValueError("task %d missing key(s) %s" % (index, ", ".join(missing)))
    criticality = task["criticality"]
    if criticality not in ("LO", "HI"):
        raise ValueError("criticality must be 'LO' or 'HI', got %r" % criticality)
    c_lo = _validate_positive(task["C_LO"], "C_LO")
    c_hi = _validate_positive(task["C_HI"], "C_HI")
    t = _validate_positive(task["T"], "T")
    if c_hi < c_lo:
        raise ValueError(
            "C_HI must be at least C_LO, got C_HI %s with C_LO %s" % (c_hi, c_lo)
        )
    if criticality == "LO" and c_hi != c_lo:
        raise ValueError(
            "a LO-criticality task carries no high estimate: C_HI must "
            "equal C_LO, got C_HI %s with C_LO %s" % (c_hi, c_lo)
        )
    return {
        "name": task.get("name", "task"),
        "criticality": criticality,
        "C_LO": c_lo,
        "C_HI": c_hi,
        "T": t,
    }


def _validate_tasks(tasks):
    """Validate a task list and return the normalized list.

    Raises ValueError on an empty list. EDF is priority-free: no order
    check exists (step 1 of the SKILL.md workflow).
    """
    if not isinstance(tasks, (list, tuple)) or len(tasks) == 0:
        raise ValueError("task list must be a non-empty list")
    return [_validate_task(task, i) for i, task in enumerate(tasks)]


def _demand_sums(validated):
    """Return the per-mode demand sums (a, b, c) over a validated task list.

    Step 2 of the SKILL.md workflow: a = u_lo_lo, b = u_hi_lo, c = u_hi_hi.
    """
    a = sum(t["C_LO"] / t["T"] for t in validated if t["criticality"] == "LO")
    b = sum(t["C_LO"] / t["T"] for t in validated if t["criticality"] == "HI")
    c = sum(t["C_HI"] / t["T"] for t in validated if t["criticality"] == "HI")
    return a, b, c


def _factor(a, b, has_hi):
    """Return the virtual-deadline factor x for demand sums (a, b).

    Step 3 of the SKILL.md workflow: 1.0 when no HI task exists, None
    when a >= 1 with at least one HI task, else b / (1 - a).
    """
    if not has_hi:
        return 1.0
    if a >= 1.0:
        return None
    return b / (1.0 - a)


def utilizations(tasks):
    """Return the per-mode demand sums {u_lo_lo, u_hi_lo, u_hi_hi, u_lo, u_hi}.

    Step 2 of the SKILL.md workflow. ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, c = _demand_sums(validated)
    return {"u_lo_lo": a, "u_hi_lo": b, "u_hi_hi": c, "u_lo": a + b, "u_hi": c}


def virtual_deadline_factor(tasks):
    """Return the common virtual-deadline factor x, or None.

    Step 3 of the SKILL.md workflow. ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, _c = _demand_sums(validated)
    has_hi = any(t["criticality"] == "HI" for t in validated)
    return _factor(a, b, has_hi)


def virtual_deadlines(tasks):
    """Return {task name: x * T} for every HI task, or None when no factor.

    Step 4 of the SKILL.md workflow: an empty dict for an all-LO set, None
    when x is None. A task without a "name" key is keyed "task".
    ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, _c = _demand_sums(validated)
    hi_tasks = [t for t in validated if t["criticality"] == "HI"]
    x = _factor(a, b, bool(hi_tasks))
    if x is None:
        return None
    return {t["name"]: x * t["T"] for t in hi_tasks}


def lo_mode_feasible(tasks):
    """True iff the LO-mode demand condition a + b / x <= 1 holds.

    Step 5 of the SKILL.md workflow. False when no factor exists.
    ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, _c = _demand_sums(validated)
    has_hi = any(t["criticality"] == "HI" for t in validated)
    x = _factor(a, b, has_hi)
    if x is None:
        return False
    return a + b / x <= 1.0 + TOL


def hi_mode_feasible(tasks):
    """True iff the HI-mode demand condition c + a * x <= 1 holds.

    Step 6 of the SKILL.md workflow. Vacuously True for an all-LO set
    (no HI task to guarantee). ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, c = _demand_sums(validated)
    has_hi = any(t["criticality"] == "HI" for t in validated)
    if not has_hi:
        return True
    x = _factor(a, b, has_hi)
    if x is None:
        return False
    return c + a * x <= 1.0 + TOL


def edf_vd_report(tasks):
    """Return the whole edf-vd report dict for one task list.

    Step 7 of the SKILL.md workflow: gathers the per-mode demand sums,
    the virtual-deadline factor, the per-HI-task virtual deadlines, the
    lo-mode and hi-mode feasible verdicts, and the whole-set feasible
    verdict. ValueErrors of the task shape.
    """
    validated = _validate_tasks(tasks)
    a, b, c = _demand_sums(validated)
    hi_tasks = [t for t in validated if t["criticality"] == "HI"]
    has_hi = bool(hi_tasks)
    x = _factor(a, b, has_hi)
    if x is None:
        lo_feasible = False
        hi_feasible = False
        vdeadlines = None
    else:
        lo_feasible = a + b / x <= 1.0 + TOL
        hi_feasible = True if not has_hi else (c + a * x <= 1.0 + TOL)
        vdeadlines = {t["name"]: x * t["T"] for t in hi_tasks}
    return {
        "u_lo_lo": a,
        "u_hi_lo": b,
        "u_hi_hi": c,
        "u_lo": a + b,
        "u_hi": c,
        "x": x,
        "lo_feasible": lo_feasible,
        "hi_feasible": hi_feasible,
        "feasible": lo_feasible and hi_feasible,
        "virtual_deadlines": vdeadlines,
    }


def feasible(tasks):
    """Convenience: edf_vd_report(tasks)["feasible"].

    Step 8 of the SKILL.md workflow. Same ValueErrors.
    """
    return edf_vd_report(tasks)["feasible"]
