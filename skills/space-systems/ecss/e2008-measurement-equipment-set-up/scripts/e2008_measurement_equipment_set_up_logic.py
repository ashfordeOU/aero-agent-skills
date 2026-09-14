#!/usr/bin/env python3
"""Equipment arrangement ahead of the second cell measurement method.

Anchor: ECSS-E-ST-20-08C clause 11.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Clause 11 offers two ways of measuring the quantity at cell level. The
second of them gets its own set-up clause because the arrangement is
part of the method rather than a preamble to it: the cell is a small,
lightly driven article, and the fixture, the shielding and the recorder
contribute as much to the number as the cell does. Nothing in the run
itself can recover an arrangement that was wrong when the run started.

Six stations have to be present and characterised before anything is
energised.

    bias-supply                     range that covers the bias the method
                                    sweeps, resolution finer than its step
    excitation-source               the drive the second method applies
    guarded-cell-fixture            a guarded, four-terminal mount whose
                                    own stray is small against the cell
    transient-recorder              sample rate and vertical resolution
                                    matched to the response, not to the
                                    trigger
    shield-and-single-point-ground  one ground reference, no loop
    cell-temperature-stage          the cell held at the reference
                                    temperature the result is quoted at

Two further conditions sit across the whole chain: every instrument has
to be inside its calibration interval, and the open and short
compensation of the fixture has to have been run and still be valid.

The order the chain is assembled in is also part of the arrangement.
Ground is bonded first so that nothing is referenced through a signal
lead, and the bias supply is energised last so that no station is
connected to a live article.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BIAS_SUPPLY = "bias-supply"
EXCITATION_SOURCE = "excitation-source"
GUARDED_FIXTURE = "guarded-cell-fixture"
TRANSIENT_RECORDER = "transient-recorder"
SHIELD_AND_GROUND = "shield-and-single-point-ground"
TEMPERATURE_STAGE = "cell-temperature-stage"

REQUIRED_STATIONS = (
    BIAS_SUPPLY,
    EXCITATION_SOURCE,
    GUARDED_FIXTURE,
    TRANSIENT_RECORDER,
    SHIELD_AND_GROUND,
    TEMPERATURE_STAGE,
)

CONNECTION_SEQUENCE = (
    "bond-the-shield-and-ground",
    "mount-the-cell-in-the-guarded-fixture",
    "connect-the-recorder-through-the-guard",
    "connect-the-excitation-source",
    "connect-the-bias-supply",
    "run-open-and-short-compensation",
    "stabilise-the-cell-temperature",
    "energise-the-bias-supply",
)

FIRST_STEP = CONNECTION_SEQUENCE[0]
LAST_STEP = CONNECTION_SEQUENCE[-1]

REFERENCE_TEMPERATURE_K = 298.15
MAX_TEMPERATURE_DEVIATION_K = 2.0
MIN_SAMPLES_PER_TRANSIENT = 20.0
MAX_QUANTISATION_FRACTION = 0.01
MAX_FIXTURE_STRAY_FRACTION = 0.05
MAX_BIAS_RESOLUTION_FRACTION = 0.1

SETUP_READY = "measurement-setup-ready"
SETUP_NOT_READY = "measurement-setup-not-ready"

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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A sample count or a quantisation fraction is a product or quotient of
    floats that can land a few units in the last place either side of a
    written limit. The limit is never relaxed; only the comparison
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


def validate_chain(chain):
    """Reduce a declared equipment chain to named, usable stations."""
    if not isinstance(chain, dict) or not chain:
        raise ValueError(
            "equipment chain must be a non-empty mapping of station to settings, "
            "got %r" % (chain,)
        )
    stations = {}
    for name, settings in chain.items():
        if name not in REQUIRED_STATIONS:
            raise ValueError(
                "unknown station %r; the arrangement is built from %s"
                % (name, ", ".join(REQUIRED_STATIONS))
            )
        if not isinstance(settings, dict):
            raise ValueError(
                "station %s must carry a mapping of settings, got %r"
                % (name, settings)
            )
        stations[name] = dict(settings)
    return stations


def missing_stations(chain):
    """Stations the arrangement still owes before anything is energised."""
    stations = validate_chain(chain)
    return tuple(name for name in REQUIRED_STATIONS if name not in stations)


def bias_supply_span_v(settings):
    """Bias range the supply can actually reach, low limit to high limit."""
    if not isinstance(settings, dict):
        raise ValueError("bias supply settings must be a mapping, got %r" % (settings,))
    low = _require_number("bias supply minimum_v", settings.get("minimum_v"))
    high = _require_number("bias supply maximum_v", settings.get("maximum_v"))
    if not high > low:
        raise ValueError(
            "bias supply maximum_v %g must be above minimum_v %g" % (high, low)
        )
    return high - low


def bias_supply_covers(settings, required_span_v):
    """Whether the supply reaches across the bias the method sweeps."""
    required = _require_positive("required_bias_span_v", required_span_v)
    return _at_least(bias_supply_span_v(settings), required)


def bias_resolution_fraction(settings, smallest_step_v):
    """Supply resolution expressed against the smallest bias step asked for."""
    if not isinstance(settings, dict):
        raise ValueError("bias supply settings must be a mapping, got %r" % (settings,))
    resolution = _require_positive(
        "bias supply resolution_v", settings.get("resolution_v")
    )
    step = _require_positive("smallest_bias_step_v", smallest_step_v)
    return resolution / step


def samples_per_transient(sample_rate_hz, transient_duration_s):
    """Samples the recorder places inside the response it has to capture."""
    rate = _require_positive("recorder sample_rate_hz", sample_rate_hz)
    duration = _require_positive("transient_duration_s", transient_duration_s)
    return rate * duration


def quantisation_step_v(full_scale_v, resolution_bits):
    """Size of one least significant bit of the recorder's vertical scale."""
    full_scale = _require_positive("recorder full_scale_v", full_scale_v)
    if not isinstance(resolution_bits, int) or isinstance(resolution_bits, bool):
        raise ValueError(
            "recorder resolution_bits must be a whole number, got %r"
            % (resolution_bits,)
        )
    if resolution_bits < 1:
        raise ValueError(
            "recorder resolution_bits must be at least one, got %d" % resolution_bits
        )
    return full_scale / float(2 ** resolution_bits)


