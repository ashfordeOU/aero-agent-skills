#!/usr/bin/env python3
"""Running the illumination stability soak on photovoltaic samples.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.12.2 (holding samples under continuous
simulated sunlight at a controlled temperature for two days). Paraphrased
into an implementable procedure; no standard text is reproduced.

The run has three obligations and they fail independently.

The light has to be sunlight, not merely bright. A solar simulator is graded
on three separate axes -- how close its total irradiance sits to the
reference solar constant, how evenly that irradiance falls across the sample
plane, and how steadily it holds over the soak. A lamp an hour from the end
of its life can meet the first and fail the third.

The soak has to be continuous. Illuminated segments separated by darkness
are not one soak: carrier injection stops, metastable defects relax, and the
article partially recovers, so the second segment starts from a different
state than the first ended in. Two twenty-four hour segments a week apart
are two one-day soaks, not one two-day soak, and the run is graded on the
longest unbroken chain rather than on the arithmetic total.

The temperature has to be controlled. Output moves with temperature far
faster than with illumination history, so a segment that drifted off the
reference temperature contributes drift that cannot be separated from the
light-driven drift the test is looking for.

Finally, the before and after electrical measurements are what turn a soak
into a test. The stability figure is a ratio, and without the pre-soak
reference the post-soak output is an absolute number with nothing to divide
by.

The required duration, reference irradiance and its tolerance, uniformity
and stability allowances, interruption allowance and the temperature window
below are a declared policy, not physical constants: a project substitutes
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Characterisation point -> what the electrical measurement at it supplies.
CHARACTERISATION_POINTS = {
    "pre-soak-iv": "pre-soak-reference-output",
    "intermediate-soak-iv": "soak-drift-intermediate-point",
    "post-soak-iv": "end-of-soak-output",
    "post-recovery-iv": "dark-recovery-output",
}

RECOGNISED_POINTS = tuple(sorted(CHARACTERISATION_POINTS))

MANDATORY_POINTS = ("pre-soak-iv", "post-soak-iv")

SOAK_CONDITIONS_VIOLATED = "soak-conditions-violated"
SOAK_NOT_CONTINUOUS = "soak-not-continuous"
SOAK_DURATION_SHORTFALL = "soak-duration-shortfall"
CHARACTERISATION_INCOMPLETE = "characterisation-incomplete"
ILLUMINATION_SOAK_CONFORMS = "illumination-soak-conforms"

DEFAULT_SOAK_POLICY = {
    "required_continuous_hours": 48.0,
    "reference_irradiance_w_per_m2": 1367.0,
    "irradiance_tolerance_fraction": 0.05,
    "max_plane_non_uniformity": 0.05,
    "max_temporal_instability": 0.02,
    "max_interruption_hours": 0.25,
    "reference_temperature_c": 25.0,
    "temperature_tolerance_c": 2.0,
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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_soak_policy(policy):
    """Check an illumination-soak policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "required_continuous_hours", policy.get("required_continuous_hours")
    )
    _require_positive(
        "reference_irradiance_w_per_m2", policy.get("reference_irradiance_w_per_m2")
    )
    tolerance = _require_positive(
        "irradiance_tolerance_fraction", policy.get("irradiance_tolerance_fraction")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "irradiance_tolerance_fraction %g must be below one; a band that "
            "reaches darkness accepts any lamp" % tolerance
        )
    _require_positive(
        "max_plane_non_uniformity", policy.get("max_plane_non_uniformity")
    )
    _require_positive(
        "max_temporal_instability", policy.get("max_temporal_instability")
    )
    _require_non_negative(
        "max_interruption_hours", policy.get("max_interruption_hours")
    )
    _require_number("reference_temperature_c", policy.get("reference_temperature_c"))
    _require_positive("temperature_tolerance_c", policy.get("temperature_tolerance_c"))
    return policy


def segment_hours(segment):
    """Illuminated duration of one segment, from its start and end marks."""
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (segment,))
    start = _require_non_negative("start_hours", segment.get("start_hours"))
    end = _require_number("end_hours", segment.get("end_hours"))
    if end <= start:
        raise ValueError(
            "end_hours %g must be after start_hours %g" % (end, start)
        )
    return end - start


