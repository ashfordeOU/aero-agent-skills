"""Failure criteria for a photovoltaic assembly under subgroup testing.

Anchor: ECSS-E-ST-20-08C clause 5.6.1 (the conditions that count as a
photovoltaic assembly failure while a test subgroup is being run).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every observation taken on a subgroup sample: which sample it came
   from, which recognized condition it describes, and either the occurrence
   flag or the measured value that condition is read through.
2. Separate the conditions that are a failure on occurrence alone - a lost
   conduction path, an unintended one, a detached component - from the ones
   that only become a failure once a declared limit is crossed.
3. Compare each measured value against its declared limit in the direction of
   merit that condition carries, admitting an exact equality at the limit
   through a named tolerance, and report the margin beside the outcome.
4. Check that the subgroup record is complete: every declared sample carries a
   record for every required condition, and no observation arrives from a
   sample the subgroup never contained.
5. Fail the subgroup on any failing observation, and carry the coverage
   findings beside the verdict so an incomplete record is never read as a pass.
"""

import math

__all__ = [
    "COMPARISON_ABSOLUTE_TOLERANCE",
    "COMPARISON_RELATIVE_TOLERANCE",
    "FAILURE_CONDITIONS",
    "OCCURRENCE_BASIS",
    "assess_subgroup_failure",
    "condition_basis",
    "evaluate_observation",
    "evaluate_observations",
    "evaluate_sample_coverage",
    "failing_sample_ids",
    "normalize_condition",
    "validate_observation",
]

# Measured values reach this module as scaled instrument readings and ratios of
# two readings, so a quantity physically equal to a limit can land a few ULPs
# on the wrong side of it. Absorb that here rather than moving any limit.
COMPARISON_RELATIVE_TOLERANCE = 1e-12
COMPARISON_ABSOLUTE_TOLERANCE = 1e-12

# A condition read through occurrence alone: it either happened or it did not,
# and there is no limit that makes it acceptable.
OCCURRENCE_BASIS = "on-occurrence"

# The recognized failure conditions of a photovoltaic assembly under subgroup
# test, each with the basis it is read through. "at-or-under" conditions are
# acceptable while they stay at or below their declared limit; "at-or-over"
# conditions are acceptable while they reach it.
FAILURE_CONDITIONS = {
    "continuity-loss": {"basis": OCCURRENCE_BASIS},
    "unintended-conduction-path": {"basis": OCCURRENCE_BASIS},
    "component-detachment": {"basis": OCCURRENCE_BASIS},
    "coverglass-loss": {"basis": OCCURRENCE_BASIS},
    "in-situ-discontinuity": {"basis": "at-or-under"},
    "output-power-degradation": {"basis": "at-or-under"},
    "cracked-area-fraction": {"basis": "at-or-under"},
    "visual-defect-count": {"basis": "at-or-under"},
    "power-retention-ratio": {"basis": "at-or-over"},
    "insulation-resistance-ohm": {"basis": "at-or-over"},
}


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _close(left, right):
    """Return True when two measured quantities are equal within tolerance."""
    return math.isclose(
        left,
        right,
        rel_tol=COMPARISON_RELATIVE_TOLERANCE,
        abs_tol=COMPARISON_ABSOLUTE_TOLERANCE,
    )


def _at_or_below(value, limit):
    """Return True when value stays at or under limit, tolerating equality."""
    return value < limit or _close(value, limit)


def _at_or_above(value, limit):
    """Return True when value reaches limit, tolerating equality."""
    return value > limit or _close(value, limit)


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def normalize_condition(condition):
    """Return a recognized failure condition name, refusing anything else."""
    if not isinstance(condition, str):
        raise ValueError("condition must be a string, got %r" % (condition,))
    cleaned = condition.strip().lower()
    if cleaned not in FAILURE_CONDITIONS:
        raise ValueError(
            "unrecognized condition %r; recognized: %s"
            % (condition, ", ".join(sorted(FAILURE_CONDITIONS)))
        )
    return cleaned


def condition_basis(condition):
    """Return the basis a recognized condition is read through."""
    return FAILURE_CONDITIONS[normalize_condition(condition)]["basis"]


