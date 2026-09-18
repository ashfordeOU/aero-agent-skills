"""Build set-up and execution control for a powder-bed additive-manufacturing job.

Anchor: ECSS-Q-ST-70-80 process clauses covering execution of a build: platform
preparation, the start-up checks that gate the first layer, and the monitoring
that runs while the job builds. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade the start-up checklist against its declared limits. A check that was
   never recorded blocks the start exactly as an out-of-limit one does, because
   neither shows the machine was ready.
2. Refuse to look at monitoring data at all while the start is blocked: a build
   that should not have started is dispositioned on that, not on how it ran.
3. Grade each monitored channel layer by layer against its limits, and measure
   how many consecutive layers an excursion persisted for - a single layer
   outside a band is a concession, a run of them is a process that left control.
4. Measure monitoring coverage against the layer count. Sparse sampling is a
   finding in its own right, because unmonitored layers are unevidenced layers.
5. Grade the discrete build events (recoater interruptions, restarts) against
   their allowed counts.
6. Give the disposition: start blocked, aborted, complete with concession, or
   complete.
"""

import math

__all__ = [
    "LIMIT_REL_TOLERANCE",
    "LIMIT_ABS_TOLERANCE",
    "DEFAULT_ABORT_AFTER_LAYERS",
    "DEFAULT_MIN_COVERAGE",
    "validate_limits",
    "check_value",
    "evaluate_startup_checks",
    "start_permitted",
    "layer_excursions",
    "longest_consecutive_layers",
    "monitoring_coverage",
    "evaluate_channel",
    "evaluate_event_counts",
    "execute_build",
]

# Monitored values arrive through sensor scaling and logger rounding, so a value
# exactly on a limit can read a few units in the last place outside it. The
# comparison absorbs that; the limit itself is never moved.
LIMIT_REL_TOLERANCE = 1e-9
LIMIT_ABS_TOLERANCE = 1e-12

# Consecutive layers outside a band before the build is no longer a concession.
DEFAULT_ABORT_AFTER_LAYERS = 3

# Fraction of layers that has to carry a sample for monitoring to be evidence.
DEFAULT_MIN_COVERAGE = 0.9


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_limits(name, limits):
    """Return the validated limit pair for one check or channel."""
    if not isinstance(limits, dict) or not ({"min", "max"} & set(limits)):
        raise ValueError("limits for '%s' must declare 'min' and/or 'max'" % name)
    low = None
    high = None
    if "min" in limits:
        low = _finite("limits['%s']['min']" % name, limits["min"])
    if "max" in limits:
        high = _finite("limits['%s']['max']" % name, limits["max"])
    if low is not None and high is not None and low > high:
        raise ValueError("limits for '%s' are inverted: min %g above max %g" % (name, low, high))
    return (low, high)


def check_value(value, limits, name="value"):
    """Return 'ok', 'below-minimum' or 'above-maximum' for one reading."""
    low, high = validate_limits(name, limits)
    number = _finite(name, value)
    if low is not None and number < low and not math.isclose(
        number, low, rel_tol=LIMIT_REL_TOLERANCE, abs_tol=LIMIT_ABS_TOLERANCE
    ):
        return "below-minimum"
    if high is not None and number > high and not math.isclose(
        number, high, rel_tol=LIMIT_REL_TOLERANCE, abs_tol=LIMIT_ABS_TOLERANCE
    ):
        return "above-maximum"
    return "ok"


def evaluate_startup_checks(recorded, requirements):
    """Return one status record per required start-up check."""
    if not isinstance(requirements, dict) or not requirements:
        raise ValueError("requirements must be a non-empty mapping of checks to limits")
    if not isinstance(recorded, dict):
        raise ValueError("recorded start-up checks must be a mapping")
    for name in recorded:
        if name not in requirements:
            raise ValueError(
                "start-up record '%s' has no declared limit to be graded against" % name
            )
    records = []
    for name in sorted(requirements):
        limits = requirements[name]
        validate_limits(name, limits)
        if name not in recorded or recorded[name] is None:
            records.append({"check": name, "status": "unrecorded", "value": None})
            continue
        value = _finite("start-up check '%s'" % name, recorded[name])
        records.append({"check": name, "status": check_value(value, limits, name),
                        "value": value})
    return records


def start_permitted(startup_records):
    """Return True only when every start-up check was recorded and inside limits."""
    if not isinstance(startup_records, (list, tuple)) or not startup_records:
        raise ValueError("startup_records must be a non-empty sequence")
    for record in startup_records:
        if not isinstance(record, dict) or "status" not in record:
            raise ValueError("each start-up record must carry a 'status'")
        if record["status"] != "ok":
            return False
    return True


