#!/usr/bin/env python3
"""Acceptance test methods and conditions for solar cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.3.2. The methods and the conditions already
fixed for cell assembly qualification are reused for cell assembly
acceptance. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

What reuse actually means
-------------------------
    method      the acceptance activity runs the same measurement method the
                qualification baseline ran. A substituted method -- a faster
                probe, a different illumination source, an inspection by eye
                where the baseline used a microscope -- produces numbers that
                are not comparable with the qualification data set, however
                good the substitute is on its own terms.
    conditions  each condition carries the baseline value under its own
                sense. A severity condition is reused at least as severely
                (below it the acceptance test is weaker than the one the
                design was qualified against, so it can pass hardware the
                qualification would have caught). A limit condition is reused
                no more severely. A settings condition is simply matched.
    drift       a condition inside its declared tolerance is reuse; outside
                it in the weaker direction is a relaxation; far outside it in
                the stronger direction is an escalation that over-tests
                delivered hardware for no qualification reason.

Every acceptance activity has to trace to a baseline entry. One that traces
to nothing is not reuse at all, and is reported before any condition of it is
compared.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CONDITION_SENSES",
    "DEFAULT_CONDITION_TOLERANCE",
    "DEFAULT_OVER_TEST_FACTOR",
    "REUSE_TOLERANCE_REL",
    "CONDITION_REUSED",
    "CONDITION_RELAXED",
    "CONDITION_ESCALATED",
    "CONDITION_OMITTED",
    "CONDITION_UNBASELINED",
    "TEST_REUSED",
    "TEST_METHOD_SUBSTITUTED",
    "TEST_CONDITION_RELAXED",
    "TEST_CONDITION_ESCALATED",
    "TEST_UNBASELINED",
    "REUSE_CONFORMING",
    "REUSE_DEVIATING",
    "validate_identifier",
    "validate_real",
    "validate_tolerance",
    "validate_condition_baseline",
    "compare_condition",
    "compare_test",
    "assess_method_and_condition_reuse",
]

# How a condition is reused. 'at-least' is a severity the acceptance test may
# exceed but not fall below; 'at-most' is a limit it may fall below but not
# exceed; 'match' is a setting it reproduces.
CONDITION_SENSES = ("at-least", "at-most", "match")

# Default relative tolerance on a reused condition, and the factor beyond
# which a stronger-than-baseline condition is an over-test rather than
# conservatism.
DEFAULT_CONDITION_TOLERANCE = 0.02
DEFAULT_OVER_TEST_FACTOR = 1.25

# Condition comparisons are ratios of floats, so a condition that physically
# equals its baseline can land a few units in the last place either side of
# it. The comparisons absorb that instead of moving the baseline.
REUSE_TOLERANCE_REL = 1e-9

# Per-condition outcomes.
CONDITION_REUSED = "condition-reused"
CONDITION_RELAXED = "condition-relaxed"
CONDITION_ESCALATED = "condition-escalated"
CONDITION_OMITTED = "condition-omitted"
CONDITION_UNBASELINED = "condition-not-in-baseline"

# Per-test outcomes, ranked worst first by _TEST_RANK below.
TEST_REUSED = "acceptance-test-reuses-baseline"
TEST_METHOD_SUBSTITUTED = "acceptance-test-method-substituted"
TEST_CONDITION_RELAXED = "acceptance-test-condition-relaxed"
TEST_CONDITION_ESCALATED = "acceptance-test-condition-escalated"
TEST_UNBASELINED = "acceptance-test-has-no-baseline"

REUSE_CONFORMING = "sca-acceptance-reuse-conforming"
REUSE_DEVIATING = "sca-acceptance-reuse-deviating"

# An activity with no baseline cannot be compared at all, so it is reported
# first; a substituted method invalidates every condition beneath it, so it
# is reported before the conditions; a relaxation lets bad hardware through
# and outranks an escalation, which only costs good hardware.
_TEST_RANK = {
    TEST_UNBASELINED: 0,
    TEST_METHOD_SUBSTITUTED: 1,
    TEST_CONDITION_RELAXED: 2,
    TEST_CONDITION_ESCALATED: 3,
    TEST_REUSED: 4,
}


def validate_identifier(value, label):
    """Return value as a trimmed, non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier string" % label)
    return value.strip()


