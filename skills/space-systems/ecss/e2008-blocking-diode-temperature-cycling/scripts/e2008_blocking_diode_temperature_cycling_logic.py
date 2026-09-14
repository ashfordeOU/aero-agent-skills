#!/usr/bin/env python3
"""Sizing and sentencing the temperature cycling a blocking diode sample has
to survive before it is called mission-representative.

Anchor: ECSS-E-ST-20-08C clause 12.6.5. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause applies thermal stress equivalent to a mission of eclipse cycles
to the test samples. Every word of that carries a decision:

    equivalent to a mission  the cycle count is not a round number somebody
                      liked. It comes out of the eclipse rate the orbit
                      produces, the years the array has to last and the
                      test margin the project declared, and it is rounded
                      up, never down
    thermal stress    a cycle is a hot plateau, a cold plateau, a dwell
                      long enough at each for the diode stack to reach
                      them, and a transition slow enough to be a thermal
                      cycle rather than a shock
    the test samples  the samples carry the result. Each one is sentenced
                      on how far its forward voltage and reverse leakage
                      moved across the run, and on whether the cycling
                      opened a crack or lifted a layer

A run that stopped short of the required cycles has not tested a mission.
It is closed as not evaluated rather than sentenced on the cycles it did
manage, because the cycles it skipped are the ones that would have found
the fatigue.

A cracked or delaminated sample fails the lot outright instead of being
diluted into a reject fraction: a fraction describes a spread of drift, a
crack describes a part that came apart.

The rates, plateaus, dwells and caps below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_DRIFT = "within-drift"
DRIFT_EXCEEDED = "drift-exceeded"
CRACKED = "cracked"

SAMPLE_CATEGORIES = (WITHIN_DRIFT, DRIFT_EXCEEDED, CRACKED)

FORWARD_VOLTAGE = "forward-voltage"
REVERSE_LEAKAGE = "reverse-leakage"

MONITORED_PARAMETERS = (FORWARD_VOLTAGE, REVERSE_LEAKAGE)

CYCLING_NOT_EVALUATED = "blocking-diode-cycling-not-evaluated"
PROFILE_DEFICIENT = "blocking-diode-cycling-profile-deficient"
SAMPLES_FAILED = "blocking-diode-cycling-samples-failed"
SAMPLES_PASSED = "blocking-diode-cycling-samples-passed"

RUN_VERDICTS = (
    CYCLING_NOT_EVALUATED,
    PROFILE_DEFICIENT,
    SAMPLES_FAILED,
    SAMPLES_PASSED,
)

DEFAULT_CYCLING_POLICY = {
    "min_hot_plateau_c": 80.0,
    "max_cold_plateau_c": -95.0,
    "min_cycle_amplitude_k": 160.0,
    "min_plateau_dwell_min": 5.0,
    "max_ramp_rate_k_per_min": 10.0,
    "min_test_margin_factor": 1.25,
    "max_parameter_drift_fraction": 0.05,
    "max_reject_fraction": 0.10,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
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


def validate_cycling_policy(policy):
    """Check a temperature cycling profile and acceptance policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    hot = _require_number("min_hot_plateau_c", policy.get("min_hot_plateau_c"))
    cold = _require_number("max_cold_plateau_c", policy.get("max_cold_plateau_c"))
    if not cold < hot:
        raise ValueError(
            "max_cold_plateau_c %g must sit below min_hot_plateau_c %g"
            % (cold, hot)
        )
    amplitude = _require_positive(
        "min_cycle_amplitude_k", policy.get("min_cycle_amplitude_k")
    )
    if amplitude > (hot - cold):
        raise ValueError(
            "min_cycle_amplitude_k %g cannot exceed the %g K the declared "
            "plateaus span" % (amplitude, hot - cold)
        )
    _require_positive(
        "min_plateau_dwell_min", policy.get("min_plateau_dwell_min")
    )
    _require_positive(
        "max_ramp_rate_k_per_min", policy.get("max_ramp_rate_k_per_min")
    )
    margin = _require_number(
        "min_test_margin_factor", policy.get("min_test_margin_factor")
    )
    if margin < 1.0:
        raise ValueError(
            "min_test_margin_factor %g would test less than the mission itself"
            % (margin,)
        )
    _require_fraction(
        "max_parameter_drift_fraction",
        policy.get("max_parameter_drift_fraction"),
    )
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def required_cycle_count(mission, policy=DEFAULT_CYCLING_POLICY):
    """Cycles the mission owes the samples, rounded up and never down."""
    validate_cycling_policy(policy)
    if not isinstance(mission, dict):
        raise ValueError("mission must be a mapping, got %r" % (mission,))
    rate = _require_positive(
        "mission eclipse_cycles_per_year", mission.get("eclipse_cycles_per_year")
    )
    years = _require_positive("mission years", mission.get("years"))
    margin = _require_positive(
        "mission test_margin_factor", mission.get("test_margin_factor")
    )
    if not _at_least(margin, float(policy["min_test_margin_factor"])):
        raise ValueError(
            "test_margin_factor %g sits under the %g the policy requires"
            % (margin, float(policy["min_test_margin_factor"]))
        )
    exact = rate * years * margin
    return int(math.ceil(exact - _ABS_TOL))


