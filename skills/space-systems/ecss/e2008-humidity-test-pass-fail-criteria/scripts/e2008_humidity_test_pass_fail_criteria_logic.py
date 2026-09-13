"""Post-exposure acceptance of a humidity-exposed photovoltaic coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.4.5 (the continuity and output-power
limits a coupon respects once its humidity exposure has ended). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check that the coupon was left to stabilize for the required recovery
   period before the post-exposure measurement was taken; a reading taken on a
   still-damp coupon is not an admissible basis for a verdict.
2. Correct the pre-exposure and the post-exposure illuminated measurement back
   to reference irradiance and reference cell temperature, so that the
   comparison is between two coupon states and not between two sets of
   measurement conditions.
3. Derive the output-power loss fraction and the retention ratio from the two
   corrected powers, and compare the loss with the limit the coupon has to
   respect.
4. Screen every interconnect circuit of the coupon: an open circuit is an
   outright loss of continuity, and a circuit whose series resistance grew by
   more than its allowance is a finding even while it still conducts.
5. Aggregate the recovery, power and continuity findings into one acceptance
   verdict, reporting the finding list so that a near miss stays visible.
"""

import math

__all__ = [
    "DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C",
    "LIMIT_TOLERANCE",
    "REFERENCE_IRRADIANCE_W_M2",
    "REFERENCE_TEMPERATURE_C",
    "assess_humidity_acceptance",
    "correct_power_to_reference",
    "evaluate_continuity",
    "evaluate_output_power",
    "measurement_power_at_reference",
    "power_loss_fraction",
    "power_retention_ratio",
    "resistance_increase_fraction",
    "within_limit",
]

# Limits are compared against quantities built from differences and ratios of
# measured values, so an exactly-compliant coupon can land a few ULPs on the
# wrong side. Absorb that representation error here instead of widening any
# engineering limit.
LIMIT_TOLERANCE = 1e-9

# Illuminated measurements are reported back to these reference conditions
# before any pre/post comparison is formed.
REFERENCE_IRRADIANCE_W_M2 = 1367.0
REFERENCE_TEMPERATURE_C = 25.0

# Relative power change per degree of cell temperature for a silicon coupon;
# a coupon that carries its own measured coefficient overrides this default.
DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C = -0.0045


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
    """Return a limit expressed as a fraction in the closed range 0 to 1."""
    out = _real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError("%s must be a fraction between 0 and 1, got %g" % (label, out))
    return out


