#!/usr/bin/env python3
"""Evenness of the metallisation laid across a bare solar cell contact.

Anchor: ECSS-E-ST-20-08C clause 7.5.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The qualification measurement behind this clause asks a narrow question:
across one contact feature of a bare cell -- a grid finger, a bus bar,
the rear metallisation -- is the deposited metal the same depth
everywhere it was laid down? A contact that is thick at one end and thin
at the other carries current unevenly, heats unevenly and takes an
interconnect weld unevenly, and none of that is visible in a single
spot reading or in a feature average.

So the measurement is a map, not a number. Thickness readings are taken
at known positions along the feature, and the reduction has to do three
things the raw map does not do by itself:

    reject a map too sparse or too clustered to speak for the feature
    reduce the spread to figures a limit can be written against
    separate a plating gradient from random scatter from one outlier

The third is what makes the result actionable. The same coefficient of
variation can come from a mask that drifted along the cell, from bath
agitation noise, or from a single blocked nozzle, and those are three
different corrective actions on the line.

Thickness is carried in micrometres and position in millimetres along
the feature. Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTACT_FEATURES = (
    "front-bus-bar",
    "front-grid-finger",
    "rear-bus-bar",
    "rear-contact",
)

DEFAULT_UNIFORMITY_POLICY = {
    "minimum_points_per_feature": 5,
    "minimum_position_span_fraction": 0.80,
    "maximum_coefficient_of_variation": 0.10,
    "minimum_uniformity_ratio": 0.80,
    "maximum_point_deviation_fraction": 0.20,
    "gradient_significance_fraction": 0.05,
    "outlier_residual_sigma": 2.5,
}

_FRACTION_POLICY_KEYS = (
    "minimum_position_span_fraction",
    "maximum_coefficient_of_variation",
    "minimum_uniformity_ratio",
    "maximum_point_deviation_fraction",
    "gradient_significance_fraction",
)

UNIFORM_VERDICT = "metallisation-uniform"
NON_UNIFORM_VERDICT = "metallisation-non-uniform"
SAMPLE_INADEQUATE = "thickness-map-inadequate"

MODE_WITHIN_LIMITS = "within-limits"
MODE_GRADIENT = "gradient-dominated"
MODE_OUTLIER = "outlier-dominated"
MODE_SCATTER = "scatter-dominated"

NON_UNIFORMITY_MODES = (
    MODE_WITHIN_LIMITS,
    MODE_GRADIENT,
    MODE_OUTLIER,
    MODE_SCATTER,
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A limit written in one unit and compared in another lands a few units
    in the last place either side of the bound. The limit is never
    relaxed; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_uniformity_policy(policy=None):
    """Normalise the declared uniformity limits, rejecting an unusable set."""
    if policy is None:
        policy = DEFAULT_UNIFORMITY_POLICY
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_UNIFORMITY_POLICY)
    for key in policy:
        if key not in DEFAULT_UNIFORMITY_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = policy[key]
    points = merged["minimum_points_per_feature"]
    if not isinstance(points, int) or isinstance(points, bool) or points < 2:
        raise ValueError(
            "minimum_points_per_feature must be an integer of at least two, got %r"
            % (points,)
        )
    for key in _FRACTION_POLICY_KEYS:
        merged[key] = _require_fraction(key, merged[key])
    merged["outlier_residual_sigma"] = _require_positive(
        "outlier_residual_sigma", merged["outlier_residual_sigma"]
    )
    return merged


def normalise_thickness_map(readings):
    """Order and validate the mapped thickness readings for one feature.

    Each reading is a position in millimetres along the feature and a
    metallisation thickness in micrometres. Two readings at the same
    position are a transcription fault, not a repeat: they make the
    position axis degenerate and no slope can be fitted through them.
    """
    if isinstance(readings, dict) or isinstance(readings, (str, bytes)):
        raise ValueError("readings must be a sequence of position/thickness pairs")
    try:
        items = list(readings)
    except TypeError:
        raise ValueError("readings must be a sequence of position/thickness pairs")
    if len(items) < 2:
        raise ValueError("at least two readings are needed, got %d" % (len(items),))
    mapped = []
    seen = set()
    for index, item in enumerate(items):
        if isinstance(item, dict):
            position = item.get("position_mm")
            thickness = item.get("thickness_um")
        else:
            try:
                position, thickness = item
            except (TypeError, ValueError):
                raise ValueError(
                    "reading %d must be a position/thickness pair, got %r"
                    % (index, item)
                )
        position = _require_number("reading %d position_mm" % index, position)
        if position < 0.0:
            raise ValueError(
                "reading %d position_mm must not be negative, got %r"
                % (index, position)
            )
        thickness = _require_positive("reading %d thickness_um" % index, thickness)
        key = round(position, 9)
        if key in seen:
            raise ValueError(
                "two readings share position %g mm; positions must be distinct"
                % (position,)
            )
        seen.add(key)
        mapped.append((position, thickness))
    mapped.sort()
    return tuple(mapped)


def map_span_mm(readings):
    """Distance along the feature between the first and last reading."""
    mapped = normalise_thickness_map(readings)
    return mapped[-1][0] - mapped[0][0]


def sample_adequacy(readings, feature_length_mm, policy=None):
    """Whether the map is dense enough and wide enough to speak for the feature."""
    limits = validate_uniformity_policy(policy)
    mapped = normalise_thickness_map(readings)
    length = _require_positive("feature_length_mm", feature_length_mm)
    span = mapped[-1][0] - mapped[0][0]
    if mapped[-1][0] > length and not math.isclose(
        mapped[-1][0], length, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "reading at %g mm lies beyond the declared feature length %g mm"
            % (mapped[-1][0], length)
        )
    span_fraction = span / length
    findings = []
    enough_points = len(mapped) >= limits["minimum_points_per_feature"]
    if not enough_points:
        findings.append(
            "%d readings taken, %d needed to speak for the feature"
            % (len(mapped), limits["minimum_points_per_feature"])
        )
    wide_enough = _at_least(span_fraction, limits["minimum_position_span_fraction"])
    if not wide_enough:
        findings.append(
            "readings cover %.0f%% of the feature, %.0f%% needed"
            % (
                span_fraction * 100.0,
                limits["minimum_position_span_fraction"] * 100.0,
            )
        )
    return {
        "point_count": len(mapped),
        "span_mm": span,
        "feature_length_mm": length,
        "span_fraction": span_fraction,
        "adequate": enough_points and wide_enough,
        "findings": findings,
    }


def thickness_statistics(readings):
    """Reduce the map to the spread figures a uniformity limit is written against."""
    mapped = normalise_thickness_map(readings)
    values = [thickness for _, thickness in mapped]
    count = len(values)
    mean = sum(values) / count
    minimum = min(values)
    maximum = max(values)
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    stdev = math.sqrt(variance)
    return {
        "point_count": count,
        "mean_um": mean,
        "minimum_um": minimum,
        "maximum_um": maximum,
        "range_um": maximum - minimum,
        "sample_stdev_um": stdev,
        "coefficient_of_variation": stdev / mean,
        "uniformity_ratio": minimum / maximum,
    }


def point_deviations(readings):
    """Signed departure of each reading from the feature mean, as a fraction."""
    mapped = normalise_thickness_map(readings)
    mean = sum(thickness for _, thickness in mapped) / len(mapped)
    return tuple(
        (position, (thickness - mean) / mean) for position, thickness in mapped
    )


def worst_point_deviation(readings):
    """Largest absolute departure of any single reading from the feature mean."""
    return max(abs(deviation) for _, deviation in point_deviations(readings))


def thickness_gradient(readings):
    """Least-squares slope of thickness along the feature, and its size.

    The slope alone means nothing without the feature it crosses: half a
    micrometre per millimetre is negligible on a grid finger and severe
    on a bus bar. So the slope is also returned normalised -- the drift
    it produces end to end, as a fraction of the feature mean.

    Two residual scales are returned. The plain one describes the fit.
    The trimmed one drops the single largest residual before taking the
    scale, because an outlier inflates any scale computed from a set it
    is a member of, and at the sample sizes this measurement runs at
    that inflation is enough to hide the outlier from every threshold.
    """
    mapped = normalise_thickness_map(readings)
    positions = [position for position, _ in mapped]
    values = [thickness for _, thickness in mapped]
    count = len(mapped)
    position_mean = sum(positions) / count
    value_mean = sum(values) / count
    denominator = sum((position - position_mean) ** 2 for position in positions)
    if denominator <= 0.0:
        raise ValueError("all readings share one position; no slope can be fitted")
    numerator = sum(
        (positions[i] - position_mean) * (values[i] - value_mean)
        for i in range(count)
    )
    slope = numerator / denominator
    intercept = value_mean - slope * position_mean
    span = positions[-1] - positions[0]
    drift = slope * span
    residuals = tuple(
        values[i] - (intercept + slope * positions[i]) for i in range(count)
    )
    if count > 2:
        residual_stdev = math.sqrt(
            sum(residual ** 2 for residual in residuals) / (count - 2)
        )
    else:
        residual_stdev = 0.0
    trimmed = sorted(residuals, key=abs)[:-1]
    if len(trimmed) > 1:
        trimmed_stdev = math.sqrt(
            sum(residual ** 2 for residual in trimmed) / (len(trimmed) - 1)
        )
    else:
        trimmed_stdev = 0.0
    return {
        "slope_um_per_mm": slope,
        "intercept_um": intercept,
        "end_to_end_drift_um": drift,
        "drift_fraction": abs(drift) / value_mean,
        "residuals_um": residuals,
        "residual_stdev_um": residual_stdev,
        "residual_scatter_fraction": residual_stdev / value_mean,
        "trimmed_residual_stdev_um": trimmed_stdev,
    }


def dominant_non_uniformity_mode(readings, policy=None):
    """Name what the spread is made of, so the line knows what to correct.

    A drift the fit can account for is a gradient; a single reading far
    off an otherwise flat fit is an outlier; anything left is scatter.
    """
    limits = validate_uniformity_policy(policy)
    statistics = thickness_statistics(readings)
    gradient = thickness_gradient(readings)
    within = (
        _at_most(
            statistics["coefficient_of_variation"],
            limits["maximum_coefficient_of_variation"],
        )
        and _at_least(
            statistics["uniformity_ratio"], limits["minimum_uniformity_ratio"]
        )
        and _at_most(
            worst_point_deviation(readings),
            limits["maximum_point_deviation_fraction"],
        )
    )
    if within:
        return MODE_WITHIN_LIMITS
    if _at_least(
        gradient["drift_fraction"], limits["gradient_significance_fraction"]
    ):
        return MODE_GRADIENT
    scale = gradient["trimmed_residual_stdev_um"]
    if scale > 0.0:
        worst_residual = max(abs(residual) for residual in gradient["residuals_um"])
        if _at_least(worst_residual / scale, limits["outlier_residual_sigma"]):
            return MODE_OUTLIER
    return MODE_SCATTER


def assess_feature_uniformity(feature_case, policy=None):
    """Full clause 7.5.9 judgement of one mapped contact feature."""
    if not isinstance(feature_case, dict):
        raise ValueError("feature case must be a mapping, got %r" % (feature_case,))
    limits = validate_uniformity_policy(policy)
    feature = _require_choice(
        "feature", feature_case.get("feature"), CONTACT_FEATURES
    )
    readings = feature_case.get("readings")
    adequacy = sample_adequacy(
        readings, feature_case.get("feature_length_mm"), limits
    )
    statistics = thickness_statistics(readings)
    gradient = thickness_gradient(readings)
    worst = worst_point_deviation(readings)
    findings = list(adequacy["findings"])
    if not _at_most(
        statistics["coefficient_of_variation"],
        limits["maximum_coefficient_of_variation"],
    ):
        findings.append(
            "%s spread is %.1f%% of the mean, limit %.1f%%"
            % (
                feature,
                statistics["coefficient_of_variation"] * 100.0,
                limits["maximum_coefficient_of_variation"] * 100.0,
            )
        )
    if not _at_least(
        statistics["uniformity_ratio"], limits["minimum_uniformity_ratio"]
    ):
        findings.append(
            "%s thinnest reading is %.2f of the thickest, floor %.2f"
            % (
                feature,
                statistics["uniformity_ratio"],
                limits["minimum_uniformity_ratio"],
            )
        )
    if not _at_most(worst, limits["maximum_point_deviation_fraction"]):
        findings.append(
            "%s worst reading departs %.1f%% from the mean, limit %.1f%%"
            % (
                feature,
                worst * 100.0,
                limits["maximum_point_deviation_fraction"] * 100.0,
            )
        )
    mode = dominant_non_uniformity_mode(readings, limits)
    if mode == MODE_GRADIENT:
        findings.append(
            "%s drifts %.1f%% end to end; a plating gradient, not scatter"
            % (feature, gradient["drift_fraction"] * 100.0)
        )
    elif mode == MODE_OUTLIER:
        findings.append(
            "%s spread is carried by one reading off an otherwise flat fit"
            % (feature,)
        )
    uniform = adequacy["adequate"] and mode == MODE_WITHIN_LIMITS
    if not adequacy["adequate"]:
        verdict = SAMPLE_INADEQUATE
    elif uniform:
        verdict = UNIFORM_VERDICT
    else:
        verdict = NON_UNIFORM_VERDICT
    return {
        "feature": feature,
        "sample_adequacy": adequacy,
        "statistics": statistics,
        "gradient": gradient,
        "worst_point_deviation": worst,
        "non_uniformity_mode": mode,
        "uniform": uniform,
        "verdict": verdict,
        "findings": findings,
    }


def assess_bare_cell_contact_uniformity(case, policy=None):
    """Roll the mapped features of one bare cell into a qualification verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    limits = validate_uniformity_policy(policy if policy is not None else case.get("policy"))
    features = case.get("features")
    if not isinstance(features, (list, tuple)) or not features:
        raise ValueError("case must carry at least one mapped contact feature")
    results = [assess_feature_uniformity(entry, limits) for entry in features]
    seen = [result["feature"] for result in results]
    if len(set(seen)) != len(seen):
        raise ValueError("each contact feature may be mapped only once per cell")
    findings = []
    for result in results:
        findings.extend(result["findings"])
    inadequate = tuple(
        result["feature"] for result in results if result["verdict"] == SAMPLE_INADEQUATE
    )
    non_uniform = tuple(
        result["feature"] for result in results if result["verdict"] == NON_UNIFORM_VERDICT
    )
    if inadequate:
        verdict = SAMPLE_INADEQUATE
    elif non_uniform:
        verdict = NON_UNIFORM_VERDICT
    else:
        verdict = UNIFORM_VERDICT
    modes = tuple(
        sorted(
            {
                result["non_uniformity_mode"]
                for result in results
                if result["non_uniformity_mode"] != MODE_WITHIN_LIMITS
            }
        )
    )
    return {
        "cell_identifier": case.get("cell_identifier"),
        "feature_results": tuple(results),
        "features_mapped": tuple(seen),
        "features_inadequate": inadequate,
        "features_non_uniform": non_uniform,
        "modes_observed": modes,
        "worst_coefficient_of_variation": max(
            result["statistics"]["coefficient_of_variation"] for result in results
        ),
        "uniform": verdict == UNIFORM_VERDICT,
        "verdict": verdict,
        "findings": findings,
    }
