"""Allowed degradation of a photovoltaic coupon after vacuum thermal cycling.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.11.3 (how much coupon performance and
insulation resistance may degrade once the vacuum cycling run has ended).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Report the pre-cycling and the post-cycling illuminated readings back to
   reference irradiance and reference cell temperature, so the comparison is
   between two coupon states rather than two sets of measurement conditions.
2. Form the loss fraction of maximum power, of short-circuit current and of
   open-circuit voltage, and compare each with its own allowance: the three
   degrade for different reasons and a single power number hides which.
3. Guard the open-circuit voltage comparison, which is corrected for cell
   temperature only, against being formed across two very different
   irradiances.
4. Judge the post-cycling insulation resistance three ways: against its own
   floor, against the decades it lost relative to the pre-cycling value, and
   against the leakage current it implies at the declared test voltage. A
   dielectric breakdown is carried as its own outcome rather than as a very
   large decade loss.
5. Aggregate the performance and the insulation findings into one acceptance
   verdict, reporting the finding list so a near miss stays visible.
"""

import math

__all__ = [
    "DEFAULT_TEMPERATURE_COEFFICIENTS_PER_C",
    "LIMIT_TOLERANCE",
    "PERFORMANCE_PARAMETERS",
    "REFERENCE_IRRADIANCE_W_M2",
    "REFERENCE_TEMPERATURE_C",
    "VOC_IRRADIANCE_TOLERANCE",
    "assess_vacuum_cycling_criteria",
    "correct_reading_to_reference",
    "degradation_fraction",
    "evaluate_insulation",
    "evaluate_performance",
    "insulation_decades_lost",
    "leakage_current_a",
    "reading_at_reference",
    "within_allowance",
]

# Allowances are compared against quantities built from differences and ratios
# of measured values, so an exactly compliant coupon can land a few ULPs on the
# wrong side. Absorb that representation error here rather than widening any
# engineering allowance.
LIMIT_TOLERANCE = 1e-9

# Illuminated readings are reported back to these reference conditions before
# any pre/post comparison is formed.
REFERENCE_IRRADIANCE_W_M2 = 1367.0
REFERENCE_TEMPERATURE_C = 25.0

# The three illuminated parameters the acceptance decision rests on. Maximum
# power and short-circuit current scale with irradiance; open-circuit voltage
# is corrected for cell temperature only, which is why its comparison carries
# an irradiance-comparability guard.
PERFORMANCE_PARAMETERS = ("pmax_w", "isc_a", "voc_v")

SCALES_WITH_IRRADIANCE = {"pmax_w": True, "isc_a": True, "voc_v": False}

# Relative change per degree of cell temperature for a silicon coupon; a coupon
# carrying its own measured coefficients overrides these defaults.
DEFAULT_TEMPERATURE_COEFFICIENTS_PER_C = {
    "pmax_w": -0.0045,
    "isc_a": 0.0005,
    "voc_v": -0.0033,
}

# How far the two measurement irradiances may differ before the open-circuit
# voltage comparison stops meaning anything.
VOC_IRRADIANCE_TOLERANCE = 0.10

OUTCOME_BREAKDOWN = "dielectric-breakdown"
OUTCOME_MEASURED = "measured"


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _fraction(value, label):
    """Return an allowance expressed as a fraction in the closed range 0 to 1."""
    out = _real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError("%s must be a fraction between 0 and 1, got %g" % (label, out))
    return out


