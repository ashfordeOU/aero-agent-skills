#!/usr/bin/env python3
"""Choosing the measurement technique for solar cell assembly capacitance.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.16.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause allows the assembly capacitance to be measured either in the
frequency domain or in the time domain, and asks for an accepted
technique -- one of them, nominated, not a menu left open. A campaign
that keeps both domains alive produces two numbers with no rule for
reconciling them, and the assembly figure is the one that gets
extrapolated to the panel, so it has to be defensible rather than merely
available.

What each domain actually asks of the setup:

    frequency domain   an impedance bridge or a swept analyser reads the
                       reactive part at a test frequency. The article
                       presents 1 / (2 pi f C) ohms there, which has to
                       land inside the instrument's measurable band, and
                       the assembly's own leakage shows up as a
                       dissipation factor 1 / (2 pi f C R) that has to
                       stay small enough for the reactive part to
                       dominate.

    time domain        a constant-current ramp reads dV/dt = I / C, or a
                       resistive discharge reads the decay constant R C.
                       Either way the recorder has to place enough
                       samples inside the observation window for the
                       slope or the decay to be fitted at all.

Both domains carry the same two closing checks: the fixture stray
capacitance has to be a small fraction of the article -- a solar cell
assembly is a small capacitor and a careless fixture is not -- and the
combined uncertainty has to close against the requirement.

The instrument limits below are a declared policy, not a physical
constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Accepted technique -> the domain it belongs to.
CAPACITANCE_METHODS = {
    "frequency-domain-lcr-bridge": "frequency-domain",
    "frequency-domain-swept-impedance-analyser": "frequency-domain",
    "time-domain-constant-current-ramp": "time-domain",
    "time-domain-resistive-discharge-decay": "time-domain",
}

RECOGNISED_METHODS = tuple(sorted(CAPACITANCE_METHODS))
RECOGNISED_DOMAINS = ("frequency-domain", "time-domain")

METHOD_NOT_NOMINATED = "capacitance-method-not-nominated"
MORE_THAN_ONE_METHOD_OPEN = "more-than-one-method-left-open"
METHOD_INADEQUATE = "nominated-method-inadequate"
METHOD_ACCEPTED = "capacitance-method-accepted"

DEFAULT_METHOD_POLICY = {
    "meter_min_reactance_ohm": 10.0,
    "meter_max_reactance_ohm": 1.0e7,
    "max_dissipation_factor": 0.1,
    "min_samples_in_window": 20.0,
    "max_stray_fraction": 0.1,
    "max_combined_uncertainty_percent": 5.0,
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


def validate_method_policy(policy):
    """Check a capacitance measurement policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    low = _require_positive(
        "meter_min_reactance_ohm", policy.get("meter_min_reactance_ohm")
    )
    high = _require_positive(
        "meter_max_reactance_ohm", policy.get("meter_max_reactance_ohm")
    )
    if high <= low:
        raise ValueError(
            "meter_max_reactance_ohm %g must be above meter_min_reactance_ohm %g"
            % (high, low)
        )
    _require_positive(
        "max_dissipation_factor", policy.get("max_dissipation_factor")
    )
    _require_positive(
        "min_samples_in_window", policy.get("min_samples_in_window")
    )
    fraction = _require_positive(
        "max_stray_fraction", policy.get("max_stray_fraction")
    )
    if fraction >= 1.0:
        raise ValueError(
            "max_stray_fraction %g must be below one; a fixture that holds more "
            "than the article is measuring itself" % fraction
        )
    _require_positive(
        "max_combined_uncertainty_percent",
        policy.get("max_combined_uncertainty_percent"),
    )
    return policy


def method_domain(method):
    """Which domain an accepted technique belongs to."""
    if method not in CAPACITANCE_METHODS:
        raise ValueError(
            "unknown capacitance method %r; recognised methods are %s"
            % (method, ", ".join(RECOGNISED_METHODS))
        )
    return CAPACITANCE_METHODS[method]


