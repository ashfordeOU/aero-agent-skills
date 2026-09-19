#!/usr/bin/env python3
"""Validation of the test process and service provision,
ECSS-Q-ST-20-07C clause 5.7.4.2.

Paraphrased clause intent, no verbatim standard text. Before a designed
process is used on customer work the centre has to show, from runs it
actually made, that the process returns results a customer can rely on.
This module turns replicate-run data into that evidence:

  group spreads pooled        -> repeatability standard deviation
  spread of the group means   -> reproducibility, once repeatability is
                                 taken out of it
  reference specimen          -> bias, which no spread reveals
  quadrature + coverage       -> expanded uncertainty vs the tolerance

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Standard deviations, ratios and expanded
# uncertainties are floats, so a process that exactly meets a limit can
# land a few units in the last place the wrong side of it. The tolerance
# absorbs that representation error only; it never relaxes a limit.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# A validation quoting fewer runs than this is an indication, not
# evidence.
MIN_TOTAL_RUNS = 6

# A single group cannot resolve a reproducibility term at all.
MIN_GROUPS = 2

# Coverage factor applied to the combined standard uncertainty.
DEFAULT_COVERAGE_FACTOR = 2.0

# The tolerance has to be at least this many expanded uncertainties wide
# before the process can decide conformance against it.
DEFAULT_MIN_CAPABILITY = 2.0

PROCESS_VALIDATED = "test-process-validated"
PROCESS_NOT_VALIDATED = "test-process-not-validated"


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_groups(groups, min_groups=MIN_GROUPS, min_total_runs=MIN_TOTAL_RUNS):
    """Validate the replicate-run groups and return them as lists of floats."""
    if not isinstance(groups, (list, tuple)):
        raise ValueError("groups: must be a sequence of run groups")
    floor_groups = int(min_groups)
    floor_runs = int(min_total_runs)
    if floor_groups < 1:
        raise ValueError("min_groups must be >= 1, got %d" % floor_groups)
    if floor_runs < 1:
        raise ValueError("min_total_runs must be >= 1, got %d" % floor_runs)
    if len(groups) < floor_groups:
        raise ValueError(
            "groups: %d group(s) cannot resolve reproducibility; %d are needed"
            % (len(groups), floor_groups)
        )
    out = []
    total = 0
    for index, group in enumerate(groups):
        where = "groups[%d]" % index
        if not isinstance(group, (list, tuple)):
            raise ValueError("%s: must be a sequence of run results" % where)
        if len(group) < 2:
            raise ValueError(
                "%s: %d run(s) has no within-group spread; 2 are needed"
                % (where, len(group))
            )
        values = [_finite(v, "%s[%d]" % (where, i)) for i, v in enumerate(group)]
        total += len(values)
        out.append(values)
    if total < floor_runs:
        raise ValueError(
            "groups: %d run(s) in total is under the %d a validation quotes"
            % (total, floor_runs)
        )
    return out


def mean_value(values):
    """Arithmetic mean of a non-empty sequence of results."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values: must be a non-empty sequence")
    numbers = [_finite(v, "values[%d]" % i) for i, v in enumerate(values)]
    return sum(numbers) / len(numbers)


def sample_standard_deviation(values):
    """Sample standard deviation on n minus one degrees of freedom."""
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("values: at least 2 results are needed for a spread")
    numbers = [_finite(v, "values[%d]" % i) for i, v in enumerate(values)]
    centre = sum(numbers) / len(numbers)
    variance = sum((v - centre) ** 2 for v in numbers) / (len(numbers) - 1)
    return math.sqrt(variance)


def repeatability_sd(groups):
    """Pooled within-group standard deviation, weighted by degrees of freedom."""
    normalized = validate_groups(groups, min_groups=1, min_total_runs=2)
    numerator = 0.0
    freedom = 0
    for values in normalized:
        spread = sample_standard_deviation(values)
        degrees = len(values) - 1
        numerator += degrees * spread * spread
        freedom += degrees
    if freedom < 1:
        raise ValueError("groups: no degrees of freedom to pool")
    return math.sqrt(numerator / freedom)


