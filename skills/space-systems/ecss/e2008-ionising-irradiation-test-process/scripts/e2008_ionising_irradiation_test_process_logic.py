#!/usr/bin/env python3
"""Ionising irradiation of diodes: gamma field or accelerator electron beam.

Anchor: ECSS-E-ST-20-08C clause 12.6.11.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two facilities are admitted for this exposure and they are not
interchangeable in how they have to be run. A cobalt gamma cell soaks the
whole sample volume in a broadly uniform photon field and delivers dose
slowly and steadily; an electron accelerator paints the sample plane with
a beam, delivers the same dose in a small fraction of the time, and its
beam energy is a parameter the gamma cell simply does not have. A third
kind of facility is outside this exposure entirely, and grading its run
against this process produces a confident verdict about evidence the
clause does not govern.

What the two share is that the dose is what counts and the dose is never
read directly. It is accumulated: a rate held for a duration, segment by
segment, with beam-off gaps between them that deliver nothing. Summing
the segments is the whole measurement, and a run reported by its
wall-clock length has counted the gaps as exposure.

Rate is bounded on both sides and for different reasons. Too slow and a
long exposure anneals as fast as it damages, so the part under test is
repairing itself while the dose accumulates and the endpoint understates
what a mission profile would do. Too fast and the opposite happens: the
damage is delivered faster than the lattice can relax and the endpoint
overstates it. Neither error is visible in the total dose.

Uniformity across the sample plane decides what the total dose describes.
A spread across the monitors means the devices at one end of the tray
received a different exposure from the devices at the other, and the
average is then a number no individual device was actually given.

Bias during exposure is part of the exposure. An unbiased junction and a
reverse-biased junction accumulate charge differently in the same field,
so a run whose bias condition is not on record cannot be compared with
any other run, however well its dose was measured.

The bands below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GAMMA = "cobalt-gamma-source"
ELECTRON = "electron-accelerator"
ADMITTED_FACILITIES = (GAMMA, ELECTRON)

UNBIASED = "unbiased"
REVERSE_BIASED = "reverse-biased"
ADMITTED_BIAS_CONDITIONS = (UNBIASED, REVERSE_BIASED)

FACILITY_NOT_ADMITTED = "irradiation-facility-not-admitted"
BIAS_CONDITION_NOT_STATED = "exposure-bias-condition-not-stated"
BEAM_CONDITIONS_INVALID = "irradiation-beam-conditions-invalid"
DOSE_UNIFORMITY_OUT_OF_BAND = "sample-plane-dose-uniformity-out-of-band"
ACCUMULATED_DOSE_OFF_TARGET = "accumulated-dose-off-target"
EXPOSURE_ACCEPTED = "ionising-exposure-accepted"

DEFAULT_IRRADIATION_POLICY = {
    "gamma_min_rate_gy_per_h": 0.36,
    "gamma_max_rate_gy_per_h": 36.0,
    "electron_min_rate_gy_per_h": 36.0,
    "electron_max_rate_gy_per_h": 3600.0,
    "electron_min_energy_mev": 0.5,
    "electron_max_energy_mev": 12.0,
    "max_uniformity_spread_fraction": 0.10,
    "dose_tolerance_fraction": 0.10,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_irradiation_policy(policy):
    """Check the exposure policy is complete and its windows are ordered."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    pairs = (
        ("gamma_min_rate_gy_per_h", "gamma_max_rate_gy_per_h"),
        ("electron_min_rate_gy_per_h", "electron_max_rate_gy_per_h"),
        ("electron_min_energy_mev", "electron_max_energy_mev"),
    )
    for low_key, high_key in pairs:
        low = _require_positive(low_key, policy.get(low_key))
        high = _require_positive(high_key, policy.get(high_key))
        if low > high:
            raise ValueError(
                "%s %g sits above %s %g, so the window admits nothing"
                % (low_key, low, high_key, high)
            )
    spread = _require_positive(
        "max_uniformity_spread_fraction",
        policy.get("max_uniformity_spread_fraction"),
    )
    if spread >= 1.0:
        raise ValueError(
            "max_uniformity_spread_fraction %g admits a plane where one "
            "monitor read nothing" % spread
        )
    tolerance = _require_positive(
        "dose_tolerance_fraction", policy.get("dose_tolerance_fraction")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "dose_tolerance_fraction %g admits a run that delivered no dose"
            % tolerance
        )
    return policy


def facility_admitted(facility):
    """True when the facility is one of the two this exposure allows."""
    return _require_label("facility", facility).lower() in ADMITTED_FACILITIES


