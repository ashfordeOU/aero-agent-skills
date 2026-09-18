#!/usr/bin/env python3
"""Process parameter monitoring and build data logging for powder bed fusion.

Anchor: the equipment clauses of ECSS-Q-ST-70-80C on in-process
monitoring and the build data record. The steps below are a paraphrase
into implementable form; no standard text is reproduced.

A build log is evidence, and evidence has two failure modes. The first
is a parameter that left its window: the log has to say when, for how
long, how far, and - because a defect is found on a part and not on a
time axis - which layers that excursion sits under. The second is
quieter: the log itself is incomplete. A channel that was never
recorded, a sampling interval slower than the one required, or a gap
where the recorder stopped all leave a build that cannot be shown to
have been in control, whether or not it was.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MONITORED_PARAMETERS = (
    "laser-power-w",
    "scan-speed-mm-s",
    "residual-oxygen-ppm",
    "chamber-pressure-mbar",
    "build-plate-temperature-c",
    "recoater-force-n",
    "gas-flow-velocity-m-s",
)

PARAMETER_WITHIN_LIMITS = "within-limits"
PARAMETER_SHORT_EXCURSION = "short-excursion-recorded"
PARAMETER_NONCONFORMANCE = "out-of-limit-nonconformance"

LOG_ACCEPTABLE = "build-log-acceptable"
LOG_WITH_OBSERVATIONS = "build-log-acceptable-with-observations"
LOG_NONCONFORMING = "build-log-nonconforming"

SAMPLING_ADEQUATE = "sampling-adequate"
SAMPLING_TOO_SLOW = "sampling-slower-than-required"
SAMPLING_GAPPED = "sampling-gap-in-the-record"

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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An excursion duration is a difference of sample times, so an episode
    that lasts exactly the allowed time can land a few units in the last
    place above it. The allowance is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_parameter_limits(limits):
    """Normalize the control window and excursion allowance of one channel."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    for key in ("lower", "upper"):
        if key not in limits:
            raise ValueError("limits are missing %s" % key)
    lower = _require_number("lower", limits["lower"])
    upper = _require_number("upper", limits["upper"])
    if lower >= upper:
        raise ValueError("the lower limit is not below the upper limit")
    return {
        "lower": lower,
        "upper": upper,
        "max_excursion_s": _require_non_negative(
            "max_excursion_s", limits.get("max_excursion_s", 0.0)
        ),
    }


