#!/usr/bin/env python3
"""ECSS-E-ST-10C §4.2 development test planning and evaluation (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS space systems testing standard requires that development tests are
planned with explicit objectives and success criteria, executed under
controlled and documented conditions within specified tolerance bands,
and reported with recorded actual conditions, outcome determinations,
and a complete anomaly record. Development tests precede the
qualification test programme; they are used to generate design margin
data and reduce programme risk and are not subject to the full
qualification witness chain. This module implements objective
validation, test-type recognition, condition tolerance checking,
measurement-against-requirement evaluation, test-plan assembly, and
report completeness verification; it does not implement environmental
models, hardware qualification records, or the acceptance-test chain.
"""

VALID_TEST_CATEGORIES = frozenset({
    "functional",
    "environmental",
    "structural",
    "electrical",
    "thermal",
    "mechanical",
})

REQUIRED_OBJECTIVE_FIELDS = frozenset({
    "objective_id",
    "description",
    "success_criterion",
})

REQUIRED_REPORT_FIELDS = frozenset({
    "test_id",
    "objective_ids",
    "actual_conditions",
    "measurements",
    "outcome",
    "anomalies",
})

VALID_OUTCOMES = frozenset({"pass", "fail", "inconclusive"})


def validate_test_objective(objective):
    """Returns a sorted list of required field names absent from a
    development test objective dict. An empty list means the objective
    is complete. Raises TypeError if objective is not a dict."""
    if not isinstance(objective, dict):
        raise TypeError(
            "objective must be a dict, got %r" % type(objective).__name__
        )
    return sorted(f for f in REQUIRED_OBJECTIVE_FIELDS if f not in objective)


def categorize_test(test_type):
    """Returns the development test category string for a given test_type.
    Raises ValueError for a type not in the recognized set."""
    if test_type not in VALID_TEST_CATEGORIES:
        raise ValueError(
            "unrecognized development test type %r under E-ST-10C §4.2"
            % (test_type,)
        )
    return test_type


def check_condition_within_tolerance(nominal, actual, tolerance_fraction):
    """Returns True if the actual measured condition value falls within
    tolerance_fraction (0.0–1.0 fractional deviation) of the nominal
    specified value. For a zero nominal the allowable band collapses to
    zero so actual must equal nominal exactly.
    Raises ValueError for a negative tolerance_fraction or one > 1.0."""
    if tolerance_fraction < 0:
        raise ValueError("tolerance_fraction must be >= 0")
    if tolerance_fraction > 1.0:
        raise ValueError("tolerance_fraction must be <= 1.0")
    allowable_delta = abs(nominal) * tolerance_fraction
    return abs(actual - nominal) <= allowable_delta


def evaluate_test_conditions(specified_conditions, actual_conditions, tolerance_fraction):
    """Checks each specified nominal condition against the actual measured
    value recorded during the test.
    specified_conditions: {name: nominal_value}.
    actual_conditions:   {name: actual_value}.
    Returns {name: {"within_tolerance": bool, "nominal": v, "actual": v}}.
    Raises KeyError if a specified condition has no actual measurement.
    Does not mutate inputs."""
    results = {}
    for name, nominal in specified_conditions.items():
        if name not in actual_conditions:
            raise KeyError(
                "no actual measurement recorded for condition %r" % name
            )
        actual = actual_conditions[name]
        within = check_condition_within_tolerance(nominal, actual, tolerance_fraction)
        results[name] = {"within_tolerance": within, "nominal": nominal, "actual": actual}
    return results


def evaluate_measurements(measurements, requirements):
    """Evaluates a set of measurements against min/max requirement bounds.
    measurements:  {param: measured_value}.
    requirements:  {param: {"min": value, "max": value}}.
    Returns {"outcome": "pass"|"fail", "failures": [param, ...]}.
    A parameter present in requirements but absent from measurements is a
    failure. Raises ValueError if a requirement entry lacks "min" or "max"."""
    failures = []
    for param, req in requirements.items():
        if "min" not in req or "max" not in req:
            raise ValueError(
                "requirement for %r must have both 'min' and 'max' keys" % param
            )
        if param not in measurements:
            failures.append(param)
            continue
        val = measurements[param]
        if val < req["min"] or val > req["max"]:
            failures.append(param)
    return {"outcome": "pass" if not failures else "fail", "failures": failures}


def check_report_completeness(report):
    """Returns a sorted list of field names missing from a development test
    report. An empty list means the report satisfies the mandatory-element
    check. Raises TypeError if report is not a dict."""
    if not isinstance(report, dict):
        raise TypeError("report must be a dict, got %r" % type(report).__name__)
    return sorted(f for f in REQUIRED_REPORT_FIELDS if f not in report)


def build_development_test_plan(test_id, objectives, conditions):
    """Assembles and validates a development test plan.
    test_id:    unique identifier string.
    objectives: list of objective dicts (each validated by
                validate_test_objective).
    conditions: dict of {condition_name: nominal_value}.
    Returns {"test_id": str, "objectives": list, "conditions": dict,
             "validation_errors": list}. Does not mutate inputs."""
    errors = []
    if not test_id or not isinstance(test_id, str):
        errors.append("test_id must be a non-empty string")
    if not objectives:
        errors.append("at least one test objective is required")
    for i, obj in enumerate(objectives):
        missing = validate_test_objective(obj)
        if missing:
            errors.append("objective[%d] missing fields: %s" % (i, missing))
    if not conditions:
        errors.append("at least one test condition must be specified")
    return {
        "test_id": test_id,
        "objectives": list(objectives),
        "conditions": dict(conditions),
        "validation_errors": errors,
    }


def is_plan_valid(plan):
    """True when the plan returned by build_development_test_plan has no
    validation errors — the plan is ready for test execution."""
    return len(plan.get("validation_errors", [])) == 0
