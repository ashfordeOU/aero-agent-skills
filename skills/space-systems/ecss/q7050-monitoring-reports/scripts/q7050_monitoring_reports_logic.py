"""Reporting of cleanliness monitoring results against a programme's obligations.

Anchor: ECSS-Q-ST-70-50C, the clause on reporting monitoring results.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
A monitoring report is accepted when four independent things hold:

1. period coverage -- the reported monitoring intervals, merged, cover the
   whole reporting period. Every day the period contains and the intervals
   do not is an unmonitored day, and two intervals covering the same days
   are a double count, not extra coverage;
2. location coverage -- every location the programme named appears;
3. traceability -- every reported result names the instrument that
   produced it and the method it was produced by, so a later exceedance can
   be chased back to an instrument-control record;
4. timeliness -- the submission sits inside the turnaround the programme
   allowed, measured from the end of the period and not from the last
   sample;

plus the content items the programme listed, graded as a fraction so a
partial package reports how partial it is.
"""

import math

__all__ = [
    "DAY_TOLERANCE",
    "DEFAULT_CONTENT_ITEMS",
    "require_real",
    "require_int",
    "validate_interval",
    "validate_intervals",
    "merge_intervals",
    "overlapping_pairs",
    "period_coverage",
    "submission_latency_days",
    "grade_timeliness",
    "grade_traceability",
    "grade_location_coverage",
    "content_completeness",
    "assess_monitoring_report",
]

# Coverage arithmetic is differences of day numbers; an interval that ends
# exactly where the next begins must not read as a gap. Absorb the
# representation error here, never by widening the reporting period.
DAY_TOLERANCE = 1e-9

DEFAULT_CONTENT_ITEMS = (
    "period",
    "locations",
    "methods",
    "results",
    "limits_applied",
    "exceedances",
    "trend",
    "signature",
)


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def require_int(value, label, non_negative=False, positive=False):
    """Return value as an int, rejecting booleans and floats."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_interval(interval, label="interval"):
    """Return one (start_day, end_day) interval with a positive duration."""
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        raise ValueError("%s must be a (start_day, end_day) pair" % label)
    start = require_real(interval[0], "%s start_day" % label)
    end = require_real(interval[1], "%s end_day" % label)
    if end <= start:
        raise ValueError(
            "%s must end after it starts, got (%g, %g)" % (label, start, end)
        )
    return (start, end)


def validate_intervals(intervals):
    """Return the reported intervals, each validated, ordered by start day."""
    if not isinstance(intervals, (list, tuple)) or not intervals:
        raise ValueError("intervals must be a non-empty sequence of day pairs")
    validated = [
        validate_interval(item, "intervals[%d]" % index)
        for index, item in enumerate(intervals)
    ]
    validated.sort(key=lambda pair: pair[0])
    return validated


def merge_intervals(intervals):
    """Merge the reported intervals into disjoint covered stretches."""
    ordered = validate_intervals(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start < last_end or math.isclose(
            start, last_end, rel_tol=0.0, abs_tol=DAY_TOLERANCE
        ):
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def overlapping_pairs(intervals):
    """List the reported intervals that cover the same days twice."""
    ordered = validate_intervals(intervals)
    overlaps = []
    for i in range(1, len(ordered)):
        previous = ordered[i - 1]
        current = ordered[i]
        if current[0] < previous[1] and not math.isclose(
            current[0], previous[1], rel_tol=0.0, abs_tol=DAY_TOLERANCE
        ):
            overlaps.append({
                "first": previous,
                "second": current,
                "overlap_days": min(previous[1], current[1]) - current[0],
            })
    return overlaps


def period_coverage(intervals, period_start, period_end):
    """Measure how much of the reporting period the intervals actually cover."""
    start = require_real(period_start, "period_start")
    end = require_real(period_end, "period_end")
    if end <= start:
        raise ValueError(
            "period_end %g must be after period_start %g" % (end, start)
        )
    merged = merge_intervals(intervals)
    covered = 0.0
    gaps = []
    outside = []
    cursor = start
    for interval_start, interval_end in merged:
        if interval_end <= start or interval_start >= end:
            outside.append((interval_start, interval_end))
            continue
        if interval_start < start or interval_end > end:
            outside.append((interval_start, interval_end))
        clipped_start = max(interval_start, start)
        clipped_end = min(interval_end, end)
        if clipped_start > cursor and not math.isclose(
            clipped_start, cursor, rel_tol=0.0, abs_tol=DAY_TOLERANCE
        ):
            gaps.append((cursor, clipped_start))
        covered += clipped_end - clipped_start
        cursor = max(cursor, clipped_end)
    if cursor < end and not math.isclose(
        cursor, end, rel_tol=0.0, abs_tol=DAY_TOLERANCE
    ):
        gaps.append((cursor, end))
    period_days = end - start
    return {
        "period_days": period_days,
        "covered_days": covered,
        "coverage_fraction": covered / period_days,
        "gaps": gaps,
        "outside_period": outside,
        "overlaps": overlapping_pairs(intervals),
        "complete": not gaps,
    }


def submission_latency_days(period_end, submitted_day):
    """Return the days between the end of the period and the submission."""
    end = require_real(period_end, "period_end")
    submitted = require_real(submitted_day, "submitted_day")
    return submitted - end


def grade_timeliness(period_end, submitted_day, turnaround_days):
    """Grade the submission against the turnaround the programme allowed."""
    turnaround = require_real(turnaround_days, "turnaround_days", positive=True)
    latency = submission_latency_days(period_end, submitted_day)
    if latency < 0.0:
        raise ValueError(
            "submitted_day precedes the end of the reporting period by %g days; "
            "the period cannot be reported before it closed" % (-latency)
        )
    on_time = latency <= turnaround or math.isclose(
        latency, turnaround, rel_tol=0.0, abs_tol=DAY_TOLERANCE
    )
    return {
        "latency_days": latency,
        "turnaround_days": turnaround,
        "on_time": on_time,
        "overdue_days": 0.0 if on_time else latency - turnaround,
    }


def grade_traceability(results):
    """Check that every reported result names its instrument and its method."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence of result records")
    untraceable = []
    for index, record in enumerate(results):
        if not isinstance(record, dict):
            raise ValueError("results[%d] must be a mapping" % index)
        if "location" not in record:
            raise ValueError("results[%d] must name its location" % index)
        missing = [
            field for field in ("instrument_id", "method")
            if not record.get(field)
        ]
        if missing:
            untraceable.append({
                "index": index,
                "location": record["location"],
                "missing": missing,
            })
    return {
        "count": len(results),
        "untraceable": untraceable,
        "traceable": not untraceable,
    }


