"""Detection limits and uncertainty for an infrared contamination method.

Anchor: ECSS-Q-ST-70-05C, quantification. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the blank replicates and form their mean and sample standard
   deviation.
2. Scale that standard deviation by the detection and quantification
   multipliers to obtain both limits in signal units.
3. Convert both limits through the calibration slope and the sampling factor
   (dilution / (recovery * sampled area)) into areal masses.
4. Place the sample reading against the two limits and return the reporting
   decision: not detected, detected but not quantified, or quantified.
5. Combine the relative uncertainty components in quadrature and expand by
   the coverage factor.
"""

import math

__all__ = [
    "DEFAULT_COVERAGE_FACTOR",
    "DETECTED_NOT_QUANTIFIED",
    "DETECTION_MULTIPLIER",
    "MIN_BLANK_REPLICATES",
    "NOT_DETECTED",
    "QUANTIFICATION_MULTIPLIER",
    "QUANTIFIED",
    "assess_detection_limits",
    "blank_mean",
    "blank_standard_deviation",
    "combined_relative_uncertainty",
    "detection_limit_signal",
    "expanded_uncertainty",
    "quantification_limit_signal",
    "reporting_decision",
    "sampling_factor",
    "signal_to_areal_mass",
    "validate_blank_replicates",
]

# A standard deviation from fewer replicates than this is itself too badly
# known to build a limit on.
MIN_BLANK_REPLICATES = 7

DETECTION_MULTIPLIER = 3.0
QUANTIFICATION_MULTIPLIER = 10.0
DEFAULT_COVERAGE_FACTOR = 2.0

NOT_DETECTED = "not-detected"
DETECTED_NOT_QUANTIFIED = "detected-not-quantified"
QUANTIFIED = "quantified"

_BOUND_TOLERANCE = 1e-12


def _positive(label, value, allow_zero=False):
    """Return value as a finite float, raising on a non-numeric or non-positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _at_least(value, bound):
    """True when value is above bound or lands on it within tolerance."""
    return value > bound or abs(value - bound) <= _BOUND_TOLERANCE


def validate_blank_replicates(values, minimum=MIN_BLANK_REPLICATES):
    """Return the validated list of blank replicate signals."""
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        raise ValueError("minimum must be an integer")
    if minimum < 2:
        raise ValueError("a standard deviation needs at least two replicates")
    if not isinstance(values, (list, tuple)):
        raise ValueError("blank replicates must be a sequence of signals")
    out = []
    for i, value in enumerate(values):
        out.append(_positive("blank replicate %d" % i, value, allow_zero=True))
    if len(out) < minimum:
        raise ValueError(
            "method needs at least %d blank replicates to fix a limit, got %d"
            % (minimum, len(out))
        )
    return out


def blank_mean(values, minimum=MIN_BLANK_REPLICATES):
    """Return the mean blank signal."""
    data = validate_blank_replicates(values, minimum)
    return sum(data) / float(len(data))


def blank_standard_deviation(values, minimum=MIN_BLANK_REPLICATES):
    """Return the sample standard deviation of the blank replicates."""
    data = validate_blank_replicates(values, minimum)
    mean = sum(data) / float(len(data))
    variance = sum((v - mean) ** 2 for v in data) / float(len(data) - 1)
    scale = max(max(abs(v) for v in data), 1.0e-12)
    # Zero scatter at the precision of the readings is a rounding artefact,
    # not a perfect method; the test is relative, never an exact zero.
    if variance <= (1.0e-12 * scale) ** 2:
        raise ValueError(
            "blank replicates show no scatter at the reported precision; the "
            "readings are rounded too coarsely to fix a limit"
        )
    return math.sqrt(variance)


def detection_limit_signal(standard_deviation,
                           multiplier=DETECTION_MULTIPLIER):
    """Return the detection limit in signal units."""
    sd = _positive("standard_deviation", standard_deviation)
    return sd * _positive("multiplier", multiplier)


def quantification_limit_signal(standard_deviation,
                                multiplier=QUANTIFICATION_MULTIPLIER):
    """Return the quantification limit in signal units."""
    sd = _positive("standard_deviation", standard_deviation)
    return sd * _positive("multiplier", multiplier)


def sampling_factor(dilution_factor, recovery_fraction, sampled_area_cm2):
    """Return the factor turning a deposit mass into an areal mass."""
    dilution = _positive("dilution_factor", dilution_factor)
    if dilution < 1.0 and abs(dilution - 1.0) > _BOUND_TOLERANCE:
        raise ValueError("dilution_factor %g is below unity" % dilution)
    recovery = _positive("recovery_fraction", recovery_fraction)
    if recovery > 1.0 and abs(recovery - 1.0) > _BOUND_TOLERANCE:
        raise ValueError("recovery_fraction must not exceed unity, got %g"
                         % recovery)
    area = _positive("sampled_area_cm2", sampled_area_cm2)
    return dilution / (recovery * area)


def signal_to_areal_mass(signal, calibration_slope, factor):
    """Convert a signal to an areal mass through the slope and sampling factor."""
    value = _positive("signal", signal, allow_zero=True)
    slope = _positive("calibration_slope", calibration_slope)
    scale = _positive("factor", factor)
    return (value / slope) * scale


def reporting_decision(sample_signal, detection_signal, quantification_signal):
    """Return the reporting decision for a sample reading against both limits."""
    signal = _positive("sample_signal", sample_signal, allow_zero=True)
    lod = _positive("detection_signal", detection_signal)
    loq = _positive("quantification_signal", quantification_signal)
    if loq < lod and abs(loq - lod) > _BOUND_TOLERANCE:
        raise ValueError(
            "quantification limit %g sits below the detection limit %g"
            % (loq, lod)
        )
    if _at_least(signal, loq):
        return QUANTIFIED
    if _at_least(signal, lod):
        return DETECTED_NOT_QUANTIFIED
    return NOT_DETECTED


def combined_relative_uncertainty(components):
    """Combine relative uncertainty components in quadrature.

    components is a mapping of source name to relative standard uncertainty.
    """
    if not isinstance(components, dict) or not components:
        raise ValueError("components must be a non-empty mapping of name to value")
    total = 0.0
    for name in sorted(components):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("uncertainty component name must be a non-empty string")
        value = _positive("component %s" % name, components[name], allow_zero=True)
        if value >= 1.0:
            raise ValueError(
                "relative component %s is %g; a component of one hundred "
                "percent or more is not a relative standard uncertainty"
                % (name, value)
            )
        total += value * value
    return math.sqrt(total)


def expanded_uncertainty(value, relative_uc,
                         coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Return the expanded uncertainty record for a reported value."""
    result = _positive("value", value, allow_zero=True)
    relative = _positive("relative_uc", relative_uc, allow_zero=True)
    k = _positive("coverage_factor", coverage_factor)
    standard = result * relative
    expanded = k * standard
    return {
        "value": result,
        "relative_standard_uncertainty": relative,
        "standard_uncertainty": standard,
        "coverage_factor": k,
        "expanded_uncertainty": expanded,
        "lower": result - expanded,
        "upper": result + expanded,
    }