def quantisation_fraction(full_scale_v, resolution_bits, expected_signal_v):
    """One least significant bit as a share of the signal being captured."""
    signal = _require_positive("expected_signal_v", expected_signal_v)
    return quantisation_step_v(full_scale_v, resolution_bits) / signal


def fixture_stray_fraction(stray_capacitance_f, cell_capacitance_f):
    """Share of the reading owed to the fixture rather than to the cell."""
    stray = _require_non_negative(
        "fixture stray_capacitance_f", stray_capacitance_f
    )
    cell = _require_positive("cell_capacitance_f", cell_capacitance_f)
    return stray / cell


def temperature_deviation_k(setpoint_k, reference_k=REFERENCE_TEMPERATURE_K):
    """How far the stage setpoint sits from the reference the result is quoted at."""
    setpoint = _require_positive("cell stage setpoint_k", setpoint_k)
    reference = _require_positive("reference_k", reference_k)
    return abs(setpoint - reference)


def calibration_valid(days_since_calibration, interval_days):
    """Whether an instrument is still inside its calibration interval."""
    elapsed = _require_non_negative(
        "days_since_calibration", days_since_calibration
    )
    interval = _require_positive("calibration_interval_days", interval_days)
    return _at_most(elapsed, interval)


def overdue_calibrations(chain):
    """Stations whose calibration interval has already run out."""
    stations = validate_chain(chain)
    overdue = []
    for name in REQUIRED_STATIONS:
        settings = stations.get(name)
        if settings is None:
            continue
        elapsed = settings.get("days_since_calibration")
        interval = settings.get("calibration_interval_days")
        if elapsed is None or interval is None:
            continue
        if not calibration_valid(elapsed, interval):
            overdue.append(name)
    return tuple(overdue)


def setup_sequence():
    """The order the chain is assembled in, ground first and power last."""
    return CONNECTION_SEQUENCE


def sequence_findings(proposed):
    """What a proposed assembly order gets wrong against the canonical one."""
    if not isinstance(proposed, (list, tuple)) or not proposed:
        raise ValueError(
            "proposed set-up order must be a non-empty sequence, got %r" % (proposed,)
        )
    seen = set()
    for step in proposed:
        if step not in CONNECTION_SEQUENCE:
            raise ValueError(
                "unknown set-up step %r; the sequence is built from %s"
                % (step, ", ".join(CONNECTION_SEQUENCE))
            )
        if step in seen:
            raise ValueError("set-up step %r appears more than once" % step)
        seen.add(step)

    findings = []
    absent = tuple(step for step in CONNECTION_SEQUENCE if step not in seen)
    if absent:
        findings.append("set-up order omits %s" % ", ".join(absent))

    order = {step: index for index, step in enumerate(CONNECTION_SEQUENCE)}
    steps = tuple(proposed)
    for index in range(len(steps) - 1):
        if order[steps[index]] > order[steps[index + 1]]:
            findings.append(
                "%s is assembled before %s, inverting the canonical order"
                % (steps[index], steps[index + 1])
            )
            break

    if FIRST_STEP in seen and steps[0] != FIRST_STEP:
        findings.append(
            "ground is not bonded first; every earlier station is referenced "
            "through a signal lead until it is"
        )
    if LAST_STEP in seen and steps[-1] != LAST_STEP:
        findings.append(
            "the bias supply is energised before the chain is complete; a "
            "station is being connected to a live article"
        )
    return tuple(findings)