def reproducibility_sd(groups):
    """Between-group spread with the within-group contribution removed."""
    normalized = validate_groups(groups)
    means = [mean_value(values) for values in normalized]
    between = sample_standard_deviation(means)
    within = repeatability_sd(groups)
    average_size = sum(len(values) for values in normalized) / len(normalized)
    residual = between * between - (within * within) / average_size
    if residual <= 0.0:
        return 0.0
    return math.sqrt(residual)


def bias_estimate(groups, reference_value):
    """Overall mean less the known value of the reference specimen."""
    normalized = validate_groups(groups, min_groups=1, min_total_runs=2)
    reference = _finite(reference_value, "reference_value")
    flat = [v for values in normalized for v in values]
    return mean_value(flat) - reference


def combined_standard_uncertainty(repeatability, reproducibility, bias):
    """Quadrature sum of the two spreads and the bias magnitude."""
    first = _finite(repeatability, "repeatability")
    second = _finite(reproducibility, "reproducibility")
    third = _finite(bias, "bias")
    if first < 0.0 or second < 0.0:
        raise ValueError("standard deviations must be >= 0")
    return math.sqrt(first * first + second * second + third * third)


def expanded_uncertainty(standard_uncertainty, coverage=DEFAULT_COVERAGE_FACTOR):
    """Combined standard uncertainty scaled by the coverage factor."""
    value = _finite(standard_uncertainty, "standard_uncertainty")
    factor = _finite(coverage, "coverage")
    if value < 0.0:
        raise ValueError("standard_uncertainty must be >= 0, got %g" % value)
    if factor < 1.0:
        raise ValueError("coverage must be >= 1, got %g" % factor)
    return factor * value


def capability_ratio(tolerance, expanded):
    """How many expanded uncertainties wide the tolerance to be resolved is."""
    band = _finite(tolerance, "tolerance")
    spread = _finite(expanded, "expanded")
    if band <= 0.0:
        raise ValueError("tolerance must be > 0, got %g" % band)
    if spread <= 0.0:
        raise ValueError("expanded must be > 0 to form a ratio, got %g" % spread)
    return band / spread


def validate_test_process(
    record,
    coverage=DEFAULT_COVERAGE_FACTOR,
    min_capability=DEFAULT_MIN_CAPABILITY,
):
    """Full clause 5.7.4.2 validation pass over one set of replicate runs."""
    if not isinstance(record, dict):
        raise ValueError("record: must be a mapping")
    floor = _finite(min_capability, "min_capability")
    if floor <= 0.0:
        raise ValueError("min_capability must be > 0, got %g" % floor)

    groups = validate_groups(record.get("groups"))
    reference = _finite(record.get("reference_value"), "reference_value")
    tolerance = _finite(record.get("tolerance"), "tolerance")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be > 0, got %g" % tolerance)
    bias_allowance = _finite(record.get("bias_allowance"), "bias_allowance")
    if bias_allowance < 0.0:
        raise ValueError("bias_allowance must be >= 0, got %g" % bias_allowance)

    within = repeatability_sd(groups)
    between = reproducibility_sd(groups)
    bias = bias_estimate(groups, reference)
    combined = combined_standard_uncertainty(within, between, bias)
    expanded = expanded_uncertainty(combined, coverage)
    ratio = capability_ratio(tolerance, expanded) if expanded > 0.0 else None

    findings = []
    if not at_most(abs(bias), bias_allowance):
        findings.append(
            "bias of %g against the reference specimen exceeds the %g the process "
            "is allowed" % (bias, bias_allowance)
        )
    if ratio is not None and not at_least(ratio, floor):
        findings.append(
            "capability ratio %g is under the %g needed to decide conformance "
            "against a tolerance of %g" % (ratio, floor, tolerance)
        )

    limitations = []
    if between <= 0.0:
        limitations.append(
            "the run groups do not resolve a reproducibility term, so the expanded "
            "uncertainty rests on repeatability and bias alone"
        )

    return {
        "group_means": [mean_value(values) for values in groups],
        "group_spreads": [sample_standard_deviation(values) for values in groups],
        "total_runs": sum(len(values) for values in groups),
        "repeatability_sd": within,
        "reproducibility_sd": between,
        "bias": bias,
        "combined_standard_uncertainty": combined,
        "expanded_uncertainty": expanded,
        "capability_ratio": ratio,
        "findings": findings,
        "limitations": limitations,
        "verdict": PROCESS_VALIDATED if not findings else PROCESS_NOT_VALIDATED,
    }