def layer_excursions(samples, limits, name="channel"):
    """Return the layer samples that sit outside the channel limits."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples for '%s' must be a non-empty sequence" % name)
    excursions = []
    seen = set()
    for item in samples:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each sample of '%s' must be a (layer, value) pair" % name)
        layer = item[0]
        if not isinstance(layer, int) or isinstance(layer, bool) or layer < 1:
            raise ValueError("layer index in '%s' must be a positive integer" % name)
        if layer in seen:
            raise ValueError("duplicate sample for layer %d of '%s'" % (layer, name))
        seen.add(layer)
        status = check_value(item[1], limits, name)
        if status != "ok":
            excursions.append({"layer": layer, "value": float(item[1]), "status": status})
    excursions.sort(key=lambda record: record["layer"])
    return excursions


def longest_consecutive_layers(layers):
    """Return the length of the longest run of consecutive layer indices."""
    if not isinstance(layers, (list, tuple, set)):
        raise ValueError("layers must be a sequence of integers")
    ordered = []
    for layer in layers:
        if not isinstance(layer, int) or isinstance(layer, bool) or layer < 1:
            raise ValueError("layer indices must be positive integers")
        ordered.append(layer)
    ordered = sorted(set(ordered))
    if not ordered:
        return 0
    longest = 1
    run = 1
    for i in range(1, len(ordered)):
        if ordered[i] == ordered[i - 1] + 1:
            run += 1
        else:
            run = 1
        if run > longest:
            longest = run
    return longest


def monitoring_coverage(sampled_layers, total_layers):
    """Return the fraction of build layers that carry a monitoring sample."""
    if not isinstance(total_layers, int) or isinstance(total_layers, bool) or total_layers < 1:
        raise ValueError("total_layers must be a positive integer")
    unique = set()
    for layer in sampled_layers:
        if not isinstance(layer, int) or isinstance(layer, bool) or layer < 1:
            raise ValueError("layer indices must be positive integers")
        if layer > total_layers:
            raise ValueError(
                "sample at layer %d is above the declared build height of %d layers"
                % (layer, total_layers)
            )
        unique.add(layer)
    return len(unique) / float(total_layers)


def evaluate_channel(name, channel, total_layers, abort_after_layers=DEFAULT_ABORT_AFTER_LAYERS):
    """Evaluate one monitored channel and return its record."""
    if not isinstance(channel, dict) or "samples" not in channel or "limits" not in channel:
        raise ValueError("channel '%s' needs 'samples' and 'limits'" % name)
    if (not isinstance(abort_after_layers, int) or isinstance(abort_after_layers, bool)
            or abort_after_layers < 1):
        raise ValueError("abort_after_layers must be a positive integer")
    excursions = layer_excursions(channel["samples"], channel["limits"], name)
    sampled = [item[0] for item in channel["samples"]]
    coverage = monitoring_coverage(sampled, total_layers)
    longest = longest_consecutive_layers([record["layer"] for record in excursions])
    return {
        "channel": name,
        "excursions": excursions,
        "longest_excursion_run": longest,
        "coverage": coverage,
        "abort": longest >= abort_after_layers,
    }


def evaluate_event_counts(counts, limits):
    """Return findings where a discrete build event exceeded its allowed count."""
    if not isinstance(counts, dict):
        raise ValueError("event counts must be a mapping")
    if not isinstance(limits, dict):
        raise ValueError("event limits must be a mapping")
    findings = []
    for name in sorted(counts):
        value = counts[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("event count '%s' must be a non-negative integer" % name)
        if name not in limits:
            raise ValueError("event '%s' has no declared allowed count" % name)
        allowed = limits[name]
        if not isinstance(allowed, int) or isinstance(allowed, bool) or allowed < 0:
            raise ValueError("allowed count for '%s' must be a non-negative integer" % name)
        if value > allowed:
            findings.append({"event": name, "count": value, "allowed": allowed})
    return findings


def execute_build(spec):
    """Run the full build set-up and execution assessment.

    spec keys: startup_records, startup_requirements, total_layers, channels,
    optional event_counts, event_limits, abort_after_layers, min_coverage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("startup_records", "startup_requirements", "total_layers", "channels"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    startup = evaluate_startup_checks(spec["startup_records"], spec["startup_requirements"])
    blocking = [
        "start-up check %s %s" % (record["check"], record["status"])
        for record in startup
        if record["status"] != "ok"
    ]
    if not start_permitted(startup):
        return {
            "disposition": "start-blocked",
            "startup": startup,
            "channels": [],
            "blocking": blocking,
            "findings": [],
        }
    channels = spec["channels"]
    if not isinstance(channels, dict) or not channels:
        raise ValueError("spec['channels'] must be a non-empty mapping")
    abort_after = spec.get("abort_after_layers", DEFAULT_ABORT_AFTER_LAYERS)
    min_coverage = _finite("min_coverage", spec.get("min_coverage", DEFAULT_MIN_COVERAGE))
    if not 0.0 < min_coverage <= 1.0:
        raise ValueError("min_coverage must sit in (0, 1]")
    records = []
    findings = []
    aborted = []
    for name in sorted(channels):
        record = evaluate_channel(name, channels[name], spec["total_layers"], abort_after)
        records.append(record)
        if record["abort"]:
            aborted.append(
                "channel %s stayed outside its band for %d consecutive layers"
                % (name, record["longest_excursion_run"])
            )
        elif record["excursions"]:
            findings.append(
                "channel %s had %d isolated layer excursion(s)"
                % (name, len(record["excursions"]))
            )
        if record["coverage"] < min_coverage and not math.isclose(
            record["coverage"], min_coverage, rel_tol=LIMIT_REL_TOLERANCE, abs_tol=0.0
        ):
            findings.append(
                "channel %s sampled %.1f%% of the layers, below the %.1f%% required"
                % (name, 100.0 * record["coverage"], 100.0 * min_coverage)
            )
    for item in evaluate_event_counts(spec.get("event_counts", {}), spec.get("event_limits", {})):
        findings.append(
            "%s occurred %d times, above the %d allowed"
            % (item["event"], item["count"], item["allowed"])
        )
    if aborted:
        disposition = "aborted"
    elif findings:
        disposition = "complete-with-concession"
    else:
        disposition = "complete"
    return {
        "disposition": disposition,
        "startup": startup,
        "channels": records,
        "blocking": aborted,
        "findings": findings,
    }
