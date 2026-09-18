#!/usr/bin/env python3
"""Cable injection susceptibility purpose, ECSS-E-ST-20-07C clause 5.4.8.1.

Paraphrased procedure, no verbatim standard text. The clause states an
aim: a unit has to keep working while sine wave currents are coupled onto
the cables and leads that reach it. This module turns that aim into a
deterministic assessment of a completed injection run:

  sweep records per harness bundle -> validated, frequencies advancing
  achieved against required current -> drive margin in decibels
  frequency list against the grid    -> coverage gaps in the swept band
  deviation onset against the level  -> susceptibility threshold margin
  every bundle reduced              -> governing bundle and frequency

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Margins, band edges and grid ratios are floats,
# so a value that exactly meets a bound can land a few units in the last
# place off it. These absorb representation error only; they never relax
# a required level.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# A point whose drive margin sits inside this many decibels of the
# required level is carried as sitting on the limit, not clearing it.
AT_LIMIT_TOLERANCE_DB = 0.5

# Points per decade the sweep has to keep up with before a step between
# two frequencies counts as a gap in the coverage.
POINTS_PER_DECADE = 10.0

MEETS_LIMIT = "meets-limit"
AT_LIMIT = "at-limit"
DRIVE_SHORTFALL = "drive-shortfall"

NOT_SUSCEPTIBLE = "not-susceptible"
SUSCEPTIBLE_ABOVE_LIMIT = "susceptible-above-limit"
SUSCEPTIBLE_AT_OR_BELOW_LIMIT = "susceptible-at-or-below-limit"

VERDICT_DEMONSTRATED = "aim-demonstrated"
VERDICT_WITH_LIMITATIONS = "aim-demonstrated-with-limitations"
VERDICT_NOT_DEMONSTRATED = "aim-not-demonstrated"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _token(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s: field %r must not be empty" % (where, key))
    return token


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def margin_db(achieved_current_a, required_current_a):
    """Decibels by which an injected current clears the level required."""
    achieved = _scalar(achieved_current_a, "achieved_current_a")
    required = _scalar(required_current_a, "required_current_a")
    if achieved <= 0.0:
        raise ValueError("achieved_current_a must be > 0, got %g" % achieved)
    if required <= 0.0:
        raise ValueError("required_current_a must be > 0, got %g" % required)
    return 20.0 * math.log10(achieved / required)


def validate_band(band, name="band"):
    """Validate one (low, high) frequency band in hertz and return it."""
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("%s: must be a (low, high) pair in hertz" % name)
    low = _scalar(band[0], "%s.low" % name)
    high = _scalar(band[1], "%s.high" % name)
    if low <= 0.0:
        raise ValueError("%s: low edge must be > 0, got %g" % (name, low))
    if high <= low:
        raise ValueError(
            "%s: high edge (%g) must exceed the low edge (%g)" % (name, high, low)
        )
    return (low, high)


def validate_injection_point(record, where="point"):
    """Validate one swept injection point and return it normalized.

    A point carries the bundle it was injected onto, the frequency, the
    current the specified level asks for, the current the bench actually
    drove, and the injected current at which a performance deviation
    first appeared -- None when the unit rode the whole point out.
    """
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)

    bundle = _token(record, "bundle", where)
    point = {"bundle": bundle}
    for key in ("frequency_hz", "required_current_a", "achieved_current_a"):
        value = _number(record, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        point[key] = value

    onset = record.get("deviation_current_a", None)
    if onset is not None:
        onset = _scalar(onset, "%s.deviation_current_a" % where)
        if onset <= 0.0:
            raise ValueError(
                "%s: deviation_current_a must be > 0 when present, got %g"
                % (where, onset)
            )
    point["deviation_current_a"] = onset
    return point


def validate_sweep(points, where="sweep"):
    """Validate one bundle's sweep: at least two points, advancing in frequency."""
    if isinstance(points, dict) or not isinstance(points, (tuple, list)):
        raise ValueError("%s: must be a sequence of injection points" % where)
    if len(points) < 2:
        raise ValueError("%s: needs at least 2 points, got %d" % (where, len(points)))

    normalized = []
    previous = None
    for index, record in enumerate(points):
        point = validate_injection_point(record, "%s[%d]" % (where, index))
        if previous is not None and not point["frequency_hz"] > previous:
            raise ValueError(
                "%s[%d]: frequencies must advance; %g follows %g"
                % (where, index, point["frequency_hz"], previous)
            )
        previous = point["frequency_hz"]
        normalized.append(point)

    bundles = {point["bundle"] for point in normalized}
    if len(bundles) != 1:
        raise ValueError(
            "%s: a sweep covers one bundle, got %s" % (where, ", ".join(sorted(bundles)))
        )
    return normalized


