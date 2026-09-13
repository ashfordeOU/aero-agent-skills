#!/usr/bin/env python3
"""Running a one megaelectronvolt electron irradiation on cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.11.2 (exposing photovoltaic cell
assemblies to a one megaelectronvolt electron fluence under the referenced
methodology). Paraphrased into an implementable procedure; no standard text
is reproduced.

Trapped-electron damage is reduced to a single equivalent particle: a one
megaelectronvolt electron, delivered as a fluence in electrons per square
centimetre. The run therefore has two independent obligations. The beam has
to be the beam the methodology names -- the nominal energy, a flux inside
the rate window the reference method allows, and a plane uniform enough
that every sample on the holder sees the same exposure. And the exposure
has to be the exposure the plan asked for: flux integrated over every
irradiated segment, reconciled against the planned fluence point, with the
electrical characterisation taken before and after so the degradation the
fluence caused is actually measurable.

The degradation itself follows a semi-empirical logarithmic law: the
remaining power factor falls as the logarithm of the accumulated fluence
above a reference fluence, so a decade of extra fluence costs a fixed
increment of output rather than a fixed fraction. That is why an
under-delivered fluence point is not a small error -- it lands the article
on a different point of a log curve than the one the mission needs.

Flux matters on its own account. Too low and the run never finishes; too
high and the damage is delivered faster than the assembly can respond to,
so short-term annealing is suppressed and the measured degradation is not
the degradation the mission accumulates over years.

The energy, flux window, uniformity allowance, temperature window and
pressure ceiling below are a declared policy, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Characterisation point -> what the electrical measurement at it supplies.
CHARACTERISATION_POINTS = {
    "pre-irradiation-iv": "undamaged-reference-output",
    "intermediate-fluence-iv": "degradation-curve-intermediate-point",
    "post-irradiation-iv": "end-of-fluence-remaining-output",
    "post-anneal-iv": "short-term-anneal-recovery-output",
}

RECOGNISED_POINTS = tuple(sorted(CHARACTERISATION_POINTS))

MANDATORY_POINTS = ("pre-irradiation-iv", "post-irradiation-iv")

RUN_CONDITIONS_VIOLATED = "run-conditions-violated"
EXPOSURE_FLUENCE_SHORTFALL = "exposure-fluence-shortfall"
CHARACTERISATION_INCOMPLETE = "characterisation-incomplete"
IRRADIATION_RUN_CONFORMS = "irradiation-run-conforms"

DEFAULT_IRRADIATION_POLICY = {
    "beam_energy_nominal_mev": 1.0,
    "beam_energy_tolerance_mev": 0.05,
    "min_flux_e_per_cm2_s": 1.0e9,
    "max_flux_e_per_cm2_s": 1.0e11,
    "max_plane_non_uniformity": 0.10,
    "min_sample_temperature_c": 20.0,
    "max_sample_temperature_c": 30.0,
    "max_chamber_pressure_pa": 1.0e-3,
    "fluence_tolerance_fraction": 0.10,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def validate_irradiation_policy(policy):
    """Check an irradiation-run policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("beam_energy_nominal_mev", policy.get("beam_energy_nominal_mev"))
    _require_positive(
        "beam_energy_tolerance_mev", policy.get("beam_energy_tolerance_mev")
    )
    low = _require_positive("min_flux_e_per_cm2_s", policy.get("min_flux_e_per_cm2_s"))
    high = _require_positive("max_flux_e_per_cm2_s", policy.get("max_flux_e_per_cm2_s"))
    if high <= low:
        raise ValueError(
            "max_flux_e_per_cm2_s %g must be above min_flux_e_per_cm2_s %g"
            % (high, low)
        )
    _require_positive(
        "max_plane_non_uniformity", policy.get("max_plane_non_uniformity")
    )
    cold = _require_number(
        "min_sample_temperature_c", policy.get("min_sample_temperature_c")
    )
    hot = _require_number(
        "max_sample_temperature_c", policy.get("max_sample_temperature_c")
    )
    if hot <= cold:
        raise ValueError(
            "max_sample_temperature_c %g must be above min_sample_temperature_c %g"
            % (hot, cold)
        )
    _require_positive("max_chamber_pressure_pa", policy.get("max_chamber_pressure_pa"))
    _require_non_negative(
        "fluence_tolerance_fraction", policy.get("fluence_tolerance_fraction")
    )
    return policy


