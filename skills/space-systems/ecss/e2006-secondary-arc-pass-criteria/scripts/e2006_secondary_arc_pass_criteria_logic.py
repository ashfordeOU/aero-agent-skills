#!/usr/bin/env python3
"""Secondary-arc pass conditions - ECSS-E-ST-20-06C clause 7.2.3.3 (anchor only).

Deterministic, offline, stdlib-only implementation of the pass conditions a
secondary-arc qualification campaign on a solar-array coupon has to satisfy:

1. campaign coverage bounds the worst-case string-voltage, string-current,
   primary-arc population and bias dwell of the flight design;
2. no sustained discharge is recorded - every discharge event is categorized
   as non-sustained, temporary-sustained or permanent-sustained from its
   duration, its peak arc-current and the way it terminated;
3. the insulation between adjacent strings survives - post-campaign
   insulation-resistance stays at or above the required floor and retains a
   minimum fraction of its pre-campaign value, and the observed surface
   condition carries no disqualifying damage.

The verdict is the conjunction of the three; an empty finding list is the only
pass. No verbatim standard text is reproduced here.
"""

import math

__all__ = [
    "ARC_CATEGORIES",
    "COSMETIC_CONDITIONS",
    "DISQUALIFYING_CONDITIONS",
    "TERMINATION_MODES",
    "NON_SUSTAINED_LIMIT_S",
    "SUSTAINING_CURRENT_A",
    "MIN_RESISTANCE_RETENTION",
    "categorize_arc_event",
    "summarize_arc_events",
    "arc_condition_findings",
    "insulation_retention_ratio",
    "evaluate_string_insulation",
    "check_campaign_coverage",
    "assess_secondary_arc_pass",
]

# Representation tolerance. Durations and voltages arrive as differences or
# sums of floats, so an exactly-compliant value can land a few ULPs on the
# wrong side of a limit. The tolerance absorbs that representation error only;
# the engineering limits below are never widened.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# A discharge shorter than the supply transient-recovery window and below the
# current the string can feed is a primary-arc blow-off transient, not a
# secondary arc.
NON_SUSTAINED_LIMIT_S = 1.0e-3
SUSTAINING_CURRENT_A = 0.05

# Minimum fraction of the pre-campaign string-to-string insulation-resistance
# that has to remain after the campaign.
MIN_RESISTANCE_RETENTION = 0.5

ARC_CATEGORIES = ("non-sustained", "temporary-sustained", "permanent-sustained")
TERMINATION_MODES = ("self-extinguished", "external-cutoff")
COSMETIC_CONDITIONS = ("none", "discoloration", "surface-deposit")
DISQUALIFYING_CONDITIONS = (
    "carbonized-track",
    "melted-insulation",
    "exposed-conductor",
    "string-to-string-short",
)


def _le(value, limit):
    """value <= limit, tolerant of float representation error at equality."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _ge(value, limit):
    """value >= limit, tolerant of float representation error at equality."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _number(mapping, key, context, *, minimum=None, strict=False):
    if key not in mapping:
        raise ValueError("%s: missing required field %r" % (context, key))
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: %r must be a real number, got %r" % (context, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: %r must be finite, got %r" % (context, key, value))
    if minimum is not None:
        if strict and value <= minimum:
            raise ValueError(
                "%s: %r must be greater than %g, got %g" % (context, key, minimum, value)
            )
        if not strict and value < minimum:
            raise ValueError(
                "%s: %r must be at least %g, got %g" % (context, key, minimum, value)
            )
    return value


def _mapping(value, context):
    if not isinstance(value, dict):
        raise ValueError("%s: expected a mapping, got %r" % (context, type(value).__name__))
    return value


