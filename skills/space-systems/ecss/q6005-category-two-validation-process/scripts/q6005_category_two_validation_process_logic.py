"""Category-two validation of a non-approved hybrid supplier for one programme.

Anchor: ECSS-Q-ST-60-05 clause 6.3 (the steps followed to qualify a hybrid
supplier that holds no line approval, for use on a given programme).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the process as a step registry with prerequisites and nominal
   durations, and prove the registry is a workable order at all - no unknown
   prerequisite, no step waiting on itself, no cycle.
2. Validate the declared state of every step against that registry.
3. Detect ordering defects: a step reported started or finished while a step
   it depends on is not finished is a process defect, not progress.
4. Work out what is still to do - the longest remaining chain through the
   unfinished steps, which is the earliest the validation can close, not the
   sum of the outstanding work.
5. Date that chain from the start date and compare it with the date the
   programme needs the supplier, in whole days.
6. Roll the whole thing up into one verdict, and refuse to let a validation
   earned on another programme carry over to this one.
"""

import datetime

__all__ = [
    "VALIDATION_STEPS",
    "STEP_STATUSES",
    "parse_date",
    "validate_registry",
    "topological_order",
    "validate_step_states",
    "ordering_defects",
    "ready_steps",
    "outstanding_steps",
    "remaining_days",
    "critical_chain",
    "earliest_completion_days",
    "earliest_completion_date",
    "programme_margin_days",
    "reuse_admissible",
    "validation_verdict",
    "assess_category_two_validation",
]

# The category-two validation process. Each step names the steps that must be
# finished before it can start, and the nominal working days it takes.
VALIDATION_STEPS = {
    "programme-applicability-review": {"requires": (), "nominal_days": 10},
    "supplier-survey": {"requires": ("programme-applicability-review",), "nominal_days": 20},
    "element-procurement-review": {
        "requires": ("programme-applicability-review",),
        "nominal_days": 25,
    },
    "process-identification-audit": {"requires": ("supplier-survey",), "nominal_days": 15},
    "validation-lot-build": {
        "requires": ("process-identification-audit", "element-procurement-review"),
        "nominal_days": 45,
    },
    "validation-lot-testing": {"requires": ("validation-lot-build",), "nominal_days": 40},
    "destructive-physical-analysis": {"requires": ("validation-lot-testing",), "nominal_days": 20},
    "validation-report-review": {
        "requires": ("destructive-physical-analysis",),
        "nominal_days": 15,
    },
    "programme-authority-agreement": {"requires": ("validation-report-review",), "nominal_days": 10},
}

STEP_STATUSES = ("not-started", "in-progress", "complete", "failed")


def parse_date(value, label="date"):
    """Return value as a calendar date; accept a date or an ISO date string."""
    if isinstance(value, datetime.datetime):
        raise ValueError("%s must be a calendar date, not a timestamp" % label)
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO calendar date: %r" % (label, value))


def validate_registry(registry=None):
    """Return the registry after proving it is a usable dependency graph."""
    reg = VALIDATION_STEPS if registry is None else registry
    if not isinstance(reg, dict) or not reg:
        raise ValueError("step registry must be a non-empty mapping")
    for step, spec in reg.items():
        if not isinstance(step, str) or not step.strip():
            raise ValueError("step name must be a non-empty string, got %r" % (step,))
        if not isinstance(spec, dict):
            raise ValueError("step %r must map to a spec mapping" % (step,))
        for key in ("requires", "nominal_days"):
            if key not in spec:
                raise ValueError("step %r spec omits '%s'" % (step, key))
        requires = spec["requires"]
        if not isinstance(requires, (list, tuple)):
            raise ValueError("step %r 'requires' must be a sequence" % (step,))
        for prereq in requires:
            if prereq == step:
                raise ValueError("step %r requires itself" % (step,))
            if prereq not in reg:
                raise ValueError("step %r requires unknown step %r" % (step, prereq))
        days = spec["nominal_days"]
        if not isinstance(days, int) or isinstance(days, bool):
            raise ValueError("step %r nominal_days must be a whole number of days" % (step,))
        if days <= 0:
            raise ValueError("step %r nominal_days must be positive, got %d" % (step, days))
    return reg


