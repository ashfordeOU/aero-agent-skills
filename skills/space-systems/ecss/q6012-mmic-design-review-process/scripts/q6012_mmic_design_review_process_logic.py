"""Design-review programme assessment for an MMIC before fabrication release.

Anchor: ECSS-Q-ST-60-12C clause 7.3 (the formal checkpoints at which the
microwave circuit design is examined before it is released to fabrication).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise a declared review programme into the canonical checkpoint order,
   refusing an unknown checkpoint key, a duplicate entry or an action count
   that closes more items than it raised.
2. Name the mandatory checkpoints that were never held, because a programme
   that merely plans a gate is not a programme that passed it.
3. Detect a checkpoint held out of sequence: a later gate cannot be held on an
   earlier day than the gate it depends on.
4. Measure the schedule slip of each held gate against its planned day and the
   action-item closure ratio accumulated over the held gates.
5. Decide fabrication release: every mandatory gate held, no sequence
   violation, the closure ratio at or above the required value, and the
   release day sitting at or after the last gate plus its quiet period.

Days are integer programme days counted from a common origin, so the module
never needs a calendar and never touches the clock.
"""

import math

__all__ = [
    "CANONICAL_CHECKPOINTS",
    "CLOSURE_TOLERANCE",
    "validate_checkpoint",
    "normalise_programme",
    "missing_checkpoints",
    "sequence_violations",
    "schedule_slip_days",
    "programme_slip_days",
    "action_closure_ratio",
    "coverage_fraction",
    "release_readiness",
    "assess_design_review_process",
]

# The gate order a microwave circuit walks through before its mask set is cut.
# Order is the contract; the names are the paraphrased checkpoint keys.
CANONICAL_CHECKPOINTS = (
    "requirements",
    "architecture",
    "detailed-design",
    "layout",
    "pre-release",
)

# A closure ratio is a quotient of integers turned into a float. An exact
# equality with the required value can land a few ULPs low, so the comparison
# absorbs representation error here instead of relaxing the required ratio.
CLOSURE_TOLERANCE = 1e-9


def _require_int(value, label, minimum=None):
    """Return value as an int, refusing bools, floats and out-of-range input."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_checkpoint(entry):
    """Return one normalised checkpoint record.

    entry keys: key (canonical checkpoint), planned_day, optional held_day
    (None when the gate was never held), optional actions_raised and
    actions_closed, optional mandatory flag (defaults True).
    """
    if not isinstance(entry, dict):
        raise ValueError("checkpoint entry must be a mapping, got %r" % (entry,))
    key = entry.get("key")
    if not isinstance(key, str) or key not in CANONICAL_CHECKPOINTS:
        raise ValueError(
            "checkpoint key %r is not one of %s" % (key, ", ".join(CANONICAL_CHECKPOINTS))
        )
    planned_day = _require_int(entry.get("planned_day"), "planned_day", minimum=0)
    held_day = entry.get("held_day")
    if held_day is not None:
        held_day = _require_int(held_day, "held_day", minimum=0)
    raised = _require_int(entry.get("actions_raised", 0), "actions_raised", minimum=0)
    closed = _require_int(entry.get("actions_closed", 0), "actions_closed", minimum=0)
    if closed > raised:
        raise ValueError(
            "checkpoint %s closes %d actions but raised only %d" % (key, closed, raised)
        )
    if held_day is None and raised > 0:
        raise ValueError("checkpoint %s was never held yet raised %d actions" % (key, raised))
    mandatory = entry.get("mandatory", True)
    if not isinstance(mandatory, bool):
        raise ValueError("mandatory flag of %s must be a boolean" % key)
    return {
        "key": key,
        "order": CANONICAL_CHECKPOINTS.index(key),
        "planned_day": planned_day,
        "held_day": held_day,
        "held": held_day is not None,
        "actions_raised": raised,
        "actions_closed": closed,
        "mandatory": mandatory,
    }


def normalise_programme(entries):
    """Return the checkpoint records sorted into canonical gate order."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("programme must be a non-empty sequence of checkpoint entries")
    records = [validate_checkpoint(entry) for entry in entries]
    seen = set()
    for record in records:
        if record["key"] in seen:
            raise ValueError("checkpoint %s declared twice" % record["key"])
        seen.add(record["key"])
    records.sort(key=lambda r: r["order"])
    return records


def missing_checkpoints(programme):
    """Return the canonical keys of mandatory gates that were never held."""
    by_key = {record["key"]: record for record in programme}
    missing = []
    for key in CANONICAL_CHECKPOINTS:
        record = by_key.get(key)
        if record is None:
            missing.append(key)
        elif record["mandatory"] and not record["held"]:
            missing.append(key)
    return missing


