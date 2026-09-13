#!/usr/bin/env python3
"""Mission-specific ultraviolet testing of solar cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.15.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The standard ultraviolet qualification exposure is sized for an ordinary
near-Earth mission. Science and planetary missions are not ordinary: a
flyby that drops inside half an astronomical unit, an inner-planetary
cruise that spends years closer to the Sun than the Earth ever gets, or
a solar observatory that never enters an eclipse all collect far more
ultraviolet than the baseline exposure covers. Clause 6.4.3.15.4 is the
hook for the extra testing those profiles earn.

The arithmetic that decides it:

    solar intensity     one over the square of the heliocentric distance
                        in astronomical units, so 0.3 AU is eleven suns
    equivalent sun
    hours (ESH)         intensity multiplied by illuminated hours,
                        accumulated over every declared mission phase
    extra testing       earned when the mission ESH budget exceeds the
                        standard qualification exposure times a margin
    acceleration        lamp intensity divided by the mission mean
                        intensity, bounded because the darkening of a
                        coverglass adhesive stops following the dose
                        once the lamp is driven hard enough

An accelerated run is only representative if the facility can actually
produce the lamp intensity, the acceleration stays under the bound, the
planned ESH covers the mission budget, and the sample sits near its
flight operating temperature while it is illuminated -- darkening and
annealing both move with temperature.

The exposure limits below are a declared policy, not a physical
constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Mission profile -> the exposure the extra ultraviolet testing has to
# demonstrate the solar cell assembly survives.
MISSION_PROFILES = {
    "near-sun-science-flyby": "solar-intensity-multiplied-ultraviolet-dose",
    "inner-planetary-cruise": "prolonged-high-intensity-ultraviolet-dose",
    "solar-observatory-station-keeping": "eclipse-free-continuous-ultraviolet-dose",
    "planetary-orbit-low-eclipse-fraction": "eclipse-poor-ultraviolet-duty-cycle",
    "extended-interplanetary-transfer": "long-duration-cumulative-ultraviolet-dose",
}

RECOGNISED_PROFILES = tuple(sorted(MISSION_PROFILES))

COMMON_OBJECTIVE = "mission-specific-ultraviolet-exposure-demonstration"

EXTRA_TESTING_NOT_REQUIRED = "extra-ultraviolet-testing-not-required"
TEST_NOT_PLANNED = "mission-ultraviolet-test-not-planned"
TEST_INADEQUATE = "mission-ultraviolet-test-inadequate"
EXPOSURE_DEMONSTRATED = "mission-ultraviolet-exposure-demonstrated"

DEFAULT_ULTRAVIOLET_POLICY = {
    "standard_qualification_esh": 1000.0,
    "extra_test_margin": 1.0,
    "max_acceleration_factor": 5.0,
    "max_facility_intensity_suns": 10.0,
    "max_sample_temperature_offset_c": 10.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
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


def validate_ultraviolet_policy(policy):
    """Check a mission ultraviolet exposure policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "standard_qualification_esh", policy.get("standard_qualification_esh")
    )
    margin = _require_positive("extra_test_margin", policy.get("extra_test_margin"))
    if margin < 1.0:
        raise ValueError(
            "extra_test_margin %g must not be below one; the extra testing cannot "
            "be earned by less exposure than the standard qualification" % margin
        )
    acceleration = _require_positive(
        "max_acceleration_factor", policy.get("max_acceleration_factor")
    )
    if acceleration < 1.0:
        raise ValueError(
            "max_acceleration_factor %g must not be below one" % acceleration
        )
    _require_positive(
        "max_facility_intensity_suns", policy.get("max_facility_intensity_suns")
    )
    _require_non_negative(
        "max_sample_temperature_offset_c",
        policy.get("max_sample_temperature_offset_c"),
    )
    return policy


def solar_intensity_suns(heliocentric_distance_au):
    """Solar intensity in suns: the inverse square of the distance in AU."""
    distance = _require_positive(
        "heliocentric_distance_au", heliocentric_distance_au
    )
    return 1.0 / (distance * distance)


def phase_equivalent_sun_hours(phase):
    """Equivalent sun hours one declared mission phase contributes."""
    if not isinstance(phase, dict):
        raise ValueError("a mission phase must be a mapping, got %r" % (phase,))
    intensity = solar_intensity_suns(phase.get("heliocentric_distance_au"))
    duration = _require_non_negative("duration_h", phase.get("duration_h"))
    illuminated = _require_fraction(
        "illuminated_fraction", phase.get("illuminated_fraction")
    )
    return intensity * duration * illuminated