def ordered_segments(segments):
    """Validate a segment list is in run order and free of overlaps."""
    if not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a sequence of segment mappings")
    if not segments:
        raise ValueError("segments must hold at least one illuminated segment")
    previous_end = None
    for index, segment in enumerate(segments):
        segment_hours(segment)
        start = float(segment["start_hours"])
        if previous_end is not None and start < previous_end:
            raise ValueError(
                "segment %d starts at %g hours, before segment %d ended at %g"
                % (index, start, index - 1, previous_end)
            )
        previous_end = float(segment["end_hours"])
    return tuple(segments)


def total_illuminated_hours(segments):
    """Arithmetic total of illuminated time across every segment."""
    return sum(segment_hours(segment) for segment in ordered_segments(segments))


def interruption_hours(segments):
    """Dark gaps between consecutive illuminated segments, in run order."""
    ordered = ordered_segments(segments)
    gaps = []
    for index in range(1, len(ordered)):
        gaps.append(
            float(ordered[index]["start_hours"]) - float(ordered[index - 1]["end_hours"])
        )
    return tuple(gaps)


def longest_continuous_hours(segments, policy=DEFAULT_SOAK_POLICY):
    """Longest unbroken illuminated stretch, gaps inside the allowance bridged."""
    validate_soak_policy(policy)
    ordered = ordered_segments(segments)
    allowance = float(policy["max_interruption_hours"])
    best = 0.0
    running = 0.0
    previous_end = None
    for segment in ordered:
        start = float(segment["start_hours"])
        if previous_end is not None:
            gap = start - previous_end
            if not _at_most(gap, allowance):
                running = 0.0
        running += segment_hours(segment)
        if running > best:
            best = running
        previous_end = float(segment["end_hours"])
    return best


def plane_non_uniformity(max_irradiance_w_per_m2, min_irradiance_w_per_m2):
    """Fractional spread of irradiance across the sample plane."""
    high = _require_positive("max_irradiance_w_per_m2", max_irradiance_w_per_m2)
    low = _require_positive("min_irradiance_w_per_m2", min_irradiance_w_per_m2)
    if low > high and not math.isclose(low, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "min_irradiance_w_per_m2 %g exceeds max_irradiance_w_per_m2 %g"
            % (low, high)
        )
    return (high - low) / (high + low)


def simulator_plane_uniform(
    max_irradiance_w_per_m2, min_irradiance_w_per_m2, policy=DEFAULT_SOAK_POLICY
):
    """True when every sample on the plane sees the same simulated sunlight."""
    validate_soak_policy(policy)
    spread = plane_non_uniformity(max_irradiance_w_per_m2, min_irradiance_w_per_m2)
    return _at_most(spread, float(policy["max_plane_non_uniformity"]))


def simulator_temporally_stable(temporal_instability, policy=DEFAULT_SOAK_POLICY):
    """True when the lamp holds its output steadily enough over the soak."""
    validate_soak_policy(policy)
    instability = _require_non_negative("temporal_instability", temporal_instability)
    return _at_most(instability, float(policy["max_temporal_instability"]))


def irradiance_on_reference(irradiance_w_per_m2, policy=DEFAULT_SOAK_POLICY):
    """True when a segment ran at the reference solar irradiance within band."""
    validate_soak_policy(policy)
    irradiance = _require_positive("irradiance_w_per_m2", irradiance_w_per_m2)
    reference = float(policy["reference_irradiance_w_per_m2"])
    offset = abs(irradiance - reference) / reference
    return _at_most(offset, float(policy["irradiance_tolerance_fraction"]))


def temperature_controlled(temperature_c, policy=DEFAULT_SOAK_POLICY):
    """True when a segment held the reference temperature within tolerance."""
    validate_soak_policy(policy)
    temperature = _require_number("temperature_c", temperature_c)
    offset = abs(temperature - float(policy["reference_temperature_c"]))
    return _at_most(offset, float(policy["temperature_tolerance_c"]))


def characterisation_inventory(points):
    """Group the electrical characterisation points, rejecting an unknown one."""
    if not isinstance(points, (list, tuple, set, frozenset)):
        raise ValueError("points must be a collection of characterisation points")
    grouped = []
    for point in points:
        if point not in CHARACTERISATION_POINTS:
            raise ValueError(
                "unknown characterisation point %r; recognised points are %s"
                % (point, ", ".join(RECOGNISED_POINTS))
            )
        if point not in grouped:
            grouped.append(point)
    return tuple(sorted(grouped))


def missing_characterisation_points(points):
    """Mandatory characterisation points the soak did not take."""
    grouped = characterisation_inventory(points)
    return tuple(point for point in MANDATORY_POINTS if point not in grouped)


