#!/usr/bin/env python3
"""Placing the thermal anneal between the two post-irradiation measurements.

Anchor: ECSS-E-ST-20-08C clause 12.6.12. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause fixes a position in a sequence, not a number. A blocking diode
comes out of its electron exposure, it is measured, it is then soaked warm,
and it is measured again. The anneal sits between the two measurements, and
almost everything that can go wrong with this test is a way of losing that
ordering.

Why the order carries the meaning. The first reading catches the part at its
worst, while the exposure damage is still fully present. The soak lets the
part recover whatever it is going to recover. The second reading is what the
array will actually fly. Two readings either side of the soak therefore give
a recovered share; a single reading, or two readings on the same side of the
soak, give a number that looks like a recovery and is not one.

Where the ordering quietly breaks. A first measurement taken days after the
exposure has already let the part anneal at room temperature, so the shift
it reports is smaller than the exposure caused and the soak appears to have
done less than it did. A soak that begins before the first measurement is
finished has merged the two events. A second measurement taken at a
different temperature from the first is comparing a recovery against a
thermal coefficient. Each of those produces a plausible recovery figure from
a sequence that never happened as described.

The soak itself still has to be a soak: hot enough and long enough to mean
anything, and below the rating of the package it is applied to. A profile
that clears the dwell floor by sitting above the package rating has damaged
the part it was meant to recover.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STAGE_FIRST_MEASUREMENT = "first-post-irradiation-measurement"
STAGE_SOAK = "anneal-soak"
STAGE_SECOND_MEASUREMENT = "second-post-irradiation-measurement"

ANNEAL_SEQUENCE_NOT_ESTABLISHED = "anneal-sequence-not-established"
SOAK_PROFILE_OUT_OF_BOUNDS = "soak-profile-out-of-bounds"
READING_CONDITIONS_NOT_COMPARABLE = "reading-conditions-not-comparable"
ANNEAL_INSERTION_ACCEPTED = "anneal-insertion-accepted"

DEFAULT_ANNEAL_POLICY = {
    "min_soak_temperature_c": 60.0,
    "min_dwell_hours": 24.0,
    "max_package_temperature_c": 125.0,
    "max_first_measurement_delay_h": 24.0,
    "reading_temperature_tolerance_k": 2.0,
    "advisory_min_recovery_fraction": 0.25,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
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


def validate_anneal_policy(policy):
    """Check the declared anneal policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    soak_floor = _require_number(
        "min_soak_temperature_c", policy.get("min_soak_temperature_c")
    )
    package_ceiling = _require_number(
        "max_package_temperature_c", policy.get("max_package_temperature_c")
    )
    if not _at_most(soak_floor, package_ceiling):
        raise ValueError(
            "the policy asks for a soak at or above %g C inside a package "
            "rated to %g C, which no profile satisfies"
            % (soak_floor, package_ceiling)
        )
    _require_positive("min_dwell_hours", policy.get("min_dwell_hours"))
    _require_non_negative(
        "max_first_measurement_delay_h",
        policy.get("max_first_measurement_delay_h"),
    )
    _require_positive(
        "reading_temperature_tolerance_k",
        policy.get("reading_temperature_tolerance_k"),
    )
    advisory = _require_number(
        "advisory_min_recovery_fraction",
        policy.get("advisory_min_recovery_fraction"),
    )
    if not 0.0 <= advisory <= 1.0:
        raise ValueError(
            "advisory_min_recovery_fraction %g must sit between zero and one"
            % advisory
        )
    return policy


