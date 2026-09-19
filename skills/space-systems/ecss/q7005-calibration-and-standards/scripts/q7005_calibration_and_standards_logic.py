"""Calibration of an infrared contamination method against prepared standards.

Anchor: ECSS-Q-ST-70-05C, quantification. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the standards: at least three distinct areal-mass levels, each
   with a net absorbance measured under the sample method.
2. Fit net absorbance against areal mass by least squares, with a free
   intercept or forced through the origin.
3. Refuse a non-positive slope; grade the fit on its coefficient of
   determination and its worst relative residual.
4. Record the working range the standards bracket and invert a sample
   absorbance only inside it.
5. Put an independent verification standard back through the curve and grade
   its recovery against the acceptance band.
"""

import math

__all__ = [
    "MAX_RELATIVE_RESIDUAL",
    "MIN_R_SQUARED",
    "MIN_STANDARDS",
    "RECOVERY_BAND",
    "assess_calibration",
    "build_calibration",
    "coefficient_of_determination",
    "invert_calibration",
    "least_squares_fit",
    "predicted_absorbance",
    "residuals",
    "validate_standards",
    "verify_with_standard",
    "working_range",
]

# Three distinct levels is the floor: two points leave no residual to grade
# linearity with.
MIN_STANDARDS = 3

# The line has to explain essentially all of the spread of the standards.
MIN_R_SQUARED = 0.995

# No single level may be served worse than this, relative to its own value.
MAX_RELATIVE_RESIDUAL = 0.10

# A verification standard has to recover inside this band of its prepared
# value for the curve to be accepted.
RECOVERY_BAND = (0.90, 1.10)

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


def _real(label, value):
    """Return value as a finite float of any sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _at_most(value, bound):
    """True when value is below bound or lands on it within tolerance."""
    return value < bound or abs(value - bound) <= _BOUND_TOLERANCE


def _at_least(value, bound):
    """True when value is above bound or lands on it within tolerance."""
    return value > bound or abs(value - bound) <= _BOUND_TOLERANCE


def validate_standards(standards):
    """Return the validated list of (areal_mass, net_absorbance) standards."""
    if not isinstance(standards, (list, tuple)):
        raise ValueError("standards must be a sequence of (mass, absorbance) pairs")
    points = []
    for i, item in enumerate(standards):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("standards[%d] must be a (mass, absorbance) pair" % i)
        mass = _positive("standards[%d] areal mass" % i, item[0], allow_zero=True)
        absorbance = _positive("standards[%d] absorbance" % i, item[1],
                               allow_zero=True)
        points.append((mass, absorbance))
    distinct = set()
    for mass, _ in points:
        distinct.add(round(mass, 12))
    if len(distinct) < MIN_STANDARDS:
        raise ValueError(
            "calibration needs at least %d distinct areal-mass levels, got %d"
            % (MIN_STANDARDS, len(distinct))
        )
    return sorted(points)


def least_squares_fit(points, through_origin=False):
    """Return (slope, intercept) of the least-squares line through the points."""
    if not isinstance(through_origin, bool):
        raise ValueError("through_origin must be a boolean")
    data = validate_standards(points)
    n = float(len(data))
    if through_origin:
        sxx = sum(x * x for x, _ in data)
        if sxx == 0.0:
            raise ValueError("all standards sit at zero mass; no slope is defined")
        slope = sum(x * y for x, y in data) / sxx
        return (slope, 0.0)
    mean_x = sum(x for x, _ in data) / n
    mean_y = sum(y for _, y in data) / n
    sxx = sum((x - mean_x) ** 2 for x, _ in data)
    if sxx == 0.0:
        raise ValueError("all standards sit at one mass level; no slope is defined")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in data)
    slope = sxy / sxx
    return (slope, mean_y - slope * mean_x)


def predicted_absorbance(slope, intercept, areal_mass):
    """Return the absorbance the fitted line predicts at an areal mass."""
    return _real("slope", slope) * _positive("areal_mass", areal_mass,
                                             allow_zero=True) + _real(
        "intercept", intercept
    )


def residuals(points, slope, intercept):
    """Return the list of (mass, observed, predicted, residual) records."""
    data = validate_standards(points)
    out = []
    for mass, observed in data:
        fitted = predicted_absorbance(slope, intercept, mass)
        out.append({
            "areal_mass": mass,
            "observed_absorbance": observed,
            "predicted_absorbance": fitted,
            "residual": observed - fitted,
        })
    return out


def coefficient_of_determination(points, slope, intercept):
    """Return the share of the observed spread the fitted line explains."""
    data = validate_standards(points)
    mean_y = sum(y for _, y in data) / float(len(data))
    ss_tot = sum((y - mean_y) ** 2 for _, y in data)
    # A flat response has a spread that is only representation error, so the
    # test is relative to the size of the readings, never an exact zero.
    scale = max(abs(y) for _, y in data)
    flat_floor = (1.0e-12 * max(scale, 1.0e-12)) ** 2 * float(len(data))
    if ss_tot <= flat_floor:
        raise ValueError(
            "every standard gave the same absorbance; the response is flat and "
            "no fit can be graded"
        )
    ss_res = sum(
        (y - predicted_absorbance(slope, intercept, x)) ** 2 for x, y in data
    )
    return 1.0 - ss_res / ss_tot


def working_range(points, slope, intercept):
    """Return the areal-mass and absorbance interval the standards bracket."""
    data = validate_standards(points)
    masses = [x for x, _ in data]
    lo_mass = min(masses)
    hi_mass = max(masses)
    return {
        "min_areal_mass": lo_mass,
        "max_areal_mass": hi_mass,
        "min_absorbance": predicted_absorbance(slope, intercept, lo_mass),
        "max_absorbance": predicted_absorbance(slope, intercept, hi_mass),
    }


def build_calibration(standards, through_origin=False,
                      min_r_squared=MIN_R_SQUARED,
                      max_relative_residual=MAX_RELATIVE_RESIDUAL):
    """Return the graded calibration record for a set of standards."""
    threshold = _positive("min_r_squared", min_r_squared)
    residual_limit = _positive("max_relative_residual", max_relative_residual)
    data = validate_standards(standards)
    slope, intercept = least_squares_fit(data, through_origin)
    if slope <= 0.0:
        raise ValueError(
            "fitted slope %g is not positive; the standards, the baseline or "
            "the band choice is wrong" % slope
        )
    r_squared = coefficient_of_determination(data, slope, intercept)
    records = residuals(data, slope, intercept)
    worst = 0.0
    worst_level = None
    for record in records:
        if record["observed_absorbance"] == 0.0:
            continue
        relative = abs(record["residual"]) / record["observed_absorbance"]
        if relative > worst:
            worst = relative
            worst_level = record["areal_mass"]
    linear = _at_least(r_squared, threshold) and _at_most(worst, residual_limit)
    return {
        "slope": slope,
        "intercept": intercept,
        "through_origin": bool(through_origin),
        "r_squared": r_squared,
        "residuals": records,
        "worst_relative_residual": worst,
        "worst_level": worst_level,
        "linear": linear,
        "range": working_range(data, slope, intercept),
        "n_levels": len(data),
    }


def invert_calibration(calibration, net_absorbance):
    """Return the areal mass a net absorbance implies, inside the working range."""
    if not isinstance(calibration, dict) or "slope" not in calibration:
        raise ValueError("calibration must be a record carrying 'slope'")
    absorbance = _positive("net_absorbance", net_absorbance, allow_zero=True)
    bounds = calibration["range"]
    if not _at_least(absorbance, bounds["min_absorbance"]):
        raise ValueError(
            "absorbance %g is below the lowest standard's %g; the calibration "
            "does not bracket it" % (absorbance, bounds["min_absorbance"])
        )
    if not _at_most(absorbance, bounds["max_absorbance"]):
        raise ValueError(
            "absorbance %g is above the top standard's %g; the calibration "
            "does not bracket it" % (absorbance, bounds["max_absorbance"])
        )
    return (absorbance - calibration["intercept"]) / calibration["slope"]


def verify_with_standard(calibration, prepared_areal_mass, measured_absorbance,
                         band=RECOVERY_BAND):
    """Put a verification standard back through the curve and grade its recovery."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("band must be a (low, high) pair")
    low = _positive("band low", band[0])
    high = _positive("band high", band[1])
    if low >= high:
        raise ValueError("band low %g must be below band high %g" % (low, high))
    prepared = _positive("prepared_areal_mass", prepared_areal_mass)
    recovered = invert_calibration(calibration, measured_absorbance)
    recovery = recovered / prepared
    within = _at_least(recovery, low) and _at_most(recovery, high)
    return {
        "prepared_areal_mass": prepared,
        "recovered_areal_mass": recovered,
        "recovery_fraction": recovery,
        "within_band": within,
        "band": (low, high),
    }


