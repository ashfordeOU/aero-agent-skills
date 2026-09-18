"""Noise immunity test for an undervoltage trip, driven by a defined voltage step.

Anchor: ECSS-E-ST-20-20C clause 5.4.3.4.1 (a voltage step of defined size is
applied to show the undervoltage protection does not react to noise).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
The stimulus is a single downward step on the bus, held for a dwell and then
released. Four things have to be true at once before a no-trip result means
anything:

1. the step has to be big enough. It stands in for the disturbance envelope
   the bus really carries -- broadband noise plus ripple -- so a step smaller
   than that envelope demonstrates immunity to something gentler than reality.
2. both levels have to stay clear of the trip point, sensing uncertainty
   included. A step that reaches the trip band is not a noise stimulus; it is
   a genuine undervoltage, and the protection is then correct to react.
3. the dwell at the lower level has to outlast the detection chain's own
   response. A step released before the sensing filter has settled produces a
   no-trip result that says the chain was still looking, not that it was
   immune.
4. the edge has to be at least as fast as the disturbance it represents. A
   slow ramp is filtered by exactly the chain the test is meant to stress.

Requirements 1 and 2 pull against each other, and that tension is the useful
output. The largest step that still clears the trip band is fixed by where the
threshold sits under the operating point; when the envelope demands more than
that headroom, the finding belongs to the threshold placement, not to the test
specification, because no step can satisfy both at once.

Observed runs are then graded. Immunity is a repeated result, so a single
application is not a demonstration, and one trip across the set is enough to
fail it.
"""

import math

__all__ = [
    "VOLT_TOLERANCE_V",
    "TIME_TOLERANCE_S",
    "DEFAULT_AMPLITUDE_FACTOR",
    "DEFAULT_DWELL_FACTOR",
    "MIN_REPETITIONS",
    "validate_threshold",
    "validate_noise",
    "validate_stimulus",
    "required_step_amplitude_v",
    "step_levels",
    "amplitude_headroom_v",
    "slew_rate_v_per_s",
    "required_dwell_s",
    "grade_runs",
    "assess_noise_immunity_test",
]

# Two voltages, or two durations, a design can place exactly on top of each
# other; absorb the representation error here rather than relaxing the limit.
VOLT_TOLERANCE_V = 1e-9
TIME_TOLERANCE_S = 1e-12

# Coverage factor applied to the disturbance envelope when sizing the step, so
# the stimulus bounds the noise rather than matching its typical amplitude.
DEFAULT_AMPLITUDE_FACTOR = 2.0

# The dwell has to outlast the detection chain by this factor before a no-trip
# result can be read as immunity rather than as an unfinished measurement.
DEFAULT_DWELL_FACTOR = 1.5

# One application is an anecdote; immunity is a repeated result.
MIN_REPETITIONS = 3


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _count(label, value):
    """Return value as a positive integer count or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %d" % (label, value))
    return value


def validate_threshold(spec):
    """Return (trip_threshold_v, sensing_uncertainty_v), or raise."""
    if not isinstance(spec, dict):
        raise ValueError("threshold spec must be a mapping")
    for key in ("trip_threshold_v", "sensing_uncertainty_v"):
        if key not in spec:
            raise ValueError("threshold spec missing required key '%s'" % key)
    return (
        _positive("trip_threshold_v", spec["trip_threshold_v"]),
        _non_negative("sensing_uncertainty_v", spec["sensing_uncertainty_v"]),
    )


def validate_noise(spec):
    """Return the disturbance description as a mapping of floats, or raise.

    spec keys: noise_envelope_v, ripple_peak_to_peak_v, disturbance_slew_v_per_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("noise spec must be a mapping")
    required = (
        "noise_envelope_v",
        "ripple_peak_to_peak_v",
        "disturbance_slew_v_per_s",
    )
    for key in required:
        if key not in spec:
            raise ValueError("noise spec missing required key '%s'" % key)
    return {
        "noise_envelope_v": _non_negative("noise_envelope_v", spec["noise_envelope_v"]),
        "ripple_peak_to_peak_v": _non_negative(
            "ripple_peak_to_peak_v", spec["ripple_peak_to_peak_v"]
        ),
        "disturbance_slew_v_per_s": _positive(
            "disturbance_slew_v_per_s", spec["disturbance_slew_v_per_s"]
        ),
    }


