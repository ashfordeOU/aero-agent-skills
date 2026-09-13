"""In-situ continuity monitoring of a vacuum thermal-cycling run.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.11.2 (which components of the article
are watched for electrical continuity throughout the vacuum cycling run).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Separate the declared items into the ones that carry a current path, and so
   owe a continuity channel, and the ones no continuity monitor can watch at
   all. Both groups are reported: the second is where a false sense of
   coverage comes from.
2. Assign each item that owes monitoring to its own monitor channel, refuse a
   channel that two items claim, and compare the channel demand with the
   channels the monitor actually has.
3. Size the sampling interval from the shortest discontinuity that has to be
   caught, and report the shortest event the planned interval can actually
   resolve.
4. Account for the time the monitor was not watching: a late start, an early
   stop and every logged gap, clipped to the run window and merged so
   overlapping gaps are not counted twice.
5. Aggregate the unmonitored items, the channel shortfall, the sampling
   shortfall and the monitoring gaps into one plan verdict.
"""

import math

__all__ = [
    "CONDUCTING_ITEM_CLASSES",
    "ITEM_CLASSES",
    "LIMIT_TOLERANCE",
    "NON_CONDUCTING_ITEM_CLASSES",
    "assess_continuity_monitoring",
    "at_or_above",
    "at_or_below",
    "build_channel_assignment",
    "categorize_monitoring_scope",
    "evaluate_monitoring_window",
    "evaluate_sampling",
    "merge_gaps",
    "required_sample_interval_s",
]

# Durations and intervals are built from differences of logged times, so a plan
# that lands exactly on a bound can sit a few ULPs on the wrong side. Absorb
# that representation error here rather than moving any engineering bound.
LIMIT_TOLERANCE = 1e-9

# Items carrying a current path: an interruption in one of them is visible to a
# continuity monitor, so each of them owes a channel.
CONDUCTING_ITEM_CLASSES = frozenset({
    "solar-cell-string",
    "interconnector",
    "bus-bar-joint",
    "bypass-diode",
    "harness",
    "connector-interface",
    "grounding-strap",
})

# Items with no current path. They are cycled and they are inspected, but a
# continuity monitor says nothing about them, and pretending otherwise is how a
# run reports coverage it never had.
NON_CONDUCTING_ITEM_CLASSES = frozenset({
    "coverglass",
    "coverglass-adhesive",
    "substrate-bondline",
    "thermal-blanket-attachment",
    "structural-hinge",
})

