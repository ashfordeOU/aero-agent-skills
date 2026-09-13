#!/usr/bin/env python3
"""One accepted method for measuring the capacitance of an array string.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly string behaves as a distributed capacitor: the
cells, their coverglasses and the substrate under them hold charge
against the structure, and that capacitance is what feeds a discharge
when the surface flashes over. The clause asks for the measurement to
be made by one accepted method, drawn from either the frequency domain
or the time domain -- not by whichever instrument the laboratory had
free on the day, and not by two methods averaged together.

Frequency-domain methods

    lcr-bridge            balanced bridge at a single test frequency
    impedance-analyser    swept impedance, capacitance from the reactive part

Time-domain methods

    resistive-discharge   decay through a known resistor, tau = R * C
    constant-current-charge   ramp rate dV/dt = I / C

The two domains need different evidence. A frequency-domain run stands
or falls on the reactance the article presents at the test frequency and
on the dissipation factor its leakage conductance produces; a
time-domain run stands or falls on the decay constant the discharge
resistor sets, on the samples the recorder places inside that constant,
and on a record window long enough for the decay to finish. Both carry
the same stray and lead capacitance, and both have to close an
uncertainty budget against the figure the requirement asks for.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FREQUENCY_DOMAIN_METHODS = (
    "lcr-bridge",
    "impedance-analyser",
)

TIME_DOMAIN_METHODS = (
    "resistive-discharge",
    "constant-current-charge",
)

ACCEPTED_METHODS = FREQUENCY_DOMAIN_METHODS + TIME_DOMAIN_METHODS

FREQUENCY_DOMAIN = "frequency-domain"
TIME_DOMAIN = "time-domain"

REQUIRED_EVIDENCE_BY_DOMAIN = {
    FREQUENCY_DOMAIN: (
        "expected_capacitance_f",
        "instrument_accuracy_fraction",
        "instrument_reactance_band_ohm",
        "leakage_conductance_s",
        "required_uncertainty_fraction",
        "stray_capacitance_f",
        "test_frequency_hz",
    ),
    TIME_DOMAIN: (
        "discharge_resistance_ohm",
        "expected_capacitance_f",
        "instrument_accuracy_fraction",
        "record_window_s",
        "recorder_sample_rate_hz",
        "required_uncertainty_fraction",
        "stray_capacitance_f",
    ),
}

MIN_SAMPLES_PER_TIME_CONSTANT = 10.0
MIN_RECORD_WINDOW_TIME_CONSTANTS = 5.0
MAX_DISSIPATION_FACTOR = 0.1
MAX_STRAY_FRACTION = 0.05

METHOD_ACCEPTED = "measurement-method-accepted"
METHOD_NOT_ACCEPTED = "measurement-method-not-accepted"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError("%s must be a fraction at or below one, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A sample rate written in one unit and compared in another can land a
    few units in the last place either side of the limit. The limit is
    never relaxed; only the comparison tolerates the representation
    error, which is why no caller uses a bare >= on a derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def method_domain(method):
    """Whether an accepted method works in the frequency or the time domain."""
    if method in FREQUENCY_DOMAIN_METHODS:
        return FREQUENCY_DOMAIN
    if method in TIME_DOMAIN_METHODS:
        return TIME_DOMAIN
    raise ValueError(
        "unknown measurement method %r; accepted methods are %s"
        % (method, ", ".join(ACCEPTED_METHODS))
    )


def required_evidence(method):
    """Inputs the nominated method has to bring before it can be judged."""
    return tuple(sorted(REQUIRED_EVIDENCE_BY_DOMAIN[method_domain(method)]))


def nominate_single_method(nominated):
    """Reduce a nomination to the one method the clause allows.

    A campaign that leaves two methods open produces two numbers with no
    rule for reconciling them, so an ambiguous nomination is refused at
    the input rather than resolved by preference later.
    """
    if isinstance(nominated, str):
        candidates = (nominated,)
    elif isinstance(nominated, (list, tuple)):
        candidates = tuple(nominated)
    else:
        raise ValueError(
            "nominated method must be a name or a sequence of names, got %r"
            % (nominated,)
        )
    if len(candidates) != 1:
        raise ValueError(
            "exactly one measurement method must be nominated, got %d"
            % (len(candidates),)
        )
    method = candidates[0]
    method_domain(method)
    return method


def capacitive_reactance_ohm(capacitance_f, frequency_hz):
    """Magnitude of the reactance the string presents at a test frequency."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    frequency = _require_positive("frequency_hz", frequency_hz)
    return 1.0 / (2.0 * math.pi * frequency * capacitance)


