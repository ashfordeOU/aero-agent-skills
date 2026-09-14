#!/usr/bin/env python3
"""Equivalent network elements from the measured impedance of a cell.

Anchor: ECSS-E-ST-20-08C clause 11.1.4.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What an impedance meter actually obtains at one frequency is two
numbers: a magnitude and a phase. A solar cell is not a capacitor, so
those two numbers do not name a capacitance on their own. They have to
be resolved into an equivalent network first, and there are two
equivalent networks that fit the same measurement exactly:

    series      a resistance R_s in series with a capacitance C_s
    parallel    a resistance R_p across a capacitance C_p

Both reproduce the measured impedance at the measurement frequency and
neither is more correct than the other. They are, however, different
numbers. The gap between C_s and C_p grows with the loss of the cell as
D squared over one plus D squared, so a capacitance quoted without
naming its network is only unambiguous while the cell is nearly
lossless. The derivation therefore produces both forms, the loss terms
that connect them, and the spread between them.

A third element sits outside both forms: the contact and lead
resistance of the fixture. It adds to the measured series resistance
and belongs to the harness, not to the cell, so it is subtracted before
the cell's own network is reported.

The derivation closes on itself. Rebuilding the impedance from the
derived parallel pair has to return the magnitude and phase that went
in; a residual above representation error means the resolution, not the
measurement, is wrong.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_EVIDENCE = (
    "impedance_magnitude_ohm",
    "phase_deg",
    "test_frequency_hz",
)

MAX_UNSTATED_NETWORK_SPREAD = 0.01
MAX_CONTACT_RESISTANCE_SHARE = 0.5
MAX_READOUT_DEVIATION_FRACTION = 0.02
MAX_CLOSURE_RESIDUAL_FRACTION = 1.0e-9

NETWORK_DERIVED = "equivalent-network-derived"
NETWORK_NOT_DERIVED = "equivalent-network-not-derived"

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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A spread and a deviation are both quotients of floats that can land
    a few units in the last place either side of a limit written as a
    round fraction. The limit is never relaxed; only the comparison
    tolerates the representation error, which is why no caller uses a
    bare <= on a derived float.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def capacitive_phase_deg(phase_deg):
    """Validate that the measured phase describes a capacitive article.

    A solar cell under a small-signal capacitance measurement lags
    between zero and a quarter turn. A phase at or past either end is
    not a lossy capacitor: zero is a pure resistance, a quarter turn is
    a lossless capacitance that no real cell presents, and a positive
    phase is an inductive fixture the derivation cannot resolve.
    """
    if not _is_finite_number(phase_deg):
        raise ValueError("phase_deg must be a finite number, got %r" % (phase_deg,))
    value = float(phase_deg)
    if value >= 0.0:
        raise ValueError(
            "phase_deg %g is not capacitive; a cell measurement lags between -90 and 0"
            % (value,)
        )
    if value <= -90.0:
        raise ValueError(
            "phase_deg %g is at or past a quarter turn; no real cell is lossless"
            % (value,)
        )
    return value


def series_components(impedance_magnitude_ohm, phase_deg):
    """Resolve magnitude and phase into the series resistance and reactance."""
    magnitude = _require_positive(
        "impedance_magnitude_ohm", impedance_magnitude_ohm
    )
    phase = capacitive_phase_deg(phase_deg)
    radians = math.radians(phase)
    return magnitude * math.cos(radians), magnitude * math.sin(radians)


def series_capacitance_f(series_reactance_ohm, frequency_hz):
    """Series-form capacitance behind a capacitive reactance."""
    if not _is_finite_number(series_reactance_ohm):
        raise ValueError(
            "series_reactance_ohm must be a finite number, got %r"
            % (series_reactance_ohm,)
        )
    if series_reactance_ohm >= 0.0:
        raise ValueError(
            "series_reactance_ohm %g is not capacitive" % (series_reactance_ohm,)
        )
    frequency = _require_positive("test_frequency_hz", frequency_hz)
    return -1.0 / (2.0 * math.pi * frequency * float(series_reactance_ohm))


def dissipation_factor(series_resistance_ohm, series_reactance_ohm):
    """Loss tangent of the measurement, the series resistance over reactance."""
    resistance = _require_non_negative(
        "series_resistance_ohm", series_resistance_ohm
    )
    if not _is_finite_number(series_reactance_ohm) or series_reactance_ohm >= 0.0:
        raise ValueError(
            "series_reactance_ohm %r is not capacitive" % (series_reactance_ohm,)
        )
    return resistance / abs(float(series_reactance_ohm))


def quality_factor(dissipation):
    """Reciprocal of the loss tangent."""
    value = _require_positive("dissipation_factor", dissipation)
    return 1.0 / value


def parallel_resistance_ohm(series_resistance_ohm, quality):
    """Loss resistance of the parallel form that fits the same measurement."""
    resistance = _require_positive(
        "series_resistance_ohm", series_resistance_ohm
    )
    q = _require_positive("quality_factor", quality)
    return resistance * (1.0 + q * q)


def parallel_capacitance_f(series_capacitance, dissipation):
    """Capacitance of the parallel form that fits the same measurement."""
    capacitance = _require_positive("series_capacitance_f", series_capacitance)
    d = _require_non_negative("dissipation_factor", dissipation)
    return capacitance / (1.0 + d * d)


def network_spread_fraction(series_capacitance, parallel_capacitance):
    """Gap between the two equivalent capacitances, relative to the series one."""
    series = _require_positive("series_capacitance_f", series_capacitance)
    parallel = _require_positive("parallel_capacitance_f", parallel_capacitance)
    return abs(series - parallel) / series


def contact_corrected_resistance_ohm(series_resistance_ohm, contact_resistance_ohm):
    """Series resistance left once the harness contribution is removed."""
    resistance = _require_positive(
        "series_resistance_ohm", series_resistance_ohm
    )
    contact = _require_non_negative(
        "contact_resistance_ohm", contact_resistance_ohm
    )
    if contact >= resistance:
        raise ValueError(
            "contact_resistance_ohm %g is not below the measured series resistance %g; the declared harness term cannot exceed what was measured"
            % (contact, resistance)
        )
    return resistance - contact


def contact_resistance_share(series_resistance_ohm, contact_resistance_ohm):
    """Share of the measured series resistance owed to the harness."""
    resistance = _require_positive(
        "series_resistance_ohm", series_resistance_ohm
    )
    contact = _require_non_negative(
        "contact_resistance_ohm", contact_resistance_ohm
    )
    return contact / resistance


def parallel_network_impedance(parallel_capacitance, parallel_resistance, frequency_hz):
    """Rebuild magnitude and phase from a derived parallel pair."""
    capacitance = _require_positive("parallel_capacitance_f", parallel_capacitance)
    resistance = _require_positive("parallel_resistance_ohm", parallel_resistance)
    frequency = _require_positive("test_frequency_hz", frequency_hz)
    conductance = 1.0 / resistance
    susceptance = 2.0 * math.pi * frequency * capacitance
    admittance = math.hypot(conductance, susceptance)
    magnitude = 1.0 / admittance
    phase = -math.degrees(math.atan2(susceptance, conductance))
    return magnitude, phase


def closure_residual_fraction(measured_magnitude_ohm, rebuilt_magnitude_ohm):
    """Relative gap between the measurement and the rebuilt impedance."""
    measured = _require_positive(
        "impedance_magnitude_ohm", measured_magnitude_ohm
    )
    rebuilt = _require_positive("rebuilt_magnitude_ohm", rebuilt_magnitude_ohm)
    return abs(measured - rebuilt) / measured


def readout_deviation_fraction(derived_value, declared_value):
    """Relative gap between a derived element and an instrument readout."""
    derived = _require_positive("derived_value", derived_value)
    declared = _require_positive("declared_value", declared_value)
    return abs(derived - declared) / derived


def missing_evidence(case):
    """Required measurement inputs the case has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(name for name in REQUIRED_EVIDENCE if case.get(name) is None)