def method_inventory(methods):
    """Group the nominated techniques, rejecting an unrecognised one."""
    if not isinstance(methods, (list, tuple, set, frozenset)):
        raise ValueError("methods must be a collection of method names")
    grouped = []
    for method in methods:
        method_domain(method)
        if method not in grouped:
            grouped.append(method)
    return tuple(sorted(grouped))


def nominate_single_method(methods):
    """The one technique the campaign runs under; the clause asks for one."""
    grouped = method_inventory(methods)
    if len(grouped) != 1:
        raise ValueError(
            "exactly one capacitance method must be nominated, got %d: %s"
            % (len(grouped), ", ".join(grouped) or "none")
        )
    return grouped[0]


def reactance_ohm(capacitance_f, frequency_hz):
    """Magnitude of the capacitive reactance the bridge has to resolve."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    frequency = _require_positive("frequency_hz", frequency_hz)
    return 1.0 / (2.0 * math.pi * frequency * capacitance)


def dissipation_factor(capacitance_f, frequency_hz, leakage_resistance_ohm):
    """Loss the assembly's own leakage adds beside the reactive part."""
    resistance = _require_positive(
        "leakage_resistance_ohm", leakage_resistance_ohm
    )
    return reactance_ohm(capacitance_f, frequency_hz) / resistance