def grid_step_ratio(points_per_decade=POINTS_PER_DECADE):
    """Largest frequency ratio between two neighbouring points on the grid."""
    per_decade = _scalar(points_per_decade, "points_per_decade")
    if per_decade < 1.0:
        raise ValueError("points_per_decade must be >= 1, got %g" % per_decade)
    return math.pow(10.0, 1.0 / per_decade)


def coverage_gaps(frequencies, band, points_per_decade=POINTS_PER_DECADE):
    """Stretches of the band the sweep left uncovered, as (low, high) pairs."""
    low, high = validate_band(band)
    if isinstance(frequencies, dict) or not isinstance(frequencies, (tuple, list)):
        raise ValueError("frequencies: must be a sequence")
    if not frequencies:
        raise ValueError("frequencies: must not be empty")
    step = grid_step_ratio(points_per_decade)

    values = []
    previous = None
    for index, item in enumerate(frequencies):
        value = _scalar(item, "frequencies[%d]" % index)
        if value <= 0.0:
            raise ValueError("frequencies[%d]: must be > 0, got %g" % (index, value))
        if previous is not None and not value > previous:
            raise ValueError(
                "frequencies[%d]: must advance; %g follows %g" % (index, value, previous)
            )
        previous = value
        values.append(value)

    gaps = []
    if not at_most(values[0], low * step):
        gaps.append((low, values[0]))
    for first, second in zip(values, values[1:]):
        if first >= high or second <= low:
            continue
        if not at_most(second / first, step):
            gaps.append((first, second))
    if not at_least(values[-1] * step, high):
        gaps.append((values[-1], high))
    return gaps


def categorize_drive(achieved_current_a, required_current_a,
                     tolerance_db=AT_LIMIT_TOLERANCE_DB):
    """Grade the current the bench drove against the level required."""
    tolerance = _scalar(tolerance_db, "tolerance_db")
    if tolerance < 0.0:
        raise ValueError("tolerance_db must be >= 0, got %g" % tolerance)
    margin = margin_db(achieved_current_a, required_current_a)
    if at_most(abs(margin), tolerance):
        return AT_LIMIT
    return MEETS_LIMIT if margin > 0.0 else DRIVE_SHORTFALL


def categorize_response(point, tolerance_db=AT_LIMIT_TOLERANCE_DB):
    """Grade where a performance deviation appeared against the required level."""
    tolerance = _scalar(tolerance_db, "tolerance_db")
    if tolerance < 0.0:
        raise ValueError("tolerance_db must be >= 0, got %g" % tolerance)
    onset = point["deviation_current_a"]
    if onset is None:
        return NOT_SUSCEPTIBLE, None
    threshold = margin_db(onset, point["required_current_a"])
    if at_most(threshold, tolerance):
        return SUSCEPTIBLE_AT_OR_BELOW_LIMIT, threshold
    return SUSCEPTIBLE_ABOVE_LIMIT, threshold


def grade_point(point, tolerance_db=AT_LIMIT_TOLERANCE_DB):
    """Reduce one validated injection point to its graded record."""
    graded = dict(point)
    graded["drive_margin_db"] = margin_db(
        point["achieved_current_a"], point["required_current_a"]
    )
    graded["drive_category"] = categorize_drive(
        point["achieved_current_a"], point["required_current_a"], tolerance_db
    )
    response, threshold = categorize_response(point, tolerance_db)
    graded["response"] = response
    graded["threshold_margin_db"] = threshold
    graded["governing_margin_db"] = (
        graded["drive_margin_db"] if threshold is None
        else min(graded["drive_margin_db"], threshold)
    )
    return graded


def worst_point(graded_points):
    """The graded point carrying the least margin, ties broken by frequency."""
    if isinstance(graded_points, dict) or not isinstance(graded_points, (tuple, list)):
        raise ValueError("graded_points: must be a sequence")
    if not graded_points:
        raise ValueError("graded_points: must not be empty")
    ranked = sorted(
        graded_points,
        key=lambda item: (item["governing_margin_db"], item["frequency_hz"]),
    )
    return ranked[0]