def sequence_violations(programme):
    """Return (earlier_key, later_key) pairs held in the wrong chronological order."""
    held = [record for record in programme if record["held"]]
    violations = []
    for i in range(1, len(held)):
        previous = held[i - 1]
        current = held[i]
        if current["held_day"] < previous["held_day"]:
            violations.append((previous["key"], current["key"]))
    return violations


def schedule_slip_days(record):
    """Return held_day minus planned_day for a gate that was actually held."""
    if not isinstance(record, dict) or "held_day" not in record:
        raise ValueError("record must be a normalised checkpoint mapping")
    if record["held_day"] is None:
        raise ValueError("checkpoint %s was never held; it has no slip" % record.get("key"))
    return record["held_day"] - record["planned_day"]


def programme_slip_days(programme):
    """Return the largest positive slip over the held gates (0 when none slipped)."""
    slips = [schedule_slip_days(r) for r in programme if r["held"]]
    if not slips:
        return 0
    return max(0, max(slips))


def action_closure_ratio(programme):
    """Return closed/raised over the held gates; 1.0 when no action was raised."""
    raised = sum(r["actions_raised"] for r in programme if r["held"])
    closed = sum(r["actions_closed"] for r in programme if r["held"])
    if raised == 0:
        return 1.0
    return closed / raised


def coverage_fraction(programme):
    """Return the share of mandatory canonical gates that were held."""
    by_key = {record["key"]: record for record in programme}
    mandatory = 0
    held = 0
    for key in CANONICAL_CHECKPOINTS:
        record = by_key.get(key)
        if record is None or record["mandatory"]:
            mandatory += 1
            if record is not None and record["held"]:
                held += 1
    if mandatory == 0:
        raise ValueError("programme declares no mandatory gate")
    return held / mandatory


def release_readiness(programme, fabrication_release_day, required_closure_ratio=1.0,
                      quiet_period_days=0):
    """Return the release verdict for a normalised programme."""
    release_day = _require_int(fabrication_release_day, "fabrication_release_day", minimum=0)
    quiet = _require_int(quiet_period_days, "quiet_period_days", minimum=0)
    if isinstance(required_closure_ratio, bool) or not isinstance(
        required_closure_ratio, (int, float)
    ):
        raise ValueError("required_closure_ratio must be a real number")
    required = float(required_closure_ratio)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_closure_ratio must lie in [0, 1], got %r" % (required_closure_ratio,))

    missing = missing_checkpoints(programme)
    violations = sequence_violations(programme)
    ratio = action_closure_ratio(programme)
    held_days = [r["held_day"] for r in programme if r["held"]]
    last_gate_day = max(held_days) if held_days else None
    ratio_ok = ratio > required or math.isclose(
        ratio, required, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    )
    if last_gate_day is None:
        quiet_ok = False
    else:
        quiet_ok = release_day >= last_gate_day + quiet
    return {
        "missing_checkpoints": missing,
        "sequence_violations": violations,
        "closure_ratio": ratio,
        "required_closure_ratio": required,
        "closure_ratio_met": ratio_ok,
        "last_gate_day": last_gate_day,
        "fabrication_release_day": release_day,
        "quiet_period_days": quiet,
        "quiet_period_met": quiet_ok,
        "released": not missing and not violations and ratio_ok and quiet_ok,
    }


def assess_design_review_process(spec):
    """Run the full clause 7.3 review-programme assessment.

    spec keys: checkpoints (sequence of entries), fabrication_release_day,
    optional required_closure_ratio and quiet_period_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("checkpoints", "fabrication_release_day"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    programme = normalise_programme(spec["checkpoints"])
    verdict = release_readiness(
        programme,
        spec["fabrication_release_day"],
        spec.get("required_closure_ratio", 1.0),
        spec.get("quiet_period_days", 0),
    )
    findings = []
    for key in verdict["missing_checkpoints"]:
        findings.append("mandatory checkpoint %s was never held" % key)
    for earlier, later in verdict["sequence_violations"]:
        findings.append("checkpoint %s was held before %s" % (later, earlier))
    if not verdict["closure_ratio_met"]:
        findings.append(
            "action closure ratio %.4f is below the required %.4f"
            % (verdict["closure_ratio"], verdict["required_closure_ratio"])
        )
    if not verdict["quiet_period_met"]:
        findings.append(
            "fabrication release on day %d does not clear the last gate plus its %d day quiet period"
            % (verdict["fabrication_release_day"], verdict["quiet_period_days"])
        )
    slip = programme_slip_days(programme)
    result = dict(verdict)
    result["programme"] = programme
    result["coverage_fraction"] = coverage_fraction(programme)
    result["max_slip_days"] = slip
    result["findings"] = findings
    return result
