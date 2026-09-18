#!/usr/bin/env python3
"""Inrush-current test procedure, ECSS-E-ST-20-07C clause 5.4.4.4.

Paraphrased procedure, no verbatim standard text. The clause runs a
switch-on surge measurement in a fixed order: let the unit settle, check
the measurement chain if that check is being used, then arm, switch and
capture -- repeatedly, with enough time between repeats for the input
filter to discharge. This module turns that into a deterministic plan
and assessment:

  dwell vs required dwell    -> is the unit steady before the first surge
  chain check + tolerance    -> passed, out of tolerance, or omitted
  filter time constant       -> the off-time each repeat needs
  trigger, pre-trigger, record -> is the surge actually caught

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Dwells, off-times and record windows are floats,
# so a requirement that is exactly met can land a few units in the last
# place short of its bound. The tolerances absorb that representation
# error only; they never relax a requirement.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Time constants of the input filter that must elapse with the unit off
# before a repeat starts from the same discharged state.
DEFAULT_DISCHARGE_CONSTANTS = 5.0

# Repeats needed before a surge peak counts as reproducible.
MIN_SWITCH_ON_EVENTS = 3

# The trigger has to stand this far above the noise floor, and stay at or
# under this fraction of the expected peak, to arm on the surge itself.
DEFAULT_NOISE_MARGIN = 3.0
DEFAULT_TRIGGER_PEAK_FRACTION = 0.5

# Pre-trigger, as a fraction of the transient, that shows the quiescent
# draw the surge started from.
DEFAULT_PRE_TRIGGER_FRACTION = 0.1

CHECK_PASSED = "chain-check-passed"
CHECK_OUT_OF_TOLERANCE = "chain-check-out-of-tolerance"
CHECK_OMITTED = "chain-check-omitted"

VERDICT_COMPLIANT = "procedure-compliant"
VERDICT_DEFICIENT = "procedure-deficient"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def _count(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            "%s: field %r must be a whole number of events, got %r"
            % (where, key, value)
        )
    if value < 1:
        raise ValueError("%s: field %r must be >= 1, got %d" % (where, key, value))
    return value


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_procedure(config):
    """Validate a switch-on surge procedure and return it normalized."""
    where = "procedure"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    out = {}
    out["capture_armed_before_switching"] = _flag(
        config, "capture_armed_before_switching", where
    )
    out["chain_check_performed"] = _flag(config, "chain_check_performed", where)
    out["switch_on_events"] = _count(config, "switch_on_events", where)

    strictly_positive = (
        "required_dwell_s",
        "filter_time_constant_s",
        "off_time_s",
        "trigger_level_a",
        "noise_floor_a",
        "expected_peak_a",
        "record_length_s",
        "transient_duration_s",
        "chain_check_tolerance_pct",
    )
    for key in strictly_positive:
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        out[key] = value

    for key in ("stabilisation_dwell_s", "pre_trigger_s", "chain_check_error_pct"):
        value = _number(config, key, where)
        if value < 0.0:
            raise ValueError("%s: %s must be >= 0, got %g" % (where, key, value))
        out[key] = value

    if out["noise_floor_a"] >= out["expected_peak_a"]:
        raise ValueError(
            "%s: noise_floor_a (%g) must sit below expected_peak_a (%g)"
            % (where, out["noise_floor_a"], out["expected_peak_a"])
        )
    return out


def stabilisation_is_complete(stabilisation_dwell_s, required_dwell_s):
    """True when the unit has been left long enough to reach a steady draw."""
    dwell = _scalar(stabilisation_dwell_s, "stabilisation_dwell_s")
    required = _scalar(required_dwell_s, "required_dwell_s")
    if dwell < 0.0:
        raise ValueError("stabilisation_dwell_s must be >= 0, got %g" % dwell)
    if required <= 0.0:
        raise ValueError("required_dwell_s must be > 0, got %g" % required)
    return at_least(dwell, required)


def min_recovery_time_s(
    filter_time_constant_s, discharge_constants=DEFAULT_DISCHARGE_CONSTANTS
):
    """Off-time a repeat needs for the input filter to discharge."""
    tau = _scalar(filter_time_constant_s, "filter_time_constant_s")
    count = _scalar(discharge_constants, "discharge_constants")
    if tau <= 0.0:
        raise ValueError("filter_time_constant_s must be > 0, got %g" % tau)
    if count < 1.0:
        raise ValueError("discharge_constants must be >= 1, got %g" % count)
    return count * tau


def recovery_is_sufficient(
    off_time_s,
    filter_time_constant_s,
    discharge_constants=DEFAULT_DISCHARGE_CONSTANTS,
):
    """True when the off-time leaves the filter discharged for the next surge."""
    off_time = _scalar(off_time_s, "off_time_s")
    if off_time <= 0.0:
        raise ValueError("off_time_s must be > 0, got %g" % off_time)
    return at_least(
        off_time, min_recovery_time_s(filter_time_constant_s, discharge_constants)
    )


def residual_charge_fraction(off_time_s, filter_time_constant_s):
    """Charge still left on the input filter when the next surge starts."""
    off_time = _scalar(off_time_s, "off_time_s")
    tau = _scalar(filter_time_constant_s, "filter_time_constant_s")
    if off_time < 0.0:
        raise ValueError("off_time_s must be >= 0, got %g" % off_time)
    if tau <= 0.0:
        raise ValueError("filter_time_constant_s must be > 0, got %g" % tau)
    return math.exp(-off_time / tau)


def chain_check_status(performed, error_pct, tolerance_pct):
    """Group the optional measurement-chain check by what it returned."""
    if not isinstance(performed, bool):
        raise ValueError("performed must be a boolean, got %r" % (performed,))
    error = _scalar(error_pct, "error_pct")
    tolerance = _scalar(tolerance_pct, "tolerance_pct")
    if error < 0.0:
        raise ValueError("error_pct must be >= 0, got %g" % error)
    if tolerance <= 0.0:
        raise ValueError("tolerance_pct must be > 0, got %g" % tolerance)
    if not performed:
        return CHECK_OMITTED
    return CHECK_PASSED if at_most(error, tolerance) else CHECK_OUT_OF_TOLERANCE


def trigger_findings(
    trigger_level_a,
    noise_floor_a,
    expected_peak_a,
    noise_margin=DEFAULT_NOISE_MARGIN,
    peak_fraction=DEFAULT_TRIGGER_PEAK_FRACTION,
):
    """Report a trigger that arms on noise or misses the leading edge."""
    trigger = _scalar(trigger_level_a, "trigger_level_a")
    noise = _scalar(noise_floor_a, "noise_floor_a")
    peak = _scalar(expected_peak_a, "expected_peak_a")
    margin = _scalar(noise_margin, "noise_margin")
    fraction = _scalar(peak_fraction, "peak_fraction")
    if trigger <= 0.0:
        raise ValueError("trigger_level_a must be > 0, got %g" % trigger)
    if noise <= 0.0:
        raise ValueError("noise_floor_a must be > 0, got %g" % noise)
    if peak <= 0.0:
        raise ValueError("expected_peak_a must be > 0, got %g" % peak)
    if margin < 1.0:
        raise ValueError("noise_margin must be >= 1, got %g" % margin)
    if not 0.0 < fraction <= 1.0:
        raise ValueError("peak_fraction must be within (0, 1], got %g" % fraction)

    out = []
    floor = margin * noise
    ceiling = fraction * peak
    if not at_least(trigger, floor):
        out.append(
            "trigger level %g A sits under the %g A that clears the %g A noise "
            "floor, so the capture can arm on noise before the unit is switched"
            % (trigger, floor, noise)
        )
    if not at_most(trigger, ceiling):
        out.append(
            "trigger level %g A is above the %g A that still catches the leading "
            "edge of a %g A peak, so the start of the surge is lost"
            % (trigger, ceiling, peak)
        )
    return out


def capture_window_findings(
    pre_trigger_s,
    record_length_s,
    transient_duration_s,
    pre_trigger_fraction=DEFAULT_PRE_TRIGGER_FRACTION,
):
    """Report a capture window that cannot hold the whole transient."""
    pre = _scalar(pre_trigger_s, "pre_trigger_s")
    record = _scalar(record_length_s, "record_length_s")
    transient = _scalar(transient_duration_s, "transient_duration_s")
    fraction = _scalar(pre_trigger_fraction, "pre_trigger_fraction")
    if pre < 0.0:
        raise ValueError("pre_trigger_s must be >= 0, got %g" % pre)
    if record <= 0.0:
        raise ValueError("record_length_s must be > 0, got %g" % record)
    if transient <= 0.0:
        raise ValueError("transient_duration_s must be > 0, got %g" % transient)
    if fraction < 0.0:
        raise ValueError("pre_trigger_fraction must be >= 0, got %g" % fraction)

    out = []
    needed = pre + transient
    if not at_least(record, needed):
        out.append(
            "record length %g s cannot hold %g s of pre-trigger plus a %g s "
            "transient; %g s is needed"
            % (record, pre, transient, needed)
        )
    wanted_pre = fraction * transient
    if not at_least(pre, wanted_pre):
        out.append(
            "pre-trigger %g s is under the %g s that shows the quiescent draw the "
            "surge started from" % (pre, wanted_pre)
        )
    return out


def build_switching_sequence(
    procedure, discharge_constants=DEFAULT_DISCHARGE_CONSTANTS
):
    """Order the stabilise, check, arm, switch and recover steps of the run."""
    config = validate_procedure(procedure)
    off_time = max(
        config["off_time_s"],
        min_recovery_time_s(config["filter_time_constant_s"], discharge_constants),
    )

    steps = []
    elapsed = 0.0

    def add(step, duration, event=None):
        nonlocal elapsed
        entry = {
            "order": len(steps) + 1,
            "step": step,
            "duration_s": duration,
            "starts_at_s": elapsed,
        }
        if event is not None:
            entry["event"] = event
        steps.append(entry)
        elapsed += duration

    add("stabilise-unit", config["stabilisation_dwell_s"])
    if config["chain_check_performed"]:
        add("measurement-chain-check", 0.0)
    for event in range(1, config["switch_on_events"] + 1):
        add("arm-capture", 0.0, event)
        add("switch-on", 0.0, event)
        add("record-transient", config["record_length_s"], event)
        add("switch-off", 0.0, event)
        if event < config["switch_on_events"]:
            add("recover-input-filter", off_time, event)
    return steps


def sequence_duration_s(steps):
    """Total elapsed time of an ordered step plan."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps: must be a non-empty sequence")
    total = 0.0
    for index, entry in enumerate(steps):
        if not isinstance(entry, dict) or "duration_s" not in entry:
            raise ValueError("steps[%d]: missing duration_s" % index)
        total += _number(entry, "duration_s", "steps[%d]" % index)
    return total