ITEM_CLASSES = CONDUCTING_ITEM_CLASSES | NON_CONDUCTING_ITEM_CLASSES


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _count(value, label):
    """Return value as a non-negative whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _identifier(value, label):
    """Return a non-empty stripped identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def at_or_below(value, limit):
    """Return True when value respects an upper bound, equality included."""
    v = _real(value, "value")
    lim = _real(limit, "limit")
    if v < lim:
        return True
    return math.isclose(v, lim, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def at_or_above(value, floor):
    """Return True when value respects a lower bound, equality included."""
    v = _real(value, "value")
    low = _real(floor, "floor")
    if v > low:
        return True
    return math.isclose(v, low, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def categorize_monitoring_scope(items):
    """Return the declared items grouped by whether continuity can watch them."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item records")
    seen = set()
    requires = []
    not_monitorable = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        for key in ("item_id", "item_class"):
            if key not in item:
                raise ValueError("items[%d] missing required key '%s'" % (index, key))
        item_id = _identifier(item["item_id"], "items[%d] item_id" % index)
        if item_id in seen:
            raise ValueError("duplicate item_id %r in items" % item_id)
        seen.add(item_id)
        item_class = item["item_class"]
        if item_class not in ITEM_CLASSES:
            raise ValueError(
                "items[%d] item_class %r is not a recognised article item; declare "
                "it or correct it rather than dropping it" % (index, item_class)
            )
        channel = item.get("monitor_channel")
        if channel is not None:
            channel = _identifier(channel, "items[%d] monitor_channel" % index)
        record = {
            "item_id": item_id,
            "item_class": item_class,
            "monitor_channel": channel,
        }
        if item_class in CONDUCTING_ITEM_CLASSES:
            requires.append(record)
        else:
            not_monitorable.append(record)
    return {
        "requires_monitoring": requires,
        "not_monitorable": not_monitorable,
        "declared_items": len(requires) + len(not_monitorable),
    }


def build_channel_assignment(scope, available_channels):
    """Return the channel plan for the items that owe continuity monitoring."""
    if not isinstance(scope, dict) or "requires_monitoring" not in scope:
        raise ValueError("scope must be the mapping returned by categorize_monitoring_scope")
    available = _count(available_channels, "available_channels")
    findings = []
    monitored = []
    unmonitored = []
    used = {}
    for record in scope["requires_monitoring"]:
        channel = record["monitor_channel"]
        if channel is None:
            unmonitored.append(record["item_id"])
            continue
        if channel in used:
            raise ValueError(
                "monitor channel %r is claimed by both %s and %s; one channel "
                "watches one item" % (channel, used[channel], record["item_id"])
            )
        used[channel] = record["item_id"]
        monitored.append({"item_id": record["item_id"], "monitor_channel": channel})
    for record in scope["not_monitorable"]:
        if record["monitor_channel"] is not None:
            findings.append(
                "channel %s is assigned to %s, which carries no current path and "
                "cannot be watched for continuity"
                % (record["monitor_channel"], record["item_id"])
            )
    required = len(scope["requires_monitoring"])
    if unmonitored:
        findings.append(
            "%d item(s) carrying a current path have no monitor channel: %s"
            % (len(unmonitored), ", ".join(unmonitored))
        )
    if required > available:
        findings.append(
            "the article needs %d continuity channels and the monitor has %d"
            % (required, available)
        )
    coverage = 1.0 if required == 0 else len(monitored) / float(required)
    return {
        "items_requiring_monitoring": required,
        "monitored_items": monitored,
        "unmonitored_items": unmonitored,
        "available_channels": available,
        "channels_used": len(monitored),
        "monitoring_coverage_fraction": coverage,
        "findings": findings,
        "complete": not findings,
    }


def required_sample_interval_s(min_event_duration_s, samples_per_event):
    """Return the sampling interval needed to resolve the shortest event."""
    duration = _positive(min_event_duration_s, "min_event_duration_s")
    samples = _count(samples_per_event, "samples_per_event")
    if samples < 1:
        raise ValueError("samples_per_event must be at least 1, got %d" % samples)
    return duration / float(samples)


def evaluate_sampling(monitor):
    """Return the sampling accounting of the continuity monitor."""
    if not isinstance(monitor, dict):
        raise ValueError("monitor must be a mapping")
    for key in ("sample_interval_s", "min_event_duration_s"):
        if key not in monitor:
            raise ValueError("monitor missing required key '%s'" % key)
    planned = _positive(monitor["sample_interval_s"], "sample_interval_s")
    duration = _positive(monitor["min_event_duration_s"], "min_event_duration_s")
    samples = monitor.get("samples_per_event", 2)
    required = required_sample_interval_s(duration, samples)
    adequate = at_or_below(planned, required)
    findings = []
    if not adequate:
        findings.append(
            "a %g s sampling interval cannot resolve a %g s discontinuity with "
            "%s sample(s) inside it; %g s or shorter is needed"
            % (planned, duration, samples, required)
        )
    return {
        "sample_interval_s": planned,
        "sample_rate_hz": 1.0 / planned,
        "required_sample_interval_s": required,
        "shortest_resolvable_event_s": planned * float(samples),
        "adequate": adequate,
        "findings": findings,
    }


def merge_gaps(gaps, run_start_s, run_end_s):
    """Return the logged monitoring gaps clipped to the run and merged."""
    start = _real(run_start_s, "run_start_s")
    end = _real(run_end_s, "run_end_s")
    if end <= start:
        raise ValueError("run_end_s %g is not after run_start_s %g" % (end, start))
    if gaps is None:
        gaps = []
    if not isinstance(gaps, (list, tuple)):
        raise ValueError("gaps must be a sequence of gap records")
    clipped = []
    for index, gap in enumerate(gaps):
        if not isinstance(gap, dict):
            raise ValueError("gaps[%d] must be a mapping" % index)
        for key in ("start_s", "end_s"):
            if key not in gap:
                raise ValueError("gaps[%d] missing required key '%s'" % (index, key))
        gap_start = _real(gap["start_s"], "gaps[%d] start_s" % index)
        gap_end = _real(gap["end_s"], "gaps[%d] end_s" % index)
        if gap_end <= gap_start:
            raise ValueError(
                "gaps[%d] ends at %g, which is not after its start %g"
                % (index, gap_end, gap_start)
            )
        lo = max(gap_start, start)
        hi = min(gap_end, end)
        if hi > lo:
            clipped.append((lo, hi))
    clipped.sort()
    merged = []
    for lo, hi in clipped:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return [{"start_s": lo, "end_s": hi} for lo, hi in merged]


def evaluate_monitoring_window(run, monitor):
    """Return how much of the run the continuity monitor was actually watching."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    if not isinstance(monitor, dict):
        raise ValueError("monitor must be a mapping")
    for key in ("start_s", "end_s"):
        if key not in run:
            raise ValueError("run missing required key '%s'" % key)
    start = _real(run["start_s"], "run start_s")
    end = _real(run["end_s"], "run end_s")
    if end <= start:
        raise ValueError("run end_s %g is not after start_s %g" % (end, start))
    monitor_start = _real(monitor.get("start_s", start), "monitor start_s")
    monitor_end = _real(monitor.get("end_s", end), "monitor end_s")
    if monitor_end <= monitor_start:
        raise ValueError(
            "monitor end_s %g is not after its start_s %g" % (monitor_end, monitor_start)
        )
    edges = list(monitor.get("gaps", []) or [])
    if monitor_start > start:
        edges = edges + [{"start_s": start, "end_s": monitor_start}]
    if monitor_end < end:
        edges = edges + [{"start_s": monitor_end, "end_s": end}]
    merged = merge_gaps(edges, start, end)
    run_duration = end - start
    unmonitored = sum(gap["end_s"] - gap["start_s"] for gap in merged)
    longest = max((gap["end_s"] - gap["start_s"] for gap in merged), default=0.0)
    monitored = run_duration - unmonitored
    max_unmonitored = _non_negative(
        monitor.get("max_unmonitored_time_s", 0.0), "max_unmonitored_time_s"
    )
    max_single_gap = _non_negative(
        monitor.get("max_single_gap_s", 0.0), "max_single_gap_s"
    )
    findings = []
    if not at_or_below(unmonitored, max_unmonitored):
        findings.append(
            "the monitor was not watching for %g s of the run, past the %g s allowed"
            % (unmonitored, max_unmonitored)
        )
    if not at_or_below(longest, max_single_gap):
        findings.append(
            "the longest monitoring gap is %g s, past the %g s allowed for a single gap"
            % (longest, max_single_gap)
        )
    return {
        "run_duration_s": run_duration,
        "monitored_time_s": monitored,
        "unmonitored_time_s": unmonitored,
        "longest_gap_s": longest,
        "gap_count": len(merged),
        "gaps": merged,
        "monitored_fraction": monitored / run_duration,
        "continuous": not findings,
        "findings": findings,
    }


def assess_continuity_monitoring(spec):
    """Run the full clause 5.5.3.11.2 continuity-monitoring assessment.

    spec keys: items, available_channels, monitor (sample_interval_s,
    min_event_duration_s, optional samples_per_event, start_s, end_s, gaps,
    max_unmonitored_time_s, max_single_gap_s) and run (start_s, end_s).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "available_channels", "monitor", "run"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    scope = categorize_monitoring_scope(spec["items"])
    assignment = build_channel_assignment(scope, spec["available_channels"])
    sampling = evaluate_sampling(spec["monitor"])
    window = evaluate_monitoring_window(spec["run"], spec["monitor"])
    findings = list(assignment["findings"]) + list(sampling["findings"]) + list(window["findings"])
    return {
        "scope": scope,
        "assignment": assignment,
        "sampling": sampling,
        "window": window,
        "findings": findings,
        "plan_acceptable": not findings,
    }
