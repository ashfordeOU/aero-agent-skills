#!/usr/bin/env python3
"""How electron fluence degrades an external protection diode, read off an
accelerated life exposure.

Anchor: ECSS-E-ST-20-08C clause 9.6.12. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The exposure is a staircase: the diode is measured unirradiated, then
after each of a rising set of electron fluences. What comes out is not a
set of readings but a life curve, and the question it has to answer is
what the device still does at the fluence the mission actually
accumulates.

A protection diode degrades in two directions at once and they are not
symmetric. Its forward drop grows, because displacement damage cuts
carrier lifetime and the junction needs more volts to pass the same
current, and that extra drop comes straight out of the string the diode
sits in. Its reverse leakage grows too, and far faster, because damage
adds generation centres; leakage that started in nanoamps can climb by
orders of magnitude, which is why it is read as a power law and the
forward drop is not.

Both are ratios against the unirradiated measurement, so that
measurement is part of the article's record rather than a preliminary. A
ratio is only a damage number if both readings were taken the same way:
a junction's forward drop moves with temperature all on its own, so a
step measured warm reports the bench and the beam gets the blame.

Damage accumulates roughly per decade of fluence, not per unit of it,
which is why the steps are spaced by factors of ten and both series are
fitted against the logarithm of fluence. A step that sits off its own
fitted curve is a dosimetry or a measurement finding, not a new physical
effect, and it is reported as one.

The limits below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

UNIRRADIATED_REFERENCE_MISSING = "unirradiated-reference-missing"
FLUENCE_STAIRCASE_INVALID = "fluence-staircase-invalid"
MEASUREMENT_CONDITIONS_INCONSISTENT = "measurement-conditions-inconsistent"
DEGRADATION_NOT_MONOTONIC = "degradation-not-monotonic"
STEP_OFF_DEGRADATION_CURVE = "step-off-degradation-curve"
END_OF_LIFE_LIMIT_EXCEEDED = "end-of-life-limit-exceeded"
DEGRADATION_CHARACTERIZED = "diode-degradation-characterized"

DEFAULT_IRRADIATION_POLICY = {
    "reference_temperature_c": 25.0,
    "temperature_tolerance_c": 2.0,
    "min_irradiated_steps": 3,
    "monotonic_tolerance_ratio": 0.002,
    "max_relative_residual": 0.05,
    "max_end_of_life_forward_voltage_ratio": 1.15,
    "max_end_of_life_leakage_growth_ratio": 50.0,
}

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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_irradiation_policy(policy):
    """Check the exposure policy is complete and internally sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_number("reference_temperature_c", policy.get("reference_temperature_c"))
    _require_positive(
        "temperature_tolerance_c", policy.get("temperature_tolerance_c")
    )
    steps = _require_count(
        "min_irradiated_steps", policy.get("min_irradiated_steps")
    )
    if steps < 2:
        raise ValueError(
            "min_irradiated_steps %d cannot define a curve; two irradiated "
            "points are the fewest a slope can be drawn through" % steps
        )
    _require_positive(
        "monotonic_tolerance_ratio", policy.get("monotonic_tolerance_ratio")
    )
    _require_positive(
        "max_relative_residual", policy.get("max_relative_residual")
    )
    forward = _require_positive(
        "max_end_of_life_forward_voltage_ratio",
        policy.get("max_end_of_life_forward_voltage_ratio"),
    )
    if forward < 1.0:
        raise ValueError(
            "max_end_of_life_forward_voltage_ratio %g asks the forward drop to "
            "fall under irradiation, which is not the damage mechanism" % forward
        )
    leakage = _require_positive(
        "max_end_of_life_leakage_growth_ratio",
        policy.get("max_end_of_life_leakage_growth_ratio"),
    )
    if leakage < 1.0:
        raise ValueError(
            "max_end_of_life_leakage_growth_ratio %g asks leakage to fall under "
            "irradiation, which is not the damage mechanism" % leakage
        )
    return policy


def validate_reference_measurement(reference):
    """Read the unirradiated measurement every later ratio is taken against."""
    if not isinstance(reference, dict):
        raise ValueError("reference must be a mapping, got %r" % (reference,))
    forward = _require_positive(
        "forward_voltage_v on the unirradiated reference",
        reference.get("forward_voltage_v"),
    )
    leakage = _require_positive(
        "reverse_leakage_a on the unirradiated reference",
        reference.get("reverse_leakage_a"),
    )
    temperature = _require_number(
        "measurement_temperature_c on the unirradiated reference",
        reference.get("measurement_temperature_c"),
    )
    return forward, leakage, temperature


