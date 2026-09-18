#!/usr/bin/env python3
"""Thermal environment and thermal-stability screen for explosives.

Anchor: ECSS-E-ST-33-11C clause 4.8.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An explosive charge is a metastable chemical, so temperature does two
separate things to it and the clause asks about both.

    envelope    the predicted flight temperatures, widened by the
                declared uncertainty, have to sit inside the range the
                device was qualified over, and clear of the
                temperature at which the charge begins to decompose
    stability   time spent hot is cumulative. A device that never
                exceeds its hot limit can still consume its whole
                qualified life by dwelling just under it, because the
                decomposition rate rises exponentially with
                temperature rather than linearly

The stability side is handled the way thermal life is handled
everywhere: an Arrhenius acceleration factor converts every segment of
the mission thermal profile into equivalent time at the reference
temperature the qualification dwell was run at, and the sum is compared
with that dwell.

Margins and the activation energy are declared inputs, not physical
constants of this module: the defaults below are a starting point and a
project substitutes the values measured for its own composition.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GAS_CONSTANT_J_PER_MOL_K = 8.314462618

ABSOLUTE_ZERO_C = -273.15

BOUNDS = ("hot", "cold")

VERDICT_MET = "thermal-requirements-met"
VERDICT_NOT_MET = "thermal-requirements-not-met"

DEFAULT_THERMAL_POLICY = {
    "qualification_margin_k": 10.0,
    "decomposition_onset_margin_k": 30.0,
    "activation_energy_j_per_mol": 1.6e5,
    "stability_utilization_limit": 1.0,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An equivalent time is a sum of exponentials and a margin is a
    difference of temperatures, so a case that sits exactly on its
    limit can land a few units in the last place off it. The limit is
    never relaxed; only the comparison tolerates the representation
    error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def kelvin_from_celsius(temperature_c):
    """Convert a declared Celsius temperature to kelvin."""
    value = _require_number("temperature_c", temperature_c)
    if value < ABSOLUTE_ZERO_C:
        raise ValueError("temperature_c is below absolute zero, got %r" % (value,))
    return value - ABSOLUTE_ZERO_C


def validate_thermal_policy(policy):
    """Check a thermal policy carries sane margins and an activation energy."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative("qualification_margin_k", policy.get("qualification_margin_k"))
    _require_non_negative(
        "decomposition_onset_margin_k", policy.get("decomposition_onset_margin_k")
    )
    _require_positive(
        "activation_energy_j_per_mol", policy.get("activation_energy_j_per_mol")
    )
    _require_positive(
        "stability_utilization_limit", policy.get("stability_utilization_limit")
    )
    return policy


def arrhenius_acceleration_factor(
    temperature_k, reference_temperature_k, activation_energy_j_per_mol
):
    """Rate at one temperature relative to the reference temperature."""
    temperature = _require_positive("temperature_k", temperature_k)
    reference = _require_positive("reference_temperature_k", reference_temperature_k)
    activation = _require_positive(
        "activation_energy_j_per_mol", activation_energy_j_per_mol
    )
    exponent = (activation / GAS_CONSTANT_J_PER_MOL_K) * (
        (1.0 / reference) - (1.0 / temperature)
    )
    return math.exp(exponent)


def validate_thermal_profile(profile):
    """Normalize a mission thermal profile into checked segments."""
    if not isinstance(profile, (list, tuple)):
        raise ValueError("profile must be a list of segments, got %r" % (profile,))
    if not profile:
        raise ValueError("profile must contain at least one segment")
    segments = []
    for index, raw in enumerate(profile):
        if not isinstance(raw, dict):
            raise ValueError("profile segment %d must be a mapping" % index)
        label = raw.get("label", "segment-%d" % index)
        if not isinstance(label, str) or not label.strip():
            raise ValueError("profile segment %d has an empty label" % index)
        segments.append(
            {
                "label": label.strip(),
                "temperature_k": _require_positive(
                    "profile segment %d temperature_k" % index, raw.get("temperature_k")
                ),
                "duration_h": _require_non_negative(
                    "profile segment %d duration_h" % index, raw.get("duration_h")
                ),
            }
        )
    if all(segment["duration_h"] == 0.0 for segment in segments):
        raise ValueError("profile has zero total duration")
    return segments


def equivalent_time_at_reference_h(
    profile, reference_temperature_k, activation_energy_j_per_mol
):
    """Mission profile expressed as time at the qualification temperature."""
    segments = validate_thermal_profile(profile)
    total = 0.0
    for segment in segments:
        factor = arrhenius_acceleration_factor(
            segment["temperature_k"],
            reference_temperature_k,
            activation_energy_j_per_mol,
        )
        total += segment["duration_h"] * factor
    return total


def hottest_segment(profile):
    """Segment of a profile that drives the decomposition check."""
    segments = validate_thermal_profile(profile)
    return max(segments, key=lambda segment: segment["temperature_k"])


def temperature_margin_k(bound, qualification_limit_k, predicted_extreme_k):
    """Kelvin between a predicted extreme and the qualification limit."""
    _require_choice("bound", bound, BOUNDS)
    limit = _require_positive("qualification_limit_k", qualification_limit_k)
    predicted = _require_positive("predicted_extreme_k", predicted_extreme_k)
    return limit - predicted if bound == "hot" else predicted - limit