def cycle_amplitude_k(hot_plateau_c, cold_plateau_c):
    """Span the sample is driven across in one cycle, in kelvin."""
    hot = _require_number("hot_plateau_c", hot_plateau_c)
    cold = _require_number("cold_plateau_c", cold_plateau_c)
    if not cold < hot:
        raise ValueError(
            "cold_plateau_c %g must sit below hot_plateau_c %g" % (cold, hot)
        )
    return hot - cold


def ramp_rate_k_per_min(amplitude_k, transition_min):
    """Rate the transition drives the sample at, in kelvin per minute."""
    amplitude = _require_positive("amplitude_k", amplitude_k)
    transition = _require_positive("transition_min", transition_min)
    return amplitude / transition


def cycling_completeness(applied_cycles, required_cycles):
    """Share of the mission-equivalent cycles the chamber actually ran."""
    applied = _require_count("applied_cycles", applied_cycles)
    required = _require_count("required_cycles", required_cycles)
    return applied / required


def parameter_drift_fraction(before, after):
    """Relative movement of a monitored parameter across the run."""
    start = _require_positive("before", before)
    end = _require_non_negative("after", after)
    return abs(end - start) / start


def categorize_sample(sample, policy=DEFAULT_CYCLING_POLICY):
    """Group one sample by its drift and by any crack the cycling opened."""
    validate_cycling_policy(policy)
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (sample,))
    readings = sample.get("readings")
    if not isinstance(readings, dict) or not readings:
        raise ValueError(
            "sample is missing a non-empty readings mapping, got %r" % (readings,)
        )
    drifts = {}
    for name, pair in readings.items():
        if name not in MONITORED_PARAMETERS:
            raise ValueError(
                "unrecognised monitored parameter %r; known parameters are %s"
                % (name, ", ".join(MONITORED_PARAMETERS))
            )
        if not isinstance(pair, dict):
            raise ValueError(
                "reading %r must be a mapping with before and after, got %r"
                % (name, pair)
            )
        drifts[name] = parameter_drift_fraction(
            pair.get("before"), pair.get("after")
        )
    cracked = sample.get("cracked", False)
    if not isinstance(cracked, bool):
        raise ValueError("sample cracked flag must be a boolean, got %r" % (cracked,))
    cap = float(policy["max_parameter_drift_fraction"])
    if cracked:
        category = CRACKED
    elif any(not _at_most(value, cap) for value in drifts.values()):
        category = DRIFT_EXCEEDED
    else:
        category = WITHIN_DRIFT
    return {
        "id": sample.get("id"),
        "parameter_drift": drifts,
        "worst_drift": max(drifts.values()),
        "category": category,
    }


