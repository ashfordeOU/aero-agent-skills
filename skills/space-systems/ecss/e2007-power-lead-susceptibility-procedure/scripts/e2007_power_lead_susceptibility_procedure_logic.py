#!/usr/bin/env python3
"""Power-lead susceptibility injection procedure (ECSS-E-ST-20-07C, 5.4.7.4).

Offline, deterministic, standard-library only. The module walks the run
itself: the warm up that precedes it, and the stepped injection carried out
while the unit is watched for a response.

* warm up held against the longer of a floor and the declared
  stabilization time of the unit,
* the geometric frequency ladder the injection is stepped along, and the
  ratio between adjacent steps,
* the dwell each step needs, derived from the slowest response the unit
  can show,
* the level ramp at a step, its coarseness, and the point at which the
  ramp is stopped because the drive limit was reached,
* the threshold at which the unit responds, the margin that leaves
  against the required level, and the verdict for the whole run.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "WARM_UP_FLOOR_S",
    "POINTS_PER_DECADE_MIN",
    "DWELL_FLOOR_S",
    "DWELL_RESPONSE_FACTOR",
    "LEVEL_STEP_MAX_DB",
    "MARGIN_REQUIRED_DB",
    "STEP_VERDICTS",
    "check_warm_up",
    "step_ratio",
    "frequency_ladder",
    "check_step_ratio",
    "required_dwell_s",
    "check_dwell",
    "check_level_ramp",
    "susceptibility_threshold_db",
    "susceptibility_margin_db",
    "evaluate_injection_step",
    "run_injection_procedure",
]

# Absorbs binary-representation error when a ratio or a power lands a few
# units in the last place outside an exactly-met bound. It never widens the
# bound itself.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Shortest warm up accepted before the first injection, whatever the unit
# declares for itself.
WARM_UP_FLOOR_S = 900.0

# Coarsest ladder accepted: fewer points than this per decade steps over
# narrow responses.
POINTS_PER_DECADE_MIN = 10

# Dwell floor, and the multiple of the slowest response the unit can show
# that a dwell has to reach.
DWELL_FLOOR_S = 1.0
DWELL_RESPONSE_FACTOR = 3.0

# Coarsest rise accepted between two levels of the ramp at one step.
LEVEL_STEP_MAX_DB = 6.0

# Margin the response threshold has to keep above the required level.
MARGIN_REQUIRED_DB = 6.0

STEP_VERDICTS = ("conforming", "susceptible", "drive-limited")

_STEP_KEYS = (
    "frequency_hz",
    "required_level_db",
    "levels_db",
    "dwell_s",
    "response_time_s",
    "responded_at_db",
    "drive_limited",
)

_PROFILE_KEYS = (
    "warm_up_s",
    "stabilization_s",
    "start_hz",
    "stop_hz",
    "points_per_decade",
    "steps",
)


def _finding(code, subject, detail):
    """Build one procedure finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _as_nonnegative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _as_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _as_count(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (label, value))
    return value


