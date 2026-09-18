"""Linearity and class-referenced accuracy of an output current telemetry.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.4.1 (the reported current is linear, and
its absolute accuracy is stated against the class current of the device across
the whole range). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate a calibration set of applied-against-reported current pairs that
   actually spans the declared range with enough distinct points for a
   straight-line fit to mean anything.
2. Form the signed absolute error at every point and divide it by the class
   current of the device, which is the reference this clause fixes: not the
   reading, and not the full scale of the chain.
3. Take the worst point, not the mean and not the root-mean-square, because
   the accuracy has to hold over the whole range.
4. Fit the straight line the chain is claimed to follow, split the error into
   a gain error, a zero offset and a residual non-linearity, and report each
   against the class current.
5. Report the coverage of the declared range and any reversal in the reported
   current, since a set that never reached the ends, or that folds back, is
   not evidence of a linear characteristic.
"""

import math

__all__ = [
    "ACCURACY_TOLERANCE",
    "DEFAULT_EDGE_TOLERANCE_FRACTION",
    "MIN_DISTINCT_POINTS",
    "validate_samples",
    "signed_errors",
    "class_referenced_errors",
    "worst_class_referenced_error",
    "compare_reference_bases",
    "fit_linear",
    "non_linearity_ratios",
    "max_non_linearity",
    "range_coverage",
    "reversal_indices",
    "assess_linearity",
]

# Accuracy verdicts are a comparison between two ratios a calibration can put
# exactly on top of each other. Absorb the representation error here instead
# of widening the allowed band.
ACCURACY_TOLERANCE = 1e-12

# A straight-line fit through two points has no residual by construction, so a
# non-linearity statement needs more distinct abscissae than that.
MIN_DISTINCT_POINTS = 3

# How close to an end of the declared range a sample has to come before the
# range counts as covered there, as a fraction of the range span.
DEFAULT_EDGE_TOLERANCE_FRACTION = 0.05


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def validate_samples(samples):
    """Return the calibration pairs as floats, ordered by applied current.

    Each pair is (applied current, reported current). The applied current is a
    real non-negative current; the reported current may be negative, because a
    negative zero offset can push the bottom of the range below zero.
    """
    if not isinstance(samples, (list, tuple)) or len(samples) < MIN_DISTINCT_POINTS:
        raise ValueError(
            "samples must be a sequence of at least %d (applied, reported) pairs"
            % MIN_DISTINCT_POINTS
        )
    pairs = []
    for i, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("samples[%d] must be an (applied, reported) pair" % i)
        applied = _real("samples[%d] applied current" % i, item[0])
        reported = _real("samples[%d] reported current" % i, item[1])
        if applied < 0.0:
            raise ValueError(
                "samples[%d] applied current must be non-negative, got %g" % (i, applied)
            )
        pairs.append((applied, reported))
    distinct = set(applied for applied, _ in pairs)
    if len(distinct) < MIN_DISTINCT_POINTS:
        raise ValueError(
            "samples carry only %d distinct applied currents; a linearity "
            "statement needs at least %d" % (len(distinct), MIN_DISTINCT_POINTS)
        )
    pairs.sort(key=lambda pair: pair[0])
    return pairs


def signed_errors(samples):
    """Return the signed absolute error, reported less applied, at each point."""
    return [reported - applied for applied, reported in validate_samples(samples)]


def class_referenced_errors(samples, class_current_a):
    """Return each signed absolute error as a fraction of the class current."""
    class_current = _positive("class_current_a", class_current_a)
    return [error / class_current for error in signed_errors(samples)]


def worst_class_referenced_error(samples, class_current_a):
    """Return the point whose class-referenced error has the largest magnitude."""
    pairs = validate_samples(samples)
    ratios = class_referenced_errors(pairs, class_current_a)
    index = 0
    for i, ratio in enumerate(ratios):
        if abs(ratio) > abs(ratios[index]):
            index = i
    applied, reported = pairs[index]
    return {
        "index": index,
        "applied_a": applied,
        "reported_a": reported,
        "error_a": reported - applied,
        "class_referenced_ratio": ratios[index],
    }


def compare_reference_bases(applied_a, reported_a, class_current_a, full_scale_a=None):
    """Return the same error expressed against class current, reading and full scale.

    The reading basis is undefined at the bottom of the range, which is why
    this clause fixes the class current as the reference instead.
    """
    class_current = _positive("class_current_a", class_current_a)
    applied = _real("applied_a", applied_a)
    reported = _real("reported_a", reported_a)
    if applied < 0.0:
        raise ValueError("applied_a must be non-negative, got %g" % applied)
    error = reported - applied
    out = {
        "error_a": error,
        "class_referenced_ratio": error / class_current,
        "reading_referenced_ratio": None,
        "full_scale_referenced_ratio": None,
    }
    if applied > 0.0:
        out["reading_referenced_ratio"] = error / applied
    if full_scale_a is not None:
        out["full_scale_referenced_ratio"] = error / _positive("full_scale_a", full_scale_a)
    return out


def fit_linear(samples):
    """Return the least-squares (slope, intercept) of reported against applied."""
    pairs = validate_samples(samples)
    n = float(len(pairs))
    sum_x = sum(applied for applied, _ in pairs)
    sum_y = sum(reported for _, reported in pairs)
    sum_xx = sum(applied * applied for applied, _ in pairs)
    sum_xy = sum(applied * reported for applied, reported in pairs)
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0.0:
        raise ValueError("applied currents are degenerate; no straight line can be fitted")
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return (slope, intercept)