def topological_order(registry=None):
    """Return the steps in an order that never precedes a prerequisite."""
    reg = validate_registry(registry)
    resolved = []
    seen = set(reg)
    remaining = dict((s, set(reg[s]["requires"])) for s in reg)
    while remaining:
        ready = [s for s in reg if s in remaining and not (remaining[s] - set(resolved))]
        if not ready:
            raise ValueError(
                "step registry contains a cycle among %s" % ", ".join(sorted(remaining))
            )
        for step in ready:
            resolved.append(step)
            del remaining[step]
    if set(resolved) != seen:
        raise ValueError("topological order did not cover the registry")
    return tuple(resolved)


def validate_step_states(states, registry=None):
    """Return the validated {step: status} record of the validation process."""
    reg = validate_registry(registry)
    if not isinstance(states, dict) or not states:
        raise ValueError("step states must be a non-empty mapping")
    validated = {}
    for step, status in states.items():
        if step not in reg:
            raise ValueError("unknown validation step %r" % (step,))
        if not isinstance(status, str):
            raise ValueError("step %r needs a string status, got %r" % (step, status))
        lowered = status.strip().lower()
        if lowered not in STEP_STATUSES:
            raise ValueError("step %r has an unknown status %r" % (step, status))
        validated[step] = lowered
    missing = [s for s in reg if s not in validated]
    if missing:
        raise ValueError("step states omit %s" % ", ".join(missing))
    return validated


def ordering_defects(states, registry=None):
    """Return (step, unmet prerequisite) pairs where the order was broken."""
    reg = validate_registry(registry)
    validated = validate_step_states(states, reg)
    defects = []
    for step in topological_order(reg):
        if validated[step] in ("complete", "in-progress"):
            for prereq in reg[step]["requires"]:
                if validated[prereq] != "complete":
                    defects.append((step, prereq))
    return tuple(defects)


def ready_steps(states, registry=None):
    """Return the not-started steps whose prerequisites are all finished."""
    reg = validate_registry(registry)
    validated = validate_step_states(states, reg)
    return tuple(
        step
        for step in topological_order(reg)
        if validated[step] == "not-started"
        and all(validated[p] == "complete" for p in reg[step]["requires"])
    )


def outstanding_steps(states, registry=None):
    """Return the steps that are not finished, in dependency order."""
    reg = validate_registry(registry)
    validated = validate_step_states(states, reg)
    return tuple(s for s in topological_order(reg) if validated[s] != "complete")


def remaining_days(states, overrides=None, registry=None):
    """Return {step: working days still to spend on it}."""
    reg = validate_registry(registry)
    validated = validate_step_states(states, reg)
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        raise ValueError("overrides must be a mapping of step to remaining days")
    for step, value in overrides.items():
        if step not in reg:
            raise ValueError("override names unknown step %r" % (step,))
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("override for %r must be a whole number of days" % (step,))
        if value < 0:
            raise ValueError("override for %r must not be negative" % (step,))
    out = {}
    for step in topological_order(reg):
        if validated[step] == "complete":
            out[step] = 0
        elif step in overrides:
            out[step] = overrides[step]
        else:
            out[step] = reg[step]["nominal_days"]
    return out


def _finish_times(states, overrides=None, registry=None):
    """Return ({step: earliest finish in days}, {step: driving prerequisite})."""
    reg = validate_registry(registry)
    left = remaining_days(states, overrides, reg)
    finish = {}
    driver = {}
    for step in topological_order(reg):
        best_start = 0
        best_prereq = None
        for prereq in reg[step]["requires"]:
            if finish[prereq] > best_start:
                best_start = finish[prereq]
                best_prereq = prereq
            elif best_prereq is None and finish[prereq] == best_start:
                best_prereq = prereq
        finish[step] = best_start + left[step]
        driver[step] = best_prereq
    return (finish, driver)


def earliest_completion_days(states, overrides=None, registry=None):
    """Return the working days from now until the validation can close."""
    finish, _ = _finish_times(states, overrides, registry)
    return max(finish.values())