def within_allowance(value, allowance):
    """Return True when value respects allowance, tolerating an exact equality."""
    v = _real(value, "value")
    limit = _real(allowance, "allowance")
    if v < limit:
        return True
    return math.isclose(v, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def correct_reading_to_reference(value, parameter, irradiance_w_m2,
                                 cell_temperature_c, coefficient_per_c=None,
                                 reference_irradiance_w_m2=REFERENCE_IRRADIANCE_W_M2,
                                 reference_temperature_c=REFERENCE_TEMPERATURE_C):
    """Return one illuminated reading reported back to reference conditions."""
    if parameter not in PERFORMANCE_PARAMETERS:
        raise ValueError(
            "parameter %r is not one of %s" % (parameter, ", ".join(PERFORMANCE_PARAMETERS))
        )
    reading = _positive(value, parameter)
    irradiance = _positive(irradiance_w_m2, "irradiance_w_m2")
    reference_irradiance = _positive(
        reference_irradiance_w_m2, "reference_irradiance_w_m2"
    )
    temperature = _real(cell_temperature_c, "cell_temperature_c")
    reference_temperature = _real(reference_temperature_c, "reference_temperature_c")
    if coefficient_per_c is None:
        coefficient_per_c = DEFAULT_TEMPERATURE_COEFFICIENTS_PER_C[parameter]
    coefficient = _real(coefficient_per_c, "coefficient_per_c")
    if coefficient <= -1.0 or coefficient >= 1.0:
        raise ValueError(
            "coefficient_per_c is a relative change per degree, got %g" % coefficient
        )
    factor = 1.0 + coefficient * (temperature - reference_temperature)
    if factor <= 0.0:
        raise ValueError(
            "temperature correction factor %g is not positive; the coefficient and "
            "the temperature span are inconsistent" % factor
        )
    corrected = reading / factor
    if SCALES_WITH_IRRADIANCE[parameter]:
        corrected = corrected * (reference_irradiance / irradiance)
    return corrected


def reading_at_reference(record, parameter, name="measurement"):
    """Return the reference-condition value of one parameter of a reading set."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % name)
    for key in (parameter, "irradiance_w_m2", "cell_temperature_c"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (name, key))
    coefficients = record.get("temperature_coefficients_per_c", {})
    if not isinstance(coefficients, dict):
        raise ValueError("%s temperature_coefficients_per_c must be a mapping" % name)
    return correct_reading_to_reference(
        record[parameter],
        parameter,
        record["irradiance_w_m2"],
        record["cell_temperature_c"],
        coefficients.get(parameter),
        record.get("reference_irradiance_w_m2", REFERENCE_IRRADIANCE_W_M2),
        record.get("reference_temperature_c", REFERENCE_TEMPERATURE_C),
    )


def degradation_fraction(before, after):
    """Return the relative degradation; an improvement comes back negative."""
    pre = _positive(before, "before")
    post = _positive(after, "after")
    return (pre - post) / pre


def evaluate_performance(pre_cycling, post_cycling, allowances):
    """Return the corrected pre/post comparison of the three illuminated parameters."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping")
    records = []
    findings = []
    for parameter in PERFORMANCE_PARAMETERS:
        if parameter not in allowances:
            raise ValueError("allowances missing required key '%s'" % parameter)
        allowance = _fraction(allowances[parameter], "allowances['%s']" % parameter)
        before = reading_at_reference(pre_cycling, parameter, "pre_cycling")
        after = reading_at_reference(post_cycling, parameter, "post_cycling")
        loss = degradation_fraction(before, after)
        acceptable = within_allowance(loss, allowance)
        records.append({
            "parameter": parameter,
            "before_at_reference": before,
            "after_at_reference": after,
            "loss_fraction": loss,
            "retention_ratio": after / before,
            "allowance": allowance,
            "within_allowance": acceptable,
        })
        if not acceptable:
            findings.append(
                "%s fell by %.4f of its pre-cycling value, past the allowed %.4f"
                % (parameter, loss, allowance)
            )

    pre_irradiance = _positive(pre_cycling["irradiance_w_m2"], "pre irradiance_w_m2")
    post_irradiance = _positive(post_cycling["irradiance_w_m2"], "post irradiance_w_m2")
    ratio = post_irradiance / pre_irradiance
    deviation = abs(ratio - 1.0)
    tolerance = _non_negative(
        allowances.get("voc_irradiance_tolerance", VOC_IRRADIANCE_TOLERANCE),
        "voc_irradiance_tolerance",
    )
    comparable = within_allowance(deviation, tolerance)
    if not comparable:
        findings.append(
            "open-circuit voltage was compared across an irradiance difference of "
            "%.4f, past the %.4f that keeps a temperature-only correction valid"
            % (deviation, tolerance)
        )
    return {
        "parameters": records,
        "irradiance_ratio": ratio,
        "irradiance_deviation": deviation,
        "voc_comparison_valid": comparable,
        "findings": findings,
        "within_allowances": not findings,
    }


