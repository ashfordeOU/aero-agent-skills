#!/usr/bin/env python3
"""Freedom from corona and gas discharge at maximum operating power.

Anchor: ECSS-E-ST-20C clause 7.3.3.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

The clause asks for one thing and asks it over the whole mission: the
radio-frequency chain has to stay free of corona and gas discharge while it
carries its maximum operating power, everywhere in the declared environment
envelope -- not only on the ground and not only in vacuum.

Three ideas carry the module:

* The stressing power is the peak envelope power of the carrier set the item
  actually carries, raised for the mismatch it really sees and for the
  tolerance stack of the chain, not the nominal single-carrier rating.
* Gas breakdown across a gap follows a similarity law in the product of
  pressure and gap length. Inside a declared pressure band the worst case is
  therefore the pressure that sits closest to the minimum of that curve, which
  is usually an interior point of the band and not one of its edges.
* An envelope is only covered if every declared phase of the mission carries
  an evaluated pressure band. A phase left out is a finding in its own right.

Stdlib only, offline, deterministic.
"""

import math

# Paschen coefficients converted to SI: A in 1/(Pa*m), B in V/(Pa*m).
GAS_COEFFICIENTS = {
    "air": {"a_per_pa_m": 11.25, "b_v_per_pa_m": 273.75},
    "nitrogen": {"a_per_pa_m": 9.00, "b_v_per_pa_m": 256.50},
    "argon": {"a_per_pa_m": 8.63, "b_v_per_pa_m": 132.00},
    "helium": {"a_per_pa_m": 2.25, "b_v_per_pa_m": 25.50},
}

DEFAULT_SECONDARY_EMISSION = 0.01

# Mission phases recognized by the clause 7.3.3.1 envelope, and the ambient
# regime each one sits in.
ENVIRONMENT_PHASES = {
    "ground-ambient": "dense-gas",
    "pre-launch-purge": "dense-gas",
    "repressurised-module": "dense-gas",
    "ascent-venting": "transitional",
    "early-orbit-outgassing": "transitional",
    "planetary-atmosphere": "transitional",
    "on-station-vacuum": "vacuum",
    "deep-space-cruise": "vacuum",
}

# The envelope is not "full" until these four phases are on record.
REQUIRED_ENVELOPE_PHASES = (
    "ground-ambient",
    "ascent-venting",
    "early-orbit-outgassing",
    "on-station-vacuum",
)

# Representation tolerance only. It absorbs floating-point round-off on an
# exactly-compliant comparison; it never relaxes an engineering limit.
COMPARISON_TOLERANCE = 1e-9