def validate_real(value, label):
    """Return value as a finite real number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_tolerance(value, label):
    """Return a relative tolerance in [0, 1)."""
    number = validate_real(value, label)
    if number < 0.0 or number >= 1.0:
        raise ValueError("%s must lie in [0, 1), got %g" % (label, number))
    return number


def validate_condition_baseline(condition, name="?"):
    """Return one validated qualification baseline condition."""
    if not isinstance(condition, dict):
        raise ValueError("baseline condition %r must be a mapping" % name)
    if "value" not in condition:
        raise ValueError("baseline condition %r is missing 'value'" % name)
    value = validate_real(condition["value"], "value of baseline condition %r" % name)
    sense = condition.get("sense", "match")
    if sense not in CONDITION_SENSES:
        raise ValueError(
            "sense of baseline condition %r must be one of %r, got %r"
            % (name, CONDITION_SENSES, sense)
        )
    tolerance = validate_tolerance(
        condition.get("tolerance", DEFAULT_CONDITION_TOLERANCE),
        "tolerance of baseline condition %r" % name,
    )
    units = condition.get("units")
    if units is not None:
        units = validate_identifier(units, "units of baseline condition %r" % name)
    return {
        "condition": name,
        "value": value,
        "sense": sense,
        "tolerance": tolerance,
        "units": units,
    }


def _within(declared, baseline, tolerance):
    """Return True when declared sits inside the relative tolerance band."""
    magnitude = abs(baseline)
    if magnitude > 0.0:
        allowed = magnitude * tolerance
    else:
        allowed = tolerance
    deviation = abs(declared - baseline)
    return deviation < allowed or math.isclose(
        deviation, allowed, rel_tol=REUSE_TOLERANCE_REL, abs_tol=0.0
    )


def compare_condition(declared, baseline, over_test_factor=DEFAULT_OVER_TEST_FACTOR):
    """Compare one declared acceptance condition with its baseline."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline condition must be a mapping")
    row = validate_condition_baseline(baseline, baseline.get("condition", "?"))
    value = validate_real(declared, "declared value of condition %r" % row["condition"])
    factor = validate_real(over_test_factor, "over_test_factor")
    if factor < 1.0:
        raise ValueError("over_test_factor must not be below unity, got %g" % factor)

    magnitude = abs(row["value"])
    if magnitude > 0.0:
        relative_deviation = (value - row["value"]) / magnitude
    else:
        relative_deviation = value - row["value"]

    inside = _within(value, row["value"], row["tolerance"])
    ceiling = row["value"] * factor
    floor = row["value"] / factor

    if inside:
        verdict = CONDITION_REUSED
    elif row["sense"] == "at-least":
        if value < row["value"]:
            verdict = CONDITION_RELAXED
        elif value > ceiling and not math.isclose(
            value, ceiling, rel_tol=REUSE_TOLERANCE_REL, abs_tol=0.0
        ):
            verdict = CONDITION_ESCALATED
        else:
            verdict = CONDITION_REUSED
    elif row["sense"] == "at-most":
        if value > row["value"]:
            verdict = CONDITION_RELAXED
        elif value < floor and not math.isclose(
            value, floor, rel_tol=REUSE_TOLERANCE_REL, abs_tol=0.0
        ):
            verdict = CONDITION_ESCALATED
        else:
            verdict = CONDITION_REUSED
    else:
        verdict = CONDITION_RELAXED if value < row["value"] else CONDITION_ESCALATED

    return {
        "condition": row["condition"],
        "declared": value,
        "baseline": row["value"],
        "sense": row["sense"],
        "tolerance": row["tolerance"],
        "relative_deviation": relative_deviation,
        "within_tolerance": inside,
        "verdict": verdict,
    }