def accumulated_fluence_e_per_cm2(flux_e_per_cm2_s, duration_s):
    """Fluence a single irradiated segment delivers: flux integrated over time."""
    flux = _require_positive("flux_e_per_cm2_s", flux_e_per_cm2_s)
    duration = _require_positive("duration_s", duration_s)
    return flux * duration


def exposure_duration_s(target_fluence_e_per_cm2, flux_e_per_cm2_s):
    """Beam time a target fluence needs at a given flux."""
    target = _require_positive("target_fluence_e_per_cm2", target_fluence_e_per_cm2)
    flux = _require_positive("flux_e_per_cm2_s", flux_e_per_cm2_s)
    return target / flux


def segment_fluences(segments):
    """Fluence delivered by each irradiated segment, in run order."""
    if not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a sequence of segment mappings")
    if not segments:
        raise ValueError("segments must hold at least one irradiated segment")
    delivered = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError("segment %d must be a mapping, got %r" % (index, segment))
        delivered.append(
            accumulated_fluence_e_per_cm2(
                segment.get("flux_e_per_cm2_s"), segment.get("duration_s")
            )
        )
    return tuple(delivered)


def cumulative_fluence_schedule(segments):
    """Running total of delivered fluence after each irradiated segment."""
    running = 0.0
    schedule = []
    for fluence in segment_fluences(segments):
        running += fluence
        schedule.append(running)
    return tuple(schedule)


def plane_non_uniformity(max_flux_e_per_cm2_s, min_flux_e_per_cm2_s):
    """Fractional spread of flux across the sample plane of the holder."""
    high = _require_positive("max_flux_e_per_cm2_s", max_flux_e_per_cm2_s)
    low = _require_positive("min_flux_e_per_cm2_s", min_flux_e_per_cm2_s)
    if low > high and not math.isclose(low, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "min_flux_e_per_cm2_s %g exceeds max_flux_e_per_cm2_s %g" % (low, high)
        )
    return (high - low) / (high + low)


def beam_plane_uniform(
    max_flux_e_per_cm2_s, min_flux_e_per_cm2_s, policy=DEFAULT_IRRADIATION_POLICY
):
    """True when every sample on the holder sees the same exposure closely enough."""
    validate_irradiation_policy(policy)
    spread = plane_non_uniformity(max_flux_e_per_cm2_s, min_flux_e_per_cm2_s)
    return _at_most(spread, float(policy["max_plane_non_uniformity"]))


def beam_energy_on_nominal(beam_energy_mev, policy=DEFAULT_IRRADIATION_POLICY):
    """True when the beam is the equivalent one megaelectronvolt electron."""
    validate_irradiation_policy(policy)
    energy = _require_positive("beam_energy_mev", beam_energy_mev)
    offset = abs(energy - float(policy["beam_energy_nominal_mev"]))
    return _at_most(offset, float(policy["beam_energy_tolerance_mev"]))


def flux_within_window(flux_e_per_cm2_s, policy=DEFAULT_IRRADIATION_POLICY):
    """True when the delivery rate sits inside the allowed rate window."""
    validate_irradiation_policy(policy)
    flux = _require_positive("flux_e_per_cm2_s", flux_e_per_cm2_s)
    return _at_least(flux, float(policy["min_flux_e_per_cm2_s"])) and _at_most(
        flux, float(policy["max_flux_e_per_cm2_s"])
    )