def non_linearity_ratios(samples, class_current_a):
    """Return each residual from the fitted straight line over the class current."""
    pairs = validate_samples(samples)
    class_current = _positive("class_current_a", class_current_a)
    slope, intercept = fit_linear(pairs)
    return [
        (reported - (slope * applied + intercept)) / class_current
        for applied, reported in pairs
    ]


def max_non_linearity(samples, class_current_a):
    """Return the largest residual magnitude as a fraction of the class current."""
    return max(abs(ratio) for ratio in non_linearity_ratios(samples, class_current_a))


def range_coverage(samples, range_min_a, range_max_a,
                   edge_tolerance_fraction=DEFAULT_EDGE_TOLERANCE_FRACTION):
    """Return how far the calibration set reached towards each end of the range."""
    pairs = validate_samples(samples)
    low = _real("range_min_a", range_min_a)
    high = _real("range_max_a", range_max_a)
    if low < 0.0:
        raise ValueError("range_min_a must be non-negative, got %g" % low)
    if high <= low:
        raise ValueError("range_max_a %g must exceed range_min_a %g" % (high, low))
    fraction = _real("edge_tolerance_fraction", edge_tolerance_fraction)
    if fraction < 0.0 or fraction >= 0.5:
        raise ValueError(
            "edge_tolerance_fraction must sit in [0, 0.5), got %g" % fraction
        )
    span = high - low
    allowance = span * fraction
    lowest = pairs[0][0]
    highest = pairs[-1][0]
    low_gap = max(0.0, lowest - low)
    high_gap = max(0.0, high - highest)
    return {
        "lowest_applied_a": lowest,
        "highest_applied_a": highest,
        "low_gap_a": low_gap,
        "high_gap_a": high_gap,
        "allowance_a": allowance,
        "low_covered": low_gap <= allowance,
        "high_covered": high_gap <= allowance,
        "covered": low_gap <= allowance and high_gap <= allowance,
    }


def reversal_indices(samples):
    """Return the indices at which the reported current falls as applied current rises."""
    pairs = validate_samples(samples)
    out = []
    for i in range(1, len(pairs)):
        if pairs[i][0] == pairs[i - 1][0]:
            continue
        if pairs[i][1] < pairs[i - 1][1]:
            out.append(i)
    return out


def assess_linearity(spec):
    """Run the clause 5.2.8.4.1 linearity and class-referenced accuracy assessment.

    spec keys: samples, class_current_a, range_a (pair), allowed_error_ratio;
    optional allowed_non_linearity_ratio, edge_tolerance_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("samples", "class_current_a", "range_a", "allowed_error_ratio"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    declared_range = spec["range_a"]
    if not isinstance(declared_range, (list, tuple)) or len(declared_range) != 2:
        raise ValueError("spec['range_a'] must be a (minimum, maximum) pair")
    allowed = _positive("allowed_error_ratio", spec["allowed_error_ratio"])
    if allowed >= 1.0:
        raise ValueError(
            "allowed_error_ratio is a fraction of the class current below 1.0, "
            "got %g" % allowed
        )
    pairs = validate_samples(spec["samples"])
    class_current = _positive("class_current_a", spec["class_current_a"])
    worst = worst_class_referenced_error(pairs, class_current)
    magnitude = abs(worst["class_referenced_ratio"])
    within = magnitude < allowed or math.isclose(
        magnitude, allowed, rel_tol=0.0, abs_tol=ACCURACY_TOLERANCE
    )
    coverage = range_coverage(
        pairs,
        declared_range[0],
        declared_range[1],
        spec.get("edge_tolerance_fraction", DEFAULT_EDGE_TOLERANCE_FRACTION),
    )
    reversals = reversal_indices(pairs)
    slope, intercept = fit_linear(pairs)
    residual = max_non_linearity(pairs, class_current)
    findings = []
    if not within:
        findings.append(
            "worst absolute error %.6f A at %.4f A applied is %.3f%% of the "
            "class current, past the allowed %.3f%%"
            % (worst["error_a"], worst["applied_a"], magnitude * 100.0, allowed * 100.0)
        )
    if not coverage["low_covered"]:
        findings.append(
            "the calibration never came within %.4f A of the bottom of the "
            "declared range; the accuracy is unproven there" % coverage["allowance_a"]
        )
    if not coverage["high_covered"]:
        findings.append(
            "the calibration stopped %.4f A short of the top of the declared "
            "range; the accuracy is unproven there" % coverage["high_gap_a"]
        )
    if reversals:
        findings.append(
            "the reported current falls as the applied current rises at "
            "sample %s; the characteristic is not linear"
            % ", ".join(str(i) for i in reversals)
        )
    allowed_residual = spec.get("allowed_non_linearity_ratio")
    residual_ok = True
    if allowed_residual is not None:
        limit = _positive("allowed_non_linearity_ratio", allowed_residual)
        residual_ok = residual < limit or math.isclose(
            residual, limit, rel_tol=0.0, abs_tol=ACCURACY_TOLERANCE
        )
        if not residual_ok:
            findings.append(
                "residual departure from the fitted line is %.3f%% of the class "
                "current, past the allowed %.3f%%" % (residual * 100.0, limit * 100.0)
            )
    return {
        "worst_error": worst,
        "worst_class_referenced_ratio": magnitude,
        "allowed_error_ratio": allowed,
        "within_accuracy": within,
        "coverage": coverage,
        "reversal_indices": reversals,
        "gain_error": slope - 1.0,
        "offset_class_ratio": intercept / class_current,
        "max_non_linearity_ratio": residual,
        "compliant": within and coverage["covered"] and not reversals and residual_ok,
        "findings": findings,
    }