def validate_step(step):
    """Read one irradiated step: its fluence and the two parameters measured."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    fluence = _require_positive(
        "fluence_e_per_cm2", step.get("fluence_e_per_cm2")
    )
    forward = _require_positive(
        "forward_voltage_v at %g e/cm2" % fluence, step.get("forward_voltage_v")
    )
    leakage = _require_positive(
        "reverse_leakage_a at %g e/cm2" % fluence, step.get("reverse_leakage_a")
    )
    temperature = _require_number(
        "measurement_temperature_c at %g e/cm2" % fluence,
        step.get("measurement_temperature_c"),
    )
    return fluence, forward, leakage, temperature


def staircase_rising(fluences):
    """True when each exposure sits strictly above the one before it."""
    if not isinstance(fluences, (list, tuple)) or len(fluences) < 2:
        raise ValueError("a staircase needs at least two fluences to rise across")
    values = [_require_positive("fluence", value) for value in fluences]
    return all(later > earlier for earlier, later in zip(values, values[1:]))


def decades_between(low_fluence, high_fluence):
    """How many decades of fluence separate two exposures."""
    low = _require_positive("low_fluence", low_fluence)
    high = _require_positive("high_fluence", high_fluence)
    if high < low:
        raise ValueError(
            "high_fluence %g sits below low_fluence %g, so the span is reversed"
            % (high, low)
        )
    return math.log10(high / low)


def measurement_at_reference_conditions(
    temperature_c, policy=DEFAULT_IRRADIATION_POLICY
):
    """True when a step was measured close enough to the reference temperature."""
    validate_irradiation_policy(policy)
    temperature = _require_number("temperature_c", temperature_c)
    reference = float(policy["reference_temperature_c"])
    return _at_most(
        abs(temperature - reference), float(policy["temperature_tolerance_c"])
    )


def forward_voltage_ratio(step_voltage_v, reference_voltage_v):
    """Forward drop as a multiple of the unirradiated drop."""
    step = _require_positive("step_voltage_v", step_voltage_v)
    reference = _require_positive("reference_voltage_v", reference_voltage_v)
    return step / reference


def leakage_growth_ratio(step_leakage_a, reference_leakage_a):
    """Reverse leakage as a multiple of the unirradiated leakage."""
    step = _require_positive("step_leakage_a", step_leakage_a)
    reference = _require_positive("reference_leakage_a", reference_leakage_a)
    return step / reference


def fit_against_log_fluence(points):
    """Least-squares line through (log10 fluence, value), returned per decade."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("a fit needs at least two points")
    xs = []
    ys = []
    for fluence, value in points:
        xs.append(math.log10(_require_positive("fluence", fluence)))
        ys.append(_require_number("fitted value", value))
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    spread = sum((x - mean_x) ** 2 for x in xs)
    if spread <= 0.0:
        raise ValueError(
            "every point sits at the same fluence, so no slope per decade can "
            "be drawn through them"
        )
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread
    intercept = mean_y - slope * mean_x
    return intercept, slope


def fitted_value_at_fluence(fit, fluence):
    """Read the fitted line at one fluence."""
    if not isinstance(fit, (list, tuple)) or len(fit) != 2:
        raise ValueError("fit must be an (intercept, slope) pair, got %r" % (fit,))
    intercept = _require_number("intercept", fit[0])
    slope = _require_number("slope", fit[1])
    target = _require_positive("fluence", fluence)
    return intercept + slope * math.log10(target)


def projected_forward_voltage_ratio(points, end_of_life_fluence):
    """Forward-drop multiple projected to the mission end-of-life fluence."""
    return fitted_value_at_fluence(
        fit_against_log_fluence(points), end_of_life_fluence
    )


def projected_leakage_growth_ratio(points, end_of_life_fluence):
    """Leakage multiple projected as a power law in fluence."""
    logged = [
        (fluence, math.log10(_require_positive("leakage ratio", ratio)))
        for fluence, ratio in points
    ]
    return 10.0 ** fitted_value_at_fluence(
        fit_against_log_fluence(logged), end_of_life_fluence
    )


def max_relative_residual(points):
    """Largest relative distance of a point from the line fitted through them."""
    fit = fit_against_log_fluence(points)
    worst = 0.0
    for fluence, value in points:
        predicted = fitted_value_at_fluence(fit, fluence)
        scale = max(abs(float(value)), 1e-12)
        worst = max(worst, abs(float(value) - predicted) / scale)
    return worst


def non_monotonic_fluences(points, policy=DEFAULT_IRRADIATION_POLICY):
    """Fluences where a damage ratio fell materially instead of growing."""
    validate_irradiation_policy(policy)
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("monotonicity needs at least two points to compare")
    tolerance = float(policy["monotonic_tolerance_ratio"])
    offenders = []
    previous_fluence, previous_value = points[0]
    for fluence, value in points[1:]:
        if float(value) < float(previous_value) - tolerance * abs(
            float(previous_value)
        ):
            offenders.append(fluence)
        previous_fluence, previous_value = fluence, value
    return tuple(offenders)


