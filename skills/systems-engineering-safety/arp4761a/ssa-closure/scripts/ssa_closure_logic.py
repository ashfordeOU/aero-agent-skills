"""ssa_closure_logic.py

Post-implementation system safety assessment close-out over the assessed
condition set, pure stdlib, deterministic.

ARP4761A-style severity classes carry quantitative probability targets
per flight hour (name and paraphrase only, never reproduced verbatim):
catastrophic 1e-9, hazardous 1e-7, major 1e-5, minor 1e-3. For each
assessed condition the analyst supplies a predicted probability q per
flight hour (for example from an updated fault tree run on the
implemented system). The per-condition margin is target / q with a
strict meets verdict (q < target, so equality fails), and the
multi-condition closure rollup aggregates the per-condition verdicts
into the closed and open counts, the open condition ids in input order,
the per-severity-class closure fraction and the overall closure-gate
verdict. The safety requirement verification statuses roll up into the
verified/open requirement closure list that gates the close-out
statement alongside the closure-gate verdict.

Non-physical inputs raise ValueError. See the SKILL.md contract test
scripts/test_ssa_closure.py for the worked-example anchors.
"""

SEVERITY_ORDER = ("catastrophic", "hazardous", "major", "minor")

TARGET_CATASTROPHIC = 1e-9
TARGET_HAZARDOUS = 1e-7
TARGET_MAJOR = 1e-5
TARGET_MINOR = 1e-3

TARGETS = {
    "catastrophic": TARGET_CATASTROPHIC,
    "hazardous": TARGET_HAZARDOUS,
    "major": TARGET_MAJOR,
    "minor": TARGET_MINOR,
}

VALID_STATUSES = ("verified", "open")


def _as_float(value, label):
    """Coerce value to float, raising ValueError for non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric" % label) from None


def severity_target(severity):
    """Probability target per flight hour for one severity class.

    Workflow step 2 of the SKILL.md, the severity-class target lookup,
    is implemented here: the severity string maps onto its
    module-constant quantitative target. Accepts exactly "catastrophic",
    "hazardous", "major" and "minor". Any other string, including
    "no safety effect" (a class that carries no quantitative target and
    therefore cannot be closed against a number), raises ValueError;
    the match is exact, so whitespace variants are rejected too.
    """
    if severity not in TARGETS:
        raise ValueError(
            "severity must be one of catastrophic, hazardous, major, "
            "minor; got %r. 'no safety effect' carries no quantitative "
            "target per flight hour and cannot be closed" % (severity,)
        )
    return TARGETS[severity]


def condition_margin(predicted_q, severity):
    """Per-condition margin and strict meets verdict for one condition.

    Workflow step 3 of the SKILL.md, the per-condition margin pass over
    the assessed conditions, is implemented here for a single condition
    with the analyst-supplied predicted probability predicted_q per
    flight hour and its severity class. Returns {"meets": predicted_q <
    target, "margin": target / predicted_q}; the comparison is strict
    (equality fails, mirroring the strict-target rule that 1e-3 does not
    meet a Minor target) and the margin is 1.0 exactly at equality.
    Raises ValueError when predicted_q is not positive or the severity
    class is unknown.
    """
    q = _as_float(predicted_q, "predicted_q")
    if q <= 0:
        raise ValueError("predicted_q must be > 0, got %r" % q)
    target = severity_target(severity)
    return {"meets": q < target, "margin": target / q}


def _validated_conditions(conditions):
    """Validate the assessed condition list, returning normalized rows.

    Returns a list of (condition_id, severity, predicted_q) tuples in
    input order. Raises ValueError when the list is empty, any element
    is not a dict with id, severity and predicted_q keys, any severity
    class is unknown, or any predicted_q is not positive.
    """
    if not conditions:
        raise ValueError("conditions must not be empty: nothing to close")
    out = []
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValueError(
                "each condition must be a dict with id, severity, "
                "predicted_q"
            )
        missing = [
            key
            for key in ("id", "severity", "predicted_q")
            if key not in condition
        ]
        if missing:
            raise ValueError(
                "condition missing keys: %s" % ", ".join(missing)
            )
        q = _as_float(condition["predicted_q"], "predicted_q")
        severity_target(condition["severity"])  # validates the class
        if q <= 0:
            raise ValueError("predicted_q must be > 0, got %r" % q)
        out.append((condition["id"], condition["severity"], q))
    return out


def closure_rollup(conditions):
    """Roll the assessed conditions into the closure-gate verdict dict.

    Workflow step 4 of the SKILL.md, the multi-condition closure rollup
    of the per-condition margins and meets verdicts, is implemented
    here. conditions is a list of dicts {id, severity, predicted_q}.
    Returns {"total": n, "closed": number of conditions meeting their
    target, "open": number missing it, "open_conditions": the failing
    condition ids in input order, "meets_by_severity": {severity:
    closed / total for that class}, "overall_gate": "CLOSED" when every
    condition meets its target else "OPEN"}. Only severities present in
    the input appear in meets_by_severity, ordered catastrophic,
    hazardous, major, minor. Raises ValueError for an empty condition
    list, an unknown severity class or a non-positive predicted_q.
    """
    validated = _validated_conditions(conditions)
    class_counts = {}
    closed = 0
    open_conditions = []
    for condition_id, severity, q in validated:
        target = severity_target(severity)
        meets = q < target
        counts = class_counts.setdefault(severity, [0, 0])
        counts[1] += 1
        if meets:
            closed += 1
            counts[0] += 1
        else:
            open_conditions.append(condition_id)
    meets_by_severity = {}
    for severity in SEVERITY_ORDER:
        if severity in class_counts:
            closed_n, class_total = class_counts[severity]
            meets_by_severity[severity] = closed_n / class_total
    return {
        "total": len(validated),
        "closed": closed,
        "open": len(open_conditions),
        "open_conditions": open_conditions,
        "meets_by_severity": meets_by_severity,
        "overall_gate": "CLOSED" if not open_conditions else "OPEN",
    }


def requirement_closure(requirements):
    """Roll the verification statuses into the requirement closure list.

    Workflow step 5 of the SKILL.md, the requirement status rollup of
    the safety requirement verification statuses, is implemented here.
    requirements is a list of dicts {id, status} with status "verified"
    or "open". Returns {"total", "verified", "open",
    "open_requirements"} with the open ids in input order. An empty
    list is valid and returns zeros with an empty open_requirements.
    Raises ValueError on any status outside {"verified", "open"}.
    """
    if not requirements:
        return {
            "total": 0,
            "verified": 0,
            "open": 0,
            "open_requirements": [],
        }
    verified = 0
    open_requirements = []
    for item in requirements:
        if not isinstance(item, dict) or "id" not in item:
            raise ValueError(
                "each requirement must be a dict with id and status"
            )
        status = item["status"]
        if status not in VALID_STATUSES:
            raise ValueError(
                "status must be 'verified' or 'open', got %r" % (status,)
            )
        if status == "verified":
            verified += 1
        else:
            open_requirements.append(item["id"])
    return {
        "total": len(requirements),
        "verified": verified,
        "open": len(open_requirements),
        "open_requirements": open_requirements,
    }
