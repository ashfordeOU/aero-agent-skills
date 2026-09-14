#!/usr/bin/env python3
"""Working standards read in short-circuit mode under a pulsed simulator.

Anchor: ECSS-E-ST-20-08C clause 10.2.2.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks whether a working standard answers adequately in short
circuit while a flash simulator illuminates it. A steady-state source
gives the cell as long as it needs to reach short-circuit current; a
flash gives it a plateau a few milliseconds wide, and the reading is
only worth taking if three things hold at once.

    the standard settles        the short-circuit loop has a time
                                constant set by the cell capacitance and
                                by the resistance in series with it, and
                                the current has to get within the
                                declared tolerance of its final value
                                before the window opens
    the window sits inside      the sampling window opens after that
    the usable plateau          settling and closes before the plateau
                                ends, so the reading never touches the
                                rise or the decay of the flash
    the load is a real short    the shunt develops a voltage across the
                                standard; if that voltage is not small
                                against the open-circuit voltage, the
                                operating point has moved off short
                                circuit and the current read is not Isc

Unit convention. Resistance is in ohms and capacitance in microfarads,
so their product is a time constant in microseconds with no conversion
factor. Flash timing is quoted in milliseconds as simulators report it
and is converted once, at the boundary.

Load connection. A four-wire shunt senses the standard at the cell; a
two-wire shunt puts the lead resistance inside the measured loop, which
both slows the settling and lifts the operating point off short circuit.
It is reported as a defect in its own right rather than folded into the
time constant, because the repair is a re-wire and not a longer window.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LOAD_CONNECTIONS = ("four-wire-shunt", "two-wire-shunt")

STANDARD_GRADES = ("primary-reference", "secondary-reference", "working-standard")

RESPONSE_DEFECTS = (
    "two-wire-shunt-load",
    "settling-not-complete",
    "window-opens-before-plateau",
    "window-closes-after-plateau",
    "plateau-too-short-to-settle",
    "shunt-voltage-off-short-circuit",
    "plateau-ripple-out-of-band",
    "flash-repeatability-out-of-band",
)

ADEQUATE_VERDICT = "pulsed-response-adequate"
INADEQUATE_VERDICT = "pulsed-response-inadequate"

DEFAULT_SETTLING_TOLERANCE = 0.001
DEFAULT_SHUNT_VOLTAGE_FRACTION = 0.02
DEFAULT_PLATEAU_RIPPLE_PERCENT = 1.0
DEFAULT_REPEATABILITY_PERCENT = 0.5

DEFAULT_ACCEPTANCE_LIMITS = {
    "settling_tolerance": DEFAULT_SETTLING_TOLERANCE,
    "shunt_voltage_fraction": DEFAULT_SHUNT_VOLTAGE_FRACTION,
    "plateau_ripple_percent": DEFAULT_PLATEAU_RIPPLE_PERCENT,
    "repeatability_percent": DEFAULT_REPEATABILITY_PERCENT,
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


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A settling time built from an exponential and a plateau width read
    from a simulator can land a few units in the last place apart on
    two platforms for the same hardware. The bound is never loosened;
    only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_limits(limits):
    """Check the acceptance limits are present, finite and in range."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    missing = set(DEFAULT_ACCEPTANCE_LIMITS) - set(limits)
    if missing:
        raise ValueError("limits are missing: %s" % ", ".join(sorted(missing)))
    tolerance = _require_positive("settling_tolerance", limits["settling_tolerance"])
    if tolerance >= 1.0:
        raise ValueError(
            "settling_tolerance must be below one, got %r" % (limits["settling_tolerance"],)
        )
    fraction = _require_positive(
        "shunt_voltage_fraction", limits["shunt_voltage_fraction"]
    )
    if fraction >= 1.0:
        raise ValueError(
            "shunt_voltage_fraction must be below one, got %r"
            % (limits["shunt_voltage_fraction"],)
        )
    _require_positive("plateau_ripple_percent", limits["plateau_ripple_percent"])
    _require_positive("repeatability_percent", limits["repeatability_percent"])
    return limits