def critical_chain(states, overrides=None, registry=None):
    """Return the chain of steps that sets the earliest completion."""
    reg = validate_registry(registry)
    finish, driver = _finish_times(states, overrides, reg)
    left = remaining_days(states, overrides, reg)
    horizon = max(finish.values())
    if horizon == 0:
        return ()
    tail = None
    for step in topological_order(reg):
        if finish[step] == horizon:
            tail = step
            break
    chain = []
    step = tail
    while step is not None:
        chain.append(step)
        step = driver[step]
    chain.reverse()
    return tuple(s for s in chain if left[s] > 0)


def earliest_completion_date(start_date, states, overrides=None, registry=None):
    """Return the calendar date the validation can close from start_date."""
    start = parse_date(start_date, "start_date")
    return start + datetime.timedelta(days=earliest_completion_days(states, overrides, registry))


def programme_margin_days(completion_date, programme_need_date):
    """Return days of slack between validation close and the programme need."""
    done = parse_date(completion_date, "completion_date")
    need = parse_date(programme_need_date, "programme_need_date")
    return (need - done).days


def reuse_admissible(previous_validation_programme, programme):
    """Return True only when a held validation belongs to this programme."""
    if not isinstance(programme, str) or not programme.strip():
        raise ValueError("programme must be a non-empty string")
    if previous_validation_programme is None:
        return False
    if not isinstance(previous_validation_programme, str):
        raise ValueError("previous_validation_programme must be a string or None")
    return previous_validation_programme.strip().lower() == programme.strip().lower()


def validation_verdict(states, registry=None):
    """Return the roll-up verdict of the validation process."""
    reg = validate_registry(registry)
    validated = validate_step_states(states, reg)
    if any(v == "failed" for v in validated.values()):
        return "failed"
    if ordering_defects(validated, reg):
        return "ordering-defect"
    if all(v == "complete" for v in validated.values()):
        return "validated"
    if all(v == "not-started" for v in validated.values()):
        return "not-started"
    return "in-progress"


def assess_category_two_validation(spec):
    """Run the full clause 6.3 category-two validation assessment.

    spec keys: programme, steps, start_date, programme_need_date, optional
    remaining_overrides and previous_validation_programme.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("programme", "steps", "start_date", "programme_need_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    programme = spec["programme"]
    if not isinstance(programme, str) or not programme.strip():
        raise ValueError("programme must be a non-empty string")
    states = validate_step_states(spec["steps"])
    start = parse_date(spec["start_date"], "start_date")
    need = parse_date(spec["programme_need_date"], "programme_need_date")
    if need < start:
        raise ValueError("programme_need_date precedes start_date")
    overrides = spec.get("remaining_overrides")
    left = remaining_days(states, overrides)
    defects = ordering_defects(states)
    verdict = validation_verdict(states)
    horizon = earliest_completion_days(states, overrides)
    completion = start + datetime.timedelta(days=horizon)
    margin = programme_margin_days(completion, need)
    chain = critical_chain(states, overrides)
    carried = spec.get("previous_validation_programme")
    reusable = reuse_admissible(carried, programme)
    findings = []
    failed = tuple(s for s in topological_order() if states[s] == "failed")
    if failed:
        findings.append("validation step(s) recorded as failed: %s" % ", ".join(failed))
    for step, prereq in defects:
        findings.append("step %s was started before its prerequisite %s finished" % (step, prereq))
    if carried is not None and not reusable:
        findings.append(
            "a validation held for programme %s does not carry over to %s; the process "
            "is run again for this programme" % (carried, programme)
        )
    if margin < 0:
        findings.append(
            "the validation closes %d day(s) after the programme needs the supplier"
            % (-margin,)
        )
    if verdict == "not-started":
        findings.append("no validation step has been opened yet")
    return {
        "programme": programme,
        "order": topological_order(),
        "states": states,
        "verdict": verdict,
        "ordering_defects": defects,
        "ready_steps": ready_steps(states),
        "outstanding_steps": outstanding_steps(states),
        "remaining_days": left,
        "critical_chain": chain,
        "earliest_completion_days": horizon,
        "earliest_completion_date": completion,
        "programme_margin_days": margin,
        "previous_validation_reusable": reusable,
        "findings": findings,
    }
