#!/usr/bin/env python3
"""Radiated electric susceptibility run sequence, clause 5.4.11.4.

Paraphrased procedure, no verbatim standard text. The clause covers two things
that sit side by side in the same run: the radiation-safety state the chamber
has to be in before any power reaches the antenna, and the stepped walk across
the test frequency range that follows. This module models both:

  forward power + antenna gain -> power density at a distance
                               -> hazard clearance distance vs the exposure limit
  safety provisions            -> present, or the run does not start
  span + maximum step ratio    -> the step ladder the walk has to follow
  recorded steps               -> skipped stretches, oversized jumps, short dwells
  aggregate                    -> run verdict with findings and limitations

The ladder is built by repeated multiplication rather than from a logarithm
count, so the step set is reproducible on any platform: libm powers and logs
are not correctly rounded and disagree in the last bits between hosts.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Relative tolerance for frequency comparisons and step ratios. Frequencies
# arrive as floats from a controller and a ratio that should land exactly on
# the ladder can miss by a few units in the last place.
REL_TOL = 1e-9

# Absolute tolerance for time comparisons, in seconds.
ABS_TOL = 1e-9

# Provisions that have to be in place before the amplifier is keyed. These are
# states of the chamber and the crew, not instrument settings.
REQUIRED_SAFETY_PROVISIONS = (
    "chamber-door-interlock-armed",
    "personnel-clear-of-the-field-volume",
    "hazard-warning-indicator-lit",
    "forward-power-continuously-monitored",
    "emergency-power-cut-within-reach",
)

# Permissible exposure power density for occupied areas, watt per square metre.
# A site limit may be lower; it is passed in rather than edited here.
DEFAULT_EXPOSURE_LIMIT_W_PER_M2 = 10.0

# Shortest dwell that is meaningful whatever the unit does, in seconds. The
# dwell a step actually needs is the longer of this and the unit's own
# response time, because a fault that takes two seconds to appear is invisible
# to a one-second step.
MINIMUM_STEP_DWELL_S = 1.0

CATEGORY_ON_LADDER = "on-ladder"
CATEGORY_OVERSIZED_JUMP = "oversized-jump"
CATEGORY_SHORT_DWELL = "short-dwell"

VERDICT_RUN_STANDS = "run-stands"
VERDICT_RUN_REJECTED = "run-rejected"


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


def linear_gain(gain_dbi):
    """Convert an antenna gain in decibels over isotropic to a plain ratio."""
    gain = _number({"v": gain_dbi}, "v", "gain_dbi")
    return 10.0 ** (gain / 10.0)


def power_density(forward_power_w, gain_dbi, distance_m):
    """Power density on boresight at a distance, watt per square metre.

    The antenna concentrates the forward power into its main beam, so the
    density is the isotropic spread P/(4*pi*d^2) multiplied by the gain.
    """
    power = _number({"v": forward_power_w}, "v", "forward_power_w")
    distance = _number({"v": distance_m}, "v", "distance_m")
    if power < 0.0:
        raise ValueError("forward_power_w must be >= 0, got %g" % power)
    if distance <= 0.0:
        raise ValueError("distance_m must be > 0, got %g" % distance)
    return power * linear_gain(gain_dbi) / (4.0 * math.pi * distance * distance)


def hazard_clearance_distance(
    forward_power_w, gain_dbi, exposure_limit_w_per_m2=DEFAULT_EXPOSURE_LIMIT_W_PER_M2
):
    """Distance on boresight inside which the density exceeds the exposure limit."""
    power = _number({"v": forward_power_w}, "v", "forward_power_w")
    limit = _number({"v": exposure_limit_w_per_m2}, "v", "exposure_limit_w_per_m2")
    if power < 0.0:
        raise ValueError("forward_power_w must be >= 0, got %g" % power)
    if limit <= 0.0:
        raise ValueError("exposure_limit_w_per_m2 must be > 0, got %g" % limit)
    return math.sqrt(power * linear_gain(gain_dbi) / (4.0 * math.pi * limit))


def validate_safety_provisions(provisions):
    """Validate the pre-power safety state and return it normalized."""
    where = "provisions"
    if not isinstance(provisions, dict):
        raise ValueError("%s: must be a mapping of provision -> boolean" % where)
    normalized = {}
    for name in REQUIRED_SAFETY_PROVISIONS:
        if name not in provisions:
            raise ValueError("%s: missing required provision %r" % (where, name))
        value = provisions[name]
        if not isinstance(value, bool):
            raise ValueError(
                "%s: provision %r must be a boolean, got %r" % (where, name, value)
            )
        normalized[name] = value
    for name in provisions:
        if name not in REQUIRED_SAFETY_PROVISIONS:
            raise ValueError("%s: unrecognized provision %r" % (where, name))
    return normalized


def validate_span(start_hz, stop_hz):
    """Validate the declared test frequency range and return it as a pair."""
    start = _number({"v": start_hz}, "v", "start_hz")
    stop = _number({"v": stop_hz}, "v", "stop_hz")
    if start <= 0.0:
        raise ValueError("start_hz must be > 0, got %g" % start)
    if stop <= start:
        raise ValueError("stop_hz must be above start_hz, got %g <= %g" % (stop, start))
    return (start, stop)


def step_ladder(start_hz, stop_hz, max_fractional_step):
    """Build the frequency ladder the exposure walk has to follow.

    Each rung sits a fixed fraction above the one below it, so the ladder is
    geometric: a susceptibility mechanism is a fractional-bandwidth effect, and
    a fixed hertz increment would crawl at the bottom of the span and stride
    over resonances at the top. The final rung is the declared stop frequency.
    """
    start, stop = validate_span(start_hz, stop_hz)
    step = _number({"v": max_fractional_step}, "v", "max_fractional_step")
    if not (0.0 < step < 1.0):
        raise ValueError("max_fractional_step must be in (0, 1), got %g" % step)
    rungs = [start]
    current = start
    while current * (1.0 + step) < stop * (1.0 - REL_TOL):
        current = current * (1.0 + step)
        rungs.append(current)
    rungs.append(stop)
    return tuple(rungs)


def normalize_steps(steps):
    """Validate the recorded exposure steps and return them sorted by frequency."""
    where = "steps"
    if not isinstance(steps, (list, tuple)):
        raise ValueError("%s: must be a sequence of step records" % where)
    if not steps:
        raise ValueError("%s: no exposure step was recorded" % where)
    normalized = []
    seen = []
    for index, raw in enumerate(steps):
        tag = "%s[%d]" % (where, index)
        if not isinstance(raw, dict):
            raise ValueError("%s: step must be a mapping" % tag)
        frequency = _number(raw, "frequency_hz", tag)
        dwell = _number(raw, "dwell_s", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if dwell <= 0.0:
            raise ValueError("%s: dwell_s must be > 0, got %g" % (tag, dwell))
        for previous in seen:
            if math.isclose(previous, frequency, rel_tol=REL_TOL, abs_tol=0.0):
                raise ValueError(
                    "%s: frequency %g Hz recorded more than once" % (tag, frequency)
                )
        seen.append(frequency)
        normalized.append({"frequency_hz": frequency, "dwell_s": dwell})
    normalized.sort(key=lambda s: s["frequency_hz"])
    return tuple(normalized)


def dwell_floor(unit_response_time_s, minimum_dwell_s=MINIMUM_STEP_DWELL_S):
    """Shortest dwell a step may use: the unit's response time, never below the floor."""
    response = _number({"v": unit_response_time_s}, "v", "unit_response_time_s")
    floor = _number({"v": minimum_dwell_s}, "v", "minimum_dwell_s")
    if response <= 0.0:
        raise ValueError("unit_response_time_s must be > 0, got %g" % response)
    if floor <= 0.0:
        raise ValueError("minimum_dwell_s must be > 0, got %g" % floor)
    return max(response, floor)


