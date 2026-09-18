"""Calibration arrangement set up before discharge pulses are injected into a harness.

Anchor: ECSS-E-ST-20-07C clause 5.4.13.3 (the calibration arrangement established
before discharge pulses are injected through the probe into the harness).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the calibration fixture itself: a through conductor of a stated
   characteristic impedance, terminated at both ends, with each termination
   graded by the reflection it returns into the fixture.
2. Reduce the recorded calibration pulses to a mean induced current and a
   relative spread, and compare that spread with the repeatability the
   arrangement has to show before it can be trusted as a reference.
3. Derive the probe injection loss from the drive applied to the probe and the
   current the fixture conductor carried, then invert it to obtain the drive
   setting that produces the target calibration current.
4. Confirm the derived setting is inside the generator range, confirm the
   monitor bandwidth resolves the calibration pulse edge, confirm the fixture
   calibration is still inside its validity window, and return the arrangement
   verdict with the settings the harness injection will use.
"""

import math

__all__ = [
    "LOSS_TOLERANCE_DB",
    "DEFAULT_MAX_TERMINATION_REFLECTION",
    "DEFAULT_MAX_RELATIVE_SPREAD",
    "MIN_CALIBRATION_PULSES",
    "RISE_TIME_BANDWIDTH_PRODUCT",
    "validate_fixture",
    "termination_reflection",
    "pulse_statistics",
    "injection_loss_db",
    "drive_setting_v",
    "monitor_bandwidth_hz",
    "validity_remaining_days",
    "assess_calibration",
]

# Losses are differences of logarithms: a drive that exactly reproduces the
# target current can land a few ULPs either side. Absorb the representation
# error here rather than by moving the calibration target.
LOSS_TOLERANCE_DB = 1e-9

# A termination returning more than this fraction of the incident wave makes the
# fixture conductor a resonator instead of a matched reference line.
DEFAULT_MAX_TERMINATION_REFLECTION = 0.05

# Pulse-to-pulse spread the arrangement may show and still be a reference.
DEFAULT_MAX_RELATIVE_SPREAD = 0.10

# A mean over fewer pulses than this cannot carry a repeatability statement.
MIN_CALIBRATION_PULSES = 3

# Gaussian-ish edge: the bandwidth that resolves a 10-90% rise time.
RISE_TIME_BANDWIDTH_PRODUCT = 0.35


def _positive(label, value):
    """Return a positive finite float for a calibration quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative_int(label, value):
    """Return a non-negative integer for a day count or a pulse count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def termination_reflection(termination_ohm, fixture_impedance_ohm):
    """Return the magnitude of the reflection a termination returns into the fixture."""
    load = _positive("termination_ohm", termination_ohm)
    line = _positive("fixture_impedance_ohm", fixture_impedance_ohm)
    return abs((load - line) / (load + line))


def validate_fixture(fixture):
    """Return the graded calibration fixture: impedance, both terminations, reflections.

    fixture keys: impedance_ohm, source_termination_ohm, load_termination_ohm,
    optional max_termination_reflection.
    """
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a mapping, got %r" % (fixture,))
    for key in ("impedance_ohm", "source_termination_ohm", "load_termination_ohm"):
        if key not in fixture:
            raise ValueError("fixture missing required key '%s'" % key)
    line = _positive("impedance_ohm", fixture["impedance_ohm"])
    limit = fixture.get("max_termination_reflection", DEFAULT_MAX_TERMINATION_REFLECTION)
    if not isinstance(limit, (int, float)) or isinstance(limit, bool):
        raise ValueError("max_termination_reflection must be a real number")
    limit = float(limit)
    if not 0.0 < limit < 1.0:
        raise ValueError("max_termination_reflection must lie in (0, 1), got %r" % (limit,))
    reflections = {}
    findings = []
    for key, label in (
        ("source_termination_ohm", "source"),
        ("load_termination_ohm", "load"),
    ):
        gamma = termination_reflection(fixture[key], line)
        reflections[label] = gamma
        if gamma > limit:
            findings.append(
                "%s termination returns %.4f of the incident wave against a %.4f limit; "
                "the fixture conductor is not a matched reference line" % (label, gamma, limit)
            )
    return {
        "impedance_ohm": line,
        "reflections": reflections,
        "max_termination_reflection": limit,
        "findings": findings,
        "matched": not findings,
    }


def pulse_statistics(currents_a, max_relative_spread=DEFAULT_MAX_RELATIVE_SPREAD):
    """Return mean, extremes and relative spread of the recorded calibration currents."""
    if not isinstance(currents_a, (list, tuple)):
        raise ValueError("currents_a must be a sequence of measured currents")
    if len(currents_a) < MIN_CALIBRATION_PULSES:
        raise ValueError(
            "a repeatability statement needs at least %d calibration pulses, got %d"
            % (MIN_CALIBRATION_PULSES, len(currents_a))
        )
    if not isinstance(max_relative_spread, (int, float)) or isinstance(
        max_relative_spread, bool
    ):
        raise ValueError("max_relative_spread must be a real number")
    limit = float(max_relative_spread)
    if not 0.0 < limit < 1.0:
        raise ValueError("max_relative_spread must lie in (0, 1), got %r" % (limit,))
    values = [_positive("calibration current", value) for value in currents_a]
    mean = sum(values) / float(len(values))
    lowest = min(values)
    highest = max(values)
    spread = (highest - lowest) / mean
    return {
        "count": len(values),
        "mean_a": mean,
        "min_a": lowest,
        "max_a": highest,
        "relative_spread": spread,
        "max_relative_spread": limit,
        "repeatable": spread <= limit,
    }