def assess_diode_electron_irradiation(case, policy=DEFAULT_IRRADIATION_POLICY):
    """Full clause 9.6.12 reading of one protection diode electron exposure."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_irradiation_policy(policy)

    findings = []
    step_records = []
    result = {
        "step_records": step_records,
        "forward_voltage_ratio_per_decade": None,
        "leakage_decades_per_decade": None,
        "max_relative_residual": None,
        "end_of_life_fluence_e_per_cm2": None,
        "projected_forward_voltage_ratio": None,
        "projected_leakage_growth_ratio": None,
        "findings": findings,
    }

    reference = case.get("unirradiated_reference")
    if reference is None:
        findings.append(
            "the run carries no unirradiated measurement, so every later reading "
            "is an absolute value with no damage ratio behind it"
        )
        result["verdict"] = UNIRRADIATED_REFERENCE_MISSING
        return result
    ref_forward, ref_leakage, ref_temperature = validate_reference_measurement(
        reference
    )

    steps = case.get("steps")
    if not isinstance(steps, (list, tuple)):
        raise ValueError("case is missing a steps record")
    if len(steps) < int(policy["min_irradiated_steps"]):
        findings.append(
            "the staircase carries %d irradiated step(s) against the %d the "
            "policy asks, which is too few to draw a life curve through"
            % (len(steps), int(policy["min_irradiated_steps"]))
        )
        result["verdict"] = FLUENCE_STAIRCASE_INVALID
        return result

    fluences = []
    for step in steps:
        fluence, forward, leakage, temperature = validate_step(step)
        fluences.append(fluence)
        step_records.append(
            {
                "fluence_e_per_cm2": fluence,
                "forward_voltage_v": forward,
                "reverse_leakage_a": leakage,
                "measurement_temperature_c": temperature,
                "forward_voltage_ratio": forward_voltage_ratio(forward, ref_forward),
                "leakage_growth_ratio": leakage_growth_ratio(leakage, ref_leakage),
            }
        )

    if not staircase_rising(fluences):
        findings.append(
            "the exposures do not rise step by step, so the record is not a "
            "staircase and the accumulated fluence at each reading is unclear"
        )
        result["verdict"] = FLUENCE_STAIRCASE_INVALID
        return result

    off_condition = [
        entry["fluence_e_per_cm2"]
        for entry in step_records
        if not measurement_at_reference_conditions(
            entry["measurement_temperature_c"], policy
        )
    ]
    if not measurement_at_reference_conditions(ref_temperature, policy):
        off_condition.insert(0, 0.0)
    if off_condition:
        findings.append(
            "%d measurement(s) sat outside the reference temperature band, so "
            "those ratios report the bench as much as the beam"
            % len(off_condition)
        )
        result["verdict"] = MEASUREMENT_CONDITIONS_INCONSISTENT
        return result

    forward_points = [
        (entry["fluence_e_per_cm2"], entry["forward_voltage_ratio"])
        for entry in step_records
    ]
    leakage_points = [
        (entry["fluence_e_per_cm2"], entry["leakage_growth_ratio"])
        for entry in step_records
    ]

    drifting_back = non_monotonic_fluences(forward_points, policy) + (
        non_monotonic_fluences(leakage_points, policy)
    )
    if drifting_back:
        findings.append(
            "%d step(s) report less damage than the exposure before them, which "
            "points at the dosimetry or the bench rather than at the diode"
            % len(drifting_back)
        )
        result["verdict"] = DEGRADATION_NOT_MONOTONIC
        return result

    _, forward_slope = fit_against_log_fluence(forward_points)
    logged_leakage = [
        (fluence, math.log10(ratio)) for fluence, ratio in leakage_points
    ]
    _, leakage_slope = fit_against_log_fluence(logged_leakage)
    result["forward_voltage_ratio_per_decade"] = forward_slope
    result["leakage_decades_per_decade"] = leakage_slope

    residual = max(
        max_relative_residual(forward_points), max_relative_residual(logged_leakage)
    )
    result["max_relative_residual"] = residual
    if not _at_most(residual, float(policy["max_relative_residual"])):
        findings.append(
            "a step sits %.3g relative off the curve fitted through the others, "
            "past the allowance, so one reading or one dosimetry number is wrong"
            % residual
        )
        result["verdict"] = STEP_OFF_DEGRADATION_CURVE
        return result

    end_of_life = case.get("end_of_life_fluence_e_per_cm2")
    if end_of_life is None:
        raise ValueError(
            "case is missing the end-of-life fluence the projection is made to"
        )
    end_of_life = _require_positive("end_of_life_fluence_e_per_cm2", end_of_life)
    result["end_of_life_fluence_e_per_cm2"] = end_of_life

    projected_forward = projected_forward_voltage_ratio(forward_points, end_of_life)
    projected_leakage = projected_leakage_growth_ratio(leakage_points, end_of_life)
    result["projected_forward_voltage_ratio"] = projected_forward
    result["projected_leakage_growth_ratio"] = projected_leakage

    if not _at_most(
        projected_forward, float(policy["max_end_of_life_forward_voltage_ratio"])
    ):
        findings.append(
            "the forward drop is projected to reach %.4g times its unirradiated "
            "value at end of life, past the limit the string budget allows"
            % projected_forward
        )
    if not _at_most(
        projected_leakage, float(policy["max_end_of_life_leakage_growth_ratio"])
    ):
        findings.append(
            "reverse leakage is projected to reach %.4g times its unirradiated "
            "value at end of life, past the limit the blocking function allows"
            % projected_leakage
        )
    if findings:
        result["verdict"] = END_OF_LIFE_LIMIT_EXCEEDED
        return result

    result["verdict"] = DEGRADATION_CHARACTERIZED
    return result
