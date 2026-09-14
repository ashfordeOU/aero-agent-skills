#!/usr/bin/env python3
"""Boiling deionised water immersion of single-coated coverglasses.

Anchor: ECSS-E-ST-20-08C clause 8.7.10. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The test is crude on purpose. Coverglasses carrying a single coating are
dropped into deionised water held at a rolling boil and left there for at
least a stated time, then taken out and looked at. A coating whose adhesion
to the glass depends on a contaminated interface, an incomplete cure or a
porous layer does not survive that; one that is properly bonded comes out
unchanged. Four things decide whether a run is evidence at all.

The samples have to be single-coated. A coverglass with a coating on both
faces produces a result nobody can attribute: a loss seen after the bath
could have come from either face, and the clause's sample is the one with a
single coated face and a bare one to compare against.

The water has to be deionised. Tap or process water leaves dissolved salts
behind as it boils off, and those deposit on the coating and on the glass.
The film they leave is read as coating damage by any inspector, so the
bath's conductivity is the gate that runs before the immersion is believed.

The bath has to be boiling, and boiling is not a temperature. Water boils
at a hundred degrees only at sea-level pressure; a laboratory on a plateau,
or a day of low pressure, boils it several degrees lower. The threshold is
therefore derived from the declared ambient pressure by Clausius-Clapeyron,
not assumed.

The duration is hold time, not elapsed time. A bath log that runs for an
hour but spends the first twenty minutes climbing towards the boil has
delivered forty minutes of immersion, and the hold is taken by integrating
the log across the threshold with the crossings interpolated, not by
subtracting the first timestamp from the last.

The minimum duration, the conductivity limit, the sample count and the
acceptance fraction below are declared policy, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SAMPLE_NOT_SINGLE_COATED = "sample-not-single-coated"
SAMPLE_COUNT_SHORT = "sample-count-below-minimum"
WATER_NOT_DEIONISED = "bath-water-not-deionised"
BATH_NOT_BOILING = "bath-never-reached-boiling"
IMMERSION_TOO_SHORT = "immersion-hold-too-short"
COATING_DAMAGE_EXCEEDS_LIMIT = "coating-damage-exceeds-limit"
COATING_WITHSTANDS_IMMERSION = "coating-withstands-immersion"

# Reference point and latent heat used to place the boil threshold at the
# declared ambient pressure. Physical reference data, not a project choice.
WATER_REFERENCE_BOILING_K = 373.15
WATER_REFERENCE_PRESSURE_KPA = 101.325
WATER_VAPORISATION_ENTHALPY_J_PER_MOL = 40660.0
MOLAR_GAS_CONSTANT_J_PER_MOL_K = 8.314462618
KELVIN_AT_ZERO_CELSIUS = 273.15

DEFAULT_IMMERSION_POLICY = {
    "min_immersion_minutes": 30.0,
    "boil_margin_c": 1.0,
    "max_water_conductivity_us_per_cm": 1.0,
    "min_sample_count": 3,
    "max_coating_loss_fraction": 0.001,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_immersion_policy(policy):
    """Check an immersion policy states a duration, a bath and an acceptance."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_immersion_minutes", policy.get("min_immersion_minutes"))
    margin = _require_non_negative("boil_margin_c", policy.get("boil_margin_c"))
    if margin > 10.0:
        raise ValueError(
            "boil_margin_c %g admits a bath ten degrees below the boil as "
            "boiling" % margin
        )
    _require_positive(
        "max_water_conductivity_us_per_cm",
        policy.get("max_water_conductivity_us_per_cm"),
    )
    _require_count("min_sample_count", policy.get("min_sample_count"))
    loss = _require_non_negative(
        "max_coating_loss_fraction", policy.get("max_coating_loss_fraction")
    )
    if loss >= 1.0:
        raise ValueError(
            "max_coating_loss_fraction %g admits a coverglass with no coating "
            "left on it" % loss
        )
    return policy


def boiling_point_c(ambient_pressure_kpa):
    """Boiling point of water at the declared ambient pressure."""
    pressure = _require_positive("ambient_pressure_kpa", ambient_pressure_kpa)
    ratio = pressure / WATER_REFERENCE_PRESSURE_KPA
    inverse_kelvin = (1.0 / WATER_REFERENCE_BOILING_K) - (
        MOLAR_GAS_CONSTANT_J_PER_MOL_K / WATER_VAPORISATION_ENTHALPY_J_PER_MOL
    ) * math.log(ratio)
    if inverse_kelvin <= 0.0:
        raise ValueError(
            "ambient_pressure_kpa %g places the boil beyond the range this "
            "reference point supports" % pressure
        )
    return (1.0 / inverse_kelvin) - KELVIN_AT_ZERO_CELSIUS