def validate_standard(record):
    """Normalise one working-standard record, rejecting an unusable one."""
    if not isinstance(record, dict):
        raise ValueError("standard must be a mapping, got %r" % (record,))
    identifier = _require_identifier("standard id", record.get("id"))
    grade = _require_choice(
        "grade of %s" % identifier,
        record.get("grade", "working-standard"),
        STANDARD_GRADES,
    )
    connection = _require_choice(
        "load_connection of %s" % identifier,
        record.get("load_connection", "four-wire-shunt"),
        LOAD_CONNECTIONS,
    )
    return {
        "id": identifier,
        "grade": grade,
        "load_connection": connection,
        "capacitance_uf": _require_positive(
            "capacitance_uf of %s" % identifier, record.get("capacitance_uf")
        ),
        "series_resistance_ohm": _require_non_negative(
            "series_resistance_ohm of %s" % identifier,
            record.get("series_resistance_ohm"),
        ),
        "shunt_resistance_ohm": _require_positive(
            "shunt_resistance_ohm of %s" % identifier,
            record.get("shunt_resistance_ohm"),
        ),
        "short_circuit_current_a": _require_positive(
            "short_circuit_current_a of %s" % identifier,
            record.get("short_circuit_current_a"),
        ),
        "open_circuit_voltage_v": _require_positive(
            "open_circuit_voltage_v of %s" % identifier,
            record.get("open_circuit_voltage_v"),
        ),
    }


def validate_pulse(record):
    """Normalise one flash description, rejecting an impossible timing."""
    if not isinstance(record, dict):
        raise ValueError("pulse must be a mapping, got %r" % (record,))
    plateau_start = _require_non_negative(
        "plateau_start_ms", record.get("plateau_start_ms")
    )
    plateau_end = _require_positive("plateau_end_ms", record.get("plateau_end_ms"))
    if not plateau_end > plateau_start:
        raise ValueError(
            "plateau_end_ms %r must follow plateau_start_ms %r"
            % (plateau_end, plateau_start)
        )
    window_start = _require_non_negative(
        "window_start_ms", record.get("window_start_ms")
    )
    window_length = _require_positive(
        "window_length_ms", record.get("window_length_ms")
    )
    return {
        "plateau_start_ms": plateau_start,
        "plateau_end_ms": plateau_end,
        "window_start_ms": window_start,
        "window_length_ms": window_length,
        "window_end_ms": window_start + window_length,
        "plateau_length_ms": plateau_end - plateau_start,
        "plateau_ripple_percent": _require_non_negative(
            "plateau_ripple_percent", record.get("plateau_ripple_percent", 0.0)
        ),
    }


def response_time_constant_us(standard):
    """Short-circuit time constant of the standard, in microseconds.

    Ohms times microfarads is microseconds, so the loop resistance and
    the cell capacitance multiply with no conversion factor.
    """
    entry = standard if "capacitance_uf" in standard else validate_standard(standard)
    loop_resistance = entry["series_resistance_ohm"] + entry["shunt_resistance_ohm"]
    if loop_resistance <= 0.0:
        raise ValueError("the short-circuit loop has no resistance to form a constant")
    return loop_resistance * entry["capacitance_uf"]


def settling_time_us(standard, tolerance=DEFAULT_SETTLING_TOLERANCE):
    """Time for the short-circuit current to reach the declared tolerance."""
    fraction = _require_positive("tolerance", tolerance)
    if fraction >= 1.0:
        raise ValueError("tolerance must be below one, got %r" % (tolerance,))
    return response_time_constant_us(standard) * -math.log(fraction)


def residual_response_error(standard, delay_us):
    """Fractional shortfall still left after a delay, one being no settling."""
    elapsed = _require_non_negative("delay_us", delay_us)
    return math.exp(-elapsed / response_time_constant_us(standard))


def shunt_voltage_v(standard):
    """Voltage the shunt develops across the standard at short circuit."""
    entry = standard if "shunt_resistance_ohm" in standard else validate_standard(standard)
    return entry["short_circuit_current_a"] * entry["shunt_resistance_ohm"]


def shunt_voltage_fraction(standard):
    """Shunt voltage as a fraction of the open-circuit voltage."""
    entry = standard if "open_circuit_voltage_v" in standard else validate_standard(standard)
    return shunt_voltage_v(entry) / entry["open_circuit_voltage_v"]


def flash_repeatability_percent(readings):
    """Spread of repeated flash readings as a percentage of their mean."""
    if not isinstance(readings, (list, tuple)) or len(readings) < 2:
        raise ValueError("at least two flash readings are needed for a spread")
    values = [_require_positive("flash reading", value) for value in readings]
    mean = sum(values) / len(values)
    return (max(values) - min(values)) / mean * 100.0