def step_coverage(recorded, start_hz, stop_hz, max_fractional_step):
    """Reduce the recorded frequencies to the stretches the walk stepped over.

    A pair of neighbouring steps separated by more than the allowed fraction
    leaves a stretch of the span that was never driven, and a susceptibility
    sitting in it is invisible to the run.
    """
    start, stop = validate_span(start_hz, stop_hz)
    step = _number({"v": max_fractional_step}, "v", "max_fractional_step")
    if not (0.0 < step < 1.0):
        raise ValueError("max_fractional_step must be in (0, 1), got %g" % step)
    frequencies = sorted(float(f) for f in recorded)
    if not frequencies:
        raise ValueError("recorded: no exposure frequency was recorded")
    allowed = 1.0 + step
    jumps = []
    edges = []
    # The walk may begin one allowed step above the declared start without
    # leaving a stretch undriven; further up than that and the bottom of the
    # span was never reached.
    if frequencies[0] > start * allowed * (1.0 + REL_TOL):
        edges.append(
            "the walk starts at %g Hz, more than one step above the declared "
            "%g Hz" % (frequencies[0], start)
        )
    if frequencies[-1] * allowed * (1.0 + REL_TOL) < stop:
        edges.append(
            "the walk stops at %g Hz, more than one step below the declared "
            "%g Hz" % (frequencies[-1], stop)
        )
    for lower, upper in zip(frequencies, frequencies[1:]):
        ratio = upper / lower
        if ratio > allowed * (1.0 + REL_TOL):
            jumps.append(
                {
                    "from_hz": lower,
                    "to_hz": upper,
                    "ratio": ratio,
                    "allowed_ratio": allowed,
                }
            )
    return {
        "frequencies": tuple(frequencies),
        "oversized_jumps": tuple(jumps),
        "edge_findings": tuple(edges),
        "continuous": not jumps and not edges,
    }


