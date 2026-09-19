"""Burn-in of hybrid microcircuits to precipitate early-life failures.

Anchor: ECSS-Q-ST-60-05C clause 10.3.9 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Burn-in is a powered exposure, not a bake. The point is to run the
   circuit hot and biased so the weak elements of the batch fail here
   rather than in flight; an unpowered oven soak of the same length has
   not applied the mechanism the screen is named for.
2. Temperature buys time, and the rate at which it does so is the
   activation energy of the mechanism. A shorter exposure at a higher
   temperature is admissible when the two are equivalent by the
   Arrhenius relation, and the equivalence has to be computed against a
   stated reference condition rather than asserted.
3. A stress temperature that is not above the use temperature
   accelerates nothing. The equivalence arithmetic still returns a
   number in that case, and the number is at or below unity, which is
   the finding rather than the result.
4. The temperature that matters is at the junction, not in the oven.
   Bias dissipates power, the power raises the die above ambient
   through the thermal resistance of the package, and a schedule that
   looks safe in ambient terms can sit above the maximum rating on the
   die.
5. A unit is graded on how far it moved, not only on where it ended.
   A device still inside its specification limits but well outside its
   allowed drift has told the batch something, and the reading has to
   be taken inside the window before recovery hides it.
6. The lot is graded too. Burn-in exists to expose a weak population,
   so a reject fraction above the allowable for the flow means the
   population is the problem and the survivors are not made good by
   having survived.

Stdlib only, offline, deterministic.
"""

import math

# Boltzmann constant in electronvolts per kelvin.
BOLTZMANN_EV_PER_K = 8.617333262e-5

ABSOLUTE_ZERO_C = -273.15

# Activation energies in electronvolts for the mechanisms burn-in is run
# against. A low-energy mechanism is accelerated far less by the same
# temperature step than a high-energy one.
ACTIVATION_ENERGY_EV = {
    "oxide-defect": 0.30,
    "ionic-contamination": 0.70,
    "wire-bond-intermetallic": 1.00,
    "electromigration": 0.90,
    "die-attach-void-growth": 0.80,
}

# Reference burn-in condition the equivalence is computed against.
REFERENCE_STRESS_TEMP_C = 125.0
REFERENCE_DURATION_H = 160.0

# Highest die temperature the exposure may reach.
MAX_JUNCTION_TEMP_C = 175.0

# Post-exposure measurement window, in hours after removal.
MEASUREMENT_WINDOW_H = 96.0

# Drift a surviving unit may carry between its pre and post readings.
DELTA_DRIFT_LIMIT = 0.10

# Reject fraction a lot may carry before the lot itself is refused.
PERCENT_DEFECTIVE_ALLOWABLE = {
    "class-1": 0.05,
    "class-2": 0.10,
    "class-3": 0.20,
}

COMPARISON_TOLERANCE = 1.0e-12

PASS = "unit-survived"
FAIL = "unit-failed"


