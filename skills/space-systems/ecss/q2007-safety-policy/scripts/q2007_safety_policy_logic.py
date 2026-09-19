"""Safety policy and safety objectives of a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.9.2 (safety policy and objectives: the
documented commitments of the centre and the targets it sets itself).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the policy statement: the commitments it has to carry, the level
   of management that approved it, whether it was communicated, and whether
   it is still inside its review interval.
2. Validate each safety objective as a measurable target: metric, unit,
   baseline, target, direction of improvement, owner and due day.
3. Grade each objective against its measured value: the progress it made
   from its baseline towards its target, and whether the target is met, with
   the direction of improvement respected.
4. Aggregate: the policy stands only when no commitment is missing, the
   approval is at the right level, the review is current, every objective is
   well formed, and the attained fraction reaches what was required.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "REQUIRED_COMMITMENTS",
    "TOP_MANAGEMENT",
    "DIRECTIONS",
    "missing_commitments",
    "policy_currency",
    "validate_policy",
    "assess_policy",
    "validate_objective",
    "objective_progress",
    "objective_status",
    "attainment_fraction",
    "assess_safety_policy",
]

# Attainment and progress are quotients; a value meant to sit exactly on its
# target can land a few ULP either side.
FRACTION_TOLERANCE = 1e-9

# The commitments a test-centre safety policy has to make explicit. A policy
# that omits one of these is not a shorter policy, it is a narrower one.
REQUIRED_COMMITMENTS = (
    "management-commitment",
    "legal-compliance",
    "hazard-prevention",
    "resource-provision",
    "personnel-consultation",
    "continual-improvement",
    "communication",
)

# Approval below this level does not bind the resources the policy promises.
TOP_MANAGEMENT = (
    "managing director",
    "centre director",
    "general manager",
    "top management",
)

DIRECTIONS = ("decrease", "increase")


def _day(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer day number" % label)
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _number(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite" % label)
    return out


def missing_commitments(commitments):
    """Return the required commitments a policy does not carry."""
    if not isinstance(commitments, (list, tuple)):
        raise ValueError("commitments must be a sequence")
    held = []
    for item in commitments:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each commitment must be a non-empty string")
        token = item.strip().lower()
        if token not in REQUIRED_COMMITMENTS:
            raise ValueError(
                "unknown commitment %r; expected one of %s"
                % (item, ", ".join(REQUIRED_COMMITMENTS))
            )
        if token not in held:
            held.append(token)
    return tuple(c for c in REQUIRED_COMMITMENTS if c not in held)


def policy_currency(issue_day, review_interval_days, today):
    """Return 'current', 'due' or 'overdue' for the policy review."""
    issue = _day("issue_day", issue_day)
    interval = _day("review_interval_days", review_interval_days)
    now = _day("today", today)
    if interval == 0:
        raise ValueError("review_interval_days must be at least one day")
    if now < issue:
        raise ValueError("today %d precedes the issue day %d" % (now, issue))
    elapsed = now - issue
    if elapsed > interval:
        return "overdue"
    if elapsed == interval:
        return "due"
    return "current"


def validate_policy(policy):
    """Return a normalised policy record, raising on anything unusable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in ("statement", "commitments", "approved_by", "issue_day",
                "review_interval_days"):
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    statement = policy["statement"]
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("policy statement must be a non-empty string")
    approved_by = policy["approved_by"]
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise ValueError("approved_by must be a non-empty string")
    communicated = policy.get("communicated", False)
    if not isinstance(communicated, bool):
        raise ValueError("'communicated' must be a boolean")
    absent = missing_commitments(policy["commitments"])
    _day("issue_day", policy["issue_day"])
    _day("review_interval_days", policy["review_interval_days"])
    return {
        "statement": statement.strip(),
        "approved_by": approved_by.strip(),
        "approved_at_top_level": approved_by.strip().lower() in TOP_MANAGEMENT,
        "communicated": communicated,
        "missing_commitments": absent,
        "issue_day": policy["issue_day"],
        "review_interval_days": policy["review_interval_days"],
    }


def assess_policy(policy, today):
    """Assess the policy statement itself at a given day."""
    record = validate_policy(policy)
    currency = policy_currency(
        record["issue_day"], record["review_interval_days"], today
    )
    findings = []
    if record["missing_commitments"]:
        findings.append(
            "the policy makes no commitment on %s"
            % ", ".join(record["missing_commitments"])
        )
    if not record["approved_at_top_level"]:
        findings.append(
            "the policy is approved by %s, below the level that binds resources"
            % record["approved_by"]
        )
    if not record["communicated"]:
        findings.append("the policy has not been communicated to the personnel")
    if currency == "overdue":
        findings.append("the policy review is overdue against its stated interval")
    record["currency"] = currency
    record["findings"] = findings
    record["sound"] = not findings
    return record