def compare_test(declared, baseline, over_test_factor=DEFAULT_OVER_TEST_FACTOR):
    """Compare one declared acceptance activity with its qualification baseline."""
    if not isinstance(declared, dict):
        raise ValueError("declared acceptance activity must be a mapping")
    name = validate_identifier(declared.get("test"), "acceptance activity name")

    if baseline is None:
        return {
            "test": name,
            "method": declared.get("method"),
            "baseline_method": None,
            "method_reused": False,
            "conditions": [],
            "verdict": TEST_UNBASELINED,
            "rank": _TEST_RANK[TEST_UNBASELINED],
        }
    if not isinstance(baseline, dict):
        raise ValueError("baseline of activity %r must be a mapping" % name)

    method = validate_identifier(declared.get("method"), "method of activity %r" % name)
    baseline_method = validate_identifier(
        baseline.get("method"), "baseline method of activity %r" % name
    )
    method_reused = method == baseline_method

    declared_conditions = declared.get("conditions", {})
    if not isinstance(declared_conditions, dict):
        raise ValueError("conditions of activity %r must be a mapping" % name)
    baseline_conditions = baseline.get("conditions", {})
    if not isinstance(baseline_conditions, dict):
        raise ValueError("baseline conditions of activity %r must be a mapping" % name)

    rows = []
    for condition_name in sorted(baseline_conditions):
        spec = dict(baseline_conditions[condition_name]) if isinstance(
            baseline_conditions[condition_name], dict
        ) else baseline_conditions[condition_name]
        if not isinstance(spec, dict):
            raise ValueError(
                "baseline condition %r of activity %r must be a mapping"
                % (condition_name, name)
            )
        spec["condition"] = condition_name
        if condition_name not in declared_conditions:
            row = validate_condition_baseline(spec, condition_name)
            rows.append(
                {
                    "condition": condition_name,
                    "declared": None,
                    "baseline": row["value"],
                    "sense": row["sense"],
                    "tolerance": row["tolerance"],
                    "relative_deviation": None,
                    "within_tolerance": False,
                    "verdict": CONDITION_OMITTED,
                }
            )
            continue
        rows.append(
            compare_condition(
                declared_conditions[condition_name], spec, over_test_factor
            )
        )

    for condition_name in sorted(set(declared_conditions) - set(baseline_conditions)):
        rows.append(
            {
                "condition": condition_name,
                "declared": validate_real(
                    declared_conditions[condition_name],
                    "declared value of condition %r" % condition_name,
                ),
                "baseline": None,
                "sense": None,
                "tolerance": None,
                "relative_deviation": None,
                "within_tolerance": False,
                "verdict": CONDITION_UNBASELINED,
            }
        )

    relaxed = [r["condition"] for r in rows if r["verdict"] == CONDITION_RELAXED]
    escalated = [r["condition"] for r in rows if r["verdict"] == CONDITION_ESCALATED]
    omitted = [r["condition"] for r in rows if r["verdict"] == CONDITION_OMITTED]
    unbaselined = [r["condition"] for r in rows if r["verdict"] == CONDITION_UNBASELINED]

    if not method_reused:
        verdict = TEST_METHOD_SUBSTITUTED
    elif relaxed or omitted or unbaselined:
        verdict = TEST_CONDITION_RELAXED
    elif escalated:
        verdict = TEST_CONDITION_ESCALATED
    else:
        verdict = TEST_REUSED

    return {
        "test": name,
        "method": method,
        "baseline_method": baseline_method,
        "method_reused": method_reused,
        "conditions": rows,
        "relaxed_conditions": relaxed,
        "escalated_conditions": escalated,
        "omitted_conditions": omitted,
        "unbaselined_conditions": unbaselined,
        "verdict": verdict,
        "rank": _TEST_RANK[verdict],
    }


def assess_method_and_condition_reuse(spec):
    """Run the full clause 6.3.2 method and condition reuse assessment.

    spec keys: procedure_id, qualification_baseline, acceptance_tests, and an
    optional over_test_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("procedure_id", "qualification_baseline", "acceptance_tests"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    procedure_id = validate_identifier(spec["procedure_id"], "procedure_id")

    baseline = spec["qualification_baseline"]
    if not isinstance(baseline, dict) or not baseline:
        raise ValueError("qualification_baseline must be a non-empty mapping")

    declared = spec["acceptance_tests"]
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError("acceptance_tests must be a non-empty sequence")

    factor = validate_real(
        spec.get("over_test_factor", DEFAULT_OVER_TEST_FACTOR), "over_test_factor"
    )
    if factor < 1.0:
        raise ValueError("over_test_factor must not be below unity, got %g" % factor)

    graded = []
    for activity in declared:
        if not isinstance(activity, dict):
            raise ValueError("each acceptance activity must be a mapping")
        name = validate_identifier(activity.get("test"), "acceptance activity name")
        graded.append(compare_test(activity, baseline.get(name), factor))
    names = [g["test"] for g in graded]
    if len(set(names)) != len(names):
        raise ValueError("acceptance activities must be unique, got %r" % (names,))

    findings = []
    for row in sorted(graded, key=lambda g: (g["rank"], g["test"])):
        if row["verdict"] == TEST_UNBASELINED:
            findings.append(
                "acceptance activity %s traces to no qualification baseline, so it "
                "reuses nothing" % row["test"]
            )
        elif row["verdict"] == TEST_METHOD_SUBSTITUTED:
            findings.append(
                "acceptance activity %s runs method %s where qualification used %s"
                % (row["test"], row["method"], row["baseline_method"])
            )
        elif row["verdict"] == TEST_CONDITION_RELAXED:
            detail = row["relaxed_conditions"] + row["omitted_conditions"] + row[
                "unbaselined_conditions"
            ]
            findings.append(
                "acceptance activity %s does not reuse the qualification conditions: "
                "%s" % (row["test"], ", ".join(detail))
            )
        elif row["verdict"] == TEST_CONDITION_ESCALATED:
            findings.append(
                "acceptance activity %s over-tests delivered hardware on: %s"
                % (row["test"], ", ".join(row["escalated_conditions"]))
            )

    grouped = {}
    for row in graded:
        grouped.setdefault(row["verdict"], []).append(row["test"])
    for key in grouped:
        grouped[key].sort()

    reused = [g for g in graded if g["verdict"] == TEST_REUSED]
    unmatched = sorted(set(baseline) - set(names))
    return {
        "procedure_id": procedure_id,
        "tests": graded,
        "tests_by_verdict": grouped,
        "reuse_share": len(reused) / len(graded),
        "baseline_tests_not_reused": unmatched,
        "findings": findings,
        "verdict": REUSE_CONFORMING if not findings else REUSE_DEVIATING,
    }