def derive_equivalent_network(case):
    """Full clause 11.1.4.2.1 derivation from one impedance measurement."""
    absent = missing_evidence(case)
    if absent:
        raise ValueError(
            "equivalent network derivation is missing required evidence: %s"
            % (", ".join(absent),)
        )

    magnitude = _require_positive(
        "impedance_magnitude_ohm", case.get("impedance_magnitude_ohm")
    )
    frequency = _require_positive("test_frequency_hz", case.get("test_frequency_hz"))
    r_series, x_series = series_components(magnitude, case.get("phase_deg"))

    c_series = series_capacitance_f(x_series, frequency)
    d = dissipation_factor(r_series, x_series)
    q = quality_factor(d)
    r_parallel = parallel_resistance_ohm(r_series, q)
    c_parallel = parallel_capacitance_f(c_series, d)
    spread = network_spread_fraction(c_series, c_parallel)

    contact = _require_non_negative(
        "contact_resistance_ohm", case.get("contact_resistance_ohm", 0.0)
    )
    r_cell = contact_corrected_resistance_ohm(r_series, contact)
    share = contact_resistance_share(r_series, contact)

    rebuilt_magnitude, rebuilt_phase = parallel_network_impedance(
        c_parallel, r_parallel, frequency
    )
    residual = closure_residual_fraction(magnitude, rebuilt_magnitude)

    findings = []

    if not _at_most(spread, MAX_UNSTATED_NETWORK_SPREAD):
        findings.append(
            "series and parallel capacitance differ by %.2f%%, beyond the %.2f%% at which the two forms can be used interchangeably; the figure has to name its network"
            % (spread * 100.0, MAX_UNSTATED_NETWORK_SPREAD * 100.0)
        )

    if not _at_most(share, MAX_CONTACT_RESISTANCE_SHARE):
        findings.append(
            "harness contributes %.1f%% of the measured series resistance, above the %.0f%% ceiling; the fixture is dominating the element being derived"
            % (share * 100.0, MAX_CONTACT_RESISTANCE_SHARE * 100.0)
        )

    if not _at_most(residual, MAX_CLOSURE_RESIDUAL_FRACTION):
        findings.append(
            "rebuilding the impedance from the derived parallel pair misses the measurement by %.3g; the resolution, not the measurement, is at fault"
            % (residual,)
        )

    readout_deviation = None
    declared_parallel = case.get("instrument_parallel_capacitance_f")
    if declared_parallel is not None:
        readout_deviation = readout_deviation_fraction(c_parallel, declared_parallel)
        if not _at_most(readout_deviation, MAX_READOUT_DEVIATION_FRACTION):
            findings.append(
                "instrument parallel readout is %.2f%% from the derived parallel capacitance, beyond the %.0f%% tolerance; the instrument and the derivation are not resolving the same network"
                % (readout_deviation * 100.0, MAX_READOUT_DEVIATION_FRACTION * 100.0)
            )

    derived = not findings
    return {
        "test_frequency_hz": frequency,
        "series_resistance_ohm": r_series,
        "series_reactance_ohm": x_series,
        "series_capacitance_f": c_series,
        "dissipation_factor": d,
        "quality_factor": q,
        "parallel_resistance_ohm": r_parallel,
        "parallel_capacitance_f": c_parallel,
        "network_spread_fraction": spread,
        "contact_resistance_share": share,
        "cell_series_resistance_ohm": r_cell,
        "rebuilt_magnitude_ohm": rebuilt_magnitude,
        "rebuilt_phase_deg": rebuilt_phase,
        "closure_residual_fraction": residual,
        "readout_deviation_fraction": readout_deviation,
        "verdict": NETWORK_DERIVED if derived else NETWORK_NOT_DERIVED,
        "derived": derived,
        "findings": findings,
    }
