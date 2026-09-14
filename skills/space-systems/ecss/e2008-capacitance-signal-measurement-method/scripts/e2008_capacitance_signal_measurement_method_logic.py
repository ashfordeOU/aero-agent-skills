#!/usr/bin/env python3
"""Preferred signal acquisition for a solar cell capacitance measurement.

Anchor: ECSS-E-ST-20-08C clause 11.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Measuring the capacitance of a solar cell means sensing a small
alternating current through a device that is, electrically, almost a
pure reactance. The clause states a preference: the signal is taken
across a shunt. A shunt is a resistor in the return path whose voltage
drop is the current, so the transfer is a single number, flat in
frequency, traceable to a resistance standard, and it adds nothing to
the loop but its own value. The alternatives -- a current transformer,
a Rogowski coil, a Hall-effect probe, a series electrometer -- all
insert a transfer function of their own, and the capacitance that comes
out inherits that transfer function's errors.

A preference is not a prohibition. An alternative pickup may be used,
but the preference is only discharged when the alternative carries a
recorded justification and the acquisition path still meets the same
numeric conditions the shunt would have had to meet:

    burden          the sensing element must stay small against the
                    reactance the cell presents at the test frequency,
                    or the article is being measured in series with the
                    instrument
    bandwidth       the sensing resistance works into the cable and
                    amplifier input capacitance, and that corner has to
                    sit well above the test frequency, otherwise the
                    path is rolling off inside the measurement band
    purity          a shunt stops being a resistor above R / (2 pi L);
                    its own self-inductance has to put that corner out
                    of the band too
    level           the voltage the pickup delivers has to stand clear
                    of the amplifier noise floor by a stated margin

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SHUNT_TECHNIQUE = "shunt"

ALTERNATIVE_TECHNIQUES = (
    "current-transformer",
    "hall-effect-probe",
    "rogowski-coil",
    "series-electrometer",
)

ACCEPTED_TECHNIQUES = (SHUNT_TECHNIQUE,) + ALTERNATIVE_TECHNIQUES

MAX_SHUNT_BURDEN_FRACTION = 0.02
MIN_CORNER_DECADES_ABOVE_TEST = 1.0
MIN_SIGNAL_TO_NOISE_DB = 20.0

REQUIRED_EVIDENCE_SHUNT = (
    "amplifier_noise_voltage_v",
    "cell_capacitance_f",
    "input_capacitance_f",
    "sense_resistance_ohm",
    "shunt_inductance_h",
    "signal_current_a",
    "test_frequency_hz",
)

REQUIRED_EVIDENCE_ALTERNATIVE = (
    "amplifier_noise_voltage_v",
    "cell_capacitance_f",
    "input_capacitance_f",
    "justification",
    "pickup_bandwidth_hz",
    "sense_resistance_ohm",
    "signal_current_a",
    "test_frequency_hz",
)

ACQUISITION_ACCEPTED = "signal-acquisition-accepted"
ACQUISITION_NOT_ACCEPTED = "signal-acquisition-not-accepted"

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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A corner frequency reached through a logarithm can land a few units
    in the last place either side of a limit written as a whole number
    of decades. The limit is never relaxed; only the comparison
    tolerates the representation error, which is why no caller uses a
    bare >= on a derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def technique_is_preferred(technique):
    """Whether the nominated pickup is the one the clause prefers."""
    if technique == SHUNT_TECHNIQUE:
        return True
    if technique in ALTERNATIVE_TECHNIQUES:
        return False
    raise ValueError(
        "unknown acquisition technique %r; accepted techniques are %s"
        % (technique, ", ".join(ACCEPTED_TECHNIQUES))
    )


def required_evidence(technique):
    """Inputs the nominated pickup has to bring before it can be judged."""
    if technique_is_preferred(technique):
        return tuple(sorted(REQUIRED_EVIDENCE_SHUNT))
    return tuple(sorted(REQUIRED_EVIDENCE_ALTERNATIVE))


def missing_evidence(technique, case):
    """Required inputs the nominated pickup has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(
        name for name in required_evidence(technique) if case.get(name) is None
    )


def cell_reactance_ohm(capacitance_f, frequency_hz):
    """Magnitude of the reactance the cell presents at the test frequency."""
    capacitance = _require_positive("cell_capacitance_f", capacitance_f)
    frequency = _require_positive("test_frequency_hz", frequency_hz)
    return 1.0 / (2.0 * math.pi * frequency * capacitance)


def sense_burden_fraction(sense_resistance_ohm, reactance_ohm):
    """Share of the loop impedance owed to the sensing element."""
    resistance = _require_positive("sense_resistance_ohm", sense_resistance_ohm)
    reactance = _require_positive("reactance_ohm", reactance_ohm)
    return resistance / reactance


def acquisition_corner_frequency_hz(sense_resistance_ohm, input_capacitance_f):
    """Corner the sensing resistance forms with the cable and input load.

    This is the bandwidth of the sense node itself and it is independent
    of the article: the same shunt into a longer cable rolls off at a
    lower frequency while the cell is unchanged.
    """
    resistance = _require_positive("sense_resistance_ohm", sense_resistance_ohm)
    capacitance = _require_positive("input_capacitance_f", input_capacitance_f)
    return 1.0 / (2.0 * math.pi * resistance * capacitance)


def shunt_inductive_corner_hz(sense_resistance_ohm, inductance_h):
    """Frequency above which a shunt stops behaving as a resistor.

    The self-inductance of the shunt puts a zero at R / (2 pi L). A
    shunt with no measurable self-inductance is reported as unbounded
    rather than as a division by zero.
    """
    resistance = _require_positive("sense_resistance_ohm", sense_resistance_ohm)
    inductance = _require_non_negative("shunt_inductance_h", inductance_h)
    if inductance == 0.0:
        return math.inf
    return resistance / (2.0 * math.pi * inductance)