def sample_environment_acceptable(
    sample_temperature_c, chamber_pressure_pa, policy=DEFAULT_IRRADIATION_POLICY
):
    """True when holder temperature and chamber pressure are both in bounds."""
    validate_irradiation_policy(policy)
    temperature = _require_number("sample_temperature_c", sample_temperature_c)
    pressure = _require_positive("chamber_pressure_pa", chamber_pressure_pa)
    in_window = _at_least(
        temperature, float(policy["min_sample_temperature_c"])
    ) and _at_most(temperature, float(policy["max_sample_temperature_c"]))
    return in_window and _at_most(pressure, float(policy["max_chamber_pressure_pa"]))


def remaining_power_factor(
    fluence_e_per_cm2, degradation_coefficient, reference_fluence_e_per_cm2
):
    """Output remaining after a fluence, on the logarithmic degradation law.

    The factor falls by a fixed increment per decade of fluence above the
    reference fluence, and is floored at zero because a negative output has
    no physical reading.
    """
    fluence = _require_non_negative("fluence_e_per_cm2", fluence_e_per_cm2)
    coefficient = _require_positive(
        "degradation_coefficient", degradation_coefficient
    )
    reference = _require_positive(
        "reference_fluence_e_per_cm2", reference_fluence_e_per_cm2
    )
    factor = 1.0 - coefficient * math.log10(1.0 + fluence / reference)
    return factor if factor > 0.0 else 0.0


def degradation_fraction(
    fluence_e_per_cm2, degradation_coefficient, reference_fluence_e_per_cm2
):
    """Fraction of the undamaged output the fluence removes."""
    return 1.0 - remaining_power_factor(
        fluence_e_per_cm2, degradation_coefficient, reference_fluence_e_per_cm2
    )


def fluence_point_met(
    delivered_fluence_e_per_cm2,
    planned_fluence_e_per_cm2,
    policy=DEFAULT_IRRADIATION_POLICY,
):
    """True when the delivered fluence reaches the planned point within tolerance."""
    validate_irradiation_policy(policy)
    delivered = _require_non_negative(
        "delivered_fluence_e_per_cm2", delivered_fluence_e_per_cm2
    )
    planned = _require_positive(
        "planned_fluence_e_per_cm2", planned_fluence_e_per_cm2
    )
    floor = planned * (1.0 - float(policy["fluence_tolerance_fraction"]))
    return _at_least(delivered, floor)


def characterisation_inventory(points):
    """Group the electrical characterisation points, rejecting an unknown one."""
    if not isinstance(points, (list, tuple, set, frozenset)):
        raise ValueError("points must be a collection of characterisation points")
    grouped = []
    for point in points:
        if point not in CHARACTERISATION_POINTS:
            raise ValueError(
                "unknown characterisation point %r; recognised points are %s"
                % (point, ", ".join(RECOGNISED_POINTS))
            )
        if point not in grouped:
            grouped.append(point)
    return tuple(sorted(grouped))


def missing_characterisation_points(points):
    """Mandatory characterisation points the run did not take."""
    grouped = characterisation_inventory(points)
    return tuple(point for point in MANDATORY_POINTS if point not in grouped)


