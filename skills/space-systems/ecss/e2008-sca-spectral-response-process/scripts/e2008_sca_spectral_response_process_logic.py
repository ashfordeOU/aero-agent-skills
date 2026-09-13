"""Pre-irradiation short circuit current baseline for solar cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.5.2. The procedure below is a paraphrase
of the clause intent and reproduces none of its text: before an irradiation
campaign begins, the short circuit current of every test sample is measured and
compared against a reference device, so that the degradation the campaign later
reports is expressed against a baseline somebody can defend.

Procedure implemented here
--------------------------
1. Validate the reference device: it carries a traceable identifier and its
   calibration is still inside the declared interval. A reference whose
   calibration has lapsed turns every ratio taken against it into an
   unsupported number.
2. Hold the bench conditions of each reading to the window the correction stays
   valid in. Irradiance and temperature far from reference conditions
   extrapolate the declared coefficients instead of interpolating them.
3. Translate every reading back to reference irradiance and temperature,
   Isc_ref = Isc * (E_ref / E) / (1 + alpha * (T - T_ref)), so that samples read
   on different days on a drifting bench are comparable at all.
4. Express each sample as a ratio of its corrected current to the corrected
   current of the reference device and hold that ratio inside the declared
   acceptance band.
5. Reconcile the samples measured against the samples the campaign intends to
   expose. A sample irradiated without a pre-irradiation reading has no
   baseline at all, which is a heavier finding than an out-of-band ratio.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "CONDITION_TOLERANCE",
    "DEFAULT_REFERENCE_IRRADIANCE_W_M2",
    "DEFAULT_REFERENCE_TEMPERATURE_C",
    "MAX_IRRADIANCE_DEVIATION_FRACTION",
    "MAX_TEMPERATURE_DEVIATION_C",
    "correct_short_circuit_current_a",
    "irradiance_deviation_fraction",
    "temperature_deviation_c",
    "conditions_correctable",
    "response_ratio",
    "ratio_within_band",
    "validate_reference_device",
    "corrected_reference_current_a",
    "evaluate_sample",
    "assess_spectral_response_baseline",
]

# Corrected currents and their ratios are products and quotients of floats, so a
# sample built exactly to a band edge can land a few units in the last place
# outside it. Absorb that representation error here rather than by widening the
# declared band itself.
RATIO_TOLERANCE = 1e-9
CONDITION_TOLERANCE = 1e-9

# Air-mass-zero reference conditions the corrected current is expressed at.
DEFAULT_REFERENCE_IRRADIANCE_W_M2 = 1367.0
DEFAULT_REFERENCE_TEMPERATURE_C = 25.0

# Beyond these deviations the declared coefficients are being extrapolated and
# the corrected reading carries an error nobody quantified.
MAX_IRRADIANCE_DEVIATION_FRACTION = 0.20
MAX_TEMPERATURE_DEVIATION_C = 15.0


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


def _count(label, value, allow_zero=True):
    """Return value as a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must be greater than zero" % label)
    return value


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


def correct_short_circuit_current_a(
    isc_a,
    irradiance_w_m2,
    temperature_c,
    alpha_per_c,
    reference_irradiance_w_m2=DEFAULT_REFERENCE_IRRADIANCE_W_M2,
    reference_temperature_c=DEFAULT_REFERENCE_TEMPERATURE_C,
):
    """Return the short circuit current translated back to reference conditions."""
    current = _real("isc_a", isc_a)
    irradiance = _real("irradiance_w_m2", irradiance_w_m2)
    temperature = _real("temperature_c", temperature_c, allow_negative=True)
    alpha = _real("alpha_per_c", alpha_per_c, allow_zero=True, allow_negative=True)
    ref_irradiance = _real("reference_irradiance_w_m2", reference_irradiance_w_m2)
    ref_temperature = _real(
        "reference_temperature_c", reference_temperature_c, allow_negative=True
    )
    thermal_factor = 1.0 + alpha * (temperature - ref_temperature)
    if thermal_factor <= 0.0:
        raise ValueError(
            "temperature coefficient %g /C drives the correction factor to %g at "
            "%g C; the translation is not defined there"
            % (alpha, thermal_factor, temperature)
        )
    return current * (ref_irradiance / irradiance) / thermal_factor


