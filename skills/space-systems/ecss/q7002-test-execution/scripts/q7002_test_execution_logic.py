"""Execution of a thermal-vacuum outgassing exposure from its run log.

Anchor: ECSS-Q-ST-70-02C, procedure clause -- the exposure is carried out by
pumping down, heating the specimen bar, holding the collectors at their
controlled temperature and keeping all of it steady for the soak. Paraphrased
into an implementable procedure; no standard text is reproduced.

What this module decides
------------------------
How much of the soak the run actually delivered, and what has to be reported
about the way it was delivered.

1. Ordering. The phases happen in one order: pump-down, heating, stabilisation,
   soak start, soak end, cool-down. A log whose stamps do not increase in that
   order describes a run nobody can reconstruct.
2. Qualified time. Soak time only accrues while the specimen temperature, the
   collector temperature and the chamber pressure are all inside their limits
   at the same moment. An interval between two samples is credited only when
   both of its ends qualify, so a dropout is never credited to the soak.
3. Excursions. A stretch of non-qualifying samples is one event with a start,
   an end and the reasons it failed, not one finding per sample. The longest
   excursion is what a reviewer asks about first.
4. Verdict. The soak is delivered when the qualified time reaches the required
   duration; wall-clock time between soak start and soak end is not the same
   quantity and is reported beside it, never instead of it.
"""

import math

__all__ = [
    "PHASE_ORDER",
    "DEFAULT_LIMITS",
    "validate_timeline",
    "sample_failures",
    "sample_qualifies",
    "qualified_dwell_h",
    "excursions",
    "longest_excursion_h",
    "phase_order_findings",
    "assess_test_execution",
]

# The phases of an exposure, in the only order they can occur in.
PHASE_ORDER = (
    "pump_down_start",
    "heating_start",
    "stabilised",
    "soak_start",
    "soak_end",
    "cooldown_complete",
)

# Limits every sample of the soak has to satisfy at the same moment.
DEFAULT_LIMITS = {
    "specimen_temperature_band_c": (124.0, 126.0),
    "collector_temperature_band_c": (24.0, 26.0),
    "pressure_ceiling_pa": 1.0e-4,
}