def injection_loss_db(drive_voltage_v, measured_current_a, fixture_impedance_ohm):
    """Return the probe injection loss in dB from a calibration shot.

    The fixture converts the injected current back into an equivalent voltage
    through its own impedance, so the loss is the ratio of the drive applied at
    the probe to the voltage that current represents on the fixture conductor.
    """
    drive = _positive("drive_voltage_v", drive_voltage_v)
    current = _positive("measured_current_a", measured_current_a)
    line = _positive("fixture_impedance_ohm", fixture_impedance_ohm)
    return 20.0 * math.log10(drive / (current * line))


def drive_setting_v(target_current_a, loss_db, fixture_impedance_ohm):
    """Return the generator drive that produces a target calibration current."""
    target = _positive("target_current_a", target_current_a)
    line = _positive("fixture_impedance_ohm", fixture_impedance_ohm)
    if not isinstance(loss_db, (int, float)) or isinstance(loss_db, bool):
        raise ValueError("loss_db must be a real number, got %r" % (loss_db,))
    loss = float(loss_db)
    if not math.isfinite(loss):
        raise ValueError("loss_db must be finite, got %r" % (loss_db,))
    return target * line * math.pow(10.0, loss / 20.0)


def monitor_bandwidth_hz(rise_time_s):
    """Return the monitor bandwidth in Hz needed to resolve a calibration pulse edge."""
    return RISE_TIME_BANDWIDTH_PRODUCT / _positive("rise_time_s", rise_time_s)


def validity_remaining_days(age_days, interval_days):
    """Return the days of calibration validity left; negative once the window has closed."""
    age = _non_negative_int("age_days", age_days)
    interval = _non_negative_int("interval_days", interval_days)
    if interval < 1:
        raise ValueError("interval_days must be at least 1, got %r" % (interval_days,))
    return interval - age


def assess_calibration(spec):
    """Run the full clause 5.4.13.3 calibration-arrangement assessment.

    spec keys: fixture, calibration_drive_v, measured_currents_a,
    target_current_a, generator_max_v, pulse_rise_time_s,
    monitor_bandwidth_hz, calibration_age_days, calibration_interval_days,
    optional max_relative_spread.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "fixture",
        "calibration_drive_v",
        "measured_currents_a",
        "target_current_a",
        "generator_max_v",
        "pulse_rise_time_s",
        "monitor_bandwidth_hz",
        "calibration_age_days",
        "calibration_interval_days",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    fixture = validate_fixture(spec["fixture"])
    statistics = pulse_statistics(
        spec["measured_currents_a"],
        spec.get("max_relative_spread", DEFAULT_MAX_RELATIVE_SPREAD),
    )
    loss = injection_loss_db(
        spec["calibration_drive_v"], statistics["mean_a"], fixture["impedance_ohm"]
    )
    setting = drive_setting_v(spec["target_current_a"], loss, fixture["impedance_ohm"])
    generator_max = _positive("generator_max_v", spec["generator_max_v"])
    needed_bandwidth = monitor_bandwidth_hz(spec["pulse_rise_time_s"])
    declared_bandwidth = _positive("monitor_bandwidth_hz", spec["monitor_bandwidth_hz"])
    remaining = validity_remaining_days(
        spec["calibration_age_days"], spec["calibration_interval_days"]
    )

    findings = list(fixture["findings"])
    limitations = []
    if not statistics["repeatable"]:
        findings.append(
            "calibration pulses spread %.4f of the mean against a %.4f limit; the "
            "arrangement is not yet a reference"
            % (statistics["relative_spread"], statistics["max_relative_spread"])
        )
    over_range = setting > generator_max and not math.isclose(
        setting, generator_max, rel_tol=1e-12, abs_tol=0.0
    )
    if over_range:
        findings.append(
            "the %.1f V drive needed for a %.4g A calibration current exceeds the %.1f V "
            "the generator can produce"
            % (setting, spec["target_current_a"], generator_max)
        )
    if declared_bandwidth < needed_bandwidth and not math.isclose(
        declared_bandwidth, needed_bandwidth, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "monitor bandwidth of %.4g Hz cannot resolve the %.4g Hz edge of the "
            "calibration pulse" % (declared_bandwidth, needed_bandwidth)
        )
    if remaining < 0:
        findings.append(
            "the fixture calibration closed %d days ago; the arrangement has no "
            "traceable reference" % (-remaining,)
        )
    elif remaining <= 30:
        limitations.append(
            "the fixture calibration has %d days left; a long campaign will outlast it"
            % remaining
        )
    if setting > generator_max * 0.9 and not over_range:
        limitations.append(
            "the drive setting uses %.1f%% of the generator range" % (100.0 * setting / generator_max)
        )
    return {
        "fixture": fixture,
        "pulse_statistics": statistics,
        "injection_loss_db": loss,
        "drive_setting_v": setting,
        "generator_max_v": generator_max,
        "required_monitor_bandwidth_hz": needed_bandwidth,
        "declared_monitor_bandwidth_hz": declared_bandwidth,
        "validity_remaining_days": remaining,
        "findings": findings,
        "limitations": limitations,
        "arrangement_ready": not findings,
    }