def assess_temperature_envelope(case, policy=DEFAULT_THERMAL_POLICY):
    """Grade both predicted extremes against the qualification range."""
    validate_thermal_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("envelope case must be a mapping, got %r" % (case,))
    uncertainty = _require_non_negative(
        "prediction_uncertainty_k", case.get("prediction_uncertainty_k", 0.0)
    )
    hot_limit = _require_positive(
        "qualification_hot_limit_k", case.get("qualification_hot_limit_k")
    )
    cold_limit = _require_positive(
        "qualification_cold_limit_k", case.get("qualification_cold_limit_k")
    )
    if cold_limit >= hot_limit:
        raise ValueError(
            "qualification cold limit %g K is not below the hot limit %g K"
            % (cold_limit, hot_limit)
        )
    hot_predicted = (
        _require_positive("predicted_hot_k", case.get("predicted_hot_k")) + uncertainty
    )
    cold_predicted = (
        _require_positive("predicted_cold_k", case.get("predicted_cold_k")) - uncertainty
    )
    if cold_predicted <= 0.0:
        raise ValueError("the cold prediction with uncertainty falls below absolute zero")
    required = policy["qualification_margin_k"]
    bounds = {}
    findings = []
    for bound, limit, predicted in (
        ("hot", hot_limit, hot_predicted),
        ("cold", cold_limit, cold_predicted),
    ):
        margin = temperature_margin_k(bound, limit, predicted)
        ok = _at_least(margin, required)
        bounds[bound] = {
            "qualification_limit_k": limit,
            "predicted_with_uncertainty_k": predicted,
            "margin_k": margin,
            "compliant": ok,
        }
        if not ok:
            findings.append(
                "%s margin %.2f K is below the required %.2f K (predicted %.2f K "
                "against a %.2f K limit)" % (bound, margin, required, predicted, limit)
            )
    return {
        "check": "temperature-envelope",
        "bounds": bounds,
        "required_margin_k": required,
        "compliant": not findings,
        "findings": findings,
    }


def assess_decomposition_onset(case, policy=DEFAULT_THERMAL_POLICY):
    """Grade the hottest predicted temperature against decomposition onset."""
    validate_thermal_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("onset case must be a mapping, got %r" % (case,))
    onset = _require_positive(
        "decomposition_onset_k", case.get("decomposition_onset_k")
    )
    uncertainty = _require_non_negative(
        "prediction_uncertainty_k", case.get("prediction_uncertainty_k", 0.0)
    )
    hottest = (
        _require_positive("predicted_hot_k", case.get("predicted_hot_k")) + uncertainty
    )
    required = policy["decomposition_onset_margin_k"]
    margin = onset - hottest
    ok = _at_least(margin, required)
    findings = []
    if not ok:
        findings.append(
            "decomposition-onset margin %.2f K is below the required %.2f K "
            "(hottest %.2f K against an onset of %.2f K)"
            % (margin, required, hottest, onset)
        )
    return {
        "check": "decomposition-onset",
        "hottest_predicted_k": hottest,
        "decomposition_onset_k": onset,
        "margin_k": margin,
        "required_margin_k": required,
        "compliant": ok,
        "findings": findings,
    }


def assess_thermal_stability(case, policy=DEFAULT_THERMAL_POLICY):
    """Grade cumulative time at temperature against the qualified dwell."""
    validate_thermal_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("stability case must be a mapping, got %r" % (case,))
    reference = _require_positive(
        "qualification_dwell_temperature_k", case.get("qualification_dwell_temperature_k")
    )
    dwell = _require_positive(
        "qualification_dwell_hours", case.get("qualification_dwell_hours")
    )
    activation = _require_positive(
        "activation_energy_j_per_mol",
        case.get("activation_energy_j_per_mol", policy["activation_energy_j_per_mol"]),
    )
    equivalent = equivalent_time_at_reference_h(
        case.get("profile"), reference, activation
    )
    utilization = equivalent / dwell
    limit = policy["stability_utilization_limit"]
    ok = _at_most(utilization, limit)
    findings = []
    if not ok:
        findings.append(
            "equivalent time %.4g h at %.1f K consumes %.3f of the qualified "
            "dwell, above the allowed %.3f" % (equivalent, reference, utilization, limit)
        )
    driver = hottest_segment(case.get("profile"))
    return {
        "check": "thermal-stability",
        "reference_temperature_k": reference,
        "qualification_dwell_hours": dwell,
        "equivalent_time_h": equivalent,
        "utilization": utilization,
        "utilization_limit": limit,
        "driving_segment": driver["label"],
        "compliant": ok,
        "findings": findings,
    }


def assess_thermal_requirements(case, policy=DEFAULT_THERMAL_POLICY):
    """Full clause 4.8.3 thermal screen with an overall verdict."""
    validate_thermal_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    uncertainty = case.get("prediction_uncertainty_k", 0.0)
    envelope_case = dict(case.get("envelope") or {})
    envelope_case.setdefault("prediction_uncertainty_k", uncertainty)
    onset_case = dict(case.get("onset") or {})
    onset_case.setdefault("prediction_uncertainty_k", uncertainty)
    onset_case.setdefault("predicted_hot_k", envelope_case.get("predicted_hot_k"))
    stability_case = dict(case.get("stability") or {})
    results = {
        "temperature-envelope": assess_temperature_envelope(envelope_case, policy),
        "decomposition-onset": assess_decomposition_onset(onset_case, policy),
        "thermal-stability": assess_thermal_stability(stability_case, policy),
    }
    findings = []
    failed = []
    for name in ("temperature-envelope", "decomposition-onset", "thermal-stability"):
        result = results[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "checks": results,
        "failed_checks": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