def assess_equipment_setup(case):
    """Full clause 11.2.2 readiness judgement of one equipment arrangement."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    stations = validate_chain(case.get("chain"))
    absent = missing_stations(case.get("chain"))

    findings = []
    detail = {}

    if absent:
        findings.append(
            "arrangement is incomplete without %s" % ", ".join(absent)
        )

    required_span = _require_positive(
        "required_bias_span_v", case.get("required_bias_span_v")
    )
    smallest_step = _require_positive(
        "smallest_bias_step_v", case.get("smallest_bias_step_v")
    )
    cell_capacitance = _require_positive(
        "cell_capacitance_f", case.get("cell_capacitance_f")
    )
    transient_s = _require_positive(
        "transient_duration_s", case.get("transient_duration_s")
    )
    expected_signal = _require_positive(
        "expected_signal_v", case.get("expected_signal_v")
    )

    if BIAS_SUPPLY in stations:
        settings = stations[BIAS_SUPPLY]
        covers = bias_supply_covers(settings, required_span)
        resolution_share = bias_resolution_fraction(settings, smallest_step)
        detail["bias_supply_span_v"] = bias_supply_span_v(settings)
        detail["bias_resolution_fraction"] = resolution_share
        if not covers:
            findings.append(
                "bias supply spans %.3f V against the %.3f V the method sweeps"
                % (detail["bias_supply_span_v"], required_span)
            )
        if not _at_most(resolution_share, MAX_BIAS_RESOLUTION_FRACTION):
            findings.append(
                "bias resolution is %.1f%% of the smallest step, above the %.0f%% "
                "ceiling; the sweep cannot place its own points"
                % (resolution_share * 100.0, MAX_BIAS_RESOLUTION_FRACTION * 100.0)
            )

    if TRANSIENT_RECORDER in stations:
        settings = stations[TRANSIENT_RECORDER]
        samples = samples_per_transient(
            settings.get("sample_rate_hz"), transient_s
        )
        share = quantisation_fraction(
            settings.get("full_scale_v"),
            settings.get("resolution_bits"),
            expected_signal,
        )
        detail["samples_per_transient"] = samples
        detail["quantisation_fraction"] = share
        if not _at_least(samples, MIN_SAMPLES_PER_TRANSIENT):
            findings.append(
                "recorder places %.1f samples in the response, below the %.0f it "
                "needs to reconstruct it"
                % (samples, MIN_SAMPLES_PER_TRANSIENT)
            )
        if not _at_most(share, MAX_QUANTISATION_FRACTION):
            findings.append(
                "one recorder bit is %.2f%% of the expected signal, above the %.0f%% "
                "ceiling; the vertical scale is too coarse for this cell"
                % (share * 100.0, MAX_QUANTISATION_FRACTION * 100.0)
            )

    if GUARDED_FIXTURE in stations:
        settings = stations[GUARDED_FIXTURE]
        stray_share = fixture_stray_fraction(
            settings.get("stray_capacitance_f"), cell_capacitance
        )
        detail["fixture_stray_fraction"] = stray_share
        if not _at_most(stray_share, MAX_FIXTURE_STRAY_FRACTION):
            findings.append(
                "fixture stray is %.1f%% of the cell, above the %.0f%% ceiling; "
                "guard the mount or subtract a measured open reading"
                % (stray_share * 100.0, MAX_FIXTURE_STRAY_FRACTION * 100.0)
            )
        if not settings.get("four_terminal", False):
            findings.append(
                "fixture is not four-terminal; the lead resistance joins the cell"
            )
        if not settings.get("compensation_run", False):
            findings.append(
                "open and short compensation has not been run on the fixture"
            )

    if SHIELD_AND_GROUND in stations:
        settings = stations[SHIELD_AND_GROUND]
        detail["single_point_ground"] = bool(settings.get("single_point", False))
        if not settings.get("single_point", False):
            findings.append(
                "ground is not brought to a single point; a loop is enclosed in "
                "the measurement path"
            )

    if TEMPERATURE_STAGE in stations:
        settings = stations[TEMPERATURE_STAGE]
        deviation = temperature_deviation_k(settings.get("setpoint_k"))
        detail["temperature_deviation_k"] = deviation
        if not _at_most(deviation, MAX_TEMPERATURE_DEVIATION_K):
            findings.append(
                "cell stage sits %.2f K from the reference temperature, above the "
                "%.1f K band the result is quoted inside"
                % (deviation, MAX_TEMPERATURE_DEVIATION_K)
            )

    overdue = overdue_calibrations(case.get("chain"))
    if overdue:
        findings.append(
            "calibration interval has run out on %s" % ", ".join(overdue)
        )

    order_findings = ()
    if case.get("proposed_order") is not None:
        order_findings = sequence_findings(case.get("proposed_order"))
        findings.extend(order_findings)

    ready = not findings
    return {
        "stations_present": tuple(sorted(stations)),
        "missing_stations": absent,
        "overdue_calibrations": overdue,
        "sequence_findings": order_findings,
        "detail": detail,
        "verdict": SETUP_READY if ready else SETUP_NOT_READY,
        "ready": ready,
        "findings": findings,
    }