def assess_temperature_cycling_run(run, policy=DEFAULT_CYCLING_POLICY):
    """Full clause 12.6.5 judgement for one blocking diode cycling run."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    validate_cycling_policy(policy)
    mission = run.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("run is missing a mission block")
    profile = run.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("run is missing a profile block")
    samples = run.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("run is missing a non-empty samples list")

    required = required_cycle_count(mission, policy)
    applied = _require_count("profile applied_cycles", profile.get("applied_cycles"))
    hot = _require_number("profile hot_plateau_c", profile.get("hot_plateau_c"))
    cold = _require_number("profile cold_plateau_c", profile.get("cold_plateau_c"))
    dwell = _require_positive(
        "profile plateau_dwell_min", profile.get("plateau_dwell_min")
    )
    transition = _require_positive(
        "profile transition_min", profile.get("transition_min")
    )
    amplitude = cycle_amplitude_k(hot, cold)
    ramp = ramp_rate_k_per_min(amplitude, transition)
    completeness = cycling_completeness(applied, required)

    sentences = [categorize_sample(sample, policy) for sample in samples]
    cracked = [s for s in sentences if s["category"] == CRACKED]
    drifted = [s for s in sentences if s["category"] == DRIFT_EXCEEDED]
    reject_fraction = (len(cracked) + len(drifted)) / len(sentences)

    findings = []
    result = {
        "required_cycles": required,
        "applied_cycles": applied,
        "cycling_completeness": completeness,
        "cycle_amplitude_k": amplitude,
        "ramp_rate_k_per_min": ramp,
        "sentences": sentences,
        "cracked_samples": len(cracked),
        "drifted_samples": len(drifted),
        "reject_fraction": reject_fraction,
        "findings": findings,
    }

    short = not _at_least(applied, required)
    if short:
        findings.append(
            "the chamber ran %d of the %d cycles this mission is equivalent "
            "to, so the fatigue the remaining cycles would have found is "
            "untested" % (applied, required)
        )

    deficiencies = []
    if not _at_least(hot, float(policy["min_hot_plateau_c"])):
        deficiencies.append(
            "the hot plateau reached %.1f C against the %.1f C the profile "
            "calls for" % (hot, float(policy["min_hot_plateau_c"]))
        )
    if not _at_most(cold, float(policy["max_cold_plateau_c"])):
        deficiencies.append(
            "the cold plateau stopped at %.1f C against the %.1f C the profile "
            "calls for" % (cold, float(policy["max_cold_plateau_c"]))
        )
    if not _at_least(amplitude, float(policy["min_cycle_amplitude_k"])):
        deficiencies.append(
            "the cycle spans %.1f K against the %.1f K minimum amplitude"
            % (amplitude, float(policy["min_cycle_amplitude_k"]))
        )
    if not _at_least(dwell, float(policy["min_plateau_dwell_min"])):
        deficiencies.append(
            "each plateau is held %.2f min against the %.2f min that lets the "
            "stack reach it" % (dwell, float(policy["min_plateau_dwell_min"]))
        )
    if not _at_most(ramp, float(policy["max_ramp_rate_k_per_min"])):
        deficiencies.append(
            "the transition drives %.3f K/min against the %.3f K/min ceiling "
            "that keeps this a cycle rather than a shock"
            % (ramp, float(policy["max_ramp_rate_k_per_min"]))
        )
    findings.extend(deficiencies)

    if cracked:
        findings.append(
            "%d sample(s) came apart during cycling rather than drifting"
            % (len(cracked),)
        )
    if not _at_most(reject_fraction, float(policy["max_reject_fraction"])):
        findings.append(
            "%.4f of the samples fall short against the %.4f the lot allows"
            % (reject_fraction, float(policy["max_reject_fraction"]))
        )

    if short:
        result["verdict"] = CYCLING_NOT_EVALUATED
    elif deficiencies:
        result["verdict"] = PROFILE_DEFICIENT
    elif cracked or not _at_most(
        reject_fraction, float(policy["max_reject_fraction"])
    ):
        result["verdict"] = SAMPLES_FAILED
    else:
        result["verdict"] = SAMPLES_PASSED
    return result