def boil_threshold_c(ambient_pressure_kpa, boil_margin_c):
    """Temperature at or above which the bath counts as boiling."""
    boil = boiling_point_c(ambient_pressure_kpa)
    margin = _require_non_negative("boil_margin_c", boil_margin_c)
    return boil - margin


def validate_temperature_log(entries):
    """Check a bath log ascends in time and reads real temperatures."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("temperature log must be a sequence of readings")
    if len(entries) < 2:
        raise ValueError(
            "a log of %d reading(s) spans no time interval and cannot show a "
            "hold" % len(entries)
        )
    reduced = []
    previous = None
    for index, entry in enumerate(entries, start=1):
        if isinstance(entry, dict):
            elapsed = entry.get("elapsed_minutes")
            temperature = entry.get("temperature_c")
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            elapsed, temperature = entry
        else:
            raise ValueError(
                "log reading %d must be an (elapsed_minutes, temperature_c) "
                "pair or a mapping, got %r" % (index, entry)
            )
        elapsed = _require_non_negative("elapsed_minutes at reading %d" % index, elapsed)
        temperature = _require_number(
            "temperature_c at reading %d" % index, temperature
        )
        if temperature <= -KELVIN_AT_ZERO_CELSIUS:
            raise ValueError(
                "temperature %g C at reading %d is at or below absolute zero"
                % (temperature, index)
            )
        if previous is not None and not elapsed > previous:
            raise ValueError(
                "log times must strictly ascend; reading %d at %g min does not "
                "follow %g min" % (index, elapsed, previous)
            )
        previous = elapsed
        reduced.append((elapsed, temperature))
    return tuple(reduced)


def hold_time_minutes(entries, threshold_c):
    """Minutes the bath actually spent at or above the threshold."""
    readings = validate_temperature_log(entries)
    level = _require_number("threshold_c", threshold_c)
    held = 0.0
    for index in range(len(readings) - 1):
        start_time, start_temp = readings[index]
        end_time, end_temp = readings[index + 1]
        span = end_time - start_time
        start_hot = _at_least(start_temp, level)
        end_hot = _at_least(end_temp, level)
        if start_hot and end_hot:
            held += span
            continue
        if not start_hot and not end_hot:
            continue
        gradient = end_temp - start_temp
        if gradient == 0.0:
            continue
        fraction = (level - start_temp) / gradient
        if fraction < 0.0:
            fraction = 0.0
        elif fraction > 1.0:
            fraction = 1.0
        if end_hot:
            held += span * (1.0 - fraction)
        else:
            held += span * fraction
    return held


def peak_temperature_c(entries):
    """Hottest reading in the bath log."""
    readings = validate_temperature_log(entries)
    return max(temperature for _elapsed, temperature in readings)


def water_is_deionised(conductivity_us_per_cm, limit_us_per_cm):
    """True when the bath water is pure enough to leave no residue behind."""
    measured = _require_non_negative(
        "conductivity_us_per_cm", conductivity_us_per_cm
    )
    limit = _require_positive("limit_us_per_cm", limit_us_per_cm)
    return _at_most(measured, limit)


def validate_sample(sample, index=1):
    """Check one immersion sample is the single-coated article the clause takes."""
    if not isinstance(sample, dict):
        raise ValueError("sample %d must be a mapping, got %r" % (index, sample))
    _require_label("sample %d sample_id" % index, sample.get("sample_id"))
    faces = sample.get("coated_faces")
    if not isinstance(faces, int) or isinstance(faces, bool) or faces < 0:
        raise ValueError(
            "sample %d coated_faces must be a whole number of faces, got %r"
            % (index, faces)
        )
    if faces > 2:
        raise ValueError(
            "sample %d declares %d coated faces; a coverglass has two"
            % (index, faces)
        )
    coated_area = _require_positive(
        "sample %d coated_area_mm2" % index, sample.get("coated_area_mm2")
    )
    affected = _require_non_negative(
        "sample %d affected_area_mm2" % index, sample.get("affected_area_mm2")
    )
    if affected > coated_area:
        raise ValueError(
            "sample %d reports %g mm2 affected on a %g mm2 coated face"
            % (index, affected, coated_area)
        )
    return sample


def is_single_coated(sample, index=1):
    """True when exactly one face of the coverglass carries a coating."""
    validate_sample(sample, index)
    return sample["coated_faces"] == 1


def coating_loss_fraction(sample, index=1):
    """Share of the coated face that did not survive the immersion."""
    validate_sample(sample, index)
    return float(sample["affected_area_mm2"]) / float(sample["coated_area_mm2"])


def worst_coating_loss_fraction(samples):
    """The largest loss fraction across the immersed batch."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of sample records")
    return max(
        coating_loss_fraction(sample, index)
        for index, sample in enumerate(samples, start=1)
    )


