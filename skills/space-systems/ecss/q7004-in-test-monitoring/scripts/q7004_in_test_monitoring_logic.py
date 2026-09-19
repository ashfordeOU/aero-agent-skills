"""In-test monitoring of temperatures, pressures and functional parameters.

Anchor: ECSS-Q-ST-70-04C, the monitoring clause requiring that the quantities
the test is defined by are recorded continuously while the item is under test,
so that a departure is visible in the record rather than inferred afterwards.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each monitored channel: identity, role, limits, required sampling
   interval, and a strictly time-ordered sample record.
2. Check that the three monitored roles -- temperature, pressure and
   functional parameter -- are all covered by at least one channel.
3. Measure each channel's sampling against the interval the plan required and
   report the intervals that ran long enough to count as a recording gap.
4. Measure how much of the planned test window the channel actually covered.
5. Find the excursions outside the channel's limits, merge consecutive
   out-of-limit samples into one event, and time each event.
6. Combine role coverage, gap count, coverage ratio and excursions into one
   monitoring verdict with the findings that produced it.
"""

import math

__all__ = [
    "REQUIRED_ROLES",
    "COMPARISON_TOLERANCE",
    "DEFAULT_GAP_FACTOR",
    "validate_samples",
    "validate_channel",
    "sampling_intervals",
    "recording_gaps",
    "coverage_ratio",
    "limit_excursions",
    "assess_channel",
    "role_coverage",
    "assess_monitoring",
]

# The three families of quantity a thermal test has to watch while the item is
# under test. Each has to be covered by at least one channel.
REQUIRED_ROLES = ("temperature", "pressure", "functional")

# Intervals, ratios and limit edges are floats; a value sitting on a limit is
# compared within this tolerance rather than by relaxing the limit.
COMPARISON_TOLERANCE = 1e-9

# An interval this many times the required one counts as a recording gap.
DEFAULT_GAP_FACTOR = 2.0


def _as_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_samples(samples):
    """Return the validated (time_s, value) record of one channel."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of (time_s, value) pairs")
    if len(samples) < 2:
        raise ValueError("a monitored channel needs at least two samples")
    record = []
    for i, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("samples[%d] must be a (time_s, value) pair" % i)
        t = _as_float(item[0], "samples[%d] time_s" % i)
        value = _as_float(item[1], "samples[%d] value" % i)
        if t < 0.0:
            raise ValueError("samples[%d] time_s must be non-negative" % i)
        record.append((t, value))
    for i in range(1, len(record)):
        if record[i][0] <= record[i - 1][0]:
            raise ValueError("channel sample times must strictly increase (index %d)" % i)
    return record


def validate_channel(channel):
    """Return the validated description of one monitored channel."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping")
    for key in ("id", "role", "required_interval_s", "lower_limit", "upper_limit", "samples"):
        if key not in channel:
            raise ValueError("channel missing required key '%s'" % key)
    identity = channel["id"]
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("channel id must be a non-empty string")
    role = channel["role"]
    if role not in REQUIRED_ROLES:
        raise ValueError(
            "channel %s has role %r, expected one of %s"
            % (identity, role, ", ".join(REQUIRED_ROLES))
        )
    lower = _as_float(channel["lower_limit"], "lower_limit")
    upper = _as_float(channel["upper_limit"], "upper_limit")
    if lower >= upper:
        raise ValueError(
            "channel %s lower_limit %g must be below upper_limit %g" % (identity, lower, upper)
        )
    return {
        "id": identity.strip(),
        "role": role,
        "required_interval_s": _positive(channel["required_interval_s"], "required_interval_s"),
        "lower_limit": lower,
        "upper_limit": upper,
        "samples": validate_samples(channel["samples"]),
    }


def sampling_intervals(record):
    """Return the successive sampling intervals of a validated record."""
    if not isinstance(record, (list, tuple)) or len(record) < 2:
        raise ValueError("record must be a validated sequence of at least two samples")
    return [record[i][0] - record[i - 1][0] for i in range(1, len(record))]


def recording_gaps(record, required_interval_s, gap_factor=DEFAULT_GAP_FACTOR):
    """Return the intervals long enough to count as a break in the recording."""
    required = _positive(required_interval_s, "required_interval_s")
    factor = _as_float(gap_factor, "gap_factor")
    if factor < 1.0:
        raise ValueError("gap_factor must be at least 1.0, got %g" % factor)
    threshold = required * factor
    intervals = sampling_intervals(record)
    gaps = []
    for index, span in enumerate(intervals):
        if span > threshold + COMPARISON_TOLERANCE:
            gaps.append(
                {
                    "index": index + 1,
                    "start_s": record[index][0],
                    "end_s": record[index + 1][0],
                    "span_s": span,
                }
            )
    return {
        "intervals": intervals,
        "threshold_s": threshold,
        "longest_interval_s": max(intervals),
        "gaps": gaps,
    }