def assess_cable_injection_aim(
    records,
    band,
    required_bundles,
    points_per_decade=POINTS_PER_DECADE,
    at_limit_tolerance_db=AT_LIMIT_TOLERANCE_DB,
):
    """Full clause 5.4.8.1 assessment of a sine wave cable injection run."""
    if isinstance(records, dict) or not isinstance(records, (tuple, list)):
        raise ValueError("records: must be a sequence of injection points")
    if not records:
        raise ValueError("records: must not be empty")
    if isinstance(required_bundles, str) or not isinstance(
        required_bundles, (tuple, list, set, frozenset)
    ):
        raise ValueError("required_bundles: must be a sequence of bundle names")
    required = {str(name).strip().lower() for name in required_bundles}
    if not required:
        raise ValueError("required_bundles: must name at least one bundle")

    low, high = validate_band(band)

    grouped = {}
    for index, record in enumerate(records):
        point = validate_injection_point(record, "records[%d]" % index)
        grouped.setdefault(point["bundle"], []).append(point)

    findings = []
    limitations = []
    bundles = {}
    for name in sorted(grouped):
        points = validate_sweep(grouped[name], "sweep[%s]" % name)
        graded = [grade_point(point, at_limit_tolerance_db) for point in points]
        gaps = coverage_gaps(
            [point["frequency_hz"] for point in points], (low, high), points_per_decade
        )
        bundles[name] = {
            "points": graded,
            "coverage_gaps": gaps,
            "worst": worst_point(graded),
        }
        for gap_low, gap_high in gaps:
            findings.append(
                "bundle %s leaves %g Hz to %g Hz of the swept band uncovered"
                % (name, gap_low, gap_high)
            )
        for item in graded:
            if item["drive_category"] == DRIVE_SHORTFALL:
                findings.append(
                    "bundle %s at %g Hz reached %g A against the %g A required, "
                    "%.2f dB short; the level was never applied"
                    % (
                        name,
                        item["frequency_hz"],
                        item["achieved_current_a"],
                        item["required_current_a"],
                        item["drive_margin_db"],
                    )
                )
            elif item["drive_category"] == AT_LIMIT:
                limitations.append(
                    "bundle %s at %g Hz sat on the required level with %.2f dB of "
                    "margin; the next bench will move it"
                    % (name, item["frequency_hz"], item["drive_margin_db"])
                )
            if item["response"] == SUSCEPTIBLE_AT_OR_BELOW_LIMIT:
                findings.append(
                    "bundle %s deviated at %g Hz from %g A, at or under the %g A "
                    "required; the aim is not met at that frequency"
                    % (
                        name,
                        item["frequency_hz"],
                        item["deviation_current_a"],
                        item["required_current_a"],
                    )
                )
            elif item["response"] == SUSCEPTIBLE_ABOVE_LIMIT:
                limitations.append(
                    "bundle %s deviated at %g Hz only %.2f dB above the required "
                    "level; the threshold is known and close"
                    % (name, item["frequency_hz"], item["threshold_margin_db"])
                )

    for name in sorted(required - set(bundles)):
        findings.append(
            "required bundle %s was never injected; the aim covers every bundle "
            "reaching the unit" % name
        )
    extra = sorted(set(bundles) - required)
    for name in extra:
        limitations.append(
            "bundle %s was injected although it is not on the required list; its "
            "result is carried but does not close a required bundle" % name
        )

    covered = sorted(required & set(bundles))
    governing = None
    if covered:
        governing = worst_point([bundles[name]["worst"] for name in covered])

    if findings:
        verdict = VERDICT_NOT_DEMONSTRATED
    elif limitations:
        verdict = VERDICT_WITH_LIMITATIONS
    else:
        verdict = VERDICT_DEMONSTRATED

    return {
        "band_hz": (low, high),
        "bundles": bundles,
        "required_bundles": sorted(required),
        "covered_bundles": covered,
        "governing_bundle": None if governing is None else governing["bundle"],
        "governing_frequency_hz": None if governing is None else governing["frequency_hz"],
        "governing_margin_db": None if governing is None else governing["governing_margin_db"],
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