def validate_stimulus(spec):
    """Return the applied step as a mapping of floats, or raise.

    spec keys: start_voltage_v, step_amplitude_v, edge_time_s, dwell_s,
    repetitions.
    """
    if not isinstance(spec, dict):
        raise ValueError("stimulus spec must be a mapping")
    required = (
        "start_voltage_v",
        "step_amplitude_v",
        "edge_time_s",
        "dwell_s",
        "repetitions",
    )
    for key in required:
        if key not in spec:
            raise ValueError("stimulus spec missing required key '%s'" % key)
    stimulus = {
        "start_voltage_v": _positive("start_voltage_v", spec["start_voltage_v"]),
        "step_amplitude_v": _positive("step_amplitude_v", spec["step_amplitude_v"]),
        "edge_time_s": _positive("edge_time_s", spec["edge_time_s"]),
        "dwell_s": _positive("dwell_s", spec["dwell_s"]),
        "repetitions": _count("repetitions", spec["repetitions"]),
    }
    if stimulus["step_amplitude_v"] >= stimulus["start_voltage_v"]:
        raise ValueError(
            "step_amplitude_v %r would take the bus to or below zero from %r"
            % (stimulus["step_amplitude_v"], stimulus["start_voltage_v"])
        )
    return stimulus


def required_step_amplitude_v(noise, factor=DEFAULT_AMPLITUDE_FACTOR):
    """Return the smallest step that bounds the declared disturbance envelope.

    Ripple is declared peak to peak and the step is a one-sided excursion, so
    only half of it belongs on this side of the operating point.
    """
    factor = _positive("amplitude factor", factor)
    envelope = noise["noise_envelope_v"] + noise["ripple_peak_to_peak_v"] / 2.0
    return factor * envelope


def step_levels(start_voltage_v, step_amplitude_v):
    """Return (upper_level_v, lower_level_v) for the applied step."""
    start = _positive("start_voltage_v", start_voltage_v)
    amplitude = _positive("step_amplitude_v", step_amplitude_v)
    return (start, start - amplitude)


def amplitude_headroom_v(start_voltage_v, trip_threshold_v, sensing_uncertainty_v):
    """Return the largest step that still keeps the lower level out of the trip band."""
    return start_voltage_v - (trip_threshold_v + sensing_uncertainty_v)


def slew_rate_v_per_s(step_amplitude_v, edge_time_s):
    """Return the edge rate the stimulus presents to the sensing chain."""
    return _positive("step_amplitude_v", step_amplitude_v) / _positive(
        "edge_time_s", edge_time_s
    )


def required_dwell_s(detector_response_time_s, factor=DEFAULT_DWELL_FACTOR):
    """Return the shortest dwell that outlasts the detection chain."""
    return _positive(
        "detector_response_time_s", detector_response_time_s
    ) * _positive("dwell factor", factor)