def coverage_ratio(record, window_start_s, window_end_s):
    """Return the fraction of the planned test window the record spans."""
    if not isinstance(record, (list, tuple)) or len(record) < 2:
        raise ValueError("record must be a validated sequence of at least two samples")
    start = _as_float(window_start_s, "window_start_s")
    end = _as_float(window_end_s, "window_end_s")
    if start >= end:
        raise ValueError("window_start_s %g must be below window_end_s %g" % (start, end))
    first = max(record[0][0], start)
    last = min(record[-1][0], end)
    if last <= first:
        return 0.0
    return (last - first) / (end - start)


def limit_excursions(record, lower_limit, upper_limit):
    """Return the merged runs of samples outside the channel's limits."""
    if not isinstance(record, (list, tuple)) or len(record) < 2:
        raise ValueError("record must be a validated sequence of at least two samples")
    lower = _as_float(lower_limit, "lower_limit")
    upper = _as_float(upper_limit, "upper_limit")
    if lower >= upper:
        raise ValueError("lower_limit %g must be below upper_limit %g" % (lower, upper))
    events = []
    current = None
    for t, value in record:
        below = value < lower - COMPARISON_TOLERANCE
        above = value > upper + COMPARISON_TOLERANCE
        if not below and not above:
            if current is not None:
                events.append(current)
                current = None
            continue
        side = "below" if below else "above"
        extreme = value
        if current is None or current["side"] != side:
            if current is not None:
                events.append(current)
            current = {
                "side": side,
                "start_s": t,
                "end_s": t,
                "duration_s": 0.0,
                "extreme_value": extreme,
            }
        else:
            current["end_s"] = t
            current["duration_s"] = t - current["start_s"]
            if side == "below":
                current["extreme_value"] = min(current["extreme_value"], extreme)
            else:
                current["extreme_value"] = max(current["extreme_value"], extreme)
    if current is not None:
        events.append(current)
    return events


def assess_channel(channel, window_start_s, window_end_s,
                   minimum_coverage=0.99, gap_factor=DEFAULT_GAP_FACTOR):
    """Judge one monitored channel over the planned test window."""
    view = validate_channel(channel)
    minimum = _as_float(minimum_coverage, "minimum_coverage")
    if minimum <= 0.0 or minimum > 1.0:
        raise ValueError("minimum_coverage must lie in (0, 1], got %g" % minimum)
    gaps = recording_gaps(view["samples"], view["required_interval_s"], gap_factor)
    coverage = coverage_ratio(view["samples"], window_start_s, window_end_s)
    excursions = limit_excursions(view["samples"], view["lower_limit"], view["upper_limit"])
    covered = coverage > minimum or math.isclose(
        coverage, minimum, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE
    )
    findings = []
    for gap in gaps["gaps"]:
        findings.append(
            "channel %s has no record between %.0f s and %.0f s"
            % (view["id"], gap["start_s"], gap["end_s"])
        )
    if not covered:
        findings.append(
            "channel %s covers %.4f of the test window, below the required %.4f"
            % (view["id"], coverage, minimum)
        )
    for event in excursions:
        findings.append(
            "channel %s ran %s its limit from %.0f s for %.0f s, reaching %g"
            % (view["id"], event["side"], event["start_s"], event["duration_s"],
               event["extreme_value"])
        )
    return {
        "id": view["id"],
        "role": view["role"],
        "gaps": gaps["gaps"],
        "longest_interval_s": gaps["longest_interval_s"],
        "coverage_ratio": coverage,
        "coverage_met": covered,
        "excursions": excursions,
        "acceptable": not findings,
        "findings": findings,
    }


def role_coverage(channels):
    """Return which monitored roles the channel set covers and which it misses."""
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("at least one monitored channel is required")
    seen = set()
    for channel in channels:
        seen.add(validate_channel(channel)["role"])
    missing = [role for role in REQUIRED_ROLES if role not in seen]
    return {"covered": sorted(seen), "missing": missing, "complete": not missing}


def assess_monitoring(spec):
    """Judge a whole in-test monitoring record.

    spec keys: channels (sequence), window_start_s, window_end_s, and
    optionally minimum_coverage and gap_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("channels", "window_start_s", "window_end_s"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    roles = role_coverage(spec["channels"])
    results = [
        assess_channel(
            channel,
            spec["window_start_s"],
            spec["window_end_s"],
            spec.get("minimum_coverage", 0.99),
            spec.get("gap_factor", DEFAULT_GAP_FACTOR),
        )
        for channel in spec["channels"]
    ]
    findings = []
    for role in roles["missing"]:
        findings.append("no channel monitors the %s role" % role)
    for result in results:
        findings.extend(result["findings"])
    return {
        "roles": roles,
        "channels": results,
        "excursion_count": sum(len(r["excursions"]) for r in results),
        "gap_count": sum(len(r["gaps"]) for r in results),
        "adequate": roles["complete"] and all(r["acceptable"] for r in results),
        "findings": findings,
    }