def dissipation_factor(capacitance_f, frequency_hz, leakage_conductance_s):
    """Loss term the string leakage adds to a frequency-domain reading.

    A lossy article reads as a capacitance that moves with frequency, so
    the dissipation factor is the check that the number being recorded
    is a capacitance at all.
    """
    capacitance = _require_positive("capacitance_f", capacitance_f)
    frequency = _require_positive("frequency_hz", frequency_hz)
    conductance = _require_non_negative("leakage_conductance_s", leakage_conductance_s)
    return conductance / (2.0 * math.pi * frequency * capacitance)


def discharge_time_constant_s(capacitance_f, resistance_ohm):
    """Decay constant a time-domain discharge through a known resistor sets."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    resistance = _require_positive("discharge_resistance_ohm", resistance_ohm)
    return resistance * capacitance


def samples_per_time_constant(time_constant_s, sample_rate_hz):
    """Samples the recorder places inside one decay constant."""
    tau = _require_positive("time_constant_s", time_constant_s)
    rate = _require_positive("recorder_sample_rate_hz", sample_rate_hz)
    return tau * rate


def record_window_time_constants(record_window_s, time_constant_s):
    """How many decay constants the record window spans."""
    window = _require_positive("record_window_s", record_window_s)
    tau = _require_positive("time_constant_s", time_constant_s)
    return window / tau


def stray_capacitance_fraction(stray_capacitance_f, expected_capacitance_f):
    """Share of the reading owed to the fixture rather than the article."""
    stray = _require_non_negative("stray_capacitance_f", stray_capacitance_f)
    expected = _require_positive("expected_capacitance_f", expected_capacitance_f)
    return stray / expected


def combined_uncertainty_fraction(terms):
    """Root-sum-square of the independent error terms of the measurement."""
    if not isinstance(terms, (list, tuple)) or not terms:
        raise ValueError("uncertainty terms must be a non-empty sequence, got %r" % (terms,))
    total = 0.0
    for index, term in enumerate(terms):
        value = _require_fraction("uncertainty term %d" % index, term)
        total += value * value
    return math.sqrt(total)


def reactance_within_instrument_band(reactance_ohm, band):
    """Whether the instrument can resolve the impedance the article shows."""
    if not isinstance(band, dict):
        raise ValueError(
            "instrument_reactance_band_ohm must be a mapping with minimum_ohm and maximum_ohm"
        )
    low = _require_positive("instrument minimum_ohm", band.get("minimum_ohm"))
    high = _require_positive("instrument maximum_ohm", band.get("maximum_ohm"))
    if not high > low:
        raise ValueError(
            "instrument maximum_ohm %g must be above minimum_ohm %g" % (high, low)
        )
    value = _require_positive("reactance_ohm", reactance_ohm)
    return _at_least(value, low) and _at_most(value, high)


def missing_evidence(method, case):
    """Required inputs the nominated method has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(
        name for name in required_evidence(method) if case.get(name) is None
    )


