"""Continuity evidence taken across a solar-array thermal-cycling run.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.3.2 (general provisions for thermal
cycling -- the evidence that the cells and the wiring of the assembly keep
conducting from the first cycle to the last). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every monitored channel: its kind, its baseline resistance and its
   checkpoint readings, which must be taken at whole cycles inside the run and
   in increasing cycle order.
2. Measure the resistance drift of each reading against the channel baseline
   and compare it with the drift the run allows.
3. Detect an open at the end of the run, and an intermittent open that showed
   up at an intermediate checkpoint and closed again before the next one.
4. Group each channel as continuous, drifting, intermittent or open, and
   summarise the counts.
5. Check the monitoring itself: a checkpoint at the start and at the end of the
   run, no gap between checkpoints wider than the allowed one, and at least one
   cell-string channel and one wiring channel, since a run that watched only
   one of the two leaves the other without evidence.
6. Continuity is maintained only when every channel is continuous and the
   monitoring covers the whole cycle count.
"""

import math

__all__ = [
    "DRIFT_TOLERANCE",
    "RESISTANCE_TOLERANCE",
    "CHANNEL_KINDS",
    "REQUIRED_KINDS",
    "CATEGORIES",
    "normalize_kind",
    "drift_fraction",
    "is_open",
    "validate_readings",
    "categorize_channel",
    "monitoring_gaps",
    "kind_findings",
    "assess_continuity_evidence",
]

# A drift landing exactly on the allowed fraction is allowed: the fraction is a
# subtraction over a division and can miss by a few units in the last place.
DRIFT_TOLERANCE = 1e-9

# Same reasoning for a reading sitting exactly on the open-circuit threshold,
# which counts as an open.
RESISTANCE_TOLERANCE = 1e-12

CHANNEL_KINDS = ("cell-string", "wiring", "interconnect")

# Evidence for the cells and evidence for the wiring are both required by the
# clause; an interconnect channel is welcome but does not replace either.
REQUIRED_KINDS = ("cell-string", "wiring")

