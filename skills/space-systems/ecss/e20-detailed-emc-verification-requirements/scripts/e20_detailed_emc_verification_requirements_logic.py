#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.4.3 -- performing electromagnetic compatibility
verification against the detailed verification requirement it references.

Deterministic, offline, stdlib only. A compatibility verification run is
not judged on its number alone: the run is judged against the detailed
requirement it cites, which fixes the frequency range to be swept, the
measurement bandwidth and the step the sweep may take across it, the
dwell the sweep owes each step, the detector the level is read with, the
limit the level is held against and the separation the ambient
background owes that limit. This module resolves that reference and
grades the run against it.

No verbatim standard text is reproduced; the clause is the anchor only.
"""

import math

# Verification categories a detailed requirement can cover.
VERIFICATION_CATEGORIES = (
    "conducted-emission",
    "conducted-susceptibility",
    "radiated-emission",
    "radiated-susceptibility",
)

# Detectors a level can be read with. A level read with the wrong
# detector is not the quantity the limit is written against.
DETECTORS = (
    "peak",
    "quasi-peak",
    "average",
    "root-mean-square",
)

# Dispositions a graded level can carry once uncertainty is applied.
DISPOSITIONS = ("compliant", "non-compliant", "inconclusive")

# Default separation the ambient background owes the limit line.
DEFAULT_AMBIENT_SEPARATION_DB = 6.0

# Accumulated dwell times and decibel sums carry representation error; a
# case that sits exactly on the requirement can land a few units in the
# last place off it. These tolerances absorb that, never the engineering
# requirement itself.
DB_TOLERANCE = 1e-9
SECOND_TOLERANCE = 1e-9


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number (got %r)" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite (got %r)" % (label, value))
    return number


def _strictly_positive(value, label):
    number = _finite(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive (got %r)" % (label, value))
    return number


def _non_negative(value, label):
    number = _finite(value, label)
    if number < 0.0:
        raise ValueError("%s cannot be negative (got %r)" % (label, value))
    return number


def normalise_referenced_requirement(record):
    """Canonicalise one detailed verification requirement."""
    if not isinstance(record, dict):
        raise ValueError("requirement record must be a mapping (got %r)" % (record,))
    ident = str(record.get("id", "")).strip()
    if not ident:
        raise ValueError("detailed requirement needs a non-empty id")
    category = record.get("category")
    if category not in VERIFICATION_CATEGORIES:
        raise ValueError(
            "detailed requirement %r has unknown category %r (expected one of %s)"
            % (ident, category, ", ".join(VERIFICATION_CATEGORIES))
        )
    start = _strictly_positive(record.get("start_hz"), "start frequency of %r" % ident)
    stop = _strictly_positive(record.get("stop_hz"), "stop frequency of %r" % ident)
    if stop <= start:
        raise ValueError(
            "detailed requirement %r stops at or below its start frequency" % ident
        )
    bandwidth = _strictly_positive(
        record.get("bandwidth_hz"), "measurement bandwidth of %r" % ident
    )
    fraction = _finite(record.get("max_step_fraction"), "step fraction of %r" % ident)
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "step fraction of %r must lie in the half-open range 0..1 (got %r)"
            % (ident, record.get("max_step_fraction"))
        )
    min_step_dwell = _strictly_positive(
        record.get("min_step_dwell_s"), "minimum step dwell of %r" % ident
    )
    min_total_dwell = _non_negative(
        record.get("min_total_dwell_s", 0.0), "minimum total dwell of %r" % ident
    )
    detector = record.get("detector")
    if detector not in DETECTORS:
        raise ValueError(
            "detailed requirement %r has unknown detector %r (expected one of %s)"
            % (ident, detector, ", ".join(DETECTORS))
        )
    limit = _finite(record.get("limit_db"), "limit of %r" % ident)
    separation = _non_negative(
        record.get("ambient_separation_db", DEFAULT_AMBIENT_SEPARATION_DB),
        "ambient separation of %r" % ident,
    )
    return {
        "id": ident,
        "category": category,
        "start_hz": start,
        "stop_hz": stop,
        "bandwidth_hz": bandwidth,
        "max_step_fraction": fraction,
        "min_step_dwell_s": min_step_dwell,
        "min_total_dwell_s": min_total_dwell,
        "detector": detector,
        "limit_db": limit,
        "ambient_separation_db": separation,
    }


def build_requirement_index(records):
    """Index the applicable detailed requirements by identifier."""
    if records is None:
        raise ValueError("no detailed verification requirements were referenced")
    index = {}
    for record in records:
        requirement = normalise_referenced_requirement(record)
        if requirement["id"] in index:
            raise ValueError("duplicate detailed requirement id %r" % requirement["id"])
        index[requirement["id"]] = requirement
    if not index:
        raise ValueError("no detailed verification requirements were referenced")
    return index


def normalise_verification_run(record):
    """Canonicalise one as-run verification sweep."""
    if not isinstance(record, dict):
        raise ValueError("verification run must be a mapping (got %r)" % (record,))
    ident = str(record.get("id", "")).strip()
    if not ident:
        raise ValueError("verification run needs a non-empty id")
    reference = str(record.get("reference", "")).strip()
    if not reference:
        raise ValueError("verification run %r references no detailed requirement" % ident)
    detector = record.get("detector")
    if detector not in DETECTORS:
        raise ValueError(
            "verification run %r used unknown detector %r" % (ident, detector)
        )
    measured = _finite(record.get("measured_db"), "measured level of %r" % ident)
    ambient = _finite(record.get("ambient_db"), "ambient level of %r" % ident)
    uncertainty = _non_negative(
        record.get("uncertainty_db"), "measurement uncertainty of %r" % ident
    )
    raw_segments = record.get("segments")
    if raw_segments is None:
        raise ValueError("verification run %r swept no segment" % ident)
    segments = []
    for raw in raw_segments:
        if not isinstance(raw, dict):
            raise ValueError("verification run %r has a segment that is not a mapping" % ident)
        start = _strictly_positive(raw.get("start_hz"), "segment start of %r" % ident)
        stop = _strictly_positive(raw.get("stop_hz"), "segment stop of %r" % ident)
        if stop <= start:
            raise ValueError(
                "verification run %r has a segment that stops at or below its start" % ident
            )
        step = _strictly_positive(raw.get("step_hz"), "segment step of %r" % ident)
        dwell = _strictly_positive(raw.get("dwell_s"), "segment dwell of %r" % ident)
        segments.append(
            {"start_hz": start, "stop_hz": stop, "step_hz": step, "dwell_s": dwell}
        )
    if not segments:
        raise ValueError("verification run %r swept no segment" % ident)
    segments.sort(key=lambda seg: (seg["start_hz"], seg["stop_hz"]))
    return {
        "id": ident,
        "reference": reference,
        "detector": detector,
        "measured_db": measured,
        "ambient_db": ambient,
        "uncertainty_db": uncertainty,
        "segments": segments,
    }


def coverage_gaps(segments, start_hz, stop_hz):
    """Sub-bands of the required range that no swept segment covered."""
    if stop_hz <= start_hz:
        raise ValueError("required range stops at or below its start frequency")
    gaps = []
    cursor = start_hz
    for segment in sorted(segments, key=lambda seg: (seg["start_hz"], seg["stop_hz"])):
        if segment["stop_hz"] <= cursor:
            continue
        if segment["start_hz"] > cursor:
            gaps.append((cursor, min(segment["start_hz"], stop_hz)))
        cursor = max(cursor, segment["stop_hz"])
        if cursor >= stop_hz:
            break
    if cursor < stop_hz:
        gaps.append((cursor, stop_hz))
    return [(lo, hi) for lo, hi in gaps if hi > lo]


def max_allowed_step(bandwidth_hz, fraction):
    """Widest frequency step the referenced procedure allows."""
    bandwidth = _strictly_positive(bandwidth_hz, "measurement bandwidth")
    share = _finite(fraction, "step fraction")
    if share <= 0.0 or share > 1.0:
        raise ValueError("step fraction must lie in the half-open range 0..1")
    return bandwidth * share


def step_count(start_hz, stop_hz, step_hz):
    """Number of frequency points a segment is sampled at."""
    start = _strictly_positive(start_hz, "segment start")
    stop = _strictly_positive(stop_hz, "segment stop")
    if stop <= start:
        raise ValueError("segment stops at or below its start frequency")
    step = _strictly_positive(step_hz, "segment step")
    span = stop - start
    if step > span:
        raise ValueError("segment step is wider than the segment itself")
    return int(math.floor(span / step)) + 1


def per_step_dwell(segment_dwell_s, steps):
    """Dwell each frequency point actually received."""
    dwell = _strictly_positive(segment_dwell_s, "segment dwell")
    if isinstance(steps, bool) or not isinstance(steps, int):
        raise ValueError("step count must be a whole number (got %r)" % (steps,))
    if steps <= 0:
        raise ValueError("step count must be strictly positive")
    return dwell / steps


def total_sweep_dwell(segments):
    """Dwell the whole sweep spent, summed over its segments."""
    if not segments:
        raise ValueError("no segment to accumulate dwell over")
    total = 0.0
    for segment in segments:
        total += _strictly_positive(segment["dwell_s"], "segment dwell")
    return total


def meets_minimum_dwell(total_s, minimum_s):
    """Compare an accumulated dwell against the minimum the procedure fixes.

    The accumulated value is a sum of decimal seconds, so a sweep that
    spends exactly the minimum can land a few units in the last place
    below it: 4.1 three times sums to 12.299999999999999, not 12.3. That
    representation error is absorbed; the minimum itself is never
    shortened.
    """
    total = _non_negative(total_s, "accumulated dwell")
    minimum = _non_negative(minimum_s, "minimum dwell")
    if total >= minimum:
        return True
    return math.isclose(total, minimum, rel_tol=0.0, abs_tol=SECOND_TOLERANCE)


def ambient_separation_db(limit_db, ambient_db):
    """How far the ambient background sits below the limit line."""
    limit = _finite(limit_db, "limit level")
    ambient = _finite(ambient_db, "ambient level")
    return limit - ambient


def ambient_is_quiet_enough(limit_db, ambient_db, required_db):
    """Whether the background leaves the limit line readable."""
    separation = ambient_separation_db(limit_db, ambient_db)
    required = _non_negative(required_db, "required ambient separation")
    if separation >= required:
        return True
    return math.isclose(separation, required, rel_tol=0.0, abs_tol=DB_TOLERANCE)


def disposition(measured_db, limit_db, uncertainty_db):
    """Settle a measured level against a limit once uncertainty applies.

    Compliant when the level plus its uncertainty still sits at or under
    the limit, non-compliant when the level less its uncertainty sits
    above it, and inconclusive in the band between -- where the run
    cannot decide and has to be repeated with a tighter setup.
    """
    measured = _finite(measured_db, "measured level")
    limit = _finite(limit_db, "limit level")
    uncertainty = _non_negative(uncertainty_db, "measurement uncertainty")
    upper = measured + uncertainty
    lower = measured - uncertainty
    if upper <= limit or math.isclose(upper, limit, rel_tol=0.0, abs_tol=DB_TOLERANCE):
        return "compliant"
    if lower > limit and not math.isclose(lower, limit, rel_tol=0.0, abs_tol=DB_TOLERANCE):
        return "non-compliant"
    return "inconclusive"


def evaluate_run(run_record, requirement_index):
    """Grade one verification run against the requirement it references."""
    run = normalise_verification_run(run_record)
    requirement = requirement_index.get(run["reference"])
    if requirement is None:
        return {
            "id": run["id"],
            "reference": run["reference"],
            "resolved": False,
            "disposition": None,
            "coverage_gaps": [],
            "findings": [
                "run %s references %s, which is not in the applicable requirement set"
                % (run["id"], run["reference"])
            ],
            "conformant": False,
        }
    findings = []
    gaps = coverage_gaps(run["segments"], requirement["start_hz"], requirement["stop_hz"])
    for low, high in gaps:
        findings.append(
            "run %s left %.0f Hz to %.0f Hz of %s unswept"
            % (run["id"], low, high, requirement["id"])
        )
    widest = max_allowed_step(requirement["bandwidth_hz"], requirement["max_step_fraction"])
    for segment in run["segments"]:
        if segment["step_hz"] > widest:
            findings.append(
                "run %s stepped %.1f Hz from %.0f Hz, wider than the %.1f Hz the "
                "bandwidth allows" % (run["id"], segment["step_hz"], segment["start_hz"], widest)
            )
            continue
        steps = step_count(segment["start_hz"], segment["stop_hz"], segment["step_hz"])
        dwell = per_step_dwell(segment["dwell_s"], steps)
        if dwell < requirement["min_step_dwell_s"] and not math.isclose(
            dwell, requirement["min_step_dwell_s"], rel_tol=0.0, abs_tol=SECOND_TOLERANCE
        ):
            findings.append(
                "run %s dwelt %.6f s per point from %.0f Hz, under the %.6f s demanded"
                % (run["id"], dwell, segment["start_hz"], requirement["min_step_dwell_s"])
            )
    total = total_sweep_dwell(run["segments"])
    if not meets_minimum_dwell(total, requirement["min_total_dwell_s"]):
        findings.append(
            "run %s spent %.6f s in total, under the %.6f s demanded"
            % (run["id"], total, requirement["min_total_dwell_s"])
        )
    if run["detector"] != requirement["detector"]:
        findings.append(
            "run %s read the level with a %s detector where %s fixes %s"
            % (run["id"], run["detector"], requirement["id"], requirement["detector"])
        )
    if not ambient_is_quiet_enough(
        requirement["limit_db"], run["ambient_db"], requirement["ambient_separation_db"]
    ):
        findings.append(
            "run %s sat in an ambient %.3f dB below the limit, short of the %.1f dB "
            "demanded"
            % (
                run["id"],
                ambient_separation_db(requirement["limit_db"], run["ambient_db"]),
                requirement["ambient_separation_db"],
            )
        )
    settled = disposition(run["measured_db"], requirement["limit_db"], run["uncertainty_db"])
    if settled != "compliant":
        findings.append(
            "run %s settles as %s against %s" % (run["id"], settled, requirement["id"])
        )
    return {
        "id": run["id"],
        "reference": run["reference"],
        "resolved": True,
        "category": requirement["category"],
        "disposition": settled,
        "total_dwell_s": total,
        "coverage_gaps": gaps,
        "findings": findings,
        "conformant": not findings,
    }


def review_campaign(run_records, requirement_records):
    """Aggregate the clause 6.4.3 review over a verification campaign."""
    index = build_requirement_index(requirement_records)
    if run_records is None:
        raise ValueError("no verification run to review")
    results = []
    seen = set()
    for record in run_records:
        result = evaluate_run(record, index)
        if result["id"] in seen:
            raise ValueError("duplicate verification run id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
    if not results:
        raise ValueError("no verification run to review")
    findings = []
    for result in sorted(results, key=lambda item: item["id"]):
        findings.extend(result["findings"])
    exercised = set(r["reference"] for r in results if r["resolved"])
    unexercised = sorted(ident for ident in index if ident not in exercised)
    for ident in unexercised:
        findings.append("requirement %s was never exercised by a run" % ident)
    return {
        "runs": results,
        "unexercised_requirements": unexercised,
        "inconclusive_runs": sorted(
            r["id"] for r in results if r["disposition"] == "inconclusive"
        ),
        "findings": findings,
        "conformant": not findings,
    }
