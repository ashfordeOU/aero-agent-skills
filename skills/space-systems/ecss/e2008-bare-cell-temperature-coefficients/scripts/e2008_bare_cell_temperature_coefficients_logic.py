"""Bare solar cell temperature coefficients on the irradiated qualification subgroup.

Anchor: ECSS-E-ST-20-08C clause 7.5.4. The procedure below is a paraphrase of
the clause intent and reproduces none of its text: the temperature coefficients
of the bare cells are measured on the samples of the qualification subgroup
that have already taken their irradiation, so that the end-of-life behaviour a
generator is predicted at rests on cells in the state they will fly in.

Procedure implemented here
--------------------------
1. Confirm the sample is one the clause allows: a member of the qualification
   subgroup that actually carries its irradiation. A coefficient measured on a
   pristine cell describes a cell that will not exist after a year in orbit.
2. Hold the measurement set to enough distinct temperatures, separated widely
   enough to be separate points, over a span wide enough for a slope to mean
   something. Three readings inside two kelvin produce a number, not a slope.
3. Fit short circuit current, open circuit voltage and maximum power against
   temperature by ordinary least squares, and keep the fit quality alongside
   each slope. A coefficient with no fit quality behind it cannot be argued
   with.
4. Express each slope both absolutely, per kelvin in its own unit, and relative
   to the value the fit puts at reference temperature, because a generator
   model consumes the relative form and a test report records the absolute one.
5. Hold each coefficient to its expected sign. Current rises with temperature
   while voltage and power fall; a slope of the wrong sign is an instrument or
   transcription fault, not a surprising cell.
6. Reconcile the samples measured against the qualification subgroup roster and
   name every member nobody measured.
"""

import math

__all__ = [
    "TOLERANCE",
    "DEFAULT_REFERENCE_TEMPERATURE_C",
    "MIN_TEMPERATURE_POINTS",
    "MIN_POINT_SEPARATION_C",
    "MIN_TEMPERATURE_SPAN_C",
    "MIN_FIT_QUALITY",
    "EXPECTED_SIGNS",
    "least_squares_fit",
    "fit_quality",
    "value_at_temperature",
    "temperature_span_c",
    "distinct_temperature_count",
    "relative_coefficient_per_c",
    "derive_coefficient",
    "validate_sample_eligibility",
    "evaluate_sample_coefficients",
    "assess_bare_cell_temperature_coefficients",
]

# Slopes, intercepts and fit qualities are sums of products of floats, so a set
# that is exactly linear can land a few units in the last place off its own
# ideal. Absorb that representation error here rather than by loosening a limit.
TOLERANCE = 1e-9

# The temperature the coefficients are referred back to.
DEFAULT_REFERENCE_TEMPERATURE_C = 28.0

# Below these the fit is arithmetic rather than measurement.
MIN_TEMPERATURE_POINTS = 3
MIN_POINT_SEPARATION_C = 1.0
MIN_TEMPERATURE_SPAN_C = 30.0
MIN_FIT_QUALITY = 0.98

# Current rises with temperature; voltage and power fall with it.
EXPECTED_SIGNS = {"isc_a": 1, "voc_v": -1, "pmpp_w": -1}


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _mapping(label, value, required_keys=()):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def _identifier(label, value):
    """Return value as a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _flag(label, value):
    """Return value as a validated boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _not_below(value, limit):
    """Return True when value sits at or above limit, edge included."""
    return value > limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TOLERANCE)