def assess_illumination_soak_run(case, policy=DEFAULT_SOAK_POLICY):
    """Full clause 6.4.3.12.2 judgement for one illumination stability soak."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_soak_policy(policy)

    simulator = case.get("simulator")
    if not isinstance(simulator, dict):
        raise ValueError("case is missing a simulator block")
    if "characterisation_points" not in case:
        raise ValueError(
            "case is missing characterisation_points; an absent inventory is "
            "not an empty one"
        )

    segments = ordered_segments(case.get("segments"))
    total_hours = total_illuminated_hours(segments)
    continuous_hours = longest_continuous_hours(segments, policy)
    gaps = interruption_hours(segments)

    plane_max = _require_positive(
        "simulator plane_max_irradiance_w_per_m2",
        simulator.get("plane_max_irradiance_w_per_m2"),
    )
    plane_min = _require_positive(
        "simulator plane_min_irradiance_w_per_m2",
        simulator.get("plane_min_irradiance_w_per_m2"),
    )
    instability = _require_non_negative(
        "simulator temporal_instability", simulator.get("temporal_instability")
    )
    spread = plane_non_uniformity(plane_max, plane_min)

    grouped = characterisation_inventory(case["characterisation_points"])
    absent = missing_characterisation_points(case["characterisation_points"])

    required_hours = float(policy["required_continuous_hours"])
    findings = []
    result = {
        "total_illuminated_hours": total_hours,
        "longest_continuous_hours": continuous_hours,
        "required_continuous_hours": required_hours,
        "interruption_hours": gaps,
        "plane_non_uniformity": spread,
        "temporal_instability": instability,
        "characterisation_points": grouped,
        "missing_characterisation_points": absent,
        "findings": findings,
    }

    conditions_ok = True
    if not simulator_plane_uniform(plane_max, plane_min, policy):
        conditions_ok = False
        findings.append(
            "simulated sunlight spreads %.4g across the sample plane, above the "
            "%.4g allowance, so samples on one plane took different soaks"
            % (spread, float(policy["max_plane_non_uniformity"]))
        )
    if not simulator_temporally_stable(instability, policy):
        conditions_ok = False
        findings.append(
            "the simulator held to %.4g over the soak, above the %.4g temporal "
            "stability allowance"
            % (instability, float(policy["max_temporal_instability"]))
        )
    for index, segment in enumerate(segments):
        irradiance = _require_positive(
            "segment %d irradiance_w_per_m2" % index,
            segment.get("irradiance_w_per_m2"),
        )
        if not irradiance_on_reference(irradiance, policy):
            conditions_ok = False
            findings.append(
                "segment %d ran at %.5g W/m2, off the %.5g W/m2 reference "
                "irradiance by more than the allowed band"
                % (index, irradiance, float(policy["reference_irradiance_w_per_m2"]))
            )
        temperature = _require_number(
            "segment %d temperature_c" % index, segment.get("temperature_c")
        )
        if not temperature_controlled(temperature, policy):
            conditions_ok = False
            findings.append(
                "segment %d sat at %.4g C, off the %.4g C reference temperature, "
                "adding a thermal term to the measured drift"
                % (index, temperature, float(policy["reference_temperature_c"]))
            )
    result["conditions_acceptable"] = conditions_ok

    duration_ok = _at_least(total_hours, required_hours)
    continuity_ok = _at_least(continuous_hours, required_hours)
    result["duration_met"] = duration_ok
    result["continuous"] = continuity_ok

    if not duration_ok:
        findings.append(
            "the run accumulated %.4g illuminated hours against the %.4g hour "
            "requirement" % (total_hours, required_hours)
        )
    elif not continuity_ok:
        findings.append(
            "the longest unbroken stretch was %.4g hours against the %.4g hour "
            "requirement; darkness lets the article recover, so the segments "
            "are separate soaks" % (continuous_hours, required_hours)
        )

    if absent:
        findings.append(
            "no electrical characterisation was taken at %s, so the stability "
            "ratio the soak exists to produce cannot be formed"
            % ", ".join(absent)
        )

    if not conditions_ok:
        result["verdict"] = SOAK_CONDITIONS_VIOLATED
    elif not duration_ok:
        result["verdict"] = SOAK_DURATION_SHORTFALL
    elif not continuity_ok:
        result["verdict"] = SOAK_NOT_CONTINUOUS
    elif absent:
        result["verdict"] = CHARACTERISATION_INCOMPLETE
    else:
        result["verdict"] = ILLUMINATION_SOAK_CONFORMS
    return result