def _meets(value, limit):
    """True when value is at or above limit, ULP noise absorbed."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=1e-12, abs_tol=COMPARISON_TOLERANCE)


def gas_coefficients(gas):
    """Return the similarity-law coefficients for a recognized fill gas."""
    if not isinstance(gas, str) or not gas.strip():
        raise ValueError("gas must be a non-empty string")
    key = gas.strip().lower()
    if key not in GAS_COEFFICIENTS:
        raise ValueError("unrecognized gas %r" % (gas,))
    return dict(GAS_COEFFICIENTS[key])


def categorize_environment_phase(phase):
    """Map a declared mission phase onto its ambient-pressure regime."""
    if not isinstance(phase, str) or not phase.strip():
        raise ValueError("phase must be a non-empty string")
    key = phase.strip().lower()
    if key not in ENVIRONMENT_PHASES:
        raise ValueError("unrecognized environment phase %r" % (phase,))
    return ENVIRONMENT_PHASES[key]


def similarity_minimum(gas="air", secondary_emission=DEFAULT_SECONDARY_EMISSION):
    """Product-of-pressure-and-gap at which breakdown is easiest, and the
    breakdown voltage there.

    Returns (pd_min_pa_m, voltage_min_v).
    """
    if secondary_emission <= 0.0:
        raise ValueError("secondary_emission must be > 0")
    coeff = gas_coefficients(gas)
    seed = math.log(1.0 + 1.0 / secondary_emission)
    pd_min = math.e * seed / coeff["a_per_pa_m"]
    return pd_min, coeff["b_v_per_pa_m"] * pd_min


def breakdown_voltage_v(
    pressure_pa, gap_m, gas="air", secondary_emission=DEFAULT_SECONDARY_EMISSION
):
    """Breakdown voltage of a uniform gap from the pressure-gap product.

    Returns math.inf on the long-mean-free-path branch, where too few
    ionising collisions occur for an avalanche to build and the gap has no
    finite breakdown voltage at all.
    """
    if pressure_pa <= 0.0:
        raise ValueError("pressure_pa must be > 0")
    if gap_m <= 0.0:
        raise ValueError("gap_m must be > 0")
    if secondary_emission <= 0.0:
        raise ValueError("secondary_emission must be > 0")
    coeff = gas_coefficients(gas)
    product = pressure_pa * gap_m
    seed = math.log(1.0 + 1.0 / secondary_emission)
    denominator = math.log(coeff["a_per_pa_m"] * product / seed)
    if denominator <= 0.0:
        return math.inf
    return coeff["b_v_per_pa_m"] * product / denominator


def worst_case_pressure_pa(
    low_pa, high_pa, gap_m, gas="air", secondary_emission=DEFAULT_SECONDARY_EMISSION
):
    """Pressure inside a declared band at which the gap is weakest.

    The breakdown curve falls on one side of its minimum and rises on the
    other, so the worst case is the minimum itself when the band contains it,
    and the nearer edge otherwise.
    """
    if low_pa <= 0.0:
        raise ValueError("low_pa must be > 0")
    if high_pa < low_pa:
        raise ValueError("high_pa must be >= low_pa")
    if gap_m <= 0.0:
        raise ValueError("gap_m must be > 0")
    pd_min, _ = similarity_minimum(gas, secondary_emission)
    pressure_at_minimum = pd_min / gap_m
    if pressure_at_minimum < low_pa:
        return low_pa
    if pressure_at_minimum > high_pa:
        return high_pa
    return pressure_at_minimum


def peak_envelope_power_w(carrier_powers_w, vswr=1.0, tolerance_db=0.0):
    """Worst-case peak envelope power seen by the item.

    Carriers are taken to add coherently at the worst instant, so the peak
    envelope is the square of the sum of the carrier amplitudes. The mismatch
    uplift is the standing-wave factor of the declared vswr, and the tolerance
    stack of the chain is applied on top in decibels.
    """
    if not isinstance(carrier_powers_w, (list, tuple)) or not carrier_powers_w:
        raise ValueError("carrier_powers_w must be a non-empty sequence")
    for power in carrier_powers_w:
        if power <= 0.0:
            raise ValueError("every carrier power must be > 0")
    if vswr < 1.0:
        raise ValueError("vswr must be >= 1.0")
    if tolerance_db < 0.0:
        raise ValueError("tolerance_db must be >= 0")
    amplitude_sum = sum(math.sqrt(power) for power in carrier_powers_w)
    coherent_peak = amplitude_sum ** 2
    reflection = (vswr - 1.0) / (vswr + 1.0)
    mismatch_uplift = (1.0 + reflection) ** 2
    return coherent_peak * mismatch_uplift * 10.0 ** (tolerance_db / 10.0)


def discharge_onset_power_w(
    reference_onset_w,
    reference_pressure_pa,
    reference_gap_m,
    pressure_pa,
    gap_m,
    gas="air",
    secondary_emission=DEFAULT_SECONDARY_EMISSION,
):
    """Scale a measured onset power to another pressure and gap.

    Onset power follows the square of the breakdown voltage, so the measured
    point is transported by the ratio of the two breakdown voltages squared.
    A gap with no finite breakdown voltage returns an infinite onset power:
    the gap cannot strike a discharge there.
    """
    if reference_onset_w <= 0.0:
        raise ValueError("reference_onset_w must be > 0")
    reference_voltage = breakdown_voltage_v(
        reference_pressure_pa, reference_gap_m, gas, secondary_emission
    )
    if math.isinf(reference_voltage):
        raise ValueError(
            "reference point sits on the no-breakdown branch; it cannot anchor a scaling"
        )
    voltage = breakdown_voltage_v(pressure_pa, gap_m, gas, secondary_emission)
    if math.isinf(voltage):
        return math.inf
    return reference_onset_w * (voltage / reference_voltage) ** 2


def discharge_margin_db(onset_power_w, applied_power_w):
    """Headroom in decibels between onset power and applied power."""
    if applied_power_w <= 0.0:
        raise ValueError("applied_power_w must be > 0")
    if onset_power_w <= 0.0:
        raise ValueError("onset_power_w must be > 0")
    if math.isinf(onset_power_w):
        return math.inf
    return 10.0 * math.log10(onset_power_w / applied_power_w)


def evaluate_phase_freedom(item, phase_record, required_margin_db):
    """Evaluate one mission phase for one radio-frequency chain item."""
    if required_margin_db < 0.0:
        raise ValueError("required_margin_db must be >= 0")
    for key in ("gap_m", "reference_onset_w", "reference_pressure_pa", "reference_gap_m"):
        if key not in item:
            raise ValueError("item missing required key %r" % (key,))
    for key in ("phase", "pressure_low_pa", "pressure_high_pa"):
        if key not in phase_record:
            raise ValueError("phase_record missing required key %r" % (key,))

    gas = item.get("gas", "air")
    secondary = item.get("secondary_emission", DEFAULT_SECONDARY_EMISSION)
    regime = categorize_environment_phase(phase_record["phase"])
    worst_pressure = worst_case_pressure_pa(
        phase_record["pressure_low_pa"],
        phase_record["pressure_high_pa"],
        item["gap_m"],
        gas,
        secondary,
    )
    applied = peak_envelope_power_w(
        item.get("carrier_powers_w", [item.get("nominal_power_w", 0.0)]),
        item.get("vswr", 1.0),
        item.get("tolerance_db", 0.0),
    )
    onset = discharge_onset_power_w(
        item["reference_onset_w"],
        item["reference_pressure_pa"],
        item["reference_gap_m"],
        worst_pressure,
        item["gap_m"],
        gas,
        secondary,
    )
    margin = discharge_margin_db(onset, applied)
    compliant = _meets(margin, required_margin_db)
    findings = []
    if not compliant:
        findings.append(
            "%s: discharge margin %.2f dB below the required %.2f dB at %.3f Pa"
            % (phase_record["phase"], margin, required_margin_db, worst_pressure)
        )
    return {
        "phase": phase_record["phase"],
        "regime": regime,
        "worst_case_pressure_pa": worst_pressure,
        "applied_power_w": applied,
        "onset_power_w": onset,
        "margin_db": margin,
        "compliant": compliant,
        "findings": findings,
    }


def envelope_coverage(declared_phases, required_phases=REQUIRED_ENVELOPE_PHASES):
    """Report the declared phases missing from the required envelope."""
    if not isinstance(declared_phases, (list, tuple)):
        raise ValueError("declared_phases must be a sequence")
    seen = []
    for phase in declared_phases:
        categorize_environment_phase(phase)
        key = phase.strip().lower()
        if key in seen:
            raise ValueError("phase %r declared more than once" % (phase,))
        seen.append(key)
    missing = [phase for phase in required_phases if phase not in seen]
    return {"declared": seen, "missing": missing, "complete": not missing}


def assess_gas_discharge_freedom(
    item,
    phase_records,
    required_margin_db,
    required_phases=REQUIRED_ENVELOPE_PHASES,
):
    """Full clause 7.3.3.1 assessment for one radio-frequency chain item."""
    if not isinstance(phase_records, (list, tuple)) or not phase_records:
        raise ValueError("phase_records must be a non-empty sequence")
    coverage = envelope_coverage(
        [record["phase"] for record in phase_records], required_phases
    )
    evaluations = [
        evaluate_phase_freedom(item, record, required_margin_db)
        for record in phase_records
    ]
    findings = []
    for evaluation in evaluations:
        findings.extend(evaluation["findings"])
    for phase in coverage["missing"]:
        findings.append("envelope incomplete: no pressure band declared for %s" % phase)
    finite = [
        evaluation["margin_db"]
        for evaluation in evaluations
        if not math.isinf(evaluation["margin_db"])
    ]
    return {
        "item": item.get("id", "unnamed-item"),
        "phases": evaluations,
        "coverage": coverage,
        "worst_margin_db": min(finite) if finite else math.inf,
        "findings": findings,
        "compliant": not findings,
    }