def assess_inrush_procedure(
    config,
    discharge_constants=DEFAULT_DISCHARGE_CONSTANTS,
    min_events=MIN_SWITCH_ON_EVENTS,
):
    """Full clause 5.4.4.4 assessment of a switch-on surge procedure."""
    procedure = validate_procedure(config)
    events = int(min_events)
    if events < 1:
        raise ValueError("min_events must be >= 1, got %d" % events)

    steady = stabilisation_is_complete(
        procedure["stabilisation_dwell_s"], procedure["required_dwell_s"]
    )
    needed_off = min_recovery_time_s(
        procedure["filter_time_constant_s"], discharge_constants
    )
    recovered = recovery_is_sufficient(
        procedure["off_time_s"], procedure["filter_time_constant_s"],
        discharge_constants,
    )
    check = chain_check_status(
        procedure["chain_check_performed"],
        procedure["chain_check_error_pct"],
        procedure["chain_check_tolerance_pct"],
    )
    trigger = trigger_findings(
        procedure["trigger_level_a"],
        procedure["noise_floor_a"],
        procedure["expected_peak_a"],
    )
    window = capture_window_findings(
        procedure["pre_trigger_s"],
        procedure["record_length_s"],
        procedure["transient_duration_s"],
    )

    findings = []
    if not steady:
        findings.append(
            "the unit dwelled %g s before the first switch-on, under the %g s it "
            "needs to reach a steady draw"
            % (procedure["stabilisation_dwell_s"], procedure["required_dwell_s"])
        )
    if not procedure["capture_armed_before_switching"]:
        findings.append(
            "the capture is armed after the switching command, so the leading edge "
            "of the surge is outside the record"
        )
    if not recovered:
        findings.append(
            "off-time %g s between repeats leaves the input filter charged; %g s "
            "is needed before the next surge starts from the same state"
            % (procedure["off_time_s"], needed_off)
        )
    if procedure["switch_on_events"] < events:
        findings.append(
            "%d switch-on event(s) recorded, under the %d that make a surge peak "
            "reproducible" % (procedure["switch_on_events"], events)
        )
    if check == CHECK_OUT_OF_TOLERANCE:
        findings.append(
            "the measurement-chain check returned %g%% against a %g%% tolerance, so "
            "the captured amplitudes are not traceable"
            % (
                procedure["chain_check_error_pct"],
                procedure["chain_check_tolerance_pct"],
            )
        )
    findings.extend(trigger)
    findings.extend(window)

    limitations = []
    if check == CHECK_OMITTED:
        limitations.append(
            "the optional measurement-chain check was not run, so the captured "
            "amplitudes rest on the calibration record alone"
        )
    residual = residual_charge_fraction(
        procedure["off_time_s"], procedure["filter_time_constant_s"]
    )
    if recovered and not at_most(residual, 0.01):
        limitations.append(
            "%.3g of the filter charge is still present at the next switch-on, so "
            "later repeats draw a slightly smaller surge than the first" % residual
        )

    return {
        "procedure": procedure,
        "steps": build_switching_sequence(config, discharge_constants),
        "stabilisation_is_complete": steady,
        "min_recovery_time_s": needed_off,
        "recovery_is_sufficient": recovered,
        "residual_charge_fraction": residual,
        "chain_check_status": check,
        "trigger_findings": trigger,
        "capture_window_findings": window,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_COMPLIANT if not findings else VERDICT_DEFICIENT,
    }
