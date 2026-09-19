#!/usr/bin/env python3
"""Design of the test process, ECSS-Q-ST-20-07C clause 5.7.3.

Paraphrased clause intent, no verbatim standard text. An accepted
request becomes a runnable process only once someone has fixed what is
controlled, how tightly, with what instrument, and in what order the
loads are applied. This module turns that into deterministic
specification content:

  nominal + tolerance band -> what still counts as the test performed
  band / uncertainty       -> can the instrument decide conformance
  guard band               -> the limits the operator actually accepts
  instrument range         -> does the channel cover the whole band
  load steps + ramps       -> a sequence the facility can hold

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Bands, ratios and ramp rates are floats, so a
# design that exactly meets a bound can land a few units in the last
# place the wrong side of it. The tolerance absorbs that representation
# error only; it never relaxes a design rule.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# The band half-width has to be at least this many times the measurement
# uncertainty before a reading can decide conformance.
DEFAULT_MIN_ACCURACY_RATIO = 4.0

# A process that applies fewer steps than this is a single-point check,
# not a load sequence.
MIN_LOAD_STEPS = 2

VERDICT_APPROVED = "process-design-approved"
VERDICT_REWORK = "process-design-rework"


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


def validate_parameter(param, where="parameter"):
    """Validate one controlled parameter of the test process."""
    if not isinstance(param, dict):
        raise ValueError("%s: record must be a mapping" % where)
    name = param.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("%s: name must be a non-empty string" % where)

    out = {"name": name.strip()}
    out["nominal"] = _number(param, "nominal", where)

    tolerance = _number(param, "tolerance", where)
    if tolerance <= 0.0:
        raise ValueError("%s: tolerance must be > 0, got %g" % (where, tolerance))
    out["tolerance"] = tolerance

    uncertainty = _number(param, "uncertainty", where)
    if uncertainty < 0.0:
        raise ValueError("%s: uncertainty must be >= 0, got %g" % (where, uncertainty))
    out["uncertainty"] = uncertainty

    span = param.get("instrument_range")
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise ValueError("%s: instrument_range must be a (lower, upper) pair" % where)
    lower = _scalar(span[0], "%s.instrument_range.lower" % where)
    upper = _scalar(span[1], "%s.instrument_range.upper" % where)
    if not upper > lower:
        raise ValueError(
            "%s: instrument_range upper (%g) must exceed lower (%g)"
            % (where, upper, lower)
        )
    out["instrument_range"] = (lower, upper)
    return out


def test_accuracy_ratio(tolerance, uncertainty):
    """Band half-width divided by the measurement uncertainty."""
    band = _scalar(tolerance, "tolerance")
    unc = _scalar(uncertainty, "uncertainty")
    if band <= 0.0:
        raise ValueError("tolerance must be > 0, got %g" % band)
    if unc <= 0.0:
        raise ValueError(
            "uncertainty must be > 0 to form an accuracy ratio, got %g" % unc
        )
    return band / unc


def guard_banded_limits(nominal, tolerance, uncertainty):
    """Acceptance limits pulled inward by the measurement uncertainty."""
    centre = _scalar(nominal, "nominal")
    band = _scalar(tolerance, "tolerance")
    unc = _scalar(uncertainty, "uncertainty")
    if band <= 0.0:
        raise ValueError("tolerance must be > 0, got %g" % band)
    if unc < 0.0:
        raise ValueError("uncertainty must be >= 0, got %g" % unc)
    if at_least(unc, band):
        raise ValueError(
            "uncertainty %g consumes the whole tolerance band %g; no acceptance "
            "limit can be stated from this instrument" % (unc, band)
        )
    usable = band - unc
    return {
        "specified_lower": centre - band,
        "specified_upper": centre + band,
        "accept_lower": centre - usable,
        "accept_upper": centre + usable,
        "guard_band": unc,
    }


def instrument_covers_band(param):
    """True when the instrument range brackets nominal plus and minus the band."""
    normalized = validate_parameter(param)
    lower, upper = normalized["instrument_range"]
    band_lower = normalized["nominal"] - normalized["tolerance"]
    band_upper = normalized["nominal"] + normalized["tolerance"]
    return at_most(lower, band_lower) and at_least(upper, band_upper)


def validate_load_steps(steps, min_steps=MIN_LOAD_STEPS):
    """Validate the load sequence and return it normalized in order."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps: must be a sequence of load steps")
    floor = int(min_steps)
    if floor < 1:
        raise ValueError("min_steps must be >= 1, got %d" % floor)
    if len(steps) < floor:
        raise ValueError(
            "steps: %d step(s) is fewer than the %d that make a load sequence"
            % (len(steps), floor)
        )

    out = []
    previous = None
    for index, step in enumerate(steps):
        where = "steps[%d]" % index
        if not isinstance(step, dict):
            raise ValueError("%s: record must be a mapping" % where)
        level = _number(step, "level", where)
        dwell = _number(step, "dwell_s", where)
        transition = _number(step, "transition_s", where)
        if dwell <= 0.0:
            raise ValueError("%s: dwell_s must be > 0, got %g" % (where, dwell))
        if transition <= 0.0:
            raise ValueError(
                "%s: transition_s must be > 0, got %g" % (where, transition)
            )
        if previous is not None and not level > previous:
            raise ValueError(
                "%s: level %g does not advance on the previous step %g"
                % (where, level, previous)
            )
        previous = level
        out.append(
            {
                "order": index + 1,
                "level": level,
                "dwell_s": dwell,
                "transition_s": transition,
            }
        )
    return out


