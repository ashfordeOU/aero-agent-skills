#!/usr/bin/env python3
"""Junction model parameters extracted from a multi-bias capacitance sweep.

Anchor: ECSS-E-ST-20-08C clause 11.1.4.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A single capacitance reading at one bias point is a number, not a model.
The clause asks for the model of the cell junction to be determined from
capacitance measured at several different bias voltages, because it is
the way the capacitance moves with bias that carries the parameters: the
depletion width tracks the bias, so the slope of the swept quantity is
what holds the built-in voltage, the doping of the lighter-doped side
and the grading of the junction.

Two model forms are supported.

    mott-schottky-abrupt   1/C^2 falls linearly with bias. The line's
                           voltage intercept is the built-in voltage and
                           its slope carries the doping concentration
                           once the junction area and permittivity are
                           known.

    power-law-graded       C = C0 / (1 - V / Vbi) ** m. A straight line
                           in log capacitance against log depletion drive
                           returns the grading coefficient m, one half
                           for an abrupt junction and about one third for
                           a linearly graded one.

Both fits are only as good as the sweep underneath them. Too few points,
too narrow a bias span, or points pushed far enough forward that
diffusion capacitance joins the depletion term, and the line still fits
-- it simply fits the wrong physics. Those are the gates this module
applies before it will report a determined model.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MOTT_SCHOTTKY_ABRUPT = "mott-schottky-abrupt"
POWER_LAW_GRADED = "power-law-graded"

SUPPORTED_MODELS = (MOTT_SCHOTTKY_ABRUPT, POWER_LAW_GRADED)

ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

MIN_BIAS_POINTS = 5
MIN_BIAS_SPAN_V = 0.5
MIN_FIT_QUALITY = 0.98
MAX_FORWARD_BIAS_FRACTION = 0.3
MIN_GRADING_COEFFICIENT = 0.2
MAX_GRADING_COEFFICIENT = 0.6
MIN_BUILT_IN_VOLTAGE_V = 0.3
MAX_BUILT_IN_VOLTAGE_V = 3.0

MODEL_DETERMINED = "junction-model-determined"
MODEL_NOT_DETERMINED = "junction-model-not-determined"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coefficient of determination or a bias span reached by summation
    can land a few units in the last place either side of a written
    limit. The limit is never relaxed; only the comparison tolerates the
    representation error, which is why no caller uses a bare >= on a
    derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_bias_sweep(readings):
    """Reduce a bias sweep to sorted, distinct, physically usable points.

    Each reading is a bias voltage in volts paired with the capacitance
    in farads read at that bias. Reverse bias is negative. A repeated
    bias point carries no new information about the slope, so a duplicate
    is refused rather than averaged silently.
    """
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError(
            "bias sweep must be a non-empty sequence of readings, got %r" % (readings,)
        )
    points = []
    seen = set()
    for index, reading in enumerate(readings):
        if isinstance(reading, dict):
            bias = reading.get("bias_voltage_v")
            capacitance = reading.get("capacitance_f")
        elif isinstance(reading, (list, tuple)) and len(reading) == 2:
            bias, capacitance = reading
        else:
            raise ValueError(
                "reading %d must be a mapping or a two-element pair, got %r"
                % (index, reading)
            )
        bias_v = _require_number("reading %d bias_voltage_v" % index, bias)
        capacitance_f = _require_positive(
            "reading %d capacitance_f" % index, capacitance
        )
        key = repr(bias_v)
        if key in seen:
            raise ValueError(
                "bias voltage %g appears more than once in the sweep" % bias_v
            )
        seen.add(key)
        points.append((bias_v, capacitance_f))
    points.sort(key=lambda item: item[0])
    return tuple(points)


def bias_span_v(readings):
    """Voltage the sweep actually covers, low point to high point."""
    points = validate_bias_sweep(readings)
    return points[-1][0] - points[0][0]


def distinct_bias_count(readings):
    """How many separate bias points the sweep offers the fit."""
    return len(validate_bias_sweep(readings))


def inverse_square_capacitance(capacitance_f):
    """The Mott-Schottky ordinate, one over capacitance squared."""
    value = _require_positive("capacitance_f", capacitance_f)
    return 1.0 / (value * value)


def least_squares_line(xs, ys):
    """Ordinary least squares line through paired samples.

    Returns the slope, the intercept and the coefficient of
    determination. A sweep whose abscissa never moves has no slope and
    is refused rather than returned as a vertical line.
    """
    if not isinstance(xs, (list, tuple)) or not isinstance(ys, (list, tuple)):
        raise ValueError("least squares inputs must be sequences")
    if len(xs) != len(ys):
        raise ValueError(
            "abscissa and ordinate must be the same length, got %d and %d"
            % (len(xs), len(ys))
        )
    count = len(xs)
    if count < 2:
        raise ValueError("a line needs at least two samples, got %d" % count)
    x_values = [_require_number("abscissa sample", value) for value in xs]
    y_values = [_require_number("ordinate sample", value) for value in ys]
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    sxx = sum((value - mean_x) ** 2 for value in x_values)
    if sxx <= 0.0:
        raise ValueError("abscissa does not vary; the sweep holds one bias point")
    sxy = sum(
        (x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(count)
    )
    syy = sum((value - mean_y) ** 2 for value in y_values)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    if syy <= 0.0:
        r_squared = 1.0
    else:
        r_squared = (sxy * sxy) / (sxx * syy)
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "sample_count": count,
    }


def mott_schottky_fit(readings):
    """Straight-line fit of one over capacitance squared against bias.

    The voltage at which the fitted line reaches zero is the built-in
    voltage; the magnitude of the slope carries the doping once the
    junction area and the permittivity are supplied.
    """
    points = validate_bias_sweep(readings)
    if len(points) < 2:
        raise ValueError("a Mott-Schottky line needs at least two bias points")
    xs = [bias for bias, _ in points]
    ys = [inverse_square_capacitance(capacitance) for _, capacitance in points]
    fit = least_squares_line(xs, ys)
    slope = fit["slope"]
    if slope >= 0.0:
        raise ValueError(
            "one over capacitance squared must fall with forward bias; "
            "fitted slope %g has the wrong sign for a depletion junction" % slope
        )
    built_in_voltage_v = -fit["intercept"] / slope
    return {
        "slope_per_volt": slope,
        "intercept": fit["intercept"],
        "built_in_voltage_v": built_in_voltage_v,
        "r_squared": fit["r_squared"],
        "sample_count": fit["sample_count"],
    }


def doping_concentration_per_m3(slope_per_volt, junction_area_m2, relative_permittivity):
    """Doping of the lighter-doped side implied by the fitted slope."""
    slope = _require_number("slope_per_volt", slope_per_volt)
    if slope == 0.0:
        raise ValueError("a flat Mott-Schottky line carries no doping information")
    area = _require_positive("junction_area_m2", junction_area_m2)
    permittivity = _require_positive("relative_permittivity", relative_permittivity)
    epsilon = permittivity * VACUUM_PERMITTIVITY_F_PER_M
    return 2.0 / (ELEMENTARY_CHARGE_C * epsilon * area * area * abs(slope))


def depletion_drive(bias_voltage_v, built_in_voltage_v):
    """The one-minus-bias-over-built-in term the power law is raised over."""
    bias = _require_number("bias_voltage_v", bias_voltage_v)
    built_in = _require_positive("built_in_voltage_v", built_in_voltage_v)
    drive = 1.0 - bias / built_in
    if drive <= 0.0:
        raise ValueError(
            "bias %g V is at or beyond the built-in voltage %g V; the depletion "
            "model has no drive term there" % (bias, built_in)
        )
    return drive


def power_law_fit(readings, built_in_voltage_v):
    """Grading coefficient and zero-bias capacitance of the graded model.

    Log capacitance against log depletion drive is a straight line whose
    slope is the negative of the grading coefficient and whose intercept
    is the log of the zero-bias capacitance.
    """
    points = validate_bias_sweep(readings)
    if len(points) < 2:
        raise ValueError("a power-law fit needs at least two bias points")
    built_in = _require_positive("built_in_voltage_v", built_in_voltage_v)
    xs = []
    ys = []
    for bias, capacitance in points:
        xs.append(math.log(depletion_drive(bias, built_in)))
        ys.append(math.log(capacitance))
    fit = least_squares_line(xs, ys)
    grading_coefficient = -fit["slope"]
    zero_bias_capacitance_f = math.exp(fit["intercept"])
    return {
        "grading_coefficient": grading_coefficient,
        "zero_bias_capacitance_f": zero_bias_capacitance_f,
        "r_squared": fit["r_squared"],
        "sample_count": fit["sample_count"],
    }


def forward_bias_offenders(readings, built_in_voltage_v):
    """Sweep points pushed far enough forward to carry diffusion charge.

    Past roughly a third of the built-in voltage the injected minority
    carriers add a diffusion capacitance that has nothing to do with the
    depletion model, and a fit that keeps those points returns a doping
    that is simply wrong.
    """
    points = validate_bias_sweep(readings)
    built_in = _require_positive("built_in_voltage_v", built_in_voltage_v)
    ceiling = MAX_FORWARD_BIAS_FRACTION * built_in
    return tuple(
        (bias, capacitance)
        for bias, capacitance in points
        if not _at_most(bias, ceiling)
    )


def determine_capacitance_model(case):
    """Full clause 11.1.4.2.2 model determination from one bias sweep."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    model = case.get("model_form", MOTT_SCHOTTKY_ABRUPT)
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            "unknown model form %r; supported forms are %s"
            % (model, ", ".join(SUPPORTED_MODELS))
        )
    points = validate_bias_sweep(case.get("readings"))
    area = _require_positive("junction_area_m2", case.get("junction_area_m2"))
    permittivity = _require_positive(
        "relative_permittivity", case.get("relative_permittivity")
    )

    findings = []
    count = len(points)
    span = points[-1][0] - points[0][0]

    if count < MIN_BIAS_POINTS:
        findings.append(
            "sweep offers %d bias points, below the %d a model determination needs"
            % (count, MIN_BIAS_POINTS)
        )
    if not _at_least(span, MIN_BIAS_SPAN_V):
        findings.append(
            "bias span of %.3f V is under the %.2f V floor; the slope is being read "
            "off a sweep too narrow to separate it from the scatter"
            % (span, MIN_BIAS_SPAN_V)
        )

    line = mott_schottky_fit(points)
    built_in_voltage_v = line["built_in_voltage_v"]
    doping = doping_concentration_per_m3(line["slope_per_volt"], area, permittivity)

    parameters = {
        "built_in_voltage_v": built_in_voltage_v,
        "doping_concentration_per_m3": doping,
        "mott_schottky_slope_per_volt": line["slope_per_volt"],
        "mott_schottky_r_squared": line["r_squared"],
    }

    if not _at_least(line["r_squared"], MIN_FIT_QUALITY):
        findings.append(
            "Mott-Schottky line explains only %.4f of the sweep, under the %.2f "
            "floor; the readings are not following one depletion model"
            % (line["r_squared"], MIN_FIT_QUALITY)
        )

    if not (
        _at_least(built_in_voltage_v, MIN_BUILT_IN_VOLTAGE_V)
        and _at_most(built_in_voltage_v, MAX_BUILT_IN_VOLTAGE_V)
    ):
        findings.append(
            "extracted built-in voltage %.3f V falls outside the %.2f V to %.2f V "
            "band a cell junction occupies"
            % (built_in_voltage_v, MIN_BUILT_IN_VOLTAGE_V, MAX_BUILT_IN_VOLTAGE_V)
        )

    offenders = forward_bias_offenders(points, built_in_voltage_v)
    if offenders:
        findings.append(
            "%d sweep point(s) sit above %.0f%% of the built-in voltage, where "
            "diffusion capacitance joins the depletion term; drop them and refit"
            % (len(offenders), MAX_FORWARD_BIAS_FRACTION * 100.0)
        )

    if model == POWER_LAW_GRADED:
        graded = power_law_fit(points, built_in_voltage_v)
        parameters["grading_coefficient"] = graded["grading_coefficient"]
        parameters["zero_bias_capacitance_f"] = graded["zero_bias_capacitance_f"]
        parameters["power_law_r_squared"] = graded["r_squared"]
        if not _at_least(graded["r_squared"], MIN_FIT_QUALITY):
            findings.append(
                "graded power law explains only %.4f of the sweep, under the %.2f "
                "floor" % (graded["r_squared"], MIN_FIT_QUALITY)
            )
        if not (
            _at_least(graded["grading_coefficient"], MIN_GRADING_COEFFICIENT)
            and _at_most(graded["grading_coefficient"], MAX_GRADING_COEFFICIENT)
        ):
            findings.append(
                "grading coefficient %.3f falls outside the %.2f to %.2f band a "
                "real junction profile produces"
                % (
                    graded["grading_coefficient"],
                    MIN_GRADING_COEFFICIENT,
                    MAX_GRADING_COEFFICIENT,
                )
            )

    determined = not findings
    return {
        "model_form": model,
        "bias_point_count": count,
        "bias_span_v": span,
        "parameters": parameters,
        "forward_bias_offender_count": len(offenders),
        "verdict": MODEL_DETERMINED if determined else MODEL_NOT_DETERMINED,
        "determined": determined,
        "findings": findings,
    }