def validate_samples(samples):
    """Normalize one channel's time series and reject a broken time axis."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("samples must be a sequence of at least two readings")
    resolved = []
    previous = None
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("every sample must be a mapping, got %r" % (sample,))
        time_s = _require_non_negative("t_s", sample.get("t_s"))
        value = _require_number("value", sample.get("value"))
        if previous is not None and not time_s > previous:
            raise ValueError(
                "sample times must increase; %g follows %g" % (time_s, previous)
            )
        previous = time_s
        resolved.append({"t_s": time_s, "value": value})
    return tuple(resolved)


def excursion_episodes(samples, limits):
    """Contiguous runs outside the control window, with duration and depth."""
    samples = validate_samples(samples)
    limits = validate_parameter_limits(limits)
    episodes = []
    current = None
    for index, sample in enumerate(samples):
        above = not _at_most(sample["value"], limits["upper"])
        below = not _at_least(sample["value"], limits["lower"])
        if above or below:
            deviation = (
                sample["value"] - limits["upper"]
                if above
                else limits["lower"] - sample["value"]
            )
            bound = "upper" if above else "lower"
            if current is None:
                current = {
                    "start_s": sample["t_s"],
                    "end_s": sample["t_s"],
                    "sample_count": 0,
                    "worst_value": sample["value"],
                    "worst_deviation": deviation,
                    "bound_crossed": bound,
                }
            current["sample_count"] += 1
            if deviation > current["worst_deviation"]:
                current["worst_deviation"] = deviation
                current["worst_value"] = sample["value"]
                current["bound_crossed"] = bound
            current["end_s"] = (
                samples[index + 1]["t_s"] if index + 1 < len(samples) else sample["t_s"]
            )
        elif current is not None:
            current["end_s"] = sample["t_s"]
            current["duration_s"] = current["end_s"] - current["start_s"]
            episodes.append(current)
            current = None
    if current is not None:
        current["duration_s"] = current["end_s"] - current["start_s"]
        episodes.append(current)
    return tuple(episodes)


def sampling_statistics(samples, build_duration_s):
    """Interval and coverage of one channel against the build it describes."""
    samples = validate_samples(samples)
    duration = _require_positive("build_duration_s", build_duration_s)
    if samples[-1]["t_s"] > duration:
        raise ValueError("a sample is timestamped after the end of the build")
    intervals = []
    for index in range(1, len(samples)):
        intervals.append(samples[index]["t_s"] - samples[index - 1]["t_s"])
    intervals.sort()
    middle = len(intervals) // 2
    if len(intervals) % 2 == 1:
        median = intervals[middle]
    else:
        median = 0.5 * (intervals[middle - 1] + intervals[middle])
    covered = samples[-1]["t_s"] - samples[0]["t_s"]
    return {
        "sample_count": len(samples),
        "median_interval_s": median,
        "largest_interval_s": intervals[-1],
        "covered_s": covered,
        "coverage_fraction": covered / duration,
    }


def grade_sampling(samples, build_duration_s, required_interval_s,
                   max_gap_s, min_coverage_fraction=1.0):
    """Grade the record itself: fast enough, gapless enough, complete enough."""
    stats = sampling_statistics(samples, build_duration_s)
    required_interval = _require_positive("required_interval_s", required_interval_s)
    max_gap = _require_positive("max_gap_s", max_gap_s)
    coverage_floor = _require_non_negative(
        "min_coverage_fraction", min_coverage_fraction
    )
    if coverage_floor > 1.0:
        raise ValueError("min_coverage_fraction must not exceed 1")
    findings = []
    verdict = SAMPLING_ADEQUATE
    if not _at_most(stats["median_interval_s"], required_interval):
        verdict = SAMPLING_TOO_SLOW
        findings.append(
            "median sampling interval %.4g s is slower than the required %.4g s"
            % (stats["median_interval_s"], required_interval)
        )
    if not _at_most(stats["largest_interval_s"], max_gap):
        verdict = SAMPLING_GAPPED
        findings.append(
            "a %.4g s gap sits in the record, past the allowed %.4g s"
            % (stats["largest_interval_s"], max_gap)
        )
    if not _at_least(stats["coverage_fraction"], coverage_floor):
        verdict = SAMPLING_GAPPED
        findings.append(
            "the record covers %.3f of the build, below the required %.3f"
            % (stats["coverage_fraction"], coverage_floor)
        )
    stats["verdict"] = verdict
    stats["findings"] = findings
    return stats


def missing_channels(required_channels, logged_channels):
    """Channels the project required that never reached the record."""
    for label, value in (
        ("required_channels", required_channels),
        ("logged_channels", logged_channels),
    ):
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    required = set()
    for item in required_channels:
        name = _require_text("required channel", item)
        if name not in MONITORED_PARAMETERS:
            raise ValueError("unknown monitored parameter %r" % name)
        required.add(name)
    logged = set()
    for item in logged_channels:
        logged.add(_require_text("logged channel", item))
    return tuple(sorted(required - logged))


def layers_touched(start_s, end_s, layer_time_s):
    """Layer indices an excursion sits under, counting the first layer as one."""
    start = _require_non_negative("start_s", start_s)
    end = _require_non_negative("end_s", end_s)
    layer_time = _require_positive("layer_time_s", layer_time_s)
    if end < start:
        raise ValueError("the excursion ends before it starts")
    first = int(start // layer_time) + 1
    last = int(end // layer_time) + 1
    return tuple(range(first, last + 1))


def assess_parameter(parameter, samples, limits, layer_time_s=None):
    """Grade one channel: episodes, worst deviation and the layers beneath."""
    name = _require_text("parameter", parameter)
    if name not in MONITORED_PARAMETERS:
        raise ValueError("unknown monitored parameter %r" % name)
    limits = validate_parameter_limits(limits)
    episodes = excursion_episodes(samples, limits)
    affected = set()
    total_out_of_limit_s = 0.0
    worst_deviation = 0.0
    long_episodes = []
    for episode in episodes:
        total_out_of_limit_s += episode["duration_s"]
        worst_deviation = max(worst_deviation, episode["worst_deviation"])
        if not _at_most(episode["duration_s"], limits["max_excursion_s"]):
            long_episodes.append(episode)
        if layer_time_s is not None:
            affected.update(
                layers_touched(episode["start_s"], episode["end_s"], layer_time_s)
            )
    if not episodes:
        verdict = PARAMETER_WITHIN_LIMITS
    elif long_episodes:
        verdict = PARAMETER_NONCONFORMANCE
    else:
        verdict = PARAMETER_SHORT_EXCURSION
    return {
        "parameter": name,
        "episodes": episodes,
        "episode_count": len(episodes),
        "total_out_of_limit_s": total_out_of_limit_s,
        "worst_deviation": worst_deviation,
        "affected_layers": tuple(sorted(affected)),
        "verdict": verdict,
    }


def assess_build_monitoring(case):
    """Full build log assessment: channels, sampling, excursions, verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    channels = case.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise ValueError("case needs a non-empty channels mapping")
    build_duration = _require_positive(
        "build_duration_s", case.get("build_duration_s")
    )
    layer_time = case.get("layer_time_s")
    if layer_time is not None:
        layer_time = _require_positive("layer_time_s", layer_time)
    findings = []
    results = {}
    affected = set()
    for name in sorted(channels):
        channel = channels[name]
        if not isinstance(channel, dict):
            raise ValueError("channel %s must be a mapping" % name)
        result = assess_parameter(
            name, channel.get("samples"), channel.get("limits"), layer_time
        )
        result["sampling"] = grade_sampling(
            channel.get("samples"),
            build_duration,
            case.get("required_interval_s"),
            case.get("max_gap_s"),
            case.get("min_coverage_fraction", 1.0),
        )
        affected.update(result["affected_layers"])
        results[name] = result
        if result["verdict"] == PARAMETER_NONCONFORMANCE:
            findings.append(
                "%s left its window for longer than allowed, worst deviation "
                "%.4g at the %s bound" % (name, result["worst_deviation"],
                                          result["episodes"][0]["bound_crossed"])
            )
        elif result["verdict"] == PARAMETER_SHORT_EXCURSION:
            findings.append(
                "%s recorded %d short excursion(s) inside the allowance"
                % (name, result["episode_count"])
            )
        findings.extend("%s: %s" % (name, f) for f in result["sampling"]["findings"])
    gaps = missing_channels(case.get("required_channels", ()), tuple(channels))
    if gaps:
        findings.append("required channels never logged: %s" % ", ".join(gaps))
    sampling_clean = all(
        results[name]["sampling"]["verdict"] == SAMPLING_ADEQUATE for name in results
    )
    nonconforming = tuple(
        sorted(
            name
            for name in results
            if results[name]["verdict"] == PARAMETER_NONCONFORMANCE
        )
    )
    if nonconforming or gaps or not sampling_clean:
        verdict = LOG_NONCONFORMING
    elif any(
        results[name]["verdict"] == PARAMETER_SHORT_EXCURSION for name in results
    ):
        verdict = LOG_WITH_OBSERVATIONS
    else:
        verdict = LOG_ACCEPTABLE
    return {
        "parameters": results,
        "nonconforming_parameters": nonconforming,
        "missing_channels": gaps,
        "affected_layers": tuple(sorted(affected)),
        "verdict": verdict,
        "findings": findings,
    }