def window_defects(standard, pulse, limits=DEFAULT_ACCEPTANCE_LIMITS):
    """Every timing and loading defect in one flash reading."""
    entry = standard if "capacitance_uf" in standard else validate_standard(standard)
    flash = pulse if "window_end_ms" in pulse else validate_pulse(pulse)
    validate_acceptance_limits(limits)
    settle_us = settling_time_us(entry, limits["settling_tolerance"])
    settle_ms = settle_us / 1000.0
    defects = []
    if entry["load_connection"] == "two-wire-shunt":
        defects.append(
            {
                "defect": "two-wire-shunt-load",
                "detail": "lead resistance sits inside the measured short-circuit loop",
            }
        )
    if flash["window_start_ms"] < flash["plateau_start_ms"] and not math.isclose(
        flash["window_start_ms"], flash["plateau_start_ms"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        defects.append(
            {
                "defect": "window-opens-before-plateau",
                "detail": "the window opens %.6f ms before the plateau"
                % (flash["plateau_start_ms"] - flash["window_start_ms"]),
            }
        )
    if not _at_most(flash["window_end_ms"], flash["plateau_end_ms"]):
        defects.append(
            {
                "defect": "window-closes-after-plateau",
                "detail": "the window runs %.6f ms past the plateau"
                % (flash["window_end_ms"] - flash["plateau_end_ms"]),
            }
        )
    available_ms = flash["window_start_ms"] - flash["plateau_start_ms"]
    if not _at_least(available_ms, settle_ms):
        defects.append(
            {
                "defect": "settling-not-complete",
                "detail": "the window opens %.6f ms into a %.6f ms settling"
                % (max(available_ms, 0.0), settle_ms),
            }
        )
    if not _at_least(flash["plateau_length_ms"], settle_ms + flash["window_length_ms"]):
        defects.append(
            {
                "defect": "plateau-too-short-to-settle",
                "detail": "a %.6f ms plateau cannot hold %.6f ms of settling plus window"
                % (flash["plateau_length_ms"], settle_ms + flash["window_length_ms"]),
            }
        )
    fraction = shunt_voltage_fraction(entry)
    if not _at_most(fraction, limits["shunt_voltage_fraction"]):
        defects.append(
            {
                "defect": "shunt-voltage-off-short-circuit",
                "detail": "the shunt holds %.6f of the open-circuit voltage" % fraction,
            }
        )
    if not _at_most(flash["plateau_ripple_percent"], limits["plateau_ripple_percent"]):
        defects.append(
            {
                "defect": "plateau-ripple-out-of-band",
                "detail": "the plateau ripples %.6f %%" % flash["plateau_ripple_percent"],
            }
        )
    return defects


def assess_pulsed_response(case, limits=DEFAULT_ACCEPTANCE_LIMITS):
    """Full clause 10.2.2.3.4 check of one working standard on a flash."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    standard = validate_standard(case.get("standard"))
    pulse = validate_pulse(case.get("pulse"))
    validate_acceptance_limits(limits)
    defects = window_defects(standard, pulse, limits)
    tau_us = response_time_constant_us(standard)
    settle_us = settling_time_us(standard, limits["settling_tolerance"])
    delay_us = (pulse["window_start_ms"] - pulse["plateau_start_ms"]) * 1000.0
    residual = residual_response_error(standard, max(delay_us, 0.0))
    readings = case.get("flash_readings")
    spread = None
    if readings is not None:
        spread = flash_repeatability_percent(readings)
        if not _at_most(spread, limits["repeatability_percent"]):
            defects.append(
                {
                    "defect": "flash-repeatability-out-of-band",
                    "detail": "repeated flashes spread %.6f %%" % spread,
                }
            )
    findings = ["%s: %s" % (d["defect"], d["detail"]) for d in defects]
    adequate = not defects
    return {
        "standard": standard["id"],
        "grade": standard["grade"],
        "time_constant_us": tau_us,
        "settling_time_us": settle_us,
        "available_settling_us": delay_us,
        "residual_response_error": residual,
        "shunt_voltage_v": shunt_voltage_v(standard),
        "shunt_voltage_fraction": shunt_voltage_fraction(standard),
        "plateau_length_ms": pulse["plateau_length_ms"],
        "window_end_ms": pulse["window_end_ms"],
        "flash_repeatability_percent": spread,
        "defects": defects,
        "findings": findings,
        "verdict": ADEQUATE_VERDICT if adequate else INADEQUATE_VERDICT,
        "adequate": adequate,
    }
