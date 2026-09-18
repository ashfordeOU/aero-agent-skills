"""Storage-condition monitoring and exposure accounting for shelf-life materials.

Anchor: ECSS-Q-ST-70-22 storage-monitoring clause -- the store's conditions are
monitored, and the exposure the stored material actually accumulated is
recorded. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the envelope being monitored against, and the reading series:
   strictly increasing timestamps, finite values, readings inside the declared
   monitoring period.
2. Grade the record itself before grading the material. A sampling gap wider
   than the required interval is unmonitored time, and unmonitored time is not
   in-limit time -- it is absence of evidence, reported as such.
3. Attribute out-of-limit time between samples by the midpoint rule: each
   interval contributes its length weighted by how many of its two endpoints
   were outside the envelope.
4. Group consecutive out-of-limit readings into named excursion events carrying
   their axes, their span and their peak deviation.
5. Close with a disposition that separates an inadequate RECORD from an
   exceeded EXPOSURE -- they call for different actions.
"""

import math

__all__ = [
    "TIME_TOLERANCE_H",
    "DEVIATION_TOLERANCE",
    "validate_envelope",
    "validate_readings",
    "reading_deviation",
    "is_out_of_limit",
    "monitoring_coverage",
    "accumulated_excursion_h",
    "excursion_events",
    "peak_deviation",
    "assess_storage_monitoring",
]