def categorize_arc_event(
    event,
    non_sustained_limit_s=NON_SUSTAINED_LIMIT_S,
    sustaining_current_a=SUSTAINING_CURRENT_A,
):
    """Categorize one recorded discharge event.

    Required keys: ``duration_s`` (>= 0), ``peak_current_a`` (>= 0),
    ``termination`` (one of TERMINATION_MODES).

    - terminated by an external cut-off -> permanent-sustained: the discharge
      was still burning when the bias supply was removed, so the coupon never
      demonstrated extinction;
    - self-extinguished within the transient window, or drawing less than the
      current the string can sustain -> non-sustained;
    - self-extinguished but longer than the transient window while drawing a
      string-sustainable current -> temporary-sustained.
    """
    event = _mapping(event, "arc event")
    limit = float(non_sustained_limit_s)
    if limit <= 0.0:
        raise ValueError("non_sustained_limit_s must be positive, got %g" % limit)
    sustaining = float(sustaining_current_a)
    if sustaining <= 0.0:
        raise ValueError("sustaining_current_a must be positive, got %g" % sustaining)

    duration = _number(event, "duration_s", "arc event", minimum=0.0)
    peak = _number(event, "peak_current_a", "arc event", minimum=0.0)
    termination = event.get("termination")
    if termination not in TERMINATION_MODES:
        raise ValueError(
            "arc event: 'termination' must be one of %s, got %r"
            % (", ".join(TERMINATION_MODES), termination)
        )

    if termination == "external-cutoff":
        return "permanent-sustained"
    if not _ge(peak, sustaining):
        return "non-sustained"
    if _le(duration, limit):
        return "non-sustained"
    return "temporary-sustained"