def validate_observation(observation, label="observation"):
    """Return one subgroup observation as a validated record.

    An occurrence condition carries 'observed'; a limit-governed condition
    carries 'value'. Supplying the wrong one is an input defect, not a default.
    """
    if not isinstance(observation, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("sample_id", "condition"):
        if key not in observation:
            raise ValueError("%s missing required key '%s'" % (label, key))
    condition = normalize_condition(observation["condition"])
    basis = FAILURE_CONDITIONS[condition]["basis"]
    record = {
        "sample_id": _identifier(observation["sample_id"], "%s sample_id" % label),
        "condition": condition,
        "basis": basis,
    }
    if basis == OCCURRENCE_BASIS:
        if "observed" not in observation:
            raise ValueError(
                "%s for occurrence condition '%s' must carry 'observed'"
                % (label, condition)
            )
        if not isinstance(observation["observed"], bool):
            raise ValueError(
                "%s 'observed' must be a boolean, got %r"
                % (label, observation["observed"])
            )
        record["observed"] = observation["observed"]
    else:
        if "value" not in observation:
            raise ValueError(
                "%s for limit-governed condition '%s' must carry 'value'"
                % (label, condition)
            )
        record["value"] = _non_negative(observation["value"], "%s value" % label)
    return record


def _limit_for(condition, limits):
    """Return the declared limit for a limit-governed condition."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping of condition to declared limit")
    if condition not in limits:
        raise ValueError(
            "no declared limit for condition '%s'; an undeclared limit is not a "
            "zero limit and cannot be assumed" % condition
        )
    return _non_negative(limits[condition], "limit for '%s'" % condition)


def evaluate_observation(observation, limits=None):
    """Return the failure outcome of one subgroup observation."""
    record = validate_observation(observation)
    condition = record["condition"]
    if record["basis"] == OCCURRENCE_BASIS:
        failed = record["observed"]
        if failed:
            reason = (
                "'%s' occurred on sample %s, and this condition is a failure on "
                "occurrence alone" % (condition, record["sample_id"])
            )
        else:
            reason = "'%s' did not occur on sample %s" % (condition, record["sample_id"])
        outcome = dict(record)
        outcome["failed"] = failed
        outcome["reason"] = reason
        return outcome
    limit = _limit_for(condition, limits if limits is not None else {})
    value = record["value"]
    if record["basis"] == "at-or-under":
        acceptable = _at_or_below(value, limit)
        margin = limit - value
        direction = "at or under"
    else:
        acceptable = _at_or_above(value, limit)
        margin = value - limit
        direction = "at or over"
    outcome = dict(record)
    outcome["limit"] = limit
    outcome["margin"] = margin
    outcome["failed"] = not acceptable
    if acceptable:
        outcome["reason"] = "'%s' read %g, %s its %g limit" % (
            condition, value, direction, limit,
        )
    else:
        outcome["reason"] = "'%s' read %g, which is not %s its %g limit" % (
            condition, value, direction, limit,
        )
    return outcome


def evaluate_observations(observations, limits=None):
    """Return one outcome per observation, refusing a repeated reading."""
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence of observation records")
    seen = set()
    outcomes = []
    for observation in observations:
        outcome = evaluate_observation(observation, limits)
        key = (outcome["sample_id"], outcome["condition"])
        if key in seen:
            raise ValueError(
                "duplicate reading of '%s' on sample %s" % (key[1], key[0])
            )
        seen.add(key)
        outcomes.append(outcome)
    return outcomes


def failing_sample_ids(outcomes):
    """Return, in first-seen order, the samples carrying a failing outcome."""
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("outcomes must be a sequence of evaluated observations")
    ordered = []
    for outcome in outcomes:
        if not isinstance(outcome, dict) or "failed" not in outcome:
            raise ValueError("each outcome must be a mapping carrying 'failed'")
        if outcome["failed"] and outcome["sample_id"] not in ordered:
            ordered.append(outcome["sample_id"])
    return tuple(ordered)


def evaluate_sample_coverage(outcomes, sample_ids, required_conditions):
    """Return one coverage record per declared sample of the subgroup."""
    if not isinstance(sample_ids, (list, tuple)) or not sample_ids:
        raise ValueError("sample_ids must be a non-empty sequence")
    declared = []
    for index, sample_id in enumerate(sample_ids):
        cleaned = _identifier(sample_id, "sample_ids[%d]" % index)
        if cleaned in declared:
            raise ValueError("duplicate sample_id %r in sample_ids" % cleaned)
        declared.append(cleaned)
    if not isinstance(required_conditions, (list, tuple)) or not required_conditions:
        raise ValueError("required_conditions must be a non-empty sequence")
    required = []
    for condition in required_conditions:
        cleaned = normalize_condition(condition)
        if cleaned not in required:
            required.append(cleaned)
    recorded = {}
    for outcome in outcomes:
        recorded.setdefault(outcome["sample_id"], set()).add(outcome["condition"])
    records = []
    for sample_id in declared:
        present = recorded.get(sample_id, set())
        missing = tuple(c for c in required if c not in present)
        records.append({
            "sample_id": sample_id,
            "recorded_conditions": len(present),
            "missing_conditions": missing,
            "complete": not missing,
        })
    return records


def assess_subgroup_failure(spec):
    """Run the full clause 5.6.1 subgroup failure decision.

    spec keys: sample_ids, observations, required_conditions, limits.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sample_ids", "observations", "required_conditions", "limits"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    outcomes = evaluate_observations(spec["observations"], spec["limits"])
    coverage = evaluate_sample_coverage(
        outcomes, spec["sample_ids"], spec["required_conditions"]
    )
    declared = {record["sample_id"] for record in coverage}
    findings = []
    for outcome in outcomes:
        if outcome["failed"]:
            findings.append(
                "sample %s failed: %s" % (outcome["sample_id"], outcome["reason"])
            )
    for outcome in outcomes:
        if outcome["sample_id"] not in declared:
            findings.append(
                "observation of '%s' came from sample %s, which the subgroup never "
                "contained" % (outcome["condition"], outcome["sample_id"])
            )
    for record in coverage:
        if not record["complete"]:
            findings.append(
                "sample %s has no record for: %s"
                % (record["sample_id"], ", ".join(record["missing_conditions"]))
            )
    failed_samples = failing_sample_ids(outcomes)
    return {
        "observations": outcomes,
        "coverage": coverage,
        "failing_sample_ids": failed_samples,
        "failing_observation_count": sum(1 for o in outcomes if o["failed"]),
        "record_complete": all(record["complete"] for record in coverage),
        "subgroup_failed": bool(failed_samples),
        "findings": findings,
        "passed": not findings,
    }