def irradiance_deviation_fraction(
    irradiance_w_m2, reference_irradiance_w_m2=DEFAULT_REFERENCE_IRRADIANCE_W_M2
):
    """Return how far the bench irradiance sits from reference, as a fraction."""
    irradiance = _real("irradiance_w_m2", irradiance_w_m2)
    reference = _real("reference_irradiance_w_m2", reference_irradiance_w_m2)
    return abs(irradiance - reference) / reference


def temperature_deviation_c(
    temperature_c, reference_temperature_c=DEFAULT_REFERENCE_TEMPERATURE_C
):
    """Return how far the sample temperature sits from reference, in kelvin."""
    temperature = _real("temperature_c", temperature_c, allow_negative=True)
    reference = _real(
        "reference_temperature_c", reference_temperature_c, allow_negative=True
    )
    return abs(temperature - reference)


def conditions_correctable(
    irradiance_w_m2,
    temperature_c,
    reference_irradiance_w_m2=DEFAULT_REFERENCE_IRRADIANCE_W_M2,
    reference_temperature_c=DEFAULT_REFERENCE_TEMPERATURE_C,
    max_irradiance_fraction=MAX_IRRADIANCE_DEVIATION_FRACTION,
    max_temperature_c=MAX_TEMPERATURE_DEVIATION_C,
):
    """Return True when the reading sits inside the correction window."""
    irradiance_limit = _real("max_irradiance_fraction", max_irradiance_fraction)
    temperature_limit = _real("max_temperature_c", max_temperature_c)
    irradiance_gap = irradiance_deviation_fraction(
        irradiance_w_m2, reference_irradiance_w_m2
    )
    temperature_gap = temperature_deviation_c(temperature_c, reference_temperature_c)
    irradiance_ok = irradiance_gap < irradiance_limit or math.isclose(
        irradiance_gap, irradiance_limit, rel_tol=0.0, abs_tol=CONDITION_TOLERANCE
    )
    temperature_ok = temperature_gap < temperature_limit or math.isclose(
        temperature_gap, temperature_limit, rel_tol=0.0, abs_tol=CONDITION_TOLERANCE
    )
    return irradiance_ok and temperature_ok


def response_ratio(sample_current_a, reference_current_a):
    """Return the sample current expressed against the reference current."""
    sample = _real("sample_current_a", sample_current_a)
    reference = _real("reference_current_a", reference_current_a)
    return sample / reference


