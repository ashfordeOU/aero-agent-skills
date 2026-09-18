"""GSE maintenance planning, post-maintenance reverification and readiness logic.

Anchor: ECSS-Q-ST-20C clause 5.8.9 -- maintenance of ground support equipment:
the planned maintenance the equipment is kept on, the calibration or inspection
that follows an intervention before the equipment is used again, and the
records that show it is still ready. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each planned maintenance task against its own basis, since a task
   driven by calendar days and one driven by operating hours are not measured
   with the same clock.
2. Compute, per task, how much of its interval has been consumed and by how
   much it is overdue, treating a task that lands exactly on its interval as
   due rather than late.
3. Derive the reverification each intervention owes from what the intervention
   touched: a measuring chain owes recalibration, a load path owes a proof
   reverification, a pressure boundary owes a pressure re-test, control
   software owes a functional re-test.
4. Name every derived reverification that has not been completed, because the
   equipment goes back into service the moment somebody signs it off.
5. Combine the overdue tasks, the outstanding reverifications and the state of
   the readiness record into a single readiness verdict.
"""

import math

__all__ = [
    "INTERVAL_BASES",
    "INTERVENTION_REVERIFICATIONS",
    "DUE_TOLERANCE",
    "normalize_token",
    "validate_task",
    "task_status",
    "maintenance_findings",
    "required_reverifications",
    "reverification_findings",
    "readiness_verdict",
    "assess_gse_maintenance",
]

# The two clocks a planned maintenance task can be driven by.
INTERVAL_BASES = ("calendar-days", "operating-hours")

# What an intervention owes before the equipment goes back into service,
# keyed by the part of the equipment the intervention touched.
INTERVENTION_REVERIFICATIONS = {
    "measuring-chain": "recalibration",
    "load-path": "proof-load-reverification",
    "pressure-boundary": "pressure-re-test",
    "control-software": "functional-re-test",
    "structural-interface": "dimensional-inspection",
    "electrical-supply": "electrical-safety-re-test",
}

# A task landing exactly on its interval is due, not overdue; the last few bits
# of an elapsed-time subtraction are absorbed here.
DUE_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(value, label):
    v = _real(value, label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(value, label):
    v = _real(value, label)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_task(task):
    """Return the validated planned maintenance task record."""
    if not isinstance(task, dict):
        raise ValueError("task must be a mapping")
    for key in ("id", "basis", "interval", "since_last"):
        if key not in task:
            raise ValueError("task is missing '%s'" % key)
    basis = normalize_token(task["basis"], "task basis")
    if basis not in INTERVAL_BASES:
        raise ValueError("task basis %r is not a maintenance interval basis" % basis)
    return {
        "id": normalize_token(task["id"], "task id"),
        "basis": basis,
        "interval": _positive(task["interval"], "task interval"),
        "since_last": _non_negative(task["since_last"], "task since_last"),
        "safety_critical": _flag(
            task.get("safety_critical", False), "task safety_critical"
        ),
    }


def task_status(task):
    """Return how far through its interval one maintenance task has run."""
    record = validate_task(task)
    consumed = record["since_last"] / record["interval"]
    overdue_by = record["since_last"] - record["interval"]
    on_interval = math.isclose(
        record["since_last"], record["interval"], rel_tol=0.0, abs_tol=DUE_TOLERANCE
    )
    if on_interval:
        state = "due"
        overdue_by = 0.0
    elif overdue_by > 0.0:
        state = "overdue"
    else:
        state = "within-interval"
    return {
        "id": record["id"],
        "basis": record["basis"],
        "consumed_fraction": consumed,
        "overdue_by": overdue_by,
        "state": state,
        "safety_critical": record["safety_critical"],
    }


def maintenance_findings(tasks):
    """Return the findings the planned maintenance schedule raises."""
    if not isinstance(tasks, (list, tuple)):
        raise ValueError("tasks must be a sequence of maintenance task records")
    seen = set()
    findings = []
    statuses = []
    for task in tasks:
        status = task_status(task)
        if status["id"] in seen:
            raise ValueError("maintenance task %r is listed twice" % status["id"])
        seen.add(status["id"])
        statuses.append(status)
        if status["state"] == "overdue":
            findings.append(
                "maintenance task %s is overdue by %g %s"
                % (status["id"], status["overdue_by"], status["basis"])
            )
        elif status["state"] == "due" and status["safety_critical"]:
            findings.append(
                "safety-critical maintenance task %s has reached its interval" % status["id"]
            )
    return {"statuses": statuses, "findings": findings}


def required_reverifications(interventions):
    """Return the reverifications the interventions carried out owe."""
    if not isinstance(interventions, (list, tuple)):
        raise ValueError("interventions must be a sequence of touched-part names")
    required = []
    for i, intervention in enumerate(interventions):
        token = normalize_token(intervention, "interventions[%d]" % i)
        if token not in INTERVENTION_REVERIFICATIONS:
            raise ValueError(
                "interventions[%d] names %r, which is not a maintained part" % (i, token)
            )
        action = INTERVENTION_REVERIFICATIONS[token]
        if action not in required:
            required.append(action)
    return required


def reverification_findings(required, completed):
    """Return the post-maintenance reverifications that are still outstanding."""
    if not isinstance(required, (list, tuple)):
        raise ValueError("required must be a sequence of reverification names")
    if not isinstance(completed, (list, tuple)):
        raise ValueError("completed must be a sequence of reverification names")
    done = {normalize_token(c, "completed reverification") for c in completed}
    findings = []
    for action in required:
        token = normalize_token(action, "required reverification")
        if token not in done:
            findings.append(
                "%s is owed after maintenance and has not been carried out" % token
            )
    return findings


def readiness_verdict(findings, readiness_record_current):
    """Return the continued-readiness verdict for the equipment."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    current = _flag(readiness_record_current, "readiness_record_current")
    if findings:
        return "not-ready"
    if not current:
        return "ready-pending-record"
    return "ready"


def assess_gse_maintenance(spec):
    """Run the full clause 5.8.9 GSE maintenance and readiness assessment.

    spec keys: tasks, interventions, completed_reverifications,
    readiness_record_current.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "tasks",
        "interventions",
        "completed_reverifications",
        "readiness_record_current",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    maintenance = maintenance_findings(spec["tasks"])
    required = required_reverifications(spec["interventions"])
    outstanding = reverification_findings(required, spec["completed_reverifications"])
    findings = list(maintenance["findings"]) + list(outstanding)
    return {
        "statuses": maintenance["statuses"],
        "maintenance_findings": maintenance["findings"],
        "required_reverifications": required,
        "reverification_findings": outstanding,
        "findings": findings,
        "verdict": readiness_verdict(findings, spec["readiness_record_current"]),
    }