CATEGORIES = ("continuous", "drifting", "intermittent", "open")


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _whole(value, label):
    """Return value as a non-negative integer, rejecting booleans and floats."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def normalize_kind(kind):
    """Return a channel kind lowered, trimmed and hyphenated."""
    if not isinstance(kind, str):
        raise ValueError("channel kind must be a string, got %r" % (kind,))
    cleaned = " ".join(kind.strip().lower().replace("_", " ").split())
    cleaned = cleaned.replace(" ", "-")
    if cleaned not in CHANNEL_KINDS:
        raise ValueError(
            "channel kind '%s' is not one of %s" % (kind, ", ".join(CHANNEL_KINDS))
        )
    return cleaned


def drift_fraction(baseline_ohm, measured_ohm):
    """Return the fractional resistance change of a reading from its baseline."""
    baseline = _positive(baseline_ohm, "baseline_ohm")
    measured = _real(measured_ohm, "measured_ohm")
    if measured < 0.0:
        raise ValueError("measured_ohm must be non-negative, got %g" % measured)
    return (measured - baseline) / baseline


def is_open(measured_ohm, open_threshold_ohm):
    """Return True when a reading has reached the open-circuit threshold."""
    measured = _real(measured_ohm, "measured_ohm")
    threshold = _positive(open_threshold_ohm, "open_threshold_ohm")
    if measured < 0.0:
        raise ValueError("measured_ohm must be non-negative, got %g" % measured)
    if math.isclose(measured, threshold, rel_tol=RESISTANCE_TOLERANCE, abs_tol=0.0):
        return True
    return measured > threshold


def validate_readings(readings, total_cycles):
    """Return the validated [(cycle, ohm), ...] series of one channel."""
    total = _whole(total_cycles, "total_cycles")
    if total <= 0:
        raise ValueError("total_cycles must be strictly positive, got %d" % total)
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of (cycle, ohm) pairs")
    series = []
    previous = None
    for index, item in enumerate(readings):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("readings[%d] must be a (cycle, ohm) pair" % index)
        cycle = _whole(item[0], "readings[%d] cycle" % index)
        if cycle > total:
            raise ValueError(
                "readings[%d] cycle %d is past the %d-cycle run" % (index, cycle, total)
            )
        ohm = _real(item[1], "readings[%d] resistance" % index)
        if ohm < 0.0:
            raise ValueError("readings[%d] resistance must be non-negative" % index)
        if previous is not None and cycle <= previous:
            raise ValueError(
                "readings must be in increasing cycle order (index %d)" % index
            )
        previous = cycle
        series.append((cycle, ohm))
    return series


def categorize_channel(channel, total_cycles, drift_limit, open_threshold_ohm):
    """Return the continuity record of one monitored channel."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping")
    for key in ("id", "kind", "baseline_ohm", "readings"):
        if key not in channel:
            raise ValueError("channel missing required key '%s'" % key)
    identifier = channel["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("channel id must be a non-empty string")
    kind = normalize_kind(channel["kind"])
    baseline = _positive(channel["baseline_ohm"], "baseline_ohm")
    limit = _real(drift_limit, "drift_limit")
    if limit <= 0.0:
        raise ValueError("drift_limit must be strictly positive, got %g" % limit)
    threshold = _positive(open_threshold_ohm, "open_threshold_ohm")
    if threshold <= baseline:
        raise ValueError(
            "open_threshold_ohm %g must exceed the channel baseline %g"
            % (threshold, baseline)
        )
    series = validate_readings(channel["readings"], total_cycles)

    max_drift = None
    open_cycles = []
    for cycle, ohm in series:
        drift = drift_fraction(baseline, ohm)
        if max_drift is None or drift > max_drift:
            max_drift = drift
        if is_open(ohm, threshold):
            open_cycles.append(cycle)
    final_cycle, final_ohm = series[-1]
    final_open = is_open(final_ohm, threshold)

    if final_open:
        category = "open"
    elif open_cycles:
        category = "intermittent"
    elif max_drift > limit + DRIFT_TOLERANCE:
        category = "drifting"
    else:
        category = "continuous"
    return {
        "id": identifier.strip(),
        "kind": kind,
        "baseline_ohm": baseline,
        "cycles": [cycle for cycle, _ in series],
        "final_cycle": final_cycle,
        "final_ohm": final_ohm,
        "max_drift_fraction": max_drift,
        "open_cycles": open_cycles,
        "category": category,
    }


def monitoring_gaps(cycles, total_cycles, max_gap_cycles):
    """Return findings where the checkpoint series leaves the run unwitnessed."""
    total = _whole(total_cycles, "total_cycles")
    if total <= 0:
        raise ValueError("total_cycles must be strictly positive, got %d" % total)
    gap = _whole(max_gap_cycles, "max_gap_cycles")
    if gap <= 0:
        raise ValueError("max_gap_cycles must be strictly positive, got %d" % gap)
    if not isinstance(cycles, (list, tuple)) or not cycles:
        raise ValueError("cycles must be a non-empty sequence")
    ordered = sorted(_whole(c, "checkpoint cycle") for c in cycles)
    findings = []
    if ordered[0] != 0:
        findings.append(
            "no continuity reading before the run: first checkpoint is cycle %d"
            % ordered[0]
        )
    if ordered[-1] != total:
        findings.append(
            "no continuity reading at the end of the run: last checkpoint is "
            "cycle %d of %d" % (ordered[-1], total)
        )
    for index in range(1, len(ordered)):
        span = ordered[index] - ordered[index - 1]
        if span > gap:
            findings.append(
                "cycles %d to %d are unwitnessed, a gap of %d against the "
                "allowed %d" % (ordered[index - 1], ordered[index], span, gap)
            )
    return findings


def kind_findings(records):
    """Return findings for the channel kinds the evidence never covered."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    present = set()
    for record in records:
        if not isinstance(record, dict) or "kind" not in record:
            raise ValueError("each record must be a mapping carrying 'kind'")
        present.add(record["kind"])
    return [
        "no %s channel was monitored across the run" % kind
        for kind in REQUIRED_KINDS
        if kind not in present
    ]


def assess_continuity_evidence(spec):
    """Run the full clause 5.5.1.3.2 continuity-evidence assessment.

    spec keys: total_cycles, drift_limit_fraction, open_threshold_ohm,
    max_gap_cycles, channels (each: id, kind, baseline_ohm, readings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("total_cycles", "drift_limit_fraction", "open_threshold_ohm",
                "max_gap_cycles", "channels"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    channels = spec["channels"]
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("spec['channels'] must be a non-empty sequence")

    records = []
    seen = set()
    for channel in channels:
        record = categorize_channel(
            channel,
            spec["total_cycles"],
            spec["drift_limit_fraction"],
            spec["open_threshold_ohm"],
        )
        if record["id"] in seen:
            raise ValueError("channel id '%s' appears twice" % record["id"])
        seen.add(record["id"])
        records.append(record)

    summary = dict((category, 0) for category in CATEGORIES)
    findings = []
    for record in records:
        summary[record["category"]] += 1
        if record["category"] == "open":
            findings.append(
                "channel '%s' is open at cycle %d; continuity is not maintained"
                % (record["id"], record["final_cycle"])
            )
        elif record["category"] == "intermittent":
            findings.append(
                "channel '%s' opened at cycle(s) %s and closed again; the open is "
                "evidence, not noise"
                % (record["id"], ", ".join(str(c) for c in record["open_cycles"]))
            )
        elif record["category"] == "drifting":
            findings.append(
                "channel '%s' drifted %.4f from baseline, past the allowed %.4f"
                % (record["id"], record["max_drift_fraction"],
                   float(spec["drift_limit_fraction"]))
            )
    for record in records:
        for text in monitoring_gaps(
            record["cycles"], spec["total_cycles"], spec["max_gap_cycles"]
        ):
            findings.append("channel '%s': %s" % (record["id"], text))
    findings.extend(kind_findings(records))
    return {
        "records": records,
        "summary": summary,
        "findings": findings,
        "continuity_maintained": not findings,
    }