def normalise_facility(facility):
    """Read the facility back, refusing anything outside the two admitted."""
    label = _require_label("facility", facility).lower()
    if label not in ADMITTED_FACILITIES:
        raise ValueError(
            "facility %r is neither %r nor %r" % (facility, GAMMA, ELECTRON)
        )
    return label


def bias_condition_stated(bias_condition):
    """True when the bias the devices were held at during exposure is on record."""
    if bias_condition is None:
        return False
    if not isinstance(bias_condition, str):
        return False
    return bias_condition.strip().lower() in ADMITTED_BIAS_CONDITIONS


def dose_rate_window(facility, policy=DEFAULT_IRRADIATION_POLICY):
    """The rate window the chosen facility has to be run inside."""
    validate_irradiation_policy(policy)
    label = normalise_facility(facility)
    if label == GAMMA:
        return (
            float(policy["gamma_min_rate_gy_per_h"]),
            float(policy["gamma_max_rate_gy_per_h"]),
        )
    return (
        float(policy["electron_min_rate_gy_per_h"]),
        float(policy["electron_max_rate_gy_per_h"]),
    )


def dose_rate_within_window(facility, rate_gy_per_h, policy=DEFAULT_IRRADIATION_POLICY):
    """True when the rate sits inside the window for that facility."""
    low, high = dose_rate_window(facility, policy)
    rate = _require_positive("rate_gy_per_h", rate_gy_per_h)
    return _at_least(rate, low) and _at_most(rate, high)


def beam_energy_within_window(energy_mev, policy=DEFAULT_IRRADIATION_POLICY):
    """True when an accelerator beam energy sits inside its declared window."""
    validate_irradiation_policy(policy)
    energy = _require_positive("energy_mev", energy_mev)
    return _at_least(energy, float(policy["electron_min_energy_mev"])) and _at_most(
        energy, float(policy["electron_max_energy_mev"])
    )


def validate_segment(segment):
    """Read one beam-on segment: the rate it held and how long it held it."""
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (segment,))
    rate = _require_positive("rate_gy_per_h", segment.get("rate_gy_per_h"))
    hours = _require_positive("duration_hours", segment.get("duration_hours"))
    return rate, hours


def segment_dose_gy(rate_gy_per_h, duration_hours):
    """Dose one segment delivered, its rate held for its duration."""
    rate = _require_positive("rate_gy_per_h", rate_gy_per_h)
    hours = _require_positive("duration_hours", duration_hours)
    return rate * hours


def accumulated_dose_gy(segments):
    """Total dose the beam-on segments delivered, gaps contributing nothing."""
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("no beam-on segment was recorded, so no dose accumulated")
    total = 0.0
    for segment in segments:
        rate, hours = validate_segment(segment)
        total += segment_dose_gy(rate, hours)
    return total


def beam_on_hours(segments):
    """Hours the beam was actually on, which is not the wall-clock length."""
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("no beam-on segment was recorded")
    return sum(validate_segment(segment)[1] for segment in segments)


def mean_rate_gy_per_h(segments):
    """Dose-weighted average rate the exposure actually ran at."""
    return accumulated_dose_gy(segments) / beam_on_hours(segments)


def nominal_exposure_hours(target_dose_gy, rate_gy_per_h):
    """Hours a steady rate would need to reach the target dose."""
    target = _require_positive("target_dose_gy", target_dose_gy)
    rate = _require_positive("rate_gy_per_h", rate_gy_per_h)
    return target / rate


def dose_deviation_fraction(accumulated_gy, target_dose_gy):
    """How far the accumulated dose sits from the target, as a share of it."""
    accumulated = _require_positive("accumulated_gy", accumulated_gy)
    target = _require_positive("target_dose_gy", target_dose_gy)
    return abs(accumulated - target) / target


def dose_within_tolerance(
    accumulated_gy, target_dose_gy, policy=DEFAULT_IRRADIATION_POLICY
):
    """True when the accumulated dose landed inside the declared tolerance."""
    validate_irradiation_policy(policy)
    deviation = dose_deviation_fraction(accumulated_gy, target_dose_gy)
    return _at_most(deviation, float(policy["dose_tolerance_fraction"]))


def uniformity_spread_fraction(monitor_readings_gy):
    """Spread across the sample plane monitors, as a share of their mean."""
    if not isinstance(monitor_readings_gy, (list, tuple)):
        raise ValueError(
            "monitor_readings_gy must be a sequence, got %r" % (monitor_readings_gy,)
        )
    if len(monitor_readings_gy) < 2:
        raise ValueError(
            "a spread needs at least two monitors; one monitor measures a "
            "point and says nothing about the plane"
        )
    readings = [
        _require_positive("monitor reading", reading) for reading in monitor_readings_gy
    ]
    mean = sum(readings) / len(readings)
    return (max(readings) - min(readings)) / mean