def summarize_arc_events(events, **kwargs):
    """Return per-category counts plus the ordered category of every event."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a list or tuple, got %r" % type(events).__name__)
    categories = [categorize_arc_event(event, **kwargs) for event in events]
    counts = {name: 0 for name in ARC_CATEGORIES}
    for name in categories:
        counts[name] += 1
    return {
        "categories": categories,
        "counts": counts,
        "event_count": len(categories),
        "sustained_count": counts["temporary-sustained"] + counts["permanent-sustained"],
    }


def arc_condition_findings(events, allow_temporary_sustained=False, **kwargs):
    """Findings against the no-sustained-arc condition of clause 7.2.3.3."""
    summary = summarize_arc_events(events, **kwargs)
    findings = []
    permanent = summary["counts"]["permanent-sustained"]
    temporary = summary["counts"]["temporary-sustained"]
    if permanent:
        findings.append(
            "permanent-sustained discharge recorded on %d event(s): the coupon "
            "never self-extinguished" % permanent
        )
    if temporary and not allow_temporary_sustained:
        findings.append(
            "temporary-sustained discharge recorded on %d event(s): sustained "
            "conduction between strings is not admissible" % temporary
        )
    return {"findings": findings, "summary": summary}


def insulation_retention_ratio(pre_resistance_ohm, post_resistance_ohm):
    """post / pre insulation-resistance ratio; both values must be positive."""
    pre = _number(
        {"pre_test_resistance_ohm": pre_resistance_ohm},
        "pre_test_resistance_ohm",
        "insulation",
        minimum=0.0,
        strict=True,
    )
    post = _number(
        {"post_test_resistance_ohm": post_resistance_ohm},
        "post_test_resistance_ohm",
        "insulation",
        minimum=0.0,
    )
    return post / pre


def evaluate_string_insulation(sample, min_retention=MIN_RESISTANCE_RETENTION):
    """Evaluate the string-to-string insulation after the campaign.

    Required keys: ``pre_test_resistance_ohm`` (> 0),
    ``post_test_resistance_ohm`` (>= 0), ``required_resistance_ohm`` (> 0),
    ``observed_conditions`` (list drawn from COSMETIC_CONDITIONS +
    DISQUALIFYING_CONDITIONS).
    """
    sample = _mapping(sample, "insulation sample")
    retention_floor = float(min_retention)
    if not 0.0 < retention_floor <= 1.0:
        raise ValueError(
            "min_retention must lie in (0, 1], got %g" % retention_floor
        )

    pre = _number(sample, "pre_test_resistance_ohm", "insulation sample", minimum=0.0, strict=True)
    post = _number(sample, "post_test_resistance_ohm", "insulation sample", minimum=0.0)
    required = _number(
        sample, "required_resistance_ohm", "insulation sample", minimum=0.0, strict=True
    )

    conditions = sample.get("observed_conditions", ["none"])
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("insulation sample: 'observed_conditions' must be a list")
    known = set(COSMETIC_CONDITIONS) | set(DISQUALIFYING_CONDITIONS)
    for condition in conditions:
        if condition not in known:
            raise ValueError(
                "insulation sample: uncategorized surface condition %r" % (condition,)
            )
    damage = [c for c in conditions if c in DISQUALIFYING_CONDITIONS]

    retention = post / pre
    findings = []
    if not _ge(post, required):
        findings.append(
            "post-campaign insulation-resistance %.3g ohm is below the required "
            "%.3g ohm" % (post, required)
        )
    if not _ge(retention, retention_floor):
        findings.append(
            "insulation-resistance retention %.3f is below the %.3f floor"
            % (retention, retention_floor)
        )
    for condition in damage:
        findings.append("disqualifying insulation damage observed: %s" % condition)

    return {
        "retention_ratio": retention,
        "damage_conditions": damage,
        "cosmetic_conditions": [c for c in conditions if c in COSMETIC_CONDITIONS],
        "findings": findings,
    }


def check_campaign_coverage(coverage):
    """Check that the campaign envelope bounds the flight worst case.

    Required keys: ``applied_string_voltage_v``, ``worst_case_string_voltage_v``,
    ``applied_string_current_a``, ``worst_case_string_current_a``,
    ``primary_arc_count``, ``required_primary_arc_count``, ``dwell_duration_s``,
    ``required_dwell_duration_s``.
    """
    coverage = _mapping(coverage, "coverage")
    applied_v = _number(coverage, "applied_string_voltage_v", "coverage", minimum=0.0, strict=True)
    needed_v = _number(
        coverage, "worst_case_string_voltage_v", "coverage", minimum=0.0, strict=True
    )
    applied_i = _number(coverage, "applied_string_current_a", "coverage", minimum=0.0, strict=True)
    needed_i = _number(
        coverage, "worst_case_string_current_a", "coverage", minimum=0.0, strict=True
    )
    arcs = _number(coverage, "primary_arc_count", "coverage", minimum=0.0)
    needed_arcs = _number(coverage, "required_primary_arc_count", "coverage", minimum=0.0)
    dwell = _number(coverage, "dwell_duration_s", "coverage", minimum=0.0)
    needed_dwell = _number(coverage, "required_dwell_duration_s", "coverage", minimum=0.0)

    findings = []
    if not _ge(applied_v, needed_v):
        findings.append(
            "applied string-voltage %.4g V does not bound the worst-case %.4g V"
            % (applied_v, needed_v)
        )
    if not _ge(applied_i, needed_i):
        findings.append(
            "applied string-current %.4g A does not bound the worst-case %.4g A"
            % (applied_i, needed_i)
        )
    if not _ge(arcs, needed_arcs):
        findings.append(
            "primary-arc population %d is short of the required %d"
            % (int(arcs), int(needed_arcs))
        )
    if not _ge(dwell, needed_dwell):
        findings.append(
            "bias dwell %.4g s is shorter than the required %.4g s" % (dwell, needed_dwell)
        )
    return {
        "voltage_margin_v": applied_v - needed_v,
        "current_margin_a": applied_i - needed_i,
        "findings": findings,
    }


def assess_secondary_arc_pass(record, allow_temporary_sustained=False):
    """Aggregate the three clause 7.2.3.3 conditions into one verdict.

    ``record`` needs ``coverage`` (mapping), ``arc_events`` (list) and
    ``insulation`` (mapping). The verdict is ``pass`` only when every one of
    the three finding lists is empty.
    """
    record = _mapping(record, "campaign record")
    for key in ("coverage", "arc_events", "insulation"):
        if key not in record:
            raise ValueError("campaign record: missing required section %r" % key)

    coverage = check_campaign_coverage(record["coverage"])
    arcs = arc_condition_findings(
        record["arc_events"], allow_temporary_sustained=allow_temporary_sustained
    )
    insulation = evaluate_string_insulation(record["insulation"])

    findings = list(coverage["findings"]) + list(arcs["findings"]) + list(insulation["findings"])
    return {
        "verdict": "pass" if not findings else "fail",
        "coverage": coverage,
        "arc_events": arcs,
        "insulation": insulation,
        "findings": findings,
        "finding_count": len(findings),
    }
