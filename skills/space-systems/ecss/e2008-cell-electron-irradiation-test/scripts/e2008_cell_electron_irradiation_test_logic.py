"""Bare cell electron irradiation: how fluence takes electrical output away.

Anchor: ECSS-E-ST-20-08C clause 7.5.13 (accelerated life exposure of a bare
solar cell to electrons, measuring how the accumulated electron fluence
degrades its electrical output). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the exposure is a staircase: every planned fluence point is positive
   and strictly above the one before it, and an unirradiated reference
   measurement exists, because every later number is a ratio against it.
2. Check each electrical measurement was taken under the same temperature and
   illumination as that reference. A cell measured warmer reads a lower voltage
   for reasons the beam had nothing to do with, and the ratio then mixes two
   different measurements instead of showing damage.
3. Turn each step's short-circuit current, open-circuit voltage and maximum
   power into remaining factors against the unirradiated reference.
4. Refuse a remaining factor that climbs as fluence rises, or that sits above
   the unirradiated value: electron damage does not heal between steps, so a
   rise is an instrument or a contact, not a cell that recovered.
5. Fit each parameter's remaining factor against the natural logarithm of
   fluence, report the retention lost per decade of fluence, and flag any step
   that departs from its own fit by more than the allowed residual.
6. Project the retention at the mission end-of-life fluence from the fit and
   compare it with the retention the power budget requires.
7. Report the factors, the fit, the per-decade loss, the projection, every
   finding and the run verdict; the run is conformant only with no finding.
"""

import math

__all__ = [
    "FACTOR_TOLERANCE",
    "PARAMETERS",
    "NOISE_ALLOWANCE",
    "TEMPERATURE_TOLERANCE_C",
    "IRRADIANCE_TOLERANCE_W_M2",
    "MAX_FIT_RESIDUAL",
    "validate_fluence_steps",
    "remaining_factor",
    "condition_findings",
    "remaining_series",
    "monotonicity_findings",
    "fit_log_degradation",
    "predict_remaining",
    "retention_lost_per_decade",
    "residual_findings",
    "assess_cell_electron_irradiation",
]

# A factor or a condition sitting exactly on a declared bound is conformant;
# the comparison absorbs representation error and the bound never moves.
FACTOR_TOLERANCE = 1e-9

# The three electrical outputs the exposure is read on.
PARAMETERS = (
    "short-circuit-current",
    "open-circuit-voltage",
    "maximum-power",
)

# A remaining factor may sit this far above its predecessor, or above unity,
# before the rise is the measurement rather than the cell.
NOISE_ALLOWANCE = 0.002

# A measurement taken further than this from the reference conditions is not
# comparable with it.
TEMPERATURE_TOLERANCE_C = 2.0
IRRADIANCE_TOLERANCE_W_M2 = 10.0

# A step this far off its own logarithmic fit is an outlier, not a point on
# the degradation curve.
MAX_FIT_RESIDUAL = 0.02


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def _parameter(value):
    """Return a validated electrical parameter name."""
    name = _name(value, "parameter")
    if name not in PARAMETERS:
        raise ValueError(
            "parameter must be one of %s, got '%s'"
            % (", ".join(PARAMETERS), name)
        )
    return name


def _values(mapping, label):
    """Return a validated mapping of every parameter to a positive reading."""
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping of parameter to reading" % label)
    result = {}
    for key in PARAMETERS:
        if key not in mapping:
            raise ValueError("%s is missing the '%s' reading" % (label, key))
        result[key] = _positive(mapping[key], "%s '%s'" % (label, key))
    for key in mapping:
        _parameter(key)
    return result


def validate_fluence_steps(fluences):
    """Return the validated, strictly rising electron fluence staircase."""
    if not isinstance(fluences, (list, tuple)) or len(fluences) < 2:
        raise ValueError("at least two fluence steps are needed for a fit")
    steps = [_positive(value, "fluence_e_per_cm2") for value in fluences]
    for earlier, later in zip(steps, steps[1:]):
        if later <= earlier:
            raise ValueError(
                "fluence steps must strictly rise, got %g after %g"
                % (later, earlier)
            )
    return steps


def remaining_factor(measured, reference):
    """Return the fraction of an unirradiated reading a step still holds."""
    value = _positive(measured, "measured")
    base = _positive(reference, "reference")
    return value / base