def grade_location_coverage(results, required_locations):
    """Check that every location the programme named was reported on."""
    if not isinstance(required_locations, (list, tuple)) or not required_locations:
        raise ValueError("required_locations must be a non-empty sequence")
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence of result records")
    reported = set()
    for index, record in enumerate(results):
        if not isinstance(record, dict) or "location" not in record:
            raise ValueError("results[%d] must be a mapping naming its location" % index)
        reported.add(record["location"])
    missing = [name for name in required_locations if name not in reported]
    extra = sorted(name for name in reported if name not in required_locations)
    return {
        "required": list(required_locations),
        "reported": sorted(reported),
        "missing": missing,
        "unexpected": extra,
        "complete": not missing,
    }


def content_completeness(package, required_items=DEFAULT_CONTENT_ITEMS):
    """Grade the report package against the content items the programme listed."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    if not isinstance(required_items, (list, tuple)) or not required_items:
        raise ValueError("required_items must be a non-empty sequence")
    present = []
    missing = []
    for item in required_items:
        value = package.get(item)
        if value is None or value is False or value == "":
            missing.append(item)
        else:
            present.append(item)
    return {
        "present": present,
        "missing": missing,
        "fraction_complete": len(present) / len(required_items),
        "complete": not missing,
    }


def assess_monitoring_report(spec):
    """Grade a monitoring report package against the programme's obligations.

    spec keys: period_start, period_end, intervals, results, submitted_day,
    turnaround_days, required_locations, optional package and required_items.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("period_start", "period_end", "intervals", "results",
                "submitted_day", "turnaround_days", "required_locations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coverage = period_coverage(
        spec["intervals"], spec["period_start"], spec["period_end"]
    )
    timeliness = grade_timeliness(
        spec["period_end"], spec["submitted_day"], spec["turnaround_days"]
    )
    traceability = grade_traceability(spec["results"])
    locations = grade_location_coverage(spec["results"], spec["required_locations"])
    content = content_completeness(
        spec.get("package", {}), spec.get("required_items", DEFAULT_CONTENT_ITEMS)
    )
    findings = []
    for gap_start, gap_end in coverage["gaps"]:
        findings.append(
            "reporting period is unmonitored from day %.1f to day %.1f"
            % (gap_start, gap_end)
        )
    for overlap in coverage["overlaps"]:
        findings.append(
            "reported intervals double count %.1f days from day %.1f"
            % (overlap["overlap_days"], overlap["second"][0])
        )
    if coverage["outside_period"]:
        findings.append(
            "%d reported interval(s) extend outside the reporting period"
            % len(coverage["outside_period"])
        )
    if not timeliness["on_time"]:
        findings.append(
            "submission is %.1f days past the %.1f day turnaround"
            % (timeliness["overdue_days"], timeliness["turnaround_days"])
        )
    for entry in traceability["untraceable"]:
        findings.append(
            "result %d at %s does not name its %s"
            % (entry["index"], entry["location"], " and ".join(entry["missing"]))
        )
    if locations["missing"]:
        findings.append(
            "no results reported for location(s): %s" % ", ".join(locations["missing"])
        )
    if not content["complete"]:
        findings.append(
            "report content missing: %s" % ", ".join(content["missing"])
        )
    return {
        "coverage": coverage,
        "timeliness": timeliness,
        "traceability": traceability,
        "locations": locations,
        "content": content,
        "findings": findings,
        "acceptable": not findings,
    }