def _number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _positive_number(label, value):
    value = _number(label, value)
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_number(label, value):
    value = _number(label, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def to_kelvin(label, celsius):
    """Absolute temperature behind a celsius reading."""
    value = _number(label, celsius)
    if value <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return value - ABSOLUTE_ZERO_C


def activation_energy(mechanism):
    """Activation energy carried by a failure mechanism."""
    if mechanism not in ACTIVATION_ENERGY_EV:
        raise ValueError(
            "unknown mechanism %r (expected one of %s)"
            % (mechanism, ", ".join(sorted(ACTIVATION_ENERGY_EV)))
        )
    return ACTIVATION_ENERGY_EV[mechanism]


def arrhenius_acceleration_factor(mechanism, use_temp_c, stress_temp_c):
    """How much faster the mechanism runs at the stress temperature."""
    energy = activation_energy(mechanism)
    use_k = to_kelvin("use_temp_c", use_temp_c)
    stress_k = to_kelvin("stress_temp_c", stress_temp_c)
    return math.exp((energy / BOLTZMANN_EV_PER_K) * (1.0 / use_k - 1.0 / stress_k))


def equivalence_factor(mechanism, stress_temp_c, reference_temp_c=REFERENCE_STRESS_TEMP_C):
    """Reference hours bought by one hour at the stress temperature."""
    energy = activation_energy(mechanism)
    reference_k = to_kelvin("reference_temp_c", reference_temp_c)
    stress_k = to_kelvin("stress_temp_c", stress_temp_c)
    return math.exp(
        (energy / BOLTZMANN_EV_PER_K) * (1.0 / reference_k - 1.0 / stress_k)
    )


def equivalent_reference_hours(
    duration_h, mechanism, stress_temp_c, reference_temp_c=REFERENCE_STRESS_TEMP_C
):
    """Hours at the reference condition an exposure is worth."""
    duration = _positive_number("duration_h", duration_h)
    return duration * equivalence_factor(mechanism, stress_temp_c, reference_temp_c)


def required_duration_h(
    mechanism,
    stress_temp_c,
    reference_temp_c=REFERENCE_STRESS_TEMP_C,
    reference_hours=REFERENCE_DURATION_H,
):
    """Exposure at this temperature that matches the reference condition."""
    hours = _positive_number("reference_hours", reference_hours)
    return hours / equivalence_factor(mechanism, stress_temp_c, reference_temp_c)


def junction_temperature_c(ambient_temp_c, dissipated_power_w, theta_ja_c_per_w):
    """Die temperature the bias produces above the oven ambient."""
    ambient = _number("ambient_temp_c", ambient_temp_c)
    power = _non_negative_number("dissipated_power_w", dissipated_power_w)
    theta = _non_negative_number("theta_ja_c_per_w", theta_ja_c_per_w)
    to_kelvin("ambient_temp_c", ambient)
    return ambient + power * theta


def delta_drift_fraction(pre_reading, post_reading):
    """Fractional movement of a parameter across the exposure."""
    pre = _number("pre_reading", pre_reading)
    post = _number("post_reading", post_reading)
    if pre == 0.0:
        raise ValueError("pre_reading must be non-zero to form a drift fraction")
    return abs(post - pre) / abs(pre)


def percent_defective_allowable(flow_class):
    """Reject fraction a lot of this flow class may carry."""
    if flow_class not in PERCENT_DEFECTIVE_ALLOWABLE:
        raise ValueError(
            "unknown flow_class %r (expected one of %s)"
            % (flow_class, ", ".join(sorted(PERCENT_DEFECTIVE_ALLOWABLE)))
        )
    return PERCENT_DEFECTIVE_ALLOWABLE[flow_class]


def validate_burn_in(record):
    """Validate one burn-in record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    mechanism = record.get("mechanism")
    activation_energy(mechanism)
    flow_class = record.get("flow_class", "class-2")
    percent_defective_allowable(flow_class)
    return {
        "id": unit_id,
        "mechanism": mechanism,
        "flow_class": flow_class,
        "use_temp_c": _number("unit %s use_temp_c" % unit_id, record.get("use_temp_c")),
        "ambient_temp_c": _number(
            "unit %s ambient_temp_c" % unit_id, record.get("ambient_temp_c")
        ),
        "duration_h": _positive_number(
            "unit %s duration_h" % unit_id, record.get("duration_h")
        ),
        "dissipated_power_w": _non_negative_number(
            "unit %s dissipated_power_w" % unit_id,
            record.get("dissipated_power_w", 0.0),
        ),
        "theta_ja_c_per_w": _non_negative_number(
            "unit %s theta_ja_c_per_w" % unit_id, record.get("theta_ja_c_per_w")
        ),
        "bias_applied": _boolean(
            "unit %s bias_applied" % unit_id, record.get("bias_applied", True)
        ),
        "measurement_delay_h": _non_negative_number(
            "unit %s measurement_delay_h" % unit_id,
            record.get("measurement_delay_h", 0.0),
        ),
        "pre_reading": _number(
            "unit %s pre_reading" % unit_id, record.get("pre_reading")
        ),
        "post_reading": _number(
            "unit %s post_reading" % unit_id, record.get("post_reading")
        ),
        "reduced_duration_approved": _boolean(
            "unit %s reduced_duration_approved" % unit_id,
            record.get("reduced_duration_approved", False),
        ),
        "catastrophic_failure": _boolean(
            "unit %s catastrophic_failure" % unit_id,
            record.get("catastrophic_failure", False),
        ),
    }


def check_schedule(record):
    """Findings about the temperature and duration that were run."""
    norm = validate_burn_in(record)
    findings = []
    if arrhenius_acceleration_factor(
        norm["mechanism"], norm["use_temp_c"], norm["ambient_temp_c"]
    ) <= 1.0 + COMPARISON_TOLERANCE:
        findings.append("stress-temperature-does-not-accelerate-the-mechanism")
    owed = required_duration_h(norm["mechanism"], norm["ambient_temp_c"])
    if norm["duration_h"] < owed * (1.0 - COMPARISON_TOLERANCE):
        findings.append("exposure-below-the-reference-equivalent-duration")
    elif norm["duration_h"] < REFERENCE_DURATION_H * (
        1.0 - COMPARISON_TOLERANCE
    ) and not norm["reduced_duration_approved"]:
        findings.append("reduced-duration-equivalence-without-an-approval")
    return findings


def check_thermal(record):
    """Findings about what the bias did to the die temperature."""
    norm = validate_burn_in(record)
    findings = []
    if not norm["bias_applied"]:
        findings.append("bias-not-applied-during-the-exposure")
    junction = junction_temperature_c(
        norm["ambient_temp_c"], norm["dissipated_power_w"], norm["theta_ja_c_per_w"]
    )
    if junction > MAX_JUNCTION_TEMP_C + COMPARISON_TOLERANCE:
        findings.append("junction-temperature-above-the-maximum-rating")
    return findings


def check_measurement(record):
    """Findings about the reading taken after the exposure."""
    norm = validate_burn_in(record)
    findings = []
    if norm["measurement_delay_h"] > MEASUREMENT_WINDOW_H + COMPARISON_TOLERANCE:
        findings.append("post-exposure-measurement-outside-the-window")
    drift = delta_drift_fraction(norm["pre_reading"], norm["post_reading"])
    if drift > DELTA_DRIFT_LIMIT + COMPARISON_TOLERANCE:
        findings.append("delta-drift-above-the-limit")
    if norm["catastrophic_failure"]:
        findings.append("unit-failed-during-the-exposure")
    return findings


def assess_burn_in(record):
    """Assess one burn-in exposure against clause 10.3.9."""
    norm = validate_burn_in(record)
    findings = list(check_schedule(norm))
    findings.extend(check_thermal(norm))
    findings.extend(check_measurement(norm))
    return {
        "id": norm["id"],
        "mechanism": norm["mechanism"],
        "activation_energy_ev": activation_energy(norm["mechanism"]),
        "acceleration_factor": arrhenius_acceleration_factor(
            norm["mechanism"], norm["use_temp_c"], norm["ambient_temp_c"]
        ),
        "equivalent_reference_hours": equivalent_reference_hours(
            norm["duration_h"], norm["mechanism"], norm["ambient_temp_c"]
        ),
        "required_duration_h": required_duration_h(
            norm["mechanism"], norm["ambient_temp_c"]
        ),
        "junction_temperature_c": junction_temperature_c(
            norm["ambient_temp_c"],
            norm["dissipated_power_w"],
            norm["theta_ja_c_per_w"],
        ),
        "delta_drift_fraction": delta_drift_fraction(
            norm["pre_reading"], norm["post_reading"]
        ),
        "findings": findings,
        "disposition": FAIL if findings else PASS,
    }


def assess_burn_in_lot(records, flow_class="class-2"):
    """Run the clause 10.3.9 exposure over a lot and grade the lot."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    allowable = percent_defective_allowable(flow_class)
    results = []
    seen = set()
    for record in records:
        result = assess_burn_in(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    failed = [r["id"] for r in results if r["disposition"] == FAIL]
    fraction = len(failed) / len(results)
    return {
        "units": results,
        "surviving_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "failed_ids": failed,
        "flow_class": flow_class,
        "reject_fraction": fraction,
        "percent_defective_allowable": allowable,
        "lot_accepted": fraction <= allowable + COMPARISON_TOLERANCE,
    }


def schedule_options(mechanism, temperatures_c):
    """Durations that each match the reference condition, by temperature."""
    if not isinstance(temperatures_c, (list, tuple)) or not temperatures_c:
        raise ValueError("temperatures_c must be a non-empty sequence")
    options = []
    for temperature in temperatures_c:
        options.append(
            (float(temperature), required_duration_h(mechanism, temperature))
        )
    return options