def condition_findings(measurement, reference,
                       temperature_tolerance_c=TEMPERATURE_TOLERANCE_C,
                       irradiance_tolerance_w_m2=IRRADIANCE_TOLERANCE_W_M2):
    """Return findings where a step was not measured as the reference was."""
    for label, item in (("measurement", measurement), ("reference", reference)):
        if not isinstance(item, dict):
            raise ValueError("%s must be a mapping" % label)
        for key in ("label", "temperature_c", "irradiance_w_m2"):
            if key not in item:
                raise ValueError("%s missing key '%s'" % (label, key))
    temp_tol = _positive(temperature_tolerance_c, "temperature_tolerance_c")
    irr_tol = _positive(irradiance_tolerance_w_m2, "irradiance_tolerance_w_m2")
    tag = _name(measurement["label"], "label")
    temperature = _real(measurement["temperature_c"], "temperature_c")
    base_temperature = _real(reference["temperature_c"], "temperature_c")
    irradiance = _positive(measurement["irradiance_w_m2"], "irradiance_w_m2")
    base_irradiance = _positive(reference["irradiance_w_m2"], "irradiance_w_m2")
    findings = []
    if abs(temperature - base_temperature) > temp_tol + FACTOR_TOLERANCE:
        findings.append(
            "step '%s' was measured at %g C against a reference at %g C, "
            "outside the %g C the comparison allows"
            % (tag, temperature, base_temperature, temp_tol)
        )
    if abs(irradiance - base_irradiance) > irr_tol + FACTOR_TOLERANCE:
        findings.append(
            "step '%s' was measured at %g W/m2 against a reference at %g W/m2, "
            "outside the %g W/m2 the comparison allows"
            % (tag, irradiance, base_irradiance, irr_tol)
        )
    return findings


def remaining_series(reference_values, step_values):
    """Return each parameter's remaining factor across the fluence steps."""
    base = _values(reference_values, "reference_values")
    if not isinstance(step_values, (list, tuple)) or not step_values:
        raise ValueError("step_values must be a non-empty sequence of readings")
    series = {key: [] for key in PARAMETERS}
    for index, reading in enumerate(step_values):
        values = _values(reading, "step %d readings" % (index + 1))
        for key in PARAMETERS:
            series[key].append(remaining_factor(values[key], base[key]))
    return series


def monotonicity_findings(parameter, fluences, factors,
                          noise_allowance=NOISE_ALLOWANCE):
    """Return findings where a remaining factor rose instead of falling."""
    name = _parameter(parameter)
    steps = validate_fluence_steps(fluences)
    if not isinstance(factors, (list, tuple)) or len(factors) != len(steps):
        raise ValueError("one remaining factor is needed per fluence step")
    allowance = _positive(noise_allowance, "noise_allowance")
    values = [_positive(value, "remaining factor") for value in factors]
    findings = []
    for index, value in enumerate(values):
        if value > 1.0 + allowance + FACTOR_TOLERANCE:
            findings.append(
                "%s reads %.4f of its unirradiated value at %.3g e/cm2, above "
                "the cell's own starting point" % (name, value, steps[index])
            )
    for index in range(1, len(values)):
        rise = values[index] - values[index - 1]
        if rise > allowance + FACTOR_TOLERANCE:
            findings.append(
                "%s recovered from %.4f to %.4f between %.3g and %.3g e/cm2, "
                "which electron damage does not do"
                % (name, values[index - 1], values[index],
                   steps[index - 1], steps[index])
            )
    return findings


def fit_log_degradation(fluences, factors):
    """Return the least-squares fit of remaining factor against ln(fluence)."""
    steps = validate_fluence_steps(fluences)
    if not isinstance(factors, (list, tuple)) or len(factors) != len(steps):
        raise ValueError("one remaining factor is needed per fluence step")
    values = [_positive(value, "remaining factor") for value in factors]
    logs = [math.log(step) for step in steps]
    count = len(logs)
    mean_log = sum(logs) / count
    mean_value = sum(values) / count
    covariance = sum(
        (log - mean_log) * (value - mean_value)
        for log, value in zip(logs, values)
    )
    spread = sum((log - mean_log) ** 2 for log in logs)
    if spread <= 0.0:
        raise ValueError("the fluence steps carry no spread to fit against")
    slope = covariance / spread
    intercept = mean_value - slope * mean_log
    return {
        "slope": slope,
        "intercept": intercept,
        "point_count": count,
    }


def predict_remaining(fit, fluence):
    """Return the remaining factor the fit puts at a given fluence."""
    if not isinstance(fit, dict):
        raise ValueError("fit must be a mapping with slope and intercept")
    for key in ("slope", "intercept"):
        if key not in fit:
            raise ValueError("fit missing key '%s'" % key)
    slope = _real(fit["slope"], "slope")
    intercept = _real(fit["intercept"], "intercept")
    point = _positive(fluence, "fluence_e_per_cm2")
    return intercept + slope * math.log(point)