# Band comparisons are inclusive; absorb representation error at the edge
# rather than widening the limits themselves.
BAND_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _validate_band(band, label):
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _as_finite_float(band[0], "%s low" % label)
    high = _as_finite_float(band[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def _resolve_limits(limits):
    settings = dict(DEFAULT_LIMITS)
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits must be a mapping")
        for key in limits:
            if key not in DEFAULT_LIMITS:
                raise ValueError("'%s' is not an exposure limit" % key)
        settings.update(limits)
    return {
        "specimen_temperature_band_c": _validate_band(
            settings["specimen_temperature_band_c"], "specimen temperature band"
        ),
        "collector_temperature_band_c": _validate_band(
            settings["collector_temperature_band_c"], "collector temperature band"
        ),
        "pressure_ceiling_pa": _as_positive_float(
            settings["pressure_ceiling_pa"], "pressure_ceiling_pa"
        ),
    }


def validate_timeline(samples):
    """Return the run-log samples as validated records in strict time order."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("a run log needs at least two samples")
    records = []
    for i, item in enumerate(samples):
        if not isinstance(item, dict):
            raise ValueError("sample %d must be a mapping" % i)
        for key in ("time_h", "specimen_temperature_c", "collector_temperature_c",
                    "pressure_pa"):
            if key not in item:
                raise ValueError("sample %d is missing '%s'" % (i, key))
        records.append(
            {
                "time_h": _as_finite_float(item["time_h"], "sample %d time_h" % i),
                "specimen_temperature_c": _as_finite_float(
                    item["specimen_temperature_c"], "sample %d specimen_temperature_c" % i
                ),
                "collector_temperature_c": _as_finite_float(
                    item["collector_temperature_c"],
                    "sample %d collector_temperature_c" % i,
                ),
                "pressure_pa": _as_positive_float(
                    item["pressure_pa"], "sample %d pressure_pa" % i
                ),
            }
        )
    for i in range(1, len(records)):
        if records[i]["time_h"] <= records[i - 1]["time_h"]:
            raise ValueError(
                "run log time stamps must strictly increase (sample %d at %g h follows "
                "%g h)" % (i, records[i]["time_h"], records[i - 1]["time_h"])
            )
    return records


def sample_failures(sample, limits=None):
    """Return the reasons one sample does not qualify as soak time."""
    settings = _resolve_limits(limits)
    reasons = []
    low, high = settings["specimen_temperature_band_c"]
    value = _as_finite_float(sample["specimen_temperature_c"], "specimen_temperature_c")
    if value < low - BAND_TOLERANCE or value > high + BAND_TOLERANCE:
        reasons.append("specimen-temperature")
    low, high = settings["collector_temperature_band_c"]
    value = _as_finite_float(sample["collector_temperature_c"], "collector_temperature_c")
    if value < low - BAND_TOLERANCE or value > high + BAND_TOLERANCE:
        reasons.append("collector-temperature")
    ceiling = settings["pressure_ceiling_pa"]
    value = _as_positive_float(sample["pressure_pa"], "pressure_pa")
    if value > ceiling * (1.0 + BAND_TOLERANCE):
        reasons.append("chamber-pressure")
    return reasons


def sample_qualifies(sample, limits=None):
    """Return True when a sample satisfies every exposure limit at once."""
    return not sample_failures(sample, limits)


def qualified_dwell_h(samples, limits=None):
    """Return the soak time credited by the run log, in hours.

    An interval is credited only when the samples at both of its ends qualify,
    so a dropout costs the intervals on either side of it rather than being
    interpolated away.
    """
    records = validate_timeline(samples)
    settings = _resolve_limits(limits)
    flags = [sample_qualifies(record, settings) for record in records]
    total = 0.0
    for i in range(1, len(records)):
        if flags[i - 1] and flags[i]:
            total += records[i]["time_h"] - records[i - 1]["time_h"]
    return total


def excursions(samples, limits=None):
    """Return the stretches of the run log that do not qualify as soak time."""
    records = validate_timeline(samples)
    settings = _resolve_limits(limits)
    events = []
    current = None
    for record in records:
        reasons = sample_failures(record, settings)
        if reasons:
            if current is None:
                current = {
                    "start_h": record["time_h"],
                    "end_h": record["time_h"],
                    "causes": list(reasons),
                }
            else:
                current["end_h"] = record["time_h"]
                for reason in reasons:
                    if reason not in current["causes"]:
                        current["causes"].append(reason)
        elif current is not None:
            current["duration_h"] = current["end_h"] - current["start_h"]
            current["causes"] = sorted(current["causes"])
            events.append(current)
            current = None
    if current is not None:
        current["duration_h"] = current["end_h"] - current["start_h"]
        current["causes"] = sorted(current["causes"])
        events.append(current)
    return events


def longest_excursion_h(events):
    """Return the duration of the longest excursion, or zero when there is none."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of excursion records")
    if not events:
        return 0.0
    longest = 0.0
    for event in events:
        if not isinstance(event, dict) or "duration_h" not in event:
            raise ValueError("each excursion must carry 'duration_h'")
        longest = max(longest, _as_finite_float(event["duration_h"], "duration_h"))
    return longest


def phase_order_findings(events):
    """Return findings for an exposure log whose phases are out of order."""
    if not isinstance(events, dict):
        raise ValueError("events must be a mapping of phase name to hour stamp")
    for key in events:
        if key not in PHASE_ORDER:
            raise ValueError("'%s' is not an exposure phase" % key)
    findings = []
    stamped = []
    for phase in PHASE_ORDER:
        if phase not in events:
            findings.append("exposure log has no stamp for '%s'" % phase)
            continue
        stamped.append((phase, _as_finite_float(events[phase], phase)))
    for i in range(1, len(stamped)):
        previous_phase, previous_time = stamped[i - 1]
        phase, time_h = stamped[i]
        if time_h < previous_time:
            findings.append(
                "'%s' is stamped at %g h, before '%s' at %g h"
                % (phase, time_h, previous_phase, previous_time)
            )
    return findings


def assess_test_execution(spec):
    """Run the full exposure execution assessment for one run log.

    spec keys: samples (run-log sequence), required_duration_h; optional
    events (phase stamps), limits (exposure limit overrides).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("samples", "required_duration_h"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = _as_positive_float(spec["required_duration_h"], "required_duration_h")
    limits = _resolve_limits(spec.get("limits"))
    records = validate_timeline(spec["samples"])
    delivered = qualified_dwell_h(records, limits)
    events = excursions(records, limits)
    findings = []
    if spec.get("events") is not None:
        findings.extend(phase_order_findings(spec["events"]))
    shortfall = required - delivered
    delivered_enough = shortfall <= BAND_TOLERANCE * max(required, 1.0)
    if not delivered_enough:
        findings.append(
            "qualified soak time of %.4f h is %.4f h short of the required %.4f h"
            % (delivered, shortfall, required)
        )
    for event in events:
        findings.append(
            "excursion from %g h to %g h (%.4f h) on %s"
            % (event["start_h"], event["end_h"], event["duration_h"],
               ", ".join(event["causes"]))
        )
    return {
        "qualified_dwell_h": delivered,
        "elapsed_h": records[-1]["time_h"] - records[0]["time_h"],
        "required_duration_h": required,
        "excursions": events,
        "longest_excursion_h": longest_excursion_h(events),
        "findings": findings,
        "soak_delivered": delivered_enough,
        "execution_clean": delivered_enough and not findings,
    }