def mission_equivalent_sun_hours(phases):
    """Equivalent sun hours the whole declared mission profile accumulates."""
    if not isinstance(phases, (list, tuple)):
        raise ValueError("phases must be a sequence of mission phases")
    if not phases:
        raise ValueError(
            "phases is empty; an absent exposure profile is not a zero one"
        )
    return math.fsum(phase_equivalent_sun_hours(phase) for phase in phases)


def mission_illuminated_hours(phases):
    """Illuminated hours the declared mission profile accumulates."""
    if not isinstance(phases, (list, tuple)):
        raise ValueError("phases must be a sequence of mission phases")
    if not phases:
        raise ValueError("phases is empty; an absent profile is not a zero one")
    total = 0.0
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("a mission phase must be a mapping, got %r" % (phase,))
        duration = _require_non_negative("duration_h", phase.get("duration_h"))
        illuminated = _require_fraction(
            "illuminated_fraction", phase.get("illuminated_fraction")
        )
        total += duration * illuminated
    return total


def mission_mean_intensity_suns(phases):
    """Dose-weighted mean intensity the assembly actually works under."""
    hours = mission_illuminated_hours(phases)
    if hours <= 0.0:
        raise ValueError(
            "the mission profile accumulates no illuminated hours, so it has no "
            "mean intensity"
        )
    return mission_equivalent_sun_hours(phases) / hours


def extra_testing_threshold_esh(policy=DEFAULT_ULTRAVIOLET_POLICY):
    """Exposure above which clause 6.4.3.15.4 extra testing is earned."""
    validate_ultraviolet_policy(policy)
    return float(policy["standard_qualification_esh"]) * float(
        policy["extra_test_margin"]
    )


def extra_testing_required(mission_esh, policy=DEFAULT_ULTRAVIOLET_POLICY):
    """True when the mission exposure outruns the standard qualification."""
    exposure = _require_non_negative("mission_esh", mission_esh)
    return _at_least(exposure, extra_testing_threshold_esh(policy))


def acceleration_factor(test_intensity_suns, mission_mean_suns):
    """How much harder the lamp is driven than the mission mean intensity."""
    lamp = _require_positive("test_intensity_suns", test_intensity_suns)
    mean = _require_positive("mission_mean_suns", mission_mean_suns)
    return lamp / mean


def accelerated_test_duration_h(required_esh, test_intensity_suns):
    """Lamp hours needed to deliver an exposure at a given lamp intensity."""
    exposure = _require_positive("required_esh", required_esh)
    lamp = _require_positive("test_intensity_suns", test_intensity_suns)
    return exposure / lamp


def planned_equivalent_sun_hours(test_intensity_suns, duration_h):
    """Exposure a planned run delivers: lamp intensity times lamp hours."""
    lamp = _require_positive("test_intensity_suns", test_intensity_suns)
    hours = _require_positive("duration_h", duration_h)
    return lamp * hours


def absorptance_increase(exposure_esh, saturation, characteristic_esh):
    """Saturating rise in solar absorptance a coverglass stack darkens to.

    Ultraviolet darkening of a coverglass adhesive fills the available
    colour centres and then stops, so the rise saturates rather than
    growing without bound with dose.
    """
    exposure = _require_non_negative("exposure_esh", exposure_esh)
    ceiling = _require_positive("saturation", saturation)
    characteristic = _require_positive("characteristic_esh", characteristic_esh)
    return ceiling * (1.0 - math.exp(-exposure / characteristic))


def profile_inventory(profiles):
    """Group the declared mission profiles, rejecting an unrecognised one."""
    if not isinstance(profiles, (list, tuple, set, frozenset)):
        raise ValueError("profiles must be a collection of mission profile names")
    grouped = []
    for profile in profiles:
        if profile not in MISSION_PROFILES:
            raise ValueError(
                "unknown mission profile %r; recognised profiles are %s"
                % (profile, ", ".join(RECOGNISED_PROFILES))
            )
        if profile not in grouped:
            grouped.append(profile)
    return tuple(sorted(grouped))


