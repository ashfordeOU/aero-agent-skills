#!/usr/bin/env python3
"""What marks a planar blocking diode failed inside a subgroup test.

Anchor: ECSS-E-ST-20-08C clause 12.7.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A subgroup of blocking diodes is characterised, driven through a test,
characterised again and then looked at. This clause fixes what turns that pair
of characterisations plus the closing inspection into the word "failed", and
it does so on arms that do not offset one another:

    drift       a parameter that moved further between the before and the
                after characterisation than the governing specification lets
                it move
    absolute    an after reading outside the limit the specification fixes for
                that parameter, whatever its drift -- a part can creep a
                little from a value already near the limit and be out, or move
                a long way from a comfortable start and still be in
    function    a blocking diode has two jobs and can lose either. A junction
                reading no reverse blocking voltage has stopped blocking the
                bus out of a shadowed string; one that never turns on in the
                forward direction has taken its whole string off the array.
                Neither is a percentage on a curve.
    observed    a condition the closing inspection can see, which fails the
                part on its own whatever the numbers said

Reverse leakage is strongly dependent on the bias it is measured at, so a
reverse reading taken below the reference bias the specification names is not
comparable with the limit and is held as unread rather than as a low number.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GRADED_PARAMETERS = (
    "forward-voltage-drop",
    "reverse-leakage-current",
    "reverse-blocking-voltage",
    "thermal-resistance-junction-to-case",
)

# Which way a parameter has to move before the movement counts as degradation.
DEGRADATION_SENSE = {
    "forward-voltage-drop": "increase",
    "reverse-leakage-current": "increase",
    "reverse-blocking-voltage": "decrease",
    "thermal-resistance-junction-to-case": "increase",
}

# The parameters whose reading only means anything at the reference bias.
BIAS_DEPENDENT_PARAMETERS = (
    "reverse-leakage-current",
    "reverse-blocking-voltage",
)

OBSERVABLE_CONDITIONS = (
    "die-crack",
    "contact-metallisation-lifted",
    "solder-void-beyond-limit",
    "encapsulation-damage",
    "terminal-corrosion",
    "adhering-contamination",
)

REVERSE_BLOCKING_LOST = "blocking-diode-reverse-blocking-lost"
FORWARD_CONDUCTION_LOST = "blocking-diode-forward-conduction-lost"

SPECIMEN_FAILED = "blocking-diode-failed"
SPECIMEN_PASSED = "blocking-diode-passed"
SPECIMEN_NOT_EVALUATED = "blocking-diode-not-evaluated"

SUBGROUP_MEETS_CRITERIA = "subgroup-meets-criteria"
SUBGROUP_FAILED = "subgroup-failed"
SUBGROUP_NOT_EVALUABLE = "subgroup-not-evaluable"

DEFAULT_FAILURE_CRITERIA = {
    "specification_reference": "planar-blocking-diode-source-control-drawing-issue-c",
    "drift_allowances": {
        "forward-voltage-drop": 0.10,
        "reverse-leakage-current": 0.50,
        "reverse-blocking-voltage": 0.10,
        "thermal-resistance-junction-to-case": 0.20,
    },
    "absolute_limits": {
        "forward-voltage-drop": 1.10,
        "reverse-leakage-current": 5.0e-6,
        "reverse-blocking-voltage": 40.0,
    },
    "reference_reverse_bias_v": 30.0,
    "open_circuit_forward_threshold_v": 5.0,
    "disqualifying_conditions": (
        "die-crack",
        "contact-metallisation-lifted",
        "solder-void-beyond-limit",
        "encapsulation-damage",
    ),
    "max_failed_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _within(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_reading(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            "%s must be a finite non-negative reading, got %r" % (name, value)
        )
    return value


def _require_positive(name, value):
    value = _require_reading(name, value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def graded_parameters():
    """The blocking diode parameters a subgroup test is graded on."""
    return tuple(GRADED_PARAMETERS)


def bias_dependent_parameters():
    """The parameters whose reading only means anything at the reference bias."""
    return tuple(BIAS_DEPENDENT_PARAMETERS)


def observable_conditions():
    """The conditions the closing inspection can raise against a part."""
    return tuple(OBSERVABLE_CONDITIONS)


def degradation_sense(parameter):
    """The direction this parameter has to move in before it counts as decay."""
    parameter = _require_text("parameter", parameter)
    if parameter not in GRADED_PARAMETERS:
        raise ValueError("unknown graded parameter %s" % parameter)
    return DEGRADATION_SENSE[parameter]


def bias_adequate(declared_bias_v, reference_bias_v):
    """Was the reverse reading taken at or above the reference bias."""
    declared = _require_reading("declared_bias_v", declared_bias_v)
    reference = _require_reading("reference_bias_v", reference_bias_v)
    return _at_least(declared, reference)


def validate_failure_criteria(criteria):
    """Check a declared criteria set can decide anything at all."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_text("specification_reference", criteria.get("specification_reference"))

    allowances = criteria.get("drift_allowances")
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError("drift_allowances must be a non-empty mapping")
    for name, allowance in allowances.items():
        name = _require_text("drift_allowances key", name)
        if name not in GRADED_PARAMETERS:
            raise ValueError("drift_allowances names an unknown parameter %s" % name)
        _require_fraction("drift allowance for %s" % name, allowance)

    limits = criteria.get("absolute_limits", {})
    if not isinstance(limits, dict):
        raise ValueError("absolute_limits must be a mapping, got %r" % (limits,))
    for name, limit in limits.items():
        name = _require_text("absolute_limits key", name)
        if name not in GRADED_PARAMETERS:
            raise ValueError("absolute_limits names an unknown parameter %s" % name)
        _require_reading("absolute limit for %s" % name, limit)

    _require_positive(
        "reference_reverse_bias_v", criteria.get("reference_reverse_bias_v")
    )
    _require_positive(
        "open_circuit_forward_threshold_v",
        criteria.get("open_circuit_forward_threshold_v"),
    )

    conditions = criteria.get("disqualifying_conditions")
    if not isinstance(conditions, (list, tuple, set, frozenset)) or not conditions:
        raise ValueError("disqualifying_conditions must be a non-empty sequence")
    for condition in conditions:
        condition = _require_text("disqualifying condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("unknown disqualifying condition %s" % condition)

    _require_fraction("max_failed_fraction", criteria.get("max_failed_fraction"))
    return criteria


def parameter_drift(parameter, before, after):
    """How far one parameter moved, and how much of that movement is decay."""
    sense = degradation_sense(parameter)
    parameter = parameter.strip()
    before = _require_reading("before reading for %s" % parameter, before)
    after = _require_reading("after reading for %s" % parameter, after)
    if before == 0.0:
        raise ValueError("before reading for %s must be positive" % parameter)
    signed = after - before
    decay = signed if sense == "increase" else -signed
    return {
        "parameter": parameter,
        "sense": sense,
        "before": before,
        "after": after,
        "signed_change": signed,
        "degradation": decay,
        "relative_drift": decay / before,
    }


def drift_within_allowance(parameter, before, after, allowance):
    """Did this parameter stay inside its allowance, a tie being admissible."""
    allowance = _require_fraction("drift allowance for %s" % parameter, allowance)
    drift = parameter_drift(parameter, before, after)
    relative = drift["relative_drift"]
    drift["allowance"] = allowance
    drift["margin"] = allowance - relative
    drift["within_allowance"] = relative <= 0.0 or _within(relative, allowance)
    return drift


def absolute_limit_respected(parameter, reading, limit):
    """Is this after reading on the admissible side of its absolute limit."""
    sense = degradation_sense(parameter)
    reading = _require_reading("reading for %s" % parameter, reading)
    limit = _require_reading("absolute limit for %s" % parameter, limit)
    if sense == "increase":
        return _within(reading, limit)
    return _at_least(reading, limit)


def assess_blocking_diode_specimen(specimen, criteria=DEFAULT_FAILURE_CRITERIA):
    """Failure call for one blocking diode, naming every mode it shows."""
    validate_failure_criteria(criteria)
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    specimen_id = _require_text("specimen_id", specimen.get("specimen_id"))

    before = specimen.get("before_readings")
    after = specimen.get("after_readings")
    if not isinstance(before, dict) or not before:
        raise ValueError("before_readings must be a non-empty mapping")
    if not isinstance(after, dict):
        raise ValueError("after_readings must be a mapping, got %r" % (after,))

    reference_bias = float(criteria["reference_reverse_bias_v"])
    declared_bias = specimen.get("measurement_bias_v")
    bias_ok = True
    if declared_bias is not None:
        bias_ok = bias_adequate(declared_bias, reference_bias)

    allowances = criteria["drift_allowances"]
    limits = criteria.get("absolute_limits", {})
    modes = []
    findings = []
    drifts = {}
    unread = []

    for parameter in sorted(allowances):
        if not bias_ok and parameter in BIAS_DEPENDENT_PARAMETERS:
            unread.append(parameter)
            findings.append(
                "%s read %s at %.6g V against a reference bias of %.6g V, so "
                "the reading is not comparable with its limit"
                % (specimen_id, parameter, float(declared_bias), reference_bias)
            )
            continue
        if before.get(parameter) is None:
            unread.append(parameter)
            findings.append(
                "%s has no before reading for %s, so no drift can be taken "
                "against its allowance" % (specimen_id, parameter)
            )
            continue
        if after.get(parameter) is None:
            unread.append(parameter)
            findings.append(
                "%s has no after reading for %s, so the part has not been "
                "evaluated on it" % (specimen_id, parameter)
            )
            continue
        drift = drift_within_allowance(
            parameter, before[parameter], after[parameter], allowances[parameter]
        )
        drifts[parameter] = drift
        if not drift["within_allowance"]:
            modes.append("%s-drift-exceeded" % parameter)
            findings.append(
                "%s moved %.4f of its %s against a drift allowance of %.4f"
                % (specimen_id, drift["relative_drift"], parameter, drift["allowance"])
            )
        if parameter in limits:
            limit = float(limits[parameter])
            respected = absolute_limit_respected(parameter, drift["after"], limit)
            drift["absolute_limit"] = limit
            drift["absolute_limit_respected"] = respected
            if not respected:
                modes.append("%s-outside-absolute-limit" % parameter)
                findings.append(
                    "%s reads %.6g for %s against an absolute limit of %.6g"
                    % (specimen_id, drift["after"], parameter, limit)
                )

    blocking = drifts.get("reverse-blocking-voltage")
    if blocking is not None and blocking["after"] == 0.0:
        modes.append(REVERSE_BLOCKING_LOST)
        findings.append(
            "%s reads no reverse blocking voltage after the test, so the bus "
            "is no longer held out of the string behind it" % specimen_id
        )

    forward = drifts.get("forward-voltage-drop")
    open_threshold = float(criteria["open_circuit_forward_threshold_v"])
    if forward is not None and _at_least(forward["after"], open_threshold):
        modes.append(FORWARD_CONDUCTION_LOST)
        findings.append(
            "%s needs %.6g V before it conducts forward against an open-circuit "
            "threshold of %.6g V, so its string no longer reaches the bus"
            % (specimen_id, forward["after"], open_threshold)
        )

    observed = specimen.get("observed_conditions", ())
    if not isinstance(observed, (list, tuple, set, frozenset)):
        raise ValueError("observed_conditions must be a sequence, got %r" % (observed,))
    declared = set(criteria["disqualifying_conditions"])
    seen = []
    for condition in observed:
        condition = _require_text("observed condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("inspection reports an unknown condition %s" % condition)
        seen.append(condition)
        if condition in declared and condition not in modes:
            modes.append(condition)
            findings.append(
                "%s shows %s, which the specification lists as disqualifying "
                "on its own" % (specimen_id, condition)
            )

    modes = sorted(set(modes))
    if modes:
        verdict = SPECIMEN_FAILED
    elif unread:
        verdict = SPECIMEN_NOT_EVALUATED
    else:
        verdict = SPECIMEN_PASSED

    margins = {name: drift["margin"] for name, drift in drifts.items()}
    return {
        "specimen_id": specimen_id,
        "verdict": verdict,
        "failed": verdict == SPECIMEN_FAILED,
        "evaluated": not unread,
        "failure_modes": modes,
        "parameter_drifts": drifts,
        "margins": margins,
        "limiting_margin": min(margins.values()) if margins else None,
        "unread_parameters": sorted(set(unread)),
        "measurement_bias_adequate": bias_ok,
        "observed_conditions": sorted(set(seen)),
        "findings": findings,
    }


def assess_blocking_diode_subgroup(subgroup, criteria=DEFAULT_FAILURE_CRITERIA):
    """Full clause 12.7.1 sweep over one tested blocking diode subgroup."""
    validate_failure_criteria(criteria)
    if not isinstance(subgroup, dict):
        raise ValueError("subgroup must be a mapping, got %r" % (subgroup,))
    subgroup_id = _require_text("subgroup_id", subgroup.get("subgroup_id"))
    _require_text("test_reference", subgroup.get("test_reference"))

    specimens = subgroup.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("subgroup specimens must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for specimen in specimens:
        assessed = assess_blocking_diode_specimen(specimen, criteria)
        if assessed["specimen_id"] in seen:
            raise ValueError(
                "subgroup declares specimen %s twice" % assessed["specimen_id"]
            )
        seen.add(assessed["specimen_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["specimen_id"])

    failed = [e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_FAILED]
    passed = [e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_PASSED]
    unevaluated = [
        e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_NOT_EVALUATED
    ]

    total = len(assessments)
    failed_fraction = len(failed) / float(total)
    allowance = float(criteria["max_failed_fraction"])
    share_ok = _within(failed_fraction, allowance)

    mode_tally = {}
    for entry in assessments:
        for mode in entry["failure_modes"]:
            mode_tally.setdefault(mode, []).append(entry["specimen_id"])

    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])
    if unevaluated:
        findings.append(
            "subgroup %s cannot be closed while %s carry no complete reading pair"
            % (subgroup_id, ", ".join(sorted(unevaluated)))
        )
    if not share_ok:
        findings.append(
            "subgroup %s failed %d of %d parts, a share of %.4f against an "
            "allowance of %.4f"
            % (subgroup_id, len(failed), total, failed_fraction, allowance)
        )

    if unevaluated:
        verdict = SUBGROUP_NOT_EVALUABLE
    elif not share_ok:
        verdict = SUBGROUP_FAILED
    else:
        verdict = SUBGROUP_MEETS_CRITERIA

    return {
        "verdict": verdict,
        "subgroup_id": subgroup_id,
        "specimen_assessments": assessments,
        "failed_specimen_ids": sorted(failed),
        "passed_specimen_ids": sorted(passed),
        "unevaluated_specimen_ids": sorted(unevaluated),
        "failed_fraction": failed_fraction,
        "allowed_failed_fraction": allowance,
        "failed_share_within_allowance": share_ok,
        "modes_by_specimen": {k: sorted(v) for k, v in mode_tally.items()},
        "findings": findings,
    }