def grade_runs(raw):
    """Return (run_count, tripped_run_names) for the observed applications."""
    if not isinstance(raw, (list, tuple)):
        raise ValueError("runs must be a sequence")
    names = []
    tripped = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("runs[%d] must be a mapping" % i)
        for key in ("run", "tripped"):
            if key not in item:
                raise ValueError("runs[%d] missing required key '%s'" % (i, key))
        name = item["run"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("runs[%d]['run'] must be a non-empty string" % i)
        name = name.strip()
        if name in names:
            raise ValueError("run name %r is used twice" % name)
        names.append(name)
        flag = item["tripped"]
        if not isinstance(flag, bool):
            raise ValueError("run %r 'tripped' must be a boolean" % name)
        if flag:
            tripped.append(name)
    return (len(names), tripped)


def assess_noise_immunity_test(spec):
    """Grade an undervoltage noise immunity test against clause 5.4.3.4.1."""
    if not isinstance(spec, dict):
        raise ValueError("immunity test spec must be a mapping")
    for key in ("threshold", "noise", "stimulus", "detector_response_time_s"):
        if key not in spec:
            raise ValueError("immunity test spec missing required key '%s'" % key)

    threshold_v, uncertainty_v = validate_threshold(spec["threshold"])
    noise = validate_noise(spec["noise"])
    stimulus = validate_stimulus(spec["stimulus"])
    response_s = _positive(
        "detector_response_time_s", spec["detector_response_time_s"]
    )
    amplitude_factor = spec.get("amplitude_factor", DEFAULT_AMPLITUDE_FACTOR)
    dwell_factor = spec.get("dwell_factor", DEFAULT_DWELL_FACTOR)

    upper_v, lower_v = step_levels(
        stimulus["start_voltage_v"], stimulus["step_amplitude_v"]
    )
    trip_band_v = threshold_v + uncertainty_v
    headroom_v = amplitude_headroom_v(
        stimulus["start_voltage_v"], threshold_v, uncertainty_v
    )
    needed_v = required_step_amplitude_v(noise, amplitude_factor)
    needed_dwell_s = required_dwell_s(response_s, dwell_factor)
    slew = slew_rate_v_per_s(stimulus["step_amplitude_v"], stimulus["edge_time_s"])

    findings = []
    clears_band = lower_v >= trip_band_v - VOLT_TOLERANCE_V
    if not clears_band:
        findings.append(
            "the step lands at %.3f V, inside the %.3f V trip band; that is a "
            "genuine undervoltage stimulus, not a noise one, and a trip would "
            "be the correct response" % (lower_v, trip_band_v)
        )
    if upper_v < trip_band_v - VOLT_TOLERANCE_V:
        findings.append(
            "the step starts at %.3f V, already inside the %.3f V trip band"
            % (upper_v, trip_band_v)
        )

    amplitude_sufficient = (
        stimulus["step_amplitude_v"] >= needed_v - VOLT_TOLERANCE_V
    )
    if not amplitude_sufficient:
        findings.append(
            "step amplitude %.3f V is under the %.3f V the declared "
            "disturbance envelope calls for"
            % (stimulus["step_amplitude_v"], needed_v)
        )

    demonstrable = needed_v <= headroom_v + VOLT_TOLERANCE_V
    if not demonstrable:
        findings.append(
            "the envelope needs %.3f V but only %.3f V of headroom sits above "
            "the trip band; the threshold is too close to the operating point "
            "for this immunity to be demonstrable at all" % (needed_v, headroom_v)
        )

    dwell_sufficient = stimulus["dwell_s"] >= needed_dwell_s - TIME_TOLERANCE_S
    if not dwell_sufficient:
        findings.append(
            "dwell %.6f s is under the %.6f s the detection chain needs; a "
            "no-trip result would mean the chain was still settling, not that "
            "it was immune" % (stimulus["dwell_s"], needed_dwell_s)
        )

    edge_sufficient = slew >= noise["disturbance_slew_v_per_s"] * (
        1.0 - 1e-9
    )
    if not edge_sufficient:
        findings.append(
            "the edge runs at %.1f V/s against a disturbance at %.1f V/s, so "
            "the sensing filter sees a gentler event than the real one"
            % (slew, noise["disturbance_slew_v_per_s"])
        )

    repeated = stimulus["repetitions"] >= MIN_REPETITIONS
    if not repeated:
        findings.append(
            "the step is applied %d time(s); immunity is a repeated result and "
            "at least %d applications are needed"
            % (stimulus["repetitions"], MIN_REPETITIONS)
        )

    runs_graded = "runs" in spec
    run_count = 0
    tripped_runs = []
    if runs_graded:
        run_count, tripped_runs = grade_runs(spec["runs"])
        if run_count < stimulus["repetitions"]:
            findings.append(
                "%d run(s) were recorded against %d declared applications"
                % (run_count, stimulus["repetitions"])
            )
        for name in tripped_runs:
            findings.append(
                "run %r tripped on a stimulus that stays clear of the trip "
                "band; the protection is reacting to noise" % name
            )

    design_sound = (
        clears_band
        and upper_v >= trip_band_v - VOLT_TOLERANCE_V
        and amplitude_sufficient
        and demonstrable
        and dwell_sufficient
        and edge_sufficient
        and repeated
    )
    demonstrated = (
        design_sound
        and runs_graded
        and not tripped_runs
        and run_count >= stimulus["repetitions"]
    )
    compliant = demonstrated if runs_graded else design_sound
    return {
        "upper_level_v": upper_v,
        "lower_level_v": lower_v,
        "trip_band_v": trip_band_v,
        "clears_trip_band": clears_band,
        "required_amplitude_v": needed_v,
        "amplitude_headroom_v": headroom_v,
        "amplitude_sufficient": amplitude_sufficient,
        "demonstrable": demonstrable,
        "required_dwell_s": needed_dwell_s,
        "dwell_sufficient": dwell_sufficient,
        "slew_rate_v_per_s": slew,
        "edge_sufficient": edge_sufficient,
        "repetitions": stimulus["repetitions"],
        "repeated_enough": repeated,
        "runs_graded": runs_graded,
        "run_count": run_count,
        "tripped_runs": tripped_runs,
        "design_sound": design_sound,
        "immunity_demonstrated": demonstrated,
        "verdict": "compliant" if compliant else "non-compliant",
        "findings": findings,
    }