def validate_objective(objective):
    """Return a normalised safety objective, raising on an unmeasurable one."""
    if not isinstance(objective, dict):
        raise ValueError("objective must be a mapping")
    for key in ("id", "metric", "unit", "baseline", "target", "direction",
                "owner", "due_day"):
        if key not in objective:
            raise ValueError("objective missing required key '%s'" % key)
    for key in ("id", "metric", "unit", "owner"):
        value = objective[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("objective '%s' must be a non-empty string" % key)
    direction = objective["direction"]
    if direction not in DIRECTIONS:
        raise ValueError(
            "unknown direction %r; expected one of %s"
            % (direction, ", ".join(DIRECTIONS))
        )
    baseline = _number("baseline", objective["baseline"])
    target = _number("target", objective["target"])
    if math.isclose(baseline, target, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE):
        raise ValueError(
            "objective %s sets its target equal to its baseline; it asks for "
            "no improvement" % objective["id"]
        )
    if direction == "decrease" and target > baseline:
        raise ValueError(
            "objective %s is a decrease with a target above its baseline"
            % objective["id"]
        )
    if direction == "increase" and target < baseline:
        raise ValueError(
            "objective %s is an increase with a target below its baseline"
            % objective["id"]
        )
    _day("due_day", objective["due_day"])
    return {
        "id": objective["id"],
        "metric": objective["metric"].strip(),
        "unit": objective["unit"].strip(),
        "baseline": baseline,
        "target": target,
        "direction": direction,
        "owner": objective["owner"].strip(),
        "due_day": objective["due_day"],
    }


def objective_progress(baseline, target, actual):
    """Return the fraction of the baseline-to-target movement achieved."""
    base = _number("baseline", baseline)
    goal = _number("target", target)
    value = _number("actual", actual)
    span = goal - base
    if math.isclose(span, 0.0, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE):
        raise ValueError("baseline and target coincide; progress is undefined")
    return (value - base) / span


def objective_status(objective, actual):
    """Grade one safety objective against its measured value."""
    record = validate_objective(objective)
    value = _number("actual", actual)
    progress = objective_progress(record["baseline"], record["target"], value)
    if record["direction"] == "decrease":
        met = value < record["target"] or math.isclose(
            value, record["target"], rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
        )
    else:
        met = value > record["target"] or math.isclose(
            value, record["target"], rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
        )
    regressed = progress < 0.0 and not math.isclose(
        progress, 0.0, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    findings = []
    if regressed:
        findings.append(
            "%s moved away from its target, %.4f of the way back from the baseline"
            % (record["id"], progress)
        )
    record["actual"] = value
    record["progress"] = progress
    record["met"] = met
    record["regressed"] = regressed
    record["findings"] = findings
    return record


def attainment_fraction(records):
    """Return the fraction of graded objectives whose target is met."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    if not records:
        raise ValueError(
            "an attainment fraction over no objectives is undefined; a policy "
            "with no objectives is itself the finding"
        )
    met = sum(1 for r in records if r["met"])
    return float(met) / float(len(records))


def assess_safety_policy(spec):
    """Run the full clause 5.9.2 safety policy and objectives assessment.

    spec keys: policy, objectives (each carrying an 'actual'), today,
    optional required_attainment (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("policy", "objectives", "today"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    objectives = spec["objectives"]
    if not isinstance(objectives, (list, tuple)) or not objectives:
        raise ValueError(
            "spec['objectives'] must be a non-empty sequence; a policy with no "
            "objectives states an intention and sets no target"
        )
    required = spec.get("required_attainment", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_attainment must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_attainment must lie in [0, 1]")
    policy_record = assess_policy(spec["policy"], spec["today"])
    graded = []
    seen = set()
    for objective in objectives:
        if not isinstance(objective, dict) or "actual" not in objective:
            raise ValueError("each objective must carry its measured 'actual'")
        record = objective_status(objective, objective["actual"])
        if record["id"] in seen:
            raise ValueError("duplicate objective id %r" % record["id"])
        seen.add(record["id"])
        graded.append(record)
    attained = attainment_fraction(graded)
    findings = list(policy_record["findings"])
    for record in graded:
        findings.extend(record["findings"])
    met = attained > required or math.isclose(
        attained, required, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    if not met:
        findings.append(
            "%.4f of the safety objectives are met, below the required %.4f"
            % (attained, required)
        )
    overdue = [
        r for r in graded if not r["met"] and r["due_day"] < spec["today"]
    ]
    for record in overdue:
        findings.append(
            "%s is past its due day and still short of its target" % record["id"]
        )
    return {
        "policy": policy_record,
        "objectives": graded,
        "attainment": attained,
        "required_attainment": required,
        "overdue_count": len(overdue),
        "findings": findings,
        "policy_stands": not findings,
    }