def ramp_rates(steps, start_level=0.0):
    """Level change per second on the transition into each load step."""
    normalized = validate_load_steps(steps)
    previous = _scalar(start_level, "start_level")
    rates = []
    for step in normalized:
        rates.append((step["level"] - previous) / step["transition_s"])
        previous = step["level"]
    return rates


def ramp_findings(steps, max_ramp_rate, start_level=0.0):
    """Report transitions whose ramp outruns what the facility can hold."""
    limit = _scalar(max_ramp_rate, "max_ramp_rate")
    if limit <= 0.0:
        raise ValueError("max_ramp_rate must be > 0, got %g" % limit)
    out = []
    for index, rate in enumerate(ramp_rates(steps, start_level)):
        if not at_most(abs(rate), limit):
            out.append(
                "step %d ramps at %g per second, over the %g per second the "
                "facility holds" % (index + 1, abs(rate), limit)
            )
    return out


def sequence_duration_s(steps):
    """Total dwell plus transition time of the designed load sequence."""
    normalized = validate_load_steps(steps)
    return sum(step["dwell_s"] + step["transition_s"] for step in normalized)


def design_test_process(design, min_accuracy_ratio=DEFAULT_MIN_ACCURACY_RATIO):
    """Full clause 5.7.3 design pass over one test process."""
    if not isinstance(design, dict):
        raise ValueError("design: record must be a mapping")
    floor = _scalar(min_accuracy_ratio, "min_accuracy_ratio")
    if floor <= 0.0:
        raise ValueError("min_accuracy_ratio must be > 0, got %g" % floor)

    params = design.get("parameters")
    if not isinstance(params, (list, tuple)) or not params:
        raise ValueError("design: parameters must be a non-empty sequence")
    max_ramp = _number(design, "max_ramp_rate", "design")
    if max_ramp <= 0.0:
        raise ValueError("design: max_ramp_rate must be > 0, got %g" % max_ramp)
    raw_steps = design.get("load_steps", [])

    table = []
    findings = []
    for index, raw in enumerate(params):
        param = validate_parameter(raw, "parameters[%d]" % index)
        ratio = test_accuracy_ratio(param["tolerance"], param["uncertainty"]) if param[
            "uncertainty"
        ] > 0.0 else None
        limits = guard_banded_limits(
            param["nominal"], param["tolerance"], param["uncertainty"]
        )
        covers = instrument_covers_band(raw)
        entry = dict(param)
        entry["accuracy_ratio"] = ratio
        entry["limits"] = limits
        entry["instrument_covers_band"] = covers
        table.append(entry)

        if ratio is not None and not at_least(ratio, floor):
            findings.append(
                "%s: accuracy ratio %g is under the %g needed to decide conformance "
                "against a tolerance of %g"
                % (param["name"], ratio, floor, param["tolerance"])
            )
        if not covers:
            findings.append(
                "%s: instrument range %g to %g does not bracket the band %g to %g"
                % (
                    param["name"],
                    param["instrument_range"][0],
                    param["instrument_range"][1],
                    limits["specified_lower"],
                    limits["specified_upper"],
                )
            )

    steps = validate_load_steps(raw_steps)
    findings.extend(ramp_findings(raw_steps, max_ramp))

    return {
        "parameters": table,
        "load_steps": steps,
        "max_ramp_rate": max_ramp,
        "ramp_rates": ramp_rates(raw_steps),
        "sequence_duration_s": sequence_duration_s(raw_steps),
        "findings": findings,
        "verdict": VERDICT_APPROVED if not findings else VERDICT_REWORK,
    }
