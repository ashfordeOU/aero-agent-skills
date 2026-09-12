#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.5 converter and regulator control-loop
stability margins (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard asks every closed control loop of a
power converter or regulator to hold a stated phase margin and gain
margin, and asks the demonstration to be made at the worst case of the
operating envelope rather than at the nominal point alone. This module
implements the checkable part of that clause: categorization of the
loop kind, the default margin targets that follow from the category
and the project override of them, enumeration of the worst-case corner
set from the declared envelope extremes, a frequency-response model of
the open-loop gain built from a direct-current gain, left-half-plane
poles and zeros, an optional right-half-plane zero and a transport
delay, the gain- and phase-crossover frequencies found by bisection,
the phase and gain margins read at those crossings, and the per-corner
comparison against the targets. It does not synthesise a compensator,
does not fit a model to measured data, and does not cover large-signal
start-up or fault transients.
"""

import math

SWITCHING_CONVERTER_KINDS = frozenset(
    {
        "buck_converter",
        "boost_converter",
        "buck_boost_converter",
        "flyback_converter",
        "point_of_load_converter",
        "battery_charge_regulator",
        "shunt_switching_regulator",
    }
)
LINEAR_REGULATOR_KINDS = frozenset(
    {
        "linear_series_regulator",
        "linear_shunt_regulator",
        "low_dropout_regulator",
    }
)
BUS_CONTROL_LOOP_KINDS = frozenset(
    {
        "main_bus_voltage_control_loop",
        "maximum_power_point_control_loop",
    }
)

DEFAULT_MARGIN_TARGETS = {
    "switching_converter": {"phase_margin_deg": 45.0, "gain_margin_db": 6.0},
    "linear_regulator": {"phase_margin_deg": 60.0, "gain_margin_db": 10.0},
    "bus_control_loop": {"phase_margin_deg": 50.0, "gain_margin_db": 8.0},
}

REQUIRED_CORNER_AXES = ("temperature", "input_voltage", "load")
DEFAULT_SEARCH_BAND_HZ = (1.0, 1.0e6)

# Margins are engineering limits and are never widened. These absorb the
# representation error of a corner that sits exactly on its target.
MARGIN_TOLERANCE_DEG = 1.0e-9
MARGIN_TOLERANCE_DB = 1.0e-9
_BISECTION_STEPS = 80


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value, label):
    if not _is_number(value) or not math.isfinite(float(value)):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _positive(value, label):
    number = _finite(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def categorize_loop_kind(loop_kind):
    """Category of a closed control loop: "switching_converter",
    "linear_regulator" or "bus_control_loop". Raises ValueError for a
    kind that is not a clause 5.7.5 converter or regulator loop."""
    if loop_kind in SWITCHING_CONVERTER_KINDS:
        return "switching_converter"
    if loop_kind in LINEAR_REGULATOR_KINDS:
        return "linear_regulator"
    if loop_kind in BUS_CONTROL_LOOP_KINDS:
        return "bus_control_loop"
    raise ValueError(
        "unrecognized control loop kind %r under E-ST-20C clause 5.7.5"
        % (loop_kind,)
    )


def required_margin_targets(category, requirement=None):
    """Phase- and gain-margin targets for a loop category, with the
    project requirement applied field by field over the default pair.
    Raises ValueError for an unknown category, a requirement that is
    not a mapping, an unknown target name or a negative target."""
    if category not in DEFAULT_MARGIN_TARGETS:
        raise ValueError("unknown loop category %r" % (category,))
    targets = dict(DEFAULT_MARGIN_TARGETS[category])
    if requirement is None:
        return targets
    if not isinstance(requirement, dict):
        raise ValueError(
            "requirement must be a mapping of target name to value, got %r"
            % (type(requirement).__name__,)
        )
    for key, value in requirement.items():
        if key not in targets:
            raise ValueError(
                "unknown stability target %r; expected one of %s"
                % (key, ", ".join(sorted(targets)))
            )
        number = _finite(value, "requirement[%r]" % (key,))
        if number < 0.0:
            raise ValueError(
                "stability target %r must not be negative, got %r" % (key, value)
            )
        targets[key] = number
    return targets


def corner_label(corner):
    """Deterministic label for one worst-case corner mapping, in the
    declared axis order. Raises ValueError if an axis is missing."""
    if not isinstance(corner, dict):
        raise ValueError("corner must be a mapping of axis to extreme")
    parts = []
    for axis in REQUIRED_CORNER_AXES:
        if axis not in corner:
            raise ValueError("corner is missing required axis %r" % (axis,))
        parts.append("%s=%s" % (axis, corner[axis]))
    return ",".join(parts)


def enumerate_worst_case_corners(corner_axes):
    """Full combination of the declared envelope extremes, as a list of
    corner mappings in deterministic order. Raises ValueError if the
    axis mapping is absent, misses a required axis, carries an
    unrecognized axis, or offers fewer than two extremes on an axis."""
    if not isinstance(corner_axes, dict) or not corner_axes:
        raise ValueError(
            "corner_axes must be a non-empty mapping of axis to its extremes"
        )
    for axis in corner_axes:
        if axis not in REQUIRED_CORNER_AXES:
            raise ValueError(
                "unrecognized worst-case corner axis %r; expected %s"
                % (axis, ", ".join(REQUIRED_CORNER_AXES))
            )
    corners = [{}]
    for axis in REQUIRED_CORNER_AXES:
        values = corner_axes.get(axis)
        if not isinstance(values, (list, tuple)):
            raise ValueError(
                "corner axis %r must list its extremes, got %r" % (axis, values)
            )
        if len(values) < 2:
            raise ValueError(
                "corner axis %r carries %d value(s); a worst-case sweep needs "
                "both extremes" % (axis, len(values))
            )
        if len(set(values)) != len(values):
            raise ValueError("corner axis %r repeats an extreme" % (axis,))
        grown = []
        for partial in corners:
            for value in values:
                extended = dict(partial)
                extended[axis] = value
                grown.append(extended)
        corners = grown
    return corners


def _validate_model(model):
    """Normalised open-loop model. Raises ValueError for a malformed
    frequency response description."""
    if not isinstance(model, dict):
        raise ValueError("loop model must be a mapping, got %r" % (type(model).__name__,))
    dc_gain_db = _finite(model.get("dc_gain_db"), "dc_gain_db")
    poles = model.get("pole_hz")
    if not isinstance(poles, (list, tuple)) or not poles:
        raise ValueError("loop model needs a non-empty pole_hz list")
    poles = [_positive(p, "pole_hz entry") for p in poles]
    zeros = model.get("zero_hz", [])
    if not isinstance(zeros, (list, tuple)):
        raise ValueError("zero_hz must be a list of frequencies")
    zeros = [_positive(z, "zero_hz entry") for z in zeros]
    rhp = model.get("rhp_zero_hz")
    if rhp is not None:
        rhp = _positive(rhp, "rhp_zero_hz")
    delay = model.get("delay_s", 0.0)
    delay = _finite(delay, "delay_s")
    if delay < 0.0:
        raise ValueError("delay_s must not be negative, got %r" % (model.get("delay_s"),))
    return {
        "dc_gain_db": dc_gain_db,
        "pole_hz": poles,
        "zero_hz": zeros,
        "rhp_zero_hz": rhp,
        "delay_s": delay,
    }


def loop_gain_db(model, frequency_hz):
    """Open-loop magnitude in decibels at one frequency. Poles
    attenuate, zeros and a right-half-plane zero both lift, and the
    transport delay is all-pass."""
    normalised = _validate_model(model)
    frequency = _positive(frequency_hz, "frequency_hz")
    gain = normalised["dc_gain_db"]
    for zero in normalised["zero_hz"]:
        gain += 20.0 * math.log10(math.hypot(1.0, frequency / zero))
    if normalised["rhp_zero_hz"] is not None:
        gain += 20.0 * math.log10(math.hypot(1.0, frequency / normalised["rhp_zero_hz"]))
    for pole in normalised["pole_hz"]:
        gain -= 20.0 * math.log10(math.hypot(1.0, frequency / pole))
    return gain


def loop_phase_deg(model, frequency_hz):
    """Open-loop phase in degrees at one frequency. A left-half-plane
    zero leads, a pole lags, and both the right-half-plane zero and the
    transport delay lag without touching the magnitude."""
    normalised = _validate_model(model)
    frequency = _positive(frequency_hz, "frequency_hz")
    phase = 0.0
    for zero in normalised["zero_hz"]:
        phase += math.degrees(math.atan(frequency / zero))
    if normalised["rhp_zero_hz"] is not None:
        phase -= math.degrees(math.atan(frequency / normalised["rhp_zero_hz"]))
    for pole in normalised["pole_hz"]:
        phase -= math.degrees(math.atan(frequency / pole))
    phase -= 360.0 * frequency * normalised["delay_s"]
    return phase


def _validate_band(search_band_hz):
    if not isinstance(search_band_hz, (list, tuple)) or len(search_band_hz) != 2:
        raise ValueError(
            "search_band_hz must be a (low, high) frequency pair, got %r"
            % (search_band_hz,)
        )
    low = _positive(search_band_hz[0], "search band lower edge")
    high = _positive(search_band_hz[1], "search band upper edge")
    if high <= low:
        raise ValueError(
            "search band upper edge %g Hz must exceed the lower edge %g Hz"
            % (high, low)
        )
    return (low, high)


def _bisect_log(function, low, high):
    """Frequency in [low, high] where function changes sign from
    positive to negative, found on a logarithmic axis."""
    log_low = math.log10(low)
    log_high = math.log10(high)
    for _ in range(_BISECTION_STEPS):
        log_mid = 0.5 * (log_low + log_high)
        if function(10.0 ** log_mid) > 0.0:
            log_low = log_mid
        else:
            log_high = log_mid
    return 10.0 ** (0.5 * (log_low + log_high))


def gain_crossover_hz(model, search_band_hz=DEFAULT_SEARCH_BAND_HZ):
    """Frequency where the open-loop magnitude passes unity. Raises
    ValueError when the band does not bracket the crossing."""
    low, high = _validate_band(search_band_hz)
    if loop_gain_db(model, low) <= 0.0:
        raise ValueError(
            "open-loop gain is already at or below unity at the band lower edge "
            "%g Hz; extend the search band downward" % low
        )
    if loop_gain_db(model, high) >= 0.0:
        raise ValueError(
            "open-loop gain is still at or above unity at the band upper edge "
            "%g Hz; extend the search band upward" % high
        )
    return _bisect_log(lambda f: loop_gain_db(model, f), low, high)


def phase_crossover_hz(model, search_band_hz=DEFAULT_SEARCH_BAND_HZ):
    """Frequency where the open-loop phase passes minus one hundred and
    eighty degrees, or None when the phase stays above it across the
    whole band. Raises ValueError when the band starts below it."""
    low, high = _validate_band(search_band_hz)
    if loop_phase_deg(model, low) <= -180.0:
        raise ValueError(
            "open-loop phase is already at or below -180 deg at the band lower "
            "edge %g Hz; extend the search band downward" % low
        )
    if loop_phase_deg(model, high) > -180.0:
        return None
    return _bisect_log(lambda f: loop_phase_deg(model, f) + 180.0, low, high)


def phase_margin_deg(model, search_band_hz=DEFAULT_SEARCH_BAND_HZ):
    """Phase margin: one hundred and eighty degrees plus the open-loop
    phase at the gain-crossover frequency."""
    crossover = gain_crossover_hz(model, search_band_hz)
    return 180.0 + loop_phase_deg(model, crossover)


def gain_margin_db(model, search_band_hz=DEFAULT_SEARCH_BAND_HZ):
    """Gain margin: the attenuation below unity at the phase-crossover
    frequency, or positive infinity when there is no phase crossover in
    the analysis band."""
    crossover = phase_crossover_hz(model, search_band_hz)
    if crossover is None:
        return math.inf
    return -loop_gain_db(model, crossover)


def _meets(value, target, tolerance):
    """True when a margin reaches its target, absorbing the few bits a
    crossover search costs at an exactly-on-target corner."""
    if value >= target:
        return True
    return math.isclose(value, target, rel_tol=1.0e-12, abs_tol=tolerance)


def evaluate_corner_margins(label, model, targets, search_band_hz=DEFAULT_SEARCH_BAND_HZ):
    """Margins of one corner against the targets, with a finding per
    target the corner does not reach."""
    if not isinstance(targets, dict):
        raise ValueError("targets must be a mapping of target name to value")
    for key in ("phase_margin_deg", "gain_margin_db"):
        if key not in targets:
            raise ValueError("targets is missing %r" % (key,))
    crossover = gain_crossover_hz(model, search_band_hz)
    phase_cross = phase_crossover_hz(model, search_band_hz)
    phase_margin = 180.0 + loop_phase_deg(model, crossover)
    if phase_cross is None:
        gain_margin = math.inf
    else:
        gain_margin = -loop_gain_db(model, phase_cross)
    findings = []
    if not _meets(phase_margin, targets["phase_margin_deg"], MARGIN_TOLERANCE_DEG):
        findings.append(
            "corner %s: phase margin %.3f deg is below the %.3f deg target"
            % (label, phase_margin, targets["phase_margin_deg"])
        )
    if not _meets(gain_margin, targets["gain_margin_db"], MARGIN_TOLERANCE_DB):
        findings.append(
            "corner %s: gain margin %.3f dB is below the %.3f dB target"
            % (label, gain_margin, targets["gain_margin_db"])
        )
    return {
        "corner": label,
        "gain_crossover_hz": crossover,
        "phase_crossover_hz": phase_cross,
        "phase_margin_deg": phase_margin,
        "gain_margin_db": gain_margin,
        "findings": findings,
    }


def assess_control_loop_stability(case):
    """Clause 5.7.5 stability review of one control loop across its
    worst-case corner set. Raises ValueError for a malformed case."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    loop_id = case.get("loop_id")
    if not isinstance(loop_id, str) or not loop_id.strip():
        raise ValueError("case needs a non-empty loop_id")
    category = categorize_loop_kind(case.get("loop_kind"))
    targets = required_margin_targets(category, case.get("requirement"))
    band = _validate_band(case.get("search_band_hz", DEFAULT_SEARCH_BAND_HZ))
    corners = enumerate_worst_case_corners(case.get("corner_axes"))
    models = case.get("corner_models")
    if not isinstance(models, dict) or not models:
        raise ValueError(
            "corner_models must be a non-empty mapping of corner label to model"
        )
    expected = [corner_label(corner) for corner in corners]
    coverage_findings = []
    for label in expected:
        if label not in models:
            coverage_findings.append(
                "corner %s has no loop model on record" % label
            )
    for label in sorted(models):
        if label not in expected:
            coverage_findings.append(
                "loop model %r matches no enumerated worst-case corner" % label
            )
    results = []
    margin_findings = []
    for label in expected:
        if label not in models:
            continue
        result = evaluate_corner_margins(label, models[label], targets, band)
        results.append(result)
        margin_findings.extend(result["findings"])
    return {
        "loop_id": loop_id,
        "category": category,
        "targets": targets,
        "corner_count": len(expected),
        "corner_results": results,
        "coverage_findings": coverage_findings,
        "margin_findings": margin_findings,
        "compliant": not coverage_findings and not margin_findings,
    }