def corner_decades_above(corner_hz, test_frequency_hz):
    """How many decades a corner sits above the test frequency."""
    frequency = _require_positive("test_frequency_hz", test_frequency_hz)
    if corner_hz == math.inf:
        return math.inf
    corner = _require_positive("corner_hz", corner_hz)
    return math.log10(corner / frequency)


def signal_voltage_v(signal_current_a, sense_resistance_ohm):
    """Voltage the sensing element delivers for the sensed current."""
    current = _require_positive("signal_current_a", signal_current_a)
    resistance = _require_positive("sense_resistance_ohm", sense_resistance_ohm)
    return current * resistance


def signal_to_noise_db(signal_v, noise_v):
    """Margin of the delivered signal over the amplifier noise floor."""
    signal = _require_positive("signal_voltage_v", signal_v)
    noise = _require_positive("amplifier_noise_voltage_v", noise_v)
    return 20.0 * math.log10(signal / noise)


def justification_recorded(justification):
    """Whether a non-shunt pickup carries a usable written justification."""
    if not isinstance(justification, str):
        raise ValueError(
            "justification must be recorded as text, got %r" % (justification,)
        )
    return bool(justification.strip())


def assess_signal_acquisition(case):
    """Full clause 11.1.2 judgement of one nominated acquisition path."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    technique = case.get("technique")
    preferred = technique_is_preferred(technique)
    absent = missing_evidence(technique, case)
    if absent:
        raise ValueError(
            "acquisition technique %s is missing required evidence: %s"
            % (technique, ", ".join(absent))
        )

    capacitance = _require_positive("cell_capacitance_f", case.get("cell_capacitance_f"))
    frequency = _require_positive("test_frequency_hz", case.get("test_frequency_hz"))
    sense_resistance = _require_positive(
        "sense_resistance_ohm", case.get("sense_resistance_ohm")
    )

    reactance = cell_reactance_ohm(capacitance, frequency)
    burden = sense_burden_fraction(sense_resistance, reactance)
    corner = acquisition_corner_frequency_hz(
        sense_resistance, case.get("input_capacitance_f")
    )
    corner_decades = corner_decades_above(corner, frequency)
    signal = signal_voltage_v(case.get("signal_current_a"), sense_resistance)
    snr = signal_to_noise_db(signal, case.get("amplifier_noise_voltage_v"))

    findings = []
    detail = {
        "cell_reactance_ohm": reactance,
        "sense_burden_fraction": burden,
        "acquisition_corner_frequency_hz": corner,
        "acquisition_corner_decades_above_test": corner_decades,
        "signal_voltage_v": signal,
        "signal_to_noise_db": snr,
    }

    if not _at_most(burden, MAX_SHUNT_BURDEN_FRACTION):
        findings.append(
            "sensing element carries %.2f%% of the loop impedance, above the %.2f%% ceiling; the instrument is being measured with the cell"
            % (burden * 100.0, MAX_SHUNT_BURDEN_FRACTION * 100.0)
        )

    if not _at_least(corner_decades, MIN_CORNER_DECADES_ABOVE_TEST):
        findings.append(
            "acquisition corner sits %.3f decades above the test frequency, below the %.1f needed to keep the roll-off out of the band"
            % (corner_decades, MIN_CORNER_DECADES_ABOVE_TEST)
        )

    if preferred:
        inductive_corner = shunt_inductive_corner_hz(
            sense_resistance, case.get("shunt_inductance_h")
        )
        inductive_decades = corner_decades_above(inductive_corner, frequency)
        detail["shunt_inductive_corner_hz"] = inductive_corner
        detail["shunt_inductive_decades_above_test"] = inductive_decades
        if not _at_least(inductive_decades, MIN_CORNER_DECADES_ABOVE_TEST):
            findings.append(
                "shunt self-inductance puts its resistive limit %.3f decades above the test frequency, below the %.1f required; the shunt is not a resistor in this band"
                % (inductive_decades, MIN_CORNER_DECADES_ABOVE_TEST)
            )
    else:
        pickup_bandwidth = _require_positive(
            "pickup_bandwidth_hz", case.get("pickup_bandwidth_hz")
        )
        pickup_decades = corner_decades_above(pickup_bandwidth, frequency)
        recorded = justification_recorded(case.get("justification"))
        detail["pickup_bandwidth_hz"] = pickup_bandwidth
        detail["pickup_decades_above_test"] = pickup_decades
        detail["justification_recorded"] = recorded
        if not recorded:
            findings.append(
                "technique %s departs from the preferred shunt with no recorded justification; the preference is not discharged by silence"
                % (technique,)
            )
        if not _at_least(pickup_decades, MIN_CORNER_DECADES_ABOVE_TEST):
            findings.append(
                "pickup bandwidth reaches only %.3f decades above the test frequency, below the %.1f required of the path it replaces"
                % (pickup_decades, MIN_CORNER_DECADES_ABOVE_TEST)
            )

    if not _at_least(snr, MIN_SIGNAL_TO_NOISE_DB):
        findings.append(
            "signal stands %.2f dB over the amplifier noise floor, below the %.0f dB margin; raise the sensed level rather than averaging longer"
            % (snr, MIN_SIGNAL_TO_NOISE_DB)
        )

    accepted = not findings
    return {
        "technique": technique,
        "preferred_technique": preferred,
        "test_frequency_hz": frequency,
        "detail": detail,
        "verdict": ACQUISITION_ACCEPTED if accepted else ACQUISITION_NOT_ACCEPTED,
        "accepted": accepted,
        "findings": findings,
    }