def validate_soak_profile(profile):
    """Read the anneal soak: when it started, when it ended, how hot it ran."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping, got %r" % (profile,))
    start = _require_number("soak start_hour", profile.get("start_hour"))
    end = _require_number("soak end_hour", profile.get("end_hour"))
    temperature = _require_number(
        "soak_temperature_c", profile.get("soak_temperature_c")
    )
    if not end > start:
        raise ValueError(
            "the soak ends at hour %g having started at hour %g, which is not "
            "a dwell" % (end, start)
        )
    return {
        "start_hour": start,
        "end_hour": end,
        "soak_temperature_c": temperature,
    }


def soak_dwell_hours(profile):
    """How long the part actually sat at the soak temperature."""
    checked = validate_soak_profile(profile)
    return checked["end_hour"] - checked["start_hour"]


def validate_measurement(label, measurement):
    """Read one electrical measurement and the conditions it was taken under."""
    if not isinstance(measurement, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, measurement))
    return {
        "stage": _require_label("%s stage" % label, measurement.get("stage", label)),
        "hour": _require_number("%s hour" % label, measurement.get("hour")),
        "reading_temperature_c": _require_number(
            "%s reading_temperature_c" % label,
            measurement.get("reading_temperature_c"),
        ),
        "forward_voltage_v": _require_positive(
            "%s forward_voltage_v" % label, measurement.get("forward_voltage_v")
        ),
        "reverse_leakage_a": _require_positive(
            "%s reverse_leakage_a" % label, measurement.get("reverse_leakage_a")
        ),
    }


def sequence_breaks(exposure_end_hour, first, profile, second):
    """Name every place the required ordering of the four events is lost.

    The required order is: exposure ends, first measurement, soak, second
    measurement. Every break is named, because a timeline that has lost two
    of them is a different problem from one that has lost one.
    """
    end_hour = _require_number("exposure_end_hour", exposure_end_hour)
    first_checked = validate_measurement(STAGE_FIRST_MEASUREMENT, first)
    soak = validate_soak_profile(profile)
    second_checked = validate_measurement(STAGE_SECOND_MEASUREMENT, second)
    breaks = []
    if not _at_least(first_checked["hour"], end_hour):
        breaks.append(
            "the first measurement is timed before the exposure ended"
        )
    if not _at_least(soak["start_hour"], first_checked["hour"]):
        breaks.append(
            "the soak begins before the first measurement was taken, so the "
            "anneal is not inserted between the two readings"
        )
    if not _at_least(second_checked["hour"], soak["end_hour"]):
        breaks.append(
            "the second measurement is timed before the soak ended, so it "
            "reports a part still in the middle of its anneal"
        )
    return tuple(breaks)


def first_measurement_delay_h(exposure_end_hour, first):
    """How long the part waited between the exposure ending and its first reading."""
    end_hour = _require_number("exposure_end_hour", exposure_end_hour)
    checked = validate_measurement(STAGE_FIRST_MEASUREMENT, first)
    return checked["hour"] - end_hour


def soak_profile_breaches(profile, policy=DEFAULT_ANNEAL_POLICY):
    """Name every soak bound the profile missed."""
    validate_anneal_policy(policy)
    checked = validate_soak_profile(profile)
    dwell = checked["end_hour"] - checked["start_hour"]
    breaches = []
    if not _at_least(
        checked["soak_temperature_c"], float(policy["min_soak_temperature_c"])
    ):
        breaches.append(
            "the soak ran at %g C, below the %g C the anneal policy asks for"
            % (checked["soak_temperature_c"], float(policy["min_soak_temperature_c"]))
        )
    if not _at_most(
        checked["soak_temperature_c"], float(policy["max_package_temperature_c"])
    ):
        breaches.append(
            "the soak ran at %g C, above the %g C the package is rated to; the "
            "anneal has damaged the part it was meant to recover"
            % (
                checked["soak_temperature_c"],
                float(policy["max_package_temperature_c"]),
            )
        )
    if not _at_least(dwell, float(policy["min_dwell_hours"])):
        breaches.append(
            "the dwell lasted %g h, short of the %g h the anneal policy asks for"
            % (dwell, float(policy["min_dwell_hours"]))
        )
    return tuple(breaches)


def reading_temperature_gap_k(first, second):
    """How far apart the two readings were taken, in kelvin."""
    first_checked = validate_measurement(STAGE_FIRST_MEASUREMENT, first)
    second_checked = validate_measurement(STAGE_SECOND_MEASUREMENT, second)
    return abs(
        second_checked["reading_temperature_c"]
        - first_checked["reading_temperature_c"]
    )


def readings_comparable(first, second, policy=DEFAULT_ANNEAL_POLICY):
    """True when the two readings share a temperature closely enough to subtract."""
    validate_anneal_policy(policy)
    return _at_most(
        reading_temperature_gap_k(first, second),
        float(policy["reading_temperature_tolerance_k"]),
    )


def recovered_share(baseline_value, first_value, second_value):
    """Share of the exposure-induced shift the soak gave back.

    One means the soak returned the characteristic to its pre-exposure
    value; zero means the soak moved nothing. A negative share means the
    part kept drifting through the soak, which is a finding rather than an
    error.
    """
    baseline = _require_positive("baseline_value", baseline_value)
    first_value = _require_positive("first_value", first_value)
    second_value = _require_positive("second_value", second_value)
    shift = first_value - baseline
    if math.isclose(shift, 0.0, rel_tol=_REL_TOL, abs_tol=1e-12):
        raise ValueError(
            "the exposure moved this characteristic by nothing, so there is "
            "no shift for the soak to have recovered"
        )
    return (first_value - second_value) / shift


def assess_blocking_diode_annealing(case, policy=DEFAULT_ANNEAL_POLICY):
    """Full clause 12.6.12 review of one annealed blocking diode timeline."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_anneal_policy(policy)

    findings = []
    advisories = []
    result = {
        "dwell_hours": None,
        "soak_temperature_c": None,
        "first_measurement_delay_h": None,
        "reading_temperature_gap_k": None,
        "forward_recovered_share": None,
        "leakage_recovered_share": None,
        "findings": findings,
        "advisories": advisories,
    }

    for key in ("first_measurement", "soak_profile", "second_measurement"):
        if case.get(key) is None:
            findings.append(
                "the timeline carries no %s, so the anneal cannot be shown to "
                "sit between the two post-irradiation readings"
                % key.replace("_", " ")
            )
    if findings:
        result["verdict"] = ANNEAL_SEQUENCE_NOT_ESTABLISHED
        return result

    first = case["first_measurement"]
    second = case["second_measurement"]
    profile = case["soak_profile"]
    exposure_end = case.get("exposure_end_hour")
    if exposure_end is None:
        findings.append(
            "the timeline carries no exposure end, so the delay before the "
            "first reading cannot be bounded"
        )
        result["verdict"] = ANNEAL_SEQUENCE_NOT_ESTABLISHED
        return result

    result["dwell_hours"] = soak_dwell_hours(profile)
    result["soak_temperature_c"] = validate_soak_profile(profile)[
        "soak_temperature_c"
    ]
    result["first_measurement_delay_h"] = first_measurement_delay_h(
        exposure_end, first
    )
    result["reading_temperature_gap_k"] = reading_temperature_gap_k(first, second)

    breaks = sequence_breaks(exposure_end, first, profile, second)
    if breaks:
        findings.extend(breaks)
        result["verdict"] = ANNEAL_SEQUENCE_NOT_ESTABLISHED
        return result

    if not _at_most(
        result["first_measurement_delay_h"],
        float(policy["max_first_measurement_delay_h"]),
    ):
        findings.append(
            "the first reading came %g h after the exposure, past the %g h the "
            "policy allows; the part has already annealed at ambient and the "
            "soak will look less effective than it was"
            % (
                result["first_measurement_delay_h"],
                float(policy["max_first_measurement_delay_h"]),
            )
        )
        result["verdict"] = ANNEAL_SEQUENCE_NOT_ESTABLISHED
        return result

    breaches = soak_profile_breaches(profile, policy)
    if breaches:
        findings.extend(breaches)
        result["verdict"] = SOAK_PROFILE_OUT_OF_BOUNDS
        return result

    if not readings_comparable(first, second, policy):
        findings.append(
            "the two readings were taken %g K apart, past the %g K tolerance; "
            "the difference between them is a thermal coefficient as much as "
            "a recovery"
            % (
                result["reading_temperature_gap_k"],
                float(policy["reading_temperature_tolerance_k"]),
            )
        )
        result["verdict"] = READING_CONDITIONS_NOT_COMPARABLE
        return result

    baseline = case.get("pre_irradiation")
    if baseline is not None:
        checked_baseline = validate_measurement("pre_irradiation", baseline)
        checked_first = validate_measurement(STAGE_FIRST_MEASUREMENT, first)
        checked_second = validate_measurement(STAGE_SECOND_MEASUREMENT, second)
        for label, key in (
            ("forward_recovered_share", "forward_voltage_v"),
            ("leakage_recovered_share", "reverse_leakage_a"),
        ):
            try:
                result[label] = recovered_share(
                    checked_baseline[key], checked_first[key], checked_second[key]
                )
            except ValueError:
                result[label] = None
        if result["forward_recovered_share"] is not None and not _at_least(
            result["forward_recovered_share"],
            float(policy["advisory_min_recovery_fraction"]),
        ):
            advisories.append(
                "the soak gave back %.3g per cent of the forward drop shift, "
                "under the %.3g per cent the policy expects; the sequence is "
                "sound and the recovery is small"
                % (
                    result["forward_recovered_share"] * 100.0,
                    float(policy["advisory_min_recovery_fraction"]) * 100.0,
                )
            )

    result["verdict"] = ANNEAL_INSERTION_ACCEPTED
    return result