def _series(label, values, allow_negative=True):
    """Return a validated non-empty sequence of finite floats."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("%s must be a non-empty sequence" % label)
    return [
        _real("%s entry" % label, entry, allow_zero=True, allow_negative=allow_negative)
        for entry in values
    ]


def least_squares_fit(temperatures_c, values):
    """Return the ordinary least squares (slope, intercept) of values on temperature."""
    xs = _series("temperatures_c", temperatures_c)
    ys = _series("values", values)
    if len(xs) != len(ys):
        raise ValueError(
            "temperatures_c holds %d points and values holds %d; a fit needs pairs"
            % (len(xs), len(ys))
        )
    count = len(xs)
    if count < 2:
        raise ValueError("a slope needs at least two points, got %d" % count)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    variance = sum((x - mean_x) * (x - mean_x) for x in xs)
    if math.isclose(variance, 0.0, rel_tol=0.0, abs_tol=TOLERANCE):
        raise ValueError(
            "every reading sits at the same temperature, so no slope against "
            "temperature exists"
        )
    slope = covariance / variance
    return slope, mean_y - slope * mean_x


def fit_quality(temperatures_c, values, slope, intercept):
    """Return the fraction of the spread in values the straight line accounts for."""
    xs = _series("temperatures_c", temperatures_c)
    ys = _series("values", values)
    if len(xs) != len(ys):
        raise ValueError("temperatures_c and values must hold the same point count")
    gradient = _real("slope", slope, allow_zero=True, allow_negative=True)
    offset = _real("intercept", intercept, allow_zero=True, allow_negative=True)
    mean_y = sum(ys) / len(ys)
    total = sum((y - mean_y) * (y - mean_y) for y in ys)
    residual = sum(
        (y - (gradient * x + offset)) * (y - (gradient * x + offset))
        for x, y in zip(xs, ys)
    )
    if math.isclose(total, 0.0, rel_tol=0.0, abs_tol=TOLERANCE):
        return 1.0 if math.isclose(residual, 0.0, rel_tol=0.0, abs_tol=TOLERANCE) else 0.0
    return 1.0 - residual / total


def value_at_temperature(slope, intercept, temperature_c):
    """Return the fitted value the straight line puts at one temperature."""
    gradient = _real("slope", slope, allow_zero=True, allow_negative=True)
    offset = _real("intercept", intercept, allow_zero=True, allow_negative=True)
    temperature = _real("temperature_c", temperature_c, allow_negative=True)
    return gradient * temperature + offset


def temperature_span_c(temperatures_c):
    """Return the width in kelvin the measurement set covers."""
    xs = _series("temperatures_c", temperatures_c)
    return max(xs) - min(xs)


def distinct_temperature_count(temperatures_c, separation_c=MIN_POINT_SEPARATION_C):
    """Return how many of the readings sit far enough apart to be separate points."""
    xs = sorted(_series("temperatures_c", temperatures_c))
    gap = _real("separation_c", separation_c)
    kept = [xs[0]]
    for value in xs[1:]:
        if value - kept[-1] > gap or math.isclose(
            value - kept[-1], gap, rel_tol=0.0, abs_tol=TOLERANCE
        ):
            kept.append(value)
    return len(kept)


def relative_coefficient_per_c(slope, reference_value):
    """Return the slope as a fraction of the value at reference temperature."""
    gradient = _real("slope", slope, allow_zero=True, allow_negative=True)
    reference = _real("reference_value", reference_value, allow_negative=True)
    if math.isclose(reference, 0.0, rel_tol=0.0, abs_tol=TOLERANCE):
        raise ValueError(
            "the fitted value at reference temperature is zero, so a relative "
            "coefficient against it is not defined"
        )
    return gradient / reference


def derive_coefficient(
    temperatures_c,
    values,
    reference_temperature_c=DEFAULT_REFERENCE_TEMPERATURE_C,
):
    """Return the absolute and relative coefficient of one quantity with its fit quality."""
    slope, intercept = least_squares_fit(temperatures_c, values)
    quality = fit_quality(temperatures_c, values, slope, intercept)
    reference = value_at_temperature(slope, intercept, reference_temperature_c)
    return {
        "slope_per_c": slope,
        "intercept": intercept,
        "fit_quality": quality,
        "value_at_reference": reference,
        "relative_per_c": relative_coefficient_per_c(slope, reference),
    }


def validate_sample_eligibility(sample, subgroup_ids=()):
    """Return (sample_id, findings) for one candidate coefficient sample."""
    data = _mapping("sample", sample, ("id", "irradiated", "points"))
    sample_id = _identifier("sample['id']", data["id"])
    irradiated = _flag("sample['irradiated']", data["irradiated"])
    if not isinstance(subgroup_ids, (list, tuple, set, frozenset)):
        raise ValueError("subgroup_ids must be a sequence or set")
    roster = {_identifier("subgroup_ids entry", entry) for entry in subgroup_ids}
    findings = []
    if not irradiated:
        findings.append(
            "sample %s never took its irradiation, so its coefficients describe "
            "a cell state the mission leaves behind" % sample_id
        )
    if roster and sample_id not in roster:
        findings.append(
            "sample %s is not a member of the qualification subgroup the clause "
            "draws coefficient samples from" % sample_id
        )
    return sample_id, findings


def evaluate_sample_coefficients(sample, limits=None, subgroup_ids=()):
    """Derive and check every coefficient of one irradiated qualification sample."""
    sample_id, findings = validate_sample_eligibility(sample, subgroup_ids)
    points = sample["points"]
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("sample['points'] must be a non-empty sequence of readings")
    bounds = _mapping("limits", limits if limits is not None else {})
    min_points = bounds.get("min_points", MIN_TEMPERATURE_POINTS)
    if not isinstance(min_points, int) or isinstance(min_points, bool) or min_points < 2:
        raise ValueError("limits['min_points'] must be an integer of at least 2")
    min_span = _real("limits['min_span_c']", bounds.get("min_span_c", MIN_TEMPERATURE_SPAN_C))
    min_quality = _real(
        "limits['min_fit_quality']",
        bounds.get("min_fit_quality", MIN_FIT_QUALITY),
        allow_zero=True,
    )
    reference_t = _real(
        "limits['reference_temperature_c']",
        bounds.get("reference_temperature_c", DEFAULT_REFERENCE_TEMPERATURE_C),
        allow_negative=True,
    )

    temperatures = []
    columns = {"isc_a": [], "voc_v": [], "pmpp_w": []}
    for point in points:
        record = _mapping(
            "sample['points'] entry", point, ("temperature_c", "isc_a", "voc_v", "pmpp_w")
        )
        temperatures.append(
            _real("point['temperature_c']", record["temperature_c"], allow_negative=True)
        )
        for key in columns:
            columns[key].append(_real("point['%s']" % key, record[key]))

    span = temperature_span_c(temperatures)
    separate = distinct_temperature_count(temperatures)
    if separate < min_points:
        findings.append(
            "sample %s offers %d separate temperatures, fewer than the %d a "
            "coefficient fit rests on" % (sample_id, separate, min_points)
        )
    if not _not_below(span, min_span):
        findings.append(
            "sample %s spans %.4g K, narrower than the %.4g K a slope needs to "
            "mean anything" % (sample_id, span, min_span)
        )

    coefficients = {}
    for key, series in columns.items():
        coefficient = derive_coefficient(temperatures, series, reference_t)
        expected = EXPECTED_SIGNS[key]
        actual_sign = 0
        if coefficient["slope_per_c"] > TOLERANCE:
            actual_sign = 1
        elif coefficient["slope_per_c"] < -TOLERANCE:
            actual_sign = -1
        coefficient["expected_sign"] = expected
        coefficient["sign_as_expected"] = actual_sign == expected
        if not coefficient["sign_as_expected"]:
            findings.append(
                "sample %s returns a %s coefficient of %.6g per K, against the "
                "expected sign %+d" % (sample_id, key, coefficient["slope_per_c"], expected)
            )
        if not _not_below(coefficient["fit_quality"], min_quality):
            findings.append(
                "sample %s fits %s to %.6f of its own spread, below the %.6f a "
                "coefficient is reported at" % (sample_id, key, coefficient["fit_quality"], min_quality)
            )
        coefficients[key] = coefficient

    return {
        "id": sample_id,
        "temperature_span_c": span,
        "separate_temperatures": separate,
        "point_count": len(temperatures),
        "coefficients": coefficients,
        "conforms": not findings,
        "findings": findings,
    }


def assess_bare_cell_temperature_coefficients(spec):
    """Run the full clause 7.5.4 temperature coefficient assessment.

    spec keys: samples (a non-empty sequence of irradiated subgroup samples),
    optional subgroup_ids naming the qualification subgroup roster, and optional
    limits (min_points, min_span_c, min_fit_quality, reference_temperature_c).
    """
    data = _mapping("spec", spec, ("samples",))
    samples = data["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("spec['samples'] must be a non-empty sequence of samples")
    subgroup = data.get("subgroup_ids", ())
    if not isinstance(subgroup, (list, tuple, set, frozenset)):
        raise ValueError("spec['subgroup_ids'] must be a sequence or set")
    roster = sorted({_identifier("subgroup_ids entry", entry) for entry in subgroup})
    limits = data.get("limits")
    records = []
    findings = []
    seen = set()
    for sample in samples:
        record = evaluate_sample_coefficients(sample, limits, subgroup)
        if record["id"] in seen:
            raise ValueError(
                "sample id '%s' appears twice in spec['samples']" % record["id"]
            )
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["findings"])
    unmeasured = sorted(set(roster) - seen)
    for sample_id in unmeasured:
        findings.append(
            "subgroup member %s carries no temperature coefficient measurement"
            % sample_id
        )
    conforming = sum(1 for record in records if record["conforms"])
    return {
        "sample_records": records,
        "samples_measured": len(records),
        "samples_conforming": conforming,
        "samples_rejected": len(records) - conforming,
        "subgroup_roster": roster,
        "unmeasured_subgroup_ids": unmeasured,
        "findings": findings,
        "valid": not findings,
    }