def assess_exposure_run(
    provisions,
    steps,
    start_hz,
    stop_hz,
    max_fractional_step,
    unit_response_time_s,
    forward_power_w,
    gain_dbi,
    occupied_distance_m,
    exposure_limit_w_per_m2=DEFAULT_EXPOSURE_LIMIT_W_PER_M2,
):
    """Full clause 5.4.11.4 assessment of one stepped radiated exposure."""
    checked = validate_safety_provisions(provisions)
    recorded = normalize_steps(steps)
    ladder = step_ladder(start_hz, stop_hz, max_fractional_step)
    coverage = step_coverage(
        [s["frequency_hz"] for s in recorded], start_hz, stop_hz, max_fractional_step
    )
    floor = dwell_floor(unit_response_time_s)
    clearance = hazard_clearance_distance(
        forward_power_w, gain_dbi, exposure_limit_w_per_m2
    )
    occupied = _number({"v": occupied_distance_m}, "v", "occupied_distance_m")
    if occupied <= 0.0:
        raise ValueError("occupied_distance_m must be > 0, got %g" % occupied)
    density = power_density(forward_power_w, gain_dbi, occupied)

    findings = []
    limitations = []

    for name in REQUIRED_SAFETY_PROVISIONS:
        if not checked[name]:
            findings.append("safety provision not in place: %s" % name)

    if occupied < clearance and not math.isclose(
        occupied, clearance, rel_tol=REL_TOL, abs_tol=0.0
    ):
        findings.append(
            "the nearest occupied position sits %g m inside the %g m hazard "
            "clearance" % (clearance - occupied, clearance)
        )

    graded = []
    short_dwells = 0
    for entry in recorded:
        category = CATEGORY_ON_LADDER
        headroom = entry["dwell_s"] - floor
        if entry["dwell_s"] < floor and not math.isclose(
            entry["dwell_s"], floor, rel_tol=0.0, abs_tol=ABS_TOL
        ):
            category = CATEGORY_SHORT_DWELL
            short_dwells += 1
            findings.append(
                "the step at %g Hz dwelt %g s, short of the %g s floor"
                % (entry["frequency_hz"], entry["dwell_s"], floor)
            )
        graded.append(
            {
                "frequency_hz": entry["frequency_hz"],
                "dwell_s": entry["dwell_s"],
                "dwell_headroom_s": headroom,
                "category": category,
            }
        )

    for jump in coverage["oversized_jumps"]:
        findings.append(
            "the walk stepped from %g Hz to %g Hz, a ratio of %g against the %g "
            "allowed" % (jump["from_hz"], jump["to_hz"], jump["ratio"], jump["allowed_ratio"])
        )
    for edge in coverage["edge_findings"]:
        findings.append(edge)

    if len(recorded) > len(ladder):
        limitations.append(
            "the walk used %d steps where the ladder needs %d, costing chamber time"
            % (len(recorded), len(ladder))
        )

    total_dwell = sum(entry["dwell_s"] for entry in recorded)

    return {
        "provisions": checked,
        "hazard_clearance_m": clearance,
        "power_density_at_occupied_position_w_per_m2": density,
        "ladder": ladder,
        "ladder_steps": len(ladder),
        "recorded_steps": len(recorded),
        "steps": tuple(graded),
        "dwell_floor_s": floor,
        "short_dwell_steps": short_dwells,
        "coverage": coverage,
        "total_dwell_s": total_dwell,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_RUN_STANDS if not findings else VERDICT_RUN_REJECTED,
    }
