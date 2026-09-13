"""Pass decision for the electrostatic-discharge test of a photovoltaic coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.5.2 (absence of sustained arcing under
the discharge conditions applied to the coupon). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every recorded discharge event: identifier, duration, peak arc
   current, the bias the coupon sat at, and how the event terminated.
2. Categorize each event as transient or sustained. An event that was still
   burning when the run ended, or that was stopped by interrupting the supply,
   is sustained because the coupon never showed extinction. A self-extinguished
   event is transient when it died inside the supply recovery window, or when
   it never drew the current the coupon is able to feed.
3. Check that the events were recorded under the conditions the campaign says
   were applied; an event at a bias that appears in no applied condition cannot
   be read against this criterion.
4. Check that every required condition was actually applied with at least its
   minimum discharge population.
5. Fail the coupon on any sustained event, and report the coverage findings
   alongside, so that a clean arc record obtained under an incomplete set of
   conditions is never read as a pass.
"""

import math

__all__ = [
    "COMPARISON_ABSOLUTE_TOLERANCE",
    "COMPARISON_RELATIVE_TOLERANCE",
    "TERMINATION_MODES",
    "assess_esd_pass_criteria",
    "categorize_event",
    "categorize_events",
    "count_sustained",
    "evaluate_condition_coverage",
    "matches_bias",
    "normalize_termination",
    "validate_event",
]

# Durations arrive as timestamp differences and currents as scaled probe
# readings, so a value physically equal to a limit can land a few ULPs on the
# wrong side. Absorb that here rather than moving any limit.
COMPARISON_RELATIVE_TOLERANCE = 1e-12
COMPARISON_ABSOLUTE_TOLERANCE = 1e-12

# How a recorded discharge event came to an end.
TERMINATION_MODES = (
    "externally-interrupted",
    "self-extinguished",
    "still-burning-at-end",
)


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


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
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


def normalize_termination(mode):
    """Return a recognized termination mode, refusing anything else."""
    if not isinstance(mode, str):
        raise ValueError("termination must be a string, got %r" % (mode,))
    cleaned = mode.strip().lower()
    if cleaned not in TERMINATION_MODES:
        raise ValueError(
            "unrecognized termination %r; recognized: %s"
            % (mode, ", ".join(TERMINATION_MODES))
        )
    return cleaned