def assess_capacitance_method(case):
    """Full clause 5.5.3.5.2 judgement of one nominated method."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    method = nominate_single_method(case.get("nominated_method"))
    domain = method_domain(method)
    absent = missing_evidence(method, case)
    if absent:
        raise ValueError(
            "%s method %s is missing required evidence: %s"
            % (domain, method, ", ".join(absent))
        )

    expected = _require_positive(
        "expected_capacitance_f", case.get("expected_capacitance_f")
    )
    stray_fraction = stray_capacitance_fraction(
        case.get("stray_capacitance_f"), expected
    )
    instrument_accuracy = _require_fraction(
        "instrument_accuracy_fraction", case.get("instrument_accuracy_fraction")
    )
    required_uncertainty = _require_fraction(
        "required_uncertainty_fraction", case.get("required_uncertainty_fraction")
    )
    repeatability = _require_fraction(
        "fixture_repeatability_fraction",
        case.get("fixture_repeatability_fraction", 0.0),
    )

    findings = []
    detail = {}

    if not _at_most(stray_fraction, MAX_STRAY_FRACTION):
        findings.append(
            "stray and lead capacitance is %.1f%% of the article, above the %.1f%% ceiling; guard the fixture or subtract a measured open-circuit reading"
            % (stray_fraction * 100.0, MAX_STRAY_FRACTION * 100.0)
        )

    if domain == FREQUENCY_DOMAIN:
        frequency = _require_positive("test_frequency_hz", case.get("test_frequency_hz"))
        reactance = capacitive_reactance_ohm(expected, frequency)
        loss = dissipation_factor(expected, frequency, case.get("leakage_conductance_s"))
        in_band = reactance_within_instrument_band(
            reactance, case.get("instrument_reactance_band_ohm")
        )
        detail["test_frequency_hz"] = frequency
        detail["reactance_ohm"] = reactance
        detail["dissipation_factor"] = loss
        detail["reactance_within_instrument_band"] = in_band
        if not in_band:
            findings.append(
                "reactance of %.3g ohm at %.3g Hz falls outside the instrument band; move the test frequency rather than the article"
                % (reactance, frequency)
            )
        if not _at_most(loss, MAX_DISSIPATION_FACTOR):
            findings.append(
                "dissipation factor %.3f exceeds %.2f; the leakage conductance is corrupting the capacitance reading"
                % (loss, MAX_DISSIPATION_FACTOR)
            )
    else:
        tau = discharge_time_constant_s(expected, case.get("discharge_resistance_ohm"))
        samples = samples_per_time_constant(tau, case.get("recorder_sample_rate_hz"))
        spans = record_window_time_constants(case.get("record_window_s"), tau)
        detail["time_constant_s"] = tau
        detail["samples_per_time_constant"] = samples
        detail["record_window_time_constants"] = spans
        if not _at_least(samples, MIN_SAMPLES_PER_TIME_CONSTANT):
            findings.append(
                "recorder places %.1f samples in one decay constant, below the %.0f needed to fit the decay"
                % (samples, MIN_SAMPLES_PER_TIME_CONSTANT)
            )
        if not _at_least(spans, MIN_RECORD_WINDOW_TIME_CONSTANTS):
            findings.append(
                "record window spans %.2f decay constants, below the %.0f the decay needs to finish"
                % (spans, MIN_RECORD_WINDOW_TIME_CONSTANTS)
            )

    uncertainty = combined_uncertainty_fraction(
        (instrument_accuracy, stray_fraction, repeatability)
    )
    uncertainty_met = _at_most(uncertainty, required_uncertainty)
    if not uncertainty_met:
        findings.append(
            "combined uncertainty %.3f%% exceeds the required %.3f%%"
            % (uncertainty * 100.0, required_uncertainty * 100.0)
        )

    accepted = not findings
    return {
        "method": method,
        "domain": domain,
        "expected_capacitance_f": expected,
        "stray_capacitance_fraction": stray_fraction,
        "combined_uncertainty_fraction": uncertainty,
        "required_uncertainty_fraction": required_uncertainty,
        "uncertainty_met": uncertainty_met,
        "domain_detail": detail,
        "verdict": METHOD_ACCEPTED if accepted else METHOD_NOT_ACCEPTED,
        "accepted": accepted,
        "findings": findings,
    }