def insulation_decades_lost(pre_resistance_ohm, post_resistance_ohm):
    """Return how many decades the insulation resistance fell across the run."""
    before = _positive(pre_resistance_ohm, "pre_resistance_ohm")
    after = _positive(post_resistance_ohm, "post_resistance_ohm")
    return math.log10(before / after)


def leakage_current_a(resistance_ohm, test_voltage_v):
    """Return the leakage current the insulation passes at the test voltage."""
    resistance = _positive(resistance_ohm, "resistance_ohm")
    voltage = _positive(test_voltage_v, "test_voltage_v")
    return voltage / resistance


def evaluate_insulation(insulation):
    """Return the post-cycling insulation verdict of the coupon."""
    if not isinstance(insulation, dict):
        raise ValueError("insulation must be a mapping")
    for key in ("test_voltage_v", "min_resistance_ohm"):
        if key not in insulation:
            raise ValueError("insulation missing required key '%s'" % key)
    voltage = _positive(insulation["test_voltage_v"], "test_voltage_v")
    floor = _positive(insulation["min_resistance_ohm"], "min_resistance_ohm")
    breakdown = insulation.get("breakdown", False)
    if not isinstance(breakdown, bool):
        raise ValueError("insulation breakdown must be a boolean")
    if breakdown:
        return {
            "outcome": OUTCOME_BREAKDOWN,
            "test_voltage_v": voltage,
            "post_resistance_ohm": None,
            "min_resistance_ohm": floor,
            "decades_lost": None,
            "leakage_current_a": None,
            "findings": [
                "the insulation broke down at the %g V test voltage after cycling"
                % voltage
            ],
            "acceptable": False,
        }
    if "post_resistance_ohm" not in insulation:
        raise ValueError("insulation missing required key 'post_resistance_ohm'")
    after = _positive(insulation["post_resistance_ohm"], "post_resistance_ohm")
    findings = []
    above_floor = after > floor or math.isclose(
        after, floor, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )
    if not above_floor:
        findings.append(
            "post-cycling insulation resistance %g ohm is below the %g ohm floor"
            % (after, floor)
        )
    decades = None
    if insulation.get("pre_resistance_ohm") is not None:
        before = _positive(insulation["pre_resistance_ohm"], "pre_resistance_ohm")
        decades = insulation_decades_lost(before, after)
        max_decades = _non_negative(
            insulation.get("max_decades_lost", 1.0), "max_decades_lost"
        )
        if not within_allowance(decades, max_decades):
            findings.append(
                "insulation resistance lost %.4f decades, past the %.4f allowed"
                % (decades, max_decades)
            )
    leakage = leakage_current_a(after, voltage)
    max_leakage = insulation.get("max_leakage_a")
    if max_leakage is not None:
        allowed = _positive(max_leakage, "max_leakage_a")
        if not within_allowance(leakage, allowed):
            findings.append(
                "leakage current %.3e A at %g V is past the %.3e A allowed"
                % (leakage, voltage, allowed)
            )
    return {
        "outcome": OUTCOME_MEASURED,
        "test_voltage_v": voltage,
        "post_resistance_ohm": after,
        "min_resistance_ohm": floor,
        "decades_lost": decades,
        "leakage_current_a": leakage,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_vacuum_cycling_criteria(spec):
    """Run the full clause 5.5.3.11.3 post-cycling acceptance assessment.

    spec keys: pre_cycling, post_cycling (each carrying pmax_w, isc_a, voc_v,
    irradiance_w_m2, cell_temperature_c), allowances and insulation.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("pre_cycling", "post_cycling", "allowances", "insulation"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    performance = evaluate_performance(
        spec["pre_cycling"], spec["post_cycling"], spec["allowances"]
    )
    insulation = evaluate_insulation(spec["insulation"])
    findings = list(performance["findings"]) + list(insulation["findings"])
    return {
        "performance": performance,
        "insulation": insulation,
        "findings": findings,
        "accepted": not findings,
    }