def ratio_within_band(ratio, lower, upper):
    """Return True when the response ratio sits inside the declared band."""
    value = _real("ratio", ratio)
    low = _real("lower", lower)
    high = _real("upper", upper)
    if low > high:
        raise ValueError("band is inverted: lower %g above upper %g" % (low, high))
    above_low = value > low or math.isclose(
        value, low, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    below_high = value < high or math.isclose(
        value, high, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    return above_low and below_high


def validate_reference_device(reference):
    """Return (device, findings) for the reference the samples are read against."""
    data = _mapping(
        "reference",
        reference,
        ("id", "isc_a", "irradiance_w_m2", "temperature_c", "alpha_per_c",
         "calibration_age_days", "calibration_interval_days"),
    )
    device = {
        "id": _identifier("reference['id']", data["id"]),
        "isc_a": _real("reference['isc_a']", data["isc_a"]),
        "irradiance_w_m2": _real(
            "reference['irradiance_w_m2']", data["irradiance_w_m2"]
        ),
        "temperature_c": _real(
            "reference['temperature_c']", data["temperature_c"], allow_negative=True
        ),
        "alpha_per_c": _real(
            "reference['alpha_per_c']",
            data["alpha_per_c"],
            allow_zero=True,
            allow_negative=True,
        ),
        "calibration_age_days": _count(
            "reference['calibration_age_days']", data["calibration_age_days"]
        ),
        "calibration_interval_days": _count(
            "reference['calibration_interval_days']",
            data["calibration_interval_days"],
            allow_zero=False,
        ),
    }
    traceable = data.get("traceable", True)
    if not isinstance(traceable, bool):
        raise ValueError("reference['traceable'] must be a boolean")
    device["traceable"] = traceable
    findings = []
    if not traceable:
        findings.append(
            "reference device %s carries no traceable calibration, so every ratio "
            "taken against it is unsupported" % device["id"]
        )
    if device["calibration_age_days"] > device["calibration_interval_days"]:
        findings.append(
            "reference device %s was calibrated %d days ago, past its %d day "
            "interval"
            % (
                device["id"],
                device["calibration_age_days"],
                device["calibration_interval_days"],
            )
        )
    if not conditions_correctable(device["irradiance_w_m2"], device["temperature_c"]):
        findings.append(
            "reference device %s was read at %g W/m2 and %g C, outside the window "
            "the correction stays valid in"
            % (device["id"], device["irradiance_w_m2"], device["temperature_c"])
        )
    return device, findings


def corrected_reference_current_a(device):
    """Return the reference reading translated to reference conditions."""
    return correct_short_circuit_current_a(
        device["isc_a"],
        device["irradiance_w_m2"],
        device["temperature_c"],
        device["alpha_per_c"],
    )


def evaluate_sample(sample, reference_current_a, band):
    """Evaluate one test sample against the corrected reference current."""
    data = _mapping(
        "sample",
        sample,
        ("id", "isc_a", "irradiance_w_m2", "temperature_c", "alpha_per_c"),
    )
    sample_id = _identifier("sample['id']", data["id"])
    current = _real("sample['isc_a']", data["isc_a"])
    irradiance = _real("sample['irradiance_w_m2']", data["irradiance_w_m2"])
    temperature = _real(
        "sample['temperature_c']", data["temperature_c"], allow_negative=True
    )
    alpha = _real(
        "sample['alpha_per_c']",
        data["alpha_per_c"],
        allow_zero=True,
        allow_negative=True,
    )
    before_irradiation = data.get("before_irradiation", True)
    if not isinstance(before_irradiation, bool):
        raise ValueError("sample['before_irradiation'] must be a boolean")
    limits = _mapping("band", band, ("ratio_min", "ratio_max"))
    lower = _real("band['ratio_min']", limits["ratio_min"])
    upper = _real("band['ratio_max']", limits["ratio_max"])
    correctable = conditions_correctable(irradiance, temperature)
    corrected = correct_short_circuit_current_a(current, irradiance, temperature, alpha)
    ratio = response_ratio(corrected, reference_current_a)
    in_band = ratio_within_band(ratio, lower, upper)
    findings = []
    if not before_irradiation:
        findings.append(
            "sample %s was read after exposure started, so it carries no "
            "pre-irradiation baseline" % sample_id
        )
    if not correctable:
        findings.append(
            "sample %s was read at %g W/m2 and %g C, outside the window the "
            "correction stays valid in" % (sample_id, irradiance, temperature)
        )
    if not in_band:
        findings.append(
            "sample %s reads %.6g of the reference current, outside the declared "
            "[%g, %g] band" % (sample_id, ratio, lower, upper)
        )
    return {
        "id": sample_id,
        "corrected_isc_a": corrected,
        "response_ratio": ratio,
        "conditions_correctable": correctable,
        "before_irradiation": before_irradiation,
        "within_band": in_band,
        "conforms": not findings,
        "findings": findings,
    }


def assess_spectral_response_baseline(spec):
    """Run the full clause 6.4.3.5.2 pre-irradiation baseline assessment.

    spec keys: reference (the device every sample is read against), samples
    (non-empty sequence of test-sample readings), band (ratio_min, ratio_max),
    and optional planned_irradiation_ids naming the samples the campaign
    intends to expose.
    """
    data = _mapping("spec", spec, ("reference", "samples", "band"))
    device, findings = validate_reference_device(data["reference"])
    reference_current = corrected_reference_current_a(device)
    samples = data["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("spec['samples'] must be a non-empty sequence of readings")
    records = []
    seen = set()
    for sample in samples:
        record = evaluate_sample(sample, reference_current, data["band"])
        if record["id"] in seen:
            raise ValueError(
                "sample id '%s' appears twice in spec['samples']" % record["id"]
            )
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["findings"])
    planned = data.get("planned_irradiation_ids", ())
    if not isinstance(planned, (list, tuple)):
        raise ValueError("spec['planned_irradiation_ids'] must be a sequence")
    planned_ids = [
        _identifier("planned_irradiation_ids entry", entry) for entry in planned
    ]
    missing = sorted(set(planned_ids) - seen)
    for sample_id in missing:
        findings.append(
            "sample %s is planned for exposure but carries no pre-irradiation "
            "reading" % sample_id
        )
    in_band = sum(1 for record in records if record["within_band"])
    return {
        "reference": device,
        "reference_corrected_isc_a": reference_current,
        "sample_records": records,
        "samples_read": len(records),
        "samples_within_band": in_band,
        "samples_outside_band": len(records) - in_band,
        "baseline_missing_ids": missing,
        "findings": findings,
        "valid": not findings,
    }
