"""Monitoring and measurement of test activities at a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.8.1 (monitoring and measurement of the test
activities). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the test window and every declared acquisition channel: the ratio
   of its sample rate to the highest frequency of interest, the fraction of
   samples it drops, and whether its calibration is still inside validity.
2. Adjudicate every hold point of the test sequence: a hold point released
   without the witness it required, or without a named release authority, is a
   finding, and so is execution continued across a hold point still open.
3. Merge the surveillance intervals actually logged over the test window, clip
   them to the window, and report the covered fraction together with the gaps
   left unwatched.
4. Aggregate: the monitoring of the campaign is adequate only when every
   channel is fit, every hold point is properly adjudicated and the covered
   fraction reaches the required surveillance coverage.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "MIN_NYQUIST_RATIO",
    "RECOMMENDED_SAMPLE_RATIO",
    "MAX_DROPOUT_FRACTION",
    "validate_window",
    "acquisition_ratio",
    "assess_channel",
    "merge_intervals",
    "surveillance_coverage",
    "coverage_gaps",
    "assess_hold_point",
    "assess_monitoring",
]

# Coverage and ratio comparisons are quotients: a value meant to sit exactly on
# its limit can land a few ULP either side. Absorb the representation error
# here rather than relaxing the engineering limit.
COVERAGE_TOLERANCE = 1e-9

# Below this ratio the channel cannot represent the frequency of interest at
# all; below the recommended ratio it represents it but cannot resolve a peak.
MIN_NYQUIST_RATIO = 2.0
RECOMMENDED_SAMPLE_RATIO = 5.0

# Sample loss above this fraction makes a measured extreme unsupportable.
MAX_DROPOUT_FRACTION = 0.02


def _real(label, value, allow_zero=False):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0 or (out == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def validate_window(start_h, end_h):
    """Return the validated (start, end) test window in hours from test start."""
    if not isinstance(start_h, (int, float)) or isinstance(start_h, bool):
        raise ValueError("start_h must be a real number")
    if not isinstance(end_h, (int, float)) or isinstance(end_h, bool):
        raise ValueError("end_h must be a real number")
    start = float(start_h)
    end = float(end_h)
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("test window bounds must be finite")
    if start < 0.0:
        raise ValueError("start_h must not be negative, got %g" % start)
    if end <= start:
        raise ValueError("end_h %g must exceed start_h %g" % (end, start))
    return (start, end)


def acquisition_ratio(sample_rate_hz, max_frequency_hz):
    """Return the oversampling ratio of a channel against its frequency of interest."""
    rate = _real("sample_rate_hz", sample_rate_hz)
    freq = _real("max_frequency_hz", max_frequency_hz)
    return rate / freq


def assess_channel(channel):
    """Assess one acquisition channel and return its monitoring record."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping")
    for key in ("name", "sample_rate_hz", "max_frequency_hz"):
        if key not in channel:
            raise ValueError("channel missing required key '%s'" % key)
    name = channel["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("channel name must be a non-empty string")
    ratio = acquisition_ratio(channel["sample_rate_hz"], channel["max_frequency_hz"])
    dropout = channel.get("dropout_fraction", 0.0)
    if not isinstance(dropout, (int, float)) or isinstance(dropout, bool):
        raise ValueError("dropout_fraction must be a real number")
    dropout = float(dropout)
    if not math.isfinite(dropout) or dropout < 0.0 or dropout > 1.0:
        raise ValueError("dropout_fraction must lie in [0, 1], got %r" % (dropout,))
    days_left = channel.get("calibration_days_remaining", 0)
    if not isinstance(days_left, int) or isinstance(days_left, bool):
        raise ValueError("calibration_days_remaining must be an integer")
    findings = []
    if ratio < MIN_NYQUIST_RATIO and not math.isclose(
        ratio, MIN_NYQUIST_RATIO, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "%s samples at %.3f times its frequency of interest, under the %.1f needed"
            % (name, ratio, MIN_NYQUIST_RATIO)
        )
    elif ratio < RECOMMENDED_SAMPLE_RATIO and not math.isclose(
        ratio, RECOMMENDED_SAMPLE_RATIO, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "%s samples at %.3f times its frequency of interest; a peak cannot be "
            "resolved below %.1f" % (name, ratio, RECOMMENDED_SAMPLE_RATIO)
        )
    if dropout > MAX_DROPOUT_FRACTION and not math.isclose(
        dropout, MAX_DROPOUT_FRACTION, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "%s dropped %.3f of its samples, above the %.3f limit"
            % (name, dropout, MAX_DROPOUT_FRACTION)
        )
    if days_left <= 0:
        findings.append("%s is outside calibration validity" % name)
    return {
        "name": name,
        "ratio": ratio,
        "dropout_fraction": dropout,
        "calibration_days_remaining": days_left,
        "fit": not findings,
        "findings": findings,
    }


def merge_intervals(intervals):
    """Return the union of (start, end) intervals as a sorted disjoint list."""
    if not isinstance(intervals, (list, tuple)):
        raise ValueError("intervals must be a sequence of (start, end) pairs")
    cleaned = []
    for i, item in enumerate(intervals):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("intervals[%d] must be a (start, end) pair" % i)
        start, end = item
        for label, value in (("start", start), ("end", end)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("intervals[%d] %s must be a real number" % (i, label))
            if not math.isfinite(float(value)):
                raise ValueError("intervals[%d] %s must be finite" % (i, label))
        start = float(start)
        end = float(end)
        if end <= start:
            raise ValueError(
                "intervals[%d] has end %g not after start %g" % (i, end, start)
            )
        cleaned.append((start, end))
    cleaned.sort()
    merged = []
    for start, end in cleaned:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [tuple(pair) for pair in merged]


def surveillance_coverage(intervals, window):
    """Return the fraction of the test window covered by surveillance."""
    start, end = validate_window(window[0], window[1])
    merged = merge_intervals(intervals)
    for lo, hi in merged:
        if hi <= start or lo >= end:
            raise ValueError(
                "surveillance interval (%g, %g) lies outside the test window [%g, %g]"
                % (lo, hi, start, end)
            )
    covered = 0.0
    for lo, hi in merged:
        covered += min(hi, end) - max(lo, start)
    return covered / (end - start)


def coverage_gaps(intervals, window):
    """Return the unwatched (start, end) stretches of the test window."""
    start, end = validate_window(window[0], window[1])
    merged = merge_intervals(intervals)
    gaps = []
    cursor = start
    for lo, hi in merged:
        lo = max(lo, start)
        hi = min(hi, end)
        if hi <= cursor:
            continue
        if lo > cursor:
            gaps.append((cursor, lo))
        cursor = hi
    if cursor < end:
        gaps.append((cursor, end))
    return gaps


def assess_hold_point(hold_point):
    """Adjudicate one hold point of the test sequence."""
    if not isinstance(hold_point, dict):
        raise ValueError("hold_point must be a mapping")
    for key in ("id", "time_h", "released"):
        if key not in hold_point:
            raise ValueError("hold_point missing required key '%s'" % key)
    hp_id = hold_point["id"]
    if not isinstance(hp_id, str) or not hp_id.strip():
        raise ValueError("hold point id must be a non-empty string")
    time_h = hold_point["time_h"]
    if not isinstance(time_h, (int, float)) or isinstance(time_h, bool):
        raise ValueError("hold point time_h must be a real number")
    if not math.isfinite(float(time_h)):
        raise ValueError("hold point time_h must be finite")
    released = hold_point["released"]
    if not isinstance(released, bool):
        raise ValueError("hold point 'released' must be a boolean")
    witness_required = hold_point.get("witness_required", False)
    if not isinstance(witness_required, bool):
        raise ValueError("'witness_required' must be a boolean")
    witness_present = hold_point.get("witness_present", False)
    if not isinstance(witness_present, bool):
        raise ValueError("'witness_present' must be a boolean")
    authority = hold_point.get("release_authority")
    continued = hold_point.get("execution_continued", False)
    if not isinstance(continued, bool):
        raise ValueError("'execution_continued' must be a boolean")
    findings = []
    if released and witness_required and not witness_present:
        findings.append("%s released without the witness it required" % hp_id)
    if released and not (isinstance(authority, str) and authority.strip()):
        findings.append("%s released with no named release authority" % hp_id)
    if continued and not released:
        findings.append("%s still open while execution continued past it" % hp_id)
    return {
        "id": hp_id,
        "time_h": float(time_h),
        "released": released,
        "witness_required": witness_required,
        "witness_present": witness_present,
        "release_authority": authority if isinstance(authority, str) else None,
        "adjudicated": not findings,
        "findings": findings,
    }


def assess_monitoring(spec):
    """Run the full clause 5.8.1 monitoring assessment for one test campaign.

    spec keys: window (pair, hours), channels, hold_points, surveillance
    (intervals in hours), optional required_coverage (default 0.9).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("window", "channels", "hold_points", "surveillance"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    window = spec["window"]
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("spec['window'] must be a (start_h, end_h) pair")
    channels = spec["channels"]
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("spec['channels'] must be a non-empty sequence")
    hold_points = spec["hold_points"]
    if not isinstance(hold_points, (list, tuple)):
        raise ValueError("spec['hold_points'] must be a sequence")
    required = spec.get("required_coverage", 0.9)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_coverage must lie in [0, 1], got %r" % (required,))
    channel_records = [assess_channel(c) for c in channels]
    hold_records = [assess_hold_point(h) for h in hold_points]
    coverage = surveillance_coverage(spec["surveillance"], window)
    gaps = coverage_gaps(spec["surveillance"], window)
    findings = []
    for record in channel_records:
        findings.extend(record["findings"])
    for record in hold_records:
        findings.extend(record["findings"])
    coverage_met = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if not coverage_met:
        findings.append(
            "surveillance covered %.4f of the test window, below the required %.4f"
            % (coverage, required)
        )
    return {
        "channels": channel_records,
        "hold_points": hold_records,
        "coverage": coverage,
        "required_coverage": required,
        "gaps": gaps,
        "findings": findings,
        "adequate": not findings,
    }