def ultraviolet_objectives(profiles):
    """What the extra ultraviolet testing demonstrates, given the profiles."""
    grouped = profile_inventory(profiles)
    if not grouped:
        return ()
    objectives = [MISSION_PROFILES[profile] for profile in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_mission_specific_ultraviolet_tests(
    case, policy=DEFAULT_ULTRAVIOLET_POLICY
):
    """Full clause 6.4.3.15.4 judgement for one mission ultraviolet campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_ultraviolet_policy(policy)
    if "mission_profiles" not in case:
        raise ValueError(
            "case is missing mission_profiles; an absent inventory is not an "
            "empty one"
        )
    profiles = profile_inventory(case["mission_profiles"])
    objectives = ultraviolet_objectives(case["mission_profiles"])

    mission = case.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission block")
    phases = mission.get("phases")
    mission_esh = mission_equivalent_sun_hours(phases)
    mean_intensity = mission_mean_intensity_suns(phases)
    operating_temperature = _require_number(
        "mission operating_temperature_c", mission.get("operating_temperature_c")
    )
    saturation = _require_positive(
        "mission saturation_absorptance_increase",
        mission.get("saturation_absorptance_increase"),
    )
    characteristic = _require_positive(
        "mission characteristic_esh", mission.get("characteristic_esh")
    )

    threshold = extra_testing_threshold_esh(policy)
    findings = []
    result = {
        "mission_profiles": profiles,
        "objectives": objectives,
        "mission_equivalent_sun_hours": mission_esh,
        "mission_mean_intensity_suns": mean_intensity,
        "extra_testing_threshold_esh": threshold,
        "predicted_absorptance_increase": absorptance_increase(
            mission_esh, saturation, characteristic
        ),
        "planned_equivalent_sun_hours": None,
        "acceleration_factor": None,
        "dose_covered": None,
        "acceleration_within_bound": None,
        "facility_can_produce_intensity": None,
        "sample_temperature_representative": None,
        "findings": findings,
    }

    earned = extra_testing_required(mission_esh, policy)
    if not (profiles and earned):
        if not profiles:
            findings.append(
                "no science or planetary mission profile is declared, so no "
                "exposure beyond the standard qualification is claimed"
            )
        if not earned:
            findings.append(
                "the mission accumulates %.4g equivalent sun hours, at or below "
                "the %.4g the standard qualification already covers"
                % (mission_esh, threshold)
            )
        result["required"] = False
        result["verdict"] = EXTRA_TESTING_NOT_REQUIRED
        return result

    result["required"] = True
    test = case.get("test")
    if test is None:
        findings.append(
            "extra ultraviolet testing is earned but no run is planned; the "
            "mission exposure is stated and not yet demonstrated"
        )
        result["verdict"] = TEST_NOT_PLANNED
        return result
    if not isinstance(test, dict):
        raise ValueError("test must be a mapping, got %r" % (test,))

    lamp = _require_positive("test intensity_suns", test.get("intensity_suns"))
    hours = _require_positive("test duration_h", test.get("duration_h"))
    sample_temperature = _require_number(
        "test sample_temperature_c", test.get("sample_temperature_c")
    )

    planned = planned_equivalent_sun_hours(lamp, hours)
    factor = acceleration_factor(lamp, mean_intensity)
    covered = _at_least(planned, mission_esh)
    within_bound = _at_most(factor, float(policy["max_acceleration_factor"]))
    producible = _at_most(lamp, float(policy["max_facility_intensity_suns"]))
    offset = abs(sample_temperature - operating_temperature)
    representative = _at_most(
        offset, float(policy["max_sample_temperature_offset_c"])
    )

    result["planned_equivalent_sun_hours"] = planned
    result["acceleration_factor"] = factor
    result["dose_covered"] = covered
    result["acceleration_within_bound"] = within_bound
    result["facility_can_produce_intensity"] = producible
    result["sample_temperature_representative"] = representative

    if not covered:
        findings.append(
            "the planned run delivers %.4g equivalent sun hours against the "
            "%.4g the mission accumulates" % (planned, mission_esh)
        )
    if not within_bound:
        findings.append(
            "the lamp runs %.3f times the mission mean intensity, above the "
            "%.3f the darkening stays dose-following at"
            % (factor, float(policy["max_acceleration_factor"]))
        )
    if not producible:
        findings.append(
            "the run asks for %.3f suns, above the %.3f the facility can "
            "produce" % (lamp, float(policy["max_facility_intensity_suns"]))
        )
    if not representative:
        findings.append(
            "the sample sits %.3f C from its %.3f C flight operating "
            "temperature, and both darkening and annealing move with it"
            % (offset, operating_temperature)
        )

    result["verdict"] = (
        EXPOSURE_DEMONSTRATED
        if covered and within_bound and producible and representative
        else TEST_INADEQUATE
    )
    return result