def uniformity_within_allowance(
    monitor_readings_gy, policy=DEFAULT_IRRADIATION_POLICY
):
    """True when the sample plane is flat enough for one dose to describe it."""
    validate_irradiation_policy(policy)
    spread = uniformity_spread_fraction(monitor_readings_gy)
    return _at_most(spread, float(policy["max_uniformity_spread_fraction"]))


def run_ionising_irradiation_exposure(case, policy=DEFAULT_IRRADIATION_POLICY):
    """Full clause 12.6.11.1.1 run over one presented irradiation exposure."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_irradiation_policy(policy)

    findings = []
    result = {
        "facility": None,
        "bias_condition": None,
        "target_dose_gy": None,
        "accumulated_dose_gy": None,
        "dose_deviation_fraction": None,
        "beam_on_hours": None,
        "mean_rate_gy_per_h": None,
        "nominal_exposure_hours": None,
        "uniformity_spread_fraction": None,
        "findings": findings,
    }

    facility = case.get("facility")
    if facility is None:
        raise ValueError("case is missing the irradiation facility")
    if not facility_admitted(facility):
        findings.append(
            "facility %r is neither a cobalt gamma field nor an accelerator "
            "electron beam, so this exposure process does not govern it"
            % (facility,)
        )
        result["verdict"] = FACILITY_NOT_ADMITTED
        return result
    label = normalise_facility(facility)
    result["facility"] = label

    bias = case.get("bias_condition")
    if not bias_condition_stated(bias):
        findings.append(
            "the bias the devices were held at during exposure is not on "
            "record, so the run cannot be compared with any other run"
        )
        result["verdict"] = BIAS_CONDITION_NOT_STATED
        return result
    result["bias_condition"] = bias.strip().lower()

    target = _require_positive("target_dose_gy", case.get("target_dose_gy"))
    result["target_dose_gy"] = target

    segments = case.get("segments")
    result["accumulated_dose_gy"] = accumulated_dose_gy(segments)
    result["beam_on_hours"] = beam_on_hours(segments)
    result["mean_rate_gy_per_h"] = mean_rate_gy_per_h(segments)
    result["nominal_exposure_hours"] = nominal_exposure_hours(
        target, result["mean_rate_gy_per_h"]
    )
    result["dose_deviation_fraction"] = dose_deviation_fraction(
        result["accumulated_dose_gy"], target
    )

    low, high = dose_rate_window(label, policy)
    for index, segment in enumerate(segments, start=1):
        rate, _hours = validate_segment(segment)
        if not dose_rate_within_window(label, rate, policy):
            findings.append(
                "segment %d ran at %g gray per hour, outside the %g to %g "
                "window for this facility, so annealing and damage are no "
                "longer in the proportion the endpoint assumes"
                % (index, rate, low, high)
            )

    if label == ELECTRON:
        energy = case.get("beam_energy_mev")
        if energy is None:
            findings.append(
                "an accelerator run carries a beam energy and none is on "
                "record, so the depth the dose was deposited at is unknown"
            )
        elif not beam_energy_within_window(energy, policy):
            findings.append(
                "the beam ran at %g megaelectronvolt, outside the declared "
                "energy window" % _require_positive("beam_energy_mev", energy)
            )

    if findings:
        result["verdict"] = BEAM_CONDITIONS_INVALID
        return result

    monitors = case.get("monitor_readings_gy")
    if monitors is None:
        raise ValueError("case is missing the sample plane monitor readings")
    result["uniformity_spread_fraction"] = uniformity_spread_fraction(monitors)
    if not uniformity_within_allowance(monitors, policy):
        findings.append(
            "the sample plane monitors spread by %.3g per cent of their mean, "
            "so one tray dose describes no device on the tray"
            % (result["uniformity_spread_fraction"] * 100.0)
        )
        result["verdict"] = DOSE_UNIFORMITY_OUT_OF_BAND
        return result

    if not dose_within_tolerance(result["accumulated_dose_gy"], target, policy):
        findings.append(
            "the segments accumulate %g gray against a %g gray target, %.3g "
            "per cent away, which is a different exposure from the one the "
            "programme asked for"
            % (
                result["accumulated_dose_gy"],
                target,
                result["dose_deviation_fraction"] * 100.0,
            )
        )
        result["verdict"] = ACCUMULATED_DOSE_OFF_TARGET
        return result

    result["verdict"] = EXPOSURE_ACCEPTED
    return result