# Times and deviations are sums and differences of declared decimals; an exact
# equality at a limit can land a few ULPs on the wrong side. Absorb the
# representation error here rather than by relaxing the limit itself.
TIME_TOLERANCE_H = 1e-9
DEVIATION_TOLERANCE = 1e-9


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_envelope(envelope):
    """Return a normalised monitoring envelope."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping")
    t_min = _real(envelope.get("temp_min_c"), "temp_min_c")
    t_max = _real(envelope.get("temp_max_c"), "temp_max_c")
    if t_min > t_max:
        raise ValueError("envelope temperature band is inverted (%g > %g)" % (t_min, t_max))
    rh_max = _real(envelope.get("rh_max_pct"), "rh_max_pct")
    if rh_max <= 0.0 or rh_max > 100.0:
        raise ValueError("rh_max_pct must lie in (0, 100], got %g" % rh_max)
    return {"temp_min_c": t_min, "temp_max_c": t_max, "rh_max_pct": rh_max}


def validate_readings(readings, period_h):
    """Return the normalised reading series over a monitoring period in hours."""
    period = _real(period_h, "period_h")
    if period <= 0.0:
        raise ValueError("period_h must be positive, got %g" % period)
    if not isinstance(readings, (list, tuple)) or len(readings) < 2:
        raise ValueError("readings must be a sequence of at least two samples")
    out = []
    previous = None
    for index, item in enumerate(readings):
        if not isinstance(item, dict):
            raise ValueError("readings[%d] must be a mapping" % index)
        elapsed = _real(item.get("elapsed_h"), "readings[%d].elapsed_h" % index)
        if elapsed < 0.0 or elapsed > period + TIME_TOLERANCE_H:
            raise ValueError(
                "readings[%d].elapsed_h %g lies outside the monitoring period [0, %g]"
                % (index, elapsed, period)
            )
        if previous is not None and elapsed <= previous:
            raise ValueError(
                "readings[%d].elapsed_h %g does not advance past %g" % (index, elapsed, previous)
            )
        previous = elapsed
        temp = _real(item.get("temp_c"), "readings[%d].temp_c" % index)
        rh = _real(item.get("rh_pct"), "readings[%d].rh_pct" % index)
        if rh < 0.0 or rh > 100.0:
            raise ValueError("readings[%d].rh_pct must lie in [0, 100], got %g" % (index, rh))
        out.append({"elapsed_h": elapsed, "temp_c": temp, "rh_pct": rh})
    return out


def reading_deviation(reading, envelope):
    """Return the per-axis deviation of one reading outside the envelope."""
    env = validate_envelope(envelope)
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping")
    temp = _real(reading.get("temp_c"), "temp_c")
    rh = _real(reading.get("rh_pct"), "rh_pct")
    low = env["temp_min_c"] - temp
    high = temp - env["temp_max_c"]
    wet = rh - env["rh_max_pct"]
    return {
        "temperature_low_c": low if low > DEVIATION_TOLERANCE else 0.0,
        "temperature_high_c": high if high > DEVIATION_TOLERANCE else 0.0,
        "humidity_pct": wet if wet > DEVIATION_TOLERANCE else 0.0,
    }


def is_out_of_limit(reading, envelope):
    """Return True when a reading sits outside the envelope on any axis."""
    deviation = reading_deviation(reading, envelope)
    return any(value > 0.0 for value in deviation.values())


def monitoring_coverage(readings, period_h, required_interval_h):
    """Return how much of the period the sampling cadence actually evidences."""
    interval = _real(required_interval_h, "required_interval_h")
    if interval <= 0.0:
        raise ValueError("required_interval_h must be positive, got %g" % interval)
    samples = validate_readings(readings, period_h)
    period = float(period_h)
    edges = [0.0] + [s["elapsed_h"] for s in samples] + [period]
    unmonitored = 0.0
    widest = 0.0
    breaches = 0
    for i in range(1, len(edges)):
        gap = edges[i] - edges[i - 1]
        if gap < 0.0:
            gap = 0.0
        if gap > widest:
            widest = gap
        if gap > interval + TIME_TOLERANCE_H:
            breaches += 1
            unmonitored += gap - interval
    monitored = period - unmonitored
    if monitored < 0.0:
        monitored = 0.0
    return {
        "period_h": period,
        "sample_count": len(samples),
        "widest_gap_h": widest,
        "gap_breaches": breaches,
        "unmonitored_h": unmonitored,
        "monitored_fraction": monitored / period,
        "cadence_met": breaches == 0,
    }


def accumulated_excursion_h(readings, envelope, period_h):
    """Return out-of-limit hours, attributed between samples by the midpoint rule."""
    samples = validate_readings(readings, period_h)
    env = validate_envelope(envelope)
    total = 0.0
    for i in range(1, len(samples)):
        span = samples[i]["elapsed_h"] - samples[i - 1]["elapsed_h"]
        weight = 0.0
        if is_out_of_limit(samples[i - 1], env):
            weight += 0.5
        if is_out_of_limit(samples[i], env):
            weight += 0.5
        total += span * weight
    return total


def excursion_events(readings, envelope, period_h):
    """Group consecutive out-of-limit readings into named excursion events."""
    samples = validate_readings(readings, period_h)
    env = validate_envelope(envelope)
    events = []
    current = None
    for sample in samples:
        deviation = reading_deviation(sample, env)
        axes = sorted(axis for axis, value in deviation.items() if value > 0.0)
        if axes:
            if current is None:
                current = {
                    "start_h": sample["elapsed_h"],
                    "end_h": sample["elapsed_h"],
                    "axes": set(axes),
                    "peak_deviation": max(deviation.values()),
                    "sample_count": 1,
                }
            else:
                current["end_h"] = sample["elapsed_h"]
                current["axes"].update(axes)
                current["peak_deviation"] = max(current["peak_deviation"],
                                                max(deviation.values()))
                current["sample_count"] += 1
        elif current is not None:
            current["axes"] = sorted(current["axes"])
            events.append(current)
            current = None
    if current is not None:
        current["axes"] = sorted(current["axes"])
        events.append(current)
    return events


def peak_deviation(readings, envelope, period_h):
    """Return the largest single-axis deviation seen anywhere in the series."""
    events = excursion_events(readings, envelope, period_h)
    if not events:
        return 0.0
    return max(event["peak_deviation"] for event in events)


def assess_storage_monitoring(spec):
    """Grade a monitoring record and the exposure it evidences.

    spec keys: envelope, readings, period_h, required_interval_h,
    allowed_excursion_h, optional peak_deviation_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("envelope", "readings", "period_h", "required_interval_h",
                "allowed_excursion_h"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    allowed = _real(spec["allowed_excursion_h"], "allowed_excursion_h")
    if allowed < 0.0:
        raise ValueError("allowed_excursion_h must be non-negative, got %g" % allowed)
    limit = spec.get("peak_deviation_limit")
    if limit is not None:
        limit = _real(limit, "peak_deviation_limit")
        if limit <= 0.0:
            raise ValueError("peak_deviation_limit must be positive, got %g" % limit)

    env = validate_envelope(spec["envelope"])
    coverage = monitoring_coverage(spec["readings"], spec["period_h"],
                                   spec["required_interval_h"])
    accumulated = accumulated_excursion_h(spec["readings"], env, spec["period_h"])
    events = excursion_events(spec["readings"], env, spec["period_h"])
    peak = peak_deviation(spec["readings"], env, spec["period_h"])

    findings = []
    if not coverage["cadence_met"]:
        findings.append(
            "sampling cadence not met: %d gap(s) wider than the required interval, "
            "widest %.3f h, %.3f h unmonitored"
            % (coverage["gap_breaches"], coverage["widest_gap_h"], coverage["unmonitored_h"])
        )
    exposure_exceeded = accumulated > allowed + TIME_TOLERANCE_H
    if exposure_exceeded:
        findings.append(
            "accumulated out-of-limit exposure %.3f h exceeds the allowance %.3f h"
            % (accumulated, allowed)
        )
    peak_exceeded = limit is not None and peak > limit + DEVIATION_TOLERANCE
    if peak_exceeded:
        findings.append(
            "peak deviation %.3f exceeds the single-excursion limit %.3f" % (peak, limit)
        )

    if not coverage["cadence_met"]:
        disposition = "record-inadequate"
    elif exposure_exceeded or peak_exceeded:
        disposition = "exposure-exceeded"
    elif events:
        disposition = "exposure-within-allowance"
    else:
        disposition = "no-excursion"
    return {
        "coverage": coverage,
        "events": events,
        "accumulated_excursion_h": accumulated,
        "allowed_excursion_h": allowed,
        "peak_deviation": peak,
        "findings": findings,
        "disposition": disposition,
        "acceptable": disposition in ("no-excursion", "exposure-within-allowance"),
    }