def decay_time_constant_s(capacitance_f, discharge_resistance_ohm):
    """Time constant a resistive discharge presents to the recorder."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    resistance = _require_positive(
        "discharge_resistance_ohm", discharge_resistance_ohm
    )
    return capacitance * resistance


def ramp_slope_v_per_s(ramp_current_a, capacitance_f):
    """Voltage slope a constant-current charge produces: dV/dt = I / C."""
    current = _require_positive("ramp_current_a", ramp_current_a)
    capacitance = _require_positive("capacitance_f", capacitance_f)
    return current / capacitance


def samples_in_window(observation_window_s, sample_rate_hz):
    """Samples the recorder places inside the observation window."""
    window = _require_positive("observation_window_s", observation_window_s)
    rate = _require_positive("sample_rate_hz", sample_rate_hz)
    return window * rate


def stray_fraction(stray_capacitance_f, article_capacitance_f):
    """How much of the reading the fixture contributes rather than the article."""
    stray = _require_non_negative("stray_capacitance_f", stray_capacitance_f)
    article = _require_positive("article_capacitance_f", article_capacitance_f)
    return stray / article


def combined_uncertainty_percent(components_percent):
    """Root-sum-square of the declared uncertainty contributions."""
    if not isinstance(components_percent, (list, tuple)):
        raise ValueError(
            "components_percent must be a sequence of uncertainty contributions"
        )
    if not components_percent:
        raise ValueError(
            "components_percent is empty; an undeclared budget is not a zero one"
        )
    values = [
        _require_non_negative("uncertainty component", value)
        for value in components_percent
    ]
    return math.sqrt(math.fsum(value * value for value in values))


def time_domain_observation(method, capacitance_f, settings):
    """Observation window and slope the nominated time-domain method gives."""
    if method_domain(method) != "time-domain":
        raise ValueError("%s is not a time-domain method" % (method,))
    if not isinstance(settings, dict):
        raise ValueError("settings must be a mapping, got %r" % (settings,))
    if method == "time-domain-constant-current-ramp":
        slope = ramp_slope_v_per_s(settings.get("ramp_current_a"), capacitance_f)
        span = _require_positive("ramp_span_v", settings.get("ramp_span_v"))
        window = span / slope
    else:
        slope = None
        window = decay_time_constant_s(
            capacitance_f, settings.get("discharge_resistance_ohm")
        )
    rate = _require_positive("sample_rate_hz", settings.get("sample_rate_hz"))
    return {
        "observation_window_s": window,
        "ramp_slope_v_per_s": slope,
        "samples_in_window": samples_in_window(window, rate),
    }


def assess_capacitance_measurement_method(case, policy=DEFAULT_METHOD_POLICY):
    """Full clause 6.4.3.16.2 judgement for one capacitance measurement plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_method_policy(policy)
    if "nominated_methods" not in case:
        raise ValueError(
            "case is missing nominated_methods; an absent nomination is not an "
            "empty one"
        )
    grouped = method_inventory(case["nominated_methods"])

    findings = []
    result = {
        "nominated_methods": grouped,
        "method": None,
        "domain": None,
        "reactance_ohm": None,
        "dissipation_factor": None,
        "observation": None,
        "stray_fraction": None,
        "combined_uncertainty_percent": None,
        "findings": findings,
    }

    if not grouped:
        findings.append(
            "no capacitance measurement technique is nominated, so the "
            "assembly figure would come from a method nobody accepted"
        )
        result["verdict"] = METHOD_NOT_NOMINATED
        return result
    if len(grouped) > 1:
        findings.append(
            "%d techniques are left open (%s); the clause asks for one accepted "
            "technique, and two produce two numbers with no rule for "
            "reconciling them" % (len(grouped), ", ".join(grouped))
        )
        result["verdict"] = MORE_THAN_ONE_METHOD_OPEN
        return result

    method = nominate_single_method(grouped)
    domain = method_domain(method)
    result["method"] = method
    result["domain"] = domain

    article = case.get("article")
    if not isinstance(article, dict):
        raise ValueError("case is missing an article block")
    capacitance = _require_positive(
        "article capacitance_f", article.get("capacitance_f")
    )
    stray = _require_non_negative(
        "article stray_capacitance_f", article.get("stray_capacitance_f")
    )

    settings = case.get(domain)
    if not isinstance(settings, dict):
        raise ValueError(
            "case is missing the %s settings block the nominated method needs"
            % (domain,)
        )

    if domain == "frequency-domain":
        frequency = _require_positive(
            "test_frequency_hz", settings.get("test_frequency_hz")
        )
        leakage = _require_positive(
            "leakage_resistance_ohm", settings.get("leakage_resistance_ohm")
        )
        reactance = reactance_ohm(capacitance, frequency)
        loss = dissipation_factor(capacitance, frequency, leakage)
        result["reactance_ohm"] = reactance
        result["dissipation_factor"] = loss
        if not (
            _at_least(reactance, float(policy["meter_min_reactance_ohm"]))
            and _at_most(reactance, float(policy["meter_max_reactance_ohm"]))
        ):
            findings.append(
                "at %.4g Hz the assembly presents %.4g ohm, outside the %.4g to "
                "%.4g ohm the instrument can resolve"
                % (
                    frequency,
                    reactance,
                    float(policy["meter_min_reactance_ohm"]),
                    float(policy["meter_max_reactance_ohm"]),
                )
            )
        if not _at_most(loss, float(policy["max_dissipation_factor"])):
            findings.append(
                "the leakage gives a dissipation factor of %.4g, above the %.4g "
                "the reactive part still dominates at"
                % (loss, float(policy["max_dissipation_factor"]))
            )
    else:
        observation = time_domain_observation(method, capacitance, settings)
        result["observation"] = observation
        if not _at_least(
            observation["samples_in_window"], float(policy["min_samples_in_window"])
        ):
            findings.append(
                "the recorder places %.4g samples in the %.4g s observation "
                "window, below the %.4g needed to fit it"
                % (
                    observation["samples_in_window"],
                    observation["observation_window_s"],
                    float(policy["min_samples_in_window"]),
                )
            )

    fraction = stray_fraction(stray, capacitance)
    uncertainty = combined_uncertainty_percent(
        case.get("uncertainty_components_percent")
    )
    result["stray_fraction"] = fraction
    result["combined_uncertainty_percent"] = uncertainty

    if not _at_most(fraction, float(policy["max_stray_fraction"])):
        findings.append(
            "the fixture contributes %.4g of the article capacitance, above the "
            "%.4g a guarded setup is allowed"
            % (fraction, float(policy["max_stray_fraction"]))
        )
    if not _at_most(
        uncertainty, float(policy["max_combined_uncertainty_percent"])
    ):
        findings.append(
            "the combined uncertainty closes at %.4g percent against the %.4g "
            "percent the requirement allows"
            % (uncertainty, float(policy["max_combined_uncertainty_percent"]))
        )

    result["verdict"] = METHOD_ACCEPTED if not findings else METHOD_INADEQUATE
    return result