def within_limit(value, limit):
    """Return True when value respects limit, tolerating an exact equality."""
    v = _real(value, "value")
    lim = _real(limit, "limit")
    if v < lim:
        return True
    return math.isclose(v, lim, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def correct_power_to_reference(power_w, irradiance_w_m2, cell_temperature_c,
                               temperature_coefficient_per_c=DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C,
                               reference_irradiance_w_m2=REFERENCE_IRRADIANCE_W_M2,
                               reference_temperature_c=REFERENCE_TEMPERATURE_C):
    """Return the measured output power reported back to reference conditions."""
    power = _positive(power_w, "power_w")
    irradiance = _positive(irradiance_w_m2, "irradiance_w_m2")
    reference_irradiance = _positive(reference_irradiance_w_m2, "reference_irradiance_w_m2")
    temperature = _real(cell_temperature_c, "cell_temperature_c")
    reference_temperature = _real(reference_temperature_c, "reference_temperature_c")
    coefficient = _real(temperature_coefficient_per_c, "temperature_coefficient_per_c")
    if coefficient <= -1.0 or coefficient >= 1.0:
        raise ValueError(
            "temperature_coefficient_per_c is a relative change per degree, got %g" % coefficient
        )
    factor = 1.0 + coefficient * (temperature - reference_temperature)
    if factor <= 0.0:
        raise ValueError(
            "temperature correction factor %g is not positive; the coefficient and the "
            "temperature span are inconsistent" % factor
        )
    return power * (reference_irradiance / irradiance) / factor


def measurement_power_at_reference(record, name="measurement"):
    """Return the reference-condition power of one illuminated measurement record."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % name)
    for key in ("power_w", "irradiance_w_m2", "cell_temperature_c"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (name, key))
    return correct_power_to_reference(
        record["power_w"],
        record["irradiance_w_m2"],
        record["cell_temperature_c"],
        record.get(
            "temperature_coefficient_per_c", DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C
        ),
        record.get("reference_irradiance_w_m2", REFERENCE_IRRADIANCE_W_M2),
        record.get("reference_temperature_c", REFERENCE_TEMPERATURE_C),
    )


def power_loss_fraction(power_before_w, power_after_w):
    """Return the relative output-power loss; a gain comes back negative."""
    before = _positive(power_before_w, "power_before_w")
    after = _positive(power_after_w, "power_after_w")
    return (before - after) / before


def power_retention_ratio(power_before_w, power_after_w):
    """Return the fraction of the pre-exposure output power still delivered."""
    before = _positive(power_before_w, "power_before_w")
    after = _positive(power_after_w, "power_after_w")
    return after / before


def evaluate_output_power(pre_exposure_measurement, post_exposure_measurement,
                          max_power_loss_fraction):
    """Return the corrected-power comparison of a coupon across the exposure."""
    limit = _fraction(max_power_loss_fraction, "max_power_loss_fraction")
    before = measurement_power_at_reference(
        pre_exposure_measurement, "pre_exposure_measurement"
    )
    after = measurement_power_at_reference(
        post_exposure_measurement, "post_exposure_measurement"
    )
    loss = power_loss_fraction(before, after)
    return {
        "power_before_w": before,
        "power_after_w": after,
        "power_loss_fraction": loss,
        "power_retention_ratio": power_retention_ratio(before, after),
        "max_power_loss_fraction": limit,
        "within_limit": within_limit(loss, limit),
    }


def resistance_increase_fraction(pre_resistance_ohm, post_resistance_ohm):
    """Return the relative growth of a circuit series resistance."""
    before = _positive(pre_resistance_ohm, "pre_resistance_ohm")
    after = _positive(post_resistance_ohm, "post_resistance_ohm")
    return (after - before) / before


def _is_open_circuit(value):
    """Return True when a post-exposure resistance reading means no continuity."""
    if value is None:
        return True
    if isinstance(value, float) and math.isinf(value) and value > 0.0:
        return True
    return False


def evaluate_continuity(circuits, max_resistance_increase_fraction):
    """Return one continuity record per interconnect circuit of the coupon."""
    limit = _non_negative(
        max_resistance_increase_fraction, "max_resistance_increase_fraction"
    )
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("circuits must be a non-empty sequence of circuit records")
    seen = set()
    records = []
    for index, circuit in enumerate(circuits):
        if not isinstance(circuit, dict):
            raise ValueError("circuits[%d] must be a mapping" % index)
        for key in ("circuit_id", "pre_resistance_ohm", "post_resistance_ohm"):
            if key not in circuit:
                raise ValueError("circuits[%d] missing required key '%s'" % (index, key))
        circuit_id = circuit["circuit_id"]
        if not isinstance(circuit_id, str) or not circuit_id.strip():
            raise ValueError("circuits[%d] circuit_id must be a non-empty string" % index)
        circuit_id = circuit_id.strip()
        if circuit_id in seen:
            raise ValueError("duplicate circuit_id %r in circuits" % circuit_id)
        seen.add(circuit_id)
        before = _positive(circuit["pre_resistance_ohm"], "circuits[%d] pre_resistance_ohm" % index)
        post_raw = circuit["post_resistance_ohm"]
        if _is_open_circuit(post_raw):
            records.append({
                "circuit_id": circuit_id,
                "open_circuit": True,
                "pre_resistance_ohm": before,
                "post_resistance_ohm": None,
                "resistance_increase_fraction": None,
                "within_allowance": False,
            })
            continue
        after = _positive(post_raw, "circuits[%d] post_resistance_ohm" % index)
        growth = resistance_increase_fraction(before, after)
        records.append({
            "circuit_id": circuit_id,
            "open_circuit": False,
            "pre_resistance_ohm": before,
            "post_resistance_ohm": after,
            "resistance_increase_fraction": growth,
            "within_allowance": within_limit(growth, limit),
        })
    return records


def _recovery_findings(spec):
    """Return the findings raised by the stabilization period before measurement."""
    required = _non_negative(
        spec.get("required_recovery_hours", 0.0), "required_recovery_hours"
    )
    if required == 0.0:
        return []
    if "recovery_hours" not in spec or spec["recovery_hours"] is None:
        return [
            "recovery period before the post-exposure measurement was not recorded; "
            "the required period is %g h" % required
        ]
    observed = _non_negative(spec["recovery_hours"], "recovery_hours")
    if observed > required or math.isclose(
        observed, required, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    ):
        return []
    return [
        "post-exposure measurement taken after %g h of recovery, short of the "
        "required %g h" % (observed, required)
    ]


def assess_humidity_acceptance(spec):
    """Run the full clause 5.5.1.4.5 post-exposure acceptance assessment.

    spec keys: pre_exposure_measurement, post_exposure_measurement, circuits,
    max_power_loss_fraction, max_resistance_increase_fraction, optional
    recovery_hours and required_recovery_hours.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("pre_exposure_measurement", "post_exposure_measurement", "circuits",
                "max_power_loss_fraction", "max_resistance_increase_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    findings = list(_recovery_findings(spec))
    power = evaluate_output_power(
        spec["pre_exposure_measurement"],
        spec["post_exposure_measurement"],
        spec["max_power_loss_fraction"],
    )
    continuity = evaluate_continuity(
        spec["circuits"], spec["max_resistance_increase_fraction"]
    )
    if not power["within_limit"]:
        findings.append(
            "corrected output power fell by %.4f of its pre-exposure value, past the "
            "permitted %.4f" % (power["power_loss_fraction"], power["max_power_loss_fraction"])
        )
    for record in continuity:
        if record["open_circuit"]:
            findings.append(
                "circuit %s shows no continuity after the humidity exposure"
                % record["circuit_id"]
            )
        elif not record["within_allowance"]:
            findings.append(
                "circuit %s series resistance grew by %.4f of its pre-exposure value, "
                "past the permitted %.4f"
                % (record["circuit_id"], record["resistance_increase_fraction"],
                   _non_negative(spec["max_resistance_increase_fraction"],
                                 "max_resistance_increase_fraction"))
            )
    open_count = sum(1 for record in continuity if record["open_circuit"])
    return {
        "power": power,
        "continuity": continuity,
        "open_circuit_count": open_count,
        "findings": findings,
        "accepted": not findings,
    }