def assess_boiling_water_test(case, policy=DEFAULT_IMMERSION_POLICY):
    """Full clause 8.7.10 judgement for one boiling-water immersion run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_immersion_policy(policy)

    findings = []
    advisories = []
    result = {
        "sample_count": None,
        "single_coated_samples": None,
        "water_conductivity_us_per_cm": None,
        "ambient_pressure_kpa": None,
        "boiling_point_c": None,
        "boil_threshold_c": None,
        "peak_temperature_c": None,
        "hold_minutes": None,
        "required_hold_minutes": float(policy["min_immersion_minutes"]),
        "worst_coating_loss_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    samples = case.get("samples")
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError(
            "case is missing a non-empty samples list; an absent batch is not "
            "an empty one"
        )
    for index, sample in enumerate(samples, start=1):
        validate_sample(sample, index)
    result["sample_count"] = len(samples)
    single = [
        sample
        for index, sample in enumerate(samples, start=1)
        if is_single_coated(sample, index)
    ]
    result["single_coated_samples"] = len(single)
    if len(single) != len(samples):
        findings.append(
            "%d of %d samples carry a coating on other than exactly one face; "
            "a loss found on a two-face sample cannot be attributed"
            % (len(samples) - len(single), len(samples))
        )
        result["verdict"] = SAMPLE_NOT_SINGLE_COATED
        return result

    minimum_samples = int(policy["min_sample_count"])
    if len(samples) < minimum_samples:
        findings.append(
            "the batch holds %d samples against a required %d; one survivor is "
            "not a population" % (len(samples), minimum_samples)
        )
        result["verdict"] = SAMPLE_COUNT_SHORT
        return result

    conductivity = _require_non_negative(
        "water_conductivity_us_per_cm", case.get("water_conductivity_us_per_cm")
    )
    result["water_conductivity_us_per_cm"] = conductivity
    conductivity_limit = float(policy["max_water_conductivity_us_per_cm"])
    if not water_is_deionised(conductivity, conductivity_limit):
        findings.append(
            "the bath reads %g uS/cm against a %g uS/cm limit; the salts it "
            "leaves behind are read as coating damage"
            % (conductivity, conductivity_limit)
        )
        result["verdict"] = WATER_NOT_DEIONISED
        return result

    pressure = _require_positive(
        "ambient_pressure_kpa", case.get("ambient_pressure_kpa")
    )
    result["ambient_pressure_kpa"] = pressure
    result["boiling_point_c"] = boiling_point_c(pressure)
    threshold = boil_threshold_c(pressure, float(policy["boil_margin_c"]))
    result["boil_threshold_c"] = threshold

    log = case.get("temperature_log")
    validate_temperature_log(log)
    result["peak_temperature_c"] = peak_temperature_c(log)
    if not _at_least(result["peak_temperature_c"], threshold):
        findings.append(
            "the bath peaked at %.2f C against a boil threshold of %.2f C at "
            "%g kPa; the samples were soaked, not boiled"
            % (result["peak_temperature_c"], threshold, pressure)
        )
        result["verdict"] = BATH_NOT_BOILING
        return result

    result["hold_minutes"] = hold_time_minutes(log, threshold)
    required = float(policy["min_immersion_minutes"])
    if not _at_least(result["hold_minutes"], required):
        findings.append(
            "the bath held at or above %.2f C for %.2f min against a required "
            "%.2f min; the ramp to the boil is not immersion"
            % (threshold, result["hold_minutes"], required)
        )
        result["verdict"] = IMMERSION_TOO_SHORT
        return result

    worst = worst_coating_loss_fraction(samples)
    result["worst_coating_loss_fraction"] = worst
    loss_limit = float(policy["max_coating_loss_fraction"])
    if not _at_most(worst, loss_limit):
        findings.append(
            "the worst sample lost %.5f of its coated face against an "
            "acceptance of %.5f" % (worst, loss_limit)
        )
        result["verdict"] = COATING_DAMAGE_EXCEEDS_LIMIT
        return result

    if result["hold_minutes"] > required * 3.0:
        advisories.append(
            "the hold ran well past the required minimum; record the actual "
            "duration, because a longer immersion is a different exposure from "
            "the one the acceptance was set against"
        )
    result["verdict"] = COATING_WITHSTANDS_IMMERSION
    return result