def validate_event(event, label="event"):
    """Return one recorded discharge event as a validated record."""
    if not isinstance(event, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("event_id", "duration_s", "peak_current_a", "bias_v", "termination"):
        if key not in event:
            raise ValueError("%s missing required key '%s'" % (label, key))
    event_id = event["event_id"]
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("%s event_id must be a non-empty string" % label)
    return {
        "event_id": event_id.strip(),
        "duration_s": _non_negative(event["duration_s"], "%s duration_s" % label),
        "peak_current_a": _non_negative(
            event["peak_current_a"], "%s peak_current_a" % label
        ),
        "bias_v": _non_negative(event["bias_v"], "%s bias_v" % label),
        "termination": normalize_termination(event["termination"]),
    }


def categorize_event(event, sustaining_current_a, extinction_window_s):
    """Return the transient-or-sustained outcome of one discharge event."""
    record = validate_event(event)
    sustaining = _positive(sustaining_current_a, "sustaining_current_a")
    window = _positive(extinction_window_s, "extinction_window_s")
    if record["termination"] == "still-burning-at-end":
        category = "sustained"
        reason = "the discharge was still burning when the run was stopped"
    elif record["termination"] == "externally-interrupted":
        category = "sustained"
        reason = (
            "the discharge ended only when the supply was interrupted, so the coupon "
            "never showed extinction"
        )
    elif _at_or_below(record["duration_s"], window):
        category = "transient"
        reason = "the discharge died inside the %g s supply recovery window" % window
    elif not _at_or_above(record["peak_current_a"], sustaining):
        category = "transient"
        reason = (
            "the discharge drew %g A, under the %g A the coupon is able to feed"
            % (record["peak_current_a"], sustaining)
        )
    else:
        category = "sustained"
        reason = (
            "the discharge carried %g A of coupon-sustainable current for %g s, past "
            "the %g s recovery window"
            % (record["peak_current_a"], record["duration_s"], window)
        )
    outcome = dict(record)
    outcome["category"] = category
    outcome["reason"] = reason
    return outcome


def categorize_events(events, sustaining_current_a, extinction_window_s):
    """Return one outcome record per recorded discharge event."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of event records")
    seen = set()
    outcomes = []
    for event in events:
        outcome = categorize_event(event, sustaining_current_a, extinction_window_s)
        if outcome["event_id"] in seen:
            raise ValueError("duplicate event_id %r in events" % outcome["event_id"])
        seen.add(outcome["event_id"])
        outcomes.append(outcome)
    return outcomes


def count_sustained(outcomes):
    """Return how many categorized events came out sustained."""
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("outcomes must be a sequence of categorized events")
    total = 0
    for outcome in outcomes:
        if not isinstance(outcome, dict) or "category" not in outcome:
            raise ValueError("each outcome must be a mapping carrying 'category'")
        if outcome["category"] == "sustained":
            total += 1
    return total


def matches_bias(bias_v, applied_conditions):
    """Return True when a bias value appears among the applied conditions."""
    value = _non_negative(bias_v, "bias_v")
    for condition in _validate_conditions(applied_conditions, "applied", "discharges"):
        if _close(value, condition["bias_v"]):
            return True
    return False


def _validate_conditions(conditions, label, count_key):
    """Return a validated list of bias conditions with their discharge counts."""
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError("%s_conditions must be a non-empty sequence" % label)
    validated = []
    for index, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            raise ValueError("%s_conditions[%d] must be a mapping" % (label, index))
        for key in ("bias_v", count_key):
            if key not in condition:
                raise ValueError(
                    "%s_conditions[%d] missing required key '%s'" % (label, index, key)
                )
        count = condition[count_key]
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                "%s_conditions[%d]['%s'] must be an integer, got %r"
                % (label, index, count_key, count)
            )
        if count < 0:
            raise ValueError(
                "%s_conditions[%d]['%s'] must be non-negative, got %d"
                % (label, index, count_key, count)
            )
        validated.append({
            "bias_v": _non_negative(
                condition["bias_v"], "%s_conditions[%d] bias_v" % (label, index)
            ),
            "count": int(count),
        })
    return validated


def evaluate_condition_coverage(applied_conditions, required_conditions):
    """Return one coverage record per required discharge condition."""
    applied = _validate_conditions(applied_conditions, "applied", "discharges")
    required = _validate_conditions(required_conditions, "required", "min_discharges")
    records = []
    for wanted in required:
        total = 0
        matched = False
        for condition in applied:
            if _close(condition["bias_v"], wanted["bias_v"]):
                matched = True
                total += condition["count"]
        records.append({
            "bias_v": wanted["bias_v"],
            "required_discharges": wanted["count"],
            "applied_discharges": total,
            "applied": matched,
            "satisfied": matched and total >= wanted["count"],
        })
    return records


def assess_esd_pass_criteria(spec):
    """Run the full clause 5.5.1.5.2 pass decision for a coupon.

    spec keys: events, sustaining_current_a, extinction_window_s,
    applied_conditions, required_conditions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("events", "sustaining_current_a", "extinction_window_s",
                "applied_conditions", "required_conditions"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    outcomes = categorize_events(
        spec["events"], spec["sustaining_current_a"], spec["extinction_window_s"]
    )
    coverage = evaluate_condition_coverage(
        spec["applied_conditions"], spec["required_conditions"]
    )
    findings = []
    sustained_ids = []
    for outcome in outcomes:
        if outcome["category"] == "sustained":
            sustained_ids.append(outcome["event_id"])
            findings.append(
                "event %s is a sustained arc: %s" % (outcome["event_id"], outcome["reason"])
            )
    for outcome in outcomes:
        if not matches_bias(outcome["bias_v"], spec["applied_conditions"]):
            findings.append(
                "event %s was recorded at %g V, which appears in no applied condition"
                % (outcome["event_id"], outcome["bias_v"])
            )
    for record in coverage:
        if not record["applied"]:
            findings.append(
                "required condition at %g V was never applied" % record["bias_v"]
            )
        elif not record["satisfied"]:
            findings.append(
                "condition at %g V recorded %d discharges, short of the %d required"
                % (record["bias_v"], record["applied_discharges"],
                   record["required_discharges"])
            )
    return {
        "events": outcomes,
        "coverage": coverage,
        "sustained_event_ids": tuple(sustained_ids),
        "sustained_count": count_sustained(outcomes),
        "transient_count": len(outcomes) - count_sustained(outcomes),
        "findings": findings,
        "passed": not findings,
    }