def retention_lost_per_decade(fit):
    """Return how much retention a tenfold rise in fluence costs."""
    if not isinstance(fit, dict) or "slope" not in fit:
        raise ValueError("fit must be a mapping with a slope")
    return -_real(fit["slope"], "slope") * math.log(10.0)


def residual_findings(parameter, fluences, factors, fit,
                      max_residual=MAX_FIT_RESIDUAL):
    """Return findings where a measured step sits off its own fit."""
    name = _parameter(parameter)
    steps = validate_fluence_steps(fluences)
    if not isinstance(factors, (list, tuple)) or len(factors) != len(steps):
        raise ValueError("one remaining factor is needed per fluence step")
    limit = _positive(max_residual, "max_residual")
    findings = []
    for step, value in zip(steps, factors):
        predicted = predict_remaining(fit, step)
        measured = _positive(value, "remaining factor")
        if abs(measured - predicted) > limit + FACTOR_TOLERANCE:
            findings.append(
                "%s reads %.4f at %.3g e/cm2 where its fit puts %.4f, off the "
                "curve by more than %.4f" % (name, measured, step, predicted,
                                             limit)
            )
    return findings


def assess_cell_electron_irradiation(spec):
    """Run the full clause 7.5.13 bare-cell electron irradiation assessment.

    spec keys: reference_measurement (label, temperature_c, irradiance_w_m2,
    values), steps (label, fluence_e_per_cm2, temperature_c, irradiance_w_m2,
    values), eol_fluence_e_per_cm2, required_retention; optional
    noise_allowance, max_residual, temperature_tolerance_c,
    irradiance_tolerance_w_m2.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "reference_measurement",
        "steps",
        "eol_fluence_e_per_cm2",
        "required_retention",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    steps = spec["steps"]
    if not isinstance(steps, (list, tuple)) or len(steps) < 2:
        raise ValueError("steps must carry at least two fluence points")
    reference = spec["reference_measurement"]
    if not isinstance(reference, dict) or "values" not in reference:
        raise ValueError("reference_measurement must carry its readings")
    retention = spec["required_retention"]
    if not isinstance(retention, dict) or not retention:
        raise ValueError("required_retention must name at least one parameter")
    for key in retention:
        _parameter(key)

    fluences = []
    readings = []
    findings = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("each step must be a mapping")
        for key in ("label", "fluence_e_per_cm2", "values"):
            if key not in step:
                raise ValueError("step %d missing key '%s'" % (index + 1, key))
        fluences.append(step["fluence_e_per_cm2"])
        readings.append(step["values"])
        findings.extend(
            condition_findings(
                step,
                reference,
                spec.get("temperature_tolerance_c", TEMPERATURE_TOLERANCE_C),
                spec.get("irradiance_tolerance_w_m2",
                         IRRADIANCE_TOLERANCE_W_M2),
            )
        )
    fluences = validate_fluence_steps(fluences)
    series = remaining_series(reference["values"], readings)
    eol = _positive(spec["eol_fluence_e_per_cm2"], "eol_fluence_e_per_cm2")
    if eol < fluences[-1] - FACTOR_TOLERANCE:
        findings.append(
            "the run stopped at %.3g e/cm2, above the %.3g e/cm2 end-of-life "
            "point, so the projection is an extrapolation backwards"
            % (fluences[-1], eol)
        )

    report = {}
    for parameter in PARAMETERS:
        factors = series[parameter]
        fit = fit_log_degradation(fluences, factors)
        projected = predict_remaining(fit, eol)
        parameter_findings = monotonicity_findings(
            parameter, fluences, factors,
            spec.get("noise_allowance", NOISE_ALLOWANCE),
        )
        parameter_findings.extend(
            residual_findings(
                parameter, fluences, factors, fit,
                spec.get("max_residual", MAX_FIT_RESIDUAL),
            )
        )
        if parameter in retention:
            floor = _positive(
                retention[parameter], "required_retention '%s'" % parameter
            )
            if projected < floor - FACTOR_TOLERANCE:
                parameter_findings.append(
                    "%s is projected at %.4f of its start at end of life, "
                    "under the %.4f the budget asks for"
                    % (parameter, projected, floor)
                )
        report[parameter] = {
            "remaining_factors": factors,
            "fit": fit,
            "retention_lost_per_decade": retention_lost_per_decade(fit),
            "projected_remaining": projected,
            "findings": parameter_findings,
        }
        findings.extend(parameter_findings)
    return {
        "fluences_e_per_cm2": fluences,
        "parameters": report,
        "step_count": len(fluences),
        "eol_fluence_e_per_cm2": eol,
        "findings": findings,
        "run_conformant": not findings,
    }