def _within(value, allowed):
    """Bound comparison that absorbs binary-representation error."""
    return value <= allowed or math.isclose(
        value, allowed, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _at_least(value, required):
    """Lower-bound comparison that absorbs binary-representation error."""
    return value >= required or math.isclose(
        value, required, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def check_warm_up(warm_up_s, stabilization_s=0.0, floor_s=WARM_UP_FLOOR_S):
    """Check the warm up that precedes the first injection."""
    elapsed = _as_nonnegative_float(warm_up_s, "warm_up_s")
    declared = _as_nonnegative_float(stabilization_s, "stabilization_s")
    floor = _as_positive_float(floor_s, "floor_s")
    required = max(floor, declared)
    return {
        "quantity": "warm-up",
        "elapsed_s": elapsed,
        "declared_s": declared,
        "required_s": required,
        "governed_by": "stabilization" if declared > floor else "floor",
        "within": _at_least(elapsed, required),
    }


def step_ratio(points_per_decade):
    """Ratio between two adjacent points of a geometric ladder."""
    count = _as_count(points_per_decade, "points_per_decade")
    return 10.0 ** (1.0 / count)


def frequency_ladder(start_hz, stop_hz, points_per_decade):
    """Geometric ladder of injection frequencies from start to stop.

    The last rung is pinned to the stop frequency so the ladder never ends
    a representation error short of the band it had to cover.
    """
    start = _as_positive_float(start_hz, "start_hz")
    stop = _as_positive_float(stop_hz, "stop_hz")
    count = _as_count(points_per_decade, "points_per_decade")
    if stop <= start:
        raise ValueError(
            "a ladder must rise: stop %r does not exceed start %r" % (stop_hz, start_hz)
        )
    rungs = []
    index = 0
    while True:
        value = start * 10.0 ** (float(index) / count)
        if not _within(value, stop):
            break
        rungs.append(value)
        index += 1
        if index > 100000:
            raise ValueError("the ladder does not terminate; check the arguments")
    if not rungs:
        rungs.append(start)
    if math.isclose(rungs[-1], stop, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        rungs[-1] = stop
    else:
        rungs.append(stop)
    return rungs


def check_step_ratio(previous_hz, next_hz, points_per_decade):
    """Check the ratio between two adjacent injection frequencies."""
    previous = _as_positive_float(previous_hz, "previous_hz")
    following = _as_positive_float(next_hz, "next_hz")
    count = _as_count(points_per_decade, "points_per_decade")
    if following <= previous:
        raise ValueError(
            "an injection ladder must rise: %r does not follow %r"
            % (next_hz, previous_hz)
        )
    allowed = step_ratio(count)
    ratio = following / previous
    return {
        "quantity": "step-ratio",
        "previous_hz": previous,
        "next_hz": following,
        "ratio": ratio,
        "allowed_ratio": allowed,
        "within": _within(ratio, allowed),
    }


def required_dwell_s(
    response_time_s, floor_s=DWELL_FLOOR_S, factor=DWELL_RESPONSE_FACTOR
):
    """Dwell a step needs for the slowest response the unit can show."""
    response = _as_nonnegative_float(response_time_s, "response_time_s")
    floor = _as_positive_float(floor_s, "floor_s")
    multiple = _as_positive_float(factor, "factor")
    return max(floor, response * multiple)


def check_dwell(dwell_s, response_time_s):
    """Check the dwell held at one injection step."""
    dwell = _as_positive_float(dwell_s, "dwell_s")
    required = required_dwell_s(response_time_s)
    return {
        "quantity": "dwell",
        "dwell_s": dwell,
        "required_s": required,
        "within": _at_least(dwell, required),
    }


def check_level_ramp(levels_db, max_step_db=LEVEL_STEP_MAX_DB):
    """Check the ramp of levels applied at one injection step."""
    if isinstance(levels_db, (str, bytes)) or not hasattr(levels_db, "__iter__"):
        raise ValueError("levels_db must be an iterable of levels")
    levels = [_as_float(level, "level_db") for level in levels_db]
    if len(levels) < 2:
        raise ValueError("a ramp needs at least two levels, got %d" % len(levels))
    allowed = _as_positive_float(max_step_db, "max_step_db")
    rises = []
    for previous, following in zip(levels, levels[1:]):
        if following <= previous:
            raise ValueError(
                "a ramp must rise: %r does not follow %r" % (following, previous)
            )
        rises.append(following - previous)
    coarsest = max(rises)
    return {
        "quantity": "level-ramp",
        "levels_db": levels,
        "rises_db": rises,
        "coarsest_db": coarsest,
        "allowed_db": allowed,
        "top_db": levels[-1],
        "within": _within(coarsest, allowed),
    }


def susceptibility_threshold_db(observations):
    """Lowest applied level at which the unit showed a response.

    The record has to be monotonic: once the unit responds, every higher
    level responds too. A record that recovers at a higher level is a
    contradiction, not a threshold.
    """
    if isinstance(observations, (str, bytes)) or not hasattr(observations, "__iter__"):
        raise ValueError("observations must be an iterable of level and response pairs")
    pairs = []
    for entry in observations:
        if isinstance(entry, (str, bytes)) or not hasattr(entry, "__iter__"):
            raise ValueError("each observation must be a level and response pair")
        items = list(entry)
        if len(items) != 2:
            raise ValueError("each observation must carry exactly two values")
        pairs.append((_as_float(items[0], "level_db"), _as_flag(items[1], "responded")))
    if not pairs:
        raise ValueError("an observation record must carry at least one level")
    for previous, following in zip(pairs, pairs[1:]):
        if following[0] <= previous[0]:
            raise ValueError(
                "observations must rise in level: %r does not follow %r"
                % (following[0], previous[0])
            )
    responded = False
    threshold = None
    for level, response in pairs:
        if response and not responded:
            responded = True
            threshold = level
        elif responded and not response:
            raise ValueError(
                "the unit recovered at %r after responding at %r" % (level, threshold)
            )
    return threshold


def susceptibility_margin_db(
    threshold_db, required_level_db, margin_required_db=MARGIN_REQUIRED_DB
):
    """Margin a response threshold keeps above the required level."""
    threshold = _as_float(threshold_db, "threshold_db")
    required = _as_float(required_level_db, "required_level_db")
    wanted = _as_nonnegative_float(margin_required_db, "margin_required_db")
    margin = threshold - required
    return {
        "quantity": "susceptibility-margin",
        "threshold_db": threshold,
        "required_level_db": required,
        "margin_db": margin,
        "margin_required_db": wanted,
        "above_required": _at_least(margin, 0.0),
        "within": _at_least(margin, wanted),
    }


def evaluate_injection_step(step):
    """Evaluate one stepped injection point of the run."""
    if not isinstance(step, dict):
        raise ValueError("an injection step must be a mapping, got %r" % (step,))
    unknown = sorted(set(step) - set(_STEP_KEYS))
    if unknown:
        raise ValueError("unknown key(s) %s on an injection step" % (unknown,))
    for key in ("frequency_hz", "required_level_db", "levels_db", "dwell_s"):
        if key not in step:
            raise ValueError("an injection step must declare %s" % key)
    frequency = _as_positive_float(step["frequency_hz"], "frequency_hz")
    required_level = _as_float(step["required_level_db"], "required_level_db")
    ramp = check_level_ramp(step["levels_db"])
    dwell = check_dwell(step["dwell_s"], step.get("response_time_s", 0.0))
    drive_limited = _as_flag(step.get("drive_limited", False), "drive_limited")
    responded_at = step.get("responded_at_db")
    findings = []
    if not ramp["within"]:
        findings.append(
            _finding(
                "level-step-too-coarse",
                "%.6g Hz" % frequency,
                "rose %.4f dB at once against a %.4f dB allowance"
                % (ramp["coarsest_db"], ramp["allowed_db"]),
            )
        )
    if not dwell["within"]:
        findings.append(
            _finding(
                "dwell-too-short",
                "%.6g Hz" % frequency,
                "held %.4f s against the %.4f s the response time needs"
                % (dwell["dwell_s"], dwell["required_s"]),
            )
        )
    margin = None
    if responded_at is None:
        if not _at_least(ramp["top_db"], required_level) and not drive_limited:
            findings.append(
                _finding(
                    "required-level-not-reached",
                    "%.6g Hz" % frequency,
                    "the ramp stopped at %.4f dB below the required %.4f dB "
                    "with no drive limit declared"
                    % (ramp["top_db"], required_level),
                )
            )
        verdict = "drive-limited" if drive_limited else "conforming"
    else:
        threshold = _as_float(responded_at, "responded_at_db")
        if not _at_least(threshold, ramp["levels_db"][0]) or not _within(
            threshold, ramp["top_db"]
        ):
            raise ValueError(
                "the response level %r lies outside the ramp applied at %r Hz"
                % (responded_at, step["frequency_hz"])
            )
        margin = susceptibility_margin_db(threshold, required_level)
        verdict = "susceptible"
        findings.append(
            _finding(
                "unit-responded",
                "%.6g Hz" % frequency,
                "responded at %.4f dB, %.4f dB from the required %.4f dB"
                % (threshold, margin["margin_db"], required_level),
            )
        )
        if not margin["within"]:
            findings.append(
                _finding(
                    "margin-below-requirement",
                    "%.6g Hz" % frequency,
                    "leaves %.4f dB against a %.4f dB margin"
                    % (margin["margin_db"], margin["margin_required_db"]),
                )
            )
    if drive_limited:
        findings.append(
            _finding(
                "drive-limit-reached",
                "%.6g Hz" % frequency,
                "the ramp stopped at %.4f dB because the drive limit was reached"
                % ramp["top_db"],
            )
        )
    return {
        "frequency_hz": frequency,
        "required_level_db": required_level,
        "ramp": ramp,
        "dwell": dwell,
        "margin": margin,
        "drive_limited": drive_limited,
        "verdict": verdict,
        "findings": findings,
        "conforming": verdict == "conforming" and not findings,
    }


def run_injection_procedure(profile):
    """Walk a whole stepped injection run, warm up included.

    Returns the warm-up check, every evaluated step, the ladder coverage
    across the band, the findings raised and the verdict for the run.
    """
    if not isinstance(profile, dict):
        raise ValueError("the profile must be a mapping, got %r" % (profile,))
    unknown = sorted(set(profile) - set(_PROFILE_KEYS))
    if unknown:
        raise ValueError("unknown profile key(s) %s" % (unknown,))
    for key in ("warm_up_s", "start_hz", "stop_hz", "points_per_decade", "steps"):
        if key not in profile:
            raise ValueError("the profile must declare %s" % key)
    start = _as_positive_float(profile["start_hz"], "start_hz")
    stop = _as_positive_float(profile["stop_hz"], "stop_hz")
    count = _as_count(profile["points_per_decade"], "points_per_decade")
    if stop <= start:
        raise ValueError("the band does not rise")
    steps = profile["steps"]
    if isinstance(steps, (str, bytes)) or not hasattr(steps, "__iter__"):
        raise ValueError("steps must be an iterable of injection steps")
    evaluated = [evaluate_injection_step(step) for step in steps]
    if not evaluated:
        raise ValueError("a run must contain at least one injection step")
    findings = []
    warm_up = check_warm_up(
        profile["warm_up_s"], profile.get("stabilization_s", 0.0)
    )
    if not warm_up["within"]:
        findings.append(
            _finding(
                "warm-up-too-short",
                "run",
                "warmed for %.1f s against the %.1f s required"
                % (warm_up["elapsed_s"], warm_up["required_s"]),
            )
        )
    if count < POINTS_PER_DECADE_MIN:
        findings.append(
            _finding(
                "ladder-too-coarse",
                "run",
                "%d points per decade against a minimum of %d"
                % (count, POINTS_PER_DECADE_MIN),
            )
        )
    for record in evaluated:
        findings.extend(record["findings"])
    previous = None
    ratios = []
    for record in evaluated:
        current = record["frequency_hz"]
        if previous is not None:
            if current <= previous:
                findings.append(
                    _finding(
                        "ladder-not-ascending",
                        "%.6g Hz" % current,
                        "does not follow the previous %.6g Hz" % previous,
                    )
                )
            else:
                ratio = check_step_ratio(previous, current, count)
                ratios.append(ratio)
                if not ratio["within"]:
                    findings.append(
                        _finding(
                            "ladder-step-too-coarse",
                            "%.6g Hz" % current,
                            "stepped by a ratio of %.6f against an allowed %.6f"
                            % (ratio["ratio"], ratio["allowed_ratio"]),
                        )
                    )
        previous = current
    first = evaluated[0]["frequency_hz"]
    last = evaluated[-1]["frequency_hz"]
    if not _within(first, start):
        findings.append(
            _finding(
                "band-bottom-not-reached",
                "run",
                "the run starts at %.6g Hz above the %.6g Hz band bottom"
                % (first, start),
            )
        )
    if not _at_least(last, stop):
        findings.append(
            _finding(
                "band-top-not-reached",
                "run",
                "the run ends at %.6g Hz below the %.6g Hz band top" % (last, stop),
            )
        )
    susceptible = [record for record in evaluated if record["verdict"] == "susceptible"]
    limited = [record for record in evaluated if record["drive_limited"]]
    accepted = not findings
    return {
        "verdict": "run-accepted" if accepted else "run-not-accepted",
        "accepted": accepted,
        "warm_up": warm_up,
        "points_per_decade": count,
        "step_count": len(evaluated),
        "ratio_count": len(ratios),
        "susceptible_count": len(susceptible),
        "drive_limited_count": len(limited),
        "steps": evaluated,
        "findings": findings,
        "conforming_fraction": sum(1 for record in evaluated if record["conforming"])
        / float(len(evaluated)),
    }