def assess_electron_irradiation_run(case, policy=DEFAULT_IRRADIATION_POLICY):
    """Full clause 6.4.3.11.2 judgement for one electron irradiation run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_irradiation_policy(policy)

    beam = case.get("beam")
    if not isinstance(beam, dict):
        raise ValueError("case is missing a beam block")
    environment = case.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("case is missing an environment block")
    if "characterisation_points" not in case:
        raise ValueError(
            "case is missing characterisation_points; an absent inventory is "
            "not an empty one"
        )

    energy = _require_positive("beam energy_mev", beam.get("energy_mev"))
    plane_max = _require_positive(
        "beam plane_max_flux_e_per_cm2_s", beam.get("plane_max_flux_e_per_cm2_s")
    )
    plane_min = _require_positive(
        "beam plane_min_flux_e_per_cm2_s", beam.get("plane_min_flux_e_per_cm2_s")
    )
    spread = plane_non_uniformity(plane_max, plane_min)

    delivered = cumulative_fluence_schedule(case.get("segments"))
    total_fluence = delivered[-1]
    planned = _require_positive(
        "planned_fluence_e_per_cm2", case.get("planned_fluence_e_per_cm2")
    )

    degradation = case.get("degradation")
    if not isinstance(degradation, dict):
        raise ValueError("case is missing a degradation block")
    coefficient = _require_positive(
        "degradation coefficient", degradation.get("coefficient")
    )
    reference = _require_positive(
        "degradation reference_fluence_e_per_cm2",
        degradation.get("reference_fluence_e_per_cm2"),
    )

    grouped = characterisation_inventory(case["characterisation_points"])
    absent = missing_characterisation_points(case["characterisation_points"])

    findings = []
    result = {
        "beam_energy_mev": energy,
        "plane_non_uniformity": spread,
        "cumulative_fluence_e_per_cm2": delivered,
        "delivered_fluence_e_per_cm2": total_fluence,
        "planned_fluence_e_per_cm2": planned,
        "remaining_power_factor": remaining_power_factor(
            total_fluence, coefficient, reference
        ),
        "degradation_fraction": degradation_fraction(
            total_fluence, coefficient, reference
        ),
        "characterisation_points": grouped,
        "missing_characterisation_points": absent,
        "findings": findings,
    }

    conditions_ok = True
    if not beam_energy_on_nominal(energy, policy):
        conditions_ok = False
        findings.append(
            "the beam ran at %.4g MeV, off the %.4g MeV equivalent electron the "
            "referenced method names"
            % (energy, float(policy["beam_energy_nominal_mev"]))
        )
    if not beam_plane_uniform(plane_max, plane_min, policy):
        conditions_ok = False
        findings.append(
            "flux across the sample plane spreads %.4g, above the %.4g allowance, "
            "so samples on one holder took different exposures"
            % (spread, float(policy["max_plane_non_uniformity"]))
        )
    for index, segment in enumerate(case["segments"]):
        flux = _require_positive(
            "segment %d flux_e_per_cm2_s" % index, segment.get("flux_e_per_cm2_s")
        )
        if not flux_within_window(flux, policy):
            conditions_ok = False
            findings.append(
                "segment %d ran at %.4g e/cm2/s, outside the %.4g to %.4g rate "
                "window, so the damage rate is not the one the mission "
                "accumulates"
                % (
                    index,
                    flux,
                    float(policy["min_flux_e_per_cm2_s"]),
                    float(policy["max_flux_e_per_cm2_s"]),
                )
            )
    temperature = _require_number(
        "environment sample_temperature_c", environment.get("sample_temperature_c")
    )
    pressure = _require_positive(
        "environment chamber_pressure_pa", environment.get("chamber_pressure_pa")
    )
    if not sample_environment_acceptable(temperature, pressure, policy):
        conditions_ok = False
        findings.append(
            "the holder sat at %.4g C and %.4g Pa, outside the declared "
            "irradiation environment" % (temperature, pressure)
        )
    result["conditions_acceptable"] = conditions_ok

    fluence_ok = fluence_point_met(total_fluence, planned, policy)
    result["fluence_point_met"] = fluence_ok
    if not fluence_ok:
        findings.append(
            "the run delivered %.4g e/cm2 against a planned %.4g e/cm2, which "
            "lands the article on a different point of the degradation curve"
            % (total_fluence, planned)
        )

    if absent:
        findings.append(
            "no electrical characterisation was taken at %s, so the degradation "
            "the fluence caused is not measurable from this run"
            % ", ".join(absent)
        )

    if not conditions_ok:
        result["verdict"] = RUN_CONDITIONS_VIOLATED
    elif not fluence_ok:
        result["verdict"] = EXPOSURE_FLUENCE_SHORTFALL
    elif absent:
        result["verdict"] = CHARACTERISATION_INCOMPLETE
    else:
        result["verdict"] = IRRADIATION_RUN_CONFORMS
    return result