def assess_calibration(spec):
    """Run the full calibration assessment.

    spec keys: standards, optionally through_origin, min_r_squared,
    max_relative_residual, verification (a (prepared_mass, absorbance) pair)
    and recovery_band.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "standards" not in spec:
        raise ValueError("spec missing required key 'standards'")
    calibration = build_calibration(
        spec["standards"],
        spec.get("through_origin", False),
        spec.get("min_r_squared", MIN_R_SQUARED),
        spec.get("max_relative_residual", MAX_RELATIVE_RESIDUAL),
    )
    findings = []
    if not calibration["linear"]:
        findings.append(
            "fit is not acceptable: coefficient of determination %.6f and worst "
            "relative residual %.4f at the %.4f level"
            % (calibration["r_squared"], calibration["worst_relative_residual"],
               calibration["worst_level"] if calibration["worst_level"] is not None
               else 0.0)
        )
    if calibration["through_origin"]:
        findings.append(
            "the fit was forced through the origin; confirm the blank "
            "correction justifies suppressing the intercept"
        )
    verification = None
    if "verification" in spec and spec["verification"] is not None:
        pair = spec["verification"]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("verification must be a (mass, absorbance) pair")
        verification = verify_with_standard(
            calibration, pair[0], pair[1],
            spec.get("recovery_band", RECOVERY_BAND),
        )
        if not verification["within_band"]:
            findings.append(
                "verification standard recovered %.1f%% of its prepared value, "
                "outside the %.0f%%-%.0f%% band; the curve is not verified"
                % (100.0 * verification["recovery_fraction"],
                   100.0 * verification["band"][0],
                   100.0 * verification["band"][1])
            )
    else:
        findings.append(
            "no independent verification standard was run; the curve has not "
            "been tested against a value it was not fitted to"
        )
    return {
        "calibration": calibration,
        "verification": verification,
        "findings": findings,
        "usable": not findings,
    }