def assess_detection_limits(spec):
    """Run the full detection-limit and uncertainty assessment.

    spec keys: blank_replicates, calibration_slope, dilution_factor,
    recovery_fraction, sampled_area_cm2, sample_signal, uncertainty_components,
    and optionally coverage_factor, allocation_ug_per_cm2, min_replicates,
    detection_multiplier, quantification_multiplier.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("blank_replicates", "calibration_slope", "dilution_factor",
                "recovery_fraction", "sampled_area_cm2", "sample_signal",
                "uncertainty_components"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    minimum = spec.get("min_replicates", MIN_BLANK_REPLICATES)
    replicates = validate_blank_replicates(spec["blank_replicates"], minimum)
    mean = blank_mean(replicates, minimum)
    sd = blank_standard_deviation(replicates, minimum)
    lod_signal = detection_limit_signal(
        sd, spec.get("detection_multiplier", DETECTION_MULTIPLIER)
    )
    loq_signal = quantification_limit_signal(
        sd, spec.get("quantification_multiplier", QUANTIFICATION_MULTIPLIER)
    )
    factor = sampling_factor(spec["dilution_factor"], spec["recovery_fraction"],
                             spec["sampled_area_cm2"])
    slope = spec["calibration_slope"]
    lod_areal = signal_to_areal_mass(lod_signal, slope, factor)
    loq_areal = signal_to_areal_mass(loq_signal, slope, factor)
    sample_areal = signal_to_areal_mass(spec["sample_signal"], slope, factor)
    decision = reporting_decision(spec["sample_signal"], lod_signal, loq_signal)
    relative = combined_relative_uncertainty(spec["uncertainty_components"])
    interval = expanded_uncertainty(
        sample_areal, relative, spec.get("coverage_factor",
                                         DEFAULT_COVERAGE_FACTOR)
    )
    findings = []
    reported = sample_areal if decision == QUANTIFIED else None
    if decision == DETECTED_NOT_QUANTIFIED:
        findings.append(
            "reading sits between the detection and quantification limits; "
            "report presence and the quantification limit %.4f ug/cm2, not a "
            "mass" % loq_areal
        )
    if decision == NOT_DETECTED:
        findings.append(
            "reading is below the detection limit %.4f ug/cm2; report the "
            "limit, not a mass" % lod_areal
        )
    dominant = max(spec["uncertainty_components"],
                   key=lambda k: spec["uncertainty_components"][k])
    if "allocation_ug_per_cm2" in spec and spec["allocation_ug_per_cm2"] is not None:
        allocation = _positive("allocation_ug_per_cm2",
                               spec["allocation_ug_per_cm2"])
        if interval["lower"] < allocation and interval["upper"] > allocation:
            findings.append(
                "the expanded interval %.4f to %.4f ug/cm2 spans the allocation "
                "%.4f; the result does not decide compliance at this coverage "
                "factor" % (interval["lower"], interval["upper"], allocation)
            )
    return {
        "blank_mean": mean,
        "blank_standard_deviation": sd,
        "detection_limit_signal": lod_signal,
        "quantification_limit_signal": loq_signal,
        "detection_limit_ug_per_cm2": lod_areal,
        "quantification_limit_ug_per_cm2": loq_areal,
        "sample_areal_ug_per_cm2": sample_areal,
        "decision": decision,
        "reported_mass_ug_per_cm2": reported,
        "relative_standard_uncertainty": relative,
        "dominant_component": dominant,
        "interval": interval,
        "findings": findings,
    }
